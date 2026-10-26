# Deployed Pump.fun Programs - Structural Reverse-Engineering Map

Built with `sbftool.py` directly from the on-chain binaries in
`evidence/original/*/deployed.so`. Decoder verified 0-diff vs llvm-objdump
across every instruction. This maps structure (instructions, handlers,
syscalls, functions); it is not a byte-identity claim.

## pump
- size: 1,792,208 bytes .text, 215,873 instructions
- functions recovered: 1169  |  call sites: 10,861
- syscalls linked (16, via 144 callx sites): abort, sol_create_program_address, sol_get_clock_sysvar, sol_get_rent_sysvar, sol_get_return_data, sol_invoke_signed_rust, sol_log_, sol_log_data, sol_log_pubkey, sol_memcmp_, sol_memcpy_, sol_memmove_, sol_memset_, sol_set_return_data, sol_sha256, sol_try_find_program_address
- source files baked into binary (33):
    - programs/pump/src/admin_set_idl_authority.rs
    - programs/pump/src/buy.rs
    - programs/pump/src/buy_v2.rs
    - programs/pump/src/create_v2.rs
    - programs/pump/src/creator/admin_cto.rs
    - programs/pump/src/creator/collect_creator_fee.rs
    - programs/pump/src/creator/distribute_creator_fee_v2.rs
    - programs/pump/src/creator/distribute_creator_fees.rs
    - programs/pump/src/creator/distribute_fee_to_holders.rs
    - programs/pump/src/creator/migrate_bonding_curve_creator.rs
    - programs/pump/src/creator/set_creator.rs
    - programs/pump/src/creator/set_metaplex_creator.rs
    - programs/pump/src/extend_account.rs
    - programs/pump/src/fee_recipient.rs
    - programs/pump/src/lib.rs
    - programs/pump/src/migrate.rs
    - programs/pump/src/migrate_v2.rs
    - programs/pump/src/multi_hop_curve_swap.rs
    - programs/pump/src/pump_quote.rs
    - programs/pump/src/quote_control/initialize_quote_control.rs
    - programs/pump/src/quote_control/state.rs
    - programs/pump/src/quote_control/update_quote_control_mints.rs
    - programs/pump/src/sell.rs
    - programs/pump/src/sell_v2.rs
    - programs/pump/src/set_reserved_fee_recipients.rs
    - programs/pump/src/sweep_fees.rs
    - programs/pump/src/token_incentives/claim_token_incentives.rs
    - programs/pump/src/token_incentives/init_user_volume_accumulator.rs
    - programs/pump/src/token_incentives/volume_accumulator.rs
    - programs/pump/src/trade_v3.rs
    - programs/pump/src/util/constant_product.rs
    - programs/pump/src/util/fee.rs
    - programs/pump/src/util/transfer_fee.rs
- instructions mapped to handlers: 53/53

    | instruction | discriminator | handler |
    |---|---|---|
    | add_quote_mint | `6f79153828185ed1` | `0x24774` |
    | admin_cto | `7d7ed6864de5bc59` | `0x25b40` |
    | admin_set_idl_authority | `08d960e79068c005` | `0x260a3` |
    | admin_update_token_incentives | `d10b7357d5177ccc` | `0x25c54` |
    | buy | `66063d1201daebea` | `0x2549c` |
    | buy_exact_quote_in_v2 | `c2ab1c46684d5b2f` | `0x24f6b` |
    | buy_exact_quote_in_v3 | `e1f7501ed5b38488` | `0x25185` |
    | buy_exact_sol_in | `38fc74089edfcd5f` | `0x25579` |
    | buy_v2 | `b817ee6167c5d33d` | `0x24ea2` |
    | buy_v3 | `07051dc4f5176550` | `0x250d9` |
    | claim_cashback | `253a237ebe35e4c5` | `0x25d99` |
    | claim_cashback_v2 | `7af3cc415e741d37` | `0x25e2a` |
    | claim_token_incentives | `1004471ccc01281b` | `0x25d0e` |
    | close_user_volume_accumulator | `f945a4da9667548a` | `0x25f6d` |
    | collect_creator_fee | `1416567bc61cdb84` | `0x2586e` |
    | create | `181ec828051c0777` | `0x24c1b` |
    | create_v2 | `d6904cec5f8b31b4` | `0x24d15` |
    | distribute_creator_fees | `a572670079cef751` | `0x26225` |
    | distribute_creator_fees_v2 | `ffcb134ff444089f` | `0x262dd` |
    | distribute_fee_to_holders | `623691610246ad2b` | `0x258fa` |
    | extend_account | `ea66c2cb96483ee5` | `0x257cf` |
    | get_minimum_distributable_fee | `75e17fca865f4423` | `0x261a8` |
    | init_user_volume_accumulator | `5e06ca73ff60e8b7` | `0x25ebc` |
    | initialize | `afaf6d1f0d989bed` | `0x2421b` |
    | initialize_quote_control | `ef49f5add1b15442` | `0x264a2` |
    | migrate | `9beae792ec9ea21e` | `0x256fb` |
    | migrate_bonding_curve_creator | `577c34bf3426d6e8` | `0x26118` |
    | migrate_v2 | `bbcb121fceedfe29` | `0x25749` |
    | multi_hop_curve_swap | `e19a7516d756f667` | `0x252b8` |
    | remove_quote_control_mint | `df07fd1a51a5daa6` | `0x26667` |
    | remove_quote_mint | `b141df2658d19e9b` | `0x24826` |
    | sell | `33e685a4017f83ad` | `0x25656` |
    | sell_v2 | `5df6823ce7e940b2` | `0x25034` |
    | sell_v3 | `1c92de7726c469d5` | `0x25231` |
    | set_creator | `fe94ff70cf8eaaa5` | `0x25a82` |
    | set_max_curve_depth | `209a98db8e6cdaa5` | `0x24566` |
    | set_mayhem_virtual_params | `3da9bcbf99952a61` | `0x24ab5` |
    | set_metaplex_creator | `8a60aed93055c5f6` | `0x259f2` |
    | set_params | `1beab2349302bb8d` | `0x2494e` |
    | set_quote_control_admin | `3e4fa1d3a5aad6d2` | `0x264e3` |
    | set_quote_control_mint_reserves | `74dc6b53bf2c2049` | `0x267e9` |
    | set_quote_control_reserves_admin | `a1c3dea5e165c03e` | `0x26728` |
    | set_reserved_fee_recipients | `6faca2e87259d58e` | `0x24b5d` |
    | set_virtual_quote_reserves | `6587bf6809581460` | `0x248d8` |
    | sweep_creator_fee | `20f6bf3408c949ba` | `0x25409` |
    | sweep_protocol_fee | `0830be07b644b7e5` | `0x25376` |
    | sync_user_volume_accumulator | `561fc057a3574fee` | `0x25ff1` |
    | toggle_cashback_enabled | `7367e0ffbd5956c3` | `0x243d8` |
    | toggle_create_v2 | `1cffe6f0ac6bcbab` | `0x2430e` |
    | toggle_mayhem_mode | `01096fd0641fffa3` | `0x245dc` |
    | update_creator_fee_config | `3dafa0f9424288af` | `0x246a6` |
    | update_global_authority | `e3b54ac4d01561d5` | `0x24261` |
    | update_holder_reward_config | `e1fc4204c723ec10` | `0x244a2` |

## pump_amm
- size: 1,162,040 bytes .text, 139,524 instructions
- functions recovered: 831  |  call sites: 7,397
- syscalls linked (14, via 123 callx sites): abort, sol_create_program_address, sol_get_clock_sysvar, sol_get_rent_sysvar, sol_get_return_data, sol_invoke_signed_rust, sol_log_, sol_log_data, sol_log_pubkey, sol_memcmp_, sol_memcpy_, sol_memset_, sol_sha256, sol_try_find_program_address
- source files baked into binary (0):
- instructions mapped to handlers: 30/31

    | instruction | discriminator | handler |
    |---|---|---|
    | admin_update_token_incentives | `d10b7357d5177ccc` | `0x1cb9d` |
    | boost_buy_and_burn | `694406af000723a2` | `0x1c8e7` |
    | buy | `66063d1201daebea` | `0x1cec9` |
    | buy_exact_quote_in | `c62e1552b4d9e870` | `0x1cfb1` |
    | claim_cashback | `253a237ebe35e4c5` | `0x1da42` |
    | claim_token_incentives | `1004471ccc01281b` | `0x1cc57` |
    | close_user_volume_accumulator | `f945a4da9667548a` | `0x1cd93` |
    | collect_coin_creator_fee | `a039592ab58b2b42` | `0x1d51d` |
    | create_config | `c9cff3724b6f2fbd` | `0x1c17f` |
    | create_pool | `e992d18ecf6840bc` | `0x1c634` |
    | deposit | `f223c68952e1f2b6` | `0x1ca4f` |
    | disable | `b9adbb5ad80feee9` | `0x1c2a1` |
    | extend_account | `ea66c2cb96483ee5` | `0x1d47e` |
    | init_boost | `8ce9215e845ac28f` | `0x1c7b3` |
    | init_user_volume_accumulator | `5e06ca73ff60e8b7` | `0x1cce2` |
    | migrate_pool_coin_creator | `d0089f044aaf103a` | `0x1d8e7` |
    | sell | `33e685a4017f83ad` | `0x1d099` |
    | set_boost_authority | `e3954c2a8227eacd` | `0x1c839` |
    | set_coin_creator | `d295802dbc3a4eaf` | `0x1d56e` |
    | set_reserved_fee_recipients | `6faca2e87259d58e` | `0x1c98d` |
    | sync_user_volume_accumulator | `561fc057a3574fee` | `0x1ce17` |
    | toggle_boost | `75a1a04adf897663` | `0x1d7cc` |
    | toggle_cashback_enabled | `7367e0ffbd5956c3` | `0x1d977` |
    | toggle_mayhem_mode | `01096fd0641fffa3` | `0x1d701` |
    | transfer_creator_fees_to_pump | `8b348655e4e56cf1` | `0x1d846` |
    | transfer_creator_fees_to_pump_v2 | `01214eb921432c5c` | `0x1d898` |
    | update_admin | `a1b028d53cb8b3e4` | `0x1c398` |
    | update_buyback_config | `fbe0ab92a01a71e9` | `0x1dacc` |
    | update_fee_config | `68b867f258976b14` | `0x1c446` |
    | withdraw | `b712469c946da122` | `0x1caf6` |

    unmapped (IDL-only / variant): ['admin_set_coin_creator']

## pump_fees
- size: 799,648 bytes .text, 96,083 instructions
- functions recovered: 637  |  call sites: 4,741
- syscalls linked (15, via 121 callx sites): abort, sol_create_program_address, sol_get_clock_sysvar, sol_get_rent_sysvar, sol_invoke_signed_rust, sol_log_, sol_log_data, sol_log_pubkey, sol_memcmp_, sol_memcpy_, sol_memmove_, sol_memset_, sol_set_return_data, sol_sha256, sol_try_find_program_address
- source files baked into binary (0):

## mayhem
- size: 706,744 bytes .text, 83,947 instructions
- functions recovered: 502  |  call sites: 4,902
- syscalls linked (13, via 93 callx sites): abort, sol_get_clock_sysvar, sol_get_rent_sysvar, sol_invoke_signed_rust, sol_log_, sol_log_data, sol_log_pubkey, sol_memcmp_, sol_memcpy_, sol_memmove_, sol_memset_, sol_panic_, sol_try_find_program_address
- source files baked into binary (0):
