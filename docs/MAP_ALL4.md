# Full 4-program structural map (deployed binaries)

Built with `tools/sbftool.py` + `tools/deep_map_all4.py` from
`pumpfun-source/evidence/original/*/deployed.so`.
Decoder stated 0-diff vs llvm-objdump in upstream docs.
Scope: RE / behavioral structure only — no vuln claims, no exploit PoC.

| Program | .text insns | functions | instructions mapped |
|---|---:|---:|---|
| pump | 215,873 | 1169 | 53/53 |
| pump_amm (PumpSwap) | 139,524 | 831 | 38/38 (IDL stale at 31; collaborator-found+verified) |
| pump_fees | 96,083 | 637 | 31/31 |
| mayhem | 83,947 | 502 | 25/25 (jeq+jne dispatch, collaborator-verified) |

.text sizes (bytes): pump 1,792,208 · pump_amm 1,162,040 · pump_fees 799,648 · mayhem 706,744.

Note: the `deep_map_all4.py` dispatcher pass below recovered 30 pump_amm handlers (all agree with the upstream 38/38 map in `maps/amm_handlers_full.json`); the 8 additional upstream-verified PumpSwap instructions are not re-listed here.

## SHA-256 of deployed.so

- `pump`: `7a19affaa2c6187e04a5fe0ea298cee81fa5eb8c24cfcc30d85f615e89f7b02d`
- `pump_amm`: `6a7ad34596d83b4c435b32f458a56e718e9f82eb4ad38e4316616d15d24d8ff7`
- `pump_fees`: `4f2955d0f6b40cc9ff7daa18ccad7d19119ba1249759f4e7e3bb691beee6b35e`
- `mayhem`: `a87fa9f866272514e6acb852b668c4a08aeb173d56c883039991d114d1199bdb`

## Handler tables

### pump (53/53)

| instruction | disc | cmp | stub | handler (pc) | handler (bytes) |
|---|---|---|---|---|---|
| `add_quote_mint` | `6f79153828185ed1` | jeq | `0x23873` | `0x24774` | `0x123ba0` |
| `admin_cto` | `7d7ed6864de5bc59` | jeq | `0x239fb` | `0x25b40` | `0x12da00` |
| `admin_set_idl_authority` | `08d960e79068c005` | jeq | `0x23a6b` | `0x260a3` | `0x130518` |
| `admin_update_token_incentives` | `d10b7357d5177ccc` | jeq | `0x23a09` | `0x25c54` | `0x12e2a0` |
| `buy` | `66063d1201daebea` | jeq | `0x23961` | `0x2549c` | `0x12a4e0` |
| `buy_exact_quote_in_v2` | `c2ab1c46684d5b2f` | jeq | `0x238f1` | `0x24f6b` | `0x127b58` |
| `buy_exact_quote_in_v3` | `e1f7501ed5b38488` | jeq | `0x2391b` | `0x25185` | `0x128c28` |
| `buy_exact_sol_in` | `38fc74089edfcd5f` | jeq | `0x2396f` | `0x25579` | `0x12abc8` |
| `buy_v2` | `b817ee6167c5d33d` | jeq | `0x238e3` | `0x24ea2` | `0x127510` |
| `buy_v3` | `07051dc4f5176550` | jeq | `0x2390d` | `0x250d9` | `0x1286c8` |
| `claim_cashback` | `253a237ebe35e4c5` | jeq | `0x23a25` | `0x25d99` | `0x12ecc8` |
| `claim_cashback_v2` | `7af3cc415e741d37` | jeq | `0x23a33` | `0x25e2a` | `0x12f150` |
| `claim_token_incentives` | `1004471ccc01281b` | jeq | `0x23a17` | `0x25d0e` | `0x12e870` |
| `close_user_volume_accumulator` | `f945a4da9667548a` | jeq | `0x23a4f` | `0x25f6d` | `0x12fb68` |
| `collect_creator_fee` | `1416567bc61cdb84` | jeq | `0x239b5` | `0x2586e` | `0x12c370` |
| `create` | `181ec828051c0777` | jeq | `0x238c7` | `0x24c1b` | `0x1260d8` |
| `create_v2` | `d6904cec5f8b31b4` | jeq | `0x238d5` | `0x24d15` | `0x1268a8` |
| `distribute_creator_fees` | `a572670079cef751` | jeq | `0x23a95` | `0x26225` | `0x131128` |
| `distribute_creator_fees_v2` | `ffcb134ff444089f` | jeq | `0x23aa3` | `0x262dd` | `0x1316e8` |
| `distribute_fee_to_holders` | `623691610246ad2b` | jeq | `0x239d1` | `0x258fa` | `0x12c7d0` |
| `extend_account` | `ea66c2cb96483ee5` | jeq | `0x239a7` | `0x257cf` | `0x12be78` |
| `get_minimum_distributable_fee` | `75e17fca865f4423` | jeq | `0x23a87` | `0x261a8` | `0x130d40` |
| `init_user_volume_accumulator` | `5e06ca73ff60e8b7` | jeq | `0x23a41` | `0x25ebc` | `0x12f5e0` |
| `initialize` | `afaf6d1f0d989bed` | jeq | `0x23803` | `0x2421b` | `0x1210d8` |
| `initialize_quote_control` | `ef49f5add1b15442` | jeq | `0x23abf` | `0x264a2` | `0x132510` |
| `migrate` | `9beae792ec9ea21e` | jeq | `0x2398b` | `0x256fb` | `0x12b7d8` |
| `migrate_bonding_curve_creator` | `577c34bf3426d6e8` | jeq | `0x23a79` | `0x26118` | `0x1308c0` |
| `migrate_v2` | `bbcb121fceedfe29` | jeq | `0x23999` | `0x25749` | `0x12ba48` |
| `multi_hop_curve_swap` | `e19a7516d756f667` | jeq | `0x23937` | `0x252b8` | `0x1295c0` |
| `remove_quote_control_mint` | `df07fd1a51a5daa6` | jeq | `0x23ae9` | `0x26667` | `0x133338` |
| `remove_quote_mint` | `b141df2658d19e9b` | jeq | `0x23881` | `0x24826` | `0x124130` |
| `sell` | `33e685a4017f83ad` | jeq | `0x2397d` | `0x25656` | `0x12b2b0` |
| `sell_v2` | `5df6823ce7e940b2` | jeq | `0x238ff` | `0x25034` | `0x1281a0` |
| `sell_v3` | `1c92de7726c469d5` | jeq | `0x23929` | `0x25231` | `0x129188` |
| `set_creator` | `fe94ff70cf8eaaa5` | jeq | `0x239ed` | `0x25a82` | `0x12d410` |
| `set_max_curve_depth` | `209a98db8e6cdaa5` | jeq | `0x23849` | `0x24566` | `0x122b30` |
| `set_mayhem_virtual_params` | `3da9bcbf99952a61` | jeq | `0x238ab` | `0x24ab5` | `0x1255a8` |
| `set_metaplex_creator` | `8a60aed93055c5f6` | jeq | `0x239df` | `0x259f2` | `0x12cf90` |
| `set_params` | `1beab2349302bb8d` | jeq | `0x2389d` | `0x2494e` | `0x124a70` |
| `set_quote_control_admin` | `3e4fa1d3a5aad6d2` | jeq | `0x23acd` | `0x264e3` | `0x132718` |
| `set_quote_control_mint_reserves` | `74dc6b53bf2c2049` | jeq | `0x23b05` | `0x267e9` | `0x133f48` |
| `set_quote_control_reserves_admin` | `a1c3dea5e165c03e` | jeq | `0x23af7` | `0x26728` | `0x133940` |
| `set_reserved_fee_recipients` | `6faca2e87259d58e` | jeq | `0x238b9` | `0x24b5d` | `0x125ae8` |
| `set_virtual_quote_reserves` | `6587bf6809581460` | jeq | `0x2388f` | `0x248d8` | `0x1246c0` |
| `sweep_creator_fee` | `20f6bf3408c949ba` | jeq | `0x23953` | `0x25409` | `0x12a048` |
| `sweep_protocol_fee` | `0830be07b644b7e5` | jeq | `0x23945` | `0x25376` | `0x129bb0` |
| `sync_user_volume_accumulator` | `561fc057a3574fee` | jeq | `0x23a5d` | `0x25ff1` | `0x12ff88` |
| `toggle_cashback_enabled` | `7367e0ffbd5956c3` | jeq | `0x2382d` | `0x243d8` | `0x121ec0` |
| `toggle_create_v2` | `1cffe6f0ac6bcbab` | jeq | `0x2381f` | `0x2430e` | `0x121870` |
| `toggle_mayhem_mode` | `01096fd0641fffa3` | jeq | `0x23857` | `0x245dc` | `0x122ee0` |
| `update_creator_fee_config` | `3dafa0f9424288af` | jeq | `0x23865` | `0x246a6` | `0x123530` |
| `update_global_authority` | `e3b54ac4d01561d5` | jeq | `0x23811` | `0x24261` | `0x121308` |
| `update_holder_reward_config` | `e1fc4204c723ec10` | jeq | `0x2383b` | `0x244a2` | `0x122510` |

Transfer-fee helper (cited): `0x12a1c`

Baked `programs/...rs` paths (33):
- `programs/pump/src/admin_set_idl_authority.rs`
- `programs/pump/src/buy.rs`
- `programs/pump/src/buy_v2.rs`
- `programs/pump/src/create_v2.rs`
- `programs/pump/src/creator/admin_cto.rs`
- `programs/pump/src/creator/collect_creator_fee.rs`
- `programs/pump/src/creator/distribute_creator_fee_v2.rs`
- `programs/pump/src/creator/distribute_creator_fees.rs`
- `programs/pump/src/creator/distribute_fee_to_holders.rs`
- `programs/pump/src/creator/migrate_bonding_curve_creator.rs`
- `programs/pump/src/creator/set_creator.rs`
- `programs/pump/src/creator/set_metaplex_creator.rs`
- `programs/pump/src/extend_account.rs`
- `programs/pump/src/fee_recipient.rs`
- `programs/pump/src/lib.rs`
- `programs/pump/src/migrate.rs`
- `programs/pump/src/migrate_v2.rs`
- `programs/pump/src/multi_hop_curve_swap.rs`
- `programs/pump/src/pump_quote.rs`
- `programs/pump/src/quote_control/initialize_quote_control.rs`
- `programs/pump/src/quote_control/state.rs`
- `programs/pump/src/quote_control/update_quote_control_mints.rs`
- `programs/pump/src/sell.rs`
- `programs/pump/src/sell_v2.rs`
- `programs/pump/src/set_reserved_fee_recipients.rs`
- `programs/pump/src/sweep_fees.rs`
- `programs/pump/src/token_incentives/claim_token_incentives.rs`
- `programs/pump/src/token_incentives/init_user_volume_accumulator.rs`
- `programs/pump/src/token_incentives/volume_accumulator.rs`
- `programs/pump/src/trade_v3.rs`
- `programs/pump/src/util/constant_product.rs`
- `programs/pump/src/util/fee.rs`
- `programs/pump/src/util/transfer_fee.rs`

### pump_amm (30/31)

Unmapped: `admin_set_coin_creator`

| instruction | disc | cmp | stub | handler (pc) | handler (bytes) |
|---|---|---|---|---|---|
| `admin_update_token_incentives` | `d10b7357d5177ccc` | jeq | `0x1b90b` | `0x1cb9d` | `0xe5ce8` |
| `boost_buy_and_burn` | `694406af000723a2` | jeq | `0x1b8d3` | `0x1c8e7` | `0xe4738` |
| `buy` | `66063d1201daebea` | jeq | `0x1b951` | `0x1cec9` | `0xe7648` |
| `buy_exact_quote_in` | `c62e1552b4d9e870` | jeq | `0x1b95f` | `0x1cfb1` | `0xe7d88` |
| `claim_cashback` | `253a237ebe35e4c5` | jeq | `0x1ba5b` | `0x1da42` | `0xed210` |
| `claim_token_incentives` | `1004471ccc01281b` | jeq | `0x1b919` | `0x1cc57` | `0xe62b8` |
| `close_user_volume_accumulator` | `f945a4da9667548a` | jeq | `0x1b935` | `0x1cd93` | `0xe6c98` |
| `collect_coin_creator_fee` | `a039592ab58b2b42` | jeq | `0x1b9dd` | `0x1d51d` | `0xea8e8` |
| `create_config` | `c9cff3724b6f2fbd` | jeq | `0x1b863` | `0x1c17f` | `0xe0bf8` |
| `create_pool` | `e992d18ecf6840bc` | jeq | `0x1b8a9` | `0x1c634` | `0xe31a0` |
| `deposit` | `f223c68952e1f2b6` | jeq | `0x1b8ef` | `0x1ca4f` | `0xe5278` |
| `disable` | `b9adbb5ad80feee9` | jeq | `0x1b871` | `0x1c2a1` | `0xe1508` |
| `extend_account` | `ea66c2cb96483ee5` | jeq | `0x1b9cf` | `0x1d47e` | `0xea3f0` |
| `init_boost` | `8ce9215e845ac28f` | jeq | `0x1b8b7` | `0x1c7b3` | `0xe3d98` |
| `init_user_volume_accumulator` | `5e06ca73ff60e8b7` | jeq | `0x1b927` | `0x1cce2` | `0xe6710` |
| `migrate_pool_coin_creator` | `d0089f044aaf103a` | jeq | `0x1ba3f` | `0x1d8e7` | `0xec738` |
| `sell` | `33e685a4017f83ad` | jeq | `0x1b96d` | `0x1d099` | `0xe84c8` |
| `set_boost_authority` | `e3954c2a8227eacd` | jeq | `0x1b8c5` | `0x1c839` | `0xe41c8` |
| `set_coin_creator` | `d295802dbc3a4eaf` | jeq | `0x1b9eb` | `0x1d56e` | `0xeab70` |
| `set_reserved_fee_recipients` | `6faca2e87259d58e` | jeq | `0x1b8e1` | `0x1c98d` | `0xe4c68` |
| `sync_user_volume_accumulator` | `561fc057a3574fee` | jeq | `0x1b943` | `0x1ce17` | `0xe70b8` |
| `toggle_boost` | `75a1a04adf897663` | jeq | `0x1ba15` | `0x1d7cc` | `0xebe60` |
| `toggle_cashback_enabled` | `7367e0ffbd5956c3` | jeq | `0x1ba4d` | `0x1d977` | `0xecbb8` |
| `toggle_mayhem_mode` | `01096fd0641fffa3` | jeq | `0x1ba07` | `0x1d701` | `0xeb808` |
| `transfer_creator_fees_to_pump` | `8b348655e4e56cf1` | jeq | `0x1ba23` | `0x1d846` | `0xec230` |
| `transfer_creator_fees_to_pump_v2` | `01214eb921432c5c` | jeq | `0x1ba31` | `0x1d898` | `0xec4c0` |
| `update_admin` | `a1b028d53cb8b3e4` | jeq | `0x1b87f` | `0x1c398` | `0xe1cc0` |
| `update_buyback_config` | `fbe0ab92a01a71e9` | jeq | `0x1ba69` | `0x1dacc` | `0xed660` |
| `update_fee_config` | `68b867f258976b14` | jeq | `0x1b88d` | `0x1c446` | `0xe2230` |
| `withdraw` | `b712469c946da122` | jeq | `0x1b8fd` | `0x1caf6` | `0xe57b0` |

### pump_fees (31/31)

| instruction | disc | cmp | stub | handler (pc) | handler (bytes) |
|---|---|---|---|---|---|
| `admin_cto_sharing_config` | `3c64909c408ab625` | jeq | `0x125d0` | `0x139e4` | `0x9cf20` |
| `claim_social_fee_pda` | `e115fb85a11ec7e2` | jeq | `0x125ec` | `0x13b5d` | `0x9dae8` |
| `claim_social_fee_pda_v2` | `114df0863abc3595` | jeq | `0x125fa` | `0x13c64` | `0x9e320` |
| `crank_donation_fee_pda` | `dc0abda7a9111945` | jeq | `0x1264e` | `0x140b8` | `0xa05c0` |
| `create_donation_fee_pda` | `f48b10580eff7a1a` | jeq | `0x12640` | `0x14044` | `0xa0220` |
| `create_fee_sharing_config` | `c34e564c6f34fbd5` | jeq | `0x12594` | `0x13810` | `0x9c080` |
| `create_social_fee_pda` | `90e03bd34ef8cadc` | jeq | `0x125de` | `0x13a95` | `0x9d4a8` |
| `extend_fee_config` | `44b3f45aad3811d9` | jeq | `0x1254e` | `0x134a2` | `0x9a510` |
| `get_fees` | `e7257e55cf5b3f34` | jeq | `0x12578` | `0x136a0` | `0x9b500` |
| `get_fees_with_quote_mint` | `9aed8a5ca202a2bb` | jeq | `0x12586` | `0x13763` | `0x9bb18` |
| `initialize_buyback` | `fa81eca0e3246786` | jeq | `0x12608` | `0x13d6a` | `0x9eb50` |
| `initialize_fee_config` | `3ea214857941911b` | jeq | `0x124c2` | `0x12d72` | `0x96b90` |
| `initialize_fee_program_global` | `23d78254e9387ca7` | jeq | `0x124d0` | `0x12e01` | `0x97008` |
| `revoke_fee_sharing_authority` | `12e99e27b9cf3a68` | jeq | `0x125a2` | `0x138ba` | `0x9c5d0` |
| `set_authority` | `85fa25156ea31a79` | jeq | `0x12508` | `0x130de` | `0x986f0` |
| `set_claim_rate_limit` | `b9d39faed4315804` | jeq | `0x124fa` | `0x13034` | `0x981a0` |
| `set_disable_flags` | `c2d9702372de33be` | jeq | `0x124ec` | `0x12f8a` | `0x97c50` |
| `set_exotic_flat_fees` | `1eea958afce62749` | jeq | `0x1255c` | `0x13541` | `0x9aa08` |
| `set_social_claim_authority` | `9336b89a88edb999` | jeq | `0x124de` | `0x12eca` | `0x97650` |
| `sweep_buyback` | `8a21cc26cfa19fe2` | jeq | `0x12616` | `0x13e01` | `0x9f008` |
| `transfer_fee_sharing_authority` | `ca0a4bc8a422d260` | jeq | `0x125ab` | `0x138c7` | `0x9c638` |
| `update_admin` | `a1b028d53cb8b3e4` | jeq | `0x1256a` | `0x135f3` | `0x9af98` |
| `update_buyback_authority` | `426271ca7925db6b` | jeq | `0x12624` | `0x13ea6` | `0x9f530` |
| `update_buyback_claim_rate_limit` | `ba5f87beffc789aa` | jeq | `0x12632` | `0x13f80` | `0x9fc00` |
| `update_fee_config` | `68b867f258976b14` | jeq | `0x12516` | `0x1319e` | `0x98cf0` |
| `update_fee_shares` | `bd0d8863bba4ed23` | jeq | `0x125b4` | `0x138d4` | `0x9c6a0` |
| `update_fee_shares_v2` | `6ffb31064e4e6a12` | jeq | `0x125c2` | `0x1395a` | `0x9cad0` |
| `update_stable_fee_config` | `6ba964b3869b92dd` | jeq | `0x12532` | `0x13329` | `0x99948` |
| `upsert_fee_tiers` | `e317960c4d565e04` | jeq | `0x12524` | `0x13267` | `0x99338` |
| `upsert_stable_fee_tiers` | `b5a0a2fc4a4ce0dd` | jeq | `0x12540` | `0x133e0` | `0x99f00` |
| `withdraw` | `b712469c946da122` | jeq | `0x1265c` | `0x14121` | `0xa0908` |

### mayhem (25/25)

| instruction | disc | cmp | stub | handler (pc) | handler (bytes) |
|---|---|---|---|---|---|
| `burn_tokens` | `4c0f33fee5d77942` | jne | `0xfb93` | `0xffe1` | `0x7ff08` |
| `buy` | `66063d1201daebea` | jne | `0xfb9d` | `0x1027f` | `0x813f8` |
| `buy_pump_swap` | `de939d076c089151` | jeq | `0xfbd0` | `0x1041f` | `0x820f8` |
| `buy_v2` | `b817ee6167c5d33d` | jeq | `0xfbe0` | `0x1034f` | `0x81a78` |
| `extend_account` | `ea66c2cb96483ee5` | jne | `0xfb2a` | `0x1001c` | `0x800e0` |
| `initialize_fee_recipient` | `da578ec8cec516c8` | jne | `0xfb86` | `0xfc41` | `0x7e208` |
| `initialize_global_params` | `0d127fea3b28ccda` | jne | `0xfb6c` | `0xfbfc` | `0x7dfe0` |
| `initialize_mayhem_state` | `9dbd5e485545cc2d` | jeq | `0xfbf0` | `0x101de` | `0x80ef0` |
| `reset_sol_deployed` | `b0ad9da2f0bcc439` | jne | `0xfb5f` | `0xff2d` | `0x7f968` |
| `reset_stable_deployed` | `bf2530b70f5489cb` | jeq | `0xfbcc` | `0xff59` | `0x7fac8` |
| `reset_state` | `9176742a28db948b` | jeq | `0xfbd4` | `0xfef1` | `0x7f788` |
| `resume_trading` | `922ed456459f1e41` | jeq | `0xfbf8` | `0xff85` | `0x7fc28` |
| `sell` | `33e685a4017f83ad` | jeq | `0xfbdc` | `0x10217` | `0x810b8` |
| `sell_pump_swap` | `10c691f0ee6589cb` | jeq | `0xfbe4` | `0x103b7` | `0x81db8` |
| `sell_v2` | `5df6823ce7e940b2` | jeq | `0xfbf4` | `0x102e7` | `0x81738` |
| `stop_trading` | `7fb06a3bf27a726f` | jeq | `0xfbc8` | `0xffb3` | `0x7fd98` |
| `sweep_fees` | `afe1624776422294` | jne | `0xfb4f` | `0xfc96` | `0x7e4b0` |
| `sweep_fees_admin` | `4c93c5e16f9c75e7` | jeq | `0xfbc4` | `0xfcd3` | `0x7e698` |
| `update_admin` | `a1b028d53cb8b3e4` | jeq | `0xfbbc` | `0xfe93` | `0x7f498` |
| `update_global_params` | `9224de6c59e2f97e` | jne | `0xfba7` | `0x1004b` | `0x80258` |
| `update_max_sol_per_sweep` | `22ada705c885e192` | jeq | `0xfbec` | `0xfd10` | `0x7e880` |
| `update_max_stable_per_sweep` | `804b4c8b7dc46f67` | jeq | `0xfbc0` | `0xfd50` | `0x7ea80` |
| `update_trader` | `c9cf63406556af60` | jne | `0xfb79` | `0xfe35` | `0x7f1a8` |
| `withdraw_admin` | `1e1b87bc899eda6b` | jne | `0xfb3f` | `0xfd90` | `0x7ec80` |
| `withdraw_quote_admin` | `cc712a30723af859` | jeq | `0xfbe8` | `0xfde2` | `0x7ef10` |

## Key cross-program CPI targets (from prior + this map)

- PumpSwap `create_pool` → migrate graduation CPI target
- Fees `get_fees` / `get_fees_with_quote_mint` → pump buy/sell fee CPI
- Mayhem `initialize_mayhem_state` → pump `create_v2` mayhem branch CPI target

## Artifacts

- `maps/*_handlers.json` — compact name→handler_pc
- `maps/*_handlers_full.json` — disc/cmp/stub/handler
- `maps/dispositions.json` — per-handler size/syscalls/errors/xfer-fee
- `maps/program_summaries.json` — program-level stats
- `docs/HANDLER_DISPOSITIONS.md` — narrative
- `docs/analysis/B*_notes.md` — B-unit address notes

