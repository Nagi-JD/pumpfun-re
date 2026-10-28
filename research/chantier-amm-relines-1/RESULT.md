# chantier-amm-matched: Location re-line batch 1 (685 -> 695, +10 matched)

Line-placement-only reconstruction of 10 same-side normalized-UNMATCHED PumpSwap
(`pump_amm`) windows on the `amm-r34-verified` g3 profile, stacked on the prior
`chantier-amm-matched` state (681 g3 -> 685 prior -> **695** here). Each window's sole
divergence from its deployed twin was the baked anchor `Location{line}` immediate; fixed
by moving the `error!`/`require!` statement onto its exact deployed source line. No
check / arithmetic / control-flow / error-code change; no file/line-hardcoding macro; the
deployed `.so` is never a build input.

## Windows recovered (cand line -> deployed line)

| file | window (dep) | function | site move(s) |
|---|---|---|---|
| `curve/constant_product.rs` | `0x11e70` (73328) | `quote_for_sell` (copy A) | DivisionByZero 17->45, Truncation 18->47 |
| `state/global_config.rs` | `0x61630` (398896) | `set_lp_fee_basis_points` | require_gte 7->220 |
| `state/global_config.rs` | `0x61898` (399512) | `set_protocol_fee_basis_points` | require_gte 13->230 |
| `state/global_config.rs` | `0x61b00` (400128) | `set_coin_creator_fee_basis_points` | require_gte 19->243 |
| `state/global_config.rs` | `0x61d68` (400744) | `set_protocol_fee_recipients` | require! 25->256, 27->263 |
| `state/global_config.rs` | `0x62688` (403080) | `validate_boost_authority` | require_keys_neq 91->292, require_keys_eq 92->297 |
| `state/global_config.rs` | `0x62c40` (404544) | `set_buyback_basis_points` | require! 70->306 |
| `state/global_config.rs` | `0x62e68` (405096) | `validate_buyback_recipient` | require_keys_neq 42->321, require! 43->326, require! 47->336 |
| `state/global_config.rs` | `0x63778` (407416) | `set_buyback_fee_recipients` | require! 76->347, require_neq 80->357 |
| `curve/fees.rs` | `0x13d30` (81200) | `tier` | require! FeeTiersEmpty 69->160 |

`global_config.rs` field (memory) offsets already matched our tree on the g3 profile
(the diff vs each deployed twin was purely the `Location{line}` immediate), so these are
pure R1 re-lines, not R3 layout changes.

## Measurement (tools/measure.py vs evidence/original/pump_amm/deployed.so)

| state | matched/785 | raw | note |
|---|---:|---:|---|
| base (prior chantier-amm-matched, g3+3) | 685 | 148 | `measure/base-685.json` |
| + constant_product + global_config + fees | **695** | **148** | `measure/final-695.json` |

Clean-room reproduced: fresh lalalune r5 recovered source + the verified g3 chain
(d1/d2/f2/g3) + prior chantier patches + these 3 patches -> **695**, raw parity 148,
`lost[]` empty on BOTH the matched set and the raw set. CLEAN -- committable.

Gained windows: `0x11e70 0x13d30 0x61630 0x61898 0x61b00 0x61d68 0x62688 0x62c40 0x62e68 0x63778`.

## Reproduce

```sh
cp -r <recovered pump-amm g3+prior source> $W/programs/pump-amm
patch -p1 -d $W/programs/pump-amm < patches/constant_product.patch
patch -p1 -d $W/programs/pump-amm < patches/global_config.patch
patch -p1 -d $W/programs/pump-amm < patches/fees.patch
EXTRA="$(cat r34_r2.remap)" ./build.sh relines1 $W   # tools/measure.py vs deployed.so
```

Base source is lalalune/pumpfun-source (MIT); the deployed `.so` is never a build input.
Per-window deployed target lines read from the deployed binary (`Location` reloc, type 8);
re-line mechanism identical to the verified `d1`/`d2` packets (+27) and the prior
chantier-amm-matched packet (+4).

Credit: form oracle lalalune/pumpfun-source (MIT). PR-only; no `.so`, no secrets.
