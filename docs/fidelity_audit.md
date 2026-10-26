# Reconstruction fidelity audit - recovered source vs deployed binaries

Private analysis for the user. Scope: the four deployed pump.fun programs. The goal is to
find places where the recovered SOURCE (the base lalalune tree plus the Nagi-JD
`recovered-fixes/` overlay in `D:/dev/pumpfun-re/clone/`) would behave differently from the
deployed binary, so Claude can confirm each item by execution and fix it.

Tags: **[B]** = confirmed in the deployed disassembly / rodata; **[R]** = recovered source
or recovered-fixes overlay; **[partial]** = inferred, reason stated. Addresses are `sbftool`
pc units (byte address = pc*8) unless a raw byte/rodata address is marked.

Method: cross-checked the binary-derived specs (`spec/01..11-*.md`, `amm_specs.md`,
`fees_specs.md`, `mayhem_specs.md`, `create_v2_mayhem.md`, `multihop_specs.md`,
`pump_error_map.md`), the base source (`D:/dev/ext/pumpfun-source/programs/*/src`), the
`recovered-fixes` overlay (`D:/dev/pumpfun-re/clone`), and targeted `sbftool` disassembly
(callers of the transfer-fee helper, the Mayhem CPI builder, the mayhem disc search, the
admin_cto guard emits). No build or execution was performed here.

Status key: **OPEN** = not fixed; **PARTIAL** = a fix exists but is incomplete or inferred;
**FIXED-VERIFY** = the overlay appears to fix it and needs a harness run; **NO-DIVERGENCE**.

## Priority summary

| id | program | handler @ address | divergence | severity | status |
|---|---|---|---|---|---|
| F1 | pump | `admin_cto` wrapper `0x25b40`, execute `0x4542` | deployed guard set/order differs from source: no 6088/6092, extra 6080/6095, reordered | HIGH (security/admin) | OPEN |
| F2 | pump | `create_v2` wrapper `0x24d15`, execute body `0x3cf8..0x4492` [partial pin] | Mayhem CPI data is 8 bytes in the binary; recovered-fixes adds args; no second mint to `mayhem_token_vault`; account list/order inferred | HIGH (function/economics) | PARTIAL |
| F3 | mayhem | `initialize_mayhem_state` wrapper `0x101de`, parser `0xd25f`, body `0x10527` | handler absent from the recovered mayhem build/source; deployed has it at disc `9dbd5e485545cc2d` | HIGH (completeness; blocks create_v2 Mayhem CPI) | OPEN |
| F4 | pump | `set_mayhem_virtual_params` wrapper `0x24ab5`, execute `0x26ff8` | no source counterpart; recovered-fixes infers account seeds, args, and arithmetic; persistence mechanism is binary-proven | MEDIUM-HIGH (state/config) | PARTIAL |
| F5 | pump | `multi_hop_curve_swap` wrapper `0x252b8`, execute `0xacfb` | recovered-fixes adds a depth cap inside the curve executor; deployed executor has no cap (cap is in nested_create/outer router) | MEDIUM (route availability) | PARTIAL (suspect over-fix) |
| F6 | pump | `migrate` wrapper `0x256fb`, execute `0x7f6e` | source AMM-create account list passes `token_program` twice; binary passes distinct token programs | MEDIUM-HIGH (migration) | OPEN |
| F7 | pump | buy_v2 `0x24ea2`, sell_v3 `0x25231`, buy_v3 `0x250d9`, buy_exact_quote_in_v3 `0x25185` | base source omits Token-2022 net accounting; recovered-fixes adds it (helper `0x12a1c`); scope needs harness confirmation | HIGH for fee-bearing quotes | FIXED-VERIFY |
| F8 | pump | sell_v3 `0x25231` / buy_v3 `0x250d9`; `check_quote` `0x204af` | base source hardcodes USDC and does not derive the index-7 quote ATA for a general whitelisted quote; recovered-fixes fixes both | HIGH (quote route + account binding) | FIXED-VERIFY |
| F9 | pump | `claim_cashback` `0x25d99`, `claim_cashback_v2` `0x25e2a` | deployed logs on the zero-amount path; source returns silently | LOW (log only) | OPEN (cosmetic) |

The two examples named in the task are covered: **admin_cto** is F1 (real divergence), and the
**PumpError 6010/6022** item is NOT a source divergence (see the "Do not re-flag" section - the
source enum already matches the binary; the earlier spec/error-catalog attribution was wrong).
The **v3 USDC over-restriction** and **SellV3 index-7 seeds** items are F8 (base source wrong,
recovered-fixes fixes it). The **Token-2022 transfer-fee direction** is F7 (base source wrong,
overlay fixes it; confirm the net-vs-gross use with a harness).

---

## F1 - `admin_cto` guard set/order is a different revision

**Program / handler.** pump; wrapper `0x25b40`, execute `0x4542`; `try_accounts` `0x16caf`.
Source: `programs/pump/src/admin_cto.rs`.

**Deployed behavior [B].** Execute emits these AnchorError codes, in this address order:

| # | emit pc | code | PumpError |
|---:|---|---:|---|
| 1 | `0x4654` | 6083 | HolderRewardCreatorImmutable |
| 2 | `0x468c` | 6090 | CtoNewCreatorNotAllowed |
| 3 | `0x471d` | 6089 | CtoNewCreatorRequired |
| 4 | `0x4752` | 6084 | HolderRewardDisabled |
| 5 | `0x4780` | 6091 | CreatorFeeNotConfigurableForQuote |
| 6 | `0x479e` | 6019 | InvalidCreator |
| 7 | `0x47b8` | 6030 | CreatorShouldNotBeZero |
| 8 | `0x4800` | 6080 | CreatorFeeNotAllowedForCashbackCoin |
| 9 | `0x481f` | 6078 | CreatorFeeBpsOutOfRange |
| 10 | `0x4839` | 6077 | CreatorFeeNotConfigurable |
| 11 | `0x48c4` | 6095 | CreatorFeesNotSwept |

`CtoNotAllowedForMayhemCoin` (6088, `0x17c8`) and `CtoCreatorAccountNotWritable` (6092,
`0x17cc`) are **absent** from the wrapper, `try_accounts`, and execute (grep = 0). The deployed
handler uses the standard AnchorError idiom (`stw [r10-0x238], code`).

**Reconstruction behavior [R].** `admin_cto.rs:99` defines `err(n) -> ProgramError::Custom(n)`;
the guard block is:
- `admin_cto.rs:102`: `if flag(81) { return Err(err(6088)); }` (mayhem coin rejection)
- `admin_cto.rs:102-109`: 6083, 6084, 6090, 6089, 6030, 6019, 6091, 6077, 6078
- `admin_cto.rs:113` and `:121`: `return Err(err(6092))` on the wallet-payout branch
- no 6080, no 6095 anywhere.

**Divergence.** The deployed handler drops both the mayhem-coin guard and the
current-creator-writable guard, and adds a cashback-fee guard (6080) and a fees-swept guard
(6095). It also reorders the shared guards (6090/6089 before 6084; 6091 before 6019/6030;
6078 before 6077; 6019 before 6030). The source's `err()` helper also produces
`ProgramError::Custom` rather than an AnchorError, so the error origin/file/line metadata
differs even where the numeric code is shared.

**Impact.** Admin/security behavior: the source blocks CTO on mayhem coins and requires the
current creator account to be writable, both of which the deployed program does not; the
source allows a cashback-coin creator-fee change and a CTO before creator fees are swept,
both of which the deployed program rejects. Only the admin authority can invoke, so this is
not an unauthenticated exploit, but it changes which admin transactions succeed and is a
real revision mismatch. **HIGH.**

**Status / next test.** OPEN. Build the source and run differential `admin_cto` cases:
mayhem coin, cashback coin, unswept creator fee, non-writable current creator, holder/new
creator combinations. Expect code-set/order differences. The 47-call CPI tail and the
byte-level curve writes were not exhaustively decoded in the source spec, so keep the
verdict at "guard set/order confirmed; tail not fully audited" [B]/[partial].

---

## F2 - `create_v2` Mayhem branch: CPI payload is wrong and the second mint is missing

**Program / handler.** pump; wrapper `0x24d15`; Mayhem branch of execute. The exact body
span is `0x3cf8..0x4492` per the recovered-fixes header [partial]; the binary error sites are
`6046 CreateV2Disabled` at `0x3e44`, `6048 MayhemModeDisabled` at `0x41e5`, and
`6071 MayhemModeQuoteMintNotAllowed` at `0x414b` [B].

**Deployed behavior [B/partial].**
- The Mayhem `initialize_mayhem_state` CPI data builder is at `0x23181`: `lddw r1,
  0x2dcc4555485ebd9d` (= bytes `9d bd 5e 48 55 45 cc 2d`), `stxdw [r7+0], r1`, and the data
  length store at `0x231ac: stdw [r10-0x58], 0x8`. The CPI payload is **disc-only, 8 bytes,
  no arguments**.
- The helper builds AccountMeta entries with a 34-byte stride (`0x23194: mul64 r4,0x22`); the
  account keys are copied from create-body stack slots at `0x116e0-0x116f3` [partial order].
- `mayhem_token_vault` is a mut account in `CreateV2`; the only mint authority is the pump
  `mint-authority` PDA, so funding it requires a second `mint_to` before the authority is
  revoked [partial placement, strong constraint].
- Errors: 6047 `CpitializeMayhemFailed` is never a raw immediate; it wraps the CPI result
  (map_err) [B absence + R model].

**Reconstruction behavior [R].**
- Base source: `create_v2.rs:39` `require!(!is_mayhem_mode,
  ReconstructionBranchUnsupported)` - the branch is a stub.
- Recovered-fixes `clone/create_v2.rs`: implements gates 6048/6071, but:
  - builds `mayhem_data = selector.to_vec() + mint.key() + creator + initial_virtual_token_reserves
    + virtual_quote_reserves` (88+ bytes), contradicting the binary's 8-byte disc-only data;
  - places the CPI after `set_authority` (revoke) and has **no second `mint_to`** to
    `mayhem_token_vault`;
  - uses an inferred 9-account meta list (binary meta array is built at `0x116e0-0x116f3`,
    order/count not pinned);
  - infers the quote restriction as `ctx.remaining_accounts.is_empty()`.

**Divergence.** The CPI payload is not the binary's 8-byte disc-only payload; depending on
how the Mayhem parser treats trailing bytes it may be rejected or silently truncated, and
the account list/order is inferred. Independently, the reconstructed branch has no second
mint, so the Mayhem token vault is not funded. **HIGH** (functional; mayhem coin creation is
broken or creates wrong state).

**Status / next test.** PARTIAL. Fix: send only the 8-byte disc, use the binary meta order,
move the CPI before the revoke, and add the second `mint_to` for `token_total_supply` before
revocation. Then log the inner CPI instruction (data length must be 8; compare account list)
and run a mayhem create end-to-end.

---

## F3 - Mayhem `initialize_mayhem_state` is absent from the recovered program

**Program / handler.** mayhem; deployed wrapper `0x101de`, parser `0xd25f`, handler body
`0x10527`; Anchor/custom disc `9dbd5e485545cc2d`.

**Deployed behavior [B].** The deployed mayhem ELF contains the disc immediate at pc
`0xfb59`; total 83,947 instructions / 502 functions. The handler has no args and initializes
the per-mint `mayhem_state` (mint key, timestamps, zeroed counters, persistence via the
Anchor exit), per `mayhem_specs.md` Sec.25 and `create_v2_mayhem.md` Sec.3.3.

**Reconstruction behavior [R].** The recovered `mayhem_recovered.so` has 71,875
instructions / 461 functions and **no** `lddw` of `0x2dcc4555485ebd9d` (disc search = empty).
`programs/mayhem/src/lib.rs` also has no `initialize_mayhem_state` / `InitializeMayhemState`
symbol. This is the ~41-function / ~12k-instruction shortfall recorded in `VERIFICATION.md`
update 6.

**Divergence.** The one handler the pump `create_v2` Mayhem branch CPIs into is missing from
the reconstruction, so the Mayhem program cannot serve that CPI and cannot be verified
end-to-end. **HIGH** (completeness).

**Status / next test.** OPEN. Implement the handler from `mayhem_specs.md` (no args, disc-only
CPI, account list per the pump meta builder), rebuild, verify the disc appears in the
recovered `.so`, then run a mayhem `create_v2` with the inner-instruction log.

---

## F4 - `set_mayhem_virtual_params` is an inferred reconstruction

**Program / handler.** pump; wrapper `0x24ab5`, execute `0x26ff8`; validation/clamp helper
`0x1447e`; event emit sites `0x2704f`/`0x270a1` (disc `757be4b6a1a8dcd6`).

**Deployed behavior [B].** The helper writes the clamped value back to a program-owned
account at `0x14507`/`0x1450e` (`stxdw [r2+0x48], r1`), i.e. the persistence is an account
write-back, not a CPI. The execute body has no invoke into the Mayhem program [B]. The
account identity/seeds, the instruction argument layout, and the exact derived-quote
arithmetic are not proven by the current trace.

**Reconstruction behavior [R].** No base source counterpart. `clone/set_mayhem_virtual_params.rs`
models a dedicated `["mayhem-config"]` account with an 8x u64 + bool argument struct and a
product/divide/clamp formula; the comments explicitly flag the account identity and math as
inferred.

**Divergence.** The persistence mechanism matches, but the account that is written, the
argument decoding, and the derived value are guesses. A built program may write the wrong
account (or fail the seed constraint) and produce different state/events. **MEDIUM-HIGH**
(state/config), not yet a proven value divergence.

**Status / next test.** PARTIAL. Trace `0x26ff8`/`0x1447e` to pin the account owner, seeds,
args, and the two clamp ceilings; then compare account bytes and event data with the
deployed handler.

---

## F5 - `multi_hop_curve_swap`: depth cap added in the wrong frame

**Program / handler.** pump; wrapper `0x252b8`, execute `0xacfb`.

**Deployed behavior [B].** Execute enforces only: `len >= 5`, `len % 5 == 0`,
`hop_fees.len == count`, `flags < 4`, and the source/destination Tokenkeg fence. It has
**no** comparison of `count` against `Global.max_curve_depth`. `CurveDepthExceeded` (6105,
string `0x1b8b51`) and `SetMaxCurveDepth` exist; the cap is enforced in `nested_create` at
`0xc150` (ceiling `min([Global+0x430], 5)`, error store at `0xc1c6`) and/or by the outer
router.

**Reconstruction behavior [R].** Base `multi_hop_curve.rs` has no depth check. The
recovered-fixes overlay adds:
`require_gte!(a.global.max_curve_depth.min(5) as usize, count, PumpError::CurveDepthExceeded);`
inside `execute`, with a comment that the ceiling is "reproduced here" from the nested-create
check.

**Divergence.** The deployed curve executor has no cap, so if no wrapper/outer-router cap
applies to a direct call, a call with `count > max_curve_depth.min(5)` is accepted by the
deployed handler but rejected by the reconstructed handler. For the normal pump_amm router
path the outer router may enforce the same cap, so the end-to-end behavior may match, but
the handler-level behavior does not and the placement is an inference. **MEDIUM** (route
availability; no funds loss).

**Status / next test.** PARTIAL (suspect over-fix). Run a direct-call differential with
`count = max+1`; if the deployed handler accepts it, remove the check from the curve
executor and enforce it only in the outer router. The adapter-delta part of the same fix
(`TradeEvent +0x198` at `0x1184d`, before/after measured; helper `0x12a1c`) is more faithful
than the old zero, but it models the delta as the mint's transfer fee rather than a live
before/after measurement; treat that as [partial] for hooks/other lossy adapters.

---

## F6 - `migrate`: AMM-create account list passes the same token program twice

**Program / handler.** pump; wrapper `0x256fb`, execute `0x7f6e`; AMM create CPI disc
`e992d18ecf6840bc` (bytes `233,146,209,142,207,104,64,188`).

**Deployed behavior [B].** The AMM-create account list passes distinct token programs (the
base-side and quote-side programs). The handler is native-SOL quote only, but the base mint
may be SPL Token or Token-2022 and the LP leg uses Token-2022.

**Reconstruction behavior [R].** `programs/pump/src/migrate.rs` builds the same AMM-create
account list with `(&tok,false,false),(&tok,false,false)` - the same `token_program` account
in both slots, even though the `Migrate` context also carries `token_2022_program`.

**Divergence.** The reconstructed CPI gives the AMM the wrong token-program account for one
side; a migration with a Token-2022 base mint can fail account validation (or use the wrong
program) where the deployed handler succeeds. **MEDIUM-HIGH** (migration path), not observed
in the verified pump_amm harness because that harness exercises AMM instructions directly,
not pump `migrate`.

**Status / next test.** OPEN. Run a native migration differential with a Token-2022 base
mint and inspect the inner AMM-create account list; replace the second `tok` with the correct
base/quote token program.

---

## F7 - Token-2022 net accounting: base source gap, overlay fix needs harness confirmation

**Program / handlers.** pump; `buy_v2` `0x24ea2`/body `0x27737`, `sell_v3` `0x25231`/body
`0x29515`, `buy_v3` `0x250d9`/body `0x28f74`, `buy_exact_quote_in_v3` `0x25185`/body
`0x2913f`; helper `0x12a1c` (calls `0x129c5`; the spec/07 calls the same helper a
checked-sub, while the overlay calls it `amount_after_fee` - the exact identity is [partial]).

**Deployed behavior [B].** The transfer-fee helper is called at `0x27ced` (buy_v2),
`0x29601` and `0x296f4` (sell_v3), `0x291f8` (buy_exact_quote_in_v3), `0xb70e` (multi-hop
per-hop), and from helper `0x10780` which buy_v3 calls. A fee-bearing Token-2022 quote is
therefore handled in net terms somewhere on these paths; the base source's plain
`transfer_checked` with gross `quote`/`user_output` is a confirmed gap (MASTER_GAPS B1).

**Reconstruction behavior [R].** Base source has no `util/transfer_fee.rs`; buy/sell
slippage and curve credit use gross amounts. The overlay adds `clone/transfer_fee.rs`
(epoch-selected bps/max fee, ceil fee, net, pre-fee inverse) and wires net credit into
`buy_v2.rs` and `trade.rs` (`buy`, `buy_exact_quote`, sell min-output).

**Divergence / status.** The base source diverges for fee-bearing quotes; the overlay is the
right direction. Still to confirm by execution: whether the binary credits the curve
reserves with net (as the overlay does) or only nets the event/user payout; the helper's
call sites are present, but the reserve-vs-event dataflow was not fully traced here. Mark
FIXED-VERIFY, not NO-DIVERGENCE. **HIGH** economics if the overlay over- or under-credits.

**Next test.** Build a Token-2022 quote mint with a non-zero TransferFeeConfig; run buy_v2,
sell_v3, buy_v3, buy_exact_quote_in_v3 against both binaries; compare curve reserves, user
balances, fee-recipient balances, and event quote fields.

---

## F8 - v3 quote route: USDC hardcode and the index-7 ATA binding (base source wrong)

**Program / handlers.** pump; `sell_v3` `0x25231`, `buy_v3` `0x250d9`,
`buy_exact_quote_in_v3` `0x25185`; account parser / `check_quote` `0x204af`.

**Deployed behavior [B].** `check_quote` at `0x204af` compares the quote mint against the
WSOL native-mint constant at `0x20891` (rodata `0x1b5cc8`); it does **not** hardcode USDC in
the v3 core. For a non-native quote it validates the quote mint account owner/mint and the
associated quote accounts, including the canonical ATA address for
`associated_quote_bonding_curve` (account index 7) and the buyback account, using
`ConstraintSeeds` (2006) for the derived ATA. The USDC constant is not part of the v3 core
(`0x204af`, `0x28f74`, `0x2913f`) [B].

**Reconstruction behavior [R].** Base `programs/pump/src/trade.rs:296` defines the USDC
constant and `:301` requires `quote_mint == USDC && bonding_curve.quote_mint == USDC`,
rejecting every other non-native quote with `ReconstructionBranchUnsupported`. The
`associated_quote_bonding_curve` is an `UncheckedAccount` (`:23`); the base `check_quote`
only derives the ATA for the hardcoded USDC (`:304-309`). For a whitelisted non-USDC quote
there is no general index-7 seed/address check.

**Divergence.** The base source rejects valid whitelisted quote curves and, if the USDC gate
were bypassed, would lack the general ATA binding for account index 7. The recovered-fixes
overlay removes the USDC constant, accepts the curve's `quote_mint`, and adds the derived
`require_keys_eq!(info.key(), expected_ata, ConstraintSeeds)` for roles 0 (bonding-curve ATA)
and 2 (buyback ATA). **HIGH** (functionality + account binding), but already fixed in the
overlay; verify with the fuzzer.

**Status / next test.** FIXED-VERIFY. Claude's fuzzer found the index-7 substitution path in
the base build; the overlay's derived ATA check is the fix to verify. Re-run the fuzzer on
sell_v3/buy_v3 with a whitelisted non-USDC quote; confirm the index-7 ATA must be canonical
and that a substituted account is rejected with 2006. Confirm the account-index-7 mapping
against the `SellV3` struct order
(global=0, base_mint=1, quote_mint=2, base_token_program=3, quote_token_program=4,
bonding_curve=5, associated_base_bonding_curve=6, associated_quote_bonding_curve=7).

---

## F9 - cashback zero path: deployed logs, source returns silently

**Program / handlers.** pump; `claim_cashback` `0x25d99`, `claim_cashback_v2` `0x25e2a`.
Source: `programs/pump/src/cashback.rs`.

**Deployed behavior [B].** On `amount == 0` the deployed handler logs
`"No cashback to claim"` (observed at `0xe9b9` for v2; the v1 counterpart uses the same
msg). The state/return is otherwise a no-op.

**Reconstruction behavior [R].** `cashback.rs:33` and `:42` return `Ok(())` silently; no
`msg!`.

**Divergence.** Extra log line only; no state, CPI, or error difference. **LOW.**

**Status / next test.** Cosmetic; add the `msg!` if log-level parity is required. No harness
priority.

---

## Resolved / verified by the recovered-fixes overlay (do not re-file as new)

### R1. Token-2022 net accounting (F7) - overlay fix direction is right
The base source's missing `util/transfer_fee.rs` is real. The overlay adds the standard
Token-2022 epoch-fee math and wires it into buy_v2/sell_v3/buy_v3/buy_exact_quote_in_v3.
The binary's helper `0x12a1c` is called from the corresponding bodies (see F7). Remaining
work is execution-level confirmation of reserve-vs-event scope, not a code gap in the
overlay's direction.

### R2. v3 quote route / SellV3 index-7 seeds (F8) - overlay fix
The base source's USDC-only `check_quote` and incomplete index-7 binding are fixed in the
overlay by deriving the ATA from `bonding_curve.quote_mint` and adding the ConstraintSeeds
check. The binary evidence is `check_quote @0x204af` + WSOL constant `0x20891`/rodata
`0x1b5cc8`; no USDC gate in the v3 core. Verify by fuzzing.

### R3. Token incentives handlers - reconstructed, no divergence found
`admin_update_token_incentives @0x25c54` and `claim_token_incentives @0x25d0e` were
unrecovered in the base tree; the overlay adds `clone/admin_update_token_incentives.rs`,
`clone/claim_token_incentives.rs`, and `clone/token_incentives_mod.rs`. Their account order,
the eight schedule guards, the `GlobalVolumeAccumulator` offsets (start +0x00, end +0x08,
seconds_in_a_day +0x10, mint +0x18, total_token_supply +0x38, sol_volumes +0x128), the
`InvalidIncentiveMint` has_one, the zero-claim early return, and the PDA-signed
`transfer_checked` match `spec/10-incentives.md` [B/R]. No divergence found; not yet
harness-verified, so treat as a coverage gap rather than a finding.

---

## Do not re-flag (verified non-divergences)

1. **PumpError enum revision (6010 vs 6022).** The recovered `lib.rs` enum order already
   matches the deployed binary's `PumpError::name()` table at pc `0x2bd95`: 6004
   MintDoesNotMatchBondingCurve, 6005 BondingCurveComplete, 6010 AccountTypeNotSupported,
   6022 SellZeroAmount (`pump_error_map.md`, name pointers `0x1b820b/28`, `0x1b8227/20`,
   `0x1b8298/23`, `0x1b83f7/14`). The earlier spec/06 and `error_catalogs.md` attribution
   was the error; they are corrected. **Do not reorder the source enum.**
2. **BondingCurve discriminator.** The reconstruction's
   `[23,183,248,55,96,216,172,96]` is a DECIMAL byte array = hex `17 b7 f8 37 60 d8 ac 60`,
   the correct deployed discriminator (rodata `0x1b64ef`). The `23b7...` reading was a
   hex/decimal mix-up. **Do not change it.**
3. **sell_v2 slippage/event gross-vs-net.** The deployed sell_v2 and the source both compute
   the minimum-output check and event quote on the gross quote (no Token-2022 fee netting).
   The user can receive less than the minimum while the tx succeeds; this is real program
   behavior present identically in both, not a reconstruction gap. Do not "fix" it without a
   binary proof.
4. **v3 USDC constant presence.** The USDC constant exists in the binary but not in the v3
   core; the base source's hardcode was wrong (F8), but the binary does not have a hidden
   USDC gate to reproduce.

---

## Per-program coverage

| program | verified paths | findings in this audit | coverage caveats |
|---|---|---|---|
| pump | core init/create/buy/sell flow (Claude harness); all 53/54 handlers mapped | F1-F9 | admin/creator, migration, multi-hop, and Token-2022 paths not all harness-verified |
| pump_amm | create_pool/deposit/buy/sell/withdraw byte-identical (VERIFICATION update 5) | none found | multi_hop_swap, creator_reassignment, cashback, boost, incentives not audited here |
| pump_fees | get_fees + get_fees_with_quote_mint byte-identical; fee_config stored-bump constraint verified | none found | admin/update/shares/sweep handlers not audited here |
| mayhem | handler map/specs complete (25/25) | F3 | reconstruction is ~86% of deployed; missing initialize_mayhem_state and ~41 functions; not e2e-verifiable |

## Suggested order for Claude

1. F1 admin_cto differential cases (guard set/order; mayhem/cashback/unswept/writable).
2. F2 create_v2 Mayhem: fix the 8-byte disc-only CPI, account order, second mint; log the
   inner instruction.
3. F3 rebuild mayhem with `initialize_mayhem_state`; then re-run F2 end-to-end.
4. F4 pin `set_mayhem_virtual_params` account/args from `0x26ff8`/`0x1447e`; compare state.
5. F5 direct `multi_hop_curve_swap` count>max test; move the cap if the deployed handler
   accepts it.
6. F6 native migration with a Token-2022 base mint; correct the AMM-create token programs.
7. F7 fee-bearing Token-2022 quote harness; confirm net reserve/slippage/event behavior.
8. F8 re-run the v3 fuzzer; confirm the index-7 ATA binding.
9. F9 cashback log (optional).

No byte-structure proposals were added; this file is behavior/reconstruction fidelity only.
