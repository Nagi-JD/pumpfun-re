> **[Claude verification note]** Correction to the pump instruction count below:
> pump deploys **55 named instructions (not 54)**. `add_quote_control_mint` (020e3d8aaa8e0e5f)
> IS deployed — correct catch. BUT `collect_creator_fee_v2` (cf118af204221338) and
> `update_buyback_config` (fbe0ab92a01a71e9) are ALSO deployed: both are real dispatcher
> entries (lddw+jeq→handler at 0x2377f and 0x237c3). The claim that they are "not deployed"
> is WRONG — verified by enumerating the pump dispatcher (55 named dispatch entries match
> sha256("global:"+name)). BondingCurve disc = 17b7f83760d8ac60 everywhere: confirmed.

# Discriminator catalogs (deployed programs)

Private analysis for the user. Tags: **[B]** = the 8-byte value is present at the cited
site in the deployed bytes. No byte-identity or behavioral claim.

Method: instructions/events/accounts use the Anchor hash of the logged/logical name
(`sha256("global:"+name)[:8]`, `"event:"+name`, `"account:"+name`), then the raw bytes and
`lddw` immediates are searched in the corresponding ELF. Instruction "lddw" is the
dispatcher constant; "handler" is the pc (sbftool index) and byte address
(`pc*8`). Event/account "lddw" cites the compare/serializer load; "rodata" is the raw
byte offset. `S` = self-owned, `P` = pump-owned, `A` = pump_amm-owned, `F` = fees-owned,
`M` = mayhem-owned.

> The three name-spaces collide across programs by design (e.g. `buy`, `sell`,
> `update_fee_config`): the discriminator depends only on the name, so the same 8 bytes
> occur in multiple programs; the program id disambiguates. The self-CPI tag
> `e445a52e51cb9a1d` is **not** an instruction/event/account discriminator; it is the Anchor
> `emit_cpi!` receive/dispatch tag (see the mayhem dispatcher pseudo-entry at `0x10487` and
> the AMM `emit_event`).

## pump

### Instructions (54)

| instruction | disc | lddw | handler pc | handler byte |
|---|---|---|---:|---:|
| `initialize` | `afaf6d1f0d989bed` | 0x236fd | 0x2421b | 0x1210d8 |
| `update_global_authority` | `e3b54ac4d01561d5` | 0x23701 | 0x24261 | 0x121308 |
| `toggle_create_v2` | `1cffe6f0ac6bcbab` | 0x23707 | 0x2430e | 0x121870 |
| `toggle_cashback_enabled` | `7367e0ffbd5956c3` | 0x2370b | 0x243d8 | 0x121ec0 |
| `update_holder_reward_config` | `e1fc4204c723ec10` | 0x2370f | 0x244a2 | 0x122510 |
| `set_max_curve_depth` | `209a98db8e6cdaa5` | 0x23713 | 0x24566 | 0x122b30 |
| `toggle_mayhem_mode` | `01096fd0641fffa3` | 0x23717 | 0x245dc | 0x122ee0 |
| `update_creator_fee_config` | `3dafa0f9424288af` | 0x2371b | 0x246a6 | 0x123530 |
| `add_quote_mint` | `6f79153828185ed1` | 0x2371f | 0x24774 | 0x123ba0 |
| `remove_quote_mint` | `b141df2658d19e9b` | 0x23723 | 0x24826 | 0x124130 |
| `set_virtual_quote_reserves` | `6587bf6809581460` | 0x23727 | 0x248d8 | 0x1246c0 |
| `set_params` | `1beab2349302bb8d` | 0x2372b | 0x2494e | 0x124a70 |
| `set_mayhem_virtual_params` | `3da9bcbf99952a61` | 0x2372f | 0x24ab5 | 0x1255a8 |
| `set_reserved_fee_recipients` | `6faca2e87259d58e` | 0x23733 | 0x24b5d | 0x125ae8 |
| `create` | `181ec828051c0777` | 0x23737 | 0x24c1b | 0x1260d8 |
| `create_v2` | `d6904cec5f8b31b4` | 0x2373b | 0x24d15 | 0x1268a8 |
| `buy_v2` | `b817ee6167c5d33d` | 0x2373f | 0x24ea2 | 0x127510 |
| `buy_exact_quote_in_v2` | `c2ab1c46684d5b2f` | 0x23743 | 0x24f6b | 0x127b58 |
| `sell_v2` | `5df6823ce7e940b2` | 0x23747 | 0x25034 | 0x1281a0 |
| `buy_v3` | `07051dc4f5176550` | 0x2374b | 0x250d9 | 0x1286c8 |
| `buy_exact_quote_in_v3` | `e1f7501ed5b38488` | 0x2374f | 0x25185 | 0x128c28 |
| `sell_v3` | `1c92de7726c469d5` | 0x23753 | 0x25231 | 0x129188 |
| `multi_hop_curve_swap` | `e19a7516d756f667` | 0x23757 | 0x252b8 | 0x1295c0 |
| `sweep_protocol_fee` | `0830be07b644b7e5` | 0x2375b | 0x25376 | 0x129bb0 |
| `sweep_creator_fee` | `20f6bf3408c949ba` | 0x2375f | 0x25409 | 0x12a048 |
| `buy` | `66063d1201daebea` | 0x23763 | 0x2549c | 0x12a4e0 |
| `buy_exact_sol_in` | `38fc74089edfcd5f` | 0x23767 | 0x25579 | 0x12abc8 |
| `sell` | `33e685a4017f83ad` | 0x2376b | 0x25656 | 0x12b2b0 |
| `migrate` | `9beae792ec9ea21e` | 0x2376f | 0x256fb | 0x12b7d8 |
| `migrate_v2` | `bbcb121fceedfe29` | 0x23773 | 0x25749 | 0x12ba48 |
| `extend_account` | `ea66c2cb96483ee5` | 0x23777 | 0x257cf | 0x12be78 |
| `collect_creator_fee` | `1416567bc61cdb84` | 0x2377b | 0x2586e | 0x12c370 |
| `distribute_fee_to_holders` | `623691610246ad2b` | 0x23783 | 0x258fa | 0x12c7d0 |
| `set_metaplex_creator` | `8a60aed93055c5f6` | 0x23787 | 0x259f2 | 0x12cf90 |
| `set_creator` | `fe94ff70cf8eaaa5` | 0x2378b | 0x25a82 | 0x12d410 |
| `admin_cto` | `7d7ed6864de5bc59` | 0x2378f | 0x25b40 | 0x12da00 |
| `admin_update_token_incentives` | `d10b7357d5177ccc` | 0x23793 | 0x25c54 | 0x12e2a0 |
| `claim_token_incentives` | `1004471ccc01281b` | 0x23797 | 0x25d0e | 0x12e870 |
| `claim_cashback` | `253a237ebe35e4c5` | 0x2379b | 0x25d99 | 0x12ecc8 |
| `claim_cashback_v2` | `7af3cc415e741d37` | 0x2379f | 0x25e2a | 0x12f150 |
| `init_user_volume_accumulator` | `5e06ca73ff60e8b7` | 0x237a3 | 0x25ebc | 0x12f5e0 |
| `close_user_volume_accumulator` | `f945a4da9667548a` | 0x237a7 | 0x25f6d | 0x12fb68 |
| `sync_user_volume_accumulator` | `561fc057a3574fee` | 0x237ab | 0x25ff1 | 0x12ff88 |
| `admin_set_idl_authority` | `08d960e79068c005` | 0x237af | 0x260a3 | 0x130518 |
| `migrate_bonding_curve_creator` | `577c34bf3426d6e8` | 0x237b3 | 0x26118 | 0x1308c0 |
| `get_minimum_distributable_fee` | `75e17fca865f4423` | 0x237b7 | 0x261a8 | 0x130d40 |
| `distribute_creator_fees` | `a572670079cef751` | 0x237bb | 0x26225 | 0x131128 |
| `distribute_creator_fees_v2` | `ffcb134ff444089f` | 0x237bf | 0x262dd | 0x1316e8 |
| `initialize_quote_control` | `ef49f5add1b15442` | 0x237c7 | 0x264a2 | 0x132510 |
| `set_quote_control_admin` | `3e4fa1d3a5aad6d2` | 0x237cb | 0x264e3 | 0x132718 |
| `remove_quote_control_mint` | `df07fd1a51a5daa6` | 0x237d3 | 0x26667 | 0x133338 |
| `set_quote_control_reserves_admin` | `a1c3dea5e165c03e` | 0x237d7 | 0x26728 | 0x133940 |
| `set_quote_control_mint_reserves` | `74dc6b53bf2c2049` | 0x237db | 0x267e9 | 0x133f48 |
| `add_quote_control_mint` | `020e3d8aaa8e0e5f` | 0x237cf | ~0x265d5 | 0x132ea8 |

### Events (32)

| event | disc | lddw | rodata | note |
|---|---|---|---|---|
| `AddQuoteControlMintEvent` | `a4af574a582d213e` | 0xd6e4, 0xd742 | - | default Anchor event hash |
| `AdminCtoEvent` | `6e7ce262aaff1178` | 0x17836 | - | default Anchor event hash |
| `AdminSetIdlAuthorityEvent` | `f53b46224bb96d5c` | 0x1485d | - | default Anchor event hash |
| `AdminUpdateTokenIncentivesEvent` | `93fa6c78f71d43de` | 0xe937, 0xe98b | - | default Anchor event hash |
| `ClaimCashbackEvent` | `e2d6f62107f293e5` | 0x1f677 | - | default Anchor event hash |
| `ClaimTokenIncentivesEvent` | `4facf631cd5bcee8` | 0xec26, 0xec7d | - | default Anchor event hash |
| `CloseUserVolumeAccumulatorEvent` | `929fbdac925838f4` | 0xf3ca, 0xf418 | - | default Anchor event hash |
| `CollectCreatorFeeEvent` | `7a027f010ebf0caf` | 0x557f, 0x55d1 | - | default Anchor event hash |
| `CompleteEvent` | `5f72619cd42e9808` | 0x10d72, 0x10dd7 | - | default Anchor event hash |
| `CompletePumpAmmMigrationEvent` | `bde95db95c94ea94` | 0x1ab24 | - | default Anchor event hash |
| `CreateEvent` | `1b72a94ddeeb6376` | 0x2c2cf | - | default Anchor event hash |
| `DistributeCreatorFeesEvent` | `a537817004b3ca28` | 0x189d8 | - | default Anchor event hash |
| `DistributeFeeToHoldersEvent` | `e3bed7ceb0b4a584` | 0x6eaa, 0x6f00 | - | default Anchor event hash |
| `ExtendAccountEvent` | `6161d7905d92167c` | 0x19a5b | - | default Anchor event hash |
| `InitUserVolumeAccumulatorEvent` | `86240d48e86582d8` | 0xf536, 0xf587 | - | default Anchor event hash |
| `MigrateBondingCurveCreatorEvent` | `9ba768dcd56cf303` | 0x70b1, 0x711d | - | default Anchor event hash |
| `MinimumDistributableFeeEvent` | `a8d884efebb63134` | 0x64f5 | - | default Anchor event hash |
| `PostCompleteBuyEvent` | `6fb06d8b316cd5fb` | 0x2c793 | - | default Anchor event hash |
| `RemoveQuoteControlMintEvent` | `2e21568600d5d130` | 0xd88e, 0xd8e8 | - | default Anchor event hash |
| `ReservedFeeRecipientsEvent` | `2bbcfa12dd4bbb5f` | 0xe32a, 0xe383 | - | default Anchor event hash |
| `SetCreatorEvent` | `ed347b25f5fb48d2` | 0x728d, 0x72e6 | - | default Anchor event hash |
| `SetMetaplexCreatorEvent` | `8ecb06207f69bfa2` | 0x73b7, 0x7418 | - | default Anchor event hash |
| `SetParamsEvent` | `dfc39ff63e308f83` | 0x2c7ee | - | default Anchor event hash |
| `SetQuoteControlAdminEvent` | `4af88d45ca511ef7` | 0xccc1, 0xcd23 | - | default Anchor event hash |
| `SetQuoteControlMintReservesEvent` | `a943276d6686b6e8` | 0xce5b, 0xceba | - | default Anchor event hash |
| `SetQuoteControlReservesAdminEvent` | `43fbb3b6575ca921` | 0xcfef, 0xd051 | - | default Anchor event hash |
| `SweepBondingCurveFeeEvent` | `742b4dbd117a482b` | 0x1e246 | - | default Anchor event hash |
| `SyncUserVolumeAccumulatorEvent` | `c57aa77c74515bff` | 0xf6af, 0xf6fb | - | default Anchor event hash |
| `TradeEvent` | `bddb7fd34ee661ee` | 0x2c4af | - | default Anchor event hash |
| `UpdateCreatorFeeConfigEvent` | `98c67c7c6af67fbf` | 0x26bf0, 0x26c3b | - | default Anchor event hash |
| `UpdateGlobalAuthorityEvent` | `b6c3892a23cecff7` | 0x2698a, 0x269e3 | - | default Anchor event hash |
| `UpdateMayhemVirtualParamsEvent` | `757be4b6a1a8dcd6` | 0x2704f, 0x270a1 | - | default Anchor event hash |

### Accounts (7)

| account | disc | owner | lddw | rodata |
|---|---|---|---|---|
| `BondingCurve` | `17b7f83760d8ac60` | S | 0x77b2, 0x1362e | 0x1b64ef |
| `FeeConfig` | `8f3492bbdb7b4c9b` | F | 0x22ae3 | - |
| `Global` | `a7e8e8b1c86c727f` | S | 0x77ad, 0x2bfbf | 0x1b64d7 |
| `GlobalVolumeAccumulator` | `ca2af62b8ebe1eff` | S | 0x77b7, 0x20233 | 0x1b64c7 |
| `QuoteControl` | `38f423eec1d5a2c9` | S | 0xd463, 0x1c86e | 0x1b64b7 |
| `SharingConfig` | `d84a0900388c5d4b` | F | 0x22bd3 | - |
| `UserVolumeAccumulator` | `56ff700e66359afa` | S | 0x77bc, 0xdb0c | 0x1b64af |

## pump_amm

### Instructions (38)

| instruction | disc | lddw | handler pc | handler byte |
|---|---|---|---:|---:|
| `admin_cto_pool` | `2d3da597680031bd` | 0x1b81b | 0x1d5fe | 0xeaff0 |
| `admin_update_token_incentives` | `d10b7357d5177ccc` | 0x1b7d7 | 0x1cb9d | 0xe5ce8 |
| `boost_buy_and_burn` | `694406af000723a2` | 0x1b7c7 | 0x1c8e7 | 0xe4738 |
| `buy` | `66063d1201daebea` | 0x1b7eb | 0x1cec9 | 0xe7648 |
| `buy_exact_quote_in` | `c62e1552b4d9e870` | 0x1b7ef | 0x1cfb1 | 0xe7d88 |
| `buy_exact_quote_in_v2` | `c2ab1c46684d5b2f` | 0x1b7fb | 0x1d1e2 | 0xe8f10 |
| `buy_v2` | `b817ee6167c5d33d` | 0x1b7f7 | 0x1d15d | 0xe8ae8 |
| `claim_cashback` | `253a237ebe35e4c5` | 0x1b837 | 0x1da42 | 0xed210 |
| `claim_token_incentives` | `1004471ccc01281b` | 0x1b7db | 0x1cc57 | 0xe62b8 |
| `close_user_volume_accumulator` | `f945a4da9667548a` | 0x1b7e3 | 0x1cd93 | 0xe6c98 |
| `collect_coin_creator_fee` | `a039592ab58b2b42` | 0x1b813 | 0x1d51d | 0xea8e8 |
| `create_config` | `c9cff3724b6f2fbd` | 0x1b7a5 | 0x1c17f | 0xe0bf8 |
| `create_pool` | `e992d18ecf6840bc` | 0x1b7bb | 0x1c634 | 0xe31a0 |
| `deposit` | `f223c68952e1f2b6` | 0x1b7cf | 0x1ca4f | 0xe5278 |
| `disable` | `b9adbb5ad80feee9` | 0x1b7a9 | 0x1c2a1 | 0xe1508 |
| `extend_account` | `ea66c2cb96483ee5` | 0x1b80f | 0x1d47e | 0xea3f0 |
| `init_boost` | `8ce9215e845ac28f` | 0x1b7bf | 0x1c7b3 | 0xe3d98 |
| `init_user_volume_accumulator` | `5e06ca73ff60e8b7` | 0x1b7df | 0x1cce2 | 0xe6710 |
| `migrate_pool_coin_creator` | `d0089f044aaf103a` | 0x1b82f | 0x1d8e7 | 0xec738 |
| `multi_hop_swap` | `2b644913e9f66f94` | 0x1b803 | 0x1d2ec | 0xe9760 |
| `sell` | `33e685a4017f83ad` | 0x1b7f3 | 0x1d099 | 0xe84c8 |
| `sell_v2` | `5df6823ce7e940b2` | 0x1b7ff | 0x1d267 | 0xe9338 |
| `set_boost_authority` | `e3954c2a8227eacd` | 0x1b7c3 | 0x1c839 | 0xe41c8 |
| `set_coin_creator` | `d295802dbc3a4eaf` | 0x1b817 | 0x1d56e | 0xeab70 |
| `set_reserved_fee_recipients` | `6faca2e87259d58e` | 0x1b7cb | 0x1c98d | 0xe4c68 |
| `sweep_creator_fee` | `20f6bf3408c949ba` | 0x1b80b | 0x1d3f8 | 0xe9fc0 |
| `sweep_protocol_fee` | `0830be07b644b7e5` | 0x1b807 | 0x1d372 | 0xe9b90 |
| `sync_user_volume_accumulator` | `561fc057a3574fee` | 0x1b7e7 | 0x1ce17 | 0xe70b8 |
| `toggle_boost` | `75a1a04adf897663` | 0x1b823 | 0x1d7cc | 0xebe60 |
| `toggle_cashback_enabled` | `7367e0ffbd5956c3` | 0x1b833 | 0x1d977 | 0xecbb8 |
| `toggle_mayhem_mode` | `01096fd0641fffa3` | 0x1b81f | 0x1d701 | 0xeb808 |
| `transfer_creator_fees_to_pump` | `8b348655e4e56cf1` | 0x1b827 | 0x1d846 | 0xec230 |
| `transfer_creator_fees_to_pump_v2` | `01214eb921432c5c` | 0x1b82b | 0x1d898 | 0xec4c0 |
| `update_admin` | `a1b028d53cb8b3e4` | 0x1b7af | 0x1c398 | 0xe1cc0 |
| `update_buyback_config` | `fbe0ab92a01a71e9` | 0x1b83b | 0x1dacc | 0xed660 |
| `update_creator_fee_config` | `3dafa0f9424288af` | 0x1b7b7 | 0x1c565 | 0xe2b28 |
| `update_fee_config` | `68b867f258976b14` | 0x1b7b3 | 0x1c446 | 0xe2230 |
| `withdraw` | `b712469c946da122` | 0x1b7d3 | 0x1caf6 | 0xe57b0 |

### Events (27)

| event | disc | lddw | rodata | note |
|---|---|---|---|---|
| `AdminCtoPoolEvent` | `2f23a3f9969d937a` | 0xfabc | - | default Anchor event hash |
| `AdminUpdateTokenIncentivesEvent` | `93fa6c78f71d43de` | 0x2c87, 0x2cdb | - | default Anchor event hash |
| `BoostBuyAndBurnEvent` | `3f451c16305cc2b9` | 0x120e1 | - | default Anchor event hash |
| `BuyEvent` | `67f4521f2cf57777` | 0x163ac | - | default Anchor event hash |
| `ClaimCashbackEvent` | `e2d6f62107f293e5` | 0xb7a4, 0xb7f3 | - | default Anchor event hash |
| `ClaimTokenIncentivesEvent` | `4facf631cd5bcee8` | 0xb599, 0xb5f0 | - | default Anchor event hash |
| `CloseUserVolumeAccumulatorEvent` | `929fbdac925838f4` | 0xb904, 0xb952 | - | default Anchor event hash |
| `CollectCoinCreatorFeeEvent` | `e8f5c2eeeada3a59` | 0x46a1, 0x46fe | - | default Anchor event hash |
| `CreateConfigEvent` | `6b34598137e25116` | 0x107c0 | - | default Anchor event hash |
| `CreatePoolEvent` | `b1310cd2a076a774` | 0x14be5 | - | default Anchor event hash |
| `DepositEvent` | `78f83d531f8e6b90` | 0x14fc6 | - | default Anchor event hash |
| `DisableEvent` | `6bfdc14ce4ca1b68` | 0x2f93, 0x2fe7 | - | default Anchor event hash |
| `ExtendAccountEvent` | `6161d7905d92167c` | 0x14f8e | - | default Anchor event hash |
| `InitBoostEvent` | `ae7c4af90451f611` | 0x11ad0 | - | default Anchor event hash |
| `InitUserVolumeAccumulatorEvent` | `86240d48e86582d8` | 0xba70, 0xbac1 | - | default Anchor event hash |
| `MigratePoolCoinCreatorEvent` | `aadd52c793a5f72e` | 0x48b4, 0x4920 | - | default Anchor event hash |
| `ReservedFeeRecipientsEvent` | `2bbcfa12dd4bbb5f` | 0x3572, 0x35cb | - | default Anchor event hash |
| `SellEvent` | `3e2f370aa503dc2a` | 0x172b3 | - | default Anchor event hash |
| `SetBondingCurveCoinCreatorEvent` | `f2e7eb664163bdd3` | 0x4b31, 0x4b93 | - | default Anchor event hash |
| `SetBoostAuthorityEvent` | `5980f08d5bca4769` | 0x3108, 0x3162 | - | default Anchor event hash |
| `SetMetaplexCoinCreatorEvent` | `966bc77b7ccf66e4` | 0x4c75, 0x4cd7 | - | default Anchor event hash |
| `SweepPoolFeeEvent` | `82a42461e48287a5` | 0x19079 | - | default Anchor event hash |
| `SyncUserVolumeAccumulatorEvent` | `c57aa77c74515bff` | 0xbbe9, 0xbc35 | - | default Anchor event hash |
| `UpdateAdminEvent` | `e198ab57f63f42ea` | 0x3802, 0x3852 | - | default Anchor event hash |
| `UpdateCreatorFeeConfigEvent` | `98c67c7c6af67fbf` | 0x3a0c, 0x3a58 | - | default Anchor event hash |
| `UpdateFeeConfigEvent` | `5a1741233ef4bcd0` | 0x11242 | - | default Anchor event hash |
| `WithdrawEvent` | `1609851aa02c47c0` | 0x15035 | - | default Anchor event hash |

### Accounts (7)

| account | disc | owner | lddw | rodata |
|---|---|---|---|---|
| `BondingCurve` | `17b7f83760d8ac60` | P | 0x1ae0e | - |
| `FeeConfig` | `8f3492bbdb7b4c9b` | F | 0x1b3bd | - |
| `GlobalConfig` | `95089ccaa0fcb0d9` | S | 0x5d76, 0xbcf9 | 0x11c62e |
| `GlobalVolumeAccumulator` | `ca2af62b8ebe1eff` | S | 0x5d85, 0x1a8a1 | 0x11c616 |
| `Pool` | `f19a6d0411b16dbc` | S | 0x5d7b, 0xc9ce | 0x11c60e |
| `SharingConfig` | `d84a0900388c5d4b` | F | 0x1b4ad | - |
| `UserVolumeAccumulator` | `56ff700e66359afa` | S | 0x5d80, 0x9a90 | 0x11c5fe |

## pump_fees

### Instructions (31)

| instruction | disc | lddw | handler pc | handler byte |
|---|---|---|---:|---:|
| `initialize_fee_config` | `3ea214857941911b` | 0x12420 | 0x12d72 | 0x96b90 |
| `initialize_fee_program_global` | `23d78254e9387ca7` | 0x12424 | 0x12e01 | 0x97008 |
| `set_social_claim_authority` | `9336b89a88edb999` | 0x1242a | 0x12eca | 0x97650 |
| `set_disable_flags` | `c2d9702372de33be` | 0x1242e | 0x12f8a | 0x97c50 |
| `set_claim_rate_limit` | `b9d39faed4315804` | 0x12432 | 0x13034 | 0x981a0 |
| `set_authority` | `85fa25156ea31a79` | 0x12436 | 0x130de | 0x986f0 |
| `update_fee_config` | `68b867f258976b14` | 0x1243a | 0x1319e | 0x98cf0 |
| `upsert_fee_tiers` | `e317960c4d565e04` | 0x1243e | 0x13267 | 0x99338 |
| `update_stable_fee_config` | `6ba964b3869b92dd` | 0x12442 | 0x13329 | 0x99948 |
| `upsert_stable_fee_tiers` | `b5a0a2fc4a4ce0dd` | 0x12446 | 0x133e0 | 0x99f00 |
| `extend_fee_config` | `44b3f45aad3811d9` | 0x1244a | 0x134a2 | 0x9a510 |
| `set_exotic_flat_fees` | `1eea958afce62749` | 0x1244e | 0x13541 | 0x9aa08 |
| `update_admin` | `a1b028d53cb8b3e4` | 0x12452 | 0x135f3 | 0x9af98 |
| `get_fees` | `e7257e55cf5b3f34` | 0x12456 | 0x136a0 | 0x9b500 |
| `get_fees_with_quote_mint` | `9aed8a5ca202a2bb` | 0x1245a | 0x13763 | 0x9bb18 |
| `create_fee_sharing_config` | `c34e564c6f34fbd5` | 0x1245e | 0x13810 | 0x9c080 |
| `revoke_fee_sharing_authority` | `12e99e27b9cf3a68` | 0x12462 | 0x138ba | 0x9c5d0 |
| `transfer_fee_sharing_authority` | `ca0a4bc8a422d260` | 0x12466 | 0x138c7 | 0x9c638 |
| `update_fee_shares` | `bd0d8863bba4ed23` | 0x1246a | 0x138d4 | 0x9c6a0 |
| `update_fee_shares_v2` | `6ffb31064e4e6a12` | 0x1246e | 0x1395a | 0x9cad0 |
| `admin_cto_sharing_config` | `3c64909c408ab625` | 0x12472 | 0x139e4 | 0x9cf20 |
| `create_social_fee_pda` | `90e03bd34ef8cadc` | 0x12476 | 0x13a95 | 0x9d4a8 |
| `claim_social_fee_pda` | `e115fb85a11ec7e2` | 0x1247a | 0x13b5d | 0x9dae8 |
| `claim_social_fee_pda_v2` | `114df0863abc3595` | 0x1247e | 0x13c64 | 0x9e320 |
| `initialize_buyback` | `fa81eca0e3246786` | 0x12482 | 0x13d6a | 0x9eb50 |
| `sweep_buyback` | `8a21cc26cfa19fe2` | 0x12486 | 0x13e01 | 0x9f008 |
| `update_buyback_authority` | `426271ca7925db6b` | 0x1248a | 0x13ea6 | 0x9f530 |
| `update_buyback_claim_rate_limit` | `ba5f87beffc789aa` | 0x1248e | 0x13f80 | 0x9fc00 |
| `create_donation_fee_pda` | `f48b10580eff7a1a` | 0x12492 | 0x14044 | 0xa0220 |
| `crank_donation_fee_pda` | `dc0abda7a9111945` | 0x12496 | 0x140b8 | 0xa05c0 |
| `withdraw` | `b712469c946da122` | 0x1249a | 0x14121 | 0xa0908 |

### Events (22)

| event | disc | lddw | rodata | note |
|---|---|---|---|---|
| `CreateFeeSharingConfigEvent` | `8569aac8b874fb58` | 0xe434 | - | default Anchor event hash |
| `DonationFeePdaCranked` | `1ed06b5db100df4e` | 0x4c89, 0x4d03 | - | default Anchor event hash |
| `DonationFeePdaCreated` | `5e1489ef234de1eb` | 0x534a, 0x53c3 | - | default Anchor event hash |
| `ExtendFeeConfigEvent` | `e2cbe023990a5833` | 0x904f | - | default Anchor event hash |
| `InitializeFeeConfigEvent` | `598af4e60a38e27e` | 0x28b5, 0x2906 | - | default Anchor event hash |
| `InitializeFeeProgramGlobalEvent` | `28e99c4e5f0008c7` | 0x2a23, 0x2a78 | - | default Anchor event hash |
| `ResetFeeSharingConfigEvent` | `cbcc97e27837d6f3` | 0xbd4f | - | default Anchor event hash |
| `SetAuthorityEvent` | `12af8442d0c957f2` | 0x330b, 0x335d | - | default Anchor event hash |
| `SetClaimRateLimitEvent` | `0d8f8febb5133328` | 0x3723, 0x3766 | - | default Anchor event hash |
| `SetDisableFlagsEvent` | `0508b3413137917e` | 0x35e4, 0x3627 | - | default Anchor event hash |
| `SetExoticFlatFeesEvent` | `c38a6c0f084d4409` | 0x2c0d, 0x2c68 | - | default Anchor event hash |
| `SetSocialClaimAuthorityEvent` | `3c767f84ef34fe0e` | 0x3458, 0x34a2 | - | default Anchor event hash |
| `SocialFeePdaClaimed` | `3212c141edd2eaec` | 0xc665 | - | default Anchor event hash |
| `SocialFeePdaCreated` | `b7b7da93187c89a9` | 0xec43 | - | default Anchor event hash |
| `SweepBuybackEvent` | `2b382ad69939a689` | 0xba0d | - | default Anchor event hash |
| `UpdateAdminEvent` | `e198ab57f63f42ea` | 0x2e3e, 0x2e8f | - | default Anchor event hash |
| `UpdateFeeConfigEvent` | `5a1741233ef4bcd0` | 0xa508 | - | default Anchor event hash |
| `UpdateFeeSharesEvent` | `15bac4b85be4e1cb` | 0xf4b1 | - | default Anchor event hash |
| `UpdateStableFeeConfigEvent` | `5e052bed6793e8f5` | 0xa579 | - | default Anchor event hash |
| `UpsertFeeTiersEvent` | `ab59a9bb7aba21cc` | 0xa81b | - | default Anchor event hash |
| `UpsertStableFeeTiersEvent` | `e8eded34629249f3` | 0xa898 | - | default Anchor event hash |
| `WithdrawEvent` | `1609851aa02c47c0` | 0x7c8c, 0x7cde | - | default Anchor event hash |

### Accounts (9)

| account | disc | owner | lddw | rodata |
|---|---|---|---|---|
| `BondingCurve` | `17b7f83760d8ac60` | P | 0x10661 | 0xc3def |
| `BuybackVault` | `99a64790b3bd89fb` | S | 0x1028f | 0xc3daf |
| `DonationFeePda` | `f6c56009c11e5d73` | S | 0x10436 | 0xc3d6f |
| `FeeConfig` | `8f3492bbdb7b4c9b` | S | 0x11eb, 0x2590 | 0xc3db7 |
| `FeeProgramGlobal` | `a2a5f5311d2537f2` | S | 0x1056f | 0xc3d97 |
| `Global` | `a7e8e8b1c86c727f` | P | 0x10771 | - |
| `Pool` | `f19a6d0411b16dbc` | A | 0x118fb | 0xc3dc7 |
| `SharingConfig` | `d84a0900388c5d4b` | S | 0xd84d | 0xc3ddf |
| `SocialFeePda` | `8b6035112aa9ce96` | S | 0x10369 | 0xc3de7 |

## mayhem

### Instructions (25)

| instruction | disc | lddw | handler pc | handler byte |
|---|---|---|---:|---:|
| `buy_pump_swap` | `de939d076c089151` | 0xfb70 | 0x1041f | 0x820f8 |
| `sell_pump_swap` | `10c691f0ee6589cb` | 0xfb66 | 0x103b7 | 0x81db8 |
| `buy_v2` | `b817ee6167c5d33d` | 0xfb8a, 0x10998 | 0x1034f | 0x81a78 |
| `sell_v2` | `5df6823ce7e940b2` | 0xfb80, 0x10c78 | 0x102e7 | 0x81738 |
| `buy` | `66063d1201daebea` | 0xdd17, 0xeb56 | 0x1027f | 0x813f8 |
| `sell` | `33e685a4017f83ad` | 0xdf50, 0xedff | 0x10217 | 0x810b8 |
| `burn_tokens` | `4c0f33fee5d77942` | 0xfb90 | 0xffe1 | 0x7ff08 |
| `sweep_fees` | `afe1624776422294` | 0xfb4c | 0xfc96 | 0x7e4b0 |
| `sweep_fees_admin` | `4c93c5e16f9c75e7` | 0xfb97 | 0xfcd3 | 0x7e698 |
| `withdraw_quote_admin` | `cc712a30723af859` | 0xfb73 | 0xfde2 | 0x7ef10 |
| `withdraw_admin` | `1e1b87bc899eda6b` | 0xfb3c | 0xfd90 | 0x7ec80 |
| `extend_account` | `ea66c2cb96483ee5` | 0xfb27 | 0x1001c | 0x800e0 |
| `initialize_fee_recipient` | `da578ec8cec516c8` | 0xfb83 | 0xfc41 | 0x7e208 |
| `initialize_global_params` | `0d127fea3b28ccda` | 0xfb69 | 0xfbfc | 0x7dfe0 |
| `update_global_params` | `9224de6c59e2f97e` | 0xfba4 | 0x1004b | 0x80258 |
| `update_admin` | `a1b028d53cb8b3e4` | 0xfb24 | 0xfe93 | 0x7f498 |
| `update_trader` | `c9cf63406556af60` | 0xfb76 | 0xfe35 | 0x7f1a8 |
| `update_max_sol_per_sweep` | `22ada705c885e192` | 0xfb49 | 0xfd10 | 0x7e880 |
| `update_max_stable_per_sweep` | `804b4c8b7dc46f67` | 0xfb39 | 0xfd50 | 0x7ea80 |
| `reset_sol_deployed` | `b0ad9da2f0bcc439` | 0xfb5c | 0xff2d | 0x7f968 |
| `reset_stable_deployed` | `bf2530b70f5489cb` | 0xfb63 | 0xff59 | 0x7fac8 |
| `reset_state` | `9176742a28db948b` | 0xfb46 | 0xfef1 | 0x7f788 |
| `stop_trading` | `7fb06a3bf27a726f` | 0xfba1 | 0xffb3 | 0x7fd98 |
| `resume_trading` | `922ed456459f1e41` | 0xfb8d | 0xff85 | 0x7fc28 |
| `initialize_mayhem_state` | `9dbd5e485545cc2d` | 0xfb59 | 0x101de | 0x80ef0 |

### Events (5)

| event | disc | lddw | rodata | note |
|---|---|---|---|---|
| `BurnEvent` | `21592f75527ceefa` | 0x1c73, 0x1ceb | - | default Anchor event hash |
| `SellEvent` | `31487b2d6e40b085` | 0xb6f7 | - | override; historical name not recovered |
| `GlobalParamsUpdateEvent` | `63a75c9898e32629` | 0x1a02, 0x1a5f | - | override; historical name not recovered |
| `ExtendAccountEvent` | `6161d7905d92167c` | 0x793f | - | default Anchor event hash |
| `SweepEvent` | `da8286fd656d9598` | 0x247d, 0x24cc | - | override; historical name not recovered |

### Accounts (4)

| account | disc | owner | lddw | rodata |
|---|---|---|---|---|
| `GlobalParams` | `79c1f857c3384c0b` | M | 0x1dfa, 0xcee9 | 0xaca70 |
| `MayhemState` | `b1fdbf7dcb16866b` | M | 0x1dfd, 0xd129 | 0xacaa8 |
| `FeeRecipient` | `94fad18ab9eac3e3` | M | 0x1df7, 0x79b9 | 0xaca78 |
| `BondingCurve` | `17b7f83760d8ac60` | P | 0x16c, 0xdbdf | 0xacab8 |

## Corrections / notes

- **pump is 54 deployed instructions, not 53.** `handlers.json` has the 53-name IDL set;
  the deployed program also dispatches `add_quote_control_mint` (`020e3d8aaa8e0e5f` at
  `lddw 0x237cf`, handler ~`0x265d5`). The 56-name upstream IDL additionally lists
  `collect_creator_fee_v2` and `update_buyback_config`, which are **not** deployed in this
  capture (no discriminator hit). These are pump-side names; the AMM has its own
  `update_buyback_config` (`fbe0ab92a01a71e9`) and is unaffected.
- **Pump `BondingCurve` is `17b7f83760d8ac60` everywhere** (pump `0x1b64ef`/`0x77b2`, amm
  `lddw 0x1ae0e`, fees `lddw 0x10661`, mayhem `0xacab8`/`lddw 0x16c`). The reconstructed
  custom `23b7f83760d8ac60` is **not** in any deployed ELF; do not use it.
- All deployed account discriminators checked here are the standard Anchor
  `sha256("account:"+name)[:8]` (the `Pool`/`GlobalConfig`/`FeeConfig`/`SharingConfig`
  constants are their hashes, not arbitrary overrides). The only historical-name gap is
  the Mayhem `SellEvent` / `GlobalParamsUpdateEvent` / `SweepEvent` overrides.
- Instruction/event names are name-only; a program may share a disc with another program
  (e.g. `update_fee_config` `68b867f258976b14` in both AMM and fees; `claim_cashback`
  `253a237ebe35e4c5` in pump and AMM; `buy`/`sell`). The dispatcher + program id resolve
  them.
- `admin_cto` is mapped at its deployed disc `7d7ed6864de5bc59`; the reconstruction's guard
  set differs (see `pump_specs.md` / `spec/08`).
