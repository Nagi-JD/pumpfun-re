# AMM r34 race — d1 + d2 + f2 + g3 verified on OUR amm-r34-race profile (654 → 681)

Independent verification of four source-only contributor patches (DeepSeek #2, branch
`ds2-amm-r34`: d1 `f6de978`, d2 `123ad17`, f2 `7193e57`, g3 `4fbb2df`) against OUR
canonical PumpSwap profile, the `amm-r34-race` packet (commit `337329ef`, **654 / 785
matched, 148 raw**, lalalune window metric). Each patch was ported as ONLY its
error!/macro line-placement, declaration-reorder, and out-of-line-constructor edits onto
our base and rebuilt with OUR OWN recipe (packet `build.sh`, `r34_r2.remap`, native
direct-path v1.44, `tools/measure.py` vs `evidence/original/pump_amm/deployed.so`). ds2's
own tree/recipe was NOT used for any measured build.

## Baselines

| baseline | matched/785 | raw | source |
|---|---:|---:|---|
| OUR amm-r34-race (337329ef, r5) | 654 | 148 | this repo, packet `research/amm-r34-race` |
| ds2 g3 claim (cumulative) | 681 | 148 | `ds2-amm-r34` 4fbb2df |

## Verified result (OUR recipe, OUR profile)

| state | matched/785 | raw | uniq | eqloc | Δ matched vs 654 | lost matched | lost raw |
|---|---:|---:|---:|---:|---:|---|---|
| base (reproduced) | **654** | **148** | 478 | 136 | 0 | — | — |
| + d1 (13 closures) | **667** | **148** | 491 | 149 | +13 | [] | [] |
| + d2 (5 macro/Source) | **672** | **148** | 496 | 154 | +18 | [] | [] |
| + f2 (pool.rs reorder) | **676** | **148** | 500 | 158 | +22 | [] | [] |
| + g3 (out-of-line ctors) | **681** | **148** | 505 | 163 | **+27** | [] | [] |

**Cumulative verdict: +27 matched (654 → 681), raw parity 148, lost[] empty on BOTH
the matched set and the raw set at every step. CLEAN — committable.**

Per-step gained windows match the contributor claims exactly:
- d1 (+13): deposit.rs ×8 (`0x31710 0x31918 0x31b20 0x31d28 0x31f30 0x32138 0x32340
  0x32548`) + multi_hop_swap.rs amm_hop ×5 (`0x446a0 0x448a8 0x44cc8 0x44ed0 0x450d8`).
- d2 (+5): `0x12840` constant_product.rs, `0x13190` fees.rs, `0x2e468` create_pool.rs,
  `0x6bf50` pool.rs total_virtual_quote_reserves, `0x74900` transfer_fee.rs.
- f2 (+4): `0x6b780` market_cap, `0x6ba68` total_accrued_fees, `0x6bcd0`
  available_quote_reserves, `0x6d128` take_accrued_fees (pool.rs reorder).
- g3 (+5): `0x39d80 0x39f88 0x3a190 0x3a398` (checked_sub3/add3 out-of-line Overflow
  constructor bodies) + `0xb3460` (multi_hop_swap.rs caller window).

Parity: raw set unchanged at 148 at every step (all gains are matched-window / location
recoveries). `0x6c248` (can_boost) remains in the raw set throughout — the f2 reorder
keeps `can_boost` adjacent to total_virtual_quote_reserves, preserving its call distance.

## Byte-identical reproduction

Stripped candidate `.so` SHA256 (our build) == contributor-cited artifacts, and our
f2-state mod.rs / multi_hop_swap.rs are byte-identical to ds2's g3 patch base:
- base5 `030e564d10bf33b9ff63d3ad30245d9a4dc8004fe7fd53e15d0d2f5a8f1e28dd`
- d1    `e693a3e83aff80fcc281ddba17017affbb33d47fad9227bd9c5bf303ac6982d7`
- d2    `81ef57348e1c81a765d355855382d931150fd5e185e9a6afa25bcbc8724007ab`
- f2    `0b12678caa33630b8268f44e91b7eb6774a288753239482d8f8c10e04fd29233`
- g3    `bfa34b3c208cd403ed1d4392394e355519b3ce777076fc1c0b7d8f74078e21d1`
- f2-base mod.rs `ff32d60ae146abb29895b575117f8b63e84a43f8ef70ac652c3ca9568ae2fd86`,
  multi_hop_swap.rs `36bf2f0da9398d75215b66492c688b9da8e601f25f7773849dd68d33db1b1a64`

## Nature of the edits (behavior-preserving)

- d1/d2: blank lines inside existing `error!(...)` closures so the emitted `Location`
  (`line!()`/`file!()`) lands on the deployed source line (deposit.rs, multi_hop_swap.rs,
  constant_product.rs, fees.rs, create_pool.rs, pool.rs, transfer_fee.rs).
- f2: declaration REORDER in `state/pool.rs` only — the five `impl Pool` methods reordered
  to deployed source-line order with each `error!` padded onto its line; `can_boost` kept
  adjacent to total_virtual_quote_reserves.
- g3: adds `#[inline(never)]` named constructors `checked_sub3` (3 checked ops) and
  `checked_add3` (2 checked ops) plus `#[inline(never)]` `overflow_a..e` error
  constructors in `swap/mod.rs` (each `error!(Overflow)` padded onto its deployed line),
  and rewrites the two inline checked chains in `multi_hop_swap.rs` to compute the same
  operands and call them via `super::`. The metric compares out-of-line closure BODIES,
  not names; the checked sequence, operands, and `Overflow` code are identical.

No check, arithmetic, control flow, or error code was added, removed, or weakened in any
patch; no file/line-hardcoding macro. Patches apply cleanly in sequence (d1 dry-run clean
confirms the r5 base; each later patch stacks without fuzz or reject; our f2-state sources
are byte-identical to ds2's g3 base).

## Reproduce

```sh
W=/path/to/tree
cp -r <recovered pump-amm r5 source> $W/programs/pump-amm
patch -p1 -d $W/programs/pump-amm < amm-r34-d1.patch   # +13 -> 667
patch -p1 -d $W/programs/pump-amm < amm-r34-d2.patch   # +5  -> 672
patch -p1 -d $W/programs/pump-amm < amm-r34-f2.patch   # +4  -> 676
patch -p1 -d $W/programs/pump-amm < amm-r34-g3.patch   # +5  -> 681 (cumulative)
EXTRA="$(cat r34_r2.remap)" ./build.sh d1d2f2g3 $W     # strips .so, runs tools/measure.py vs deployed.so
```

Base source is lalalune/pumpfun-source (MIT); the deployed `.so` is never a build input.
Patches authored by DeepSeek #2; this packet is an independent reproduction/verification
only (measurements and byte-hashes produced here).
