# Pump.fun — Config Handler Cluster (verified against deployed.so)

Binary: `D:/dev/ext/pumpfun-source/evidence/original/pump/deployed.so`
Recovered source: `D:/dev/ext/pumpfun-source/programs/pump/src/` (handlers in `lib.rs`, `set_params.rs`)
Tool: `sbftool.py` (sBPF v1 static disassembler / abstract interpreter)

## Architecture note (applies to all 5 handlers)

Every instruction entry is a thin **Anchor `__global` trampoline** reached only
from the central dispatcher at `0x238a7` (confirmed: `callers deployed.so 0x2494e`
→ single caller `0x238a7`). Each trampoline:

1. `sol_log("Instruction: <Name>")` via `call -0x1` (the first `lddw r1,<ptr>; mov r2,<len>; call -0x1` — the string at `<ptr>` is how each address was confirmed to its handler, see below).
2. Borsh-deserializes the instruction **data** (`data_ptr = [frame-0x1000]`, `data_len = [frame-0xff8]`); the `jlt/jeq rX,0x8`/`...,0x20` branches at the top of each trampoline are **borsh length checks on the arg buffer**, NOT business `require!`s.
3. `try_accounts` for the Accounts struct (shared helper `0x2cca9`).
4. `call <execute>` — the real business logic (requires, math, Global field writes) lives in a **separate `execute` function**, not inlined in the trampoline.
5. Builds/serializes the event and `emit!` / `emit_cpi!` (self-CPI) on the way out.

Because `Account<'info, Global>` is a (non-zero-copy) borsh account, `execute`
mutates the **in-memory deserialized struct** and Anchor reserializes it on exit.
The field-store offsets observed in the binary are therefore the **Rust in-memory
layout** of `Global` (fields grouped by alignment: the `u64` run, the `Pubkey`
run, the `bool` run — NOT borsh declaration order, and NOT small sequential
offsets).

Address → handler identity, **confirmed** by the logged name string:

| Addr (trampoline) | Instruction string @ rodata | Handler |
|---|---|---|
| `0x244a2` | `Instruction: UpdateHolderRewardConfig` (@0x1b7c2f) | `update_holder_reward_config` |
| `0x246a6` | `Instruction: UpdateCreatorFeeConfig…` (@0x1b7c8e) | `update_creator_fee_config` |
| `0x2494e` | `Instruction: SetParams` (@0x1b7d0a) | `set_params` → execute `0x26cf8` |
| `0x248d8` | `Instruction: SetVirtualQuoteReserves` (@0x1b7ce6) | `set_virtual_quote_reserves` |
| `0x24b5d` | `Instruction: SetReservedFeeRecipients…` (@0x1b7d43) | `set_reserved_fee_recipients` |

---

## set_params @ trampoline 0x2494e, execute 0x26cf8 (672 insns)

**1. Purpose.** Admin-only (re)configuration of the global bonding-curve launch
parameters, migration settings, creator-fee cap, creator authorities, and the
8 protocol fee-recipient accounts.

**2. Accounts validated.** `SetParams` (set_params.rs): `global` (`mut`, PDA
`seeds=[b"global"]`, `has_one=authority @ NotAuthorized`), `authority` (`mut`
Signer). `#[event_cpi]` adds `event_authority` + `program`. Plus **8 fee-recipient
accounts passed as `remaining_accounts`** (validated in `0x7caa`, below).
- Binary: trampoline parses accounts via `0x2cca9`; `execute` receives the global
  data pointer in `r9` (`r9 = [[frame-0x5e0]+0x8]`, 26d30).

**3. Error / require! conditions — cross-checked against binary branches:**

| .rs require! | Binary evidence |
|---|---|
| `remaining_accounts.len() >= 8` → `NotEnoughRemainingAccounts` | `0x7caa` head `7cad: jlt r7,0x8,+0xf2` |
| each of 8 recipients `!= Pubkey::default()` → `AllFeeRecipientsShouldBeNonZero` | `0x7caa` 8× `call 0x366cf` (32-byte memcmp vs zeros) at 7d27,7d35,7d42,7d4f,7d5c,7d69,7d76,7d83 |
| each recipient rent-exempt → `ConstraintRentExempt` | `0x7caa` `0x2ae70`/`0x2bbd1` (Rent::get / is_exempt) at 7d8b-7db6 |
| `recipients` strictly sorted unique `w[0]<w[1]` → `UnsortedNotUniqueFeeRecipients` | `0x7caa` pairwise `call 0x366cf` run at 7ec0,7eca,7ed3,7edc,7ee5,… (7 comparisons) |
| `initial_real_token_reserves < token_total_supply` → `InitialRealTokenReservesShouldBeLessThanTokenTotalSupply` | execute, compare + err path (panic line `0x177c`, string `0x1b5f18`) 26d38-area / 26d4e |
| `initial_virtual_token_reserves > initial_real_token_reserves` → `InitialVirtualTokenReservesShouldBeGreaterThanInitialRealTokenReserves` | execute `26d2b: jgt r9,r7,+1; 26d2c: ja +0xf1` (err) ; string `0x1b5dec`, line `0x177c` |
| `fee_basis_points <= 1000` → `FeeBasisPointsGreaterThanMaximum` | `26d38: jgt r8,0x3e8,+1; 26d39: ja +0x58` (err) |
| `withdraw_authority != Pubkey::default()` → `AllZerosWithdrawAuthority` | `26d94: mov r1,r8; mov r2,0x1b5ba8(zeros),r3=0x20; call 0x366cf; 26d9b: jeq r0,0x0,+0x69` (err) |
| u128 `final_real_sol_reserves = ivtr*ivsr/(ivtr-irtr) - ivsr`; `u64::try_from` → `Truncation` | execute 26da6-26db5 u128 intrinsics `0x36ab9`,`0x36811` producing 128-bit (r2:r3); `0x177d`/`0x177d` panic lines |
| `pool_migration_fee < final_real_sol_reserves` → `PoolMigrationFeeShouldBeLessThanFinalRealSolReserves` | `26dbb: jle r3,r9,+0xdf` (err when final ≤ pool_migration_fee) |
| `creator_fee_basis_points <= 1000` → `FeeBasisPointsGreaterThanMaximum` | `26dbf: jgt r9,0x3e8,+1; 26dc0: ja +0xfc` (err) |

All 7 scalar require!s + the two recipient-loop invariants are present and in the
**same order** as set_params.rs. No missing or extra check found.

**4. CPIs.** No external program CPI. `emit_cpi!(SetParamsEvent)` performs a
**self-CPI** to the program's own `event_authority` (Anchor event-CPI). Event
built/emitted in the trampoline after execute returns (`call 0x26cf8` @24a5d,
then event serialize `0x34f1c` + log helpers `0xdcf`/`0x526`). `emit!` also logs.

**5. Global fields written — offsets confirmed in execute@0x26cf8 (Rust in-memory layout, base = global data ptr `r9`):**

| .rs field (assignment order) | type | observed store | in-mem offset |
|---|---|---|---|
| `initial_virtual_token_reserves` | u64 | `26d32 stxdw [r9+0x450],r6` | **+0x450** |
| `initial_virtual_sol_reserves` | u64 | `26d31 stxdw [r9+0x460],r7` | **+0x460** |
| `initial_real_token_reserves` | u64 | `26d36 stxdw [r9+0x458],[−0x5d0]` | **+0x458** |
| `token_total_supply` | u64 | `26d34 stxdw [r9+0x468],[−0x5c8]` | **+0x468** |
| `fee_basis_points` | u64 | `26d92 stxdw [r9+0x470],r8` (post `≤1000`) | **+0x470** |
| `withdraw_authority` | Pubkey | `26d9d-26da3 stxdw [r9+0x1b0/+0x1b8/+0x1c0/+0x1c8]` | **+0x1b0..0x1cf** |
| `enable_migrate` | bool | `26da5 stxb [r9+0x4a2],[−0x5f0]` | **+0x4a2** |
| `pool_migration_fee` | u64 | `26dbc stxdw [r1+0x478],[−0x5f8]` (post `pool<final`) | **+0x478** |
| `creator_fee_basis_points` | u64 | `26ebe stxdw [r2+0x480],r9` (post `≤1000`) | **+0x480** |
| `set_creator_authority` | Pubkey | `26ec0-26ec7 stxdw [r2+0x2b0..+0x2c8]` | **+0x2b0..0x2cf** |
| `admin_set_creator_authority` | Pubkey | `26ec9-26ed1 stxdw [r2+0x2d0..+0x2e8]` | **+0x2d0..0x2ef** |
| `fee_recipient = recipients[0]` | Pubkey | written from the `0x7caa` recipients array; see GAP | (not isolated) |
| `fee_recipients[7] = recipients[1..8]` | [Pubkey;7] | block-copied from the `0x7caa` recipients array; see GAP | (not isolated) |

The u64 fields occupy the contiguous aligned run `0x450..0x480` and the Pubkeys
live in the `0x1b0..0x4xx` pointer region — consistent with Rust alignment
grouping, confirming this is the in-memory (not borsh) layout.

**6. GAP vs recovered .rs.** The 11 scalar/pubkey writes, all 9 require!s, the
u128 `final_real_sol_reserves` computation and the recipients validation
subroutine (`0x7caa`) **match set_params.rs exactly** — handler address `0x2494e`,
execute `0x26cf8`, recipient subroutine `0x7caa`.
- **Residual (not a discrepancy, a verification gap):** the two `fee_recipient` /
  `fee_recipients[1..8]` stores into `Global` were not isolated to explicit
  offsets — they are block-copied from the array that `0x7caa` builds/returns
  (memcpy helpers `0x366c2`), rather than appearing as individual `stxdw [r9+off]`.
  The .rs `g.fee_recipient=recipients[0]; g.fee_recipients.copy_from_slice(&recipients[1..])`
  is consistent with this copy, but exact offsets were not pinned.

---

## set_reserved_fee_recipients @ trampoline 0x24b5d (lib.rs:132)

**1. Purpose.** Admin sets the `whitelist_pda` plus the reserved fee-recipient set
(`reserved_fee_recipient` + `reserved_fee_recipients[7]`) from 8 `remaining_accounts`.

**2. Accounts validated.** `AdminReadonly` (lib.rs:442): `global` (`mut`, PDA
`seeds=[b"global"]`, `has_one=authority @ NotAuthorized`), `authority` Signer
(**not `mut`**, unlike AdminGlobal). `#[event_cpi]` adds event_authority + program.
Plus **8 reserved-recipient accounts as `remaining_accounts`**.

**3. Error / require! conditions (per .rs; trampoline + execute).** Arg = single
`whitelist_pda: Pubkey`. Checks (lib.rs:133-135):
`remaining_accounts.len() >= 8` → `NotEnoughRemainingAccounts`; per account
`key() != default` → `AllFeeRecipientsShouldBeNonZero`; **`!account.executable`**
→ `ConstraintExecutable` (distinct from set_params, which does NOT check
executable); rent-exempt → `ConstraintRentExempt`. **No sort/unique check** (unlike
set_params). Binary: trampoline `0x24b5d` borsh-parses the 32-byte `whitelist_pda`
arg (`ldxb [r1+0x1f]` etc. at 24b7e) and the account set; the length/executable/
non-zero/rent loop runs in a separate execute (same trampoline→execute pattern as
set_params).

**4. CPIs.** `emit_cpi!(ReservedFeeRecipientsEvent{timestamp, reserved_fee_recipient, reserved_fee_recipients})` self-CPI + `emit!`.

**5. Global fields written (per .rs).** `whitelist_pda` (Pubkey),
`reserved_fee_recipient = remaining[0]` (Pubkey), `reserved_fee_recipients[7] = remaining[1..8]` ([Pubkey;7]).

**6. GAP.** Identity, account context (`AdminReadonly`, non-`mut` authority), arg
type (`whitelist_pda: Pubkey`) and the `!executable` vs no-sort distinction match
lib.rs. **Verification gap:** the `execute` body (and its exact `[global+off]`
store offsets for whitelist_pda / reserved_fee_recipient(s)) was not isolated to a
single function address in this pass — trampoline `0x24b5d` spans `0x24b5d-0x24bf8`
(next handler at `0x24c20`) and defers the loop+stores to a callee not pinned here.
No contradiction with .rs observed.

---

## set_virtual_quote_reserves @ trampoline 0x248d8 (lib.rs:139)

**1. Purpose.** Admin one-liner: set `global.initial_virtual_quote_reserves`.

**2. Accounts validated.** `AdminGlobal` (lib.rs:170): `global` (`mut`, PDA
`seeds=[b"global"]`, `has_one=authority @ NotAuthorized`), `authority` (`mut`
Signer). `#[event_cpi]` adds event_authority + program.
- Binary: `248e1-248e2 ldxdw r1,[r6-0xff8]; jlt r1,0x8,+0x54` = borsh check "arg
  data ≥ 8 bytes" for the single `u64`. Accounts parsed via shared `0x2cca9`.

**3. Error / require! conditions.** **None** beyond `has_one=authority`
(`NotAuthorized`) and the Anchor PDA/discriminator checks. The borsh `jlt …,0x8`
is the 8-byte u64-length check. Matches .rs (no `require!`).

**4. CPIs.** None. **No event** (`Ok(())` directly) — matches .rs (no `emit`).

**5. Global fields written.** `initial_virtual_quote_reserves` (u64) — single store.

**6. GAP.** Identity (string `SetVirtualQuoteReserves`), context (`AdminGlobal`),
single-u64 arg, and absence of event all match lib.rs:139. **Verification gap:**
the single `[global+off]` store for `initial_virtual_quote_reserves` resolves
through the shared account parse/serialize path (`0x2cca9`) and was not isolated to
an explicit offset (no `jgt`/math to anchor on, unlike set_params). No discrepancy.

---

## update_creator_fee_config @ trampoline 0x246a6 (lib.rs:141)

**1. Purpose.** Admin sets `creator_fee_configurable` (bool) and
`max_configurable_creator_fee_bps` (u64), then emits an event.

**2. Accounts validated.** `AdminGlobal`: `global` (`mut`, PDA, `has_one=authority
@ NotAuthorized`), `authority` (`mut` Signer), + event_cpi accounts.

**3. Error / require! conditions.** **None** beyond `has_one`/PDA/disc and the
borsh validity check on the `bool` arg (bool first byte must be 0/1). Matches .rs
(no `require!`). (Note the sibling `update_buyback_config` at lib.rs:140 *does*
`require!(value<=10000)` — update_creator_fee_config has no such bound; confirmed
no `0x2710`/`0x3e8` compare belongs to this handler.)

**4. CPIs.** `emit_cpi!(UpdateCreatorFeeConfigEvent{timestamp, authority,
creator_fee_configurable, max_configurable_creator_fee_bps})` self-CPI + `emit!`.

**5. Global fields written.** `creator_fee_configurable` (bool),
`max_configurable_creator_fee_bps` (u64) — two stores.

**6. GAP.** Identity (string `UpdateCreatorFeeConfig…`), context (`AdminGlobal`),
arg types (`bool`,`u64`), the event, and absence of a bps bound all match lib.rs:141.
**Verification gap:** the two `[global+off]` stores were not isolated to explicit
offsets (trampoline defers to the shared parse/serialize path). No discrepancy.

---

## update_holder_reward_config @ trampoline 0x244a2 (lib.rs:145)

**1. Purpose.** Admin sets `is_holder_reward_enabled` (bool) and
`holder_reward_claim_authority` (Pubkey).

**2. Accounts validated.** `AdminGlobal`: `global` (`mut`, PDA, `has_one=authority
@ NotAuthorized`), `authority` (`mut` Signer), + event_cpi accounts.
- Binary: `244ab ldxdw r2,[r7-0xff8]; jeq r2,0x0,…` (data-len) then `244af ldxb
  r6,[data+0]; 244b1 jlt r6,0x2,…` = **borsh bool validity check** (first byte of
  the `is_holder_reward_enabled` arg must be < 2). Confirms bool-then-Pubkey arg layout.

**3. Error / require! conditions.** **None** beyond `has_one`/PDA/disc and the borsh
bool check. Matches .rs (one-liner, no `require!`).

**4. CPIs.** None. **No event** (`Ok(())` directly) — matches .rs.

**5. Global fields written.** `is_holder_reward_enabled` (bool),
`holder_reward_claim_authority` (Pubkey) — two stores.

**6. GAP.** Identity (string `UpdateHolderRewardConfig`), context (`AdminGlobal`),
arg types/order (bool via `jlt …,0x2`, then Pubkey), and absence of event all match
lib.rs:145. **Verification gap:** the two `[global+off]` stores were not isolated to
explicit offsets. No discrepancy.

---

## Cross-cutting findings

- **Authority model:** `set_params`/`set_virtual_quote_reserves`/
  `update_creator_fee_config`/`update_holder_reward_config` use `AdminGlobal`
  (authority is `mut` Signer); `set_reserved_fee_recipients` uses `AdminReadonly`
  (authority is a plain Signer, not `mut`). All gate on `has_one=authority @
  NotAuthorized` against the `global` PDA. Confirmed in lib.rs; the PDA/has_one is
  enforced by Anchor-generated `try_accounts` (`0x2cca9` path), not by hand-written
  branches.
- **Only `set_params` and `set_reserved_fee_recipients` touch
  `remaining_accounts`** (8 fee-recipient accounts). `set_params` enforces
  non-zero + rent-exempt + **strict sort/unique** (subroutine `0x7caa`, fully
  confirmed). `set_reserved_fee_recipients` enforces non-zero + **`!executable`** +
  rent-exempt but **no sort** — a real behavioural asymmetry, matching the .rs.
- **No discrepancies** between the recovered `.rs` and the binary were found for
  any of the 5 handlers. The only open items are **verification gaps**, all of the
  same kind: for the four small handlers (and the `fee_recipient(s)` writes of
  set_params) the per-field `Global` store offsets flow through Anchor's shared
  account parse/serialize helpers and were not independently pinned to numeric
  offsets the way `set_params`' scalar/pubkey writes (execute `0x26cf8`) were.
