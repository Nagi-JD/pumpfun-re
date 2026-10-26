> **[VERIFIED 2026-10-26]** There is NO PumpError enum revision mismatch. The recovered
> lib.rs enum matches the deployed binary exactly: index 3=TooLittleSolReceived(6003),
> 4=MintDoesNotMatchBondingCurve(6004), 5=BondingCurveComplete(6005), 10=AccountTypeNotSupported(6010),
> 22=SellZeroAmount(6022) — all confirmed by enumerating the recovered enum AND the deployed
> PumpError::name() table + raise-site counts. Any 'different revision / 6010-vs-6022 shift'
> statement below is SUPERSEDED and wrong. (The admin_cto guard-SET difference is a separate,
> real divergence — not about the error enum.)

# Trade-handler gate catalogs (ordered preconditions)

Private analysis for the user. Tags: **[B]** = confirmed in the deployed bytecode;
**[R]** = from the read-only reconstruction / repo specs; **[partial]** = inferred (reason
stated).

Scope: the trade entrypoints named in the backlog.
- pump: `buy`, `buy_exact_sol_in`, `buy_v2`, `buy_exact_quote_in_v2`, `buy_v3`,
  `buy_exact_quote_in_v3`, `sell`, `sell_v2`, `sell_v3`.
- pump_amm: `buy`, `sell`, `buy_v2`, `sell_v2` (+ `buy_exact_quote_in_v2` noted).

For each gate: **condition -> error -> what the harness must seed/pass**. "Gate order" is the
order in the recovered source, which the deployed behavior was cross-checked against; where the
binary-verified source spec gives an order, it is cited. The error **codes** are `6000+index`;
pump codes are from the reconstructed `PumpError` enum and are tagged [R] unless the repo spec
verified them in the binary (6003/6005 are [B]); AMM codes 6000..6088 were observed as
immediates in the deployed AMM ELF and are [B].

Handler/stub addresses are `sbftool` pc units (instruction indices), matching
`spec/05-buy.md`/`06-sell.md` and `amm_specs.md`.

**Pump error codes - do not trust the reconstructed enum for this capture.** Only
`NotAuthorized=6000` (admin spec), `TooLittleSolReceived=6003`, and
`MintDoesNotMatchBondingCurve=6005` are binary-verified; `AccountTypeNotSupported=6022` is
verified from `spec/06-sell.md`. NOTE (superseded): the reconstructed `PumpError` enum actually MATCHES the deployed binary
(e.g. it places `AccountTypeNotSupported` at 6010), so other pump gate codes below are marked
"pump code TBD": the error **name** is the reliable handle and the harness should record the
actual AnchorError code. AMM codes 6000..6088 are verified `.text` immediates.


---

# A. pump trade gates

## A.1 `buy` (legacy, SOL-only) - stub `0x2549c`, core `0x2dcfe`
disc `66063d1201daebea`; event emit `0x29807`; `ix_name="buy"`.

Accounts: `global` (`["global"]`), `fee_recipient`, `mint`, `bonding_curve`
(`["bonding-curve", mint]`, LegacyCurve), `associated_bonding_curve`, `associated_user`
(ATA mint+authority), `user` (signer), `system_program`, `token_program`, `creator_vault`
(`["creator-vault", creator]`), event/program, `global_volume_accumulator`,
`user_volume_accumulator` (init_if_needed 137), `fee_config` (`["fee_config", ID]` under fees),
`fee_program`. **2 remaining accounts: `[0]` = `bonding-curve-v2` PDA, `[1]` = buyback
recipient.**

| # | Gate | Error | Seed requirement | Tag |
|---:|---|---|---|---|
| 1 | rent-fund curve + `realloc(166)` | System/Rent errors | curve account exists; 166 bytes | [B] spec |
| 2 | `fee_recipient` in global fee set (mayhem -> reserved set, else `fee_recipients`) | NotAuthorized (6000 [B]) | valid `global.fee_recipient`/recipients; pass the matching fee recipient | [B] spec gate |
| 3 | `remaining_accounts.len() >= 2` | BuybackFeeRecipientMissing [pump code TBD] | pass rem[0], rem[1] | [B] spec gate |
| 4 | `!bonding_curve.complete` | BondingCurveComplete [pump code TBD] | curve `complete=false` (serialized offset 48) | [B] spec gate |
| 5 | `amount > 0` | BuyZeroAmount [pump code TBD] | buy arg > 0 | [R] |
| 6 | `amount <= real_token_reserves` unless `partial_fill` | NotEnoughTokensToBuy [pump code TBD] | curve real token reserves, or set partial | [R] |
| 7 | fee-program CPI `get_fees_with_quote_mint` -> `Fees` | fee-program errors | valid `fee_config` (fees-owned, disc `8f34...`, len>=2512) + fee_program | [B] spec |
| 8 | rem[0] = `["bonding-curve-v2", mint]` under pump | InvalidBondingCurveV2 [pump code TBD] | pass the PDA | [B] spec gate |
| 9 | rem[1] in `global.buyback_fee_recipients` (serialized Global **741..997**) | BuybackFeeRecipientNotAuthorized [pump code TBD] | seed the array with rem[1] | [B] spec gate + [B] 741 |
| 10 | `quote + pf + cf <= max_sol_cost` | TooMuchSolRequired [pump code TBD] | slippage limit | [R] |

Seed-to-reach-swap-math: valid `global` (PDA, initialized, fee recipients, buyback array at
741), curve (complete=false, quote_mint=default), mint, ATAs, `user_volume_accumulator` PDA,
fee_config (2512+ bytes), and `remaining=[bonding-curve-v2 PDA, buyback_owner]` with the owner
present in Global 741..997. The native-only constraint (`UnsupportedQuoteMint` [pump code TBD]) is via
`bonding_curve.quote_mint == default`.

## A.2 `buy_exact_sol_in` - stub `0x25579`, same core `0x2dcfe`, emit `0x29e9c`
Same accounts/remaining as `buy`; exact branch. Ordered gates: rent/realloc -> NotAuthorized
(fee recipient) -> remaining>=2 (BuybackFeeRecipientMissing) -> `!complete` ->
`limit>0` (BuyZeroAmount [pump code TBD]) -> `input>0` (BuyNotEnoughSolToCoverFees [pump code TBD]; the
pre-math NotEnoughTokensToBuy is skipped) -> raw_quote>0 (BuyNotEnoughSolToCoverFees [pump code TBD]) -> computed<=real ||
partial (NotEnoughTokensToBuy [pump code TBD]) -> rem[0] curve-v2 (InvalidBondingCurveV2 [pump code TBD]) -> rem[1] buyback
membership (BuybackFeeRecipientNotAuthorized [pump code TBD]) -> slippage `(partial && computed>real) || amount>=limit`
(BuySlippageBelowMinTokensOut [pump code TBD]). Seed identical to `buy`; `ix_name="buy_exact_sol_in"`.

## A.3 `buy_v2` - stub `0x24ea2`, account core `0x1486f`/`0x157cf`, emit `0x27737`
disc `b817ee6167c5d33d`; SOL native OR arbitrary quote (curve.quote_mint; default -> WSOL).
Accounts: `global`, `base_mint`, `quote_mint`, base/quote token programs, ATA program,
`fee_recipient` + quote ATA, `buyback_fee_recipient` + quote ATA, `bonding_curve`
(LegacyCurve, constraint quote_mint == curve quote/default), pool base/quote ATAs, `user`,
user base/quote ATAs, `creator_vault` + quote ATA, `sharing_config`
(`["sharing-config", base_mint]` under fees), `global_volume_accumulator`,
`user_volume_accumulator` (137) + quote ATA, `fee_config`, `fee_program`, system, event/program.

| # | Gate | Error | Seed requirement | Tag |
|---:|---|---|---|---|
| 1 | init `user_volume_accumulator.user` if default | - | PDA 137 bytes | [R] |
| 2 | non-native quote: quote ATAs not system-owned; `check_token` mint match; user ATA owner==user; `create_idempotent` fee/buyback/creator/user-vol ATAs | AccountNotInitialized / AccountTypeNotSupported (6022 [B]) / MintDoesNotMatchBondingCurve (6005 [B]) | valid quote mint/ATAs + ATA program | [R] |
| 3 | `fee_recipient` membership | NotAuthorized (6000 [B]) | global recipients | [R] |
| 4 | `!bonding_curve.complete` | BondingCurveComplete [pump code TBD] | complete=false | [R] |
| 5 | `input > 0` | BuyZeroAmount [pump code TBD] | arg | [R] |
| 6 | `input <= real_token_reserves` unless partial | NotEnoughTokensToBuy [pump code TBD] | reserves/partial | [R] |
| 7 | fee-program `get_fees_with_quote_mint` CPI | fee errors | fee_config 2512+ | [B] spec |
| 8 | buyback recipient membership in `global.buyback_fee_recipients` (741..997) | BuybackFeeRecipientNotAuthorized [pump code TBD] | seed the array, pass the named buyback account | [R] |
| 9 | `quote + pf + cf <= max_sol_cost` | TooMuchSolRequired [pump code TBD] | slippage | [R] |

Seed: native or a valid non-native quote mint/ATAs; curve complete=false; fee_config; the named
buyback recipient must be in Global 741..997. Note: the buyback is a **named account** here
(not two remaining accounts); the BuybackFeeRecipientNotAuthorized check is on the named account key.

## A.4 `buy_exact_quote_in_v2` - stub `0x24f6b`, emit `0x27ec6`/`0x27f22`
Identical accounts/gates to `buy_v2`; exact branch: `limit>0` (BuyZeroAmount) -> `input>0`
(BuyNotEnoughSolToCoverFees [pump code TBD]) -> `!complete` -> raw_quote>0 (BuyNotEnoughSolToCoverFees [pump code TBD]) -> computed<=real||partial
(NotEnoughTokensToBuy) -> buyback membership (BuybackFeeRecipientNotAuthorized [pump code TBD]) -> slippage
`(partial && computed>real) || amount>=limit` (BuySlippageBelowMinTokensOut [pump code TBD]). `ix_name="buy_exact_quote_in"`.

## A.5 `buy_v3` - stub `0x250d9`, accounts `0x204af`, logic `0x28f74`
disc `07051dc4f5176550`; SellV3 event_cpi layout; non-SOL quote is general in the binary
(USDC is not hardcoded; `spec/05-buy.md`). Accounts: `global`, `base_mint`, `quote_mint`,
base/quote token programs, `bonding_curve` (PDA), pool base/quote ATAs, `user` + base/quote
ATAs, `user_volume_accumulator`, `fee_config` (owner=fees, `["fee_config", ID]`), named
`buyback_fee_recipient`, system; event/program.

| # | Gate | Error | Seed requirement | Tag |
|---:|---|---|---|---|
| 1 | rent + realloc curve 166 | Rent/System | 166-byte curve | [B] spec |
| 2 | `check_quote` (native WSOL; non-native against curve quote + quote_control whitelist) | UnsupportedQuoteMint / InvalidQuoteControl [pump codes TBD] | valid quote mint/program; whitelist entry | [B] behavior, [R] codes |
| 3 | `!bonding_curve.complete` | BondingCurveComplete [pump code TBD] | complete=false | [B] spec (order) |
| 4 | `!is_cashback_coin` | CashbackCoinNotSupported [pump code TBD] | curve cashback=false | [B] spec (order) |
| 5 | `amount > 0` | BuyZeroAmount [pump code TBD] | arg | [R] |
| 6 | native: `buyback_fee_recipient` in `global.buyback_fee_recipients` (741..997) | BuybackFeeRecipientNotAuthorized [pump code TBD] | seed array; named buyback account | [R] |
| 7 | fee_config read (local): len>=2512 | FeeConfigTooShort [pump code TBD] | 2512+ fee_config | [B] spec |
| 8 | fee-tier selection: non-empty tiers | FeeTiersEmpty [pump code TBD] | tiers in fee_config | [R] |
| 9 | `user_output <= max_sol_cost` | TooMuchSolRequired [pump code TBD] | slippage | [R] |

Note: `buy_v3` parses and **discards** `partial_fill` (inert) [B] (`spec/05-buy.md`).

## A.6 `buy_exact_quote_in_v3` - stub `0x25185`, accounts `0x204af`, logic `0x2913f`
Same SellV3 accounts. Ordered gates (note cashback is checked **before** complete here):
prepare/rent -> `check_quote` -> `!is_cashback_coin` (CashbackCoinNotSupported [pump code TBD]) -> `!complete` ->
`min_tokens_out>0` (BuyZeroAmount [pump code TBD]) -> `spendable_quote_in>0` (BuyNotEnoughSolToCoverFees [pump code TBD]) -> native buyback membership (BuybackFeeRecipientNotAuthorized [pump code TBD]) -> fee_config len>=8/disc/deserialize/len>=2512
(FeeConfigTooShort [pump code TBD]) -> affordability `spendable*10000/(10000+pb+cb) > 0` (BuyNotEnoughSolToCoverFees [pump code TBD]) -> NotEnoughTokensToBuy
unless `!exceeds || is_mayhem || partial_fill` -> slippage `(exceeds && mayhem &&
partial_fill) || transfer_base >= min_tokens_out` (BuySlippageBelowMinTokensOut [pump code TBD]). Partial fill IS used here (mayhem
crossing) [B]. Seed a 2512+ fee_config, complete=false, cashback=false, native/quoted curve,
and the buyback recipient in Global 741..997 for native.

## A.7 `sell` (legacy, SOL-only) - stub `0x25656`, worker `0x2a511`
Accounts: `global`, `fee_recipient`, `mint`, `bonding_curve` (`["bonding-curve", mint]`,
native constraint `quote_mint==default` -> UnsupportedQuoteMint), pool/user ATAs, `user`
(signer), `creator_vault`, token/fee programs, event. Remaining: `[0]` =
user_volume_accumulator **only if cashback**; then `bonding-curve-v2` PDA; then
`buyback_fee_recipient`.

Order: rent top-up -> NotAuthorized (fee recipient) -> BondingCurveComplete ->
SellZeroAmount [pump code TBD] -> NotEnoughTokensToSell [pump code TBD] -> fee-program CPI ->
**TooLittleSolReceived (`0x1773` = 6003 [B], site `0x2a682`)** -> base transfer ->
cashback/curve-v2/buyback remaining checks -> payout -> event. Slippage minimum is on **gross**
`output = quote - pf - cf` (no Token-2022 fee; nested quote is SOL-only).

Seed: native curve, complete=false, user token ATA, creator vault, fee_config; for the
remaining accounts pass the curve-v2 PDA and a buyback recipient in the configured set; the
cashback prefix only for cashback curves.

## A.8 `sell_v2` - stub `0x25034`, worker `0x288a1`
General quote (native + any curve quote, incl. Token-2022). Accounts: `global`, base/quote
mints, base/quote token programs, `bonding_curve`, associated base/quote bonding ATAs,
`user` signer, associated base/quote user ATAs, user_volume_accumulator, fee/ATA programs,
`creator_vault`/sharing config, fee_config, named `buyback_fee_recipient`, system, event.
Order: volume init -> (non-native) quote ATAs not system-owned + `check_token` mint match
(MintDoesNotMatchBondingCurve 6005 [B]; AccountTypeNotSupported 6022 [B]) + `create_idempotent` 4
dest ATAs -> rent top-up -> NotAuthorized -> BondingCurveComplete -> SellZeroAmount [pump code TBD] ->
NotEnoughTokensToSell [pump code TBD] -> fee-program CPI -> fee math -> **TooLittleSolReceived
(`0x1773`, site `0x28bd7`) [B]** -> base transfer -> BuybackFeeRecipientNotAuthorized [pump code TBD]
-> payout -> state -> emit. Minimum is compared to **gross** `output=quote-pf-cf`; no
Token-2022 transfer-fee netting/harvest in the worker [B] (`spec/06-sell.md`).

Seed: same as sell; non-native quote needs the 4 destination quote ATAs (or let the handler
create them idempotently) and the named buyback recipient in Global 741..997.

## A.9 `sell_v3` - stub `0x25231`, accounts `0x204af`, worker `0x29515`
WSOL/USDC-only per the recovered `check_quote` (the binary is general for buy_v3; for sell_v3
the spec says USDC/WSOL). Order: prepare (rent/realloc 166) -> `check_quote` ->
CashbackCoinNotSupported [pump code TBD] -> BondingCurveComplete -> SellZeroAmount [pump code TBD] ->
NotEnoughTokensToSell [pump code TBD] -> native buyback membership (BuybackFeeRecipientNotAuthorized [pump code TBD]) -> fee_config read
(len>=2512, FeeTiersEmpty [pump code TBD]) -> fee math -> **TooLittleSolReceived (`0x1773`, site
`0x29622`) [B]** -> base transfer -> payout. Fees from local FeeConfig tiers; no fee-program
CPI. Seed: curve complete=false, non-cashback, fee_config 2512+, quote WSOL/USDC, buyback
recipient for native.

---

# B. pump_amm (PumpSwap) trade gates

AMM error codes are [B] (immediates 6000..6088 observed; see `amm_specs.md`). Gate order is
from the reconstruction (`legacy_buy.rs`/`legacy_sell.rs`/`trade.rs`); the repo harness has
verified create_pool/deposit/withdraw and is now working through buy/sell.

## B.1 `buy` (legacy) - arg codec `0x1cec9` (byte `0xe7648`)
Accounts (`LegacyBuy`): pool (four `has_one`s), user signer, global_config, base/quote mints,
user base/quote ATAs, pool base/quote ATAs, protocol_fee_recipient + quote ATA
(init_if_needed), base/quote token programs, system, ATA program, event/program,
coin_creator_vault_ata (init_if_needed), coin_creator_vault_authority
(`["creator_vault", pool.coin_creator]`), global_volume_accumulator,
user_volume_accumulator (init_if_needed 137), fee_config (`["fee_config", pump_amm]` under
fees), fee_program.

| # | Gate | Error | Seed requirement | Tag |
|---:|---|---|---|---|
| 1 | `global_config.disable_flags & 8 == 0` | DisabledBuy (6020) | flags | [B] code |
| 2 | pool len<287 -> rent + realloc | Rent/System | 287-byte pool | [R] |
| 3 | `protocol_fee_recipient` in configured set (mayhem reserved vs normal) | InvalidProtocolFeeRecipient (6013) | global_config recipients; pass a member | [R] |
| 4 | `(exact? limit: amount) > 0` | ZeroBaseAmount (6001) | args | [R] |
| 5 | `(exact? amount: limit) > 0` | ZeroQuoteAmount (6002) | args | [R] |
| 6 | exact: `available = amount - quote_transfer_fee > 0` | BuyNotEnoughQuoteTokensToCoverFees (6039) | enough quote; no fee-bearing edge | [R] |
| 7 | `pool_quote.amount >= protocol_fees+creator_fees` | Overflow (6023) | pool quote vault >= accrued | [R] |
| 8 | non-exact: `amount <= pool_base.amount` | BuyMoreBaseAmountThanPoolReserves (6016) | base vault; else use exact | [R] |
| 9 | fees CPI `get_fees_with_quote_mint` (fees program, disc bytes `154,237,138,92,162,2,162,187`; accounts `[fee_config, pump_amm]`) | fee-program errors | valid fee_config (fees-owned, len>=2512) | [R] |
| 10 | exact: estimate>0 (6039); out>=limit (6040); non-exact: `total<=limit` | BuyNotEnoughQuoteTokensToCoverFees / BuySlippageBelowMinBaseAmountOut / ExceededSlippage (6039/6040/6004) | slippage/limit | [R] |
| 11 | transfer fees / buyback: `pool-v2` PDA + buyback owner + ATA; owner in `global_config.buyback_fee_recipients` (serialized **643..899**) | InvalidPoolV2 (6062), BuybackFeeRecipientMissing (6058), BuybackFeeRecipientNotAuthorized (6053) | pass remaining accounts; seed 643..899 | [B] sites, [R] order |

**Buyback gate (critical):** see `amm_buyback_gate.md`. Positions depend on
creator_fee/cashback: non-cashback `creator_fee==0` -> `[owner, ata]`; `creator_fee>0` ->
`[pool-v2, owner, ata]`; cashback shifts further. The 6058 at `buy.rs:116` is the missing
owner/dest; 6053 is the array/ATA rejection. `buyback_basis_points` (899..907) does not gate
the account requirement.

Seed-to-reach-swap-math: pump_amm-owned `global_config` (949 bytes; recipients, flags=0,
buyback array at 643), `pool` (287, has_one keys, accrued fees <= quote vault), mint/ATAs,
fee_config 2512+, user_volume_accumulator 137, and the applicable buyback remaining accounts.

## B.2 `sell` (legacy) - arg codec `0x1d099` (byte `0xe84c8`)
Accounts (`LegacySell`): same as buy minus global/user volume accounts; includes
fee_config/fee_program.

| # | Gate | Error | Seed requirement | Tag |
|---:|---|---|---|---|
| 1 | `disable_flags & 16 == 0` | DisabledSell (6021) | flags | [B] code |
| 2 | pool len<287 -> rent/realloc | Rent/System | 287-byte pool | [R] |
| 3 | `protocol_fee_recipient` membership | InvalidProtocolFeeRecipient (6013) | recipients | [R] |
| 4 | `amount > 0` | ZeroBaseAmount (6001) | arg | [R] |
| 5 | fees CPI `get_fees_with_quote_mint` | fee errors | fee_config 2512+ | [R] |
| 6 | `pool_quote.amount - accrued >= quote - lp_fee` | InsufficientRealQuoteReserves (6063) | real quote reserves | [R] |
| 7 | `quote - lp - protocol - creator >= limit` | ExceededSlippage (6004) | limit | [R] |
| 8 | base transfer user->pool; quote payouts (pool PDA signer); buyback named/remaining checks | token errors; 6057/6058/6053 as buy | token accounts + buyback | [R] |

Seed: pool with accrued <= quote vault, complete flags not relevant to legacy sell, fee_config,
user base ATA + pool ATAs, quote program, recipient/creator/buyback accounts. Native SOL is
not used in AMM legacy sell (quote is the pool quote mint; WSOL is a normal token account).

## B.3 `buy_v2` - arg codec `0x1d15d` (byte `0xe8ae8`)
Accounts (`TradeV2`): pool (four `has_one`s), user signer, global_config, base/quote mints,
user/pool base+quote ATAs, base/quote token programs, system, user_volume_accumulator
(init_if_needed 137), fee_config (`["fee_config", pump_amm]`), named `buyback_fee_recipient`
(mut unchecked), event/program.

| # | Gate | Error | Seed requirement | Tag |
|---:|---|---|---|---|
| 1 | `disable_flags & 8 == 0` | DisabledBuy (6020) | flags | [B] |
| 2 | prepare: pool realloc 287 | Rent/System | 287 pool | [R] |
| 3 | `!pool.is_cashback_coin` | CashbackCoinNotSupported (6079) | cashback=false | [B] |
| 4 | buyback account owner == quote token program | AccountTypeNotSupported (6027) | valid token account | [B] |
| 5 | buyback token mint == quote_mint | InvalidQuoteMint (6009) | mint match | [B] |
| 6 | buyback owner in `global_config.buyback_fee_recipients` (643..899) | BuybackFeeRecipientNotAuthorized (6053) | seed 643..899 | [B] code, [R] offset |
| 7 | buyback ATA address matches `(owner, quote_program, quote_mint)` | BuybackFeeRecipientNotAuthorized (6053) | correct ATA | [B] |
| 8 | user_volume_accumulator.user default -> set to user | - | 137-byte PDA | [R] |
| 9 | `amount>0`, `limit>0`, `amount<=b` | ZeroBaseAmount 6001 / ZeroQuoteAmount 6002 / BuyMoreBaseAmountThanPoolReserves 6016 | args/pool | [R] |
| 10 | fee_config len>=2512 (fees()) | FeeConfigTooShort (6083) | fee_config 2512+ | [B] |
| 11 | fee tiers non-empty | FeeTiersEmpty (6082) | tiers | [B] |
| 12 | `total <= limit` (buy) | ExceededSlippage (6004) | slippage | [R] |
| 13 | post-CPI: overall/coin risk limits | OverallRiskExceeded (6006) / CoinRiskExceeded (6007) | global limits, counters | [R] |

Seed: `pool.is_cashback_coin=false`, `fee_config` with tiers (2512+), buyback owner at
643..899 and its correct ATA as the **named** `buyback_fee_recipient` (not a remaining
account), user volume PDA, base/quote ATAs. Note: V2 has no fees-program CPI; it reads
fee_config directly.

## B.4 `sell_v2` - arg codec `0x1d267` (byte `0xe9338`)
Same `TradeV2` context/prepare gates as `buy_v2` (1-8). Then: `amount>0` (ZeroBaseAmount 6001);
fee_config/tiers (6083/6082); curve quote; `quote - lp - protocol - creator >= limit`
(6004); `quote - lp <= real_quote` (InsufficientRealQuoteReserves 6063); transfer base
user->pool and quote pool->user; buyback payout; accrue protocol/creator fees; event. No
post-CPI risk check. Seed: same as buy_v2, with base tokens in the user ATA and a valid
buyback.

## B.5 `buy_exact_quote_in_v2` - arg codec `0x1d1e2` (byte `0xe8f10`)
Same TradeV2 context/prepare gates; exact branch: `limit>0`, `amount>0`, `available = amount -
quote_transfer_fee`, estimate>0 (6039), out>=limit (6040); buyback/accrual/risk as buy_v2.

---

# C. Cross-cutting notes

- **AMM vs pump buyback source is different.** Pump: `remaining[0]` = curve-v2 PDA,
  `remaining[1]` = buyback recipient, array at Global **741..997**. AMM legacy: two remaining
  accounts (owner + owner ATA) after the creator-fee/pool-v2 prefix, array at GlobalConfig
  **643..899**; AMM V2: buyback is a **named** account (prepared via 6053/6027/6009), not a
  remaining account.
- **Positions depend on creator fee.** In both programs, the buyback remaining-account index
  shifts when `creator_fee > 0` (the curve-v2/pool-v2 account is consumed first) and further
  for cashback coins. Compute `creator_bps` from the fee program response (pump fees CPI) or
  the local fee config (AMM V2) before choosing the index.
- **Slippage on sell is gross.** Pump and AMM sell compare the pre-Token-2022-fee
  `output/quote - lp - protocol - creator` against the minimum; the Token-2022 program then
  skims the quote transfer. This is present in both the deployed binary and the reconstruction
  (not a reconstruction gap); `sell_v2` does not harvest withheld fees.
- **pump_v3 quote routes.** The reconstruction over-restricts non-SOL quotes to USDC; the
  binary validates the general curve quote/quote_control whitelist (USDC is not hardcoded in
  the v3 core). For a harness, seed a whitelisted quote and its `QuoteControl` entry; do not
  assume USDC-only.
- **Error-code caveat (pump).** The reconstructed `PumpError` enum may be a slightly different
  revision: the binary-verified `TooLittleSolReceived=6003` and
  `MintDoesNotMatchBondingCurve=6005` are [B], but several [R] codes above should be confirmed
  from the harness's AnchorError before being treated as authoritative. AMM codes 6000..6088
  are [B] immediates.
- **Reaching swap math.** For every handler above, the last gate before the curve/constant-
  product arithmetic is the fee-program response (pump/legacy AMM) or local fee-config/tier
  selection (AMM V2, pump v3). Seed a 2512+ byte fees-owned `FeeConfig` (disc
  `8f3492bbdb7b4c9b`) with non-empty tiers, valid global config/recipients, a curve/pool with
  the `has_one` keys and non-complete state, and the applicable buyback accounts. Then the
  first arithmetic gate (zero amount, real reserves, slippage) is reached.
