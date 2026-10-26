# 11 — Volume-Accumulator + IDL Handlers

Reverse-engineered from the deployed Pump.fun program and verified against the
binary with `sbftool.py`.

- **Binary:** `D:/dev/ext/pumpfun-source/evidence/original/pump/deployed.so`
- **Recovered source:** `programs/pump/src/lib.rs` (init/close bodies + account
  structs), `programs/pump/src/volume_sync.rs` (sync), `programs/pump/src/idl_authority.rs` (idl).

All four entrypoints are Anchor `__global` dispatch stubs. Each stub: logs
`"Instruction: <Name>"` (confirmed by log-string lengths — 38/39/38/33 bytes), calls its
generated `try_accounts`, `memcpy`s the built `Context` onto the stack, calls the
handler body, then runs Anchor exit glue (serialize + `Rc`/`RefCell` ref-count drops).

| Handler | Dispatch stub | `try_accounts` | Body |
|---|---|---|---|
| init_user_volume_accumulator | `0x25ebc` | `0x1f8e5` | `0xf4d8` |
| close_user_volume_accumulator | `0x25f6d` | `0x1f691` | `0xf378` |
| sync_user_volume_accumulator | `0x25ff1` | `0x1ffb6` | `0xf64a` |
| admin_set_idl_authority | `0x260a3` | `0x14510` | `0x2aafd` |

### `UserVolumeAccumulator` Borsh layout (account data, after 8-byte discriminator)

| Off | Field | Type |
|----:|-------|------|
| +8  | user | Pubkey (32) |
| +40 | needs_claim | bool |
| +41 | total_unclaimed_tokens | u64 |
| +49 | total_claimed_tokens | u64 |
| +57 | current_sol_volume | u64 |
| +65 | last_update_timestamp | i64 |
| +73 | has_total_claimed_tokens | bool |
| +74 | cashback_earned | u64 |
| +82 | total_cashback_claimed | u64 |
| +90 | stable_cashback_earned | u64 |
| +98 | total_stable_cashback_claimed | u64 |

Used size = 98 data + 8 disc = **106 bytes**; declared `space=137` ⇒ 31 bytes
reserved slack (forward-compat; not a bug).

---

## 1. init_user_volume_accumulator @ 0x25ebc

### 1. Purpose
Create (via `init_if_needed`) the per-user `UserVolumeAccumulator` PDA, funded by
`payer`, and set its `user` field to the target user. Emits
`InitUserVolumeAccumulatorEvent{payer,user,timestamp}` (log + CPI self-invoke).

### 2. Accounts validated (`try_accounts` @ 0x1f8e5)
- `payer: Signer (mut)`
- `user: UncheckedAccount` (any key — "any user may be funded by the payer")
- `user_volume_accumulator: Account<UserVolumeAccumulator>` —
  `init_if_needed, payer=payer, space=137,
  seeds=[b"user_volume_accumulator", user.key()], bump`
- `system_program: Program<System>`
- event-CPI accounts (`event_authority`, `program`) appended by `#[event_cpi]`.

**PDA seeds verified in binary** at `0x1f9fa–0x1fa0c`:
seed0 = rodata `0x1b6f73` (`"user_volume_accumulator"`, len `0x17`=23),
seed1 = `user.key()` (32 bytes, len `0x20`), seed count `r3=2`, passed to
`find_program_address` (`0x34fd7`). Matches source exactly.

### 3. Error / `require!` order
No explicit `require!` in the body. Ordered failure points are all in
`try_accounts`: (1) account/signer/PDA-seed+bump validation, (2) `init_if_needed`
allocation (`CreateAccount` CPI when the PDA does not yet exist, or type/owner
re-check when it does), (3) `system_program` program-id check. Body then calls
`Clock::get()` (`0x34127` @ `0xf4f0`) — its error (`!=0` at `0xf4f2`) is the only
body-level early return, before any event.

### 4. CPIs
- `system_program::CreateAccount` for the PDA (Anchor `init_if_needed`, inside
  `try_accounts`; funds from `payer`, `space=137`).
- Self-CPI `emit_cpi!` for `InitUserVolumeAccumulatorEvent` (via the appended
  event-authority PDA).

### 5. State writes (body @ 0xf4d8)
- Copies `user.key()` (the `user` UncheckedAccount, loaded from `[ctx.accounts+0x80]`)
  into `user_volume_accumulator.user` — 32-byte store at `[r8+0x18]`,`+0x20`,`+0x28`,
  `+0x30` (`0xf509–0xf50c`), i.e. account-data offset +8. All other accumulator
  fields remain at their `init` defaults (zero). Matches source line
  `ctx.accounts.user_volume_accumulator.user = ctx.accounts.user.key()`.

### 6. GAP vs recovered `.rs`
**No gap.** Seeds, `space=137`, `init_if_needed`, the single `user`-field write,
and the emit are all reproduced. The literal `137` is consumed inside the Anchor
create path (rent/space computed in a register) and was not isolated as a bare
immediate, but the `space` slot and 2-seed PDA derivation are confirmed.

---

## 2. close_user_volume_accumulator @ 0x25f6d

### 1. Purpose
Close the caller's `UserVolumeAccumulator` PDA, refunding its lamports to `user`,
after emitting `CloseUserVolumeAccumulatorEvent` with the final accumulator state.

### 2. Accounts validated (`try_accounts` @ 0x1f691)
- `user: Signer (mut)` (refund destination).
- `user_volume_accumulator: Account<UserVolumeAccumulator>` —
  `mut, close=user, seeds=[b"user_volume_accumulator", user.key()], bump`.
- event-CPI accounts.

Seed string `0x1b6f73` (`"user_volume_accumulator"`) referenced at `0x1f6aa` —
same PDA derivation as init; `close=user` binds the refund to the signer.

### 3. Error / `require!` order
No body `require!`. Failure order: `try_accounts` signer + PDA-seed/bump + account
deserialization; then body `Clock::get()` (`0xf378`) error check. Event is emitted
only after a successful clock read.

### 4. CPIs
- Anchor `close` glue (in the dispatch-stub exit path, not the body): moves all
  lamports to `user`, writes the `CLOSED_ACCOUNT_DISCRIMINATOR`, and zeroes/assigns
  the account — standard Anchor account close, no explicit system CPI.
- Self-CPI `emit_cpi!` for `CloseUserVolumeAccumulatorEvent`.

### 5. State writes (body @ 0xf378)
Body is read-only w.r.t. accumulator fields: it reads `total_unclaimed_tokens`,
`total_claimed_tokens`, `current_sol_volume`, `last_update_timestamp` to populate
the event. The lamport drain + discriminator overwrite happen in exit glue.
Only caller = close dispatch `0x25fa3` (verified via `callers 0xf378`).

### 6. GAP vs recovered `.rs`
**No gap.** Event field set, read-only body, and `close=user` refund binding match
source (lib.rs:125-126).

---

## 3. sync_user_volume_accumulator @ 0x25ff1

### 1. Purpose
If the global epoch has rolled over (both the user's last update and "now" precede
the current `start_time`), reset the user's claimed-token bookkeeping to zero so a
new epoch starts clean. Emits `SyncUserVolumeAccumulatorEvent` only when a nonzero
balance was actually cleared.

### 2. Accounts validated (`try_accounts` @ 0x1ffb6)
- `user: UncheckedAccount` (used to derive the PDA and name the event — not a signer).
- `global_volume_accumulator: Account<GlobalVolumeAccumulator>` —
  `seeds=[b"global_volume_accumulator"], bump` (`"global_volume_accumulator"`
  rodata `0x1b7037`).
- `user_volume_accumulator: Account<UserVolumeAccumulator>` —
  `mut, seeds=[b"user_volume_accumulator", user.key()], bump`.
- event-CPI accounts.

### 3. Error / `require!` order (body @ 0xf64a)
1. `Clock::get()` (`0x34127` @ `0xf64f`); error → early return (`0xf651`).
2. Guard 1: `last_update_timestamp >= start_time` → skip (`jsge` @ `0xf654`).
3. Guard 2: `timestamp >= start_time` → skip (`jslt … ja` @ `0xf656–0xf657`).
   Both `< start_time` required to proceed (matches `last_update < start && now < start`).
4. `before == 0` → skip event (`jeq` @ `0xf65b`), but the zeroing writes still happen.

### 4. CPIs
- Self-CPI `emit_cpi!` for `SyncUserVolumeAccumulatorEvent` (only when `before > 0`).
- No account create/close, no lamport movement.

### 5. State writes + recompute logic (body @ 0xf64a)
Flattened `ctx.accounts` struct (base `r9 = [ctx+8]`):
`+0x208` = `global.start_time`, `+0x250` = `total_claimed_tokens`,
`+0x258` = `current_sol_volume`, `+0x260` = `last_update_timestamp`,
`+0x289` = `has_total_claimed_tokens`.

On the taken branch:
- `before = total_claimed_tokens` (read `[r9+0x250]`, `0xf658`)
- `has_total_claimed_tokens = false` → `stb [r9+0x289], 0` (`0xf659`)
- `total_claimed_tokens = 0` → `stdw [r9+0x250], 0` (`0xf65a`)

It writes **only** those two fields. No recompute of rewards; this is a pure reset.

### 6. GAP vs recovered `.rs` — timestamp field question
**No gap. Explicitly verified the timestamp question.** The task asks whether the
binary updates a timestamp/epoch field that the source omits. It does **not**:
- `last_update_timestamp` (`[r9+0x260]`) is **read** for guard 1 but **never
  written** — no store to `+0x260` exists anywhere in `0xf64a`.
- `current_sol_volume` (`[r9+0x258]`) is untouched.

So the binary clears exactly `total_claimed_tokens` (+0x250) and
`has_total_claimed_tokens` (+0x289), identical to `volume_sync.rs`. This matches the
sibling reset in `incentives.rs:84` (`u.total_claimed_tokens=0; u.has_total_claimed_tokens=false;`)
which also deliberately leaves `last_update_timestamp` stale. Source is faithful.

---

## 4. admin_set_idl_authority @ 0x260a3

### 1. Purpose
Transfer control of the canonical Anchor IDL account. If the IDL account is still
System-owned (unclaimed), move its lamports out via a seeded System transfer;
otherwise (program-owned) rewrite the IDL header's `authority` to the supplied
`idl_authority: Pubkey`. Emits `AdminSetIdlAuthorityEvent{idl_authority}`.

### 2. Accounts validated (`try_accounts` @ 0x14510)
- `authority: Signer`
- `global: Account<Global>` — `seeds=[b"global"], bump, has_one=authority @ NotAuthorized`
- `idl_account: UncheckedAccount (mut)` — `address = IdlAccount::address(&crate::ID)`
- `system_program: Program<System>`
- `program_signer: UncheckedAccount` — `seeds=[], bump` (empty-seed canonical PDA)
- event-CPI accounts. Instruction arg `idl_authority` is passed to the body via
  `r3 = &stack[-0x20]` (dispatch copies the 32-byte Pubkey from the ix data at
  `0x260ac–0x260c5`).

`NotAuthorized` (`has_one`) and the `global` PDA are enforced in `try_accounts`
before the body runs.

### 3. Error / `require!` order (body @ 0x2aafd)
1. Load `idl_account.owner` (32 bytes, `0x2ab04–0x2ab0b`).
2. `memcmp(owner, system_program::ID, 32)` (`0x2ab11`): if equal → **branch A**
   (System-owned transfer path, `jeq +0x47`).
3. else `memcmp(owner, crate::ID /*0x1b79df*/, 32)` (`0x2ab1b`): if equal →
   **branch B** (program-owned realloc path, `jeq +0x132`).
4. else → `PumpError::AccountTypeNotSupported` (require failure, panic string
   `0x1b5fa4` len `0x37`). This is the source `require!(owner==crate::ID, AccountTypeNotSupported)`.

Branch B internal order (verified `0x2ac53+`):
`realloc(10240)` **first** (`r3=0x2800` → `0x345b6` @ `0x2ac57`), **then** the
8-byte discriminator check `data[..8] == [24,70,98,191,58,144,123,158]`
(disc bytes present at rodata `0x1b647f`; compared `0x2ac6c–0x2ac71`), else
`AccountTypeNotSupported`. Matches source ordering (realloc precedes the disc
`require!`). After the check: `IdlAccount::try_deserialize` → set `authority` →
`try_serialize`.

### 4. CPIs
- **Branch A:** `system_instruction::transfer_with_seed(idl_account → authority,
  seed "anchor:idl" [rodata `0x1b6818`], owner=crate::ID)` via
  `invoke_signed` signed by `program_signer` (empty-seed PDA, `signers=[[bump]]`),
  then `return Ok(())` — no header rewrite, no event in this branch (per source,
  the function returns before the `emit!`).
- **Branch B:** no CPI except the final self-CPI `emit_cpi!` for
  `AdminSetIdlAuthorityEvent`. The realloc is a direct account-data resize, not a CPI.

### 5. State writes
- Branch A: writes nothing in the program's own accounts; drains `idl_account`
  lamports to `authority` through the System program.
- Branch B: resizes `idl_account` to 10240 bytes, then overwrites the deserialized
  IDL header's `authority` field with `idl_authority` and re-serializes it back
  into `idl_account` data.

### 6. GAP vs recovered `.rs`
**No gap.** Branch selection (System vs program vs neither), the
`transfer_with_seed`+`invoke_signed` empty-seed signer, `realloc(10240)` **before**
the discriminator `require!`, the exact IDL discriminator `[24,70,98,191,58,144,123,158]`,
and the header-authority rewrite all match `idl_authority.rs`. The System-owned
branch returning before `emit!` (so no event on first-claim transfer) is preserved.
