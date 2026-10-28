# chantier-amm-matched: state/pool.rs reorder re-line batch 3 (+2 matched)

Reconstruction of 2 UNMATCHED PumpSwap (`pump_amm`) windows in `state/pool.rs` on the
`amm-r34-verified` g3 profile by restoring the deployed FUNCTION ORDER and re-lining the
`error!` sites:

- `effective_quote_reserves` and `accrue_fees` were defined at the TOP of our tree; the
  deployed binary places them in the tail, after `total_virtual_quote_reserves` /
  `can_boost` and before `take_accrued_fees`. Moved both to the tail with each `error!`
  on its exact deployed source line; blanked the vacated top region to keep every
  already-matched function (market_cap ... total_virtual_quote_reserves) on its line.

No check / arithmetic / control-flow / error-code change. The `buyback_fee` /
`checked_add` statement formatting was compacted (codegen-identical: same opcodes, same
operands, same `Overflow` codes) purely to place each `error!` on its deployed line; no
file/line-hardcoding macro; deployed `.so` never a build input.

## Windows recovered (deployed error! lines)

| window (dep) | function | sites |
|---|---|---|
| `0x6c328` (443176) | `effective_quote_reserves` | Overflow 439, 440 |
| `0x6c768` (444264) | `accrue_fees` | Overflow 458, 462, 465, 469 |

Preserved matched/raw: `total_virtual_quote_reserves` error! @426, `take_accrued_fees`
error! @484, `can_boost` (raw) — all kept on their deployed lines (no regression).

## Measurement (tools/measure.py vs evidence/original/pump_amm/deployed.so)

| state | matched/785 | raw |
|---|---:|---:|
| base (g3) | 685 | 148 |
| + pool.rs reorder (this batch, standalone) | **687** | **148** |

Composes additively with re-line batches 1 (+10) and 2 (+4): combined state measures
**701 / 148**. Clean-room reproduced; `lost[]` empty on BOTH the matched set and the raw
set (raw parity 148). PR-only; no `.so`, no secrets. Form oracle credit:
lalalune/pumpfun-source (MIT).

## Reproduce

```sh
cp -r <recovered pump-amm g3 source> $W/programs/pump-amm
patch -p1 -d $W/programs/pump-amm < patches/pool.patch
EXTRA="$(cat r34_r2.remap)" ./build.sh relines3 $W   # tools/measure.py vs deployed.so
```
