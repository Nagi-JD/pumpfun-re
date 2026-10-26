# PumpSwap (`pump_amm`, `pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA`) - per-handler specs

Private analysis for the user. Tags: **[B]** = I confirmed it directly in the deployed
bytecode / `.rodata`; **[R]** = taken from the read-only reconstruction in
`repro/pump_amm/formatter-restoration-main-v144/main/source/programs/pump-amm/src/` (the
reconstruction the repo harness has exercised against this capture) and its IDL/interface
inventory; **[partial]** = inferred, with the reason stated.

No byte-identity is claimed. No build or execution was performed here.

Binary analysed (read-only):
`D:\dev\ext\pumpfun-source\evidence\original\pump_amm\deployed.so`
(repo-recorded SHA-256 `6a7ad34596d83b4c435b32f458a56e718e9f82eb4ad38e4316616d15d24d8ff7`;
`.text` at vaddr/file `0x120`, size `0x11bb38`).
Decoder: `D:\dev\pumpfun-re\sbftool.py` (`pc` units = vaddr/8; addresses below are vaddr).

**Sections 1-9 are the requested priority handlers; 10-38 are "the rest".**

---

## 0. Map correction and method

The task said "map (30/31)". That is an artifact of the 31-entry IDL
`programs/pump-fees/idls/pump_amm.json`. The deployed binary actually has **38 instructions**,
matching `evidence/upstream/pump_amm.json` (38 names). `admin_set_coin_creator` (a name in the
31-entry IDL) is **not** a deployed discriminator; the real instruction is `admin_cto_pool`.

Method **[B]**:
- The `amm_handlers.json` address for each instruction is the per-instruction **argument
  codec/wrapper** (it logs `Instruction: X`, decodes the Borsh args, and returns them). The
  generated accounts parser and the business body are reached from the common dispatch tail,
  not directly from that address. Use the map address as the identity anchor; do not treat it
  as the body start.
- Dispatcher at **`0x1b793`** (byte `0xdbc98`), 721 instructions, ends `0x1ba8d`.
  It is a linear chain, not a binary search: each case is `lddw r4,<disc>; [0-2 movs]; jeq r3,r4,+off`.
- Anchor disc = `sha256("global:"+snake_name)[:8]`; each instruction stub logs
  `Instruction: <PascalCase(name)>` via `lddw r1,<str>; mov r2,<len>; call <sol_log_>`.
- The 31-entry `amm_handlers.json` addresses are reproduced; the 8 missing handlers
  (`admin_cto_pool`, `buy_exact_quote_in_v2`, `buy_v2`, `multi_hop_swap`, `sell_v2`,
  `sweep_creator_fee`, `sweep_protocol_fee`, `update_creator_fee_config`) are added below.

| # | instruction | disc (digest hex) | lddw | handler pc | handler byte |
|---:|---|---|---|---:|---:|
| 1 | create_pool | e992d18ecf6840bc | 0x1b7bb | 0x1c634 | 0xe31a0 |
| 2 | buy | 66063d1201daebea | 0x1b7eb | 0x1cec9 | 0xe7648 |
| 3 | sell | 33e685a4017f83ad | 0x1b7f3 | 0x1d099 | 0xe84c8 |
| 4 | deposit | f223c68952e1f2b6 | 0x1b7cf | 0x1ca4f | 0xe5278 |
| 5 | withdraw | b712469c946da122 | 0x1b7d3 | 0x1caf6 | 0xe57b0 |
| 6 | create_config | c9cff3724b6f2fbd | 0x1b7a5 | 0x1c17f | 0xe0bf8 |
| 7 | collect_coin_creator_fee | a039592ab58b2b42 | 0x1b813 | 0x1d51d | 0xea8e8 |
| 8 | set_coin_creator | d295802dbc3a4eaf | 0x1b817 | 0x1d56e | 0xeab70 |
| 9 | update_fee_config | 68b867f258976b14 | 0x1b7b3 | 0x1c446 | 0xe2230 |
| 10 | buy_exact_quote_in | c62e1552b4d9e870 | 0x1b7ef | 0x1cfb1 | 0xe7d88 |
| 11 | buy_v2 | b817ee6167c5d33d | 0x1b7f7 | 0x1d15d | 0xe8ae8 |
| 12 | buy_exact_quote_in_v2 | c2ab1c46684d5b2f | 0x1b7fb | 0x1d1e2 | 0xe8f10 |
| 13 | sell_v2 | 5df6823ce7e940b2 | 0x1b7ff | 0x1d267 | 0xe9338 |
| 14 | multi_hop_swap | 2b644913e9f66f94 | 0x1b803 | 0x1d2ec | 0xe9760 |
| 15 | sweep_protocol_fee | 0830be07b644b7e5 | 0x1b807 | 0x1d372 | 0xe9b90 |
| 16 | sweep_creator_fee | 20f6bf3408c949ba | 0x1b80b | 0x1d3f8 | 0xe9fc0 |
| 17 | extend_account | ea66c2cb96483ee5 | 0x1b80f | 0x1d47e | 0xea3f0 |
| 18 | transfer_creator_fees_to_pump | 8b348655e4e56cf1 | 0x1b827 | 0x1d846 | 0xec230 |
| 19 | transfer_creator_fees_to_pump_v2 | 01214eb921432c5c | 0x1b82b | 0x1d898 | 0xec4c0 |
| 20 | migrate_pool_coin_creator | d0089f044aaf103a | 0x1b82f | 0x1d8e7 | 0xec738 |
| 21 | claim_cashback | 253a237ebe35e4c5 | 0x1b837 | 0x1da42 | 0xed210 |
| 22 | update_buyback_config | fbe0ab92a01a71e9 | 0x1b83b | 0x1dacc | 0xed660 |
| 23 | admin_cto_pool | 2d3da597680031bd | 0x1b81b | 0x1d5fe | 0xeaff0 |
| 24 | toggle_mayhem_mode | 01096fd0641fffa3 | 0x1b81f | 0x1d701 | 0xeb808 |
| 25 | toggle_cashback_enabled | 7367e0ffbd5956c3 | 0x1b833 | 0x1d977 | 0xecbb8 |
| 26 | toggle_boost | 75a1a04adf897663 | 0x1b823 | 0x1d7cc | 0xebe60 |
| 27 | set_boost_authority | e3954c2a8227eacd | 0x1b7c3 | 0x1c839 | 0xe41c8 |
| 28 | update_creator_fee_config | 3dafa0f9424288af | 0x1b7b7 | 0x1c565 | 0xe2b28 |
| 29 | init_boost | 8ce9215e845ac28f | 0x1b7bf | 0x1c7b3 | 0xe3d98 |
| 30 | boost_buy_and_burn | 694406af000723a2 | 0x1b7c7 | 0x1c8e7 | 0xe4738 |
| 31 | set_reserved_fee_recipients | 6faca2e87259d58e | 0x1b7cb | 0x1c98d | 0xe4c68 |
| 32 | disable | b9adbb5ad80feee9 | 0x1b7a9 | 0x1c2a1 | 0xe1508 |
| 33 | update_admin | a1b028d53cb8b3e4 | 0x1b7af | 0x1c398 | 0xe1cc0 |
| 34 | admin_update_token_incentives | d10b7357d5177ccc | 0x1b7d7 | 0x1cb9d | 0xe5ce8 |
| 35 | claim_token_incentives | 1004471ccc01281b | 0x1b7db | 0x1cc57 | 0xe62b8 |
| 36 | init_user_volume_accumulator | 5e06ca73ff60e8b7 | 0x1b7df | 0x1cce2 | 0xe6710 |
| 37 | close_user_volume_accumulator | f945a4da9667548a | 0x1b7e3 | 0x1cd93 | 0xe6c98 |
| 38 | sync_user_volume_accumulator | 561fc057a3574fee | 0x1b7e7 | 0x1ce17 | 0xe70b8 |

Program-id constants (verified in `.rodata`) **[B]**:
`pump 0x11e55e/0x11e57e`, `pump_amm 0x11e53e`, `fees 0x11e5dc/0x11e5fc`,
`Tokenkeg 0x11bd50/0x11eb44`, `Token2022 0x11be90/0x11eb64`, `ATA 0x11bd10`,
`Metaplex 0x11bdb0`, `WSOL 0x11beb0`, `USDC 0x11bf10`. The fixed `create_config` admin
`8LWu7QM2dGR1G8nKDHthckea57bkCzXyBTAKPJUBDHo8` is at `0x11be50` **[B]**.
Error-code immediates `6000..6088` are present in `.text` (e.g. 6000 @`0xc2fd/0xc34a/0xc397`,
6004 @`0x41ac/0x6055/0x615a`, 6023 @`0x25ae/0x2605/0x45c2`, 6087 @one site, 6088 @one site),
so the 89-variant `PumpAmmError` enumeration is consistent with this capture **[B]**.

**Event accounts**: every context annotated `#[event_cpi]` appends
`event_authority` (`["__event_authority"]`) and `program` (this program) as the last two
accounts. The lists below include them for the trade/admin handlers; where a list is
abbreviated, those two are still required (the upstream IDL lists them).

Account layouts used for the state-write column (serialized offsets, **including** the 8-byte
discriminator) **[R]** (from `state.rs`):
- `Pool` (287 bytes; disc `f19a6d0411b16dbc`): pool_bump 8, index 9, creator 11, base_mint 43,
  quote_mint 75, lp_mint 107, pool_base_token_account 139, pool_quote_token_account 171,
  lp_supply 203, coin_creator 211, is_mayhem_mode 243, is_cashback_coin 244,
  virtual_quote_reserves (i128) 245, creator_fee_bps 261, can_edit_creator_fee 269,
  is_holder_reward 270, protocol_fees 271, creator_fees 279.
  Decoder accepts legacy prefixes 211/243/244/245/261/270/271/287 and zero-pads.
- `GlobalConfig` (disc `95089ccaa0fcb0d9`; 907/940/949-byte legacy variants): admin 8,
  lp_fee_basis_points 40, protocol_fee_basis_points 48, disable_flags 56,
  protocol_fee_recipients 57, coin_creator_fee_basis_points 313,
  admin_set_coin_creator_authority 321, whitelist_pda 353, reserved_fee_recipient 385,
  mayhem_mode_enabled 417, reserved_fee_recipients 418, is_cashback_enabled 642,
  buyback_fee_recipients 643, buyback_basis_points 899, boost_authority 907,
  boost_enabled 939, creator_fee_configurable 940, max_configurable_creator_fee_bps 941.
- `UserVolumeAccumulator` (init space 137; disc is Anchor `account:UserVolumeAccumulator`):
  user 8, needs_claim 40, total_unclaimed_tokens 41, total_claimed_tokens 49,
  current_sol_volume 57, last_update_timestamp 65, has_total_claimed_tokens 73,
  cashback_earned 74, total_cashback_claimed 82 (payload 90 bytes; 137 is over-allocated).
- `GlobalVolumeAccumulator`: start_time 8, end_time 16, seconds_in_a_day 24, mint 32,
  total_token_supply[30] 64, sol_volumes[30] 304 (payload ends 544).
- `TradeFeeConfig` is owned by the fees program `pfeeUx...`; the AMM only deserializes it
  (legacy truncation fixups at <4073 / <4097 bytes).
- All error codes below are `6000 + enum discriminant` (`PumpAmmError` in `lib.rs`).

---

## 1. `create_pool` @ 0x1c634 (byte 0xe31a0) **[B/R]**

1. **Purpose**: create a pool PDA, mint its LP tokens, initialize the `Pool` state, seed both
   vaults from the creator, and emit `CreatePoolEvent`. Rejects non-canonical pools that ask
   for a coin-creator/custom-fee/holder-reward configuration.
2. **Accounts** **[R]** (order from the deployed upstream IDL/`CreatePool`): `pool`
   (`init`, payer=creator, space 287, seeds `["pool", index_le, creator, base_mint, quote_mint]`),
   `global_config` (`["global_config"]`), `creator` (mut signer), `base_mint`, `quote_mint`,
   `lp_mint` (`init`, seeds `["pool_lp_mint", pool]`, 9 decimals, authority=pool,
   Token-2022), `user_base_token_account`, `user_quote_token_account`, `user_pool_token_account`
   (`init`, ATA of lp_mint/creator), `pool_base_token_account` (`init_if_needed`, ATA of
   base_mint/pool), `pool_quote_token_account` (`init_if_needed`, ATA of quote_mint/pool),
   `system_program`, `token_2022_program`, `base_token_program`, `quote_token_program`,
   `associated_token_program`, `event_authority` (`["__event_authority"]`), `program`
   (18 accounts total).
3. **Args [B, codec 0x1c641..0x1c6f0]**: `index: u16` @0, `base_amount_in: u64` @2,
   `quote_amount_in: u64` @0xa, `coin_creator: Pubkey` @0x12, `is_mayhem_mode: bool` @0x32,
   `is_cashback_coin: OptionBool` @0x33, `creator_fee_bps: OptionU64` @0x34,
   `can_edit_creator_fee: OptionBool`, `is_holder_reward: OptionBool` (the last three are
   optional/EOF-defaulting). This confirms the **9-arg** source, and that the 31-entry IDL
   (6 args) is stale.
4. **Errors** **[R]** + codes: 6017 DisabledCreatePool (disable_flags&1), 6001 ZeroBaseAmount,
   6002 ZeroQuoteAmount, 6006 UnsupportedBaseMint, 6007 UnsupportedQuoteMint, 6022 SameMint,
   6041 MayhemModeDisabled, 6042 OnlyPumpPoolsMayhemMode, 6049 CashbackNotEnabled,
   6050 OnlyPumpPoolsCashback, 6028 OnlyCanonicalPumpPoolsCanHaveCoinCreator, 6003
   TooLittlePoolTokenLiquidity (sqrt(product) >= 100).
5. **CPIs** **[R]**: `transfer_checked` from creator to each pool vault on base/quote token
   programs; Token-2022 `mint_to` LP (signer = pool PDA); System/ATA `init` CPIs for the PDAs
   and ATAs. Program IDs verified at the constants above.
6. **State writes** **[R]**: `pool = Pool { pool_bump, index, creator, base_mint, quote_mint,
   lp_mint, pool_base_token_account, pool_quote_token_account, lp_supply = sqrt(pb*pq),
   coin_creator = (canonical ? arg : default), is_mayhem_mode, is_cashback_coin,
   virtual_quote_reserves = 0, creator_fee_bps, can_edit_creator_fee,
   is_holder_reward = canonical && holder, protocol_fees = 0, creator_fees = 0 }`.
   Emits `CreatePoolEvent` (log + `emit_cpi!`), topic includes `minimum_liquidity=100`,
   `initial_liquidity`, `lp_token_amount_out`, all account keys.
7. **GAP**: [R] for the body (the repo harness covers create_pool); the arg codec and map are
   [B]. Fee/creator args are new relative to the 31-entry IDL.

## 2. `buy` @ 0x1cec9 (byte 0xe7648) **[B/R]**

1. **Purpose**: fixed-base-output buy on a pool (legacy PumpSwap path, optional fees-program
   CPI, cashback/buyback remaining accounts).
2. **Accounts [R]** (`LegacyBuy`): pool (mut, `has_one` base_mint/quote_mint/
   pool_base_token_account/pool_quote_token_account), user (mut signer), global_config,
   base_mint, quote_mint, user_base_token_account, user_quote_token_account,
   pool_base_token_account, pool_quote_token_account, protocol_fee_recipient,
   protocol_fee_recipient_token_account (`init_if_needed` ATA), base_token_program,
   quote_token_program, system_program, associated_token_program, event_authority
   (`["__event_authority"]`), program (self), coin_creator_vault_ata (`init_if_needed`),
   coin_creator_vault_authority (`["creator_vault", pool.coin_creator]`),
   global_volume_accumulator (`["global_volume_accumulator"]`),
   user_volume_accumulator (`init_if_needed`, 137, `["user_volume_accumulator", user]`),
   fee_config (`["fee_config", pump_amm]` under fees program), fee_program.
3. **Args [B, codec 0x1ced2..]**: `base_amount_out: u64`, `max_quote_amount_in: u64`,
   `track_volume: OptionBool` (wrapper requires >=16 bytes and reads a bool at +0x10 if
   present; EOF => false).
4. **Errors [R]**: 6020 DisabledBuy, 6013 InvalidProtocolFeeRecipient, 6001/6002,
   6039 BuyNotEnoughQuoteTokensToCoverFees, 6016 BuyMoreBaseAmountThanPoolReserves,
   6004 ExceededSlippage, 6040 BuySlippageBelowMinBaseAmountOut, 6023 Overflow, 6024
   Truncation, 6025 DivisionByZero, 6053/6054/6055/6058 buyback errors, 6059/6060/6061
   cashback errors, 6062 InvalidPoolV2, 6087 SelfTransferNotAllowed.
5. **CPIs [R]**: fees-program `get_fees_with_quote_mint` (`pfeeUx...`, disc bytes
   `154,237,138,92,162,2,162,187`; accounts `[fee_config, pump_amm]`); token
   `transfer_checked` for base out, quote in (grossed up by Token-2022 fee), protocol fee,
   creator fee, buyback fee; ATA create for cashback/buyback destinations; optional System
   transfer to top up a short pool account.
6. **State writes [R]**: `user_volume_accumulator.user = user`;
   `user_volume_accumulator.cashback_earned += creator_fee` when cashback is used (74);
   pool quote/base token account balances change; emits `BuyEvent` (log + `emit_cpi!`) with
   the full fee/reserve/cashback/buyback tail. `pool.protocol_fees`/`creator_fees` are NOT
   accrued on this legacy path (fees are paid out directly).
7. **GAP**: the reconstruction's `buy` body is [R]; arg codec/map [B]. Fee-config content is
   external (`fees` program), not reconstructed here.

## 3. `sell` @ 0x1d099 (byte 0xe84c8) **[B/R]**

1. **Purpose**: fixed-base-input sell (legacy path), direct fee payouts + buyback/cashback.
2. **Accounts [R]** (`LegacySell`): same as `buy` minus the global/user volume accounts and
   buyback-ATA extras; includes fee_config + fee_program.
3. **Args [B, codec 0x1d0a2..]**: `base_amount_in: u64`, `min_quote_amount_out: u64`
   (requires exactly >=16 bytes).
4. **Errors [R]**: 6021 DisabledSell, 6013, 6001, 6063 InsufficientRealQuoteReserves,
   6004 ExceededSlippage, 6023/6024/6025, cashback/buyback codes as in buy.
5. **CPIs [R]**: fees `get_fees_with_quote_mint`; base transfer user->pool (user authority); quote transfer
   pool->user, pool->protocol recipient, pool->creator vault, pool->cashback/buyback ATAs
   (pool PDA signer); ATA create.
6. **State writes [R]**: only token balances + `BuyEvent`-family `SellEvent` (log + CPI);
   `pool.protocol_fees`/`creator_fees` are not accrued on the legacy path.
7. **GAP**: [R] body, [B] arg codec/map.

## 4. `deposit` @ 0x1ca4f (byte 0xe5278) **[B/R]**

1. **Purpose**: add liquidity and mint LP tokens at the current pool ratio.
2. **Accounts [R]** (`Liquidity`): pool (mut; `has_one` base_mint/quote_mint/lp_mint/
   pool_base_token_account/pool_quote_token_account), global_config, user (signer),
   base_mint, quote_mint, lp_mint (mut), user_base_token_account, user_quote_token_account,
   user_pool_token_account (mut, authority=user), pool_base_token_account,
   pool_quote_token_account, token_program (Tokenkeg), token_2022_program,
   event_authority (`["__event_authority"]`), program (15 accounts total).
3. **Args [B, codec]**: `lp_token_amount_out: u64`, `max_base_amount_in: u64`,
   `max_quote_amount_in: u64`.
4. **Errors [R]**: 6018 DisabledDeposit, 6004 ExceededSlippage (base/cap limits), 6023/6024/
   6025, 6087 SelfTransferNotAllowed, 6064 BoostPoolLiquidityUnsupported is NOT used here
   (that is withdraw/boost path) - the source uses the ratio math directly.
5. **CPIs [R]**: base/quote `transfer_checked` user->vault (user authority; Tokenkeg or
   Token-2022 chosen by mint owner); Token-2022 `mint_to` LP (pool PDA signer).
6. **State writes [R]**: `pool.lp_supply += amount` (203), `pool.virtual_quote_reserves`
   scaled (245), emits `DepositEvent` (log + CPI) with reserves, fees, transfer fee.
7. **GAP**: repo harness covers deposit; map/args [B].

## 5. `withdraw` @ 0x1caf6 (byte 0xe57b0) **[B/R]**

1. **Purpose**: burn LP tokens and withdraw proportional base/quote reserves.
2. **Accounts [R]**: same 15-account `Liquidity` context as deposit (including
   `event_authority` and `program`).
3. **Args [B]**: `lp_token_amount_in: u64`, `min_base_amount_out: u64`,
   `min_quote_amount_out: u64`.
4. **Errors [R]**: 6019 DisabledWithdraw, 6067 SeedLockViolation (lp_mint.supply >
   pool.lp_supply), 6004, 6023/6024/6025, 6064 BoostPoolLiquidityUnsupported is not emitted
   by this legacy path, 6087.
5. **CPIs [R]**: Token-2022 `burn` from user LP (user authority); base/quote
   `transfer_checked` vault->user (pool PDA signer; quote gross-down by Token-2022 fee).
6. **State writes [R]**: `pool.lp_supply -= amount`, `pool.virtual_quote_reserves` scaled,
   emits `WithdrawEvent` (log + CPI).
7. **GAP**: repo harness covers withdraw; map/args [B].

## 6. `create_config` @ 0x1c17f (byte 0xe0bf8) **[B/R]**

1. **Purpose**: one-time creation of the `global_config` PDA with fee schedule and admin.
2. **Accounts [R]** (`CreateConfig`): `admin` (mut signer, `address = 8LWu7QM2dGR1G8nKDHthckea57bkCzXyBTAKPJUBDHo8`
   -> 6005 InvalidAdmin), `global_config` (`init`, space 949, `["global_config"]`),
   `system_program`, `event_authority` (`["__event_authority"]`), `program` (5 accounts).
3. **Args [B]**: `lp_fee_basis_points: u64`, `protocol_fee_basis_points: u64`,
   `protocol_fee_recipients: [Pubkey;8]`, `coin_creator_fee_basis_points: u64`,
   `admin_set_coin_creator_authority: Pubkey`.
4. **Errors [R]**: 6005 InvalidAdmin; 6000 FeeBasisPointsExceedsMaximum (`>= 1000` rejected
   by `require_gte!(1000, fee)`); 6011 AllProtocolFeeRecipientsShouldBeNonZero; 6012
   UnsortedNotUniqueProtocolFeeRecipients; System init errors.
5. **CPIs [R]**: System `create_account` via Anchor `init`; event log + `emit_cpi!`.
6. **State writes [R]**: admin (8), lp fee (40), protocol fee (48), disable_flags = 0 (56),
   protocol_fee_recipients (57), coin_creator_fee (313), admin_set_coin_creator_authority
   (321). `CreateConfigEvent` (log + CPI).
7. **GAP**: [R]**static-only**: the repo has no authentic fixed-admin successful replay;
   account/arg identity and the fixed admin are [B] (the address constant is in the code).

## 7. `collect_coin_creator_fee` @ 0x1d51d (byte 0xea8e8) **[B/R]**

1. **Purpose**: transfer the creator-vault quote balance to the coin creator.
2. **Accounts [R]** (`CollectCoinCreatorFee`): quote_mint, quote_token_program, coin_creator
   (unchecked), coin_creator_vault_authority (`["creator_vault", coin_creator]`),
   coin_creator_vault_ata (mut ATA of the vault authority), coin_creator_token_account (mut,
   mint=quote_mint, authority=coin_creator), `event_authority`, `program` (8 accounts).
3. **Args [B]**: none.
4. **Errors [R]**: 6048 CreatorVaultMigratedToSharingConfig (`coin_creator.owner == fees
   program`), 6023 Overflow; token errors.
5. **CPIs [R]**: `transfer_checked` from vault ATA -> creator ATA, authority = creator_vault
   PDA (signer), on `quote_token_program`.
6. **State writes [R]**: none (only token balances); `CollectCoinCreatorFeeEvent` (log + CPI).
   Zero balance returns early with `msg!("No coin creator fee to collect")`.
7. **GAP**: [R] body, [B] map/no-args.

## 8. `set_coin_creator` @ 0x1d56e (byte 0xeab70) **[B/R]**

1. **Purpose**: one-time assignment of `Pool.coin_creator` from Metaplex creators[0], else
   from the Pump bonding curve's creator.
2. **Accounts [R]** (`SetCoinCreator`): pool (mut), metadata (`["metadata", metaplex,
   pool.base_mint]` under Metaplex), bonding_curve (`["bonding-curve", pool.base_mint]` under
   Pump), `event_authority`, `program` (5 accounts).
3. **Args [B]**: none.
4. **Errors [R]**: 6028 OnlyCanonicalPumpPoolsCanHaveCoinCreator (pool.creator must equal
   `["pool-authority", base_mint]` under Pump); Metaplex/bonding-curve decode errors.
5. **CPIs [R]**: none (reads Metaplex metadata + Pump bonding curve).
6. **State writes [R]**: `pool.coin_creator` (211); if already non-default -> log
   `Pool has coin_creator already set` and return; emits `SetMetaplexCoinCreatorEvent` or
   `SetBondingCurveCoinCreatorEvent` (log + CPI).
7. **GAP**: [R] body; map/no-args [B].

## 9. `update_fee_config` @ 0x1c446 (byte 0xe2230) **[B/R]**

1. **Purpose**: update the fee schedule in `global_config` (no account creation).
2. **Accounts [R]** (`AdminGlobal`): admin signer, global_config (mut, `has_one = admin` ->
   6005 InvalidAdmin). No system/event accounts in the struct; `#[event_cpi]` adds the event
   authority/program pair implicitly.
3. **Args [B]**: same 5 as create_config: `lp_fee_basis_points`, `protocol_fee_basis_points`,
   `protocol_fee_recipients[8]`, `coin_creator_fee_basis_points`,
   `admin_set_coin_creator_authority`.
4. **Errors [R]**: 6005, 6000 (each fee > 1000), 6011, 6012.
5. **CPIs [R]**: none external; event log + `emit_cpi!`.
6. **State writes [R]**: offsets 40, 48, 57, 313, 321; `UpdateFeeConfigEvent` (log + CPI).
7. **GAP**: [R] body; args/map [B]. Whole handler body is 2,912 bytes and was the subject of
   the pass-12/AMM scalar work; the normalized body match is NOT claimed.

## 10. `buy_exact_quote_in` @ 0x1cfb1 (byte 0xe7d88) **[B/R]**

Same as `buy` but `exact=true`: arg `spendable_quote_in` is the quote budget and
`min_base_amount_out` the limit. Charges the quote fee first, requires
`net > 0` (6039), computes the base output from the net curve amount, requires
`out >= limit` (6040), and grosses up the quote transfer by the Token-2022 fee. Accounts =
`LegacyBuy`; state/event = `BuyEvent` with `ix_name = "buy_exact_quote_in"`; no pool fee
accrual.

## 11. `buy_v2` @ 0x1d15d (byte 0xe8ae8) **[B/R]**

1. **Purpose**: V2 buy path (no protocol recipient account; fees accrue in the pool;
   buyback recipient account required).
2. **Accounts [R]** (`TradeV2`): pool (mut; four `has_one`s), user signer, global_config,
   base_mint, quote_mint, user_base/quote ATAs, pool_base/quote ATAs, base/quote token
   programs, system_program, user_volume_accumulator (`init_if_needed`, 137),
   fee_config (`["fee_config", pump_amm]` under fees), buyback_fee_recipient (mut unchecked),
   event_authority, program.
3. **Args [B]**: `base_amount_out: u64`, `max_quote_amount_in: u64`.
4. **Errors [R]**: 6020 DisabledBuy, 6080 MayhemPoolNotSupported, 6079
   CashbackCoinNotSupported, 6039/6040/6016/6004, 6083 FeeConfigTooShort, 6082 FeeTiersEmpty,
   6023/6024/6025, 6053/6054/6055/6058, 6087.
5. **CPIs [R]**: base/quote `transfer_checked` (user->pool, pool->buyback), pool PDA signer for
   pool-side transfers; no fees-program or ATA CPI on this path (the fee config is read
   directly; buyback recipient must already be the correct ATA).
6. **State writes [R]**: `pool.protocol_fees += net protocol` (271),
   `pool.creator_fees += creator_fee` (279), `pool.virtual_quote_reserves -=
   (protocol+creator accrual)` (245); `BuyEvent` (log + CPI) with `ix_name="buy_v2"`.
7. **GAP**: [R] body; map/args [B]. V2 fee selection is complex (tiers/exotic/stable); see
   `trade.rs::fees`.

## 12. `buy_exact_quote_in_v2` @ 0x1d1e2 (byte 0xe8f10) **[B/R]**

Same `TradeV2` context and state writes as `buy_v2`, mode 2: args
`spendable_quote_in: u64, min_base_amount_out: u64`, computes `available = amount - fee`,
requires `estimate > 0` (6039), `out >= limit` (6040), emits `ix_name =
"buy_exact_quote_in_v2"`.

## 13. `sell_v2` @ 0x1d267 (byte 0xe9338) **[B/R]**

Same `TradeV2` context, mode 1: args `base_amount_in: u64, min_quote_amount_out: u64`.
Transfers base user->pool and quote pool->user first, then the buyback fee; accrues
`protocol_fees`/`creator_fees`, decrements `virtual_quote_reserves`; `SellEvent` (log + CPI)
with `protocol_fee_recipient = default`. Errors: 6021 DisabledSell, 6004, 6063, 6023/6024/
6025, 6080/6079/6083/6082.

## 14. `multi_hop_swap` @ 0x1d2ec (byte 0xe9760) **[B/R partial]**

1. **Purpose**: route `amount_in` across a sequence of PumpSwap pools (and Pump bonding
   curves) to `user_out_token_account`, requiring `current >= min_amount_out`.
2. **Accounts [R]** (`MultiHop` + 5-account `AmmHop` groups in `remaining_accounts`):
   `user` signer, `user_in_token_account`, `user_out_token_account`, `global_config`,
   `fee_config` (`["fee_config", pump_amm]` under fees), `user_volume_accumulator`
   (`init_if_needed`, 137), `buyback_fee_recipient`, `token_program`, `token_2022_program`,
   `system_program`, `event_authority`, `program`, `pump_program` (6EF8...), `pump_global`,
   `pump_fee_config`, `pump_event_authority`. Each AMM hop group is
   `[base_mint, quote_mint, pool, pool_base_token_account, pool_quote_token_account]` with
   the four `has_one`s on `pool`.
3. **Args [B]**: `amount_in: u64`, `min_amount_out: u64`.
4. **Errors [R]**: 6084 MultiHopDiscontinuousPath, 6085 MultiHopCurveRunMismatch,
   6086 MultiHopMixedDirection, 6078 OnlyPumpPools, 6079/6080, 6004, 6023/6024/6025,
   6044 NotEnoughRemainingAccounts, 6003/6001/6002, 6087.
5. **CPIs [R]**: per hop: token `transfer_checked` (PDA-signed where selling from a pool),
   Pump `buy`/`sell` via `invoke_signed` (Pump id at `0x11e55e`, 6EF8...) with the captured
   Pump event/fee accounts; `get_return_data` must report 16 bytes from Pump
   (6085 otherwise); self `emit_cpi!` events via the event authority.
6. **State writes [R]**: per-pool `protocol_fees`/`creator_fees`/`virtual_quote_reserves`
   updated by V2-hop math; no direct AMM config writes; events log + CPI.
7. **GAP**: **partial**: the repo's multi_hop note says arbitrary hop counts, native/WSOL
   variants, other quote currencies, completion/migration, Token-2022 extensions and
   holder/cashback/mayhem modes remain incomplete; the deployed binary has no CurveDepth cap
   in the AMM itself (the cap lives in the Pump router).

## 15. `sweep_protocol_fee` @ 0x1d372 (byte 0xe9b90) **[B/R]**

1. **Purpose**: pay `pool.protocol_fees` out of the pool quote vault to a configured protocol
   recipient and zero the bucket.
2. **Accounts [R]** (`SweepFees`): payer signer, global_config, pool (mut; `has_one`
   quote_mint/pool_quote_token_account), quote_mint, quote_token_program, pool_quote_token_account
   (mut), recipient (unchecked), recipient_token_account (mut ATA of recipient),
   system_program, associated_token_program.
3. **Args [B]**: none (`creator=false`).
4. **Errors [R]**: 6013 InvalidProtocolFeeRecipient (must be in
   `protocol_fee_recipients` for normal pools, or reserved recipient(s) for mayhem),
   6023/6024, 6087, 6027 AccountTypeNotSupported (token type).
5. **CPIs [R]**: optional ATA create; `transfer_checked` pool vault->recipient ATA, pool PDA
   signer; optional System top-up of a short pool account.
6. **State writes [R]**: `pool.virtual_quote_reserves += amount` (245),
   `pool.protocol_fees = 0` (271); `SweepPoolFeeEvent{bucket=0}` (log + CPI). Zero amount
   returns early.
7. **GAP**: [R] body; map/no-args [B].

## 16. `sweep_creator_fee` @ 0x1d3f8 (byte 0xe9fc0) **[B/R]**

Same as `sweep_protocol_fee` with `creator=true`: recipient must equal
`["creator_vault", pool.coin_creator]` under pump_amm (ConstraintSeeds, not a PumpAmm error);
pays `pool.creator_fees` and zeroes it; `SweepPoolFeeEvent{bucket=1}`; virtual reserves
increase by the amount.

## 17. `extend_account` @ 0x1d47e (byte 0xea3f0) **[B/R]**

1. **Purpose**: rent-fund and resize a program-owned account to the current schema size.
2. **Accounts [R]**: `account` (mut, owner = pump_amm), `user` (mut signer),
   `system_program`.
3. **Args [B]**: none.
4. **Errors [R]**: 6027 AccountTypeNotSupported (unknown discriminator), 6023 Overflow.
5. **CPIs [R]**: System transfer for the rent delta; `realloc` (Anchor).
6. **State writes [R]**: target size by discriminator: `Pool` -> 301, `GlobalConfig` -> 949,
   `UserVolumeAccumulator` -> 137, `202,42,246,43,142,190,30,255` -> 600 (Pump's bonding
   curve/user-volume style account). Current size >= target returns early.
   `ExtendAccountEvent` (log + CPI).
7. **GAP**: [R] body; map/no-args [B].

## 18. `transfer_creator_fees_to_pump` @ 0x1d846 (byte 0xec230) **[B/R]**

1. **Purpose**: unwrap a WSOL creator vault ATA and forward the lamports to Pump's canonical
   creator vault.
2. **Accounts [R]** (`TransferCreatorFeesToPump`): `wsol_mint` (`address = WSOL` -> 6007
   UnsupportedQuoteMint), token_program, system_program, associated_token_program,
   coin_creator (unchecked), coin_creator_vault_authority (`["creator_vault", coin_creator]`),
   coin_creator_vault_ata (mut ATA of authority), pump_creator_vault
   (`["creator-vault", coin_creator]` under Pump).
3. **Args [B]**: none.
4. **Errors [R]**: 6007, 6023.
5. **CPIs [R]**: Token `close_account` of the vault ATA (authority = creator_vault PDA),
   ATA `create` of a WSOL ATA, System transfer of the authority lamports to the Pump creator
   vault.
6. **State writes [R]**: none (lamport/token movement only); no event in this legacy path.
7. **GAP**: [R] body; map/no-args [B].

## 19. `transfer_creator_fees_to_pump_v2` @ 0x1d898 (byte 0xec4c0) **[B/R]**

1. **Purpose**: same as above but quote-generic: for WSOL it uses the unwrap path; for other
   quotes it creates the Pump creator-vault ATA and transfers the whole vault ATA balance.
2. **Accounts [R]** (`TransferCreatorFeesToPumpV2`): payer signer, quote_mint, token_program,
   system_program, associated_token_program, coin_creator, coin_creator_vault_authority,
   coin_creator_vault_ata, pump_creator_vault, pump_creator_vault_ata (mut, ATA of the Pump
   creator vault).
3. **Args [B]**: none.
4. **Errors [R]**: 6023, token/ATA errors (no 6007).
5. **CPIs [R]**: optional ATA create; token `transfer_checked` vault ATA -> Pump creator ATA
   with the creator-vault PDA signer; WSOL branch as in #18.
6. **State writes [R]**: none; no event.
7. **GAP**: [R] body; map/no-args [B].

## 20. `migrate_pool_coin_creator` @ 0x1d8e7 (byte 0xec738) **[B/R]**

1. **Purpose**: repoint `pool.coin_creator` from the old key to the fees-program
   `sharing_config` PDA, migrating future creator fees to fee sharing.
2. **Accounts [R]**: `pool` (mut, PDA seeds `["pool", index, creator, base_mint, quote_mint]`),
   `sharing_config` (`["sharing-config", pool.base_mint]` under fees program; constraints
   mint == pool.base_mint -> 6045, admin == pool.coin_creator -> 6046).
3. **Args [B]**: none.
4. **Errors [R]**: 6074 HolderRewardCreatorImmutable, 6081 CreatorFeesNotSwept,
   6045 InvalidSharingConfigBaseMint, 6046 InvalidSharingConfigCoinCreator.
5. **CPIs [R]**: none.
6. **State writes [R]**: `pool.coin_creator` (211);
   `MigratePoolCoinCreatorEvent` (log + CPI).
7. **GAP**: [R] body; map/no-args [B].

## 21. `claim_cashback` @ 0x1da42 (byte 0xed210) **[B/R]**

1. **Purpose**: pay the accumulated cashback quote tokens from the user-volume accumulator to
   the user.
2. **Accounts [R]** (`ClaimCashback`): user (mut unchecked; destination authority),
   user_volume_accumulator (`["user_volume_accumulator", user]`), quote_mint,
   quote_token_program, user_volume_accumulator_wsol_token_account
   (mut ATA of the accumulator), user_wsol_token_account (mut, mint/authority=user),
   system_program, event_authority, program.
3. **Args [B]**: none.
4. **Errors [R]**: 6023 Overflow on the cumulative counter; token errors.
5. **CPIs [R]**: `transfer_checked` accumulator ATA -> user ATA, accumulator PDA signer.
6. **State writes [R]**: `user_volume_accumulator.total_cashback_claimed += amount` (82);
   `ClaimCashbackEvent` (log + CPI).
7. **GAP**: [R] body; map/no-args [B].

## 22. `update_buyback_config` @ 0x1dacc (byte 0xed660) **[B/R]**

1. **Purpose**: optionally set `buyback_basis_points` and optionally replace the 8 buyback
   fee recipients.
2. **Accounts [R]** (`AdminGlobal`): admin signer, global_config (mut, `has_one = admin` ->
   6005); plus event accounts; `remaining_accounts` optional exactly 8 recipient keys.
3. **Args [B]**: `buyback_basis_points: Option<u64>` (codec length prelude; the
   `0x14`/kind-placement delta analysed in `structure_proposals.md` is in this wrapper's
   exit/error path).
4. **Errors [R]**: 6005, 6056 BuybackBasisPointsOutOfRange (> 10,000), 6057
   WrongBuybackFeeRecipientsCount, 6054 AllBuybackFeeRecipientsShouldBeNonZero, 6055
   NotUniqueBuybackFeeRecipients.
5. **CPIs [R]**: none.
6. **State writes [R]**: `global_config.buyback_basis_points` (899) when Some;
   `buyback_fee_recipients` (643) when 8 remaining accounts are present. No event.
7. **GAP**: **the pass-index marks the wrapper "no normalized match"**; the delta is the
   one-instruction error-path constant placement (see `structure_proposals.md`), not the
   handler semantics.

## 23. `admin_cto_pool` @ 0x1d5fe (byte 0xeaff0) **[B/R]**

1. **Purpose**: admin coin-creator takeover; optionally sets holder-reward/cashback and a
   configurable creator fee.
2. **Accounts [R]** (`AdminCtoPool`): payer signer (mut), global_config, pool (mut),
   pool_authority (signer, `["pool-authority", pool.base_mint]` under Pump),
   system_program.
3. **Args [B]**: `coin_creator: Pubkey`, `is_holder_reward: bool`,
   `creator_fee_bps: Option<u64>`.
4. **Errors [R]**: 6075 CtoNotAllowedForMayhemPool, 6074 HolderRewardCreatorImmutable,
   6076 InvalidHolderRewardCoinCreator, 6077 CreatorFeeNotConfigurableForQuote,
   6071 CreatorFeeNotAllowedForCashbackCoin, 6068 CreatorFeeNotConfigurable, 6069
   CreatorFeeBpsOutOfRange, 6081 CreatorFeesNotSwept, 6028, 6023.
5. **CPIs [R]**: System rent top-up + `realloc(287)` if the pool account is short; event log +
   `emit_cpi!`.
6. **State writes [R]**: `pool.coin_creator` (211), `pool.is_holder_reward` (270),
   `pool.can_edit_creator_fee = false` (269), `pool.creator_fee_bps` (261) when Some,
   `pool.is_cashback_coin = false` when holder reward; `AdminCtoPoolEvent` (log + CPI).
7. **GAP**: [R] body; this is the "unmapped/IDL-only" name from the 31-entry IDL; the real
   deployed name is `admin_cto_pool` (disc `2d3da597680031bd`).

## 24. `toggle_mayhem_mode` @ 0x1d701 (byte 0xeb808) **[B/R]**

`AdminGlobal` (admin signer + global_config `has_one=admin`). Arg `enabled: bool`; requires
the value to differ (6043 MayhemModeInDesiredState); writes `mayhem_mode_enabled` (417);
emits no event (the `#[event_cpi]` accounts are still parsed). Bool ABI check in the codec.

## 25. `toggle_cashback_enabled` @ 0x1d977 (byte 0xecbb8) **[B/R]**

`AdminGlobal`; arg `enabled: bool`; requires difference (6051 CashbackNotInDesiredState);
writes `is_cashback_enabled` (642); event accounts parsed, no event.

## 26. `toggle_boost` @ 0x1d7cc (byte 0xebe60) **[B/R]**

`AdminGlobalNoEvent` (admin signer + global_config, no event accounts). Arg `enabled: bool`;
requires `boost_authority != default` (6005 InvalidAdmin); writes `boost_enabled` (939); no
event.

## 27. `set_boost_authority` @ 0x1c839 (byte 0xe41c8) **[B/R]**

`SetBoostAuthority` (admin signer, global_config `has_one`, boost_authority unchecked,
system_program). No args; tops up/`realloc`s global_config to 949 if short; writes
`boost_authority` (907); emits `SetBoostAuthorityEvent{old,new}` (log + CPI).

## 28. `update_creator_fee_config` @ 0x1c565 (byte 0xe2b28) **[B/R]**

`UpdateCreatorFeeConfig` (admin signer, global_config `has_one`, system_program). Args
`creator_fee_configurable: bool`, `max_configurable_creator_fee_bps: u64`; tops up/`realloc`s
to 949; writes offsets 940/941; emits `UpdateCreatorFeeConfigEvent` (log + CPI).

## 29. `init_boost` @ 0x1c7b3 (byte 0xe3d98) **[B/R]**

`InitBoost` (pool with four `has_one`s, global_config, creator signer, base/quote mints,
pool base/quote ATAs, boost_vault_authority `["boost_vault", pool]`, boost_vault
`init_if_needed` ATA of the authority, quote_token_program, system_program,
associated_token_program). No args. Silently returns if the creator is not the canonical
Pump pool authority, or effective reserves (virtual + protocol/creator fees) != 0, or boost
is disabled. Otherwise transfers `base_amount*quote_amount/1e15` from the pool quote vault to
the boost vault (pool PDA signer), sets `pool.virtual_quote_reserves = amount` (245), emits
`InitBoostEvent` (log + CPI). No error codes for the silent gates; token/overflow (6023/6024)
otherwise.

## 30. `boost_buy_and_burn` @ 0x1c8e7 (byte 0xe4738) **[B/R]**

`BoostBuyAndBurn` (pool with four `has_one`s read-only here, authority signer,
global_config, base_mint, quote_mint, pool base/quote ATAs, boost_vault_authority, boost_vault
mut ATA, base/quote token programs). Args `quote_amount_in: u64, min_base_amount_burned: u64`.
Requires stored `boost_authority == signer` and != default (6005), `boost_enabled` (6066
BoostDisabled), buy not disabled (6020), effective reserves != 0 (6065 PoolCannotBoost),
`used = min(requested, vault)` > 0 (6002), net of Token-2022 fee > 0, burned > 0 (6001),
`burned >= minimum` (6004), `old_base > burned` (6003). Transfers quote boost_vault ->
pool_quote (authority = boost PDA), burns base from the pool base vault (pool PDA), reloads,
emits a synthetic `BuyEvent` (`ix_name="buy_exact_quote_in"`) + `BoostBuyAndBurnEvent`
(log + CPI); if the boost vault is empty, optionally harvests withheld Token-2022 fees to
the mint (requires the mint writable, 6088 QuoteMintNotWritable) and closes the vault to the
authority. State: only token balances; `pool.protocol_fees`/`creator_fees` unchanged.

## 31. `set_reserved_fee_recipients` @ 0x1c98d (byte 0xe4c68) **[B/R]**

`SetReservedFeeRecipients` (global_config PDA `has_one=admin`, admin signer). Arg
`whitelist_pda: Pubkey`. Requires exactly >=8 `remaining_accounts` (6044
NotEnoughRemainingAccounts), each non-default (6011); writes `whitelist_pda` (353),
`reserved_fee_recipient = r[0]` (385), `reserved_fee_recipients = r[1..8]` (418); emits
`ReservedFeeRecipientsEvent` (log + CPI).

## 32. `disable` @ 0x1c2a1 (byte 0xe1508) **[B/R]**

`AdminGlobal` (admin signer, global_config `has_one=admin`). Args `disable_create_pool,
disable_deposit, disable_withdraw, disable_buy, disable_sell: bool` (5 bytes, each bool-ABI
checked). Rewrites the low 5 bits of `disable_flags` (56) preserving the rest; emits
`DisableEvent` (log + CPI). No other guards.

## 33. `update_admin` @ 0x1c398 (byte 0xe1cc0) **[B/R]**

`UpdateAdmin` (admin signer, global_config `has_one=admin`, new_admin unchecked). No args;
writes `global_config.admin` (8) = `new_admin.key()`; emits `UpdateAdminEvent` (log + CPI).

## 34. `admin_update_token_incentives` @ 0x1cb9d (byte 0xe5ce8) **[B/R]**

`AdminUpdateTokenIncentives` (admin signer, global_config `has_one=admin`,
global_volume_accumulator `["global_volume_accumulator"]`, mint,
global_incentive_token_account `init_if_needed` ATA of the accumulator,
associated_token_program, system_program, token_program). Args `start_time: i64,
end_time: i64, seconds_in_a_day: i64, day_number: u64, token_supply_per_day: u64`.
Sets `g.mint` (32) and `g.seconds_in_a_day` (24); if start/end nonzero: resets schedules on a
new start_time (6008 StartTimeInThePast if not future, 6009 EndTimeInThePast, 6010
EndTimeBeforeStartTime, 6011 TimeRangeTooLarge if >= 30 days, 6012 EndTimeBeforeCurrentDay),
zeroes future sol_volumes; if token_supply_per_day > 0: 6013 SupplyUpdateForFinishedRange,
6014 DayIndexAfterEndIndex, 6015 DayInActiveRange; writes `total_token_supply[day]` (64+8*day)
or the whole active range. Emits `AdminUpdateTokenIncentivesEvent` (log + CPI).

## 35. `claim_token_incentives` @ 0x1cc57 (byte 0xe62b8) **[B/R]**

`ClaimTokenIncentives` (user unchecked, user_ata `init_if_needed` ATA of user,
global_volume_accumulator `has_one=mint` -> 6016 InvalidIncentiveMint,
global_incentive_token_account, user_volume_accumulator PDA, mint, token_program,
system_program, associated_token_program, event_authority, program, payer signer). No args.
Runs the recovered accumulator update (previous-day reward =
`current_sol_volume * total_token_supply[prev_day] / sol_volumes[prev_day]`, Truncation 6024
on overflow), sets `needs_claim`, `last_update_timestamp`, `current_sol_volume = 0`; if
`total_unclaimed_tokens == 0` returns with `msg!("No tokens to claim")`; otherwise transfers
from the incentive ATA with the accumulator PDA signer and zeroes the unclaimed counter,
adds to `total_claimed_tokens` (49), sets `has_total_claimed_tokens`. Emits
`ClaimTokenIncentivesEvent` (log + CPI).

## 36. `init_user_volume_accumulator` @ 0x1cce2 (byte 0xe6710) **[B/R]**

`InitUserVolumeAccumulator` (payer signer mut, user unchecked, user_volume_accumulator
`init_if_needed` 137 `["user_volume_accumulator", user]`, system_program). No args; sets
`u.user = user.key()` (8); emits `InitUserVolumeAccumulatorEvent{payer,user,ts}` (log + CPI).

## 37. `close_user_volume_accumulator` @ 0x1cd93 (byte 0xe6c98) **[B/R]**

`CloseUserVolumeAccumulator` (user signer mut, user_volume_accumulator PDA `close = user`).
No args; emits `CloseUserVolumeAccumulatorEvent` (user, ts, total_unclaimed/claimed,
current_sol_volume, last_update_timestamp) then the Anchor close returns the lamports to the
user. No other writes.

## 38. `sync_user_volume_accumulator` @ 0x1ce17 (byte 0xe70b8) **[B/R]**

`SyncUserVolumeAccumulator` (user unchecked, global_volume_accumulator PDA,
user_volume_accumulator PDA mut). No args. If `now < g.start_time && u.last_update_timestamp
< g.start_time`, resets `u.total_claimed_tokens = 0` and `has_total_claimed_tokens = false`;
only if the value changed emits `SyncUserVolumeAccumulatorEvent{before,after,ts}` (log + CPI).
No error codes.

---

## Cross-cutting notes / gaps

- **Tag honesty**: handler identities, discriminators, arg codecs for the priority handlers,
  program-id constants, and the account/state layout tables are [B]. The account constraints,
  body arithmetic and CPI ordering are [R] from the reconstruction; I did not re-run the
  repo harness.
- **No byte identity**: repo pass-12 records `pump_amm` 1,196,544 candidate bytes vs
  10,485,715 original, 670,791 differing common bytes, 9,289,171 excess; 306 original
  windows remain without normalized matches.
- **`admin_set_coin_creator`** from the 31-entry IDL is not deployed under that name; the
  deployed instruction is `admin_cto_pool` (#23).
- **`create_pool` args**: the deployed codec at `0x1c6a1..0x1c6f0` confirms the 9-argument
  (3 optional) form, so the 31-entry IDL's 6-arg form is stale. The upstream 38-name IDL also
  shows the 6-arg form; use the source/codec for this instruction.
- **create_config**: the repo marks it static-only (no authentic successful fixed-admin
  replay); the fixed admin constant `8LWu7QM2dGR1G8nKDHthckea57bkCzXyBTAKPJUBDHo8` is [B] in
  the code.
- The reconstruction has known gaps the specs inherit: multi-hop breadth, some V2 fee-tier
  paths, and exact CPI ordering under Token-2022 extensions. They are flagged per handler.
