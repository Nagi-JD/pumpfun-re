# 05 — BUY handlers (deployed Pump.fun program)

Reverse-engineered from `evidence/original/pump/deployed.so` with `sbftool.py`
(addresses = **instruction indices**, as emitted by the tool), cross-read against the
reconstructed source in `programs/pump/src/`. Everything below marked **[BIN]** was
confirmed against the binary; **[SRC]** is the recovered-source behaviour; **[GAP]**
is a confirmed divergence between the two.

> Scope note: the binary's baked source-path table (see `REVERSE_ENGINEERING.md`)
> lists `programs/pump/src/buy.rs`, `trade_v3.rs`, `pump_quote.rs`,
> `util/constant_product.rs`, `util/fee.rs`, **`util/transfer_fee.rs`**. None of
> those files exist in the recovered `src/` tree — the recovered equivalents are
> `legacy_buy.rs` (= `buy.rs`), `trade.rs` (= `trade_v3.rs`), `buy_v2.rs`, and
> `trade_types.rs`. **`util/transfer_fee.rs` has no recovered counterpart at all.**
> That absence is the central transfer-fee gap documented per handler.

---

## Shared architecture (verified against the binary)

Each dispatched handler is a small Anchor entry **stub** (~130–220 insns) that: logs
the ix-name string, deserializes accounts via a shared account-parser, deserializes
args, then calls a per-variant business-logic function, then a per-variant
event-finalize function.

| handler | discr | stub @ | account-parse core | logic fn | TradeEvent emit/finalize fn | emit ix_name |
|---|---|---|---|---|---|---|
| `buy` (legacy)             | `66063d1201daebea` | `0x2549c` | `0x2dcfe` | (in core) | `0x29807` | `"buy"` |
| `buy_exact_sol_in`         | `38fc74089edfcd5f` | `0x25579` | `0x2dcfe` | (in core) | `0x29e9c` | `"buy_exact_sol_in"` |
| `buy_v2`                   | `b817ee6167c5d33d` | `0x24ea2` | `0x1486f`/`0x157cf` | (in core) | `0x27737` | `"buy"` |
| `buy_exact_quote_in_v2`    | `c2ab1c46684d5b2f` | `0x24f6b` | `0x1486f`/`0x157cf` | (in core) | `0x27ec6` (→`0x27f22`) | `"buy_exact_quote_in"` |
| `buy_v3`                   | `07051dc4f5176550` | `0x250d9` | `0x204af` | `0x28f74` | (shared v3 emit) | `"buy"` |
| `buy_exact_quote_in_v3`    | `e1f7501ed5b38488` | `0x25185` | `0x204af` | `0x2913f` | (shared v3 emit) | `"buy_exact_quote_in"` |

Shared leaf helpers seen in every stub/logic fn: `0x1412` (panic/err), `0x33e64`,
`0x366c2`/`0x366cf` (memcpy/alloc), `0x351cc`, `0x35649`, `0x2bbd1`, `0x33766`,
`0x359c3`.

**Shared event serializer** `0x2c496` (TradeEvent struct in `r2`); **shared
event-builder** `0x1177a`. The 18 serializer call-sites pair up as
`emit!`+`emit_cpi!` for each of the 9 event-emitting bodies.

**TradeEvent trailing field (struct offset `0x198`) = `unparsed_trailing_field: u64`.**
**[BIN]** It is written as the literal constant **0** immediately before serialization:
- legacy-buy emit `0x29807`: `0x29bc5: stdw [r10 -0x288], 0x0` feeds `[r2+0x198]` at both serializer sites `0x29bce`/`0x29be3`.
- buy_v2 emit `0x27737`: `0x27d56: stxdw [r10 -0x288], r1` (r1 = 0) feeds `[r2+0x198]` at `0x27d6b`/`0x27d81`.
So the recovered source's `unparsed_trailing_field: 0` is **faithful**; "uninterpreted"
in COMPLETION.md means only that the field's *semantic purpose* is unknown — its
emitted **value is a hardcoded `0`**, not a copy of any curve/global/clock field.

**Native (SOL) sentinel = WSOL** `So111...112` (rodata `0x1b5cc8`), loaded by **25**
`lddw` sites across the trade code. **USDC** `EPjFW...Dt1v` (rodata `0x1b5d28`) is loaded
by **exactly one** `lddw` in the whole `.text` (at `0x8a128`) and **does not appear in
the v3 trade core `0x204af` nor in `0x28f74`/`0x2913f`**. See the per-handler
transfer-fee/quote-route gaps — this is the proof the binary does **not** gate the
non-SOL quote on USDC the way the reconstruction does.

**spl-token-2022 is linked**, including the transfer-fee extension: rodata holds
`src/extension/transfer_fee/instruction.rs` (`0x1ba1e0`) and the extension-name
blob `TransferHook/NonTransferable/PermanentDelegate/...` (`0x1b64f6`).

---

## buy  (legacy) — `0x2549c`  discr `66063d1201daebea`

1. **Purpose / routes.** Legacy fixed-token-amount buy. **SOL/native quote ONLY**
   ([SRC] `LegacyBuy` forces `bonding_curve.quote_mint == Pubkey::default()` via the
   `UnsupportedQuoteMint` constraint). No SPL/Token-2022 quote route. [SRC] dispatch:
   `buy(amount, max_sol_cost, track_volume: OptionBool, partial_fill: OptionBool)`
   → `legacy_buy::execute(.., track, partial, exact=false)` (lib.rs:73).
2. **Accounts** (LegacyBuy): `global`(PDA `global`), `fee_recipient`(mut, unchecked),
   `mint`, `bonding_curve`(PDA `bonding-curve`+mint, `LegacyCurve`), `associated_bonding_curve`,
   `associated_user`, `user`(signer,mut), `system_program`, `token_program`,
   `creator_vault`(PDA `creator-vault`+creator), `event_authority`, `program`,
   `global_volume_accumulator`, `user_volume_accumulator`(init_if_needed, space 137),
   `fee_config`(PDA `fee_config`+ID @ FEE_PROGRAM), `fee_program`. Plus **2 remaining
   accounts**: `[0]`=`bonding-curve-v2` PDA, `[1]`=buyback recipient.
3. **Require order [SRC]** (binary core `0x2dcfe`): (a) rent-fund bonding curve +
   realloc to 166; (b) `NotAuthorized` — `fee_recipient` ∈ global recipients
   (mayhem→reserved set, else normal set); (c) `BuybackFeeRecipientMissing` if
   `remaining_accounts.len() < 2`; (d) `!complete` (`BondingCurveComplete`);
   (e) `input>0` (`BuyZeroAmount`); (f) `input <= real_token_reserves || partial`
   (`NotEnoughTokensToBuy`); later `InvalidBondingCurveV2` (rem[0] PDA),
   `BuybackFeeRecipientNotAuthorized` (rem[1]); slippage `TooMuchSolRequired`
   (`quote+pf+cf <= limit`). No cashback *rejection* (cashback coins route the
   creator fee to the user-volume accumulator instead).
4. **CPIs.** fee-program `invoke` (discr `[154,237,138,92,162,2,162,187,1]` + `cap` +
   quote_mint, accounts `[fee_config, ID]`) → `get_return_data` → `Fees`; base
   `transfer_checked` signed by the bonding-curve PDA (`bonding-curve`+mint+bump);
   SOL `system_program::transfer` legs for `{creator_dest, bonding_curve, buyback, fee_recipient}`;
   self event CPI (`emit_cpi!`). Shared helper `0x2e81a` + emit fn `0x29807`.
5. **Fee math.** `cap = token_total_supply·vqr/vtr`. `Fees` from fee-program; if
   `curve.creator_fee_bps>0` it overrides. `creator_bps = 0` if `creator==default`.
   `ceil_fee(q,bps) = (q·bps + 9999)/10000` (round-up). `quote = amount·vqr/(vtr-amount) + 1`.
   `pf = ceil_fee(quote,protocol_bps)`, `cf = ceil_fee(quote,creator_bps)`,
   `buyback_bps = 0 if mayhem else global.buyback_basis_points`,
   `bf = pf·buyback_bps/10000`; `fee_recipient` receives `pf-bf`, buyback receives `bf`.
   Cashback coins: creator fee → user_volume_accumulator + `cashback_earned += cf`.
6. **TradeEvent** (emit `0x29807`): native, so `sol_amount=quote`, `virtual/real_sol_reserves`
   set, `quote_mint=default`, `creator_fee_basis_points/creator_fee` zeroed when cashback
   coin (moved into `cashback*`), `track_volume=track`. **`[r2+0x198]` = literal 0**
   (`0x29bc5`). Completion: if `real_token_reserves==0` set `complete=true` and emit
   `CompleteEvent`.
7. **Gaps.** None material vs source for SOL-only. partial_fill: honored
   (`NotEnoughTokensToBuy` gate, `amount = computed.min(real_token_reserves)`) — same as [SRC].
   Transfer-fee: **N/A** (SOL-only path, no SPL quote).

---

## buy_exact_sol_in — `0x25579`  discr `38fc74089edfcd5f`

1. **Purpose / routes.** Legacy "spend exact SOL in" buy. **SOL/native ONLY** (same
   `LegacyBuy` accounts/constraint as `buy`). [SRC] `buy_exact_sol_in(spendable_sol_in,
   min_tokens_out, track_volume, partial_fill)` → `legacy_buy::execute(.., exact=true)`
   (lib.rs:74). [BIN] shares account-parse/logic core **`0x2dcfe`** with `buy`;
   differs only in the `exact` flag path and its own emit fn **`0x29e9c`**.
2. **Accounts.** Identical to `buy` (LegacyBuy) incl. the 2 remaining accounts.
3. **Require order [SRC].** Same prologue as `buy`, except the exact branch:
   `limit>0` (`BuyZeroAmount` — here `limit`=min_tokens_out) **then** `input>0`
   (`BuyNotEnoughSolToCoverFees`). Then `!complete`; the pre-math
   `NotEnoughTokensToBuy` is *skipped* for exact. After computing `raw_quote` it
   requires `raw_quote>0` (`BuyNotEnoughSolToCoverFees`), `computed<=real || partial`
   (`NotEnoughTokensToBuy`), and slippage
   `(partial && computed>real) || amount>=limit` (`BuySlippageBelowMinTokensOut`).
4. **CPIs.** Same as `buy` (fee-program invoke, base transfer_checked signed, SOL
   system transfers, self event CPI); emit fn `0x29e9c`.
5. **Fee math.** Budget inversion: `raw_quote = input·10000/(10000+protocol_bps+creator_bps)`;
   `adjusted = raw_quote-1` if `raw_quote+ceil_fee(raw_quote,pb)+ceil_fee(raw_quote,cb) > input`;
   `computed = vtr·(adjusted-1)/(vqr+(adjusted-1))`; `amount = computed.min(real)`;
   when not crossing `quote=adjusted`, `fq=raw_quote`; when crossing
   `quote = amount·vqr/(vtr-amount)+1`, `fq=quote`. `pf/cf = ceil_fee(fq,·)`;
   buyback as above.
6. **TradeEvent.** Same layout, `ix_name="buy_exact_sol_in"`; `[r2+0x198]=0`
   (emit `0x29e9c`, same literal-0 pattern as the shared emit fns).
7. **Gaps.** partial_fill honored (exact branch). Transfer-fee: **N/A** (SOL-only).

---

## buy_v2 — `0x24ea2`  discr `b817ee6167c5d33d`

1. **Purpose / routes.** v2 fixed-token-amount buy. **SOL native OR SPL/Token-2022
   quote** (quote selected by `bonding_curve.quote_mint`; native when `==default`,
   else must equal the configured quote mint). [SRC] `buy_v2(amount, max_sol_cost,
   partial_fill)` → `buy_v2::execute(.., exact=false)` (lib.rs:78).
2. **Accounts** (BuyV2): `global`, `base_mint`, `quote_mint`(InterfaceAccount Mint),
   base/quote token programs, `associated_token_program`, `fee_recipient`+
   `associated_quote_fee_recipient`(ATA), `buyback_fee_recipient`+`associated_quote_buyback_fee_recipient`,
   `bonding_curve`(`LegacyCurve`, constraint `quote_mint == (curve.quote_mint==default? WSOL : curve.quote_mint)` else `UnsupportedQuoteMint`),
   `associated_base_bonding_curve`, `associated_quote_bonding_curve`, `user`,
   `associated_base_user`, `associated_quote_user`, `creator_vault`+`associated_creator_vault`,
   `sharing_config`(PDA `sharing-config`+base_mint @ FEE_PROGRAM),
   `global_volume_accumulator`, `user_volume_accumulator`(init_if_needed space 137)+
   `associated_user_volume_accumulator`, `fee_config`(`LegacyFeeConfig`), `fee_program`,
   `system_program`, `event_authority`, `program`.
3. **Require order [SRC].** (a) init `user_volume_accumulator.user` if default; (b) if
   non-native quote: for each quote ATA require `owner != system_program`
   (`AccountNotInitialized`/`AccountTypeNotSupported`), `check_token` mint match,
   `associated_quote_user.owner == user`, and `create_idempotent` the
   fee/buyback/creator/user-vol ATAs; (c) `NotAuthorized` (fee_recipient membership,
   mayhem-aware); (d) `!complete`; (e) `input>0` (`BuyZeroAmount`);
   (f) `input<=real || partial` (`NotEnoughTokensToBuy`); then base transfer; then
   `BuybackFeeRecipientNotAuthorized`; slippage `TooMuchSolRequired`.
4. **CPIs.** fee-program `invoke` → `Fees` (same discr as legacy); `create_idempotent`
   (ATA program) for non-native quote; base `transfer_checked` signed by curve;
   per-leg quote `transfer_checked` (non-native) OR SOL `system_program::transfer`
   (native) for `{creator/user-vol, bonding_curve, fee_recipient(pf-bf), buyback(bf)}`;
   self event CPI; final rent top-up + realloc(166).
5. **Fee math.** `cap = token_total_supply·vqr/vtr`; `Fees` from fee-program (creator
   override, cashback zeroing identical to legacy); `quote = amount·vqr/(vtr-amount)+1`;
   `pf/cf = ceil_fee(fq,·)`; `buyback_bps=0 if mayhem`; `bf=pf·bps/10000`.
   Sharing: reads `SharingConfig` shareholders into the event.
6. **TradeEvent** (emit `0x27737`): includes real `fee_recipient`, `shareholders` vec,
   `total_unclaimed/claimed_tokens`, `current_sol_volume`, `last_update_timestamp`
   from the user-volume accumulator; native→`sol_amount/virtual_sol/real_sol` set.
   **`[r2+0x198]=0`** (`0x27d56` store, value 0). Completion event as usual.
7. **[GAP] Transfer-fee on the quote.** The non-native quote path uses plain
   `token_interface::transfer_checked(.., n, quote_mint.decimals)` for all quote legs
   and treats `quote`/`pf`/`cf` as the exact amounts received. **No Token-2022
   transfer-fee gross-up / `calculate_epoch_fee` is modelled** — the recovered tree
   has no `util/transfer_fee.rs`. The binary links the transfer-fee extension
   (`0x1ba1e0`), and the quote mint is a general `InterfaceAccount<Mint>` (any
   Token-2022 mint, not USDC-locked), so a fee-bearing quote mint would under-deliver
   to pool/recipients under the reconstructed logic. **CONFIRMED gap** (COMPLETION:
   "transfer-fee extensions remain unresolved").

---

## buy_exact_quote_in_v2 — `0x24f6b`  discr `c2ab1c46684d5b2f`

1. **Purpose / routes.** v2 "spend exact quote in". Same BuyV2 accounts and SOL/SPL
   quote routing as `buy_v2`. [SRC] `buy_exact_quote_in_v2(spendable_quote_in,
   min_tokens_out, partial_fill)` → `buy_v2::execute(.., exact=true)` (lib.rs:79).
   [BIN] shares the BuyV2 account-parse with `buy_v2`; distinct logic/emit entry
   `0x27ec6` (serializer fn `0x27f22`).
2. **Accounts.** Identical to `buy_v2` (BuyV2).
3. **Require order [SRC].** As `buy_v2`, exact branch: `limit>0` (`BuyZeroAmount`)
   then `input>0` (`BuyNotEnoughSolToCoverFees`); `!complete`; `raw_quote>0`
   (`BuyNotEnoughSolToCoverFees`); `computed<=real || partial` (`NotEnoughTokensToBuy`);
   slippage `(partial && computed>real) || amount>=limit` (`BuySlippageBelowMinTokensOut`).
4. **CPIs.** Same set as `buy_v2`.
5. **Fee math.** Budget inversion identical to `buy_exact_sol_in`
   (`raw_quote=input·10000/(10000+pb+cb)`, `adjusted`, `computed`, crossing branch),
   with per-leg quote transfers or SOL transfers.
6. **TradeEvent** (emit `0x27ec6`/`0x27f22`): `ix_name="buy_exact_quote_in"`;
   `[r2+0x198]=0`.
7. **[GAP] Transfer-fee on the quote.** Same as `buy_v2` — plain `transfer_checked`
   with `quote_mint.decimals`, no transfer-fee gross-up, no `util/transfer_fee.rs`.
   CONFIRMED gap for fee-bearing Token-2022 quote mints.

---

## buy_v3 — `0x250d9`  discr `07051dc4f5176550`

1. **Purpose / routes.** v3 fixed-token-amount buy on the `SellV3` (event_cpi)
   account layout. [SRC] `trade.rs::buy(amount, max_sol_cost)`. [SRC] restricts the
   non-SOL quote to **USDC only** via `check_quote` (anything else →
   `ReconstructionError::ReconstructionBranchUnsupported`). [BIN] stub `0x250d9`
   parses `(u64, u64, OptionBool)`, deserializes accounts via **`0x204af`**, then
   calls buy-v3 logic **`0x28f74`** (444 insns) — a *different* function from the
   exact-quote logic `0x2913f`.
2. **Accounts** (SellV3): `global`, `base_mint`, `quote_mint`(unchecked),
   base/quote token programs, `bonding_curve`(`BondingCurve`, PDA),
   `associated_base_bonding_curve`, `associated_quote_bonding_curve`(unchecked,mut),
   `user`(signer), `associated_base_user`, `associated_quote_user`(unchecked),
   `user_volume_accumulator`(unchecked), `fee_config`(unchecked, `owner==FEE_PROGRAM`,
   PDA `fee_config`+ID seeds::program=FEE_PROGRAM), `buyback_fee_recipient`(unchecked,mut),
   `system_program` (+ event_authority/program from `#[event_cpi]`).
3. **Require order [SRC].** `prepare_bonding_curve` (rent+realloc166) → `check_quote`
   → `!complete` (`BondingCurveComplete`) → `!is_cashback_coin`
   (`CashbackCoinNotSupported`) → `amount>0` (`BuyZeroAmount`) → if native,
   `buyback_fee_recipient ∈ global.buyback_fee_recipients`
   (`BuybackFeeRecipientNotAuthorized`). **Complete-is-checked-before-cashback** —
   matches COMPLETION's "admitted buy path rejects complete before cashback".
   Slippage `user_output <= max_sol_cost` (`TooMuchSolRequired`).
4. **CPIs.** v3 does **not** CPI the fee program — it reads `fee_config` account data
   in-process (`read_config`, discr `[143,52,146,187,219,123,76,155]`, len≥2512) and
   selects a tier locally. Base `transfer_checked` signed by curve; non-SOL: two quote
   `transfer_checked` legs (`user_output-buyback_fee` → pool, `buyback_fee` → buyback);
   SOL: `system_program::transfer(user_output)` to curve + `sub_lamports/add_lamports`
   buyback. Self event CPI (shared v3 emit using serializer `0x2c496`).
5. **Fee math.** `quote = amount·vqr/(vtr-amount) + 1` (checked; `Overflow`/
   `DivisionByZero`). `cap = buy_fee_market_cap`: **uses `mint.supply` (non-mayhem)
   or `token_total_supply` (mayhem)** · vqr/vtr — *note this differs from v2/legacy
   which always use `token_total_supply`*. `fees = selected(config, cap, stable=!is_sol)`;
   creator override; `creator_bps=0` if `creator==default`. `fee(q,bps)=(q·bps+9999)/10000`.
   `pf=fee(quote,pb)`, `cf=fee(quote,cb)`, `buyback_bps=0 if mayhem else global`,
   `bf=pf·bps/10000`, `retained=pf-bf`. `user_output = quote+pf+cf`.
6. **TradeEvent** (shared v3 emit, serializer `0x2c496`): `sol_amount/virtual_sol/
   real_sol = 0` when non-SOL; `fee_recipient=default`; `shareholders=[]`;
   `quote_mint=curve.quote_mint`; `holder_rewards*` from `is_holder_reward`.
   **`[r2+0x198]=0`** (same literal-0 trailing-field store pattern as the proven
   emit fns). Completion event when `real_token_reserves==0`.
7. **[GAP] partial_fill discarded.** [BIN] the stub **does parse** the trailing
   `OptionBool` partial_fill byte (`0x250ec: ldxb r1,[r2+0x10]` → stored `[r10-0x1c8]`)
   and passes it through the shared account-parse `0x204af`, **exactly like the
   exact-quote stub `0x25185`** (byte-parallel). But buy_v3's dedicated logic
   `0x28f74` is a distinct, smaller function than beqv3's `0x2913f`, and the plain
   fixed-amount buy reverts on `amount >= virtual_token_reserves` (denominator
   `vtr-amount` underflow) with no partial path. So partial_fill is **accepted and
   then inert** for buy_v3 — matching [SRC] `lib.rs:104`
   `buy_v3(..partial_fill:OptionBool){ let _ = partial_fill; trade::buy(..) }`.
   **CONFIRMED**: the arg is consumed off the wire and discarded.
   **[GAP] quote route / transfer-fee.** [SRC] hardcodes the non-SOL quote to USDC and
   uses plain `transfer_checked(.., decimals)`. [BIN] **USDC is loaded by only one
   `lddw` in the entire `.text` (`0x8a128`) and is absent from `0x204af`/`0x28f74`**;
   the v3 core only tests WSOL (`0x20891: lddw r2,0x1b5cc8`). The binary validates the
   non-SOL quote generally (against `bonding_curve.quote_mint` + the quote_control
   whitelist), so arbitrary Token-2022 quote mints are reachable and the baked
   `util/transfer_fee.rs` performs fee handling the reconstruction omits. The
   reconstruction's USDC-only `check_quote` is an **over-restriction**; the
   transfer-fee gross-up is **unmodelled**. CONFIRMED gap (COMPLETION: "other quote
   routes… and exhaustive extension/account validation remain incomplete").

---

## buy_exact_quote_in_v3 — `0x25185`  discr `e1f7501ed5b38488`

1. **Purpose / routes.** v3 "spend exact quote in", SellV3 layout. [SRC]
   `trade.rs::buy_exact_quote(spendable_quote_in, min_tokens_out, partial_fill)`
   (lib.rs:85). [BIN] stub `0x25185` is byte-parallel to buy_v3's stub (same arg
   parse, same `0x204af` account-parse) and calls exact-quote logic **`0x2913f`**
   (952 insns — ~2× buy_v3's `0x28f74`, reflecting the crossing/post-complete math).
2. **Accounts.** Identical SellV3 set as `buy_v3`.
3. **Require order [SRC].** `prepare_bonding_curve` → `check_quote` →
   `!is_cashback_coin` (`CashbackCoinNotSupported`) → `!complete`
   (`BondingCurveComplete`) → `min_tokens_out>0` (`BuyZeroAmount`) →
   `spendable_quote_in>0` (`BuyNotEnoughSolToCoverFees`) → native buyback-recipient
   membership. (Note: exact-quote checks **cashback before complete**, the reverse of
   `buy_v3`.) Fee-config: len≥8, discr match, `FeeConfig::deserialize`, len≥2512.
   Affordability `spendable·10000/(10000+pb+cb) > 0` (`BuyNotEnoughSolToCoverFees`);
   `NotEnoughTokensToBuy` unless `!exceeds || is_mayhem || partial_fill`; slippage
   `(exceeds && mayhem && partial_fill) || transfer_base >= min_tokens_out`
   (`BuySlippageBelowMinTokensOut`).
4. **CPIs.** Like buy_v3: in-process fee_config read (no fee-program CPI), base
   `transfer_checked` signed, quote legs `transfer_checked` or SOL transfer, self
   event CPI. Additionally emits `PostCompleteBuyEvent` on a crossing fill.
5. **Fee math.** Two-phase (pre-complete + post-complete "crossing"):
   `quote_budget = net_quote(spendable, pb, cb)`; `effective = quote_budget-1`;
   `computed_amount = vtr·effective/(vqr+effective)`; `amount = min(computed, real)`;
   `exceeds = computed>real`; `crossing = exceeds && !mayhem`. If crossing, the
   constant-product fill at the curve boundary plus a post-complete AMM leg against
   `real_quote_reserves`/`post_complete_*` is computed (`pool_base_before`,
   `pool_quote_before`, `post_quote`, `post_base`, `post_protocol`, `post_creator`,
   `post_buyback`), and `transfer_base = amount + post_base`. `fee(q,bps)` round-up as
   above; buyback as above. `creator_fee_unclaimed`/`post_complete_*` curve fields
   updated.
6. **TradeEvent** (shared v3 emit): `ix_name="buy_exact_quote_in"`; `[r2+0x198]=0`.
   Plus `CompleteEvent` (if `real==0`) and `PostCompleteBuyEvent` (if `crossing &&
   post_quote>0`).
7. **[GAP] partial_fill IS used here** (unlike buy_v3): gates
   `NotEnoughTokensToBuy`/`BuySlippageBelowMinTokensOut` in mayhem crossing. [BIN]
   confirmed the stub parses it and `0x2913f` is the consuming body.
   **[GAP] transfer-fee + other quote routes.** Same as buy_v3: [SRC] USDC-only
   `check_quote` + plain `transfer_checked(decimals)`, **no `util/transfer_fee.rs`**;
   [BIN] USDC not hardcoded in `0x204af`/`0x2913f` (only WSOL sentinel), general quote
   validation, transfer-fee extension linked. The gross-up for fee-bearing Token-2022
   quote mints and the nested/non-USDC routes are **unmodelled**. This is the single
   handler COMPLETION flags most explicitly: "configured creator fee/gross-spend
   truncation… Nested routes, transfer-fee extensions and exhaustive account
   validation remain unresolved." CONFIRMED gap.

---

## Summary of confirmed gaps (binary vs recovered source)

- **`util/transfer_fee.rs` entirely missing from the reconstruction.** The binary
  bakes that source path and links spl-token-2022's transfer-fee extension
  (`0x1ba1e0`). Every SPL/Token-2022 quote leg in `buy_v2`, `buy_exact_quote_in_v2`,
  `buy_v3`, `buy_exact_quote_in_v3` uses plain `transfer_checked(.., decimals)` with
  **no transfer-fee gross-up** → a fee-bearing quote mint under-delivers to
  pool/fee/buyback recipients under the reconstructed math.
- **Quote route over-restriction (v3).** Recovered `trade.rs::check_quote` hardcodes
  the non-SOL quote to **USDC** (`ReconstructionBranchUnsupported` otherwise). The
  binary does **not**: USDC is loaded by a single `lddw` in all of `.text` (`0x8a128`)
  and never in the v3 core `0x204af`/logic `0x28f74`/`0x2913f`; only the WSOL sentinel
  (`0x1b5cc8`, 25 sites) gates the native branch. The deployed program accepts any
  configured/whitelisted quote mint (quote_control module), so Token-2022 quote
  routes the reconstruction rejects are live on-chain.
- **`buy_v3` consumes-then-discards `partial_fill`.** [BIN] stub `0x250d9` parses the
  trailing `OptionBool` identically to the exact-quote stub and threads it through
  `0x204af`, but buy_v3's logic `0x28f74` never acts on it (plain fixed-amount buy
  reverts on over-draw). Matches `lib.rs:104` `let _ = partial_fill`. In
  `buy_exact_quote_in_v3` the same arg **is** load-bearing (mayhem crossing gates).
- **Trailing event field `0x198` resolved.** `TradeEvent.unparsed_trailing_field` is a
  **hardcoded `u64 0`** (proven: `0x29bc5 stdw [..],0x0` in legacy-buy emit `0x29807`;
  `0x27d56` in buy_v2 emit `0x27737`), emitted at serializer `0x2c496`. The source's
  `unparsed_trailing_field: 0` is correct; "uninterpreted" refers only to the unknown
  semantic purpose of the constant, not to any unresolved value source.
