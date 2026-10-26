# Pump.fun — Quote-Control Cluster (RE spec)

Binary: `evidence/original/pump/deployed.so`
Recovered source: `programs/pump/src/quote_control/*.rs` (+ `lib.rs` for the legacy pair)
Tool: `sbftool.py` (PCs below are **instruction indices**, as printed by sbftool, not byte offsets).

## Cluster overview — TWO independent quote-mint whitelists

Binary verification shows this cluster spans **two distinct, unrelated whitelist mechanisms**. This is faithful to the recovered source but is easy to miss:

| Mechanism | Storage | Instructions | Entry log | Handler addrs |
|---|---|---|---|---|
| **Legacy** | `Global.whitelisted_quote_mints: [Pubkey; 1]` (fixed 1-slot array inside the `global` PDA) | `add_quote_mint`, `remove_quote_mint` (`AdminGlobal` ctx) | `Instruction: AddQuoteMint` / `RemoveQuoteMint` | 0x24774 / 0x24826 |
| **PDA** | `QuoteControl` PDA (`seeds=["quote-control"]`), `mints: Vec<QuoteControlMint>` grown on demand up to 256 | `initialize_quote_control`, `set_quote_control_admin`, `add_quote_control_mint`, `remove_quote_control_mint`, `set_quote_control_reserves_admin`, `set_quote_control_mint_reserves` | `Instruction: *QuoteControl*` | 0x264a2, 0x264e3, ~0x265d5, 0x26667, 0x26728, 0x267e9 |

Anchor discriminators (dispatch table at insn 0x237c7–0x237db, verified via `disc`):
`initialize_quote_control=ef49f5add1b15442`, `set_quote_control_admin=3e4fa1d3a5aad6d2`,
`add_quote_control_mint=020e3d8aaa8e0e5f`, `remove_quote_control_mint=df07fd1a51a5daa6`,
`set_quote_control_reserves_admin=a1c3dea5e165c03e`, `set_quote_control_mint_reserves=74dc6b53bf2c2049`.

`QuoteControl` in-memory layout confirmed from state-write offsets in the core fns:
`admin` @ +0x18, `reserves_admin` @ +0x38 (admin+0x20), `_reserved[32]`, then `mints` Vec.
(Account bytes: 8-disc, then admin, reserves_admin, _reserved, Vec — matches `#[account] #[derive(InitSpace)]`.)

**Authorization symmetry (key check): CONFIRMED.** `add_quote_control_mint` (wrapper ~0x265d5) and `remove_quote_control_mint` (wrapper 0x26697) both `call 0x1c9db` — the **same** `try_accounts` routine (`callers 0x1c9db` → `{0x265d5, 0x26697}`). Add and remove are therefore gated identically (`UpdateQuoteControlMints`: `authority == global.authority || quote_control.is_admin(authority)`). Each other handler has its own distinct `try_accounts` whose size tracks its constraint complexity (set_admin 104 insns < reserves/mint-reserves 114 < update 124), consistent with the differing `#[account(constraint=...)]` sets in source. **Validation** symmetry is intentionally asymmetric (add must reject default/native/duplicate; remove only locates) — see per-handler GAP notes.

---

## Handler 1: `add_quote_mint` @ 0x24774 (LEGACY)

**Purpose.** Legacy admin-only whitelisting of a quote mint into the single-slot
`Global.whitelisted_quote_mints[1]` array. Distinct from the QuoteControl PDA.

**Accounts validated.** `AdminGlobal` ctx (try_accounts @ 0x2cca9):
- `global`: `mut, seeds=[b"global"], bump, has_one = authority @ NotAuthorized`.
- `authority`: `mut, Signer`.
- `#[event_cpi]` → the two trailing event-authority / program accounts.
No `seeds::program` override anywhere in this cluster.

**Error / require! conditions** (core @ 0x13432, 315 insns):
- `quote_mint == Pubkey::default()` → `QuoteMintNotEligibleForWhitelist` (memcmp vs zero buf, 0x13440).
- `quote_mint == So11111111111111111111111111111111111111112` → `QuoteMintNotEligibleForWhitelist` (memcmp vs const @ rodata 0x1b5cc8, **decoded = SPL native mint**, 0x13441/0x13448).
- `whitelisted_quote_mints.contains(quote_mint)` → `QuoteMintAlreadyWhitelisted`.
- no empty (default) slot found → `QuoteMintWhitelistFull`.
- Signer/has_one failures → `NotAuthorized`.

**CPIs.** None (only `emit_cpi!` self-CPI from `#[event_cpi]`).

**State writes.** First default-valued slot of `Global.whitelisted_quote_mints` ← `quote_mint` (array lives at `global` data +0x3a0 region, ref at 0x13449 `add64 r8, 0x3a0`). No other field touched.

**GAP vs recovered `lib.rs:105-108`.** None. Binary matches: checks default + **only** the SPL native mint, `.contains`, finds first default slot, assigns. The single-native-mint check (SPL only, **not** the Token-2022 native mint) is faithful to source and is the one asymmetry vs `QuoteControl::validate_new_mint` (which rejects both natives). Noted as design observation, not a decompile gap; exploitability depends on whether trade paths still consume `Global.whitelisted_quote_mints`, which is outside this cluster.

---

## Handler 2: `remove_quote_mint` @ 0x24826 (LEGACY)

**Purpose.** Legacy admin-only removal of a mint from `Global.whitelisted_quote_mints[1]` (clears the slot back to default).

**Accounts validated.** Identical `AdminGlobal` ctx (try_accounts @ 0x2cca9, call at 0x24855) — same `has_one = authority` on `global`.

**Error / require! conditions** (core reached from wrapper @ 0x24863):
- `quote_mint == Pubkey::default()` → `QuoteMintNotEligibleForWhitelist`.
- no slot equal to `quote_mint` → `QuoteMintNotWhitelisted`.
- Signer/has_one failures → `NotAuthorized`.

**CPIs.** None (event self-CPI only).

**State writes.** Matching slot of `Global.whitelisted_quote_mints` ← `Pubkey::default()`.

**GAP vs recovered `lib.rs:110-112`.** None. Binary matches: default-check, locate matching slot, zero it. Add/remove validate asymmetrically **by design** (add rejects native+duplicate+full; remove only the default-check + lookup) — this is identical in source, so no decompile gap. Authorization is identical (same `AdminGlobal`/`has_one`), so the removal gate matches the add gate.

---

## Handler 3: `initialize_quote_control` @ 0x264a2

**Purpose.** Create the empty `QuoteControl` PDA. `admin`/`reserves_admin` start as the default key; `global.authority` assigns them afterwards.

**Accounts validated.** `InitializeQuoteControl` ctx (try_accounts @ 0x1bcdd, 371 insns):
- `quote_control`: `init, payer = user, space = 8 + QuoteControl::INIT_SPACE, seeds=[QUOTE_CONTROL_SEED=b"quote-control"], bump`. `init` ⇒ fails if already initialized.
- `user`: `mut, Signer` (pays rent).
- `system_program`: `Program<System>` (used by `init` for the create CPI).

**Error / require! conditions.** Only the Anchor-generated ones: PDA-seed/bump mismatch, already-initialized, payer not signer, rent/space. **No explicit authority gate — permissionless** (whoever calls just funds the account; they cannot set `admin`, which stays default and is only settable by `global.authority`). Faithful to source.

**CPIs.** System `create_account` (via `init`). Event self-CPI.

**State writes** (body @ 0x264c1-0x264c5): `memset 0x60` bytes to 0 over `admin(32)+reserves_admin(32)+_reserved(32)` ⇒ `admin = default`, `reserves_admin = default`, `_reserved = [0;32]`; `mints = Vec::new()` (len 0).

**GAP vs recovered `initialize_quote_control.rs`.** None.

---

## Handler 4: `set_quote_control_admin` @ 0x264e3

**Purpose.** Rotate the QuoteControl `admin`. **Only** `global.authority` may call (stricter than the other mutators).

**Accounts validated.** `SetQuoteControlAdmin` ctx (try_accounts @ 0x1c143, 104 insns — smallest, consistent with a single `has_one`):
- `global`: `seeds=[b"global"], bump, has_one = authority @ NotAuthorized`.
- `authority`: `Signer`.
- `quote_control`: `mut, seeds=[QUOTE_CONTROL_SEED], bump`.
- `#[event_cpi]`.
Note: `quote_control` is **not** read for authorization here (no `is_admin`/`is_reserves_admin` path) — only `global.authority` via `has_one`. Matches source.

**Error / require! conditions.** `authority != global.authority` → `NotAuthorized` (has_one); PDA-seed/bump mismatch. Arg `new_admin` is unvalidated (may be default — intentional, allows "unsetting").

**CPIs.** Event self-CPI only.

**State writes** (core @ 0xcc59): reads old `admin` from `quote_control +0x18..+0x30` (for event), writes `new_admin` arg into `quote_control +0x18..+0x30`. Only the `admin` field changes.

**GAP vs recovered `update_quote_control_mints.rs::set_quote_control_admin`.** None. Confirmed the gate is `has_one=authority` (global.authority) **only**, not `is_admin` — so an existing `admin` cannot rotate itself; the global authority controls admin assignment. Faithful.

---

## Handler 5: `remove_quote_control_mint` @ 0x26667

**Purpose.** Remove a listed quote mint from the `QuoteControl.mints` Vec. Existing curves keep their reserves.

**Accounts validated.** `UpdateQuoteControlMints` ctx (try_accounts @ 0x1c9db, 124 insns), **shared with `add_quote_control_mint`** (`callers 0x1c9db = {0x265d5(add), 0x26697(remove)}`):
- `authority`: `mut, Signer`, constraint `authority == global.authority || quote_control.is_admin(authority) @ NotAuthorized`.
- `global`: `seeds=[b"global"], bump`.
- `quote_control`: `mut, seeds=[QUOTE_CONTROL_SEED], bump`.
- `system_program`; `#[event_cpi]`.

**Error / require! conditions** (core `remove_mint`):
- `quote_mint == Pubkey::default()` → `QuoteMintNotEligibleForWhitelist`.
- mint not present in Vec → `QuoteMintNotWhitelisted`.
- authority constraint fail → `NotAuthorized`.

**CPIs.** Event self-CPI only. (No realloc/shrink — account is not resized on removal; `Vec::remove` just shifts in place. Matches source comment "account grows on demand"; it never shrinks.)

**State writes.** `quote_control.mints` ← entry at found index removed (Vec contents + len shift). No admin/reserves_admin change.

**GAP vs recovered `remove_quote_control_mint`.** None. Authorization proven identical to `add_quote_control_mint` (shared try_accounts) → the add/remove pair is authorization-symmetric. Validation asymmetry (add's `validate_new_mint` does default+2×native+duplicate+len<256; remove does default+lookup) is intentional and matches source.

---

## Handler 6: `set_quote_control_reserves_admin` @ 0x26728

**Purpose.** Rotate the `reserves_admin`. Callable by `global.authority` **or** `admin`.

**Accounts validated.** `SetQuoteControlReservesAdmin` ctx (try_accounts @ 0x1c611, 114 insns):
- `authority`: `Signer`, constraint `authority == global.authority || quote_control.is_admin(authority) @ NotAuthorized`.
- `global`: `seeds=[b"global"], bump`.
- `quote_control`: `mut, seeds=[QUOTE_CONTROL_SEED], bump`.
- `#[event_cpi]`. (No `system_program` — no realloc path.)

**Error / require! conditions.** authority not in {global.authority, admin} → `NotAuthorized`; PDA-seed/bump. `new_reserves_admin` arg unvalidated (may be default).

**CPIs.** Event self-CPI only.

**State writes** (core @ 0xcf87): reads old `reserves_admin` from `quote_control +0x38..+0x50` (for event), writes `new_reserves_admin` arg into `+0x38..+0x50`. Only `reserves_admin` changes. (This write offset confirms `reserves_admin` sits at admin+0x20.)

**GAP vs recovered `set_quote_control_reserves_admin`.** None. Note the authorization deliberately **excludes** `reserves_admin` itself (only global.authority or admin can rotate the reserves_admin) — consistent with source constraint.

---

## Handler 7: `set_quote_control_mint_reserves` @ 0x267e9

**Purpose.** Update the `initial_virtual_quote_reserves` of an already-listed mint; returns the old value for the event. Existing curves keep the reserves they were created with.

**Accounts validated.** `SetQuoteControlMintReserves` ctx (try_accounts @ 0x1c3a8, 114 insns):
- `authority`: `Signer`, constraint `authority == global.authority || quote_control.is_admin(authority) || quote_control.is_reserves_admin(authority) @ NotAuthorized` (widest set — includes `reserves_admin`).
- `global`: `seeds=[b"global"], bump`.
- `quote_control`: `mut, seeds=[QUOTE_CONTROL_SEED], bump`.
- `#[event_cpi]`. (No `system_program`.)

Instruction data = `quote_mint(32) + initial_virtual_quote_reserves(u64)`; wrapper checks data length (0x267f9 `and64 r3,-0x8; jeq r3,0x20`) and reads the u64 at data +0x20.

**Error / require! conditions** (core @ 0xcdf5): mint not found in Vec (search helper @ 0xd3e5 returns tag ≠ 2) → `QuoteMintNotWhitelisted`; authority not in {global.authority, admin, reserves_admin} → `NotAuthorized`.

**CPIs.** Event self-CPI only.

**State writes.** The matched `QuoteControlMint.initial_virtual_quote_reserves` (u64 inside the Vec entry) ← new value; old value returned and emitted. No admin/reserves_admin/Vec-length change.

**GAP vs recovered `set_quote_control_mint_reserves`.** None. This is the only handler whose authorization includes `reserves_admin` — confirmed as the widest `try_accounts` constraint set (3-way OR), matching the source comment "reserves_admin may only update the initial virtual quote reserves of listed mints."

---

## Summary of GAPs / observations

- **No decompile gaps found** in any of the 7 handlers. Discriminators, PDA seeds (`b"global"`, `b"quote-control"`, no `seeds::program`), error paths, state-write offsets (admin +0x18, reserves_admin +0x38, mint-entry u64), the SPL-native-mint constant (rodata 0x1b5cc8), and the permissionless `init` all match `quote_control/*.rs` + `lib.rs`.
- **Dual-whitelist structure** is real and faithful: a legacy single-slot array on `Global` (`add/remove_quote_mint`) *and* the growable `QuoteControl` PDA Vec. Anyone reading only the PDA mechanism will miss the legacy pair.
- **Authorization asymmetry ladder is intentional and verified structurally**: set_admin = global.authority only (has_one, smallest try_accounts) ⊂ add/remove_mint & reserves_admin = +admin ⊂ set_mint_reserves = +reserves_admin (widest). add/remove_control_mint proven identical (shared try_accounts 0x1c9db).
- **Validation (not auth) asymmetry** between add and remove is by design in source (add rejects default/native/duplicate/full; remove only default+lookup). Legacy add checks only the SPL native mint, not the Token-2022 native mint — faithful to source; flag for cross-cluster review of whether `Global.whitelisted_quote_mints` is still consumed by trade paths.
