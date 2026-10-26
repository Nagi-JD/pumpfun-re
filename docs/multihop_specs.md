# Multi-hop routing specs (pump `multi_hop_curve_swap` + pump_amm `multi_hop_swap`)

Private analysis for the user. Tags: **[B]** = confirmed in the deployed bytecode;
**[R]** = from the read-only reconstruction / cluster specs; **[partial]** = inferred
(reason stated). No byte-identity or exhaustive-behavior claim.

Sources: `spec/07-route-migrate.md` (pump, binary-verified), `pump multi_hop_curve.rs`,
`pump_amm multi_hop.rs` (reconstruction), `amm_specs.md`, `account_layouts.md`.
Addresses are `sbftool` pc units (vaddr/8).

---

# 1. pump `multi_hop_curve_swap` @ 0x252b8 (execute `0xacfb`)

## Purpose
Route an input amount through a chain of **pump bonding-curve** hops (curve-to-curve
buys/sells), ending at a destination token account. Returns
`CurveRunResult { amount_out, buyback_fee }` (16 bytes of return data). This is the
curve-leg executor the PumpSwap router and external routers invoke.

## Accounts / remaining layout [B/R]
Fixed `MultiHopCurve` context: `global`, `fee_config` (fees program), pump_amm
`global_config` (signer for the self-event), `user` signer, `source_authority` signer,
`source`, `destination`, `buyback_fee_recipient` (raw writable, slot 7), token / Token-2022 /
system programs, event authority/program.
`remaining_accounts` is consumed **5 per hop**:
`[base_mint, quote_mint, bonding_curve PDA ["bonding-curve", base_mint],
associated_base_bonding_curve, associated_quote_bonding_curve]`.
Each group is re-parsed as a `CurveHop` (`CurveHop::try_accounts` body `0xb70e`, call
`0x1bae0`).

## Args [B]
`amount_in: u64`, `hop_fees: Vec<u8>` (stub decodes amount then a Vec at `0x22eb`; execute
gets `r3=amount_in`, `r4=hop_fees`).

## Validation / order [B] (execute `0xacfb`)
1. `amount_in != 0` else `BuyZeroAmount`.
2. `remaining_accounts.len() >= 5`.
3. `len % 5 == 0` (`count = len/5`); else `NotEnoughRemainingAccounts`.
4. `hop_fees.len() == count`; else `MultiHopHopFeesMismatch`.
5. Every `hop_fees[i] < 4`.
6. Two reconstruction-domain fences on `source`/`destination` (`owner == Tokenkeg &&
   data_len == 165`) - the ordinary-Tokenkeg specialization.
7. Terminal: `current_mint == destination.mint`; else `MultiHopDiscontinuousPath`.

## Hop loop [B]
Loop induction `index` (`[r10-0x248]`), `count` (`[r10-0x308]`), `last` precomputed
(`[r10-0x2d0]`); previous-hop discriminant byte (`[r10-0x126]`, init 2 = None); event
authority bump captured once (`[r10-0x2d8]`). Per iteration calls the per-hop body `0xb70e`
which does `CurveHop::try_accounts`, `prepare_curve` (realloc fence `data_len >= 166`), the
curve-state requires, fee selection, reserve updates, token/lamport transfers and the
TradeEvent emit. After return it stitches `current_mint`, sets `previous`, `amount = output`,
`total_buyback += buyback`, `index++`; back-edge `af2d`.

## Per-hop fee flags [B]
`hop_fees[i]` is a 2-bit mask:
- bit 0 = protocol-fee leg active (also gates the buyback leg and the
  `preflight_buyback_recipient` check on `buyback_fee_recipient`).
- bit 1 = creator-fee leg active.
Rates from the shared `select_fees` (tier table by market cap; native/QUOTE_1/QUOTE_2 ->
`fee_tiers`, QUOTE_STABLE -> `stable_fee_tiers`, else exotic/flat); the corresponding bps are
zeroed when the bit is clear. Buyback = `pf*buyback_bps/10000`; `pf - buyback` accrues to
`protocol_fees`.

## Depth cap [B/R]
Execute `0xacfb` enforces only `len>=5`, `len%5==0`, `hop_fees.len==count`, `flags<4`. It
does **not** compare `count` to a max-depth global; `CurveDepthExceeded` (string
`0x1b8b51`) and `SetMaxCurveDepth` exist, so the cap is enforced by the **outer
router/dispatch** that invokes this execute, not here. The recovery also has no cap inside
the curve executor.

## CPIs [R]
Per hop: `transfer_checked` on the input leg and, on the last hop, the output leg to
`destination`; `system_transfer` on the native buy leg; `native_buyback`/`transfer_checked`
for the buyback leg; event self-CPI (`route_event`). All through the shared
invoke/recover thunks (not named syscalls inside `0xb70e`).

## Event + trailing field `+0x198` [B]
`TradeEvent` serializer `0x2c496` (disc `bddb7fd34ee661ee` at `0x2c4af`), called twice from
`route_event` (`bcd9` log, `bcec` CPI). `ix_name = "multi_hop_swap"` (`0x1b6ec8`, len 14).
Trailing field constructor `0x1177a`:
`1184c: ldxdw r1,[r10-0xe8]; 1184d: stxdw [r6+0x198],r1`; two writers of `[r10-0xfc8]`:
`bbbb` (native/SOL path, r9), `bcbb` (non-native/SPL, r8), both a computed checked
subtraction (`0x12a1c`) of a before/after quote amount. So
`TradeEvent +0x198 = quote_before_adapter - quote_after_adapter` (the per-hop quote value
withheld by the quote token program). It is 0 only for a lossless quote leg (native SOL or
Tokenkeg identity); the reconstruction hardcodes 0, so it diverges for Token-2022
transfer-fee quotes.

## Gaps
- Completion/migration mid-route, WSOL/non-native quote, Token-2022 extensions, holder/
  cashback/mayhem curves remain PARTIAL (spec 07).
- Depth cap lives in the outer router, not this function.
- `+0x198` adapter delta is unmodelled in the reconstruction.

---

# 2. pump_amm `multi_hop_swap` @ 0x1d2ec (byte 0xe9760)

## Purpose
Route `amount_in` across PumpSwap pools, optionally batching into Pump bonding-curve runs,
ending at `user_out_token_account`; require final output `>= min_amount_out`.

## Accounts [R] (`MultiHop`)
`user` signer, `user_in_token_account`, `user_out_token_account`, `global_config`,
`fee_config` (`["fee_config", pump_amm]` under fees), `user_volume_accumulator`
(`init_if_needed`, 137), `buyback_fee_recipient` (mut unchecked), `token_program`,
`token_2022_program`, `system_program`, event_authority, program, `pump_program`
(`6EF8...`), `pump_global`, `pump_fee_config`, `pump_event_authority`.
`remaining_accounts` is **5 per hop**:
`[base_mint, quote_mint, pool, pool_base_token_account, pool_quote_token_account]`.
`AmmHop` checks `has_one` base_mint/quote_mint/pool_base_token_account/
pool_quote_token_account; `pool` must be owned by pump_amm (`AccountTypeNotSupported`).

## Args [B]
`amount_in: u64`, `min_amount_out: u64` (arg codec `0x1d2ec`; two u64s).

## Direction / continuity [R]
Start `current_mint = user_in_token_account.mint`. For each 5-group:
`current_mint == group[1]` -> buy (output = group[0]); `current_mint == group[0]` -> sell
(output = group[1]); else `MultiHopDiscontinuousPath`. Every hop must have the same
direction (`MultiHopMixedDirection`). Terminal `current_mint ==
user_out_token_account.mint` (`MultiHopDiscontinuousPath`).

## Hop execution [R]
The loop walks the groups:
- **Pump-owned group** (`group[2].owner == PUMP`): batch all consecutive Pump groups into
  one `multi_hop_curve_swap` CPI. Input arguments: `amount` (u64) + `u32 flags.len()` + the
  flags bytes; program `PUMP`; accounts = pump `global`, pump fee config, pump_amm
  `global_config` (PDA signer), user, authority, source, destination,
  buyback recipient, token programs, system, pump event authority, pump program, then the
  raw hop accounts. Flags per hop: `protocol = if sell { j+1==count } else { j==0 }`,
  `creator = if sell { j==0 } else { j+1==count }` (bit0/bit1). The return data must be
  exactly 16 bytes (`MultiHopCurveRunMismatch`); `output = ret[0..8]`,
  `buyback = ret[8..16]`. The code checks the source/destination token balances against
  `source_before - current (+ output/buyback)` and `before + output (+ buyback)` to detect a
  misbehaving curve run.
- **AMM group** (`group[2].owner == pump_amm`): parse `AmmHop`, call `amm_hop(...)` with
  `minimum = if last { arg minimum } else { 0 }`, direction/first/last/prepaid/source/
  authority/seeds. After the hop, the source becomes the pool quote (sell) / base (buy) ATA,
  authority = pool, seeds = pool PDA, `prepaid = false`.

## AMM per-hop body (`amm_hop`) [R]
1. disable_flags: buy &8 (DisabledBuy 6020) / sell &16 (DisabledSell 6021).
2. `pool.creator == ["pool-authority", base_mint]` else OnlyPumpPools (6078).
3. `!pool.is_cashback_coin` (CashbackCoinNotSupported 6079); `!pool.is_mayhem_mode`
   (MayhemPoolNotSupported 6080).
4. rent/realloc pool to 287.
5. base/quote token programs chosen by mint owner (`AccountTypeNotSupported`).
6. `protocol_end` = sell ? last : first; `creator_end` = sell ? first : last. On
   `protocol_end` validate the named buyback recipient: owner == quote program (6027),
   token mint == quote mint (6009), owner in `global_config.buyback_fee_recipients`
   (643..899; 6053), ATA matches (6053).
7. Input transfer (unless prepaid/already at the vault): sell base user->pool or buy quote
   user->pool; `quote_transfer_fee` is computed for buy inputs. Reserve math:
   `received = amount - input_tf`; `b`/`raw_q` from pool vaults; `q = raw_q + virtual_quote`
   (i128 -> u64), `old_accrued = protocol+creator`, `q >= old_accrued`.
8. Fee selection `fees(a,h,q,b)` (fee_config len>=2512 -> FeeConfigTooShort 6083; tiers
   non-empty -> FeeTiersEmpty 6082; canonical/tier/exotic/flat selection; pool creator-fee
   override). End-hop flags: `!creator_end` -> lp+creator bps = 0; `!protocol_end` ->
   protocol bps = 0; creator_bps = 0 if coin_creator default.
9. Math: sell `curve = q*amount/(b+amount)`, fees, `total = curve - lp - protocol - creator`
   (must be >0); buy `estimate = received*10000/(10000+lp+protocol+creator)`, fees,
   `adjusted_estimate`, `curve = received - fees`, `adjusted = curve-1`,
   `out = b*adjusted/(q+adjusted)` (out>0, out<b). Slippage: sell total >= limit (6004);
   buy total <= limit? (the source's buy branch has `require!(total <= limit, 6004)` via the
   outer execute; see `trade.rs`).
10. Buyback: `buyback_bps = global_config.buyback_basis_points` (V2 has no mayhem zeroing);
    `buyback_fee = protocol*bps/10000`; `buyback_received = buyback - quote_transfer_fee`;
    `protocol_accrual = protocol - buyback`; `accrued = protocol_accrual + creator`.
11. Payout: on the last hop transfer the output to `user_out_token_account` (sell:
    quote from pool quote vault; buy: base from pool base vault, pool PDA signer). Accrue
    `pool.protocol_fees += protocol_accrual`, `pool.creator_fees += creator_fee`,
    `pool.virtual_quote_reserves -= accrued`. Transfer `buyback_fee` to the named buyback
    recipient if >0.
12. Emit the standard `BuyEvent`/`SellEvent` via the AMM event-CPI (`emit_event`, tag
    `e445a52e51cb9a1d` + `event.data`), with `ix_name` `"multi_hop_swap"` for buys; the
    token reserves/`quote_transfer_fee` tail as in `trade.rs`.

## Final checks
`require!(current >= minimum, ExceededSlippage)`; if `user_volume_accumulator.user ==
default` set it to the user. No depth cap in this function; `count = remaining.len()/5` and
`len % 5 == 0` (NotEnoughRemainingAccounts).

## Fee flags / depth / trailing field
- Per-hop fee flags are **computed**, not passed as an arg: protocol leg on the buy first /
  sell last hop; creator leg on the buy last / sell first hop; non-end hops zero the
  corresponding bps. Buyback is charged on the protocol-end hop.
- **Depth cap**: none in `multi_hop_swap`; the Pump curve run's depth cap is in the outer
  router (see Sec.1). The AMM has no `CurveDepthExceeded` check.
- **Trailing TradeEvent `+0x198`**: this is a **pump** `TradeEvent` field, not an AMM
  `BuyEvent`/`SellEvent` field. The AMM event's tail is `quote_transfer_fee`; the Pump
  curve-run's event carries the adapter delta for the curve batch (see Sec.1). Do not assume
  the AMM event has +0x198.

## Gaps [R]
- The AMM multi_hop source marks arbitrary hop counts, native/WSOL variants, other quote
  currencies, completion/migration, Token-2022 extensions and holder/cashback/mayhem modes
  incomplete; the Pump curve-run batching is covered only for ordinary Tokenkeg fixtures.
- The AMM's per-hop buyback is the named-account path; the Pump curve-run uses the raw
  writable buyback recipient passed through.
- No whole-byte identity.

---

## Cross-program summary

| | pump `multi_hop_curve_swap` | pump_amm `multi_hop_swap` |
|---|---|---|
| hop unit | 5 accounts = a Pump bonding curve | 5 accounts = a PumpSwap pool |
| batching | one call per curve hop from the outer loop | batches consecutive Pump groups into one `multi_hop_curve_swap` CPI |
| fee flags | `hop_fees: Vec<u8>` arg, bit0 protocol/bit1 creator | computed from first/last + direction |
| depth cap | not in this fn; `SetMaxCurveDepth`/`CurveDepthExceeded` live in the router | none |
| event trailing | `+0x198 = quote_before_adapter - quote_after_adapter` (pump TradeEvent) | AMM `Buy/SellEvent` tail `quote_transfer_fee` (no +0x198) |
| return | 16-byte `(amount_out, buyback)` | final `current >= minimum` |
