use anchor_lang::prelude::*;
use crate::{Global, PumpError};

// ===========================================================================
// set_mayhem_virtual_params   (wrapper 0x24ab5 -> execute 0x26ff8)
//
// Binary-derived reconstruction. There is NO recovered source counterpart:
// the instruction is absent from the official IDL / lib.rs but is a real,
// dispatchable entrypoint (disc 3da9bcbf99952a61, lddw@0x2372f, log string
// "Instruction: SetMayhemVirtualParams" @ rodata 0x1b7d20). Everything here is
// reconstructed from deployed.so; field names below the binary cannot name are
// inferred and flagged as such.
//
// ---------------------------------------------------------------------------
// PERSISTENCE (OPEN QUESTION — RESOLVED): account write-back, NOT a Mayhem CPI.
// ---------------------------------------------------------------------------
// The validate-and-clamp helper 0x1447e writes the clamped parameter value back
// into the params account with `stxdw [r2+0x48], r1` at 0x14507 and 0x1450e,
// where r2 is the mutable account sub-struct passed in as `r8+0x1f0` (restored
// from stack slot [r10-0xb0] at 0x144f0 / 0x144f9). r8 is the accounts context
// (`r8 = [args+0x8]`), and [r8+0x210..0x248] is the contiguous 8xu64 virtual-
// parameter block; r2+0x48 == r8+0x238 is one of those params.
//
// The execute body 0x26ff8 contains NO callx / invoke_signed into the Mayhem
// program (MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e). Its only external
// calls are: the bounds helper (0x1447e), Clock::get (0x34127), the allocator
// (0x35633), the formatter/serializer (0x33777), and the emit!/emit_cpi! pair
// (0x3409f) — the latter being the standard Anchor event self-CPI (program
// refcount bump at [r8+0x190]/[r8+0x188]), to THIS program, not to Mayhem.
// Anchor's generated wrapper exit (0x24af3 -> 0x19ea2) then serializes the
// mutated, program-owned params account back to its data buffer. Hence the
// "set" is a write-back of the validated params, and the persisted account must
// be owned by this program (a Mayhem-owned UncheckedAccount could not be
// written directly without a CPI, and no such CPI exists in the body).
// ===========================================================================

// --- Lamport sanity bounds enforced by helper 0x1447e ----------------------
// Floor: values below 1e6 take the error/return path (0x144a0 `jlt r8,0xf4240`).
const VIRTUAL_PARAM_MIN_LAMPORTS: u64 = 1_000_000; //        0xf4240       (1e6)
const VIRTUAL_RESERVE_MIN_LAMPORTS: u64 = 10_000_000; //     0x989680      (1e7)
const VIRTUAL_PARAM_MAX_LAMPORTS: u64 = 1_000_000_000_000; //0xe8d4a51000  (1e12)
// --- Clamp ceilings written back at 0x14507 / 0x1450e ----------------------
// Which ceiling applies is selected by a bool gate in the account ([r2+0x99]/
// [r2+0x9a]); modelled here by `clamp_token_scale`.
const VIRTUAL_QUOTE_CLAMP_CEILING: u64 = 160_000_000_000; // 0x2540be4000  (1.6e11)
const VIRTUAL_TOKEN_CLAMP_CEILING: u64 = 2_000_000_000_000; //0x1d1a94a2000 (2e12)

// ---------------------------------------------------------------------------
// Program-owned Mayhem configuration account holding the virtual-parameter
// block. Offsets in comments are the context offsets observed in 0x26ff8 /
// 0x1447e (relative to r8). The deployed struct is larger than reconstructed
// here (the i64 at +0x250 and the gates at +0x289/+0x28a leave a gap that
// implies further unrecovered fields); only the fields the binary touches are
// modelled. Field names are INFERRED from bonding-curve/reserve semantics.
// ---------------------------------------------------------------------------
#[account]
#[derive(Default)]
pub struct MayhemConfig {
    pub virtual_token_reserves: u64,  // +0x210
    pub virtual_quote_reserves: u64,  // +0x218
    pub real_token_reserves: u64,     // +0x220
    pub real_quote_reserves: u64,     // +0x228
    pub token_total_supply: u64,      // +0x230  (helper input [r2+0x40])
    pub derived_quote_reserves: u64,  // +0x238  (helper WRITE target [r2+0x48])
    pub min_quote_in: u64,            // +0x240
    pub max_quote_in: u64,            // +0x248  (helper input [r2+0x58])
    pub config_value: i64,            // +0x250  (helper input [r2+0x60])
    pub enabled: bool,                // +0x289  (gate [r2+0x99])
    pub clamp_token_scale: bool,      // +0x28a  (gate [r2+0x9a]: 2e12 vs 1.6e11)
}

// ---------------------------------------------------------------------------
// Accounts. Admin-gated exactly like the other authority setters in this crate
// (AdminGlobal / set_params): the global PDA carries `has_one = authority`, so
// only Global.authority may invoke. The written account (`mayhem_config`) is a
// program-owned PDA so the write-back persists via Anchor's serialize-on-exit.
// `#[event_cpi]` supplies the event_authority + program accounts for emit_cpi!.
//
// NOTE (inferred): the exact seeds of the persisted params account are not
// provable from the stripped binary. It is modelled as a dedicated program PDA
// ["mayhem-config"]; it could instead be a region appended to Global or another
// program-owned PDA. The persistence MECHANISM (write-back, not CPI) is proven;
// the account IDENTITY is the residual uncertainty.
// ---------------------------------------------------------------------------
#[event_cpi]
#[derive(Accounts)]
pub struct SetMayhemVirtualParams<'info> {
    #[account(seeds = [b"global"], bump, has_one = authority @ PumpError::NotAuthorized)]
    pub global: Box<Account<'info, Global>>,
    #[account(mut, seeds = [b"mayhem-config"], bump)]
    pub mayhem_config: Account<'info, MayhemConfig>,
    #[account(mut)]
    pub authority: Signer<'info>,
}

// 8x u64 virtual-parameter block carried as instruction arguments. (The body
// reads the live values out of the account context; behaviourally the setter
// takes the new values in, validates/clamps, and writes them back — the same
// net effect.)
#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct MayhemVirtualParams {
    pub virtual_token_reserves: u64,
    pub virtual_quote_reserves: u64,
    pub real_token_reserves: u64,
    pub real_quote_reserves: u64,
    pub token_total_supply: u64,
    pub derived_quote_reserves: u64,
    pub min_quote_in: u64,
    pub max_quote_in: u64,
}

// ---------------------------------------------------------------------------
// Event. The on-chain discriminator is 757be4b6a1a8dcd6
// (= bytes [117,123,228,182,161,168,220,214], stored via the immediate
// -0x2923575e491b848b at 0x2704f / 0x270a1). This disc does NOT match the
// Anchor hash of "event:SetMayhemVirtualParamsEvent" (nor CreateEvent /
// SetParamsEvent / the guessed MayhemVirtualParamsEvent), so the TRUE on-chain
// struct name is unknown and differs from the name used here. The name below is
// descriptive only; the raw disc is the load-bearing fact. The 0x60-byte event
// buffer built at 0x2704c..0x27066 is: disc(8) + timestamp i64 (+0x08, from
// Clock unix_timestamp [r10-0xa8]) + a 32-byte key (+0x10..+0x28, first 32
// bytes of the second account read at [r8+0x58]) + six u64 param words
// (+0x30..+0x58).
// ---------------------------------------------------------------------------
#[event]
#[derive(Clone)]
pub struct SetMayhemVirtualParamsEvent {
    pub timestamp: i64,
    pub mayhem_config: Pubkey,
    pub virtual_token_reserves: u64,
    pub virtual_quote_reserves: u64,
    pub real_token_reserves: u64,
    pub real_quote_reserves: u64,
    pub token_total_supply: u64,
    pub derived_quote_reserves: u64,
    pub min_quote_in: u64,
    pub max_quote_in: u64,
}

// Validate a single param against the [1e6, 1e12] lamport window (helper floor
// check at 0x144a0; the 1e7 reserve floor applies to reserve-class params).
fn require_param_in_bounds(value: u64, reserve_class: bool) -> Result<()> {
    let floor = if reserve_class {
        VIRTUAL_RESERVE_MIN_LAMPORTS
    } else {
        VIRTUAL_PARAM_MIN_LAMPORTS
    };
    require!(value >= floor, PumpError::Overflow);
    require!(value <= VIRTUAL_PARAM_MAX_LAMPORTS, PumpError::Overflow);
    Ok(())
}

pub fn execute(
    ctx: Context<SetMayhemVirtualParams>,
    params: MayhemVirtualParams,
    clamp_token_scale: bool,
) -> Result<()> {
    // --- Bounds validation (helper 0x1447e, floor/ceiling against 1e6/1e7/1e12)
    require_param_in_bounds(params.virtual_token_reserves, true)?;
    require_param_in_bounds(params.virtual_quote_reserves, true)?;
    require_param_in_bounds(params.real_token_reserves, true)?;
    require_param_in_bounds(params.real_quote_reserves, true)?;
    require_param_in_bounds(params.token_total_supply, false)?;
    require_param_in_bounds(params.min_quote_in, false)?;
    require_param_in_bounds(params.max_quote_in, false)?;

    // --- Derived quote reserves: the helper computes a value from the param
    // block (mul at 0x144c4, checked add at 0x144c8) then clamps it to the
    // ceiling selected by a gate (0x14507 writes the 1.6e11 ceiling; 0x1450e
    // writes the 2e12 ceiling) before the write-back. The exact arithmetic is
    // not fully recoverable from the stripped body; modelled as a product
    // relationship with overflow checking, then the observed ceiling clamp.
    let derived = (params.virtual_token_reserves as u128)
        .checked_mul(params.virtual_quote_reserves as u128)
        .ok_or_else(|| error!(PumpError::Overflow))?
        .checked_div(VIRTUAL_PARAM_MIN_LAMPORTS as u128)
        .ok_or_else(|| error!(PumpError::DivisionByZero))?;
    let mut derived = u64::try_from(derived).unwrap_or(u64::MAX);
    let ceiling = if clamp_token_scale {
        VIRTUAL_TOKEN_CLAMP_CEILING
    } else {
        VIRTUAL_QUOTE_CLAMP_CEILING
    };
    if derived > ceiling {
        derived = ceiling; // clamp written back at 0x14507 / 0x1450e
    }

    // --- Write-back (the persistence site): the validated/clamped params are
    // stored into the program-owned config account, which Anchor serializes on
    // exit. This is the reconstructed equivalent of the `stxdw [r2+0x48]` store.
    let config = &mut ctx.accounts.mayhem_config;
    config.virtual_token_reserves = params.virtual_token_reserves;
    config.virtual_quote_reserves = params.virtual_quote_reserves;
    config.real_token_reserves = params.real_token_reserves;
    config.real_quote_reserves = params.real_quote_reserves;
    config.token_total_supply = params.token_total_supply;
    config.derived_quote_reserves = derived;
    config.min_quote_in = params.min_quote_in;
    config.max_quote_in = params.max_quote_in;
    config.clamp_token_scale = clamp_token_scale;

    // --- Dual emit (0x2706b emit!, 0x2707f emit_cpi!) ------------------------
    let event = SetMayhemVirtualParamsEvent {
        timestamp: Clock::get()?.unix_timestamp,
        mayhem_config: config.key(),
        virtual_token_reserves: config.virtual_token_reserves,
        virtual_quote_reserves: config.virtual_quote_reserves,
        real_token_reserves: config.real_token_reserves,
        real_quote_reserves: config.real_quote_reserves,
        token_total_supply: config.token_total_supply,
        derived_quote_reserves: config.derived_quote_reserves,
        min_quote_in: config.min_quote_in,
        max_quote_in: config.max_quote_in,
    };
    emit!(event.clone());
    emit_cpi!(event);
    Ok(())
}
