# pump_fees (`pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ`) - per-handler specs

Private analysis for the user. Format follows `amm_specs.md`. Tags:
**[B]** = confirmed in the deployed bytecode/rodata; **[R]** = from the read-only
reconstruction (`programs/pump-fees/src/*`) / repo interface inventory; **[partial]** =
inferred (reason stated).

Binary: `evidence/original/pump_fees/deployed.so`
(repo-recorded SHA-256 `4f2955d0f6b40cc9ff7daa18ccad7d19119ba1249759f4e7e3bb691beee6b35e`).
`sbftool` pc units = vaddr/8; addresses are vaddr.

## Map (31/31) **[B]**

Dispatcher at **`0x1240e`** (byte `0x92070`), 592 instructions, ends `0x12680`. All 31
discriminators were matched and each handler resolved from the dispatch stub. Full machine map:
`fees_handlers.json`. Priority handler addresses:

| handler | disc (digest hex) | handler pc | byte |
|---|---|---|---|
| get_fees | e7257e55cf5b3f34 | 0x136a0 | 0x9b500 |
| get_fees_with_quote_mint | 9aed8a5ca202a2bb | 0x13763 | 0x9bb18 |
| initialize_fee_config | 3ea214857941911b | 0x12d72 | 0x96b90 |
| update_fee_config | 68b867f258976b14 | 0x1319e | 0x98cf0 |
| upsert_fee_tiers | e317960c4d565e04 | 0x13267 | 0x99338 |
| set_exotic_flat_fees | 1eea958afce62749 | 0x13541 | 0x9aa08 |
| update_fee_shares | bd0d8863bba4ed23 | 0x138d4 | 0x9c6a0 |
| update_fee_shares_v2 | 6ffb31064e4e6a12 | 0x1395a | 0x9cad0 |
| sweep_buyback | 8a21cc26cfa19fe2 | 0x13e01 | 0x9f008 |

All nine discs are copied from `fees_handlers.json` (generated from the dispatcher); the rest of
the 31 are in that file. Note the two fee queries are distinct:
`get_fees` = `e7257e55cf5b3f34` (OptionBool variant) and
`get_fees_with_quote_mint` = `9aed8a5ca202a2bb` (quote-mint variant). **The Pump and AMM trade
CPIs use `get_fees_with_quote_mint`** (data prefix `9aed8a5ca202a2bb`, then `is_pump_pool` bool
+ u128 cap + quote mint).

Program-id constants verified in `.rodata` **[B]**: pump `6EF8...` (`0xc4ecd/0xc4eed`),
pump_amm `pAMM...` (`0xc4f3c/0xc4f5c`), fees self (`0xc4ead`), relay `RLAYHr...`
(`0xc37c0`), Tokenkeg (`0xc3640/0xc5404`), Token2022 (`0xc3760/0xc5424`), ATA (`0xc3600`),
WSOL (`0xc3740`), USDC (`0xc37a0`); fixed fees admin
`8LWu7QM2dGR1G8nKDHthckea57bkCzXyBTAKPJUBDHo8` at `0xc36e0` **[B]**. (Metaplex is not
referenced by the fees program.)

## Error table (FeeError = 6000 + index) **[B/R]**

Observed code immediates in `.text` (sites) and the source enum agree for the codes below.

| Code | Name | Observed site(s) |
|---:|---|---|
| 6001 | InvalidAdmin | 0x32e2, 0x3f5b |
| 6002 | NoFeeTiers | 0x8028, 0x8230 |
| 6003 | TooManyFeeTiers | 0x811d, 0x8325 |
| 6004 | OffsetNotContinuous | 0x8085, 0x828d |
| 6005 | FeeTiersNotSorted | 0x8195, 0x839d |
| 6006 | InvalidFeeTotal | 0x7f7a, 0x7fc8, 0x8159 |
| 6007 | InvalidSharingConfig | 0x520e, 0x5257, 0x558e |
| 6008 | InvalidPool | 0x52cd, 0x54be, 0x5540 |
| 6010 | NoShareholders | 0x6508, 0x6edf |
| 6011 | TooManyShareholders | 0x653d, 0x6f14 |
| 6012 | DuplicateShareholder | 0x666c, 0x7045 |
| 6013 | NotEnoughRemainingAccounts | 0x62ed, 0x6d04, 0x6d5b |
| 6014 | InvalidShareTotal | 0x660e, 0x6fe5 |
| 6016 | NotAuthorized | 0x5141, 0x5603, 0x576d |
| 6017 | ZeroShareNotAllowed | 0x6572, 0x6f49 |
| 6018 | SharingConfigNotActive | 0x56b8, 0x72d8 |
| 6020 | ShareholderAccountMismatch | 0x6309, 0x6d77 |
| 6022 | UserIdTooLong | 0x5d73 |
| 6023 | DeprecatedInstruction | 0x14249, 0x1428a (both deprecated handlers) |
| 6024 | FeeSharesAlreadyUpdated | 0x5f51, 0x6787 |
| 6026 | InvalidBuybackIndex | 0x2f92, 0x2fe2, 0x3ae9, ... |
| 6028 | InvalidFeeConfigAccount | 0x25bb, 0x25de, 0x263c, ... |
| 6029 | AccountTypeNotSupported | 0x772c |
| 6030 | InvalidMint | 0x780c |
| 6031 | UnsupportedQuoteMint | 0x5f0f |
| 6033 | PoolCreatorFeesNotSwept | 0x723e |
| 6034 | InvalidQuoteMint | 0x6870 |
| 6036 | NothingToWithdraw | 0x7a6c, 0x7c30 |

Codes 6000, 6009, 6015, 6019, 6021, 6025, 6027, 6032, 6035 were not isolated as direct
immediates (they may be constructed through a helper or unused in this revision); their names
are from the source/IDL. Treat the names as the reliable handle.

Account layouts (FeeConfig, FeeProgramGlobal, SharingConfig, BuybackVault, SocialFeePda,
DonationFeePda) are in `account_layouts.md` Sec.3.

---

# Priority handlers

## 1. `get_fees` @ 0x136a0 (byte 0x9b500)
1. **Purpose**: pure query; returns `Fees {lp, protocol, creator}` selected from the
   fees-owned `FeeConfig` (no state write, no event).
2. **Accounts**: `fee_config` (`Account<FeeConfig>`, PDA `["fee_config", config_program_id]`,
   bump = stored `fee_config.bump`), `config_program_id` (unchecked namespace).
3. **Args [B]**: `is_pump_pool: bool`, `market_cap_lamports: u128`,
   `trade_size_lamports: u64`, `is_new_quote_mint: OptionBool`.
4. **Behaviour [R]**: `!is_pump_pool` -> `flat_fees`. Else select from
   `stable_fee_tiers` when `is_new_quote_mint` else `fee_tiers`: if cap < tiers[0].threshold,
   tiers[0]; otherwise the highest tier with `cap >= threshold`. `trade_size_lamports` is
   accepted but not used by the selection in the reconstruction [partial: the original may use
   it in the tier math; no evidence of a read in the handler was isolated].
5. **Errors**: `FeeConfig` decode/PDA errors only. Empty tiers would index `tiers[0]`
   (panic) - admin writers reject empty tiers, so a live empty config is malformed [partial].
6. **CPIs**: none. **State writes**: none. **Return**: serialized `Fees` via Anchor return
   data (the AMM reads `get_return_data`).
7. **GAP**: [R] body; args/accounts/handler [B].

## 2. `get_fees_with_quote_mint` @ 0x13763 (byte 0x9bb18)
1. **Purpose**: quote-aware fee query (same return shape; no event).
2. **Accounts**: same `GetFeesWithQuoteMint` (fee_config + config_program_id).
3. **Args [B]**: `is_pump_pool: bool`, `market_cap_lamports: u128`, `quote_mint: Pubkey`.
4. **Behaviour [R]**: `!is_pump_pool` -> flat. Else by quote: `default`, WSOL, or
   OTHER_NORMAL_QUOTE (`0x81 0d fc 9f ...`, the non-stable normal quote) -> `fee_tiers`;
   USDC (`EPjF...`) -> `stable_fee_tiers`; else if exotic flat fees are all zero -> flat,
   otherwise `exotic_flat_fees`.
5. **Errors**: decode/PDA only; same empty-tier caveat.
6. **CPIs/state**: none; returns `Fees`.
7. **GAP**: [R] body; args/constants [B] (WSOL/USDC/OTHER bytes are in `.rodata`).

## 3. `initialize_fee_config` @ 0x12d72 (byte 0x96b90)
1. **Purpose**: create the 2512-byte `FeeConfig` PDA and install the fixed admin.
2. **Accounts**: `admin` (mut signer, `address = 8LWu...` -> 6001 InvalidAdmin),
   `fee_config` (`init`, payer=admin, space 2512, `["fee_config", config_program_id]`),
   `system_program`, `config_program_id` (unchecked), event_authority/program.
3. **Args**: none.
4. **Errors**: 6001 InvalidAdmin (fixed admin), System/init errors.
5. **CPIs**: System `create_account` via `init`; event log + `emit_cpi!`.
6. **State writes [R]**: `bump` (8), `admin` (9); other fields zero.
   `InitializeFeeConfigEvent` (log + CPI).
7. **GAP**: no successful historical fixed-admin replay (repo note); account/address [B],
   body [R].

## 4. `update_fee_config` @ 0x1319e (byte 0x98cf0)
1. **Purpose**: replace `fee_tiers` and `flat_fees`.
2. **Accounts**: `fee_config` (mut PDA, `has_one = admin` -> 6001), `admin` signer,
   `config_program_id`, event/program.
3. **Args [B]**: `fee_tiers: Vec<FeeTier>`, `flat_fees: Fees`.
4. **Errors [R]**: 6001 InvalidAdmin (the `has_one = admin`), 6006 InvalidFeeTotal
   (lp+protocol+creator > 10000, checked-add abort on overflow), 6002 NoFeeTiers,
   6003 TooManyFeeTiers (>50), 6005 FeeTiersNotSorted (strict ascending thresholds).
5. **CPIs**: none; event log + `emit_cpi!`.
6. **State writes [R]**: `fee_tiers` (variable, offset 69), `flat_fees` (41..65);
   `UpdateFeeConfigEvent` (log + CPI).
7. **GAP**: [R] body; args/map [B].

## 5. `upsert_fee_tiers` @ 0x13267 (byte 0x99338)
1. **Purpose**: overwrite/append fee tiers at a given offset.
2. **Accounts**: same `UpsertFeeTiers` (fee_config, admin, config_program_id, event/program).
3. **Args [B]**: `fee_tiers: Vec<FeeTier>`, `offset: u8`.
4. **Errors [R]**: 6002 (incoming empty), 6004 OffsetNotContinuous
   (`offset > current.len`), 6003 TooManyFeeTiers (`max(current.len, offset+incoming) > 50`),
   then 6006/6005 from `validate_tiers` on the merged list.
5. **CPIs**: none; event log + CPI.
6. **State writes [R]**: mutates `fee_config.fee_tiers` in place (overwrite offset..,
   append past len); `UpsertFeeTiersEvent` (log + CPI).
7. **GAP**: [R] body; [B] map/args.

## 6. `set_exotic_flat_fees` @ 0x13541 (byte 0x9aa08)
1. **Purpose**: set the exotic-quote flat fees, growing FeeConfig to 4097 if needed.
2. **Accounts**: fee_config (mut, has_one admin), admin (mut signer), config_program_id,
   system_program, event/program.
3. **Args [B]**: `exotic_flat_fees: Fees`.
4. **Errors [R]**: 6006 InvalidFeeTotal (total > 10000), 6001 InvalidAdmin; System/rent.
5. **CPIs [R]**: System transfer for the rent delta; `realloc(4097)`; event log + CPI.
6. **State writes [R]**: `exotic_flat_fees` (last 24 bytes of the 4097 layout);
   `SetExoticFlatFeesEvent` (log + CPI).
7. **GAP**: [R] body; 4097 constant [B].

## 7. `update_fee_shares` @ 0x138d4 (byte 0x9c6a0) - legacy WSOL path
1. **Purpose**: replace the sharing-config shareholders after flushing creator fees through
   PumpSwap/Pump.
2. **Accounts [R]**: event_authority, program, authority signer, `global` (Pump PDA
   `["global"]`), `mint`, `sharing_config` (`["sharing-config", mint]`, has_one mint),
   `bonding_curve` (`["bonding-curve", mint]` under pump), `pump_creator_vault`
   (`["creator-vault", sharing_config]` under pump), system_program, pump_program,
   pump_event_authority, pump_amm_program, amm_event_authority, `wsol_mint` (address=WSOL),
   `token_program` (address=Tokenkeg), associated_token_program,
   coin_creator_vault_authority (`["creator_vault", sharing_config]` under AMM),
   coin_creator_vault_ata (canonical ATA), + remaining accounts (preprocessed payout set).
3. **Args [B]**: `shareholders: Vec<Shareholder>`.
4. **Errors [R]**: 6031 UnsupportedQuoteMint (curve quote not default; site 0x5f0f),
   6024 FeeSharesAlreadyUpdated (version == 1), 6016 NotAuthorized
   (admin != authority), 6009 SharingConfigAdminRevoked, 6018 SharingConfigNotActive,
   6013/6020/6010/6011/6012/6017/6014/6015 for the remaining accounts and share vector,
   6033 PoolCreatorFeesNotSwept (site 0x723e).
5. **CPIs [R]**: AMM `transfer_creator_fees_to_pump` (disc `8b348655e4e56cf1`) then Pump
   `distribute_creator_fees` (disc `a572670079cef751`) for the prepared payouts; event log +
   CPI.
6. **State writes [R]**: `sharing_config.shareholders` (80 + 34n), `admin_revoked = true`
   (75); `UpdateFeeSharesEvent` (log + CPI).
7. **GAP**: [R] handler flow (helpers in `sharing_update.rs` are the source contract); the
   exact remaining-account stride/payout prep is [partial] here (the helper `preprocess_remaining`
   consumes the shareholder ATA set). Legacy path requires the curve quote == default.

## 8. `update_fee_shares_v2` @ 0x1395a (byte 0x9cad0)
1. **Purpose**: v2 of #7 for a general quote mint (WSOL or token), with
   `transfer_creator_fees_to_pump_v2` + `distribute_creator_fees_v2`.
2. **Accounts [R]**: as #7 but with `quote_mint` and `pump_creator_vault_ata` (Pump creator
   vault ATA) instead of `wsol_mint`; no `wsol_mint` constraint.
3. **Args [B]**: `shareholders: Vec<Shareholder>`.
4. **Errors [R]**: 6034 InvalidQuoteMint (quote != curve quote; site 0x6870), 6024, 6016,
   6009, 6018, 6013/6020/6010/6011/6012/6017/6014/6015, 6033.
5. **CPIs [R]**: AMM `transfer_creator_fees_to_pump_v2` (disc `01214eb921432c5c`) then Pump
   `distribute_creator_fees_v2` (disc `ffcb134ff444089f`); event log + CPI.
6. **State writes [R]**: shareholders + admin_revoked; event.
7. **GAP**: [R] body; quote equality gate [B] site.

## 9. `sweep_buyback` @ 0x13e01 (byte 0x9f008)
1. **Purpose**: sweep a buyback vault's quote tokens + excess lamports to a destination.
2. **Accounts [R]**: `destination` (mut unchecked), `authority` signer, `buyback_vault`
   (`["buyback-vault", index]`, has_one authority -> 6016), `buyback_vault_ata` (ATA of the
   vault), `destination_ata` (ATA of destination), system/ATA/mint/token, event/program.
3. **Args [B]**: `index: u8`.
4. **Errors [R]**: 6026 InvalidBuybackIndex (index >= 8; sites 0x2f92...), 6016
   NotAuthorized, 6027 ClaimRateLimitExceeded (when `last_claimed != 0` and
   `now-last_claimed <= claim_rate_limit`), 6025 MathOverflow.
5. **CPIs [R]**: token `transfer_checked` vault ATA -> destination ATA (vault PDA signer);
   lamport move of the vault excess (rent min) to destination.
6. **State writes [R]**: `total_claimed += sol_amount` (40), `total_claimed_token1 +=
   token_amount` if mint == native, else `total_claimed_token2` (48/56), `last_claimed = now`
   (64); `SweepBuybackEvent` (log + CPI).
7. **GAP**: [R] body; [B] index/error sites.

---

# The rest

## 10. `initialize_fee_program_global` @ 0x12e01 (byte 0x97008)
Accounts: authority (mut signer), pump `global` (`["global"]` under pump, has_one authority ->
6016), fee_program_global (`init`, space 338, `["fee-program-global"]`), system_program,
event/program. Args `social_claim_authority: Pubkey, disable_flags: u8, claim_rate_limit: u64`.
Writes bump (8), authority (9), social_claim_authority (42), disable_flags (41),
claim_rate_limit (74); emits `InitializeFeeProgramGlobalEvent` (log + CPI). Errors: 6016,
System init. [R] body, [B] map/space.

## 11. `set_authority` @ 0x130de (byte 0x986f0)
Accounts: authority signer (mut), fee_program_global (has_one authority -> 6016),
event/program. Arg `new_authority: Pubkey`. Requires non-default (6001 InvalidAdmin); writes
authority (9); `SetAuthorityEvent` (log + CPI). [R]/[B].

## 12. `set_claim_rate_limit` @ 0x13034 (byte 0x981a0)
Same 3-account context; arg `claim_rate_limit: u64`; writes 74; event. [R]/[B].

## 13. `set_disable_flags` @ 0x12f8a (byte 0x97c50)
Same; arg `disable_flags: u8`; writes 41; `SetDisableFlagsEvent`. Bit 0 create social, 1
claim social, 2 create donation, 3 crank donation (from the source gates). [R]/[B].

## 14. `set_social_claim_authority` @ 0x12eca (byte 0x97650)
Same; arg `social_claim_authority: Pubkey`; writes 42; event. [R]/[B].

## 15. `update_admin` @ 0x135f3 (byte 0x9af98)
Accounts: admin signer, fee_config (mut PDA, has_one admin -> 6001), new_admin (unchecked),
config_program_id, event/program. No args; writes `fee_config.admin` (9); `UpdateAdminEvent`
(old/new). [R]/[B].

## 16. `update_stable_fee_config` @ 0x13329 (byte 0x99948)
Accounts: fee_config, admin, config_program_id, event/program. Arg `fee_tiers: Vec<FeeTier>`.
Validates tiers (6002/6003/6005/6006); writes `stable_fee_tiers` (after the fee_tiers Vec);
emits `UpdateStableFeeConfigEvent` (includes the current flat_fees). [R]/[B].

## 17. `upsert_stable_fee_tiers` @ 0x133e0 (byte 0x99f00)
Like #5 for `stable_fee_tiers`: args `fee_tiers, offset`; same 6002/6004/6003 + tier checks;
event. [R]/[B].

## 18. `extend_fee_config` @ 0x134a2 (byte 0x9a510)
Accounts: fee_config (mut unchecked), user signer, config_program_id, system_program,
event/program. No args. Checks owner == fees, len>=9, disc `8f34...`, PDA
`["fee_config", config_program_id, bump]` -> 6028 InvalidFeeConfigAccount; if len < 4097,
System top-up to rent(4097), `realloc(4097, true)`; emits `ExtendFeeConfigEvent`. [R]/[B]
owner/disc/PDA.

## 19. `initialize_buyback` @ 0x13d6a (byte 0x9eb50)
Accounts: payer signer, buyback_vault (`init`, space 208, `["buyback-vault", index]`),
buyback_vault_ata (`init_if_needed` ATA of the vault), system/ATA/mint/token, event/program.
Arg `index: u8`; requires index < 8 (6026) else shell; the `init` creates the vault (fields
default). No event/state writes in the handler body (the account init writes zeros). [R]/[B].

## 20. `update_buyback_authority` @ 0x13ea6 (byte 0x9f530)
Accounts: authority signer, fee_program_global (has_one -> 6016), buyback_vault
(`["buyback-vault", index]`), event/program. Args `index: u8, new_authority: Pubkey`;
index < 8 (6026); writes `buyback_vault.authority` (8); no event in the source. [R]/[B].

## 21. `update_buyback_claim_rate_limit` @ 0x13f80 (byte 0x9fc00)
Same context; args `index: u8, claim_rate_limit: i64`; index < 8; writes
`buyback_vault.claim_rate_limit` (72); no event. [R]/[B].

## 22. `admin_cto_sharing_config` @ 0x139e4 (byte 0x9cf20)
Accounts: pool_authority (signer, `["pool-authority", mint]` under pump), authority signer,
pump `global` (`["global"]` under pump; `admin_set_creator_authority == authority` -> 6016),
mint, sharing_config (`["sharing-config", mint]`, has_one mint -> 6007), event/program.
Arg `new_admin: Option<Pubkey>`. Some(admin): admin=admin, admin_revoked=false, status Active,
shareholders=[{admin,10000}]; None: admin=default, admin_revoked=true, status Paused,
shareholders=[]; version=2; `ResetFeeSharingConfigEvent` (log + CPI). Errors 6007/6016.
[R]/[B].

## 23. `create_fee_sharing_config` @ 0x13810 (byte 0x9c080)
Accounts: event_authority, program, payer signer, pump `global`, mint, sharing_config
(`init_if_needed`, space 1024, `["sharing-config", mint]`), system_program, bonding_curve
(`["bonding-curve", mint]` under pump), pump_program, pump_event_authority,
pump_amm_program (optional), pump_amm_event_authority (optional), pool (optional AMM),
pump_amm_program/event (optional). No args. If version != 0 return Ok. Graduated coin
(real_token_reserves==0): requires AMM accounts (6019), validates pool base_mint/creator/PDA
(6008 InvalidPool), creator=pool.coin_creator; else creator=curve.creator and
payer==creator (6016). Writes bump/version=2/status Active/mint/admin/revoked/shareholders
[{creator,10000}], exits; then Pump `extend_account` (disc `ea66c2cb96483ee5`, bytes
`234,102,194,203,150,72,62,229`) and Pump `migrate_bonding_curve_creator` (disc
`577c34bf3426d6e8`, bytes `87,124,52,191,52,38,214,232`); when graduated, the AMM
`extend_account` (same `ea66...` disc) and AMM `migrate_pool_coin_creator` (disc
`d0089f044aaf103a`, bytes `208,8,159,4,74,175,16,58`). Errors
6007/6008/6009/6016/6018/6019. [R]/[B] disc/PDA.

## 24. `create_social_fee_pda` @ 0x13a95 (byte 0x9d4a8)
Accounts: payer signer, social_fee_pda (`init_if_needed`, space 179,
`["social-fee-pda", user_id, platform]`), system_program, fee_program_global
(`["fee-program-global"]`), event/program. Args `user_id: String, platform: u8`. Requires
disable_flags & 1 == 0 (6021 FeatureDeactivated), `user_id.len() <= 20` (6022
UserIdTooLong); if version != 0 return Ok; writes bump/version=1/user_id/platform,
total_claimed/last_claimed/stable=0, reserved=0; `SocialFeePdaCreated` (log + CPI).
[R]/[B].

## 25. `claim_social_fee_pda` @ 0x13b5d (byte 0x9dae8) - native only
Accounts: recipient (mut unchecked), social_fee_pda (`["social-fee-pda", user_id, platform]`),
fee_program_global (`has_one social_claim_authority` -> 6016), social_claim_authority signer,
event/program. Args `user_id: String, platform: u8`. Requires disable_flags & 2 == 0 (6021);
rate limit: if last_claimed != 0 and `now-last < claim_rate_limit` return Ok(None) (6027 is
the buyback rate limit, not this path); amount = PDA lamports - rent(min_balance(179));
amount==0 or recipient executable -> Ok(None); lamport move; `total_claimed += amount`,
`last_claimed = now`; `SocialFeePdaClaimed` (log + CPI). [R]/[B].

## 26. `claim_social_fee_pda_v2` @ 0x13c64 (byte 0x9e320) - native or token
Accounts: recipient, social_fee_pda, quote_mint, associated_social_fee_pda (canonical ATA),
associated_recipient (canonical ATA), quote_token_program, associated_token_program,
fee_program_global (has_one -> 6016), social_claim_authority signer, system_program,
event/program. Args `user_id, platform`. Native branch = #25. Token branch: admit/create the
two ATAs, amount = social ATA token balance; transfer with the social-fee PDA signer
(`["social-fee-pda", user_id, platform, bump]`); `total_stable_claimed += amount`. Same rate
limit/disable gates; event includes quote_mint/lifetime_stable. [R]/[B].

## 27. `create_donation_fee_pda` @ 0x14044 (byte 0xa0220)
Accounts: event_authority, program, payer signer, system_program, fee_program_global,
donation_fee_pda (`init_if_needed`, space 218,
`["donation-fee-pda", base_mint, config_id]`), config_id unchecked, base_mint, bonding_curve
(`["bonding-curve", base_mint]` under pump), pool (unchecked), sharing_config
(`["sharing-config", base_mint]`). No args. disable_flags & 4 -> 6021; if version != 0 return
Ok; derivation: if the curve has non-zero reserves -> creator/quote from the curve (quote
from serialized bytes 83..115, default -> WSOL); else the AMM pool (owner==AMM, base_mint,
canonical creator/PDA -> 6008); if creator == sharing_config key, validate it (owner fees,
mint, admin==payer -> 6016, !admin_revoked -> 6009, Active -> 6018) and use config.admin;
else payer==creator (6016). Writes bump/version=1/config_id/base_mint/quote_mint/creator,
total/last=0, reserved=0; `DonationFeePdaCreated`. [R]/[B].

## 28. `crank_donation_fee_pda` @ 0x140b8 (byte 0xa05c0)
Accounts: event_authority, program, payer signer, system/token/ATA programs, rent
(address=Rent), fee_program_global, donation_fee_pda (`["donation-fee-pda", base_mint,
config_id]`), quote_mint (address=donation_fee_pda.quote_mint), donation_fee_pda_ata
(init_if_needed ATA), donation_relay_program (executable, address=RLAY...),
donation_relay_event_authority, mint_whitelist, epoch_tracker (mut), debouncer (mut),
debouncer_ata (mut), quote_mint. No args. disable_flags & 8 -> 6021. For native WSOL: move
the PDA lamport excess into the ATA, then Tokenkeg `sync_native` (tag 17) signed by the PDA.
If ATA amount == 0 return Ok. Builds the relay payload (disc `78d939f187688bb8`, amount,
config_id, 0u16, borsh string "{base_mint},{creator}", fees program id), invokes the relay
program with the PDA signer and 13 accounts; writes total_donated (138) += amount,
last_crank_ts (146); `DonationFeePdaCranked` (log + CPI). [R]/[B] relay id/payload.

## 29. `withdraw` @ 0x14121 (byte 0xa0908)
Accounts: user signer, referral_vault (`SystemAccount`, `["referral-vault", user]`),
quote_mint (Option<Mint>), vault_ata (Option, mint/authority=vault), user_ata (Option,
mint/authority=user), token_program (Option), system_program, event/program. No args. If
quote_mint is Some: require the three Optional token accounts (6035 IncompleteTokenAccounts);
amount = vault.amount; require >0 (6036 NothingToWithdraw); token transfer vault->user with
the referral PDA signer. Else: amount = vault lamports - rent(min_balance(0)); require >0
(6036); System transfer with the PDA signer. `WithdrawEvent` (log + CPI). [R]/[B].

## 30. `revoke_fee_sharing_authority` @ 0x138ba (byte 0x9c5d0)
Deprecated stub. The IDL has **no accounts**; the handler returns
`FeeError::DeprecatedInstruction` (6023) immediately. The 6023 immediates at `0x14249`/
`0x1428a` are the two deprecated handlers. No state/CPIs. [B] code/site, [R] source.

## 31. `transfer_fee_sharing_authority` @ 0x138c7 (byte 0x9c638)
Deprecated stub, same as #30 (returns 6023). No accounts/state. [B]/[R].

---

## Cross-cutting notes

- **FeeConfig is the shared AMM/Fees object**: disc `8f3492bbdb7b4c9b`, 2512 init ->
  4097 extended; the AMM `get_fees`/`get_fees_with_quote_mint` CPI it and the AMM v2/trade
  paths read it locally. Admin writers validate tiers/fees; a malformed account can still
  make `select_fee_tier` index empty tiers (panic) - do not build such a fixture.
- **SharingConfig** (disc `d84a0900388c5d4b`, 1024 init, `80+34n` live) is the fees-owned
  per-mint shareholder table used by PumpSwap `migrate_pool_coin_creator`,
  `set_coin_creator`/`collect` constraints, and Pump's creator distribution. The
  `admin_cto_sharing_config` reset sets version=2 and either a single 10000-bps admin or an
  empty paused config.
- **update_fee_shares(_v2)** is the only fees path that CPIs PumpSwap/Pump (flush creator
  fees, then distribute). It requires a live sharing config (Active, admin not revoked) and
  the legacy path additionally requires the curve quote == default. The deployed code
  validates `PoolCreatorFeesNotSwept` (6033) and the share vector (10000 bps total).
- **Deprecated handlers** are real dispatch entries but return 6023 and consume no accounts;
  the IDL shows empty account lists.
- **Tags**: handler addresses/discs, program ids, fixed admin, sizes and the observed error
  immediates are [B]; all handler *behavior* is [R] from the reconstruction unless a [B] site
  is cited. No whole-byte or exhaustive behavioral claim is made.
