# Pump.fun — Cluster 01: Admin / Config Handlers

Binary: `D:/dev/ext/pumpfun-source/evidence/original/pump/deployed.so`
Recovered source: `programs/pump/src/lib.rs` (handler bodies) + `global_init.rs`
Method: each handler dispatch stub was disassembled with `sbftool.py func/dis`; the
Anchor accounts-deser routine and the per-handler "body" function were traced, and the
concrete field-store offsets / error codes were read directly out of the bytecode.

## Handler → binary identity (verified)

Each dispatch stub begins by logging `"Instruction: <Name>"` via `sol_log_`
(`lddw r1, <strptr>; mov64 r2, <len>; call sol_log_`). The log length = 13 (`"Instruction: "`) + name length, which uniquely pins every stub to its handler:

| Addr | log len | Name string | Handler |
|------|---------|-------------|---------|
| 0x2421b | 0x17 (23) | `Instruction: Initialize` | `initialize` |
| 0x24261 | 0x22 (34) | `Instruction: UpdateGlobalAuthority` | `update_global_authority` |
| 0x2430e | 0x1b (27) | `Instruction: ToggleCreateV2` | `toggle_create_v2` |
| 0x243d8 | 0x22 (34) | `Instruction: ToggleCashbackEnabled` | `toggle_cashback_enabled` |
| 0x24566 | 0x1d (29) | `Instruction: SetMaxCurveDepth` | `set_max_curve_depth` |
| 0x245dc | 0x1d (29) | `Instruction: ToggleMayhemMode` | `toggle_mayhem_mode` |

Shared helpers observed:
- `0x2cca9` — `try_accounts` for the `AdminGlobal` context (used by the 4 admin toggle/set handlers).
- `0x20fef` — `try_accounts` for `UpdateGlobalAuthority`.
- `0x2c857` — `try_accounts` for `Initialize` (the `init` PDA).
- `0xdcf`, `0x526`, `0x33766`, `0x2dd` — generic Anchor finish/serialize + `Result`/error
  construction glue (shared across many handlers; NOT per-handler bodies).

**In-memory `Global` field offsets recovered from the bodies** (Rust struct layout as
chosen by the compiler — NOT the Borsh/serialized offsets, but they unambiguously identify
the mutated field): `authority` = +0x1a0; `create_v2_enabled` = +0x4a3;
`mayhem_mode_enabled` = +0x4a4; `is_cashback_enabled` = +0x4a5 (the three toggle bools are
packed consecutively).

---

## initialize @ 0x2421b

1. **Purpose**: One-time creation of the singleton `Global` config PDA; sets `initialized=true` and `authority=user`.
2. **Accounts** (`Initialize`, from `global_init.rs`): `global` (`#[account(init, payer=user, space=1088, seeds=[b"global"], bump)]`), `user` (`mut` `Signer`), `system_program`. `try_accounts` at `0x2c857` performs the PDA derivation + `init` (system_program `create_account`, space 1088).
3. **Error conditions**: No `require!` in the handler body. Re-initialization is blocked structurally by the `init` constraint (the PDA create fails if the `global` account already exists) — not by an `initialized`/`AlreadyInitialized` check. Account-model/signer/seed failures are raised inside `0x2c857`.
4. **CPIs**: `system_program::create_account` via the Anchor `init` path (inside `try_accounts`). No other external program invoked.
5. **State writes**: `global.initialized = true` (binary `0x24248: stb [r10-0x457], 0x1` into the stack-materialized struct before serialize-back), `global.authority = user.key()` (32-byte pubkey copied from the user account into the struct prior to the `0xdcf` serialize/exit). All other `Global` fields are left zero.
6. **GAP**: No gap found. Body is `0x2421b–0x24260`. Verified the single `initialized=1` byte store (`0x24248`) and the authority copy + serialize via `0xdcf` (`0x2424f`). No bytecode branch reads `initialized` as a guard — consistent with the recovered source, which relies on `init` for single-use.

---

## update_global_authority @ 0x24261

1. **Purpose**: Transfer `Global.authority` to `new_authority`; emits `UpdateGlobalAuthorityEvent`.
2. **Accounts** (`UpdateGlobalAuthority`, lib.rs:449): `global` (`#[account(mut, seeds=[b"global"], bump, has_one=authority @ PumpError::NotAuthorized)]`), `authority` (`Signer`), `new_authority` (`UncheckedAccount`). `try_accounts` at `0x20fef`.
3. **Error conditions**: `has_one = authority` → `NotAuthorized` (6000) if the signer ≠ current `global.authority`; signer check on `authority`; seed/bump check on `global`. Enforced in `0x20fef`. No validation on `new_authority` (zero pubkey and self are both accepted).
4. **CPIs**: `emit_cpi!` self-invoke to record the event (Anchor CPI-event log). No other external program.
5. **State writes**: `global.authority = new_authority.key()` — body `0x26918` reads the 32-byte key from the `new_authority` account (`[r1+0x0/8/0x10/0x18]`) and stores it to `global+0x1a0` (`0x26920–0x26923`). Event fields (`global.key`, `authority.key`, `new_authority.key`, `timestamp`) are assembled afterward.
6. **GAP**: No gap found. Binary confirms the Pubkey write at +0x1a0 and the event path, with no `new_authority != 0 / != self` branch — matching the source's explicit "zero/self are accepted" comment.

---

## toggle_create_v2 @ 0x2430e

1. **Purpose**: Flip `Global.create_v2_enabled` to `enabled` (must differ from current value).
2. **Accounts** (`AdminGlobal`, lib.rs): `global` (`#[account(mut, seeds=[b"global"], bump, has_one=authority @ PumpError::NotAuthorized)]`), `authority` (`mut` `Signer`). `try_accounts` at `0x2cca9`.
3. **Error conditions**:
   - `has_one=authority` / signer / seed checks → `NotAuthorized` (6000), inside `0x2cca9`.
   - **Borsh `bool` ABI check**: the stub validates the `enabled` arg byte is `< 2` (`0x2431c: jlt r6, 0x2, …`); a byte ≥ 2 takes the invalid-bool panic path (`0x2431d–0x2434c`).
   - **`require_neq!(global.create_v2_enabled, enabled, NotAuthorized)`**: body `0x26ab0` normalizes the current field to a bool and `xor`s with `enabled` (`0x26ab2–0x26ab9`); if equal it builds error code **`0x1770` (6000 = NotAuthorized)** (`0x26aee: stw [r10-0x78], 0x1770`).
4. **CPIs**: None (the trailing `callx r2` is Box/drop-glue on the error path, not a program invoke).
5. **State writes**: `global.create_v2_enabled = enabled` → `0x26aba: stxb [r8+0x4a3], r7` (only on the "value changed" branch).
6. **GAP**: No gap found. Both the `require_neq` guard (error 0x1770) and the conditional store at +0x4a3 are present and match the source. Minor binary-only detail: toggling to the **current** value returns `NotAuthorized` (6000) — same code as an auth failure, so the error message is indistinguishable from a real permission denial (source-faithful, but a caller-visible ambiguity).

---

## toggle_cashback_enabled @ 0x243d8

1. **Purpose**: Flip `Global.is_cashback_enabled` to `enabled` (must differ from current).
2. **Accounts**: `AdminGlobal` (same as above); `try_accounts` at `0x2cca9`.
3. **Error conditions**: identical structure to `toggle_create_v2` — `has_one`→6000; bool ABI check (`0x243e6: jlt r6, 0x2`); `require_neq!(..., NotAuthorized)` in body `0x26b04` (builds 0x1770 when current == enabled).
4. **CPIs**: None.
5. **State writes**: `global.is_cashback_enabled = enabled` → `0x26b0e: stxb [r8+0x4a5], r7`.
6. **GAP**: No gap found. Body `0x26b04` verified: reads `[r8+0x4a5]`, require_neq guard, conditional store at +0x4a5. Same current-value→NotAuthorized ambiguity note as `toggle_create_v2`.

---

## set_max_curve_depth @ 0x24566

1. **Purpose**: Set `Global.max_curve_depth` to an arbitrary `u8`.
2. **Accounts**: `AdminGlobal`; `try_accounts` at `0x2cca9`.
3. **Error conditions**: ONLY the account-level checks (`has_one=authority`→6000, signer, seed) inside `0x2cca9`. **No `require_neq`, no bounds/range check, no `< 2` bool check** — the arg is a raw `u8` read (`0x24572: ldxb r1, [r1+0x0]`), so the full 0..=255 range (including 0 and the current value) is accepted.
4. **CPIs**: None.
5. **State writes**: `global.max_curve_depth = max_curve_depth` (single `u8` store; no event). Unlike the toggles it has no dedicated guarded body — the store + serialize-back route through the generic finish helper `0xdcf`.
6. **GAP**: No gap found vs source. Noted binary differences from its sibling setters (consistent with the `.rs`, flagged for spec completeness): (a) **no event emission** at all — the other config mutators (`update_global_authority`, and in the wider cluster `update_creator_fee_config`, etc.) emit events, this one is silent; (b) **no value guard** — accepts the same value or `0`; (c) **no ABI 0/1 validation** (it's a `u8`, not a `bool`), in contrast to the three toggles' `jlt <2` check.

---

## toggle_mayhem_mode @ 0x245dc

1. **Purpose**: Flip `Global.mayhem_mode_enabled` to `enabled` (must differ from current).
2. **Accounts**: `AdminGlobal`; `try_accounts` at `0x2cca9`.
3. **Error conditions**: identical to the other toggles — `has_one`→6000; bool ABI check (`0x245ea: jlt r6, 0x2`); `require_neq!(..., NotAuthorized)` in body `0x26b58` (builds 0x1770 when current == enabled).
4. **CPIs**: None.
5. **State writes**: `global.mayhem_mode_enabled = enabled` → `0x26b62: stxb [r8+0x4a4], r7`.
6. **GAP**: No gap found. Body `0x26b58` verified: reads `[r8+0x4a4]`, require_neq guard, conditional store at +0x4a4. Same current-value→NotAuthorized ambiguity note.
