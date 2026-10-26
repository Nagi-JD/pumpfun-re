# PDA / seed catalog (deployed programs)

Read-only analysis of the captured `deployed.so` files. **[B]** = the seed literal
bytes, the `lddw`+`R_BPF_64_RELATIVE` site, the length immediates and the syscall
site are all in the deployed ELF; the seed *role* (which account the PDA is) is a
reading of the account resolution around the call. No behavioral MATCH is claimed.

Method. `sbftool` decodes `.text` but not `.rel.dyn`; the loader here applies it
(`R_BPF_64_32` -> syscall name, `R_BPF_64_RELATIVE` -> the `lddw` whose low 32 bits
are the target VA), drops relocated call sites from the function starts, adds
`e_entry` back and bounds the last function by the last decoded pc (the corrections
measured in #2). For each PDA syscall the argument registers `r1..r5` are abstract-
interpreted from the enclosing function entry: a seed array is recognised as a
`(base, n)` pair where every one of the `n` 16-byte `SolBytes` slots decodes as
`{addr, len}` with `addr` a relocated `.rodata` pointer plus an immediate length (the
literal case) or a pointer into the frame (the variable case, e.g. a 32-byte pubkey).
Recognition therefore does not depend on the C ABI argument order, and a slot shape
that does not fit is rejected rather than guessed.

Program ids are recovered when the derivation loads a 32-byte constant; the base58
value is given so the owning program is identified, not assumed.

| program | insns | functions | PDA/signed sites | recovered vectors | unrecovered | handlers |
|---|---:|---:|---:|---:|---:|---:|
| pump | 215873 | 906 | 202 | 110 | 92 | 53 |
| pump_amm | 139524 | 663 | 88 | 46 | 42 | 38 |
| pump_fees | 96083 | 489 | 84 | 48 | 36 | 31 |
| mayhem | 83947 | 374 | 96 | 25 | 71 | 25 |

## Seed / prefix vocabulary

Every literal recovered as an element of a seed vector, with the number of sites that
load it, the programs whose code loads it, and the program ids recovered among the 32-byte
constant arguments of those calls. The program-id argument is one of them but the column
does not prove which: a call can also carry a second program id (e.g. a fees id in r1 next
to the ATA id in r4). Per-site argument shapes and registers are in `maps/pda_seeds.json`.

| literal | len | rodata VA per program | sites | loaded by | program ids in args |
|---|---:|---|---:|---|---|
| `bonding-curve` | 13 | mayhem 0xadc1a, pump 0x1b683a, pump_amm 0x11cb69, pump_fees 0xc4d6f | 31 | mayhem, pump, pump_amm, pump_fees | pump |
| `bonding-curve-v2` | 16 | mayhem 0xad768, pump 0x1b6690 | 4 | mayhem, pump | pump |
| `boost_vault` | 11 | pump_amm 0x11c7f4 | 2 | pump_amm | not recovered |
| `buyback-vault` | 13 | pump_fees 0xc3fe8 | 3 | pump_fees | not recovered |
| `creator-vault` | 13 | pump 0x1b69ca, pump_amm 0x11e28e, pump_fees 0xc4de0 | 16 | pump, pump_amm, pump_fees | pump |
| `creator_vault` | 13 | pump 0x1b74a9, pump_amm 0x11c868, pump_fees 0xc4ded | 9 | pump, pump_amm, pump_fees | pump_amm |
| `donation-fee-pda` | 16 | pump_fees 0xc41d8 | 2 | pump_fees | not recovered |
| `fee-program-global` | 18 | pump_fees 0xc4aea | 7 | pump_fees | not recovered |
| `fee-recipient` | 13 | mayhem 0xad5d5 | 1 | mayhem | not recovered |
| `fee_config` | 10 | pump 0x1b7491, pump_amm 0x11e352, pump_fees 0xc3eb8 | 16 | pump, pump_amm, pump_fees | pump_fees |
| `holder-rewards` | 14 | pump 0x1b68be, pump_amm 0x11cb76 | 4 | pump, pump_amm | pump |
| `mayhem-state` | 12 | mayhem 0xadc0e, pump 0x1b7559 | 9 | mayhem, pump | mayhem |
| `metadata` | 8 | pump 0x1b648f, pump_amm 0x11c5d6 | 4 | pump, pump_amm | metaplex |
| `pool` | 4 | pump 0x1b5dcc, pump_amm 0x11bf8c, pump_fees 0xc3e0c | 9 | pump, pump_amm, pump_fees | pump_amm |
| `pool-authority` | 14 | pump 0x1b68a2, pump_amm 0x11cb5b, pump_fees 0xc4301 | 18 | pump, pump_amm, pump_fees | pump |
| `pool-v2` | 7 | mayhem 0xaddd6, pump_amm 0x11cd62 | 3 | mayhem, pump_amm | pump_amm |
| `pool_lp_mint` | 12 | pump 0x1b77f1, pump_amm 0x11e2c3 | 3 | pump, pump_amm | not recovered |
| `referral-vault` | 14 | pump_fees 0xc451e | 1 | pump_fees | not recovered |
| `sharing-config` | 14 | pump 0x1b7461, pump_amm 0x11e25c, pump_fees 0xc4c0e | 13 | pump, pump_amm, pump_fees | pump, pump_fees |
| `social-fee-pda` | 14 | pump_fees 0xc40d8 | 3 | pump_fees | not recovered |
| `sol-vault` | 9 | mayhem 0xad4a9 | 5 | mayhem | not recovered |
| `user_volume_accumulator` | 23 | pump 0x1b6f73, pump_amm 0x11cd4b | 20 | pump, pump_amm | pump, pump_amm |

Addresses are virtual addresses inside *that* ELF, so they are only comparable
within one program.

A 32-byte constant used *as a seed* is a key, not a prefix. These are the keys
recovered in that position (they are program ids, which is itself informative: a
program deriving another program's PDA needs its id as a seed):

| key seed | rodata VA per program | sites | loaded by |
|---|---|---:|---|
| `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P` | pump 0x1b79df | 6 | pump |
| `metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s` | pump 0x1b5bc8, pump_amm 0x11bdb0 | 4 | pump, pump_amm |
| `pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA` | pump_amm 0x11e53e | 4 | pump_amm |

## pump

### Derivation call sites and seed vectors

`{32B}` = a seed byte string whose address is a frame slot (a pubkey or an
account field); the length is measured, not assumed. `-` in the program-id column
means no 32-byte constant argument was recovered at that site.

| # | syscall | via | insn | byte | fn | seeds | program id | handlers reaching |
|---:|---|---|---:|---:|---:|---|---|---:|
| 1 | `sol_invoke_signed_rust` | wrapper-call | 0x3410c | 0x1a0860 | 0x340a6 | *(not recovered)* | - | 44 |
| 2 | `sol_try_find_program_address` | wrapper-call | 0x2fca | 0x17e50 | 0x2f9e | *(not recovered)* | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 3 | `sol_try_find_program_address` | wrapper-call | 0x3191 | 0x18c88 | 0x30cf | `pool`(4) + <frame -0xe2>(2) + <frame -0x148>(32) + <frame -0x320>(32) + <frame -0x128>(32) | r4=pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA(pump_amm) | 1 |
| 4 | `sol_try_find_program_address` | wrapper-call | 0x3262 | 0x19310 | 0x30cf | `pool-authority`(14) + <frame -0x320>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 5 | `sol_try_find_program_address` | wrapper-call | 0x33e8 | 0x19f40 | 0x33d9 | `bonding-curve`(13) + <?>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 6 | `sol_try_find_program_address` | wrapper-call | 0x3d3e | 0x1e9f0 | 0x3cf8 | `holder-rewards`(14) + <frame -0x4a8>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 7 | `sol_try_find_program_address` | wrapper-call | 0x4561 | 0x22b08 | 0x4542 | `holder-rewards`(14) + <frame -0x6c0>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 8 | `sol_try_find_program_address` | wrapper-call | 0x4911 | 0x24888 | 0x4542 | `creator-vault`(13) + <frame -0x6a0>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 9 | `sol_try_find_program_address` | wrapper-call | 0x9327 | 0x49938 | 0x9311 | *(not recovered)* | r4=pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA(pump_amm) | 1 |
| 10 | `sol_try_find_program_address` | wrapper-call | 0xd9f7 | 0x6cfb8 | 0xd9af | `user_volume_accumulator`(23) + <frame -0x260>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 11 | `sol_try_find_program_address` | wrapper-call | 0xdd9f | 0x6ecf8 | 0xd9af | `bonding-curve-v2`(16) + <?>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 12 | `sol_try_find_program_address` | wrapper-call | 0xde0e | 0x6f070 | 0xdddb | `bonding-curve-v2`(16) + <?>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 3 |
| 13 | `sol_try_find_program_address` | wrapper-call | 0xe53b | 0x729d8 | 0xe502 | `creator-vault`(13) + <?>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 2 |
| 14 | `sol_try_find_program_address` | wrapper-call | 0x14649 | 0xa3248 | 0x14510 | *(not recovered)* | - | 1 |
| 15 | `sol_try_find_program_address` | wrapper-call | 0x14761 | 0xa3b08 | 0x14510 | *(not recovered)* | - | 1 |
| 16 | `sol_try_find_program_address` | wrapper-call | 0x147ab | 0xa3d58 | 0x14510 | *(not recovered)* | - | 1 |
| 17 | `sol_try_find_program_address` | wrapper-call | 0x14b91 | 0xa5c88 | 0x1486f | `user_volume_accumulator`(23) + <frame -0x630>(32) | - | 2 |
| 18 | `sol_try_find_program_address` | wrapper-call | 0x14c3b | 0xa61d8 | 0x1486f | *(not recovered)* | - | 2 |
| 19 | `sol_try_find_program_address` | wrapper-call | 0x14c9c | 0xa64e0 | 0x1486f | <frame -0x4c0>(32) + <frame -0x4a0>(32) + <frame -0x480>(32) | r4=ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL(ata) | 2 |
| 20 | `sol_try_find_program_address` | wrapper-call | 0x14dac | 0xa6d60 | 0x1486f | <frame -0x4c0>(32) + <frame -0x4a0>(32) + <frame -0x480>(32) | r4=ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL(ata) | 2 |
| 21 | `sol_try_find_program_address` | wrapper-call | 0x14de7 | 0xa6f38 | 0x1486f | `bonding-curve`(13) + <frame -0x630>(32) | - | 2 |
| 22 | `sol_try_find_program_address` | wrapper-call | 0x14fc8 | 0xa7e40 | 0x1486f | <frame -0x4c0>(32) + <frame -0x4a0>(32) + <frame -0x480>(32) | r4=ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL(ata) | 2 |
| 23 | `sol_try_find_program_address` | wrapper-call | 0x15069 | 0xa8348 | 0x1486f | `creator-vault`(13) + <?>(32) | - | 2 |
| 24 | `sol_try_find_program_address` | wrapper-call | 0x150c5 | 0xa8628 | 0x1486f | <frame -0x4c0>(32) + <frame -0x4a0>(32) + <frame -0x480>(32) | r4=ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL(ata) | 2 |
| 25 | `sol_try_find_program_address` | wrapper-call | 0x1518e | 0xa8c70 | 0x1486f | `sharing-config`(14) + <frame -0x460>(32) | r4=pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ(pump_fees) | 2 |
| 26 | `sol_try_find_program_address` | wrapper-call | 0x151e8 | 0xa8f40 | 0x1486f | *(not recovered)* | - | 2 |
| 27 | `sol_try_find_program_address` | wrapper-call | 0x1526f | 0xa9378 | 0x1486f | <frame -0x4c0>(32) + <frame -0x4a0>(32) + <frame -0x480>(32) | r1=pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ(pump_fees), r4=ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL(ata) | 2 |
| 28 | `sol_try_find_program_address` | wrapper-call | 0x152d0 | 0xa9680 | 0x1486f | `fee_config`(10) + key:6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P | - | 2 |
| 29 | `sol_try_find_program_address` | wrapper-call | 0x1532c | 0xa9960 | 0x1486f | *(not recovered)* | - | 2 |
| 30 | `sol_try_find_program_address` | wrapper-call | 0x15b1c | 0xad8e0 | 0x158d9 | `bonding-curve`(13) + <frame -0x550>(32) | - | 1 |
| 31 | `sol_try_find_program_address` | wrapper-call | 0x15cbe | 0xae5f0 | 0x158d9 | *(not recovered)* | - | 1 |
| 32 | `sol_try_find_program_address` | wrapper-call | 0x15ce2 | 0xae710 | 0x158d9 | *(not recovered)* | - | 1 |
| 33 | `sol_try_find_program_address` | wrapper-call | 0x15e1c | 0xaf0e0 | 0x158d9 | *(not recovered)* | r4=MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e(mayhem) | 1 |
| 34 | `sol_try_find_program_address` | wrapper-call | 0x15ebb | 0xaf5d8 | 0x158d9 | *(not recovered)* | r4=MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e(mayhem) | 1 |
| 35 | `sol_try_find_program_address` | wrapper-call | 0x15f27 | 0xaf938 | 0x158d9 | `mayhem-state`(12) + <frame -0x460>(32) | r4=MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e(mayhem) | 1 |
| 36 | `sol_try_find_program_address` | wrapper-call | 0x15f86 | 0xafc30 | 0x158d9 | *(not recovered)* | - | 1 |
| 37 | `sol_try_find_program_address` | wrapper-call | 0x16f8e | 0xb7c70 | 0x16caf | *(not recovered)* | - | 1 |
| 38 | `sol_try_find_program_address` | wrapper-call | 0x170d2 | 0xb8690 | 0x16caf | `bonding-curve`(13) + <frame -0x508>(32) | - | 1 |
| 39 | `sol_try_find_program_address` | wrapper-call | 0x171dd | 0xb8ee8 | 0x16caf | <frame -0x4e0>(32) + <frame -0x4c0>(32) + <frame -0x4a0>(32) | - | 1 |
| 40 | `sol_try_find_program_address` | wrapper-call | 0x1723c | 0xb91e0 | 0x16caf | `creator-vault`(13) + <frame -0x508>(32) | - | 1 |
| 41 | `sol_try_find_program_address` | wrapper-call | 0x172ca | 0xb9650 | 0x16caf | <frame -0x4e0>(32) + <frame -0x4c0>(32) + <frame -0x4a0>(32) | - | 1 |
| 42 | `sol_try_find_program_address` | wrapper-call | 0x1735b | 0xb9ad8 | 0x16caf | <frame -0x4e0>(32) + <frame -0x4c0>(32) + <frame -0x4a0>(32) | - | 1 |
| 43 | `sol_try_find_program_address` | wrapper-call | 0x173da | 0xb9ed0 | 0x16caf | *(not recovered)* | - | 1 |
| 44 | `sol_try_find_program_address` | wrapper-call | 0x17445 | 0xba228 | 0x16caf | `pool-authority`(14) + <frame -0x508>(32) | - | 1 |
| 45 | `sol_try_find_program_address` | wrapper-call | 0x174ca | 0xba650 | 0x16caf | `pool`(4) + <frame -0x528>(2) + <frame -0x4e0>(32) + <frame -0x4c0>(32) + <frame -0x4a0>(32) | - | 1 |
| 46 | `sol_try_find_program_address` | wrapper-call | 0x17521 | 0xba908 | 0x16caf | *(not recovered)* | - | 1 |
| 47 | `sol_try_find_program_address` | wrapper-call | 0x17595 | 0xbaca8 | 0x16caf | `creator_vault`(13) + <frame -0x460>(32) | - | 1 |
| 48 | `sol_try_find_program_address` | wrapper-call | 0x17614 | 0xbb0a0 | 0x16caf | <frame -0x4e0>(32) + <frame -0x4c0>(32) + <frame -0x4a0>(32) | - | 1 |
| 49 | `sol_try_find_program_address` | wrapper-call | 0x17695 | 0xbb4a8 | 0x16caf | `sharing-config`(14) + <frame -0x460>(32) | - | 1 |
| 50 | `sol_try_find_program_address` | wrapper-call | 0x176fb | 0xbb7d8 | 0x16caf | *(not recovered)* | - | 1 |
| 51 | `sol_try_find_program_address` | wrapper-call | 0x17755 | 0xbbaa8 | 0x16caf | *(not recovered)* | - | 1 |
| 52 | `sol_try_find_program_address` | wrapper-call | 0x1796d | 0xbcb68 | 0x17878 | `creator-vault`(13) + <frame -0x60>(32) | - | 1 |
| 53 | `sol_try_find_program_address` | wrapper-call | 0x17a3b | 0xbd1d8 | 0x17878 | *(not recovered)* | - | 1 |
| 54 | `sol_try_find_program_address` | wrapper-call | 0x17c9a | 0xbe4d0 | 0x17acf | <frame -0x100>(32) + <frame -0xe0>(32) + <frame -0xc0>(32) | - | 0 |
| 55 | `sol_try_find_program_address` | wrapper-call | 0x17d37 | 0xbe9b8 | 0x17acf | `creator-vault`(13) + <frame -0x128>(32) | - | 0 |
| 56 | `sol_try_find_program_address` | wrapper-call | 0x17dce | 0xbee70 | 0x17acf | <frame -0x100>(32) + <frame -0xe0>(32) + <frame -0xc0>(32) | - | 0 |
| 57 | `sol_try_find_program_address` | wrapper-call | 0x17e29 | 0xbf148 | 0x17acf | *(not recovered)* | - | 0 |
| 58 | `sol_try_find_program_address` | wrapper-call | 0x18066 | 0xc0330 | 0x17f00 | `bonding-curve`(13) + <frame -0xa8>(32) | - | 1 |
| 59 | `sol_try_find_program_address` | wrapper-call | 0x18143 | 0xc0a18 | 0x17f00 | `sharing-config`(14) + <frame -0x20>(32) | r4=pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ(pump_fees) | 1 |
| 60 | `sol_try_find_program_address` | wrapper-call | 0x181d5 | 0xc0ea8 | 0x17f00 | `creator-vault`(13) + <?>(32) | - | 1 |
| 61 | `sol_try_find_program_address` | wrapper-call | 0x18222 | 0xc1110 | 0x17f00 | *(not recovered)* | - | 1 |
| 62 | `sol_try_find_program_address` | wrapper-call | 0x182b1 | 0xc1588 | 0x17f00 | <frame -0x80>(32) + <frame -0x60>(32) + <frame -0x40>(32) | - | 1 |
| 63 | `sol_try_find_program_address` | wrapper-call | 0x184ba | 0xc25d0 | 0x183ab | `bonding-curve`(13) + <frame -0x20>(32) | - | 1 |
| 64 | `sol_try_find_program_address` | wrapper-call | 0x185a6 | 0xc2d30 | 0x183ab | `sharing-config`(14) + <frame -0x40>(32) | r4=pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ(pump_fees) | 1 |
| 65 | `sol_try_find_program_address` | wrapper-call | 0x18639 | 0xc31c8 | 0x183ab | `creator-vault`(13) + <frame -0x230>(32) | - | 1 |
| 66 | `sol_try_find_program_address` | wrapper-call | 0x1868a | 0xc3450 | 0x183ab | *(not recovered)* | - | 1 |
| 67 | `sol_try_find_program_address` | wrapper-call | 0x187f3 | 0xc3f98 | 0x18736 | `bonding-curve`(13) + <frame -0x20>(32) | - | 1 |
| 68 | `sol_try_find_program_address` | wrapper-call | 0x188aa | 0xc4550 | 0x18736 | `sharing-config`(14) + <frame -0x40>(32) | r4=pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ(pump_fees) | 1 |
| 69 | `sol_try_find_program_address` | wrapper-call | 0x1893b | 0xc49d8 | 0x18736 | `creator-vault`(13) + <frame -0x230>(32) | - | 1 |
| 70 | `sol_try_find_program_address` | wrapper-call | 0x18c45 | 0xc6228 | 0x18aca | *(not recovered)* | - | 1 |
| 71 | `sol_try_find_program_address` | wrapper-call | 0x18d12 | 0xc6890 | 0x18aca | `holder-rewards`(14) + <frame -0x460>(32) | - | 1 |
| 72 | `sol_try_find_program_address` | wrapper-call | 0x18de3 | 0xc6f18 | 0x18aca | *(not recovered)* | - | 1 |
| 73 | `sol_try_find_program_address` | wrapper-call | 0x18f73 | 0xc7b98 | 0x18e92 | `bonding-curve`(13) + <frame -0x20>(32) | - | 1 |
| 74 | `sol_try_find_program_address` | wrapper-call | 0x19017 | 0xc80b8 | 0x18e92 | `sharing-config`(14) + <frame -0x40>(32) | r4=pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ(pump_fees) | 1 |
| 75 | `sol_try_find_program_address` | wrapper-call | 0x190f3 | 0xc8798 | 0x18e92 | *(not recovered)* | - | 1 |
| 76 | `sol_try_find_program_address` | wrapper-call | 0x19289 | 0xc9448 | 0x1917f | *(not recovered)* | - | 1 |
| 77 | `sol_try_find_program_address` | wrapper-call | 0x1933a | 0xc99d0 | 0x1917f | `metadata`(8) + key:metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s + <frame -0x40>(32) | r4=metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s(metaplex) | 1 |
| 78 | `sol_try_find_program_address` | wrapper-call | 0x19397 | 0xc9cb8 | 0x1917f | `bonding-curve`(13) + <frame -0x68>(32) | - | 1 |
| 79 | `sol_try_find_program_address` | wrapper-call | 0x19409 | 0xca048 | 0x1917f | *(not recovered)* | - | 1 |
| 80 | `sol_try_find_program_address` | wrapper-call | 0x196a8 | 0xcb540 | 0x195b8 | `metadata`(8) + key:metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s + <frame -0x40>(32) | r4=metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s(metaplex) | 1 |
| 81 | `sol_try_find_program_address` | wrapper-call | 0x1972e | 0xcb970 | 0x195b8 | `bonding-curve`(13) + <frame -0x68>(32) | - | 1 |
| 82 | `sol_try_find_program_address` | wrapper-call | 0x197a1 | 0xcbd08 | 0x195b8 | *(not recovered)* | - | 1 |
| 83 | `sol_try_find_program_address` | wrapper-call | 0x199bb | 0xccdd8 | 0x1985a | *(not recovered)* | - | 1 |
| 84 | `sol_try_find_program_address` | wrapper-call | 0x19bc5 | 0xcde28 | 0x19a7b | *(not recovered)* | r4=MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e(mayhem) | 1 |
| 85 | `sol_try_find_program_address` | wrapper-call | 0x19d0c | 0xce860 | 0x19a7b | *(not recovered)* | - | 1 |
| 86 | `sol_try_find_program_address` | wrapper-call | 0x19d77 | 0xcebb8 | 0x19a7b | `bonding-curve`(13) + <frame -0x20>(32) | - | 1 |
| 87 | `sol_try_find_program_address` | wrapper-call | 0x19dc5 | 0xcee28 | 0x19a7b | *(not recovered)* | - | 1 |
| 88 | `sol_try_find_program_address` | wrapper-call | 0x1a215 | 0xd10a8 | 0x19eea | *(not recovered)* | - | 1 |
| 89 | `sol_try_find_program_address` | wrapper-call | 0x1a2d8 | 0xd16c0 | 0x19eea | `bonding-curve`(13) + <frame -0x4f0>(32) | - | 1 |
| 90 | `sol_try_find_program_address` | wrapper-call | 0x1a49b | 0xd24d8 | 0x19eea | `pool`(4) + <frame -0x4c0>(2) + <frame -0x4a0>(32) + <frame -0x480>(32) + <frame -0x460>(32) | - | 1 |
| 91 | `sol_try_find_program_address` | wrapper-call | 0x1a4d7 | 0xd26b8 | 0x19eea | `pool-authority`(14) + <frame -0x4f0>(32) | - | 1 |
| 92 | `sol_try_find_program_address` | wrapper-call | 0x1a59e | 0xd2cf0 | 0x19eea | <frame -0x4a0>(32) + <?>(32) + <frame -0x480>(32) | - | 1 |
| 93 | `sol_try_find_program_address` | wrapper-call | 0x1a640 | 0xd3200 | 0x19eea | <frame -0x4a0>(32) + <frame -0x480>(32) + <frame -0x460>(32) | - | 1 |
| 94 | `sol_try_find_program_address` | wrapper-call | 0x1a6a8 | 0xd3540 | 0x19eea | *(not recovered)* | - | 1 |
| 95 | `sol_try_find_program_address` | wrapper-call | 0x1a75c | 0xd3ae0 | 0x19eea | `pool_lp_mint`(12) + <frame -0x518>(32) | - | 1 |
| 96 | `sol_try_find_program_address` | wrapper-call | 0x1a7d9 | 0xd3ec8 | 0x19eea | <frame -0x4a0>(32) + <frame -0x480>(32) + <frame -0x460>(32) | - | 1 |
| 97 | `sol_try_find_program_address` | wrapper-call | 0x1a861 | 0xd4308 | 0x19eea | <frame -0x4a0>(32) + <?>(32) + <frame -0x480>(32) | - | 1 |
| 98 | `sol_try_find_program_address` | wrapper-call | 0x1a8ff | 0xd47f8 | 0x19eea | <frame -0x4a0>(32) + <frame -0x480>(32) + <frame -0x460>(32) | - | 1 |
| 99 | `sol_try_find_program_address` | wrapper-call | 0x1a964 | 0xd4b20 | 0x19eea | *(not recovered)* | - | 1 |
| 100 | `sol_try_find_program_address` | wrapper-call | 0x1a9be | 0xd4df0 | 0x19eea | *(not recovered)* | - | 1 |
| 101 | `sol_try_find_program_address` | wrapper-call | 0x1ae70 | 0xd7380 | 0x1ab5e | *(not recovered)* | - | 1 |
| 102 | `sol_try_find_program_address` | wrapper-call | 0x1af3b | 0xd79d8 | 0x1ab5e | `bonding-curve`(13) + <frame -0x4e8>(32) | - | 1 |
| 103 | `sol_try_find_program_address` | wrapper-call | 0x1b0e0 | 0xd8700 | 0x1ab5e | <frame -0x4c0>(32) + <frame -0x4a0>(32) + <frame -0x480>(32) | - | 1 |
| 104 | `sol_try_find_program_address` | wrapper-call | 0x1b155 | 0xd8aa8 | 0x1ab5e | `pool`(4) + <frame -0x508>(2) + <frame -0x4c0>(32) + <frame -0x4a0>(32) + <frame -0x480>(32) | - | 1 |
| 105 | `sol_try_find_program_address` | wrapper-call | 0x1b191 | 0xd8c88 | 0x1ab5e | `pool-authority`(14) + <frame -0x4e8>(32) | - | 1 |
| 106 | `sol_try_find_program_address` | wrapper-call | 0x1b29a | 0xd94d0 | 0x1ab5e | <frame -0x4c0>(32) + <frame -0x4a0>(32) + <frame -0x480>(32) | - | 1 |
| 107 | `sol_try_find_program_address` | wrapper-call | 0x1b329 | 0xd9948 | 0x1ab5e | <frame -0x4c0>(32) + <frame -0x4a0>(32) + <frame -0x480>(32) | - | 1 |
| 108 | `sol_try_find_program_address` | wrapper-call | 0x1b38f | 0xd9c78 | 0x1ab5e | *(not recovered)* | - | 1 |
| 109 | `sol_try_find_program_address` | wrapper-call | 0x1b403 | 0xda018 | 0x1ab5e | `pool_lp_mint`(12) + <frame -0x460>(32) | - | 1 |
| 110 | `sol_try_find_program_address` | wrapper-call | 0x1b484 | 0xda420 | 0x1ab5e | <frame -0x4c0>(32) + <frame -0x4a0>(32) + <frame -0x480>(32) | - | 1 |
| 111 | `sol_try_find_program_address` | wrapper-call | 0x1b513 | 0xda898 | 0x1ab5e | <frame -0x4c0>(32) + <frame -0x4a0>(32) + <frame -0x480>(32) | - | 1 |
| 112 | `sol_try_find_program_address` | wrapper-call | 0x1b5a2 | 0xdad10 | 0x1ab5e | <frame -0x4c0>(32) + <frame -0x4a0>(32) + <frame -0x480>(32) | - | 1 |
| 113 | `sol_try_find_program_address` | wrapper-call | 0x1b64b | 0xdb258 | 0x1ab5e | *(not recovered)* | - | 1 |
| 114 | `sol_try_find_program_address` | wrapper-call | 0x1b88a | 0xdc450 | 0x1b72b | *(not recovered)* | - | 1 |
| 115 | `sol_try_find_program_address` | wrapper-call | 0x1b97c | 0xdcbe0 | 0x1b72b | *(not recovered)* | r4=pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA(pump_amm) | 1 |
| 116 | `sol_try_find_program_address` | wrapper-call | 0x1ba13 | 0xdd098 | 0x1b72b | *(not recovered)* | - | 1 |
| 117 | `sol_try_find_program_address` | wrapper-call | 0x1bbc5 | 0xdde28 | 0x1bae0 | `bonding-curve`(13) + <frame -0xf8>(32) | - | 1 |
| 118 | `sol_try_find_program_address` | wrapper-call | 0x1bd37 | 0xde9b8 | 0x1bcdd | *(not recovered)* | - | 1 |
| 119 | `sol_try_find_program_address` | wrapper-call | 0x1c1f0 | 0xe0f80 | 0x1c143 | *(not recovered)* | - | 1 |
| 120 | `sol_try_find_program_address` | wrapper-call | 0x1c2a8 | 0xe1540 | 0x1c143 | *(not recovered)* | - | 1 |
| 121 | `sol_try_find_program_address` | wrapper-call | 0x1c31c | 0xe18e0 | 0x1c143 | *(not recovered)* | - | 1 |
| 122 | `sol_try_find_program_address` | wrapper-call | 0x1c4bd | 0xe25e8 | 0x1c3a8 | *(not recovered)* | - | 1 |
| 123 | `sol_try_find_program_address` | wrapper-call | 0x1c4e2 | 0xe2710 | 0x1c3a8 | *(not recovered)* | - | 1 |
| 124 | `sol_try_find_program_address` | wrapper-call | 0x1c592 | 0xe2c90 | 0x1c3a8 | *(not recovered)* | - | 1 |
| 125 | `sol_try_find_program_address` | wrapper-call | 0x1c715 | 0xe38a8 | 0x1c611 | *(not recovered)* | - | 1 |
| 126 | `sol_try_find_program_address` | wrapper-call | 0x1c73a | 0xe39d0 | 0x1c611 | *(not recovered)* | - | 1 |
| 127 | `sol_try_find_program_address` | wrapper-call | 0x1c7ea | 0xe3f50 | 0x1c611 | *(not recovered)* | - | 1 |
| 128 | `sol_try_find_program_address` | wrapper-call | 0x1caff | 0xe57f8 | 0x1c9db | *(not recovered)* | - | 1 |
| 129 | `sol_try_find_program_address` | wrapper-call | 0x1cb24 | 0xe5920 | 0x1c9db | *(not recovered)* | - | 1 |
| 130 | `sol_try_find_program_address` | wrapper-call | 0x1cbd4 | 0xe5ea0 | 0x1c9db | *(not recovered)* | - | 1 |
| 131 | `sol_try_find_program_address` | wrapper-call | 0x1cf5f | 0xe7af8 | 0x1cc55 | `user_volume_accumulator`(23) + <frame -0x610>(32) | - | 1 |
| 132 | `sol_try_find_program_address` | wrapper-call | 0x1d009 | 0xe8048 | 0x1cc55 | *(not recovered)* | - | 1 |
| 133 | `sol_try_find_program_address` | wrapper-call | 0x1d06a | 0xe8350 | 0x1cc55 | <frame -0x4c0>(32) + <frame -0x4a0>(32) + <frame -0x480>(32) | r4=ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL(ata) | 1 |
| 134 | `sol_try_find_program_address` | wrapper-call | 0x1d17a | 0xe8bd0 | 0x1cc55 | <frame -0x4c0>(32) + <frame -0x4a0>(32) + <frame -0x480>(32) | r4=ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL(ata) | 1 |
| 135 | `sol_try_find_program_address` | wrapper-call | 0x1d1b5 | 0xe8da8 | 0x1cc55 | `bonding-curve`(13) + <frame -0x610>(32) | - | 1 |
| 136 | `sol_try_find_program_address` | wrapper-call | 0x1d396 | 0xe9cb0 | 0x1cc55 | <frame -0x4c0>(32) + <frame -0x4a0>(32) + <frame -0x480>(32) | r4=ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL(ata) | 1 |
| 137 | `sol_try_find_program_address` | wrapper-call | 0x1d437 | 0xea1b8 | 0x1cc55 | `creator-vault`(13) + <?>(32) | - | 1 |
| 138 | `sol_try_find_program_address` | wrapper-call | 0x1d493 | 0xea498 | 0x1cc55 | <frame -0x4c0>(32) + <frame -0x4a0>(32) + <frame -0x480>(32) | r4=ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL(ata) | 1 |
| 139 | `sol_try_find_program_address` | wrapper-call | 0x1d55c | 0xeaae0 | 0x1cc55 | `sharing-config`(14) + <frame -0x460>(32) | r4=pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ(pump_fees) | 1 |
| 140 | `sol_try_find_program_address` | wrapper-call | 0x1d5ee | 0xeaf70 | 0x1cc55 | <frame -0x4c0>(32) + <frame -0x4a0>(32) + <frame -0x480>(32) | r1=pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ(pump_fees), r4=ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL(ata) | 1 |
| 141 | `sol_try_find_program_address` | wrapper-call | 0x1d64f | 0xeb278 | 0x1cc55 | `fee_config`(10) + key:6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P | - | 1 |
| 142 | `sol_try_find_program_address` | wrapper-call | 0x1d6ab | 0xeb558 | 0x1cc55 | *(not recovered)* | - | 1 |
| 143 | `sol_try_find_program_address` | wrapper-call | 0x1dc5c | 0xee2e0 | 0x1dbd4 | *(not recovered)* | - | 1 |
| 144 | `sol_try_find_program_address` | wrapper-call | 0x1dd2b | 0xee958 | 0x1dbd4 | *(not recovered)* | - | 1 |
| 145 | `sol_try_find_program_address` | wrapper-call | 0x1df44 | 0xefa20 | 0x1ddbe | *(not recovered)* | - | 2 |
| 146 | `sol_try_find_program_address` | wrapper-call | 0x1dfb9 | 0xefdc8 | 0x1ddbe | `bonding-curve`(13) + <frame -0x4e8>(32) | - | 2 |
| 147 | `sol_try_find_program_address` | wrapper-call | 0x1e0b0 | 0xf0580 | 0x1ddbe | <frame -0x4c0>(32) + <frame -0x4a0>(32) + <frame -0x480>(32) | r4=ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL(ata) | 2 |
| 148 | `sol_try_find_program_address` | wrapper-call | 0x1e111 | 0xf0888 | 0x1ddbe | <frame -0x4c0>(32) + <frame -0x4a0>(32) + <frame -0x480>(32) | r4=ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL(ata) | 2 |
| 149 | `sol_try_find_program_address` | wrapper-call | 0x1e139 | 0xf09c8 | 0x1ddbe | *(not recovered)* | - | 2 |
| 150 | `sol_try_find_program_address` | wrapper-call | 0x1e4a3 | 0xf2518 | 0x1e276 | *(not recovered)* | - | 1 |
| 151 | `sol_try_find_program_address` | wrapper-call | 0x1e53a | 0xf29d0 | 0x1e276 | *(not recovered)* | - | 1 |
| 152 | `sol_try_find_program_address` | wrapper-call | 0x1e589 | 0xf2c48 | 0x1e276 | *(not recovered)* | - | 1 |
| 153 | `sol_try_find_program_address` | wrapper-call | 0x1eba7 | 0xf5d38 | 0x1e986 | *(not recovered)* | - | 1 |
| 154 | `sol_try_find_program_address` | wrapper-call | 0x1ed48 | 0xf6a40 | 0x1e986 | `user_volume_accumulator`(23) + <frame -0x178>(32) | - | 1 |
| 155 | `sol_try_find_program_address` | wrapper-call | 0x1eda5 | 0xf6d28 | 0x1e986 | *(not recovered)* | - | 1 |
| 156 | `sol_try_find_program_address` | wrapper-call | 0x1f257 | 0xf92b8 | 0x1f1a0 | `user_volume_accumulator`(23) + <frame -0x20>(32) | - | 1 |
| 157 | `sol_try_find_program_address` | wrapper-call | 0x1f2f0 | 0xf9780 | 0x1f1a0 | *(not recovered)* | - | 1 |
| 158 | `sol_try_find_program_address` | wrapper-call | 0x1f4b0 | 0xfa580 | 0x1f375 | `user_volume_accumulator`(23) + <frame -0xa8>(32) | - | 1 |
| 159 | `sol_try_find_program_address` | wrapper-call | 0x1f55c | 0xfaae0 | 0x1f375 | <frame -0x80>(32) + <frame -0x60>(32) + <frame -0x40>(32) | - | 1 |
| 160 | `sol_try_find_program_address` | wrapper-call | 0x1f5bd | 0xfade8 | 0x1f375 | *(not recovered)* | - | 1 |
| 161 | `sol_try_find_program_address` | wrapper-call | 0x1f733 | 0xfb998 | 0x1f691 | `user_volume_accumulator`(23) + <frame -0x20>(32) | - | 1 |
| 162 | `sol_try_find_program_address` | wrapper-call | 0x1f7f7 | 0xfbfb8 | 0x1f691 | *(not recovered)* | - | 1 |
| 163 | `sol_try_find_program_address` | wrapper-call | 0x1fa0c | 0xfd060 | 0x1f8e5 | `user_volume_accumulator`(23) + <frame -0xa0>(32) | - | 1 |
| 164 | `sol_try_find_program_address` | wrapper-call | 0x1fb5f | 0xfdaf8 | 0x1f8e5 | *(not recovered)* | - | 1 |
| 165 | `sol_try_find_program_address` | wrapper-call | 0x20086 | 0x100430 | 0x1ffb6 | *(not recovered)* | - | 1 |
| 166 | `sol_try_find_program_address` | wrapper-call | 0x2011b | 0x1008d8 | 0x1ffb6 | `user_volume_accumulator`(23) + <frame -0x20>(32) | - | 1 |
| 167 | `sol_try_find_program_address` | wrapper-call | 0x2018c | 0x100c60 | 0x1ffb6 | *(not recovered)* | - | 1 |
| 168 | `sol_try_find_program_address` | wrapper-call | 0x206c1 | 0x103608 | 0x204af | `user_volume_accumulator`(23) + <frame -0x558>(32) | - | 3 |
| 169 | `sol_try_find_program_address` | wrapper-call | 0x2076b | 0x103b58 | 0x204af | *(not recovered)* | - | 3 |
| 170 | `sol_try_find_program_address` | wrapper-call | 0x207a3 | 0x103d18 | 0x204af | `bonding-curve`(13) + <frame -0x558>(32) | - | 3 |
| 171 | `sol_try_find_program_address` | wrapper-call | 0x209ab | 0x104d58 | 0x204af | <frame -0x4c8>(32) + <frame -0x4a8>(32) + <frame -0x488>(32) | r4=ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL(ata) | 3 |
| 172 | `sol_try_find_program_address` | wrapper-call | 0x20aea | 0x105750 | 0x204af | *(not recovered)* | - | 3 |
| 173 | `sol_try_find_program_address` | wrapper-call | 0x210b2 | 0x108590 | 0x20fef | *(not recovered)* | - | 1 |
| 174 | `sol_try_find_program_address` | wrapper-call | 0x21182 | 0x108c10 | 0x20fef | *(not recovered)* | - | 1 |
| 175 | `sol_try_find_program_address` | wrapper-call | 0x23df9 | 0x11efc8 | 0x23de2 | *(not recovered)* | - | 0 |
| 176 | `sol_try_find_program_address` | wrapper-call | 0x268b8 | 0x1345c0 | 0x268ac | *(not recovered)* | - | 0 |
| 177 | `sol_try_find_program_address` | wrapper-call | 0x2c8af | 0x164578 | 0x2c857 | *(not recovered)* | - | 1 |
| 178 | `sol_try_find_program_address` | wrapper-call | 0x2cd31 | 0x166988 | 0x2cca9 | *(not recovered)* | - | 10 |
| 179 | `sol_try_find_program_address` | wrapper-call | 0x2ce26 | 0x167130 | 0x2cca9 | *(not recovered)* | - | 10 |
| 180 | `sol_try_find_program_address` | wrapper-call | 0x2d0ae | 0x168570 | 0x2cea5 | `bonding-curve`(13) + <frame -0xd0>(32) | - | 1 |
| 181 | `sol_try_find_program_address` | wrapper-call | 0x2d220 | 0x169100 | 0x2cea5 | *(not recovered)* | - | 1 |
| 182 | `sol_try_find_program_address` | wrapper-call | 0x2d244 | 0x169220 | 0x2cea5 | *(not recovered)* | - | 1 |
| 183 | `sol_try_find_program_address` | wrapper-call | 0x2d378 | 0x169bc0 | 0x2cea5 | `metadata`(8) + key:metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s + <frame -0x40>(32) | - | 1 |
| 184 | `sol_try_find_program_address` | wrapper-call | 0x2d3c8 | 0x169e40 | 0x2cea5 | *(not recovered)* | - | 1 |
| 185 | `sol_try_find_program_address` | wrapper-call | 0x2df4a | 0x16fa50 | 0x2dcfe | `user_volume_accumulator`(23) + <frame -0x550>(32) | - | 2 |
| 186 | `sol_try_find_program_address` | wrapper-call | 0x2dff4 | 0x16ffa0 | 0x2dcfe | *(not recovered)* | - | 2 |
| 187 | `sol_try_find_program_address` | wrapper-call | 0x2e030 | 0x170180 | 0x2dcfe | `bonding-curve`(13) + <frame -0x550>(32) | - | 2 |
| 188 | `sol_try_find_program_address` | wrapper-call | 0x2e21a | 0x1710d0 | 0x2dcfe | `creator-vault`(13) + <frame -0x898>(32) | - | 2 |
| 189 | `sol_try_find_program_address` | wrapper-call | 0x2e240 | 0x171200 | 0x2dcfe | *(not recovered)* | - | 2 |
| 190 | `sol_try_find_program_address` | wrapper-call | 0x2e2e6 | 0x171730 | 0x2dcfe | *(not recovered)* | - | 2 |
| 191 | `sol_try_find_program_address` | wrapper-call | 0x2e348 | 0x171a40 | 0x2dcfe | `fee_config`(10) + key:6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P | - | 2 |
| 192 | `sol_try_find_program_address` | wrapper-call | 0x2ea85 | 0x175428 | 0x2e8a4 | *(not recovered)* | - | 1 |
| 193 | `sol_try_find_program_address` | wrapper-call | 0x2eb0e | 0x175870 | 0x2e8a4 | `bonding-curve`(13) + <frame -0x460>(32) | - | 1 |
| 194 | `sol_try_find_program_address` | wrapper-call | 0x2ec76 | 0x1763b0 | 0x2e8a4 | `creator-vault`(13) + <frame -0x7f8>(32) | - | 1 |
| 195 | `sol_try_find_program_address` | wrapper-call | 0x2ec9c | 0x1764e0 | 0x2e8a4 | *(not recovered)* | - | 1 |
| 196 | `sol_try_find_program_address` | wrapper-call | 0x2ed54 | 0x176aa0 | 0x2e8a4 | `fee_config`(10) + key:6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P | - | 1 |
| 197 | `sol_try_find_program_address` | wrapper-call | 0x2f565 | 0x17ab28 | 0x2f468 | *(not recovered)* | - | 0 |
| 198 | `sol_try_find_program_address` | wrapper-call | 0x33274 | 0x1993a0 | 0x3323c | <frame -0x60>(32) + <frame -0x40>(32) + <frame -0x20>(32) | r4=ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL(ata) | 20 |
| 199 | `sol_try_find_program_address` | wrapper-call | 0x332bb | 0x1995d8 | 0x3327e | <frame -0x60>(32) + <frame -0x40>(32) + <frame -0x20>(32) | r4=ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL(ata) | 16 |
| 200 | `sol_try_find_program_address` | wrapper-call | 0x33a9d | 0x19d4e8 | 0x33a96 | *(not recovered)* | - | 1 |
| 201 | `sol_create_program_address` | wrapper-call | 0x1b90f | 0xdc878 | 0x1b72b | `fee_config`(10) + key:6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P + <frame -0x461>(1) | r4=pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ(pump_fees) | 1 |
| 202 | `sol_create_program_address` | wrapper-call | 0x20a60 | 0x105300 | 0x204af | `fee_config`(10) + key:6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P + <frame -0x461>(1) | r4=pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ(pump_fees) | 3 |

### Handler -> derivations reachable (forward call closure)

`body` = the derivation is inside the handler function itself; `closure` = it is
inside a helper the handler can reach. Signatures keep the literal parts and
collapse the dynamic ones to their length.

| handler | entry | body | closure | seed signatures (body) |
|---|---|---:|---:|---|
| `add_quote_mint` | 0x24774 | 0 | 2 | - |
| `admin_cto` | 0x25b40 | 0 | 19 | - |
| `admin_set_idl_authority` | 0x260a3 | 0 | 5 | - |
| `admin_update_token_incentives` | 0x25c54 | 0 | 6 | - |
| `buy` | 0x2549c | 0 | 10 | - |
| `buy_exact_quote_in_v2` | 0x24f6b | 0 | 16 | - |
| `buy_exact_quote_in_v3` | 0x25185 | 0 | 9 | - |
| `buy_exact_sol_in` | 0x25579 | 0 | 10 | - |
| `buy_v2` | 0x24ea2 | 0 | 16 | - |
| `buy_v3` | 0x250d9 | 0 | 9 | - |
| `claim_cashback` | 0x25d99 | 0 | 3 | - |
| `claim_cashback_v2` | 0x25e2a | 0 | 4 | - |
| `claim_token_incentives` | 0x25d0e | 0 | 6 | - |
| `close_user_volume_accumulator` | 0x25f6d | 0 | 3 | - |
| `collect_creator_fee` | 0x2586e | 0 | 3 | - |
| `create` | 0x24c1b | 0 | 7 | - |
| `create_v2` | 0x24d15 | 0 | 15 | - |
| `distribute_creator_fees` | 0x26225 | 0 | 5 | - |
| `distribute_creator_fees_v2` | 0x262dd | 0 | 8 | - |
| `distribute_fee_to_holders` | 0x258fa | 0 | 6 | - |
| `extend_account` | 0x257cf | 0 | 2 | - |
| `get_minimum_distributable_fee` | 0x261a8 | 0 | 3 | - |
| `init_user_volume_accumulator` | 0x25ebc | 0 | 3 | - |
| `initialize` | 0x2421b | 0 | 2 | - |
| `initialize_quote_control` | 0x264a2 | 0 | 2 | - |
| `migrate` | 0x256fb | 0 | 15 | - |
| `migrate_bonding_curve_creator` | 0x26118 | 0 | 4 | - |
| `migrate_v2` | 0x25749 | 0 | 16 | - |
| `multi_hop_curve_swap` | 0x252b8 | 0 | 8 | - |
| `remove_quote_control_mint` | 0x26667 | 0 | 4 | - |
| `remove_quote_mint` | 0x24826 | 0 | 2 | - |
| `sell` | 0x25656 | 0 | 10 | - |
| `sell_v2` | 0x25034 | 0 | 15 | - |
| `sell_v3` | 0x25231 | 0 | 9 | - |
| `set_creator` | 0x25a82 | 0 | 5 | - |
| `set_max_curve_depth` | 0x24566 | 0 | 2 | - |
| `set_mayhem_virtual_params` | 0x24ab5 | 0 | 6 | - |
| `set_metaplex_creator` | 0x259f2 | 0 | 4 | - |
| `set_params` | 0x2494e | 0 | 3 | - |
| `set_quote_control_admin` | 0x264e3 | 0 | 4 | - |
| `set_quote_control_mint_reserves` | 0x267e9 | 0 | 4 | - |
| `set_quote_control_reserves_admin` | 0x26728 | 0 | 4 | - |
| `set_reserved_fee_recipients` | 0x24b5d | 0 | 3 | - |
| `set_virtual_quote_reserves` | 0x248d8 | 0 | 2 | - |
| `sweep_creator_fee` | 0x25409 | 0 | 9 | - |
| `sweep_protocol_fee` | 0x25376 | 0 | 9 | - |
| `sync_user_volume_accumulator` | 0x25ff1 | 0 | 4 | - |
| `toggle_cashback_enabled` | 0x243d8 | 0 | 2 | - |
| `toggle_create_v2` | 0x2430e | 0 | 2 | - |
| `toggle_mayhem_mode` | 0x245dc | 0 | 2 | - |
| `update_creator_fee_config` | 0x246a6 | 0 | 3 | - |
| `update_global_authority` | 0x24261 | 0 | 3 | - |
| `update_holder_reward_config` | 0x244a2 | 0 | 2 | - |

## pump_amm

### Derivation call sites and seed vectors

`{32B}` = a seed byte string whose address is a frame slot (a pubkey or an
account field); the length is measured, not assumed. `-` in the program-id column
means no 32-byte constant argument was recovered at that site.

| # | syscall | via | insn | byte | fn | seeds | program id | handlers reaching |
|---:|---|---|---:|---:|---:|---|---|---:|
| 1 | `sol_invoke_signed_rust` | wrapper-call | 0x20dbd | 0x106de8 | 0x20d57 | *(not recovered)* | - | 34 |
| 2 | `sol_try_find_program_address` | wrapper-call | 0x2730 | 0x13980 | 0x268b | `pool-authority`(14) + <?>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 3 |
| 3 | `sol_try_find_program_address` | wrapper-call | 0x2837 | 0x141b8 | 0x2811 | `pool-authority`(14) + <?>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 4 |
| 4 | `sol_try_find_program_address` | wrapper-call | 0x2939 | 0x149c8 | 0x2924 | `pool-authority`(14) + <?>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 5 | `sol_try_find_program_address` | wrapper-call | 0x29a2 | 0x14d10 | 0x2924 | `holder-rewards`(14) + <?>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 6 | `sol_try_find_program_address` | wrapper-call | 0x3e0f | 0x1f078 | 0x3df2 | `pool-authority`(14) + <?>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 7 | `sol_try_find_program_address` | wrapper-call | 0x4a15 | 0x250a8 | 0x49fb | `pool-authority`(14) + <frame -0x208>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 8 | `sol_try_find_program_address` | wrapper-call | 0x4a90 | 0x25480 | 0x49fb | `pool-authority`(14) + <frame -0x208>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 9 | `sol_try_find_program_address` | wrapper-call | 0x572a | 0x2b950 | 0x571c | `pool-authority`(14) + <?>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 10 | `sol_try_find_program_address` | wrapper-call | 0x5742 | 0x2ba10 | 0x5734 | `bonding-curve`(13) + <?>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 2 |
| 11 | `sol_try_find_program_address` | wrapper-call | 0x5776 | 0x2bbb0 | 0x574c | `pool-authority`(14) + <frame -0x68>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 12 | `sol_try_find_program_address` | wrapper-call | 0x81a2 | 0x40d10 | 0x8141 | `pool-authority`(14) + <?>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 13 | `sol_try_find_program_address` | wrapper-call | 0x9973 | 0x4cb98 | 0x98ea | `user_volume_accumulator`(23) + <frame -0x3d0>(32) | r4=pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA(pump_amm) | 1 |
| 14 | `sol_try_find_program_address` | wrapper-call | 0x9d86 | 0x4ec30 | 0x9d52 | `pool-v2`(7) + <?>(32) | r4=pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA(pump_amm) | 3 |
| 15 | `sol_try_find_program_address` | wrapper-call | 0xb2b7 | 0x595b8 | 0xb281 | `creator_vault`(13) + <?>(32) | r4=pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA(pump_amm) | 2 |
| 16 | `sol_try_find_program_address` | wrapper-call | 0xf99a | 0x7ccd0 | 0xf89a | `pool-authority`(14) + <frame -0x178>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 17 | `sol_try_find_program_address` | wrapper-call | 0xf9bf | 0x7cdf8 | 0xf89a | *(not recovered)* | - | 1 |
| 18 | `sol_try_find_program_address` | wrapper-call | 0xfd0c | 0x7e860 | 0xfaf0 | *(not recovered)* | - | 1 |
| 19 | `sol_try_find_program_address` | wrapper-call | 0xfd9d | 0x7ece8 | 0xfaf0 | *(not recovered)* | - | 1 |
| 20 | `sol_try_find_program_address` | wrapper-call | 0xfdec | 0x7ef60 | 0xfaf0 | *(not recovered)* | - | 1 |
| 21 | `sol_try_find_program_address` | wrapper-call | 0x102cc | 0x81660 | 0x101f7 | *(not recovered)* | - | 1 |
| 22 | `sol_try_find_program_address` | wrapper-call | 0x10401 | 0x82008 | 0x101f7 | *(not recovered)* | - | 1 |
| 23 | `sol_try_find_program_address` | wrapper-call | 0x10941 | 0x84a08 | 0x10804 | *(not recovered)* | - | 5 |
| 24 | `sol_try_find_program_address` | wrapper-call | 0x10b49 | 0x85a48 | 0x109ab | *(not recovered)* | - | 1 |
| 25 | `sol_try_find_program_address` | wrapper-call | 0x10c51 | 0x86288 | 0x10bc5 | *(not recovered)* | - | 1 |
| 26 | `sol_try_find_program_address` | wrapper-call | 0x10d20 | 0x86900 | 0x10bc5 | *(not recovered)* | - | 1 |
| 27 | `sol_try_find_program_address` | wrapper-call | 0x10fe1 | 0x87f08 | 0x10e52 | *(not recovered)* | - | 1 |
| 28 | `sol_try_find_program_address` | wrapper-call | 0x11133 | 0x88998 | 0x1105c | *(not recovered)* | - | 1 |
| 29 | `sol_try_find_program_address` | wrapper-call | 0x11641 | 0x8b208 | 0x11286 | *(not recovered)* | - | 1 |
| 30 | `sol_try_find_program_address` | wrapper-call | 0x116a9 | 0x8b548 | 0x11286 | `boost_vault`(11) + <frame -0x448>(32) | - | 1 |
| 31 | `sol_try_find_program_address` | wrapper-call | 0x116ce | 0x8b670 | 0x11286 | *(not recovered)* | - | 1 |
| 32 | `sol_try_find_program_address` | wrapper-call | 0x11dd7 | 0x8eeb8 | 0x11afa | *(not recovered)* | - | 1 |
| 33 | `sol_try_find_program_address` | wrapper-call | 0x11e71 | 0x8f388 | 0x11afa | `boost_vault`(11) + <frame -0x3d8>(32) | - | 1 |
| 34 | `sol_try_find_program_address` | wrapper-call | 0x11f80 | 0x8fc00 | 0x11afa | *(not recovered)* | - | 1 |
| 35 | `sol_try_find_program_address` | wrapper-call | 0x122bd | 0x915e8 | 0x1211d | `creator_vault`(13) + <frame -0x20>(32) | - | 1 |
| 36 | `sol_try_find_program_address` | wrapper-call | 0x12452 | 0x92290 | 0x1211d | *(not recovered)* | - | 1 |
| 37 | `sol_try_find_program_address` | wrapper-call | 0x12641 | 0x93208 | 0x12581 | `pool`(4) + <frame -0x20>(2) + <frame -0x328>(32) + <frame -0x308>(32) + <frame -0x2e8>(32) | - | 1 |
| 38 | `sol_try_find_program_address` | wrapper-call | 0x1272e | 0x93970 | 0x12581 | `sharing-config`(14) + <?>(32) | r4=pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ(pump_fees) | 1 |
| 39 | `sol_try_find_program_address` | wrapper-call | 0x127b1 | 0x93d88 | 0x12581 | *(not recovered)* | - | 1 |
| 40 | `sol_try_find_program_address` | wrapper-call | 0x12918 | 0x948c0 | 0x12824 | `metadata`(8) + key:metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s + <frame -0x3b0>(32) | r4=metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s(metaplex) | 1 |
| 41 | `sol_try_find_program_address` | wrapper-call | 0x129ba | 0x94dd0 | 0x12824 | `bonding-curve`(13) + <frame -0x3b0>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 42 | `sol_try_find_program_address` | wrapper-call | 0x12a2a | 0x95150 | 0x12824 | *(not recovered)* | - | 1 |
| 43 | `sol_try_find_program_address` | wrapper-call | 0x12ca7 | 0x96538 | 0x12ac9 | `creator_vault`(13) + <frame -0x20>(32) | - | 1 |
| 44 | `sol_try_find_program_address` | wrapper-call | 0x12e06 | 0x97030 | 0x12ac9 | `creator-vault`(13) + <frame -0x40>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 45 | `sol_try_find_program_address` | wrapper-call | 0x12e62 | 0x97310 | 0x12ac9 | *(not recovered)* | - | 1 |
| 46 | `sol_try_find_program_address` | wrapper-call | 0x13143 | 0x98a18 | 0x12f7f | `creator_vault`(13) + <frame -0xa8>(32) | - | 1 |
| 47 | `sol_try_find_program_address` | wrapper-call | 0x132c6 | 0x99630 | 0x12f7f | `creator-vault`(13) + <frame -0x20>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 48 | `sol_try_find_program_address` | wrapper-call | 0x13353 | 0x99a98 | 0x12f7f | <frame -0x80>(32) + <frame -0x60>(32) + <frame -0x40>(32) | r1=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 49 | `sol_try_find_program_address` | wrapper-call | 0x133b0 | 0x99d80 | 0x12f7f | *(not recovered)* | - | 1 |
| 50 | `sol_try_find_program_address` | wrapper-call | 0x136f4 | 0x9b7a0 | 0x134d5 | `pool`(4) + <frame -0x430>(2) + <frame -0x4f8>(32) + <frame -0x4a8>(32) + <frame -0x480>(32) | - | 1 |
| 51 | `sol_try_find_program_address` | wrapper-call | 0x137c8 | 0x9be40 | 0x134d5 | `pool_lp_mint`(12) + <frame -0x3e8>(32) | - | 1 |
| 52 | `sol_try_find_program_address` | wrapper-call | 0x13bee | 0x9df70 | 0x134d5 | *(not recovered)* | - | 1 |
| 53 | `sol_try_find_program_address` | wrapper-call | 0x14eee | 0xa7770 | 0x14d8d | *(not recovered)* | - | 1 |
| 54 | `sol_try_find_program_address` | wrapper-call | 0x15459 | 0xaa2c8 | 0x1508c | *(not recovered)* | - | 2 |
| 55 | `sol_try_find_program_address` | wrapper-call | 0x159b9 | 0xacdc8 | 0x155fb | `user_volume_accumulator`(23) + <frame -0x488>(32) | - | 2 |
| 56 | `sol_try_find_program_address` | wrapper-call | 0x15cd5 | 0xae6a8 | 0x155fb | *(not recovered)* | - | 2 |
| 57 | `sol_try_find_program_address` | wrapper-call | 0x15d01 | 0xae808 | 0x155fb | `creator_vault`(13) + <?>(32) | - | 2 |
| 58 | `sol_try_find_program_address` | wrapper-call | 0x15d73 | 0xaeb98 | 0x155fb | *(not recovered)* | - | 2 |
| 59 | `sol_try_find_program_address` | wrapper-call | 0x15dd5 | 0xaeea8 | 0x155fb | `fee_config`(10) + key:pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA | - | 2 |
| 60 | `sol_try_find_program_address` | wrapper-call | 0x168bd | 0xb45e8 | 0x166cd | `user_volume_accumulator`(23) + <frame -0x470>(32) | - | 1 |
| 61 | `sol_try_find_program_address` | wrapper-call | 0x169ff | 0xb4ff8 | 0x166cd | *(not recovered)* | - | 1 |
| 62 | `sol_try_find_program_address` | wrapper-call | 0x16acf | 0xb5678 | 0x166cd | *(not recovered)* | - | 1 |
| 63 | `sol_try_find_program_address` | wrapper-call | 0x17702 | 0xbb810 | 0x174e4 | `user_volume_accumulator`(23) + <frame -0x450>(32) | - | 3 |
| 64 | `sol_try_find_program_address` | wrapper-call | 0x179f2 | 0xbcf90 | 0x174e4 | *(not recovered)* | - | 3 |
| 65 | `sol_try_find_program_address` | wrapper-call | 0x184e9 | 0xc2748 | 0x17f52 | *(not recovered)* | - | 1 |
| 66 | `sol_try_find_program_address` | wrapper-call | 0x18515 | 0xc28a8 | 0x17f52 | `creator_vault`(13) + <?>(32) | - | 1 |
| 67 | `sol_try_find_program_address` | wrapper-call | 0x1859a | 0xc2cd0 | 0x17f52 | `fee_config`(10) + key:pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA | - | 1 |
| 68 | `sol_try_find_program_address` | wrapper-call | 0x18f35 | 0xc79a8 | 0x18ca6 | <frame -0x438>(32) + <frame -0x418>(32) + <frame -0x3f8>(32) | r4=ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL(ata) | 2 |
| 69 | `sol_try_find_program_address` | wrapper-call | 0x18f5d | 0xc7ae8 | 0x18ca6 | *(not recovered)* | - | 2 |
| 70 | `sol_try_find_program_address` | wrapper-call | 0x192d2 | 0xc9690 | 0x190b1 | *(not recovered)* | - | 1 |
| 71 | `sol_try_find_program_address` | wrapper-call | 0x19473 | 0xca398 | 0x190b1 | `user_volume_accumulator`(23) + <frame -0x178>(32) | - | 1 |
| 72 | `sol_try_find_program_address` | wrapper-call | 0x194d0 | 0xca680 | 0x190b1 | *(not recovered)* | - | 1 |
| 73 | `sol_try_find_program_address` | wrapper-call | 0x19a23 | 0xcd118 | 0x198cb | `user_volume_accumulator`(23) + <frame -0x20>(32) | - | 1 |
| 74 | `sol_try_find_program_address` | wrapper-call | 0x19bcb | 0xcde58 | 0x198cb | *(not recovered)* | - | 1 |
| 75 | `sol_try_find_program_address` | wrapper-call | 0x19da1 | 0xced08 | 0x19cff | `user_volume_accumulator`(23) + <frame -0x20>(32) | - | 1 |
| 76 | `sol_try_find_program_address` | wrapper-call | 0x19e65 | 0xcf328 | 0x19cff | *(not recovered)* | - | 1 |
| 77 | `sol_try_find_program_address` | wrapper-call | 0x1a07a | 0xd03d0 | 0x19f53 | `user_volume_accumulator`(23) + <frame -0x90>(32) | - | 1 |
| 78 | `sol_try_find_program_address` | wrapper-call | 0x1a1cd | 0xd0e68 | 0x19f53 | *(not recovered)* | - | 1 |
| 79 | `sol_try_find_program_address` | wrapper-call | 0x1a6f4 | 0xd37a0 | 0x1a624 | *(not recovered)* | - | 1 |
| 80 | `sol_try_find_program_address` | wrapper-call | 0x1a789 | 0xd3c48 | 0x1a624 | `user_volume_accumulator`(23) + <frame -0x20>(32) | - | 1 |
| 81 | `sol_try_find_program_address` | wrapper-call | 0x1a7fa | 0xd3fd0 | 0x1a624 | *(not recovered)* | - | 1 |
| 82 | `sol_try_find_program_address` | wrapper-call | 0x1bd5d | 0xdeae8 | 0x1bd46 | *(not recovered)* | - | 0 |
| 83 | `sol_try_find_program_address` | wrapper-call | 0x1dba5 | 0xedd28 | 0x1db99 | *(not recovered)* | - | 0 |
| 84 | `sol_try_find_program_address` | wrapper-call | 0x1e2f3 | 0xf1798 | 0x1e1f6 | *(not recovered)* | - | 0 |
| 85 | `sol_try_find_program_address` | wrapper-call | 0x20163 | 0x100b18 | 0x2012b | <frame -0x60>(32) + <frame -0x40>(32) + <frame -0x20>(32) | r4=ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL(ata) | 16 |
| 86 | `sol_try_find_program_address` | wrapper-call | 0x201aa | 0x100d50 | 0x2016d | <frame -0x60>(32) + <frame -0x40>(32) + <frame -0x20>(32) | r4=ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL(ata) | 11 |
| 87 | `sol_create_program_address` | wrapper-call | 0x16a41 | 0xb5208 | 0x166cd | `fee_config`(10) + key:pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA + <frame -0x3d9>(1) | r4=pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ(pump_fees) | 1 |
| 88 | `sol_create_program_address` | wrapper-call | 0x1798d | 0xbcc68 | 0x174e4 | `fee_config`(10) + key:pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA + <frame -0x3d9>(1) | r4=pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ(pump_fees) | 3 |

### Handler -> derivations reachable (forward call closure)

`body` = the derivation is inside the handler function itself; `closure` = it is
inside a helper the handler can reach. Signatures keep the literal parts and
collapse the dynamic ones to their length.

| handler | entry | body | closure | seed signatures (body) |
|---|---|---:|---:|---|
| `admin_cto_pool` | 0x1d5fe | 0 | 5 | - |
| `admin_update_token_incentives` | 0x1cb9d | 0 | 6 | - |
| `boost_buy_and_burn` | 0x1c8e7 | 0 | 6 | - |
| `buy` | 0x1cec9 | 0 | 10 | - |
| `buy_exact_quote_in` | 0x1cfb1 | 0 | 10 | - |
| `buy_exact_quote_in_v2` | 0x1d1e2 | 0 | 6 | - |
| `buy_v2` | 0x1d15d | 0 | 6 | - |
| `claim_cashback` | 0x1da42 | 0 | 4 | - |
| `claim_token_incentives` | 0x1cc57 | 0 | 6 | - |
| `close_user_volume_accumulator` | 0x1cd93 | 0 | 3 | - |
| `collect_coin_creator_fee` | 0x1d51d | 0 | 4 | - |
| `create_config` | 0x1c17f | 0 | 3 | - |
| `create_pool` | 0x1c634 | 0 | 7 | - |
| `deposit` | 0x1ca4f | 0 | 2 | - |
| `disable` | 0x1c2a1 | 0 | 2 | - |
| `extend_account` | 0x1d47e | 0 | 2 | - |
| `init_boost` | 0x1c7b3 | 0 | 8 | - |
| `init_user_volume_accumulator` | 0x1cce2 | 0 | 3 | - |
| `migrate_pool_coin_creator` | 0x1d8e7 | 0 | 5 | - |
| `multi_hop_swap` | 0x1d2ec | 0 | 8 | - |
| `sell` | 0x1d099 | 0 | 9 | - |
| `sell_v2` | 0x1d267 | 0 | 6 | - |
| `set_boost_authority` | 0x1c839 | 0 | 2 | - |
| `set_coin_creator` | 0x1d56e | 0 | 6 | - |
| `set_reserved_fee_recipients` | 0x1c98d | 0 | 3 | - |
| `sweep_creator_fee` | 0x1d3f8 | 0 | 5 | - |
| `sweep_protocol_fee` | 0x1d372 | 0 | 5 | - |
| `sync_user_volume_accumulator` | 0x1ce17 | 0 | 4 | - |
| `toggle_boost` | 0x1d7cc | 0 | 0 | - |
| `toggle_cashback_enabled` | 0x1d977 | 0 | 1 | - |
| `toggle_mayhem_mode` | 0x1d701 | 0 | 1 | - |
| `transfer_creator_fees_to_pump` | 0x1d846 | 0 | 6 | - |
| `transfer_creator_fees_to_pump_v2` | 0x1d898 | 0 | 7 | - |
| `update_admin` | 0x1c398 | 0 | 2 | - |
| `update_buyback_config` | 0x1dacc | 0 | 1 | - |
| `update_creator_fee_config` | 0x1c565 | 0 | 2 | - |
| `update_fee_config` | 0x1c446 | 0 | 2 | - |
| `withdraw` | 0x1caf6 | 0 | 2 | - |

## pump_fees

### Derivation call sites and seed vectors

`{32B}` = a seed byte string whose address is a frame slot (a pubkey or an
account field); the length is measured, not assumed. `-` in the program-id column
means no 32-byte constant argument was recovered at that site.

| # | syscall | via | insn | byte | fn | seeds | program id | handlers reaching |
|---:|---|---|---:|---:|---:|---|---|---:|
| 1 | `sol_invoke_signed_rust` | wrapper-call | 0x16214 | 0xb10a0 | 0x161ae | *(not recovered)* | - | 25 |
| 2 | `sol_try_find_program_address` | wrapper-call | 0x551c | 0x2a8e0 | 0x500a | `pool-authority`(14) + <frame -0x40>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 3 | `sol_try_find_program_address` | wrapper-call | 0x57b0 | 0x2bd80 | 0x56c7 | `pool-authority`(14) + <frame -0x328>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 4 | `sol_try_find_program_address` | wrapper-call | 0x712d | 0x38968 | 0x7113 | `pool-authority`(14) + <?>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 2 |
| 5 | `sol_try_find_program_address` | wrapper-call | 0x714e | 0x38a70 | 0x7113 | `pool`(4) + <frame -0x60>(2) + <frame -0x158>(32) + <?>(32) + <?>(32) | r4=pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA(pump_amm) | 2 |
| 6 | `sol_try_find_program_address` | wrapper-call | 0x8f58 | 0x47ac0 | 0x8e83 | *(not recovered)* | - | 1 |
| 7 | `sol_try_find_program_address` | wrapper-call | 0x916c | 0x48b60 | 0x906f | `fee_config`(10) + <frame -0x140>(32) | - | 1 |
| 8 | `sol_try_find_program_address` | wrapper-call | 0x92d0 | 0x49680 | 0x906f | *(not recovered)* | - | 1 |
| 9 | `sol_try_find_program_address` | wrapper-call | 0x9784 | 0x4bc20 | 0x9690 | *(not recovered)* | - | 1 |
| 10 | `sol_try_find_program_address` | wrapper-call | 0x98ae | 0x4c570 | 0x9690 | *(not recovered)* | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 11 | `sol_try_find_program_address` | wrapper-call | 0x995d | 0x4cae8 | 0x9690 | *(not recovered)* | - | 1 |
| 12 | `sol_try_find_program_address` | wrapper-call | 0x9eb7 | 0x4f5b8 | 0x9cc5 | *(not recovered)* | - | 1 |
| 13 | `sol_try_find_program_address` | wrapper-call | 0xa176 | 0x50bb0 | 0x9f50 | *(not recovered)* | - | 1 |
| 14 | `sol_try_find_program_address` | wrapper-call | 0xa417 | 0x520b8 | 0xa214 | `buyback-vault`(13) + <frame -0x58>(1) | - | 2 |
| 15 | `sol_try_find_program_address` | wrapper-call | 0xa467 | 0x52338 | 0xa214 | *(not recovered)* | - | 2 |
| 16 | `sol_try_find_program_address` | wrapper-call | 0xa78b | 0x53c58 | 0xa5d2 | *(not recovered)* | - | 4 |
| 17 | `sol_try_find_program_address` | wrapper-call | 0xaac8 | 0x55640 | 0xa8fc | *(not recovered)* | - | 4 |
| 18 | `sol_try_find_program_address` | wrapper-call | 0xac89 | 0x56448 | 0xab73 | `buyback-vault`(13) + <frame -0x18>(1) | - | 1 |
| 19 | `sol_try_find_program_address` | wrapper-call | 0xae56 | 0x572b0 | 0xab73 | *(not recovered)* | - | 1 |
| 20 | `sol_try_find_program_address` | wrapper-call | 0xb689 | 0x5b448 | 0xb4fa | `buyback-vault`(13) + <frame -0x118>(1) | - | 1 |
| 21 | `sol_try_find_program_address` | wrapper-call | 0xb8e1 | 0x5c708 | 0xb4fa | *(not recovered)* | - | 1 |
| 22 | `sol_try_find_program_address` | wrapper-call | 0xbb27 | 0x5d938 | 0xba35 | `pool-authority`(14) + <frame -0x308>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 23 | `sol_try_find_program_address` | wrapper-call | 0xbb90 | 0x5dc80 | 0xba35 | *(not recovered)* | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 24 | `sol_try_find_program_address` | wrapper-call | 0xbcce | 0x5e670 | 0xba35 | *(not recovered)* | - | 1 |
| 25 | `sol_try_find_program_address` | wrapper-call | 0xc0a1 | 0x60508 | 0xbe2e | *(not recovered)* | - | 1 |
| 26 | `sol_try_find_program_address` | wrapper-call | 0xc3af | 0x61d78 | 0xc131 | <frame -0x80>(32) + <frame -0x60>(32) + <frame -0x40>(32) | - | 1 |
| 27 | `sol_try_find_program_address` | wrapper-call | 0xc409 | 0x62048 | 0xc131 | <frame -0x80>(32) + <frame -0x60>(32) + <frame -0x40>(32) | - | 1 |
| 28 | `sol_try_find_program_address` | wrapper-call | 0xc568 | 0x62b40 | 0xc131 | *(not recovered)* | - | 1 |
| 29 | `sol_try_find_program_address` | wrapper-call | 0xc9d7 | 0x64eb8 | 0xc788 | *(not recovered)* | - | 1 |
| 30 | `sol_try_find_program_address` | wrapper-call | 0xd151 | 0x68a88 | 0xcfe6 | `donation-fee-pda`(16) + <frame -0x40>(32) + <frame -0x20>(32) | - | 1 |
| 31 | `sol_try_find_program_address` | wrapper-call | 0xd221 | 0x69108 | 0xcfe6 | *(not recovered)* | - | 1 |
| 32 | `sol_try_find_program_address` | wrapper-call | 0xd355 | 0x69aa8 | 0xcfe6 | `bonding-curve`(13) + <frame -0x20>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 33 | `sol_try_find_program_address` | wrapper-call | 0xd3b2 | 0x69d90 | 0xcfe6 | `sharing-config`(14) + <frame -0x1a8>(32) | - | 1 |
| 34 | `sol_try_find_program_address` | wrapper-call | 0xdb2f | 0x6d978 | 0xd95d | `sharing-config`(14) + <frame -0x120>(32) | - | 1 |
| 35 | `sol_try_find_program_address` | wrapper-call | 0xdc08 | 0x6e040 | 0xd95d | *(not recovered)* | - | 1 |
| 36 | `sol_try_find_program_address` | wrapper-call | 0xdc3c | 0x6e1e0 | 0xd95d | *(not recovered)* | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 37 | `sol_try_find_program_address` | wrapper-call | 0xdd2c | 0x6e960 | 0xd95d | `bonding-curve`(13) + <frame -0x20>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 38 | `sol_try_find_program_address` | wrapper-call | 0xdd87 | 0x6ec38 | 0xd95d | *(not recovered)* | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 39 | `sol_try_find_program_address` | wrapper-call | 0xddf4 | 0x6efa0 | 0xd95d | *(not recovered)* | r4=pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA(pump_amm) | 1 |
| 40 | `sol_try_find_program_address` | wrapper-call | 0xe606 | 0x73030 | 0xe4d2 | `social-fee-pda`(14) | - | 1 |
| 41 | `sol_try_find_program_address` | wrapper-call | 0xe7bc | 0x73de0 | 0xe4d2 | *(not recovered)* | - | 1 |
| 42 | `sol_try_find_program_address` | wrapper-call | 0xef48 | 0x77a40 | 0xecba | *(not recovered)* | - | 1 |
| 43 | `sol_try_find_program_address` | wrapper-call | 0xefa0 | 0x77d00 | 0xecba | *(not recovered)* | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 44 | `sol_try_find_program_address` | wrapper-call | 0xf0fa | 0x787d0 | 0xecba | `bonding-curve`(13) + <frame -0x20>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 45 | `sol_try_find_program_address` | wrapper-call | 0xf162 | 0x78b10 | 0xecba | `creator-vault`(13) + <frame -0x20>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 46 | `sol_try_find_program_address` | wrapper-call | 0xf1bc | 0x78de0 | 0xecba | *(not recovered)* | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 47 | `sol_try_find_program_address` | wrapper-call | 0xf223 | 0x79118 | 0xecba | *(not recovered)* | r4=pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA(pump_amm) | 1 |
| 48 | `sol_try_find_program_address` | wrapper-call | 0xf307 | 0x79838 | 0xecba | `creator_vault`(13) + <frame -0x20>(32) | r4=pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA(pump_amm) | 1 |
| 49 | `sol_try_find_program_address` | wrapper-call | 0xf7bd | 0x7bde8 | 0xf52a | *(not recovered)* | - | 1 |
| 50 | `sol_try_find_program_address` | wrapper-call | 0xf83e | 0x7c1f0 | 0xf52a | *(not recovered)* | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 51 | `sol_try_find_program_address` | wrapper-call | 0xf985 | 0x7cc28 | 0xf52a | `bonding-curve`(13) + <frame -0x308>(32) | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 52 | `sol_try_find_program_address` | wrapper-call | 0xf9f0 | 0x7cf80 | 0xf52a | `creator-vault`(13) + <frame -0x308>(32) | - | 1 |
| 53 | `sol_try_find_program_address` | wrapper-call | 0xfa79 | 0x7d3c8 | 0xf52a | <frame -0x368>(32) + <frame -0x348>(32) + <frame -0x328>(32) | - | 1 |
| 54 | `sol_try_find_program_address` | wrapper-call | 0xfae2 | 0x7d710 | 0xf52a | *(not recovered)* | r4=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 55 | `sol_try_find_program_address` | wrapper-call | 0xfb49 | 0x7da48 | 0xf52a | *(not recovered)* | r4=pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA(pump_amm) | 1 |
| 56 | `sol_try_find_program_address` | wrapper-call | 0xfbcc | 0x7de60 | 0xf52a | `creator_vault`(13) + <frame -0x308>(32) | r4=pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA(pump_amm) | 1 |
| 57 | `sol_try_find_program_address` | wrapper-call | 0xfc47 | 0x7e238 | 0xf52a | <frame -0x368>(32) + <frame -0x348>(32) + <frame -0x328>(32) | r1=pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA(pump_amm) | 1 |
| 58 | `sol_try_find_program_address` | wrapper-call | 0xfff4 | 0x7ffa0 | 0xfe47 | `referral-vault`(14) + <frame -0x1d8>(32) | - | 1 |
| 59 | `sol_try_find_program_address` | wrapper-call | 0x100fd | 0x807e8 | 0xfe47 | *(not recovered)* | - | 1 |
| 60 | `sol_try_find_program_address` | wrapper-call | 0x12950 | 0x94a80 | 0x12939 | *(not recovered)* | - | 0 |
| 61 | `sol_try_find_program_address` | wrapper-call | 0x141b7 | 0xa0db8 | 0x141ab | *(not recovered)* | - | 0 |
| 62 | `sol_try_find_program_address` | wrapper-call | 0x14987 | 0xa4c38 | 0x1488a | *(not recovered)* | - | 0 |
| 63 | `sol_try_find_program_address` | wrapper-call | 0x1555f | 0xaaaf8 | 0x15527 | <frame -0x60>(32) + <frame -0x40>(32) + <frame -0x20>(32) | r4=ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL(ata) | 5 |
| 64 | `sol_try_find_program_address` | wrapper-call | 0x155a6 | 0xaad30 | 0x15569 | <frame -0x60>(32) + <frame -0x40>(32) + <frame -0x20>(32) | r4=ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL(ata) | 3 |
| 65 | `sol_create_program_address` | wrapper-call | 0x2609 | 0x13048 | 0x254c | `fee_config`(10) + <frame -0x250>(32) + <frame -0x229>(1) | - | 1 |
| 66 | `sol_create_program_address` | wrapper-call | 0x55d0 | 0x2ae80 | 0x500a | `pool`(4) + <frame -0x84>(2) + <frame -0x300>(32) + <?>(32) + <frame -0x2c0>(32) + <frame -0x81>(1) | r4=pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA(pump_amm) | 1 |
| 67 | `sol_create_program_address` | wrapper-call | 0x5817 | 0x2c0b8 | 0x56c7 | `pool`(4) + <frame -0x4>(2) + <?>(32) + <?>(32) + <?>(32) + <frame -0x1>(1) | r4=pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA(pump_amm) | 1 |
| 68 | `sol_create_program_address` | wrapper-call | 0x9da8 | 0x4ed40 | 0x9cc5 | `fee_config`(10) + <frame -0x20>(32) + <frame -0x21>(1) | - | 1 |
| 69 | `sol_create_program_address` | wrapper-call | 0xa064 | 0x50320 | 0x9f50 | `fee_config`(10) + <frame -0x20>(32) + <frame -0x21>(1) | - | 1 |
| 70 | `sol_create_program_address` | wrapper-call | 0xa2f9 | 0x517c8 | 0xa214 | `fee-program-global`(18) + <frame -0x41>(1) | - | 2 |
| 71 | `sol_create_program_address` | wrapper-call | 0xa66d | 0x53368 | 0xa5d2 | `fee-program-global`(18) + <frame -0x41>(1) | - | 4 |
| 72 | `sol_create_program_address` | wrapper-call | 0xa9da | 0x54ed0 | 0xa8fc | `fee_config`(10) + <frame -0x20>(32) + <frame -0x21>(1) | - | 4 |
| 73 | `sol_create_program_address` | wrapper-call | 0xbc17 | 0x5e0b8 | 0xba35 | `sharing-config`(14) + <frame -0x308>(32) + <frame -0x309>(1) | r1=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 74 | `sol_create_program_address` | wrapper-call | 0xbf54 | 0x5faa0 | 0xbe2e | `social-fee-pda`(14) | - | 1 |
| 75 | `sol_create_program_address` | wrapper-call | 0xbff3 | 0x5ff98 | 0xbe2e | `fee-program-global`(18) + <frame -0x21>(1) | - | 1 |
| 76 | `sol_create_program_address` | wrapper-call | 0xc2da | 0x616d0 | 0xc131 | `social-fee-pda`(14) | - | 1 |
| 77 | `sol_create_program_address` | wrapper-call | 0xc4ba | 0x625d0 | 0xc131 | `fee-program-global`(18) + <frame -0x80>(1) | - | 1 |
| 78 | `sol_create_program_address` | wrapper-call | 0xcac8 | 0x65640 | 0xc788 | `fee-program-global`(18) + <frame -0x38>(1) | - | 1 |
| 79 | `sol_create_program_address` | wrapper-call | 0xcb38 | 0x659c0 | 0xc788 | `donation-fee-pda`(16) + <frame -0x228>(32) + <frame -0x248>(32) + <frame -0x21>(1) | - | 1 |
| 80 | `sol_create_program_address` | wrapper-call | 0xd252 | 0x69290 | 0xcfe6 | `fee-program-global`(18) + <frame -0x60>(1) | - | 1 |
| 81 | `sol_create_program_address` | wrapper-call | 0xe75e | 0x73af0 | 0xe4d2 | `fee-program-global`(18) + <frame -0x1>(1) | - | 1 |
| 82 | `sol_create_program_address` | wrapper-call | 0xf003 | 0x78018 | 0xecba | `sharing-config`(14) + <frame -0x20>(32) + <frame -0x80>(1) | r1=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 83 | `sol_create_program_address` | wrapper-call | 0xf8b5 | 0x7c5a8 | 0xf52a | `sharing-config`(14) + <frame -0x308>(32) + <frame -0x368>(1) | r1=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 84 | `sol_create_program_address` | wrapper-call | 0xfdc5 | 0x7ee28 | 0xfd68 | `fee_config`(10) + <frame -0x28>(32) + <frame -0x1>(1) | - | 2 |

### Handler -> derivations reachable (forward call closure)

`body` = the derivation is inside the handler function itself; `closure` = it is
inside a helper the handler can reach. Signatures keep the literal parts and
collapse the dynamic ones to their length.

| handler | entry | body | closure | seed signatures (body) |
|---|---|---:|---:|---|
| `admin_cto_sharing_config` | 0x139e4 | 0 | 5 | - |
| `claim_social_fee_pda` | 0x13b5d | 0 | 4 | - |
| `claim_social_fee_pda_v2` | 0x13c64 | 0 | 8 | - |
| `crank_donation_fee_pda` | 0x140b8 | 0 | 6 | - |
| `create_donation_fee_pda` | 0x14044 | 0 | 8 | - |
| `create_fee_sharing_config` | 0x13810 | 0 | 9 | - |
| `create_social_fee_pda` | 0x13a95 | 0 | 4 | - |
| `extend_fee_config` | 0x134a2 | 0 | 3 | - |
| `get_fees` | 0x136a0 | 0 | 1 | - |
| `get_fees_with_quote_mint` | 0x13763 | 0 | 1 | - |
| `initialize_buyback` | 0x13d6a | 0 | 5 | - |
| `initialize_fee_config` | 0x12d72 | 0 | 3 | - |
| `initialize_fee_program_global` | 0x12e01 | 0 | 4 | - |
| `revoke_fee_sharing_authority` | 0x138ba | 0 | 0 | - |
| `set_authority` | 0x130de | 0 | 3 | - |
| `set_claim_rate_limit` | 0x13034 | 0 | 3 | - |
| `set_disable_flags` | 0x12f8a | 0 | 3 | - |
| `set_exotic_flat_fees` | 0x13541 | 0 | 3 | - |
| `set_social_claim_authority` | 0x12eca | 0 | 3 | - |
| `sweep_buyback` | 0x13e01 | 0 | 4 | - |
| `transfer_fee_sharing_authority` | 0x138c7 | 0 | 0 | - |
| `update_admin` | 0x135f3 | 0 | 3 | - |
| `update_buyback_authority` | 0x13ea6 | 0 | 3 | - |
| `update_buyback_claim_rate_limit` | 0x13f80 | 0 | 3 | - |
| `update_fee_config` | 0x1319e | 0 | 3 | - |
| `update_fee_shares` | 0x138d4 | 0 | 12 | - |
| `update_fee_shares_v2` | 0x1395a | 0 | 13 | - |
| `update_stable_fee_config` | 0x13329 | 0 | 3 | - |
| `upsert_fee_tiers` | 0x13267 | 0 | 3 | - |
| `upsert_stable_fee_tiers` | 0x133e0 | 0 | 3 | - |
| `withdraw` | 0x14121 | 0 | 3 | - |

## mayhem

### Derivation call sites and seed vectors

`{32B}` = a seed byte string whose address is a frame slot (a pubkey or an
account field); the length is measured, not assumed. `-` in the program-id column
means no 32-byte constant argument was recovered at that site.

| # | syscall | via | insn | byte | fn | seeds | program id | handlers reaching |
|---:|---|---|---:|---:|---:|---|---|---:|
| 1 | `sol_try_find_program_address` | direct | 0x7384 | 0x39c20 | 0x70ce | `mayhem-state`(12) + <frame -0x190>(32) | - | 1 |
| 2 | `sol_try_find_program_address` | direct | 0x744a | 0x3a250 | 0x70ce | `bonding-curve`(13) + <frame -0x80>(32) | r3=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 3 | `sol_try_find_program_address` | direct | 0x7bd8 | 0x3dec0 | 0x7a64 | `fee-recipient`(13) + <frame -0x238>(1) | - | 1 |
| 4 | `sol_try_find_program_address` | direct | 0x9206 | 0x49030 | 0x8c6f | `mayhem-state`(12) + <frame -0x338>(32) | - | 1 |
| 5 | `sol_try_find_program_address` | direct | 0x93cb | 0x49e58 | 0x8c6f | `pool-v2`(7) + <frame -0x338>(32) | - | 1 |
| 6 | `sol_try_find_program_address` | direct | 0x9ef9 | 0x4f7c8 | 0x9993 | `mayhem-state`(12) + <frame -0x338>(32) | - | 1 |
| 7 | `sol_try_find_program_address` | direct | 0xa0b8 | 0x505c0 | 0x9993 | `pool-v2`(7) + <frame -0x338>(32) | - | 1 |
| 8 | `sol_try_find_program_address` | direct | 0xa8dd | 0x546e8 | 0xa4bf | `mayhem-state`(12) + <frame -0x298>(32) | - | 1 |
| 9 | `sol_try_find_program_address` | direct | 0xa99e | 0x54cf0 | 0xa4bf | `bonding-curve`(13) + <frame -0x128>(32) | r3=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 10 | `sol_try_find_program_address` | direct | 0xaa6f | 0x55378 | 0xa4bf | `bonding-curve-v2`(16) + <frame -0x298>(32) | - | 1 |
| 11 | `sol_try_find_program_address` | direct | 0xb1dd | 0x58ee8 | 0xade1 | `mayhem-state`(12) + <frame -0x298>(32) | - | 1 |
| 12 | `sol_try_find_program_address` | direct | 0xb2a6 | 0x59530 | 0xade1 | `bonding-curve`(13) + <frame -0x128>(32) | r3=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 13 | `sol_try_find_program_address` | direct | 0xb37a | 0x59bd0 | 0xade1 | `bonding-curve-v2`(16) + <frame -0x298>(32) | - | 1 |
| 14 | `sol_try_find_program_address` | direct | 0xbdb0 | 0x5ed80 | 0xb8db | `mayhem-state`(12) + <frame -0x2f8>(32) | - | 1 |
| 15 | `sol_try_find_program_address` | direct | 0xbed2 | 0x5f690 | 0xb8db | `bonding-curve`(13) + <frame -0x128>(32) | r3=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 16 | `sol_try_find_program_address` | direct | 0xc823 | 0x64118 | 0xc368 | `mayhem-state`(12) + <frame -0x2f8>(32) | - | 1 |
| 17 | `sol_try_find_program_address` | direct | 0xc951 | 0x64a88 | 0xc368 | `bonding-curve`(13) + <frame -0x128>(32) | r3=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P(pump) | 1 |
| 18 | `sol_try_find_program_address` | direct | 0xd4cb | 0x6a658 | 0xd25f | `mayhem-state`(12) + <frame -0xc8>(32) | - | 1 |
| 19 | `sol_try_find_program_address` | direct | 0x12bcb | 0x95e58 | 0x12b90 | <frame -0x98>(32) + <frame -0x78>(32) + <frame -0x58>(32) | r3=ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL(ata) | 12 |
| 20 | `sol_try_find_program_address` | direct | 0x12c22 | 0x96110 | 0x12be2 | <frame -0x98>(32) + <frame -0x78>(32) + <frame -0x58>(32) | r3=ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL(ata) | 5 |
| 21 | `sol_try_find_program_address` | wrapper-call | 0xfc0e | 0x7e070 | 0xfbfc | *(not recovered)* | - | 1 |
| 22 | `sol_try_find_program_address` | wrapper-call | 0xfd37 | 0x7e9b8 | 0xfd10 | *(not recovered)* | - | 1 |
| 23 | `sol_try_find_program_address` | wrapper-call | 0xfd77 | 0x7ebb8 | 0xfd50 | *(not recovered)* | - | 1 |
| 24 | `sol_try_find_program_address` | wrapper-call | 0xfe65 | 0x7f328 | 0xfe35 | *(not recovered)* | - | 1 |
| 25 | `sol_try_find_program_address` | wrapper-call | 0xfec3 | 0x7f618 | 0xfe93 | *(not recovered)* | - | 1 |
| 26 | `sol_try_find_program_address` | wrapper-call | 0xff03 | 0x7f818 | 0xfef1 | *(not recovered)* | - | 1 |
| 27 | `sol_try_find_program_address` | wrapper-call | 0xff3f | 0x7f9f8 | 0xff2d | *(not recovered)* | - | 1 |
| 28 | `sol_try_find_program_address` | wrapper-call | 0xff6b | 0x7fb58 | 0xff59 | *(not recovered)* | - | 1 |
| 29 | `sol_try_find_program_address` | wrapper-call | 0xff97 | 0x7fcb8 | 0xff85 | *(not recovered)* | - | 1 |
| 30 | `sol_try_find_program_address` | wrapper-call | 0xffc5 | 0x7fe28 | 0xffb3 | *(not recovered)* | - | 1 |
| 31 | `sol_try_find_program_address` | wrapper-call | 0x10174 | 0x80ba0 | 0x1004b | *(not recovered)* | - | 1 |
| 32 | `sol_try_find_program_address` | wrapper-call | 0xfdb8 | 0x7edc0 | 0xfd90 | *(not recovered)* | - | 1 |
| 33 | `sol_try_find_program_address` | wrapper-call | 0xfe0a | 0x7f050 | 0xfde2 | *(not recovered)* | - | 1 |
| 34 | `sol_try_find_program_address` | wrapper-call | 0xfff4 | 0x7ffa0 | 0xffe1 | *(not recovered)* | - | 1 |
| 35 | `sol_try_find_program_address` | wrapper-call | 0x1002f | 0x80178 | 0x1001c | *(not recovered)* | - | 1 |
| 36 | `sol_try_find_program_address` | wrapper-call | 0xfc5b | 0x7e2d8 | 0xfc41 | *(not recovered)* | - | 1 |
| 37 | `sol_try_find_program_address` | wrapper-call | 0xfca9 | 0x7e548 | 0xfc96 | *(not recovered)* | - | 1 |
| 38 | `sol_try_find_program_address` | wrapper-call | 0xfce6 | 0x7e730 | 0xfcd3 | *(not recovered)* | - | 1 |
| 39 | `sol_try_find_program_address` | wrapper-call | 0x1045e | 0x822f0 | 0x1041f | *(not recovered)* | - | 1 |
| 40 | `sol_try_find_program_address` | wrapper-call | 0x103f6 | 0x81fb0 | 0x103b7 | *(not recovered)* | - | 1 |
| 41 | `sol_try_find_program_address` | wrapper-call | 0x102be | 0x815f0 | 0x1027f | *(not recovered)* | - | 1 |
| 42 | `sol_try_find_program_address` | wrapper-call | 0x10256 | 0x812b0 | 0x10217 | *(not recovered)* | - | 1 |
| 43 | `sol_try_find_program_address` | wrapper-call | 0x1038e | 0x81c70 | 0x1034f | *(not recovered)* | - | 1 |
| 44 | `sol_try_find_program_address` | wrapper-call | 0x10326 | 0x81930 | 0x102e7 | *(not recovered)* | - | 1 |
| 45 | `sol_try_find_program_address` | wrapper-call | 0x101f1 | 0x80f88 | 0x101de | *(not recovered)* | - | 1 |
| 46 | `sol_try_find_program_address` | wrapper-call | 0x6cd3 | 0x36698 | 0x6992 | *(not recovered)* | - | 1 |
| 47 | `sol_try_find_program_address` | wrapper-call | 0x6eeb | 0x37758 | 0x6e26 | *(not recovered)* | - | 1 |
| 48 | `sol_try_find_program_address` | wrapper-call | 0x73e7 | 0x39f38 | 0x70ce | *(not recovered)* | - | 1 |
| 49 | `sol_try_find_program_address` | wrapper-call | 0x8164 | 0x40b20 | 0x809d | *(not recovered)* | - | 1 |
| 50 | `sol_try_find_program_address` | wrapper-call | 0x85af | 0x42d78 | 0x834e | *(not recovered)* | - | 1 |
| 51 | `sol_try_find_program_address` | wrapper-call | 0x8a35 | 0x451a8 | 0x87eb | *(not recovered)* | - | 1 |
| 52 | `sol_try_find_program_address` | wrapper-call | 0x926f | 0x49378 | 0x8c6f | *(not recovered)* | - | 1 |
| 53 | `sol_try_find_program_address` | wrapper-call | 0x930d | 0x49868 | 0x8c6f | *(not recovered)* | - | 1 |
| 54 | `sol_try_find_program_address` | wrapper-call | 0x9377 | 0x49bb8 | 0x8c6f | *(not recovered)* | - | 1 |
| 55 | `sol_try_find_program_address` | wrapper-call | 0x96c7 | 0x4b638 | 0x95d6 | *(not recovered)* | - | 2 |
| 56 | `sol_try_find_program_address` | wrapper-call | 0x9f62 | 0x4fb10 | 0x9993 | *(not recovered)* | - | 1 |
| 57 | `sol_try_find_program_address` | wrapper-call | 0xa000 | 0x50000 | 0x9993 | *(not recovered)* | - | 1 |
| 58 | `sol_try_find_program_address` | wrapper-call | 0xa06a | 0x50350 | 0x9993 | *(not recovered)* | - | 1 |
| 59 | `sol_try_find_program_address` | wrapper-call | 0xa942 | 0x54a10 | 0xa4bf | *(not recovered)* | - | 1 |
| 60 | `sol_try_find_program_address` | wrapper-call | 0xaa08 | 0x55040 | 0xa4bf | *(not recovered)* | - | 1 |
| 61 | `sol_try_find_program_address` | wrapper-call | 0xb267 | 0x59338 | 0xade1 | *(not recovered)* | - | 1 |
| 62 | `sol_try_find_program_address` | wrapper-call | 0xb313 | 0x59898 | 0xade1 | *(not recovered)* | - | 1 |
| 63 | `sol_try_find_program_address` | wrapper-call | 0xbe15 | 0x5f0a8 | 0xb8db | *(not recovered)* | - | 1 |
| 64 | `sol_try_find_program_address` | wrapper-call | 0xbe76 | 0x5f3b0 | 0xb8db | *(not recovered)* | - | 1 |
| 65 | `sol_try_find_program_address` | wrapper-call | 0xbf41 | 0x5fa08 | 0xb8db | *(not recovered)* | - | 1 |
| 66 | `sol_try_find_program_address` | wrapper-call | 0xc88c | 0x64460 | 0xc368 | *(not recovered)* | - | 1 |
| 67 | `sol_try_find_program_address` | wrapper-call | 0xc8f1 | 0x64788 | 0xc368 | *(not recovered)* | - | 1 |
| 68 | `sol_try_find_program_address` | wrapper-call | 0xc9c4 | 0x64e20 | 0xc368 | *(not recovered)* | - | 1 |
| 69 | `sol_try_find_program_address` | wrapper-call | 0xd770 | 0x6bb80 | 0xd6a9 | *(not recovered)* | - | 1 |
| 70 | `sol_try_find_program_address` | wrapper-call | 0x12c96 | 0x964b0 | 0x12c93 | *(not recovered)* | - | 5 |
| 71 | `sol_invoke_signed_rust` | wrapper-call | 0x1adf | 0xd6f8 | 0x1961 | *(not recovered)* | - | 1 |
| 72 | `sol_invoke_signed_rust` | wrapper-call | 0x1d7d | 0xebe8 | 0x1b13 | *(not recovered)* | - | 1 |
| 73 | `sol_invoke_signed_rust` | wrapper-call | 0x1fd6 | 0xfeb0 | 0x1de2 | *(not recovered)* | - | 1 |
| 74 | `sol_invoke_signed_rust` | wrapper-call | 0x256d | 0x12b68 | 0x21c9 | *(not recovered)* | - | 1 |
| 75 | `sol_invoke_signed_rust` | wrapper-call | 0x2955 | 0x14aa8 | 0x25b2 | *(not recovered)* | - | 1 |
| 76 | `sol_invoke_signed_rust` | wrapper-call | 0x2e68 | 0x17340 | 0x29cc | *(not recovered)* | - | 1 |
| 77 | `sol_invoke_signed_rust` | wrapper-call | 0x3710 | 0x1b880 | 0x2ecd | `sol-vault`(9) | - | 1 |
| 78 | `sol_invoke_signed_rust` | wrapper-call | 0x3dfb | 0x1efd8 | 0x3781 | `sol-vault`(9) | - | 1 |
| 79 | `sol_invoke_signed_rust` | wrapper-call | 0x4453 | 0x22298 | 0x3e44 | `sol-vault`(9) | - | 1 |
| 80 | `sol_invoke_signed_rust` | wrapper-call | 0x4d79 | 0x26bc8 | 0x449c | `sol-vault`(9) | - | 1 |
| 81 | `sol_invoke_signed_rust` | wrapper-call | 0x564f | 0x2b278 | 0x4db7 | `sol-vault`(9) | - | 1 |
| 82 | `sol_invoke_signed_rust` | wrapper-call | 0xdddd | 0x6eee8 | 0xdcfc | *(not recovered)* | - | 1 |
| 83 | `sol_invoke_signed_rust` | wrapper-call | 0xe014 | 0x700a0 | 0xdf38 | *(not recovered)* | - | 1 |
| 84 | `sol_invoke_signed_rust` | wrapper-call | 0xec1c | 0x760e0 | 0xeb3b | *(not recovered)* | - | 1 |
| 85 | `sol_invoke_signed_rust` | wrapper-call | 0xeec3 | 0x77618 | 0xede7 | *(not recovered)* | - | 1 |
| 86 | `sol_invoke_signed_rust` | wrapper-call | 0x10a43 | 0x85218 | 0x1098d | *(not recovered)* | - | 1 |
| 87 | `sol_invoke_signed_rust` | wrapper-call | 0x10d1b | 0x868d8 | 0x10c6e | *(not recovered)* | - | 1 |
| 88 | `sol_invoke_signed_rust` | wrapper-call | 0x12069 | 0x90348 | 0x12036 | *(not recovered)* | - | 5 |
| 89 | `sol_invoke_signed_rust` | wrapper-call | 0x12133 | 0x90998 | 0x120a8 | *(not recovered)* | - | 3 |
| 90 | `sol_invoke_signed_rust` | wrapper-call | 0x12203 | 0x91018 | 0x12178 | *(not recovered)* | - | 1 |
| 91 | `sol_invoke_signed_rust` | wrapper-call | 0x122d3 | 0x91698 | 0x12249 | *(not recovered)* | - | 2 |
| 92 | `sol_invoke_signed_rust` | wrapper-call | 0x13175 | 0x98ba8 | 0x13162 | *(not recovered)* | - | 3 |
| 93 | `sol_invoke_signed_rust` | wrapper-call | 0x131e0 | 0x98f00 | 0x131cd | *(not recovered)* | - | 3 |
| 94 | `sol_invoke_signed_rust` | wrapper-call | 0x13259 | 0x992c8 | 0x13238 | *(not recovered)* | - | 3 |
| 95 | `sol_invoke_signed_rust` | wrapper-call | 0x132d8 | 0x996c0 | 0x132bc | *(not recovered)* | - | 6 |
| 96 | `sol_invoke_signed_rust` | wrapper-call | 0x136a1 | 0x9b508 | 0x1369f | *(not recovered)* | - | 1 |

### Handler -> derivations reachable (forward call closure)

`body` = the derivation is inside the handler function itself; `closure` = it is
inside a helper the handler can reach. Signatures keep the literal parts and
collapse the dynamic ones to their length.

| handler | entry | body | closure | seed signatures (body) |
|---|---|---:|---:|---|
| `burn_tokens` | 0xffe1 | 1 | 6 | - |
| `buy` | 0x1027f | 1 | 8 | - |
| `buy_pump_swap` | 0x1041f | 1 | 15 | - |
| `buy_v2` | 0x1034f | 1 | 8 | - |
| `extend_account` | 0x1001c | 1 | 2 | - |
| `initialize_fee_recipient` | 0xfc41 | 1 | 10 | - |
| `initialize_global_params` | 0xfbfc | 1 | 4 | - |
| `initialize_mayhem_state` | 0x101de | 1 | 10 | - |
| `reset_sol_deployed` | 0xff2d | 1 | 0 | - |
| `reset_stable_deployed` | 0xff59 | 1 | 0 | - |
| `reset_state` | 0xfef1 | 1 | 0 | - |
| `resume_trading` | 0xff85 | 1 | 0 | - |
| `sell` | 0x10217 | 1 | 8 | - |
| `sell_pump_swap` | 0x103b7 | 1 | 13 | - |
| `sell_v2` | 0x102e7 | 1 | 8 | - |
| `stop_trading` | 0xffb3 | 1 | 0 | - |
| `sweep_fees` | 0xfc96 | 1 | 4 | - |
| `sweep_fees_admin` | 0xfcd3 | 1 | 4 | - |
| `update_admin` | 0xfe93 | 1 | 0 | - |
| `update_global_params` | 0x1004b | 1 | 1 | - |
| `update_max_sol_per_sweep` | 0xfd10 | 1 | 0 | - |
| `update_max_stable_per_sweep` | 0xfd50 | 1 | 0 | - |
| `update_trader` | 0xfe35 | 1 | 0 | - |
| `withdraw_admin` | 0xfd90 | 1 | 1 | - |
| `withdraw_quote_admin` | 0xfde2 | 1 | 7 | - |

