# AMM pool.rs line layout: +7 windows (2026-10-28)

Stacked on `research/amm-multihop-941` (u4b). Same toolchain and metric
(platform-tools v1.44 direct `cargo rustc`, `remap-path-prefix.txt`, lalalune
window metric against `evidence/original/pump_amm/deployed.so`). Builds on
lalalune/pumpfun-source (MIT).

## Before / after

| build | matched / 785 | raw | unique_pairs |
|---|---:|---:|---:|
| u4b (amm-multihop-941) | 658 | 128 | 482 |
| **u5 (this packet)** | **665** | **128** | **489** |

gained deployed windows (7), lost none, raw set unchanged (128 -> 128):
`0x6b780`, `0x6ba68`, `0x6bcd0`, `0x6bf50`, `0x6c328`, `0x6c768`, `0x6d128`.

## What the windows are

All seven are the `state/pool.rs` closure family. The deployed file carries 11
closures (from the binary, `tools/10-inv-closures.py`):

| deployed line | code | fn (by window shape) |
|---|---|---|
| 386 | 6025 DivisionByZero | market_cap |
| 408 / 417 / 426 / 484 | 6023 Overflow | the four single-closure helpers |
| 439 / 440 | 6023 Overflow | effective_quote_reserves (spacing 1) |
| 458 / 462 / 465 / 469 | 6023 Overflow | accrue_fees (spacing 4/3/4) |

The candidate had the same 11 closures at lines 27/31/34/38/47/48/57/64/76/87/94
in a 102-line file. The spacing match (4/3/4 and 1) fixes the multi-closure
assignments unambiguously. The permutation of the four single-closure helpers
over 408/417/426/484 is not recoverable from the arms (identical bodies); it is
cosmetic (line numbers only, behavior unchanged) and follows the deployed window
order with `can_boost` kept adjacent to `total_virtual_quote_reserves` (see
below).

## The change (`pool-lanes.patch`)

1. Reorder the fns to the deployed file order (window order): market_cap,
   total_accrued_fees, available_quote_reserves, total_virtual_quote_reserves,
   can_boost, effective_quote_reserves, accrue_fees, take_accrued_fees.
2. Place every `error!` on its deployed line by adjusting each segment (before
   the first closure / between closures) to the exact deployed spacing:
   blank lines to pad, line joins to shrink. Both are whitespace-only: zero
   codegen impact. No macro hardcodes a file or line; the deployed `.so` is not
   a build input.

## The raw-set trap (and the fix)

The first measured attempt (u5 with `can_boost` last) gave 665 matched but
**127 raw**: window `0x6c248` (can_boost's body) lost raw-byte equality because
its PC-relative call to `total_virtual_quote_reserves` changed offset when the
fn order changed. The deployed window layout shows the small 224-byte window
immediately after the 426 single - i.e. can_boost sits right after
total_virtual_quote_reserves there too. Restoring that adjacency restores the
call immediate and the raw set (128). Rule 1 honoured: the change is kept only
with no regression in either set.

## Evidence

- `pool-lanes.patch` - u4b -> u5 (state/pool.rs only).
- `measure-u4b.json`, `measure-u5.json` - metric outputs (matched/raw sets).
- `transform-pool-lines.py` - the layout transform with per-line asserts.
- `SHA256SUMS`.
