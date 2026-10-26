# Pump.fun — FEES / SWEEP handler cluster (binary-verified spec)

Binary: `D:/dev/ext/pumpfun-source/evidence/original/pump/deployed.so`
Tool: `py -3.12 D:/dev/pumpfun-re/sbftool.py {func|dis|callers} <bin> <ADDR>`
Recovered source: `programs/pump/src/{sweep.rs, distribution.rs, minimum.rs, lib.rs}`

All addresses below are **sbftool instruction indices** (the values printed in the
`func`/`dis` output), not byte offsets.

## Cluster entry-point map (all 5 confirmed against the binary)

Each handler begins with the Anchor `sol_log("Instruction: <Name>")` preamble.
The rodata string + length were extracted directly from the ELF (`PT_LOAD` VA→offset
map) and match the handler names **exactly** — this is the primary identity proof:

| Handler (name@addr) | log VA | len | decoded string (from .so) |
|---|---|---|---|
| sweep_protocol_fee @0x25376 | 0x1b7e34 | 0x1d | `Instruction: SweepProtocolFee` |
| sweep_creator_fee @0x25409 | 0x1b7e51 | 0x1c | `Instruction: SweepCreatorFee` |
| get_minimum_distributable_fee @0x261a8 | 0x1b80a1 | 0x27 | `Instruction: GetMinimumDistributableFee` |
| distribute_creator_fees @0x26225 | 0x1b80c8 | 0x22 | `Instruction: DistributeCreatorFees` |
| distribute_creator_fees_v2 @0x262dd | 0x1b80ea | 0x24 | `Instruction: DistributeCreatorFeesV2` |

Call-graph recovered from the binary:

| Handler entry (wrapper) | try_accounts | execute | shared shareholder loop |
|---|---|---|---|
| 0x25376 sweep_protocol | 0x1ddbe | 0xe502 `(r3=0)` | — |
| 0x25409 sweep_creator | 0x1ddbe | 0xe502 `(r3=1)` | — |
| 0x261a8 minimum | 0x18736 | 0x64a6 | 0x623f |
| 0x26225 distribute | 0x183ab | 0x6508 | 0x623f family (0x5c3f/0x65af) |
| 0x262dd distribute_v2 | 0x17f00 | 0x17f00/execute_v2 `(r6=initialize_ata)` | 0x623f family |

Common helpers: `0x366cf` = `memcmp(a,b,len)` (32‑byte `Pubkey` equality);
`0x366c2` = `memcpy`; `0x33e64` = bounds/panic helper; `0x3453e`/`0x3415d` = lamports/
balance reads; `0x3409f`/`0x359c3` = `emit!`/`sol_log_data`; `0x35633`/`0x35649`/`0x35636`
= slice-index/panic trampolines. No fee/sweep handler contains a direct `call -0x1`
(syscall) in its *execute* body — all CPIs (`system_program::transfer`,
`associated_token::create[_idempotent]`, `token_interface::transfer_checked`) and
sysvar reads (`Rent::get`) route through Anchor/anchor_spl helper wrappers.

---

## 1. sweep_protocol_fee @0x25376  /  sweep_creator_fee @0x25409

### Purpose
Two thin Anchor dispatch wrappers over one shared body. Both sweep the fees that have
accrued on a `bonding_curve` account to a `recipient`: protocol fees (`pf`) for
`sweep_protocol_fee`, creator fees (`cf`) for `sweep_creator_fee`. Confirms
`lib.rs:93-94` — `sweep_creator_fee → execute(ctx,true)`, `sweep_protocol_fee →
execute(ctx,false)`.

### Routing — VERIFIED
Both wrappers are byte-identical except the log string and the `creator` immediate.
Each does: `sol_log` → `call 0x1ddbe` (SweepFees::try_accounts) → `call 0xe502`
(`sweep::execute`) → Rc-refcount drop glue → `exit`. The `creator` bool is passed to
`0xe502` in **r3**:

```
; sweep_protocol wrapper 0x25376
  253ae: mov64 r3, 0x0      ; creator = false
  253af: call -0x16eae -> 0xe502
; sweep_creator wrapper 0x25409
  25441: mov64 r3, 0x1      ; creator = true
  25442: call -0x16f41 -> 0xe502
```
Error path from `0xe502` goes to `0xb45` (Anchor error logger) with the SweepFees name
string (`lddw r3,0x1b79df`).

### Accounts validated (try_accounts 0x1ddbe, 1094 insns)
Matches `sweep.rs` `SweepFees<'info>` (`#[event_cpi]`, 11 declared + event authority +
program). try_accounts contains **8** `Pubkey` memcmps (`0x366cf`), consistent with the
seed/constraint checks:
- `payer: Signer (mut)`.
- `global: seeds=[b"global"]`.
- `base_mint`, `quote_mint` : `InterfaceAccount<Mint>`.
- `quote_token_program`, `associated_token_program`, `system_program`.
- `bonding_curve (mut)`: `seeds=[b"bonding-curve", base_mint]`, with the constraint
  `(bonding_curve.field_key(83)==default ? native_mint : field_key(83)) == quote_mint`
  (`PumpError::MintDoesNotMatchBondingCurve`). i.e. a zero quote-mint field at byte 83
  means native SOL (WSOL mint).
- `associated_quote_bonding_curve (mut)`: ATA PDA of `(bonding_curve, quote_token_program,
  quote_mint)` under the ATA program.
- `recipient (mut, UncheckedAccount)` — address NOT constrained in try_accounts; validated
  in execute.
- `associated_quote_recipient (mut)`: ATA PDA of `(recipient, quote_token_program,
  quote_mint)`.

Note the custom `SweepCurve` deserializer (`sweep.rs`): discriminator
`[23,183,248,55,96,216,172,96]`, min len 49, zero-fills legacy gaps and resizes to 166.

### execute 0xe502 (241 insns) — error/CPI ORDER (VERIFIED structure, field offsets per source)
`r8 = creator` (saved from r3). Reconstructed order (matches `sweep.rs::execute`):
1. `native = field_key(83)==Pubkey::default()`.
2. `cf = number(125)`, `pf = number(133)`.
3. `reserve = native ? cf+pf (checked, Overflow) : 0`; `available = curve.lamports −
   reserve`; `rent = Rent::minimum_balance(max(data_len,166))`; `deficit = rent −
   available` (saturating).
4. **Rent top-up CPI**: if `deficit>0` → `system_program::transfer(payer→curve, deficit)`.
5. **realloc** curve to 166 if `data_len < 166`.
6. **Recipient validation (branch on `creator`)** — 3 key memcmps (`0x366cf`) in execute:
   - `creator==true`: `expected = find_program_address([b"creator-vault",
     field_key(49)], programID)`; `require_keys_eq!(recipient, expected)`
     (`ConstraintSeeds`).
   - `creator==false`: if `data[81]!=0` → `recipient ∈ {reserved_fee_recipient} ∪
     reserved_fee_recipients`; else → `recipient == fee_recipient ||
     classic_search(fee_recipients)` (binary search). Fail → `PumpError::NotAuthorized`.
7. `amount = creator ? cf : pf`; **if amount==0 → early `Ok(())`** (no event).
8. **Payout branch**:
   - native: `curve.sub_lamports(amount)`; `recipient.add_lamports(amount)` (direct
     lamport moves, no CPI).
   - token: for `[assoc_quote_bonding_curve, assoc_quote_recipient]`: if the recipient ATA
     is system-owned, **`associated_token::create_idempotent` CPI**; then owner must be
     `spl_token`/`spl_token_2022` (else `AccountOwnedByWrongProgram` /
     `AccountNotInitialized`), and parsed `TokenAccount.mint == quote_mint`. Then one
     **`token_interface::transfer_checked` CPI** (signed by bonding-curve PDA seeds),
     `amount, quote_mint.decimals`.
9. **Clear accrued counter**: `data[offset..offset+8].fill(0)` where `offset = creator ?
   125 : 133`.
10. Emit `SweepBondingCurveFeeEvent{..., bucket: creator?1:0}` via `emit!` + `emit_cpi!`.

### Fee math
`amount` is the raw accrued counter (`cf` at 125 / `pf` at 133) — no bps/ratio math in
sweep. The native `reserve = cf+pf` ensures sweeping one bucket never pulls the other
bucket's lamports or rent. Clearing the 8-byte counter after payout prevents re-sweep.

### GAP vs recovered sweep.rs
No gap found. Routing (r3 bool), the dual native/token payout, the `data[81]` reserved-vs-
classic recipient gate, the creator-vault PDA check, the `amount==0` early return, and the
post-payout counter clear are all consistent with the binary (entry 0x25376/0x25409 →
try_accounts 0x1ddbe → execute 0xe502). Exact byte offsets (49/81/83/125/133/166) are
taken from `sweep.rs`; in the binary they are reached through field-accessor helpers
(`0x79aa`, `0x7baf`) over the `SweepCurve.data` pointer rather than literal `[reg+imm]`
immediates, so they were not independently re-derived from immediates.

---

## 2. get_minimum_distributable_fee @0x261a8

### Purpose
Read-only query. Returns `MinimumDistributableFeeEvent{minimum_required,
distributable_fees, can_distribute}` for a mint's creator vault + sharing config.

### Call chain — VERIFIED
`0x261a8` (wrapper) → `0x18736` try_accounts (139 insns) → `0x64a6` execute (92 insns) →
`0x623f` shared shareholder loop (243 insns). Event emitted via `0x3409f`; the
`MinimumDistributableFeeEvent` discriminator is stored at `0x64a6:64f5`
(`lddw r3,0x3431b6ebef84d8a8`).

### Accounts validated (try_accounts 0x18736) — matches minimum.rs
- `mint: InterfaceAccount<Mint>`.
- `bonding_curve: seeds=[b"bonding-curve", mint]`, deserialized as `DistributionCurve`
  (read-only view: `creator`@49..81, `quote_mint`@83..115; disc `[23,183,...,96]`).
- `sharing_config: seeds=[b"sharing-config", mint], seeds::program=FEES
  (pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ), has_one=mint` →
  `MintDoesNotMatchBondingCurve`.
- `creator_vault: UncheckedAccount, seeds=[b"creator-vault", sharing_config]` (lamports +
  seeds only).

### Error conditions + ORDER (execute 0x64a6 → 0x623f)
1. `require_keys_eq!(bonding_curve.creator, sharing_config.key())`
   (`BondingCurveAndSharingConfigCreatorMismatch`).
2. `require!(remaining_accounts.len() >= shareholders.len())` (`NotEnoughRemainingAccounts`).
3. Per-shareholder loop (`0x623f`, verified): `memcmp(recipient.key, share.address, 32)`
   via `0x366cf` → `ShareholdersAndRemainingAccountsMismatch`; `!recipient.executable` →
   `UnableToDistributeCreatorFeesToExecutableRecipient`; `share.share_bps>0` →
   `InvalidShareBps`. Shareholder stride `0x22` (34 B = Pubkey 32 + u16 bps) confirmed
   (`0x623f:6291 mul64 r6,0x22`, `62ae add64 r9,0x22`).
4. `required = max_i(threshold_i)`; `u64::try_from(...)` overflow → `PumpError::Overflow`.
5. Build event: `reserve = Rent::minimum_balance(0)` (via helper `0x3453e`),
   `distributable_fees = creator_vault.lamports − reserve`,
   `can_distribute = available >= required` (`0x64a6:64f9 jge r8,r2 → r9`),
   `minimum_required = reserve + required` (checked). No `require!` gate on the result —
   it is an informational query.

### CPIs
**None.** The handler is read-only. No `system_program`/token CPI, and — see gap — no
fee-program CPI.

### GAP vs recovered minimum.rs — get_return_data hypothesis: **REFUTED**
The task hint ("likely uses `get_return_data` from a fee-program CPI") does **not** hold
for the deployed binary. Verified evidence:
- No direct syscall (`call -0x1 -> self`) exists anywhere in the minimum call tree
  (`0x18736`, `0x64a6`, `0x623f`) except the one `sol_log` preamble in the wrapper
  (`0x261af`). A fee-program CPI would require `sol_invoke_signed` **plus**
  `sol_get_return_data` syscalls; neither is present, and there is no `invoke` through a
  helper either.
- `get_return_data` *is* used elsewhere — the TRADE handlers call the fee program and read
  its return data: `buy_v2.rs:79`, `sell_v2.rs:76`, `legacy_buy.rs:51`, `legacy_sell.rs:59`
  (`program::get_return_data().unwrap()` → `Fees::deserialize`). The hint appears to
  conflate that trade-path pattern with this query. `get_minimum_distributable_fee`
  instead computes the minimum **locally** from on-chain state (creator_vault lamports +
  `Rent` + the shareholders' per-account rent deficits), matching `minimum.rs`.

**Flagged (partial trace):** The shared shareholder loop `0x623f` contains
`div64 r7,0x2710` (÷10000). Recovered `minimum.rs` computes the per-share threshold as
`ceil(deficit*10000 / share_bps)` (divide by `share_bps`), identical to
`distribution.rs::native_eligible`, whereas the ÷10000 constant matches the
*distribute* per-share amount `available*share_bps/10000`. Because `0x623f` is shared by
three executes (`0x64a6` minimum, plus `0x5c3f`/`0x65af` in the distribute family) and the
multiply feeding the divide was not fully isolated, I could not byte-level confirm that
minimum's deployed `required` uses ÷`share_bps` rather than ÷10000. The local-computation
/ no-CPI conclusion is firm; the exact threshold divisor in the shared helper is the one
open item worth a deeper trace. All validation checks and their order ARE confirmed.

---

## 3. distribute_creator_fees @0x26225

### Purpose
Distributes the native lamports accrued in the creator vault to the sharing-config
shareholders pro-rata by `share_bps`. Native-only variant.

### Call chain — VERIFIED
`0x26225` wrapper → `sol_log` (0x2622c) → `0x183ab` try_accounts → `0x6508` execute. Returns
`DistributeCreatorFeesEvent`.

### Accounts validated (matches distribution.rs `DistributeCreatorFees`)
`mint`; `bonding_curve` seeds=[b"bonding-curve",mint] (`DistributionCurve`); `sharing_config`
seeds=[b"sharing-config",mint], seeds::program=FEES, has_one=mint; `creator_vault (mut)`
seeds=[b"creator-vault",sharing_config]; `system_program`; `event_authority`
seeds=[b"__event_authority"]; `program`.

### Error conditions + ORDER (per distribution.rs::execute, loop verified via 0x623f family)
1. `require_keys_eq!(bonding_curve.creator, sharing_config.key())`
   (`BondingCurveAndSharingConfigCreatorMismatch`).
2. `require!(sharing_config.status == Active)` (`SharingConfigNotActive`) — enum
   `ConfigStatus{Paused=0,Active=1}`.
3. `require!(remaining_accounts.len() >= shareholders.len())`
   (`NotEnoughRemainingAccounts`).
4. `available = creator_vault.lamports − Rent::minimum_balance(0)`.
5. `eligible = native_eligible(shareholders, remaining_accounts, available)` — pre-checks
   every shareholder (address memcmp, `!executable`, `share_bps>0`) and computes
   `minimum = max ceil(deficit*10000/share_bps)`, returning `available >= minimum`.
6. Payout loop: per shareholder re-checks address/executable/share_bps, computes
   `amount = (available as u128 * share_bps / 10000) as u64`; **if `eligible && amount>0`**
   → `system_program::transfer(creator_vault → recipient, amount)` signed by
   `[b"creator-vault", bonding_curve.creator, bump]`; `distributed += amount` (checked).
7. If `eligible`: `emit!` + `emit_cpi!` the event (quote_mint = default/native).

### Fee math
Per-share `available * share_bps / 10000` (÷10000 = `0x2710` confirmed in the shared loop
`0x623f`). `native_eligible` gate ensures the vault can satisfy every recipient's rent
deficit before any transfer, preventing partial distributions that strand dust.

### GAP vs recovered distribution.rs
No gap found. Structure (try_accounts 0x183ab → execute 0x6508), the `Active` status gate,
the `native_eligible` precondition, the pro-rata ÷10000 math, and the PDA-signed transfer
are consistent. CPIs are the single `system_program::transfer` per eligible shareholder
(via helper, no direct syscall in execute).

---

## 4. distribute_creator_fees_v2 @0x262dd

### Purpose
Generalized distribution supporting BOTH native (SOL) and SPL/Token-2022 quote mints, with
optional recipient-ATA creation. Takes an extra ix arg `initialize_ata: bool`.

### Call chain — VERIFIED
`0x262dd` wrapper (7-insn preamble — one more than the others — saving the extra 5th arg:
`262dd mov64 r6,r5`, so `initialize_ata` arrives in **r6**) → `sol_log` (0x262e5) →
try_accounts/execute via `0x17f00` (`call -0xe42b -> 0x17f00` at 0x2632a). The wrapper also
shows `callx r2` (0x26311) — a dynamic dispatch within the Anchor arg/deserialize glue.

### Accounts validated (matches distribution.rs `DistributeCreatorFeesV2`)
Adds vs v1: `payer: Signer(mut)`; `creator_vault_quote_token_account (mut)` =
ATA PDA of `(creator_vault, quote_token_program, quote_mint)`; `quote_mint:
InterfaceAccount<Mint>`; `quote_token_program`; `associated_token_program`.

### Error conditions + ORDER (per distribution.rs::execute_v2)
1. `require_keys_eq!(bonding_curve.creator, sharing_config.key())`.
2. `require!(sharing_config.status == Active)`.
3. `native = bonding_curve.quote_mint == default || == native_mint`.
4. `require_keys_eq!(quote_mint, native ? native_mint : bonding_curve.quote_mint)`
   (`MintDoesNotMatchBondingCurve`).
5. `available = native ? (creator_vault.lamports − Rent::minimum_balance(0))
   : TokenAccount(creator_vault_quote_token_account).amount`.
6. `require!(remaining_accounts.len() >= count * (native?1:2))`
   (`NotEnoughRemainingAccounts`) — token mode needs a second array of recipient ATAs.
7. `eligible = native ? native_eligible(...) : true`.
8. Per shareholder: address/executable/share_bps checks; `amount = available*share_bps/
   10000`.
   - native: `if eligible && amount>0` → `system_program::transfer` (PDA-signed).
   - token: `ata = remaining[count+i]`; require `ata == get_associated_token_address(
     recipient, quote_mint, token_program)` (`ShareholdersAndRemainingAccountsMismatch`);
     if `ata.data_is_empty()` require `initialize_ata` (else
     `UnableToDistributeCreatorFeesToUninitializedAccount`) then
     `associated_token::create` CPI; `if amount>0` → `token_interface::transfer_checked`
     CPI (PDA-signed, `decimals`).
   - `if eligible: distributed += amount` (checked).
9. If `eligible`: emit event (quote_mint = native?default:quote_mint).

### Fee math / CPIs
Same ÷10000 pro-rata. CPIs: native path = `system_program::transfer` per shareholder;
token path = optional `associated_token::create` + `token_interface::transfer_checked` per
shareholder (all via helpers; no direct syscall in execute body).

### GAP vs recovered distribution.rs
No gap found. The `initialize_ata` arg (r6 in the 7-insn preamble, vs the 6-insn preambles
of the other four handlers) and the dual native/token branch match the source. The token
branch's `get_associated_token_address_with_program_id` equality check and the
`initialize_ata`-gated ATA creation are consistent with `execute_v2`. The native/token
`available` source split (lamports vs parsed `TokenAccount.amount`) is the key v2 addition
over v1.

---

## Cross-handler notes
- `creator_vault` and `bonding_curve` reserve lamports: all four non-query handlers subtract
  rent before computing the distributable/sweepable amount, so an account is never drained
  below its rent-exempt minimum (sweep additionally tops the curve up to 166-byte rent via
  a payer-funded transfer before payout).
- Recipient-set authorization differs by path: sweep-protocol uses the `global`
  fee-recipient lists (binary-searched `classic_search`, or the `reserved_*` set when
  `data[81]!=0`); sweep-creator and both distributes bind payout to the `creator-vault` PDA
  derived from the bonding-curve creator / sharing-config, so a caller cannot redirect
  funds to an arbitrary recipient.
- `emit_cpi!` (self-CPI event) is present on sweep and both distributes (the `#[event_cpi]`
  / explicit `event_authority`+`program` accounts), giving indexers a CPI-log trail in
  addition to the program-data `emit!`.
