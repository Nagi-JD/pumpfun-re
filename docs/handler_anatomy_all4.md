# Per-handler anatomy of the four deployed programs

Body-accurate anatomy of every instruction handler the dispatcher exposes in `pump`, `pump_amm`, `pump_fees` and `mayhem`: **147 handler bodies, 22907 instructions**. Every figure here is read from the deployed bytes with `tools/handler_anatomy.py`; the raw per-handler records are in `maps/<prog>_handler_anatomy.json`.

## Method

1. **Frame boundaries are relocation-aware.** A `call` whose 32-bit immediate is an unapplied `R_BPF_64_32` relocation is a loader-patched call slot (every `sol_*` syscall). Treating such a slot as a call target invents a function start in the middle of the caller and truncates its body. `handler_anatomy.py` builds function starts from resolved call targets only, plus the ELF entry point. Measured effect: pump 906 real frames vs 1169 naive (264 bogus entries), pump_amm 663 real frames vs 831 naive (169 bogus entries), pump_fees 489 real frames vs 637 naive (149 bogus entries), mayhem 374 real frames vs 502 naive (129 bogus entries).

2. **Every handler body is identified by itself.** Anchor logs `Instruction: <PascalCase(name)>` from the handler frame as a `(ptr,len)` pair (`lddw ptr` + `mov len`). That string is read back from `.rodata` and compared with the dispatcher-map name, so a body is never attributed on address guesswork: pump 53/53, pump_amm 38/38, pump_fees 31/31, mayhem 25/25. The same scan collects the frame's other string constants (Anchor account names, seed prefixes, panic messages).

3. **Frame-local syscalls, callee syscalls kept apart.** A handler's own runtime calls are listed with their call site; a helper's calls stay under the helper. Nothing is re-attributed across a call edge.

4. **Custom-error raises are attributed by frame ownership**: in a handler body, in a direct callee body, or deeper. The re-derived raise-store totals reproduce the error-site catalog exactly (pump 366, pump_amm 233, pump_fees 68, mayhem 29).

## 1. Census

| program | handlers | instructions | median insns | range | frames (aware / naive) | identity match | raise stores | codes |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| pump (`6EF8…F6P`) | 53 | 9175 | 174 | 61–389 | 906 / 1169 | 53/53 | 366 | 96 |
| pump_amm / PumpSwap (`pAMM…XEA`) | 38 | 6559 | 165 | 78–377 | 663 / 831 | 38/38 | 233 | 74 |
| pump_fees (`pfee…ojVZ`) | 31 | 5027 | 169 | 12–249 | 489 / 637 | 31/31 | 68 | 28 |
| mayhem (`MAyh…MD4e`) | 25 | 2146 | 68 | 43–399 | 374 / 502 | 25/25 | 29 | 14 |

## 2. Runtime surface: one wrapper per syscall

Each program funnels its runtime interaction through a handful of tiny wrapper frames; every one of these syscalls has exactly **one** call site in its program. An instruction handler therefore reaches the runtime only through these wrappers.

| syscall | pump | pump_amm | pump_fees | mayhem |
|---|---|---|---|---|
| `custom_panic` | 0x35591 (2i) | 0x221c7 (2i) | 0x1750d (2i) | 0x14671 (2i) |
| `sol_create_program_address` | 0x34ffe (56i) | 0x21c34 (56i) | 0x16f7a (56i) | — |
| `sol_get_clock_sysvar` | 0x34127 (29i) | 0x20dc7 (29i) | 0x1621e (29i) | 0x13dfa (26i) |
| `sol_get_rent_sysvar` | 0x34144 (24i) | 0x20de4 (24i) | 0x1623b (24i) | 0x13e14 (21i) |
| `sol_get_return_data` | 0x3442b (135i) | 0x210c7 (135i) | — | — |
| `sol_invoke_signed_rust` | 0x343ae (121i) | 0x2104c (121i) | 0x164a3 (121i) | 0x136a3 (125i) |
| `sol_log_data` | 0x3409f (2i) | 0x20d50 (2i) | 0x161a7 (2i) | 0x1333b (2i) |
| `sol_log_pubkey` | 0x35038 (2i) | 0x21c6e (2i) | 0x16fb4 (2i) | 0x14142 (2i) |
| `sol_memcmp_` | 0x366cf (8i) | 0x2331c (8i) | 0x184e6 (8i) | 0x154be (8i) |
| `sol_memmove_` | 0x366c6 (4i) | — | 0x184dd (4i) | 0x154b5 (4i) |
| `sol_panic_` | — | — | — | 0x1067e (57i) |
| `sol_set_return_data` | 0x34429 (2i) | — | 0x1651e (2i) | — |
| `sol_sha256` | 0x351f5 (20i) | 0x21e2b (20i) | 0x17171 (20i) | — |
| `sol_try_find_program_address` | 0x34fd7 (37i) | 0x21c0d (37i) | 0x16f53 (37i) | — |

The wrappers are the same compiled code: comparing instruction shape (opcode, register bytes, offset — the loader-patched call immediates excluded), `sol_invoke_signed_rust` (121 instructions), `sol_get_return_data` (135), `sol_create_program_address` (56), `sol_try_find_program_address` (37), `sol_sha256` (20), `sol_get_clock_sysvar` (29), `sol_get_rent_sysvar` (24), `sol_memcmp_` (8), `sol_memmove_` (4), `sol_log_data` (2), `sol_log_pubkey` (2), `custom_panic` (2) are identical in `pump`, `pump_amm` and `pump_fees`. `mayhem` carries only the 2/4/8-instruction wrappers identically and differs on clock (26 vs 29), rent (21 vs 24) and invoke (125 vs 121, 116 differing slots), and has no `sol_sha256`, `sol_create_program_address`, `sol_try_find_program_address`, `sol_get_return_data` or `sol_set_return_data` site — it instead carries a `sol_panic_` wrapper (57 instructions).

### pump (`6EF8…F6P`) — shared helper frames

| helper frame | insns | handlers calling it | syscalls | raise stores | strings |
|---|---:|---:|---|---:|---|
| 0x366c2 | 4 | 53 | `sol_memcpy_` | 0 | - |
| 0x351cc | 41 | 33 | - | 0 | - |
| 0x33e64 | 70 | 33 | - | 0 | - |
| 0x526 | 77 | 28 | - | 0 | - |
| 0x35649 | 68 | 14 | - | 0 | - |
| 0x1412 | 31 | 14 | - | 0 | - |
| 0xdcf | 321 | 13 | - | 0 | - |
| 0x2cca9 | 497 | 10 | `abort` | 0 | global, authority, global, event_authority |

### pump_amm / PumpSwap (`pAMM…XEA`) — shared helper frames

| helper frame | insns | handlers calling it | syscalls | raise stores | strings |
|---|---:|---:|---|---:|---|
| 0x23313 | 4 | 37 | `sol_memcpy_` | 0 | - |
| 0x21e02 | 41 | 22 | - | 0 | - |
| 0x20bc7 | 70 | 22 | - | 0 | - |
| 0x3af | 77 | 16 | - | 0 | - |
| 0x9e0 | 204 | 11 | - | 0 | - |
| 0x2227f | 68 | 10 | - | 0 | - |
| 0x109f | 79 | 10 | - | 0 | - |
| 0x10804 | 411 | 5 | `abort` | 0 | admin, global_config, global_config, event_authority |

### pump_fees (`pfee…ojVZ`) — shared helper frames

| helper frame | insns | handlers calling it | syscalls | raise stores | strings |
|---|---:|---:|---|---:|---|
| 0x184d9 | 4 | 29 | `sol_memcpy_` | 0 | - |
| 0x1601e | 70 | 22 | - | 0 | - |
| 0x2b1 | 77 | 20 | - | 0 | - |
| 0x17148 | 41 | 19 | - | 0 | - |
| 0xbd0 | 122 | 7 | - | 0 | - |
| 0xa0f | 124 | 7 | - | 0 | - |
| 0x1621c | 2 | 4 | - | 0 | - |
| 0x175af | 3 | 4 | - | 0 | - |

### mayhem (`MAyh…MD4e`) — shared helper frames

| helper frame | insns | handlers calling it | syscalls | raise stores | strings |
|---|---:|---:|---|---:|---|
| 0x154b1 | 4 | 24 | `sol_memcpy_` | 0 | - |
| 0x14526 | 97 | 14 | - | 0 | - |
| 0x134bd | 68 | 14 | - | 0 | - |
| 0x6471 | 499 | 10 | `sol_try_find_program_address` | 0 | global_params, admin, global_params, global_params |
| 0x6694 | 88 | 10 | - | 0 | - |
| 0x70ce | 1235 | 1 | `sol_try_find_program_address` | 0 | pump_program, pump_event_authority, system_program, token_program |
| 0x1b13 | 667 | 1 | `abort` | 2 | - |
| 0x75f7 | 303 | 1 | - | 0 | - |

## 3. pump_fees, handler by handler

| handler | body | insns | own syscalls | direct callees (insns, raises, syscalls) | frame strings |
|---|---|---:|---|---|---|
| `admin_cto_sharing_config` | 0x139e4 | 171 | `sol_log_`@0x139ec | 0xba35 (733i); 0x17148 (41i); 0x175c5 (68i); 0x1275 (31i) +5 | `sharing_config` |
| `claim_social_fee_pda` | 0x13b5d | 248 | `sol_log_`@0x13b65 | 0x1d11 (69i); 0xbe2e (748i, abort); 0x184d9 (4i, sol_memcpy_); 0x40d1 (551i, abort,sol_log_) +8 | `social_fee_pda`, `called `Result::unwrap()` on an `Err` value` … |
| `claim_social_fee_pda_v2` | 0x13c64 | 249 | `sol_log_`@0x13c6c | 0x1d11 (69i); 0xc131 (1199i); 0x184d9 (4i, sol_memcpy_); 0x4308 (1303i, abort,sol_log_) +7 | `called `Result::unwrap()` on an `Err` value` |
| `crank_donation_fee_pda` | 0x140b8 | 104 | `sol_log_`@0x140bf | 0xc788 (1312i, abort); 0x184d9 (4i, sol_memcpy_); 0x483d (1950i, abort,sol_log_); 0xcf6f (112i) | - |
| `create_donation_fee_pda` | 0x14044 | 113 | `sol_log_`@0x1404b | 0xcfe6 (1094i, abort); 0x184d9 (4i, sol_memcpy_); 0x500a (1641i, 10r, abort,sol_log_); 0xb3b (147i) +1 | `donation_fee_pda` |
| `create_fee_sharing_config` | 0x13810 | 168 | `sol_log_`@0x13817 | 0xd95d (1321i, abort); 0x184d9 (4i, sol_memcpy_); 0x56c7 (1510i, 5r, abort); 0xe2a5 (365i) | - |
| `create_social_fee_pda` | 0x13a95 | 194 | `sol_log_`@0x13a9d | 0x1d11 (69i); 0xe4d2 (860i, abort); 0x184d9 (4i, sol_memcpy_); 0x5cd3 (389i, 1r, abort,sol_log_) +4 | `social_fee_pda` |
| `extend_fee_config` | 0x134a2 | 158 | `sol_log_`@0x134a9 | 0x8e83 (430i, abort); 0x184d9 (4i, sol_memcpy_); 0x254c (750i, 5r, sol_log_) | - |
| `get_fees` | 0x136a0 | 184 | `sol_log_`@0x136a8 | 0x175c5 (68i); 0x1275 (31i); 0xfd68 (216i); 0x17148 (41i) +6 | - |
| `get_fees_with_quote_mint` | 0x13763 | 164 | `sol_log_`@0x1376b | 0x175c5 (68i); 0x1275 (31i); 0xfd68 (216i); 0x17148 (41i) +6 | - |
| `initialize_buyback` | 0x13d6a | 149 | `sol_log_`@0x13d72 | 0xab73 (879i); 0x17148 (41i); 0x1601e (70i); 0x184d9 (4i, sol_memcpy_) +2 | - |
| `initialize_fee_config` | 0x12d72 | 139 | `sol_log_`@0x12d79 | 0x906f (753i, abort); 0x184d9 (4i, sol_memcpy_); 0x2861 (337i, abort); 0xbd0 (122i) +1 | `fee_config` |
| `initialize_fee_program_global` | 0x12e01 | 197 | `sol_log_`@0x12e09 | 0x9690 (833i, abort); 0x184d9 (4i, sol_memcpy_); 0x29c7 (353i, abort); 0xa0f (124i) +3 | `fee_program_global` |
| `revoke_fee_sharing_authority` | 0x138ba | 12 | `sol_log_`@0x138be | 0x14217 (58i, 1r) | - |
| `set_authority` | 0x130de | 188 | `sol_log_`@0x130e6 | 0xa5d2 (548i, abort); 0x184d9 (4i, sol_memcpy_); 0x327e (387i, 1r, abort); 0xa0f (124i) +3 | `fee_program_global` |
| `set_claim_rate_limit` | 0x13034 | 166 | `sol_log_`@0x1303c | 0xa5d2 (548i, abort); 0x184d9 (4i, sol_memcpy_); 0x36ee (313i, abort); 0xa0f (124i) +3 | `fee_program_global` |
| `set_disable_flags` | 0x12f8a | 166 | `sol_log_`@0x12f92 | 0xa5d2 (548i, abort); 0x184d9 (4i, sol_memcpy_); 0x35af (299i, abort); 0xa0f (124i) +3 | `fee_program_global` |
| `set_exotic_flat_fees` | 0x13541 | 173 | `sol_log_`@0x13549 | 0x9cc5 (632i, abort); 0x184d9 (4i, sol_memcpy_); 0x2b3d (665i, abort); 0xbd0 (122i) +3 | `fee_config` |
| `set_social_claim_authority` | 0x12eca | 188 | `sol_log_`@0x12ed2 | 0xa5d2 (548i, abort); 0x184d9 (4i, sol_memcpy_); 0x341d (382i, abort); 0xa0f (124i) +3 | `fee_program_global` |
| `sweep_buyback` | 0x13e01 | 163 | `sol_log_`@0x13e09 | 0xb4fa (1125i); 0x17148 (41i); 0x1601e (70i); 0x184d9 (4i, sol_memcpy_) +2 | - |
| `transfer_fee_sharing_authority` | 0x138c7 | 12 | `sol_log_`@0x138cb | 0x14258 (58i, 1r) | - |
| `update_admin` | 0x135f3 | 169 | `sol_log_`@0x135fa | 0x9f50 (689i, abort); 0x184d9 (4i, sol_memcpy_); 0x2def (332i, abort); 0xbd0 (122i) +1 | `fee_config` |
| `update_buyback_authority` | 0x13ea6 | 212 | `sol_log_`@0x13eae | 0xa214 (711i, abort); 0x184d9 (4i, sol_memcpy_); 0x2f50 (80i, 1r); 0xa0f (124i) +4 | `buyback_vault`, `fee_program_global` |
| `update_buyback_claim_rate_limit` | 0x13f80 | 190 | `sol_log_`@0x13f88 | 0xa214 (711i, abort); 0x184d9 (4i, sol_memcpy_); 0x2fa7 (73i, 1r); 0xa0f (124i) +4 | `buyback_vault`, `fee_program_global` |
| `update_fee_config` | 0x1319e | 195 | `sol_log_`@0x131a6 | 0x1f95 (133i); 0xa8fc (612i, abort); 0x184d9 (4i, sol_memcpy_); 0x2ff7 (312i, abort) +4 | `fee_config` |
| `update_fee_shares` | 0x138d4 | 129 | `sol_log_`@0x138dc | 0x212b (147i); 0xecba (1927i, abort); 0x184d9 (4i, sol_memcpy_); 0x5e6f (696i, 2r, abort) +4 | `sharing_config` |
| `update_fee_shares_v2` | 0x1395a | 134 | `sol_log_`@0x13962 | 0x212b (147i); 0xf52a (2034i); 0x184d9 (4i, sol_memcpy_); 0x673a (974i, 2r, abort) +4 | `sharing_config` |
| `update_stable_fee_config` | 0x13329 | 179 | `sol_log_`@0x13331 | 0x1f95 (133i); 0xa8fc (612i, abort); 0x184d9 (4i, sol_memcpy_); 0x313d (307i, abort) +3 | `fee_config` |
| `upsert_fee_tiers` | 0x13267 | 188 | `sol_log_`@0x1326f | 0x1f95 (133i); 0xa8fc (612i, abort); 0x184d9 (4i, sol_memcpy_); 0x383b (302i, abort) +4 | `fee_config` |
| `upsert_stable_fee_tiers` | 0x133e0 | 188 | `sol_log_`@0x133e8 | 0x1f95 (133i); 0xa8fc (612i, abort); 0x184d9 (4i, sol_memcpy_); 0x3977 (302i, abort) +4 | `fee_config` |
| `withdraw` | 0x14121 | 137 | `sol_log_`@0x14128 | 0xfe47 (967i); 0x184d9 (4i, sol_memcpy_); 0x79b6 (967i, 2r, abort); 0x10223 (99i) | - |

## 4. pump (`6EF8…F6P`), handler by handler

| handler | body | insns | own syscalls | direct callees (insns, raises, syscalls) | frame strings |
|---|---|---:|---|---|---|
| `add_quote_mint` | 0x24774 | 174 | `sol_log_`@0x2477c | 0x2cca9 (497i, abort); 0x366c2 (4i, sol_memcpy_); 0x13432 (315i, 4r) +4 | `global` |
| `admin_cto` | 0x25b40 | 264 | `sol_log_`@0x25b48 | 0x16caf (2855i); 0x366c2 (4i, sol_memcpy_); 0x4542 (3339i, 15r, abort,sol_log_) +7 | `bonding_curve` |
| `admin_set_idl_authority` | 0x260a3 | 115 | `sol_log_`@0x260ab | 0x14510 (808i, abort); 0x366c2 (4i, sol_memcpy_); 0x2aafd (680i, 3r, abort) +3 | - |
| `admin_update_token_incentives` | 0x25c54 | 184 | `sol_log_`@0x25c5c | 0x1e276 (936i); 0x351cc (41i); 0x33e64 (70i) +3 | - |
| `buy` | 0x2549c | 216 | `sol_log_`@0x254a4 | 0x2dcfe (1773i); 0x351cc (41i); 0x33e64 (70i) +5 | - |
| `buy_exact_quote_in_v2` | 0x24f6b | 196 | `sol_log_`@0x24f73 | 0x1486f (2814i); 0x366c2 (4i, sol_memcpy_); 0x27ec6 (2464i, 11r, abort) +5 | - |
| `buy_exact_quote_in_v3` | 0x25185 | 168 | `sol_log_`@0x2518d | 0x204af (1664i); 0x366c2 (4i, sol_memcpy_); 0x2913f (952i, 8r) +5 | - |
| `buy_exact_sol_in` | 0x25579 | 216 | `sol_log_`@0x25581 | 0x2dcfe (1773i); 0x351cc (41i); 0x33e64 (70i) +5 | - |
| `buy_v2` | 0x24ea2 | 196 | `sol_log_`@0x24eaa | 0x1486f (2814i); 0x366c2 (4i, sol_memcpy_); 0x27737 (1896i, 5r) +5 | - |
| `buy_v3` | 0x250d9 | 168 | `sol_log_`@0x250e1 | 0x204af (1664i); 0x366c2 (4i, sol_memcpy_); 0x28f74 (444i, 3r) +5 | - |
| `claim_cashback` | 0x25d99 | 142 | `sol_log_`@0x25da0 | 0x1f1a0 (458i, abort); 0x366c2 (4i, sol_memcpy_); 0xed45 (467i, 2r, abort,sol_log_) +2 | `user_volume_accumulator` |
| `claim_cashback_v2` | 0x25e2a | 143 | `sol_log_`@0x25e31 | 0x1f375 (730i, abort); 0x366c2 (4i, sol_memcpy_); 0xef28 (1070i, 4r, abort,sol_log_) +2 | `user_volume_accumulator` |
| `claim_token_incentives` | 0x25d0e | 138 | `sol_log_`@0x25d15 | 0x1e986 (1267i, abort); 0x366c2 (4i, sol_memcpy_); 0xea61 (716i, abort,sol_log_) +1 | - |
| `close_user_volume_accumulator` | 0x25f6d | 131 | `sol_log_`@0x25f74 | 0x1f691 (496i, abort); 0x366c2 (4i, sol_memcpy_); 0xf378 (331i, abort) +1 | - |
| `collect_creator_fee` | 0x2586e | 70 | `sol_log_`@0x25875 | 0x17878 (588i, abort); 0x366c2 (4i, sol_memcpy_); 0x5316 (502i, 1r, abort,sol_log_) +1 | - |
| `create` | 0x24c1b | 246 | `sol_log_`@0x24c23 | 0x1f0b (69i); 0x351cc (41i); 0x33e64 (70i) +4 | - |
| `create_v2` | 0x24d15 | 389 | `sol_log_`@0x24d1d | 0x1f0b (69i); 0x351cc (41i); 0x33e64 (70i) +7 | - |
| `distribute_creator_fees` | 0x26225 | 174 | `sol_log_`@0x2622c | 0x183ab (877i, abort); 0x366c2 (4i, sol_memcpy_); 0x6508 (620i, 2r, abort,sol_log_) +4 | `called `Result::unwrap()` on an `Err` value` … |
| `distribute_creator_fees_v2` | 0x262dd | 236 | `sol_log_`@0x262e5 | 0x35649 (68i); 0x1412 (31i); 0x351cc (41i) +8 | `called `Result::unwrap()` on an `Err` value` … |
| `distribute_fee_to_holders` | 0x258fa | 241 | `sol_log_`@0x25902 | 0x18aca (885i); 0x1c30 (44i); 0x351cc (41i) +5 | - |
| `extend_account` | 0x257cf | 158 | `sol_log_`@0x257d6 | 0x1985a (477i, abort); 0x366c2 (4i, sol_memcpy_); 0x771b (629i, 2r, abort,sol_log_) | - |
| `get_minimum_distributable_fee` | 0x261a8 | 119 | `sol_log_`@0x261af | 0x18736 (629i, abort); 0x366c2 (4i, sol_memcpy_); 0x64a6 (92i) +2 | - |
| `init_user_volume_accumulator` | 0x25ebc | 174 | `sol_log_`@0x25ec3 | 0x1f8e5 (754i, abort); 0x366c2 (4i, sol_memcpy_); 0xf4d8 (349i, abort) +2 | `user_volume_accumulator` |
| `initialize` | 0x2421b | 67 | `sol_log_`@0x24222 | 0x2c857 (361i); 0x366c2 (4i, sol_memcpy_); 0xdcf (321i) +1 | `global` |
| `initialize_quote_control` | 0x264a2 | 61 | `sol_log_`@0x264a9 | 0x1bcdd (371i); 0x366c2 (4i, sol_memcpy_); 0x366ca (5i, sol_memset_) +2 | `quote_control` |
| `migrate` | 0x256fb | 77 | `sol_log_`@0x25702 | 0x19eea (2952i); 0x366c2 (4i, sol_memcpy_); 0x7f6e (662i, 1r, sol_log_) +2 | - |
| `migrate_bonding_curve_creator` | 0x26118 | 140 | `sol_log_`@0x2611f | 0x18e92 (723i, abort); 0x366c2 (4i, sol_memcpy_); 0x6fc1 (535i, 2r, abort) +2 | `bonding_curve` |
| `migrate_v2` | 0x25749 | 133 | `sol_log_`@0x25750 | 0x1ab5e (2865i); 0x366c2 (4i, sol_memcpy_); 0x9311 (1084i, 2r, sol_log_) +1 | - |
| `multi_hop_curve_swap` | 0x252b8 | 183 | `sol_log_`@0x252c0 | 0x22eb (247i); 0x1b72b (806i); 0x366c2 (4i, sol_memcpy_) +6 | - |
| `remove_quote_control_mint` | 0x26667 | 188 | `sol_log_`@0x2666f | 0x1c9db (612i, abort); 0x366c2 (4i, sol_memcpy_); 0xd82c (366i, abort) +4 | `quote_control` |
| `remove_quote_mint` | 0x24826 | 174 | `sol_log_`@0x2482e | 0x2cca9 (497i, abort); 0x366c2 (4i, sol_memcpy_); 0x13585 (153i, 2r) +4 | `global` |
| `sell` | 0x25656 | 162 | `sol_log_`@0x2565e | 0x2e8a4 (1366i); 0x366c2 (4i, sol_memcpy_); 0x2a511 (1034i, 4r) +3 | - |
| `sell_v2` | 0x25034 | 162 | `sol_log_`@0x2503c | 0x1cc55 (2712i); 0x366c2 (4i, sol_memcpy_); 0x288a1 (1714i, 5r) +3 | - |
| `sell_v3` | 0x25231 | 133 | `sol_log_`@0x25239 | 0x204af (1664i); 0x366c2 (4i, sol_memcpy_); 0x29515 (734i, 3r) +3 | - |
| `set_creator` | 0x25a82 | 185 | `sol_log_`@0x25a8a | 0x1917f (812i, abort); 0x366c2 (4i, sol_memcpy_); 0x71f8 (722i, abort,sol_log_) +4 | `bonding_curve` |
| `set_max_curve_depth` | 0x24566 | 114 | `sol_log_`@0x2456e | 0x2cca9 (497i, abort); 0x366c2 (4i, sol_memcpy_); 0xdcf (321i) +3 | `global` |
| `set_mayhem_virtual_params` | 0x24ab5 | 167 | `sol_log_`@0x24abc | 0x19a7b (1037i, abort); 0x366c2 (4i, sol_memcpy_); 0x26ff8 (343i, abort) +1 | - |
| `set_metaplex_creator` | 0x259f2 | 140 | `sol_log_`@0x259f9 | 0x195b8 (651i, abort); 0x366c2 (4i, sol_memcpy_); 0x74f7 (419i, abort,sol_log_) +2 | `bonding_curve` |
| `set_params` | 0x2494e | 355 | `sol_log_`@0x24956 | 0x1a0d (79i); 0x1f56 (33i); 0x351cc (41i) +6 | `global` |
| `set_quote_control_admin` | 0x264e3 | 188 | `sol_log_`@0x264eb | 0x1c143 (596i, abort); 0x366c2 (4i, sol_memcpy_); 0xcc59 (391i, abort) +4 | `quote_control` |
| `set_quote_control_mint_reserves` | 0x267e9 | 190 | `sol_log_`@0x267f1 | 0x1c3a8 (597i, abort); 0x366c2 (4i, sol_memcpy_); 0xcdf5 (381i, abort) +4 | `quote_control` |
| `set_quote_control_reserves_admin` | 0x26728 | 188 | `sol_log_`@0x26730 | 0x1c611 (580i, abort); 0x366c2 (4i, sol_memcpy_); 0xcf87 (391i, abort) +4 | `quote_control` |
| `set_reserved_fee_recipients` | 0x24b5d | 186 | `sol_log_`@0x24b65 | 0x1dbd4 (480i, abort); 0x366c2 (4i, sol_memcpy_); 0xdfdf (1096i, 2r, abort) +4 | `global` |
| `set_virtual_quote_reserves` | 0x248d8 | 114 | `sol_log_`@0x248e0 | 0x2cca9 (497i, abort); 0x366c2 (4i, sol_memcpy_); 0xdcf (321i) +3 | `global` |
| `sweep_creator_fee` | 0x25409 | 144 | `sol_log_`@0x25410 | 0x1ddbe (1094i); 0x366c2 (4i, sol_memcpy_); 0xe502 (959i, 1r, abort,sol_log_) +2 | `bonding_curve` |
| `sweep_protocol_fee` | 0x25376 | 144 | `sol_log_`@0x2537d | 0x1ddbe (1094i); 0x366c2 (4i, sol_memcpy_); 0xe502 (959i, 1r, abort,sol_log_) +2 | `bonding_curve` |
| `sync_user_volume_accumulator` | 0x25ff1 | 175 | `sol_log_`@0x25ff8 | 0x1ffb6 (620i, abort); 0x366c2 (4i, sol_memcpy_); 0xf64a (340i, abort,sol_log_) +2 | `user_volume_accumulator` |
| `toggle_cashback_enabled` | 0x243d8 | 196 | `sol_log_`@0x243e0 | 0x35649 (68i); 0x1412 (31i); 0x351cc (41i) +6 | `global` |
| `toggle_create_v2` | 0x2430e | 196 | `sol_log_`@0x24316 | 0x35649 (68i); 0x1412 (31i); 0x351cc (41i) +6 | `global` |
| `toggle_mayhem_mode` | 0x245dc | 196 | `sol_log_`@0x245e4 | 0x35649 (68i); 0x1412 (31i); 0x351cc (41i) +6 | `global` |
| `update_creator_fee_config` | 0x246a6 | 200 | `sol_log_`@0x246ae | 0x35649 (68i); 0x1412 (31i); 0x351cc (41i) +6 | `global` |
| `update_global_authority` | 0x24261 | 170 | `sol_log_`@0x24268 | 0x20fef (572i, abort); 0x366c2 (4i, sol_memcpy_); 0x26918 (387i, abort) +2 | `global` |
| `update_holder_reward_config` | 0x244a2 | 189 | `sol_log_`@0x244aa | 0x35649 (68i); 0x1412 (31i); 0x351cc (41i) +5 | `global` |

## 4. pump_amm / PumpSwap (`pAMM…XEA`), handler by handler

| handler | body | insns | own syscalls | direct callees (insns, raises, syscalls) | frame strings |
|---|---|---:|---|---|---|
| `admin_cto_pool` | 0x1d5fe | 251 | `sol_log_`@0x1d606 | 0x2227f (68i); 0x109f (79i); 0xf89a (508i, abort) +6 | `pool` |
| `admin_update_token_incentives` | 0x1cb9d | 184 | `sol_log_`@0x1cba5 | 0xfaf0 (931i); 0x21e02 (41i); 0x20bc7 (70i) +3 | - |
| `boost_buy_and_burn` | 0x1c8e7 | 164 | `sol_log_`@0x1c8ef | 0x11afa (1254i); 0x23313 (4i, sol_memcpy_); 0x3fdb (1407i, 9r, abort) +3 | - |
| `buy` | 0x1cec9 | 227 | `sol_log_`@0x1ced1 | 0x155fb (2097i); 0x23313 (4i, sol_memcpy_); 0x6ed6 (1214i, 4r) +5 | - |
| `buy_exact_quote_in` | 0x1cfb1 | 227 | `sol_log_`@0x1cfb9 | 0x155fb (2097i); 0x23313 (4i, sol_memcpy_); 0x74b4 (1572i, 9r, abort) +5 | - |
| `buy_exact_quote_in_v2` | 0x1d1e2 | 131 | `sol_log_`@0x1d1ea | 0x174e4 (1369i); 0x23313 (4i, sol_memcpy_); 0xa944 (855i, 7r) +3 | - |
| `buy_v2` | 0x1d15d | 131 | `sol_log_`@0x1d165 | 0x174e4 (1369i); 0x23313 (4i, sol_memcpy_); 0xa66a (705i, 4r) +3 | - |
| `claim_cashback` | 0x1da42 | 137 | `sol_log_`@0x1da49 | 0x198cb (937i, abort); 0x23313 (4i, sol_memcpy_); 0xb6b7 (475i, 2r, abort) +1 | - |
| `claim_token_incentives` | 0x1cc57 | 138 | `sol_log_`@0x1cc5e | 0x190b1 (1267i, abort); 0x23313 (4i, sol_memcpy_); 0xb4ae (497i, abort,sol_log_) +1 | - |
| `close_user_volume_accumulator` | 0x1cd93 | 131 | `sol_log_`@0x1cd9a | 0x19cff (496i, abort); 0x23313 (4i, sol_memcpy_); 0xb8b2 (331i, abort) +1 | - |
| `collect_coin_creator_fee` | 0x1d51d | 80 | `sol_log_`@0x1d524 | 0x1211d (1010i, abort); 0x23313 (4i, sol_memcpy_); 0x45d1 (472i, 1r, abort,sol_log_) +2 | - |
| `create_config` | 0x1c17f | 285 | `sol_log_`@0x1c187 | 0x1b1e (270i); 0x23313 (4i, sol_memcpy_); 0x21e02 (41i) +5 | `global_config` |
| `create_pool` | 0x1c634 | 377 | `sol_log_`@0x1c63c | 0x2227f (68i); 0x21e02 (41i); 0x20bc7 (70i) +6 | - |
| `deposit` | 0x1ca4f | 165 | `sol_log_`@0x1ca57 | 0x1508c (1069i); 0x23313 (4i, sol_memcpy_); 0x5f67 (868i, 4r) +3 | - |
| `disable` | 0x1c2a1 | 241 | `sol_log_`@0x1c2a9 | 0x2227f (68i); 0x109f (79i); 0x21e02 (41i) +6 | `global_config` |
| `extend_account` | 0x1d47e | 158 | `sol_log_`@0x1d485 | 0x14d8d (477i, abort); 0x23313 (4i, sol_memcpy_); 0x5ce4 (617i, 2r, abort,sol_log_) | - |
| `init_boost` | 0x1c7b3 | 133 | `sol_log_`@0x1c7ba | 0x11286 (1249i); 0x23313 (4i, sol_memcpy_); 0x3df2 (481i, abort) +1 | - |
| `init_user_volume_accumulator` | 0x1cce2 | 174 | `sol_log_`@0x1cce9 | 0x19f53 (754i, abort); 0x23313 (4i, sol_memcpy_); 0xba12 (349i, abort) +2 | `user_volume_accumulator` |
| `migrate_pool_coin_creator` | 0x1d8e7 | 140 | `sol_log_`@0x1d8ee | 0x12581 (649i, abort); 0x23313 (4i, sol_memcpy_); 0x47c8 (531i, 2r, abort) +2 | `pool` |
| `multi_hop_swap` | 0x1d2ec | 132 | `sol_log_`@0x1d2f4 | 0x166cd (1109i); 0x23313 (4i, sol_memcpy_); 0x7b78 (1145i, 7r) +3 | - |
| `sell` | 0x1d099 | 193 | `sol_log_`@0x1d0a1 | 0x17f52 (1700i); 0x23313 (4i, sol_memcpy_); 0x936a (1125i, 4r) +3 | - |
| `sell_v2` | 0x1d267 | 131 | `sol_log_`@0x1d26f | 0x174e4 (1369i); 0x23313 (4i, sol_memcpy_); 0xace2 (719i, 3r) +3 | - |
| `set_boost_authority` | 0x1c839 | 171 | `sol_log_`@0x1c840 | 0x109ab (524i, abort); 0x23313 (4i, sol_memcpy_); 0x30a6 (364i, abort) +2 | `global_config` |
| `set_coin_creator` | 0x1d56e | 140 | `sol_log_`@0x1d575 | 0x12824 (649i, abort); 0x23313 (4i, sol_memcpy_); 0x49fb (898i, 1r, abort,sol_log_) +2 | `pool` |
| `set_reserved_fee_recipients` | 0x1c98d | 190 | `sol_log_`@0x1c995 | 0x10bc5 (488i, abort); 0x23313 (4i, sol_memcpy_); 0x3227 (1096i, 2r, abort) +4 | `global_config` |
| `sweep_creator_fee` | 0x1d3f8 | 133 | `sol_log_`@0x1d3ff | 0x18ca6 (850i); 0x23313 (4i, sol_memcpy_); 0xb281 (537i, 1r, sol_log_) +1 | - |
| `sweep_protocol_fee` | 0x1d372 | 133 | `sol_log_`@0x1d379 | 0x18ca6 (850i); 0x23313 (4i, sol_memcpy_); 0xb281 (537i, 1r, sol_log_) +1 | - |
| `sync_user_volume_accumulator` | 0x1ce17 | 175 | `sol_log_`@0x1ce1e | 0x1a624 (620i, abort); 0x23313 (4i, sol_memcpy_); 0xbb84 (340i, abort,sol_log_) +2 | `user_volume_accumulator` |
| `toggle_boost` | 0x1d7cc | 116 | `sol_log_`@0x1d7d4 | 0x2227f (68i); 0x109f (79i); 0x21e02 (41i) +5 | `global_config` |
| `toggle_cashback_enabled` | 0x1d977 | 197 | `sol_log_`@0x1d97f | 0x2227f (68i); 0x109f (79i); 0x21e02 (41i) +6 | `global_config` |
| `toggle_mayhem_mode` | 0x1d701 | 197 | `sol_log_`@0x1d709 | 0x2227f (68i); 0x109f (79i); 0x21e02 (41i) +6 | `global_config` |
| `transfer_creator_fees_to_pump` | 0x1d846 | 81 | `sol_log_`@0x1d84d | 0x12ac9 (1129i, abort); 0x23313 (4i, sol_memcpy_); 0x4db5 (1013i, 2r, abort,sol_log_) +2 | - |
| `transfer_creator_fees_to_pump_v2` | 0x1d898 | 78 | `sol_log_`@0x1d89f | 0x12f7f (1286i, abort); 0x23313 (4i, sol_memcpy_); 0x51ba (1360i, 2r, abort,sol_log_) +2 | - |
| `update_admin` | 0x1c398 | 171 | `sol_log_`@0x1c39f | 0x10e52 (509i, abort); 0x23313 (4i, sol_memcpy_); 0x37b6 (327i, abort) +2 | `global_config` |
| `update_buyback_config` | 0x1dacc | 199 | `sol_log_`@0x1dad4 | 0x10804 (411i, abort); 0x23313 (4i, sol_memcpy_); 0x3912 (161i, 1r) +6 | `global_config` |
| `update_creator_fee_config` | 0x1c565 | 201 | `sol_log_`@0x1c56d | 0x2227f (68i); 0x109f (79i); 0x21e02 (41i) +6 | `global_config` |
| `update_fee_config` | 0x1c446 | 282 | `sol_log_`@0x1c44e | 0x1b1e (270i); 0x23313 (4i, sol_memcpy_); 0x21e02 (41i) +5 | `global_config` |
| `withdraw` | 0x1caf6 | 165 | `sol_log_`@0x1cafe | 0x1508c (1069i); 0x23313 (4i, sol_memcpy_); 0x64ea (874i, 5r) +3 | - |

## 4. mayhem (`MAyh…MD4e`), handler by handler

| handler | body | insns | own syscalls | direct callees (insns, raises, syscalls) | frame strings |
|---|---|---:|---|---|---|
| `burn_tokens` | 0xffe1 | 58 | `sol_log_`@0xffe7 | 0x70ce (1235i, sol_try_find_program_address); 0x154b1 (4i, sol_memcpy_); 0x1b13 (667i, 2r, abort) +1 | - |
| `buy` | 0x1027f | 102 | `sol_log_`@0x10287 | 0x14526 (97i); 0x134bd (68i); 0xa4bf (1753i, sol_try_find_program_address) +3 | - |
| `buy_pump_swap` | 0x1041f | 102 | `sol_log_`@0x10427 | 0x14526 (97i); 0x134bd (68i); 0x8c6f (2261i, sol_try_find_program_address) +3 | - |
| `buy_v2` | 0x1034f | 102 | `sol_log_`@0x10357 | 0x14526 (97i); 0x134bd (68i); 0xb8db (2076i, sol_try_find_program_address) +3 | - |
| `extend_account` | 0x1001c | 46 | `sol_log_`@0x10022 | 0x774d (427i, sol_try_find_program_address); 0x1de2 (503i, 2r, abort,sol_log_) | - |
| `initialize_fee_recipient` | 0xfc41 | 83 | `sol_log_`@0xfc49 | 0x7a64 (932i, sol_try_find_program_address); 0x14526 (97i); 0x134bd (68i) +3 | - |
| `initialize_global_params` | 0xfbfc | 68 | `sol_log_`@0xfc02 | 0x6031 (374i, sol_try_find_program_address); 0x154b1 (4i, sol_memcpy_); 0x640c (88i) | - |
| `initialize_mayhem_state` | 0x101de | 56 | `sol_log_`@0x101e4 | 0xd25f (1037i, sol_try_find_program_address); 0x154b1 (4i, sol_memcpy_); 0x10527 (116i, abort) +1 | - |
| `reset_sol_deployed` | 0xff2d | 43 | `sol_log_`@0xff33 | 0x6471 (499i, sol_try_find_program_address); 0x154b1 (4i, sol_memcpy_); 0x6694 (88i) | - |
| `reset_stable_deployed` | 0xff59 | 43 | `sol_log_`@0xff5f | 0x6471 (499i, sol_try_find_program_address); 0x154b1 (4i, sol_memcpy_); 0x6694 (88i) | - |
| `reset_state` | 0xfef1 | 59 | `sol_log_`@0xfef7 | 0x6471 (499i, sol_try_find_program_address); 0x154b1 (4i, sol_memcpy_); 0x6694 (88i) | - |
| `resume_trading` | 0xff85 | 45 | `sol_log_`@0xff8b | 0x6471 (499i, sol_try_find_program_address); 0x154b1 (4i, sol_memcpy_); 0x5870 (59i, 1r) +1 | - |
| `sell` | 0x10217 | 102 | `sol_log_`@0x1021f | 0x14526 (97i); 0x134bd (68i); 0xade1 (1718i, sol_try_find_program_address) +3 | - |
| `sell_pump_swap` | 0x103b7 | 102 | `sol_log_`@0x103bf | 0x14526 (97i); 0x134bd (68i); 0x9993 (2190i, sol_try_find_program_address) +3 | - |
| `sell_v2` | 0x102e7 | 102 | `sol_log_`@0x102ef | 0x14526 (97i); 0x134bd (68i); 0xc368 (2081i, sol_try_find_program_address) +3 | - |
| `stop_trading` | 0xffb3 | 45 | `sol_log_`@0xffb9 | 0x6471 (499i, sol_try_find_program_address); 0x154b1 (4i, sol_memcpy_); 0x582d (59i, 1r) +1 | - |
| `sweep_fees` | 0xfc96 | 60 | `sol_log_`@0xfc9c | 0x834e (935i, sol_try_find_program_address); 0x154b1 (4i, sol_memcpy_); 0x25b2 (997i, 1r, abort) +1 | - |
| `sweep_fees_admin` | 0xfcd3 | 60 | `sol_log_`@0xfcd9 | 0x87eb (910i, sol_try_find_program_address); 0x154b1 (4i, sol_memcpy_); 0x21c9 (950i, 1r, abort) +1 | - |
| `update_admin` | 0xfe93 | 92 | `sol_log_`@0xfe9b | 0x14526 (97i); 0x134bd (68i); 0x6471 (499i, sol_try_find_program_address) +2 | - |
| `update_global_params` | 0x1004b | 399 | `sol_log_`@0x10053 | 0x14526 (97i); 0x1471e (180i); 0x124bc (33i) +7 | - |
| `update_max_sol_per_sweep` | 0xfd10 | 62 | `sol_log_`@0xfd18 | 0x14526 (97i); 0x134bd (68i); 0x6471 (499i, sol_try_find_program_address) +2 | - |
| `update_max_stable_per_sweep` | 0xfd50 | 62 | `sol_log_`@0xfd58 | 0x14526 (97i); 0x134bd (68i); 0x6471 (499i, sol_try_find_program_address) +2 | - |
| `update_trader` | 0xfe35 | 92 | `sol_log_`@0xfe3d | 0x14526 (97i); 0x134bd (68i); 0x6471 (499i, sol_try_find_program_address) +2 | - |
| `withdraw_admin` | 0xfd90 | 80 | `sol_log_`@0xfd98 | 0x14526 (97i); 0x134bd (68i); 0x66f9 (514i, sol_try_find_program_address) +3 | - |
| `withdraw_quote_admin` | 0xfde2 | 81 | `sol_log_`@0xfdea | 0x14526 (97i); 0x134bd (68i); 0x6992 (1114i, sol_try_find_program_address) +3 | - |

## 5. Reproducing

```
PUMPFUN_EVIDENCE=evidence/original python3 tools/handler_anatomy.py --all --out maps/
python3 tools/report_anatomy.py          # census / wrapper / helper summary
python3 tools/anatomy_doc.py > docs/handler_anatomy_all4.md
```

