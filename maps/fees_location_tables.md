# records total=63 program=26 dependency=37

## per-file table

| source file (under `programs/pump-fees/src/`) | panic sites | line:col | first record VA |
|---|---|---|---|
| `common/mod.rs` | 3 | 21:48, 21:56, 33:56 | `0xc8a50` |
| `instructions/admin/update_fee_config.rs` | 2 | 7:1, 16:1 | `0xc8c38` |
| `instructions/admin/upsert_fee_tiers.rs` | 2 | 6:1, 15:1 | `0xc8c68` |
| `instructions/fee_sharing/admin_cto_sharing_config.rs` | 1 | 53:1 | `0xc8c98` |
| `instructions/fee_sharing/claim_social_fee_pda.rs` | 1 | 100:1 | `0xc8cb0` |
| `instructions/fee_sharing/create_fee_sharing_config.rs` | 2 | 37:1, 119:1 | `0xc8cc8` |
| `instructions/fee_sharing/create_social_fee_pda.rs` | 1 | 36:1 | `0xc8cf8` |
| `instructions/fee_sharing/update_fee_shares.rs` | 2 | 114:1, 228:55 | `0xc8af0` |
| `instructions/fee_sharing/update_fee_shares_v2.rs` | 2 | 236:18, 278:55 | `0xc8b08` |
| `lib.rs` | 2 | 27:1, 28:1 | `0xc8d88` |
| `state.rs` | 8 | 50:1, 67:32, 113:1, 135:1, 154:1, 398:19, 398:33, 451:19 | `0xc8b70` |

## function table (program files only)

| function insn | function byte | size (insns) | file:line:col referenced |
|---|---|---|---|
| `0x250d` | `0x012868` | 60 | `common/mod.rs` 21:48, `common/mod.rs` 21:56 |
| `0x3afe` | `0x01d7f0` | 848 | `state.rs` 67:32 |
| `0x500a` | `0x028050` | 1641 | `common/mod.rs` 33:56 |
| `0x6134` | `0x0309a0` | 597 | `instructions/fee_sharing/update_fee_shares.rs` 228:55 |
| `0x673a` | `0x0339d0` | 974 | `common/mod.rs` 33:56 |
| `0x6b1e` | `0x0358f0` | 786 | `instructions/fee_sharing/update_fee_shares_v2.rs` 236:18, `instructions/fee_sharing/update_fee_shares_v2.rs` 278:55 |
| `0x7fd7` | `0x03feb8` | 485 | `state.rs` 398:19, `state.rs` 398:33 |
| `0x81df` | `0x040ef8` | 485 | `state.rs` 451:19 |
| `0xa4f0` | `0x052780` | 103 | `instructions/admin/update_fee_config.rs` 7:1 |
| `0xa561` | `0x052b08` | 103 | `instructions/admin/update_fee_config.rs` 16:1 |
| `0xa802` | `0x054010` | 115 | `instructions/admin/upsert_fee_tiers.rs` 6:1 |
| `0xa87f` | `0x0543f8` | 115 | `instructions/admin/upsert_fee_tiers.rs` 15:1 |
| `0xbd36` | `0x05e9b0` | 237 | `instructions/fee_sharing/admin_cto_sharing_config.rs` 53:1 |
| `0xc64d` | `0x063268` | 48 | `instructions/fee_sharing/claim_social_fee_pda.rs` 100:1 |
| `0xd8a5` | `0x06c528` | 176 | `instructions/fee_sharing/create_fee_sharing_config.rs` 37:1 |
| `0xe41c` | `0x0720e0` | 172 | `instructions/fee_sharing/create_fee_sharing_config.rs` 119:1 |
| `0xec2c` | `0x076160` | 132 | `instructions/fee_sharing/create_social_fee_pda.rs` 36:1 |
| `0xf498` | `0x07a4c0` | 136 | `instructions/fee_sharing/update_fee_shares.rs` 114:1 |
| `0x102e5` | `0x081728` | 125 | `state.rs` 50:1 |
| `0x103c1` | `0x081e08` | 108 | `state.rs` 113:1 |
| `0x1048c` | `0x082460` | 220 | `state.rs` 135:1 |
| `0x105c5` | `0x082e28` | 149 | `state.rs` 154:1 |
| `0x106b7` | `0x0835b8` | 177 | `lib.rs` 27:1 |
| `0x107c7` | `0x083e38` | 493 | `lib.rs` 27:1 |
| `0x11951` | `0x08ca88` | 361 | `lib.rs` 28:1 |

## paths with no Location record

- `programs/pump-fees/src/instructions/admin/extend_fee_config.rs`
- `programs/pump-fees/src/instructions/admin/initialize_fee_config.rs`
- `programs/pump-fees/src/instructions/admin/initialize_fee_program_global.rs`
- `programs/pump-fees/src/instructions/admin/update_buyback_authority.rs`
- `programs/pump-fees/src/instructions/admin/update_fee_program_global.rs`
- `programs/pump-fees/src/instructions/buyback/mod.rs`
- `programs/pump-fees/src/instructions/fee_sharing/create_donation_fee_pda.rs`
- `programs/pump-fees/src/instructions/fee_sharing/mod.rs`
- `programs/pump-fees/src/instructions/withdraw.rs`
