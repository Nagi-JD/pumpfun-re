//! initialize_mayhem_state reconstructed from the deployed mayhem binary.
//! wrapper 0x101de -> parser 0xd25f -> handler 0x10527 (106 insns) -> exit 0xdabe.
//! disc 9dbd5e485545cc2d ("global:initialize_mayhem_state"), no instruction args.
//! Every field write below is cross-checked against the deployed handler body 0x10527;
//! the cited addresses are sbftool pc units (byte = pc*8). See mayhem_init_state.md.
use anchor_lang::prelude::*;
use crate::checked_program::{CheckedSystemProgram, CheckedSystemProgramBumps, __client_accounts_checked_system_program, __cpi_client_accounts_checked_system_program};
use anchor_spl::associated_token::AssociatedToken;
use anchor_spl::token_interface::{Mint, TokenAccount, TokenInterface};
use crate::state::{BondingCurve, MayhemState, MayhemStatus, PUMP_ID};
use crate::{GlobalParams, MayhemError};

#[derive(Accounts)]
pub struct InitializeMayhemState<'info> {
    // parser 0xd25f: fetch 0x1406 (Signer) -> payer
    #[account(mut)]
    pub payer: Signer<'info>,
    // parser fetch 0x145a (Account) -> global_params ["global-params"]
    #[account(seeds = [b"global-params"], bump)]
    pub global_params: Box<Account<'info, GlobalParams>>,
    // parser fetch 0x59e->0x8c6 (InterfaceAccount<Mint>, owner in {spl_token, spl_token_2022}
    // at rodata 0xae302/0xae322; unpack 0x12433). Handler reads its key at [T+0x58] (0x10528).
    pub mint: Box<InterfaceAccount<'info, Mint>>,
    // init, space 106 (serialized MayhemState size; 106 const in parser region 0xd8af/0xd93b).
    // seeds ["mayhem-state", mint] (seed string 0xadc0e). extend_account later grows to 170.
    #[account(init, payer = payer, space = 106, seeds = [b"mayhem-state", mint.key().as_ref()], bump)]
    pub mayhem_state: Box<Account<'info, MayhemState>>,
    // mayhem_token_vault: ATA(mint, authority = sol_vault) (name string 0xadbc9), mut
    #[account(mut,
        associated_token::mint = mint,
        associated_token::authority = sol_vault,
        associated_token::token_program = mint.to_account_info().owner)]
    pub mayhem_token_vault: Box<InterfaceAccount<'info, TokenAccount>>,
    /// CHECK: ["sol-vault"] PDA, writable (name string "sol_vault" built at parser 0xd31d).
    #[account(mut, seeds = [b"sol-vault"], bump)]
    pub sol_vault: UncheckedAccount<'info>,
    // bonding_curve ["bonding-curve", mint] under pump (seed string 0xadc0e+12); 82-byte codec.
    #[account(seeds = [b"bonding-curve", mint.key().as_ref()], bump, seeds::program = PUMP_ID)]
    pub bonding_curve: Box<Account<'info, BondingCurve>>,
    // program accounts: system_program (0xadaf4), token_program (0xadb89), associated (0xadb96)
    pub system_program: CheckedSystemProgram<'info>,
    pub token_program: Interface<'info, TokenInterface>,
    pub associated_token_program: Program<'info, AssociatedToken>,
}

pub fn handler(ctx: Context<InitializeMayhemState>) -> Result<()> {
    // 0x1054f: r9 = ldxb [accounts+0x2c4] -- a u8 duration/limit byte.
    // [partial] The byte source is not statically proven (mayhem_init_state.md Sec 4 item 1).
    // Reconstructed here as a GlobalParams byte; the differential harness seeds it to 0 so the
    // multiplier path is a no-op (end_timestamp == now) and does not force an unproven source.
    let dur: u8 = ctx.accounts.global_params.reset_middle[0];
    // 0x10552: Clock::get via 0x13dfa; 0x10555: now = [r10-0x10].unix_timestamp
    let now = Clock::get()?.unix_timestamp;
    let state = &mut ctx.accounts.mayhem_state;
    // 0x10556: [T+0x1a0] = now  -> in-memory field_8 (serialized offset 8, "start" timestamp)
    state.field_8 = now as u64;
    // 0x10557: r9 *= 0xe10 (3600) with checked signed overflow (branch 0x1055a..0x1055f;
    // overflow path 0x10583 -> 0x15154 panic). 0x10562: [T+0x1a8] = now + r9.
    let delta = (dur as i64)
        .checked_mul(3600)
        .ok_or(MayhemError::MathOverflow)?;
    state.end_timestamp = now
        .checked_add(delta)
        .ok_or(MayhemError::MathOverflow)?; // serialized offset 16
    // 0x10547..0x1056a: copy 32-byte key of account at [T+0x58] (mint) -> [T+0x160..0x180]
    state.mint = ctx.accounts.mint.key(); // serialized offset 24
    // 0x1056c/0x1056d: zero [T+0x180],[T+0x188] -> field_56 i128
    state.field_56 = 0; // serialized offset 56
    // 0x1056e/0x1056f: zero [T+0x190],[T+0x198] -> field_72 i128
    state.field_72 = 0; // serialized offset 72
    // 0x1056b: [T+0x1b0] = now -> field_89 (last-trade timestamp, read by buy/sell)
    state.field_89 = now as u64; // serialized offset 89
    // 0x10570: sth [T+0x1c0] = 0 (u16) zeroes flag_88 (serialized 88) and status (serialized 97)
    state.flag_88 = false;
    state.status = MayhemStatus::Variant0;
    // 0x10571: [T+0x1b8] = 0 -> burned_amount
    state.burned_amount = 0; // serialized offset 98
    // 0x10572..0x10591: RefCell borrow release; 0x1057b exit r0=2 (Ok). Persistence via exit 0xdabe.
    Ok(())
}
