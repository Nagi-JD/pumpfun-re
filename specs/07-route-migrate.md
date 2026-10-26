# 07 — Route / Migration handler cluster

Reverse-engineered from the deployed Pump.fun program
`evidence/original/pump/deployed.so`, cross-checked against the recovered
sources in `programs/pump/src/` (`multi_hop_curve.rs`, `migrate.rs`,
`migrate_v2.rs`, `extend.rs`). Addresses below are sbftool instruction indices
(`0x…`). Each handler is an Anchor dispatch stub that (1) `sol_log_`s
`"Instruction: <Name>"`, (2) deserializes accounts via a `try_accounts`
routine, (3) `memcpy`s the account struct, (4) tail-calls the real `execute`.

| Handler | Dispatch stub | Name string (len) | try_accounts | execute |
|---------|---------------|-------------------|--------------|---------|
| multi_hop_curve_swap | `0x252b8` | `0x1b7e16` "Instruction: MultiHopCurveSwap" (0x1e) | — (arg+acct inline) | `0xacfb` |
| migrate | `0x256fb` | `0x1b7e98` "Instruction: Migrate" (0x14) | `0x19eea` | `0x7f6e` (264 insns) |
| migrate_v2 | `0x25749` | `0x1b7eac` "Instruction: MigrateV2" (0x16) | `0x1ab5e` | `0x9311` (460 insns) |
| extend_account | `0x257cf` | `0x1b7ec2` "Instruction: ExtendAccount" (0x1a) | `0x1985a` | `0x771b` (126 insns) |

---

## 1. multi_hop_curve_swap  (stub `0x252b8` → execute `0xacfb`)

### Purpose
Routes an input amount through a chain of **pump bonding-curve** hops
(curve↔curve swaps, buy or sell direction per hop), ending at a destination
token account. Returns `CurveRunResult { amount_out, buyback_fee }`. This is the
curve-leg executor used by the router; `COMPLETION.md` correctly marks it
PARTIAL — the deployed binary handles cases the reconstruction fences off
(completion/migration mid-route, WSOL/non-native quote, Token-2022, holder/
cashback/mayhem coins).

### Argument decode (stub `0x252b8`)
- `252c1`: `ldxdw r1,[r8-0xff8]` = ix-data len; `252c2 jlt r1,8` → needs ≥ 8.
- `252ce → 0x22eb` decodes `amount_in: u64` then `hop_fees: Vec<u8>`.
- `25311 → 0xacfb` calls execute with r2=accounts, r3=amount_in,
  r4=`hop_fees` vec.

### Validation + ORDER (execute `0xacfb`, verified)
1. `acfd jeq r9,0` → **amount_in != 0** (else `BuyZeroAmount`). r9 = amount_in.
2. `acfe ldxdw r5,[r2+0x18]` = `remaining_accounts.len()`;
   `acff jlt r5,5` → **len ≥ 5**.
3. `ad00-ad05`: `r0 = len/5`; `r0*5 == len` → **len % 5 == 0**; `count = len/5`.
   (`NotEnoughRemainingAccounts`, str `0x1b8432`.)
4. `ad06-ad07 ldxdw r1,[r4+0x10]; jne r1,r0` → **hop_fees.len() == count**
   (`MultiHopHopFeesMismatch`, str `0x1b8b63`).
5. `ad0a-ad10` loop `ldxb r4,[r3]; jlt r4,4` → **every flag < 4**.
6. `ad11-ad64`: two reconstruction-domain fences on `source`/`destination`
   (`owner == Tokenkeg && data_len == 165`) — i.e. the ordinary-Tokenkeg
   specialization.

**Accounts / remaining_accounts handling.** Fixed accounts = the `MultiHopCurve`
context (global, fee_config @FEES program, pump_amm global_config *signer*, user
*signer*, source_authority *signer*, source, destination, buyback_fee_recipient
(raw writable, slot 7), token/token-2022/system programs). `remaining_accounts`
is consumed **5 per hop**; each group is re-parsed as a `CurveHop`
(base_mint, quote_mint, bonding_curve PDA `["bonding-curve", base_mint]`,
associated_base_bonding_curve, associated_quote_bonding_curve) inside the loop
via `CurveHop::try_accounts` (`0xb70e` body, call `→0x1bae0` at `ae59`).

### Hop loop structure (execute `0xacfb`, loop head ≈ `ae05`)
- Loop induction var `index` in slot `[r10-0x248]`; `count` in `[r10-0x308]`;
  `count-1` precomputed in `[r10-0x2d0]` (`last = index==count-1`).
- `previous: Option<PreviousHop>` discriminant byte in `[r10-0x126]` (init `2`
  = None at `adce`).
- `event_authority` bump captured once in `[r10-0x2d8]` (`adee ldxb r2,[r2+0x22]`).
- Per iteration: `ae05 jlt index,count` guard → body trampoline `ae87 → 0xb676`
  (small shim) → **per-hop body `0xb70e`** which does: `CurveHop::try_accounts`,
  `prepare_curve` (realloc fence `data_len ≥ 166`), the curve-state require set,
  fee selection, reserve updates, token/lamport transfers, and the TradeEvent
  emit. After return the loop stitches `current_mint`, rebuilds `previous =
  Some(..)`, `amount = output`, `total_buyback += buyback`, `index++`.
- `af2d jlt r6,r2` is the back-edge.
- Terminal: `require_keys_eq!(current_mint, destination.mint)`
  (`MultiHopDiscontinuousPath`).

### Per-hop fee flags (verified via `0xb70e`)
`hop_fees[i]` is a 2-bit mask (`< 4`):
- `flag & 1` → **protocol fee leg active** (also gates the buyback leg and the
  `preflight_buyback_recipient` check on `buyback_fee_recipient`).
- `flag & 2` → **creator fee leg active**.
Rates come from `select_fees` (tier table by market-cap, with native/QUOTE_1/
QUOTE_2 → `fee_tiers`, QUOTE_STABLE → `stable_fee_tiers`, else exotic/flat), and
`protocol_fee_bps`/`creator_fee_bps` are zeroed when the corresponding flag bit
is clear. Buyback math (verified by the two `assert`s in source and the
`buyback_basis_points` load at `adc4-adcc`): `product = pf*buyback_bps`,
`buyback = product/10000`, with `pf - buyback` accrued to `protocol_fees`.

### Depth cap — GAP / note
Execute `0xacfb` enforces only `len≥5`, `len%5==0`, `hop_fees.len==count`,
`flags<4` — **no comparison of `count` against a max-depth global is present in
this function.** Yet the binary defines `CurveDepthExceeded` (str `0x1b8b51`)
and ships a `SetMaxCurveDepth` admin instruction, so the hop-count ceiling is
enforced by the **outer router/dispatch that invokes this `execute`**, not
inside it. The recovered `multi_hop_curve.rs` (the "noncompleting Tokenkeg"
hypothesis) likewise has no depth cap — consistent, but the cap itself lives
one frame up and is NOT reconstructed here.

### CPIs
Per hop: `checked_transfer` (spl `transfer_checked`) on the input leg and, on
the last hop, the output leg to `destination`; `system_transfer` on the native
buy leg; `native_buyback`/`checked_transfer` for the buyback leg; and the event
self-CPI (`route_event`). All go through the shared `invoke`/`invoke_signed`
thunks, so they do not appear as named syscalls inside `0xb70e` itself.

### TradeEvent trailing field `+0x198` — SOURCE TRACED (the key question)
The event struct is built by a dedicated constructor and serialized by
`Event::data` = **`0x2c496`** (TradeEvent discriminator `bddb7fd34ee661ee`
loaded at `lddw 0x2c4af` — the single monomorphization, called twice from
`route_event`: `bcd9` for `sol_log_data`, `bcec` for the CPI payload). `ix_name`
is the constant `"multi_hop_swap"` at `0x1b6ec8` (len 14), confirming this is
the multi-hop event.

Trailing field write (constructor `0x1177a`, struct base `r6`):
```
1184c: ldxdw r1, [r10 -0xe8]
1184d: stxdw [r6 +0x198], r1      ; TradeEvent.unparsed_trailing_field
```
`[r10-0xe8]` ← `r0` (`117d6`) ← caller arg spill slot `[r10-0xfc8]` (`1179a`).
The `field` analyzer on the ctor callsite reports **two** writers of that spill
slot — one per emit path:
```
writers of [r10-0xfc8] near call @ 0xbcd5:
  bbbb: stxdw [r10 -0xfc8], r9    ; native / SOL-quote path  (ctor 0xafc8)
  bcbb: stxdw [r10 -0xfc8], r8    ; non-native / SPL-quote    (ctor 0x1177a)
```
Both `r8`/`r9` are a **computed `u64` delta**, not an immediate 0: a checked
subtraction (helper `0x12a1c` = checked_sub, underflow→`Overflow`) of a
"before" quote amount (slot `-0x6c8` → `-0xa80`) and an "after" quote amount
(slot `-0xad0`), differenced at `bc8c: sub64 r1,r2`.

**Characterization:** `TradeEvent +0x198` = the hop's **quote-leg adapter
difference** — `quote_before_adapter − quote_after_adapter`, i.e. the quote
value withheld/consumed by the quote token program on that hop (a Token-2022
transfer-fee / quote-side slippage). It equals the recovered source's
`unparsed_trailing_field: adapter_difference = sub(quote_before_adapter,
quote_after_adapter)`. It is **0 only when the quote leg is lossless** (native
SOL, or a Tokenkeg identity adapter) and carries the real per-hop quote delta
otherwise.

**GAP:** the reconstruction forces `quote_after_adapter = quote_before_adapter`
(comment "Tokenkeg quote adapter is identity"), so the reconstructed field is
**always 0**; the deployed binary computes it live via the before/after quote
measurement, so it is non-zero for lossy (Token-2022 transfer-fee) quote mints.

---

## 2. migrate  (stub `0x256fb` → execute `0x7f6e`, 264 insns)

### Purpose
Migrates a **completed, native-SOL** bonding curve into a pump-AMM pool
(`pAMMBay6…`): creates the pool + ATAs, seeds base+quote liquidity, runs the
AMM create + (non-mayhem) buyback-boost CPIs, burns the LP, sweeps dust to the
withdraw_authority, zeroes the curve reserves, emits
`CompletePumpAmmMigrationEvent`.

### Accounts / PDAs
`global` (`has_one = withdraw_authority @ NotAuthorized`), `mint`, `bonding_curve`
PDA `["bonding-curve", mint]` with **`quote_mint == Pubkey::default()`**
(`UnsupportedQuoteMint` → this handler is native-only), `associated_bonding_curve`
ATA, user *signer*, and a large set of canonical pump-AMM PDAs derived with
`seeds::program = pump_amm`: `pool` `["pool", 0u16, pool_authority, mint,
wsol_mint]`, `pool_authority` `["pool-authority", mint]`, the four pool/temp
ATAs, `amm_global_config`, `lp_mint` `["pool_lp_mint", pool]`, the two event
authorities, rent sysvar. `remaining_accounts[0..2]` = `boost`,`vault` (required
only on the non-mayhem path).

### Error / require ORDER (execute `0x7f6e`)
1. `require!(d[48] != 0, BondingCurveNotComplete)` — completion flag byte 0x48.
2. **early-return** if `d[8..40]` all zero → `msg!("Bonding curve already
   migrated"); Ok(())` (idempotent; no error).
3. arithmetic guards (`Overflow`) on rent-top-up, `real_quote - fee`.
4. non-mayhem branch: `require!(remaining_accounts.len() >= 2,
   NotEnoughRemainingAccounts)`.

### CPIs (in order, all via the `call`/`invoke_signed` thunk)
system `transfer` (rent top-up to curve, if under-funded) → `realloc` curve to
166 → `move_lamports(curve→pool_authority, fee)` → 4× ATA `create` (idempotent
op `1`) for pool base/quote + temp base/quote → spl `transfer` base
(`cb→tmpb`, op 12) → `move_lamports(curve→tmpq, quote)` + spl `sync_native`
(op 17) → **AMM create** (disc `233,146,209,142,207,104,64,188`, 18 accounts) →
**non-mayhem**: optional system top-up of `vault`, then **AMM buyback/boost**
(disc `140,233,33,94,132,90,194,143`) → close temp base/quote accounts (op 9) →
LP burn (op 8, Token-2022) + close LP → system transfer pool_authority residue
to withdraw_authority → zero `d[8..40]` → emit `CompletePumpAmmMigrationEvent`
(self-CPI disc `228,69,165,46,81,203,154,29`). `quote_mint` in the event is
hardcoded `Pubkey::default()`.

### GAP vs recovered `migrate.rs`
Matches closely. The AMM-create account list in the recovered source lists
`token_program` twice (`…(&tok,..),(&tok,..)…`) where the on-chain handler
passes distinct programs; the native-only specialization is faithful. No new
guards found beyond those above.

---

## 3. migrate_v2  (stub `0x25749` → execute `0x9311`, 460 insns)

### Purpose
Generalized migrate supporting **both native-SOL and arbitrary SPL/Token-2022
quote mints**, with a dedicated `base_token_program` / `quote_token_program`
split and Token-2022 transfer-fee harvesting on the quote leg.

### Accounts / PDAs
Same skeleton as `migrate` but `base_mint`+`quote_mint` are
`InterfaceAccount<Mint>`, the curve constraint is
`quote_mint == native_mint if curve.quote_mint==default() else ==
curve.quote_mint` (`MintDoesNotMatchBondingCurve`), `associated_quote_bonding_curve`
is a canonical quote-ATA PDA, and ATAs are keyed by the per-side token program.
`base_token_program`/`quote_token_program` are `Interface<TokenInterface>`.

### Error / require ORDER (execute `0x9311`)
1. `require!(d[48] != 0, BondingCurveNotComplete)`.
2. idempotent early-return on `d[8..40]==0` ("already migrated").
3. `native = curve.quote_mint == default()`; branch-specific funding.
4. `Overflow` guards on rent/`real_quote - fee`/`quote_after - quote_before`.
5. non-mayhem: `require!(remaining_accounts.len() >= 2)`.
6. Token-2022 quote harvest branch:
   `require!(wsol.is_writable else QuoteMintNotWritable)` (error code **110**,
   `MigrateV2Error` — note the recovered IDL stops at 109; binary emits 110).

### CPIs
Superset of `migrate`, parameterized by `native`:
- **native**: `move_lamports(curve→pool_authority, fee)`; quote seeded via
  `move_lamports(curve→tmpq, quote)` + `sync_native` (op 17); ATAs created with
  the pool_authority as signer (op 1, 7 accounts incl. curve).
- **non-native**: `fee` paid by system transfer from `user`; base+quote seeded
  via spl `transfer` (op 12) using per-side decimals; ATAs created with `user`
  as payer (op 1, 6 accounts). `quote` measured as `amount(tmpq) -
  quote_before` to net out transfer-fees.
- AMM create (disc `233,…,188`, 18 accounts incl. both token programs) →
  non-mayhem AMM buyback/boost (disc `140,…,143`) → close temp base (op 9) →
  **Token-2022 fee harvest**: if quote has `TransferFeeConfig`, op `26,4`
  (`withdraw_withheld`) then close temp quote (op 9) → LP burn+close →
  pool_authority residue → zero `d[8..40]` → emit
  `CompletePumpAmmMigrationEvent` with `quote_mint = curve.quote_mint`.

### GAP vs recovered `migrate_v2.rs`
Faithful. The `quote_account_size` (Token-2022 extension-aware rent sizing) and
the `QuoteMintNotWritable` (110) harvest guard are the material differences vs
`migrate`; both present in the binary. Mayhem/holder/cashback interactions on
the quote side remain the general PARTIAL area (consistent with COMPLETION.md).

---

## 4. extend_account  (stub `0x257cf` → execute `0x771b`, 126 insns)

### Purpose
Grows an owned program account to the current fixed size for its account type
(migration/forward-compat realloc), paying the rent delta from `user` and
emitting `ExtendAccountEvent`.

### Accounts
`account` (`UncheckedAccount`, `mut`, `owner = crate::ID`), `user` *signer*
*mut*, `system_program`; `#[event_cpi]` adds event_authority+program.

### Error / require ORDER (execute `0x771b`)
1. Read `account` discriminator (first 8 bytes) and map to a target size:
   | discriminator (8 bytes) | size |
   |---|---|
   | `23,183,248,55,96,216,172,96` | 166 (BondingCurve/DistributionCurve) |
   | `167,232,232,177,200,108,114,127` | 1088 |
   | `86,255,112,14,102,53,154,250` | 137 |
   | `202,42,246,43,142,190,30,255` | 600 |
   | else | `return err!(AccountTypeNotSupported)` |
   Binary does the 8-byte compare via helper `0x34595`/`0x360b0` at `774d-7759`
   (length-≥8 guard `7755 jgt r2,7`), then branches per constant.
2. `if current >= size { return Ok(()) }` — idempotent, no shrink.
3. `delta = rent.min_balance(size) - rent.min_balance(current)`
   (`Overflow` on underflow).

### CPIs
system `transfer(user → account, delta)` → `account.realloc(size, false)` →
`emit!` + `emit_cpi!` of `ExtendAccountEvent{account,user,current_size,new_size,
timestamp}`.

### GAP vs recovered `extend.rs`
Matches exactly, including the four discriminator→size rows and the
`current >= size` early-out. No additional validation found.

---

## Evidence index (sbftool, binary `evidence/original/pump/deployed.so`)
- `func 0xacfb` (multi_hop execute), `func 0xb70e` (per-hop body / route_event),
  `func 0x1177a` + `0xafc8` (TradeEvent ctors), `func 0x2c496` (Event::data,
  disc@`0x2c4af`), `func 0x12a1c` (checked_sub).
- `field 0xbcd5 10 -0xfc8` → two trailing-field writers (`bbbb` r9 native /
  `bcbb` r8 non-native); trailing store `1184d: stxdw [r6+0x198], r1`.
- `func 0x7f6e` migrate, `func 0x9311` migrate_v2, `func 0x771b` extend_account.
- Instruction-name strings: `0x1b7e16/…98/…ac/…c2`; `multi_hop_swap`@`0x1b6ec8`;
  `CurveDepthExceeded`@`0x1b8b51`.
