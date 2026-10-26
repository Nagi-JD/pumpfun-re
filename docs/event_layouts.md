# Event struct layouts (deployed programs)

Private analysis for the user. Tags: **[B]** = confirmed in the deployed bytes / serializer
site; **[R]** = from the reconstruction / cluster specs; **[partial]** = inferred.

Rule: Anchor event data = **8-byte event discriminator + Borsh fields in declaration order**,
tightly packed (no alignment padding). `emit!` logs `event.data()`; `emit_cpi!` self-CPIs
`tag e445a52e51cb9a1d + event.data()`. Offsets below include the 8-byte discriminator.
The AMM's `emit_event` uses the same tag + `event.data()` (the AMM event disc is the first
8 bytes of `event.data()`).

Serializer/emit sites: pump TradeEvent `0x2c496` (disc `bddb7fd34ee661ee` at `0x2c4af`);
pump CreateEvent `0x2c2cf`; AMM `emit_event` (tag, event-CPI); mayhem events per
`mayhem_specs.md`. Full disc catalogs are in `discriminators.md`.

---

## 1. pump `TradeEvent` (the trade event, 37 fields)

Source: `programs/pump/src/trade_types.rs`; serializer `0x2c496`; in-memory trailing field at
`+0x198` (spec 07, `0x1184d: stxdw [r6+0x198], r1`). Field order and serialized offsets:

| Off | Field | Type |
|---:|---|---|
| 8 | mint | Pubkey |
| 40 | sol_amount | u64 |
| 48 | token_amount | u64 |
| 56 | is_buy | bool |
| 57 | user | Pubkey |
| 89 | timestamp | i64 |
| 97 | virtual_sol_reserves | u64 |
| 105 | virtual_token_reserves | u64 |
| 113 | real_sol_reserves | u64 |
| 121 | real_token_reserves | u64 |
| 129 | fee_recipient | Pubkey |
| 161 | fee_basis_points | u64 |
| 169 | fee | u64 |
| 177 | creator | Pubkey |
| 209 | creator_fee_basis_points | u64 |
| 217 | creator_fee | u64 |
| 225 | track_volume | bool |
| 226 | total_unclaimed_tokens | u64 |
| 234 | total_claimed_tokens | u64 |
| 242 | current_sol_volume | u64 |
| 250 | last_update_timestamp | i64 |
| 258 | ix_name | String: u32 len + L bytes |
| 262+L | mayhem_mode | bool |
| 263+L | cashback_fee_basis_points | u64 |
| 271+L | cashback | u64 |
| 279+L | buyback_fee_basis_points | u64 |
| 287+L | buyback_fee | u64 |
| 295+L | shareholders | Vec: u32 len + 34*n bytes (n entries) |
| 299+L+34n | quote_mint | Pubkey |
| 331+L+34n | quote_amount | u64 |
| 339+L+34n | virtual_quote_reserves | u64 |
| 347+L+34n | real_quote_reserves | u64 |
| 355+L+34n | holder_rewards_bps | u64 |
| 363+L+34n | holder_rewards | u64 |
| 371+L+34n | creator_fee_unclaimed | u64 |
| **379+L+34n** | **unparsed_trailing_field** | **u64** |

- Total = `387 + L + 34n` bytes (e.g. a `"buy"` event with no shareholders = 390 B).
- The **trailing field** is the last u64; its in-memory struct offset is **`+0x198`**
  (absolute struct base), while the serialized offset is `379+L+34n` (the two are different
  layouts). In the multi-hop curve executor the value is the per-hop
  `quote_before_adapter - quote_after_adapter` (non-zero for lossy Token-2022 quotes); in the
  normal buy/sell paths the constructor writes literal 0 [B spec 05/07].
- `Shareholder` is 34 B (Pubkey 32 + share_bps u16).

## 2. pump_amm `BuyEvent` / `SellEvent`

Source: `programs/pump-amm/src/trade.rs`. The AMM events are emitted by `emit_event` as
`tag e445a52e51cb9a1d + event.data()` (log + self-CPI); the event disc is the first 8 bytes of
`event.data()`.

### BuyEvent (40 fields; `ix_name: String`)

| Off | Field | Type |
|---:|---|---|
| 8 | timestamp | i64 |
| 16 | base_amount_out | u64 |
| 24 | max_quote_amount_in | u64 |
| 32 | user_base_token_reserves | u64 |
| 40 | user_quote_token_reserves | u64 |
| 48 | pool_base_token_reserves | u64 |
| 56 | pool_quote_token_reserves | u64 |
| 64 | quote_amount_in | u64 |
| 72 | lp_fee_basis_points | u64 |
| 80 | lp_fee | u64 |
| 88 | protocol_fee_basis_points | u64 |
| 96 | protocol_fee | u64 |
| 104 | quote_amount_in_with_lp_fee | u64 |
| 112 | user_quote_amount_in | u64 |
| 120 | pool | Pubkey |
| 152 | user | Pubkey |
| 184 | user_base_token_account | Pubkey |
| 216 | user_quote_token_account | Pubkey |
| 248 | protocol_fee_recipient | Pubkey |
| 280 | protocol_fee_recipient_token_account | Pubkey |
| 312 | coin_creator | Pubkey |
| 344 | coin_creator_fee_basis_points | u64 |
| 352 | coin_creator_fee | u64 |
| 360 | track_volume | bool |
| 361 | total_unclaimed_tokens | u64 |
| 369 | total_claimed_tokens | u64 |
| 377 | current_sol_volume | u64 |
| 385 | last_update_timestamp | i64 |
| 393 | min_base_amount_out | u64 |
| 401 | ix_name | String: u32 + L bytes |
| 405+L | cashback_fee_basis_points | u64 |
| 413+L | cashback | u64 |
| 421+L | buyback_fee_basis_points | u64 |
| 429+L | buyback_fee | u64 |
| 437+L | virtual_quote_reserves | i128 |
| 453+L | can_boost | bool |
| 454+L | base_supply | u64 |
| 462+L | holder_rewards_bps | u64 |
| 470+L | holder_rewards | u64 |
| 478+L | creator_fee_unclaimed | u64 |
| 486+L | quote_transfer_fee | u64 |
| total | `494 + L` | |

### SellEvent (34 fields, fixed)

Same as BuyEvent but the sell fields/order; total **449 bytes**:

8 timestamp, 16 base_amount_in, 24 min_quote_amount_out, 32 user_base, 40 user_quote,
48 pool_base, 56 pool_quote, 64 quote_amount_out, 72 lp_fee_bps, 80 lp_fee,
88 protocol_fee_bps, 96 protocol_fee, 104 quote_amount_out_without_lp_fee,
112 user_quote_amount_out, 120 pool, 152 user, 184 user_base_ata, 216 user_quote_ata,
248 protocol_fee_recipient, 280 protocol_fee_recipient_ata, 312 coin_creator,
344 coin_creator_fee_bps, 352 coin_creator_fee, 360 cashback_fee_bps, 368 cashback,
376 buyback_fee_bps, 384 buyback_fee, 392 virtual_quote_reserves (i128), 408 can_boost,
409 base_supply, 417 holder_rewards_bps, 425 holder_rewards, 433 creator_fee_unclaimed,
441 quote_transfer_fee; total 449.

## 3. mayhem events

### SellEvent (also used for buys with `side=0`) - **303 bytes** [B]
Source `programs/mayhem/src/instructions/sell.rs`; override disc `31487b2d6e40b085` (the
historical event type name is not recovered).

| Off | Field | Type |
|---:|---|---|
| 8 | side | u8 |
| 9 | sol_vault | Pubkey |
| 41 | mint | Pubkey |
| 73 | sol_amount | u64 |
| 81 | token_amount | u64 |
| 89 | sol_vault_balance | u64 |
| 97 | token_vault_balance | u64 |
| 105 | state_sol_deployed | i128 |
| 121 | state_token_net | i128 |
| 137 | virtual_sol | u64 |
| 145 | virtual_tokens | u64 |
| 153 | global_sol_deployed | i128 |
| 169 | timestamp | i64 |
| 177 | end_timestamp | i64 |
| 185 | real_sol | u64 |
| 193 | real_tokens | u64 |
| 201 | version | u32 |
| 205 | retained_reserve_bps | u16 |
| 207 | quote_amount | u64 |
| 215 | quote_vault_balance | u64 |
| 223 | state_quote_deployed | i128 |
| 239 | virtual_quote | u64 |
| 247 | global_quote_deployed | i128 |
| 263 | real_quote | u64 |
| 271 | quote_mint | Pubkey |
| 303 | end | |

### BurnEvent - **88 bytes**
Dis `21592f75527ceefa` (`event:BurnEvent`): amount u64 8, mint Pubkey 16, mayhem_state Pubkey
48, timestamp i64 80; total 88.

### GlobalParamsUpdateEvent - **129 bytes**
Dis `63a75c9898e32629` (override): old_version u32 8, new_version u32 12, field_0 u32 16,
field_1 u32 20, field_2..5 u64 24/32/40/48, field_6 u8 56, field_7..15 u64
57/65/73/81/89/97/105/113/121; total 129.

### ExtendAccountEvent - **96 bytes**
Dis `6161d7905d92167c`: account Pubkey 8, user Pubkey 40, old_size u64 72, new_size u64 80,
timestamp i64 88; total 96.

### SweepEvent - **24 bytes**
Dis `da8286fd656d9598` (override): amount u64 8, timestamp i64 16; total 24.

## 4. pump_fees events (field order; offsets follow 8 + declaration order)

Variable-length fields are u32 length + payload (String/Vec); `Option<Pubkey>` is 1 tag byte +
32 bytes when Some (1 byte when None). The full field lists are in
`programs/pump-fees/src/types.rs`, `donation.rs`, `social.rs`, `buyback.rs`, `sharing_admin.rs`.

| Event | Fields (order) |
|---|---|
| `UpdateFeeConfigEvent` | timestamp i64, admin Pubkey, fee_config Pubkey, fee_tiers Vec<FeeTier>, flat_fees Fees(3 u64) |
| `UpdateStableFeeConfigEvent` | timestamp, admin, fee_config, stable_fee_tiers Vec<FeeTier>, flat_fees |
| `UpsertFeeTiersEvent` | timestamp, admin, fee_config, fee_tiers Vec, offset u8 |
| `UpsertStableFeeTiersEvent` | timestamp, admin, fee_config, stable_fee_tiers Vec, offset u8 |
| `SetExoticFlatFeesEvent` | timestamp, admin, fee_config, exotic_flat_fees Fees |
| `ExtendFeeConfigEvent` | fee_config Pubkey, user Pubkey, current_size u64, new_size u64, timestamp i64 |
| `UpdateFeeSharesEvent` | timestamp, mint, sharing_config, admin, new_shareholders Vec<Shareholder>, version u8 |
| `CreateFeeSharingConfigEvent` | timestamp, mint, bonding_curve, pool Option<Pubkey>, sharing_config, admin, initial_shareholders Vec, status enum(1) |
| `ResetFeeSharingConfigEvent` | timestamp, mint, sharing_config, old_admin, old_shareholders Vec, new_admin, new_shareholders Vec, old_version u8, new_version u8 |
| `SweepBuybackEvent` | index u8, sol_amount u64, token_amount u64, destination Pubkey, buyback_vault Pubkey, mint Pubkey |
| `DonationFeePdaCreated` | timestamp, created_by, donation_fee_pda, config_id, base_mint, quote_mint, creator (Pubkeys) |
| `DonationFeePdaCranked` | timestamp, signer, donation_fee_pda, config_id, base_mint, quote_mint, creator, amount u64 |
| `SocialFeePdaCreated` | timestamp, user_id String, platform u8, social_fee_pda, created_by |
| `SocialFeePdaClaimed` | timestamp, user_id String, platform u8, social_fee_pda, recipient, social_claim_authority, amount_claimed, claimable_before, lifetime_claimed, recipient_balance_before, recipient_balance_after, quote_mint, lifetime_stable_claimed |
| `InitializeFeeConfigEvent` | timestamp, admin, fee_config |
| `InitializeFeeProgramGlobalEvent` | timestamp, authority, social_claim_authority, disable_flags u8, claim_rate_limit u64 |
| `SetAuthorityEvent` | timestamp, old_authority, new_authority |
| `SetClaimRateLimitEvent` | timestamp, claim_rate_limit u64 |
| `SetDisableFlagsEvent` | timestamp, disable_flags u8 |
| `SetSocialClaimAuthorityEvent` | timestamp, social_claim_authority |
| `UpdateAdminEvent` | timestamp, old_admin, new_admin |
| `WithdrawEvent` | timestamp, user, quote_mint, amount u64 |

`Fees` = `{lp_fee_bps u64, protocol_fee_bps u64, creator_fee_bps u64}` (24 B). `FeeTier` =
`{market_cap_lamports_threshold u128, fees Fees}` (40 B). `Shareholder` =
`{address Pubkey, share_bps u16}` (34 B).

## 5. Other pump events (compact)

The pump has 32 IDL events; the trade event is above. The non-trade events follow the same
`8-disc + declaration-order` rule; the field lists are in the source / cluster specs:
`CreateEvent` (`1b72a94ddeeb6376`), `CompleteEvent` (`5f72619cd42e9808`),
`CompletePumpAmmMigrationEvent` (`bde95db95c94ea94`), `SetParamsEvent` (`dfc39ff63e308f83`),
`AdminCtoEvent` (`6e7ce262aaff1178`), `SetCreatorEvent`, `SetMetaplexCreatorEvent`,
`UpdateGlobalAuthorityEvent`, `UpdateCreatorFeeConfigEvent`, `ReservedFeeRecipientsEvent`,
`CollectCreatorFeeEvent`, `DistributeCreatorFeesEvent`, `DistributeFeeToHoldersEvent`,
`ExtendAccountEvent`, `MigrateBondingCurveCreatorEvent`,
`MinimumDistributableFeeEvent`, `SweepBondingCurveFeeEvent`, the quote-control events, the
incentives/cashback/volume events, `PostCompleteBuyEvent`,
`UpdateMayhemVirtualParamsEvent` (`757be4b6a1a8dcd6`). Discs/sites are in
`discriminators.md`; the field order is the declaration order in the corresponding source
file (or `trade_types.rs` for the shared ones).

---

## Notes

- The pump `TradeEvent` serialized length is **variable** (`387 + len(ix_name) + 34*n_shareholders`);
  do not assume 303/390. The mayhem `SellEvent` is fixed **303**; the AMM `SellEvent` is fixed
  **449**; the AMM `BuyEvent` is **494 + len(ix_name)**.
- The trailing `unparsed_trailing_field` in the pump `TradeEvent` is the **last serialized
  u64** (offset `379+L+34n`), not the in-memory `+0x198`. In the multi-hop curve executor it
  carries the quote adapter delta; normal buy/sell writes 0.
- The AMM event-CPI tag is `e445a52e51cb9a1d`; the event's own Anchor disc is inside
  `event.data()` (first 8 bytes). The mayhem/AMM self-CPI path and the pump/fees `emit_cpi!`
  use the same tag.
- Mayhem `GlobalParamsUpdateEvent`/`SellEvent`/`SweepEvent` use observed override discs; the
  historical event names are not recovered. `BurnEvent`/`ExtendAccountEvent` are the Anchor
  hashes.
