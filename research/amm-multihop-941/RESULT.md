# AMM multi_hop 941: the missing Overflow closure, placed (2026-10-28)

Stacked on `research/amm-race-2` (u2). Same toolchain and metric: platform-tools
v1.44 direct-path `cargo rustc` (`research/amm-race/build.sh` recipe,
`remap-path-prefix.txt`), measured with the lalalune window metric
(`tools/measure.py` from `fees-sharing-slice-recovery/verify.py`) against
`evidence/original/pump_amm/deployed.so`. Builds on lalalune/pumpfun-source (MIT).

## Before / after

| build | matched / 785 | raw | unique_pairs |
|---|---:|---:|---:|
| u2 baseline (rebuilt here) | 657 | 128 | 481 |
| **u4b (this packet)** | **658** | **128** | **482** |

- gained deployed window: **0xb92c8** (520 B) - the only window changed.
- lost: none. matched set and raw set are supersets of the u2 baseline
  (`measure-u4b.json` vs `measure-u2fix.json`).

The rebuilt u2 baseline is byte-identical to the amm-race-2 candidate
(`u2-candidate.so` sha256 `48c6fc5644...`), which validates the whole local
build chain before any change.

## What the window is

`0xb92c8` is the outlined cold error arm of the `Overflow` (Anchor 6023) raise at
`programs/pump-amm/src/instructions/swap/multi_hop_swap.rs:941`:

- closure construction at pc 0x17288 (byte 0xb9440): path string vaddr 0x11ccc8
  (len 57), line 0x3ad (941), code 0x1787 (6023).
- single call site idx 0x92c3, the overflow check `r2 = r4 + r6` at idx
  0x92b8-0x92bd (a two-step `checked_add` chain shares this arm: a second check
  at idx 0x9328-0x932e jumps back to the same arm call).
- the arm is a byte-level twin of the 636-line arm at idx 0x8999 (byte 0x44cc8,
  matched since amm-race) except the baked line constant (0x27c vs 0x3ad).

The u2 candidate had the same semantic checks in the hop loop
(`checked_sub/checked_add` + `require_eq!(..., MultiHopCurveRunMismatch)`) with
its closures at lines 312/313/325/326 - the same (code, order) multiset as the
deployed cluster at 928/929/936/941. The u2 packets placed the 579/586/636/671/718
closures but not this cluster ("multi_hop 941 - not placed ... in a helper our
source does not split out").

## The change (`multi-hop-941.patch`)

1. Extract block-2's checked-add chain into `expected_destination` (same values,
   same checks, same `PumpAmmError::Overflow`, same evaluation result - the
   helper is `#[inline(always)]`, so the compiled caller keeps the same shape).
   This is the "helper our source does not split out": its definition sits after
   the event emission, exactly where the deployed file carries lines 928-941.
2. Join the two `emit_event(...)` literals to one line each (pure whitespace -
   no closures or line-bearing macros inside; no baked constants change).
3. Place the helper's `error!` on line 941 with blank-line padding inside the
   closure - the same placement method as the amm-race packets. The matched
   closures 307/579/586/636/671/718 stay on their lines (compensating padding
   in the 518-closure).

No macro hardcodes a file or line; placement is real code position. The deployed
`.so` is not a build input.

## Evidence

- `multi-hop-941.patch` - u2 source -> u4b source.
- `measure-u2fix.json`, `measure-u4b.json` - metric outputs (matched/raw sets).
- `build-recipe.sh` - the exact build + measure commands.
- `transform-941.py` - the transformation with line asserts (307/579/586/636/671/718
  preserved, error! verified at 941).
- `SHA256SUMS`.

## Notes / limits

- The big per-hop windows (0x40a08, 0x45940) remain unmatched; this packet only
  closes the 520-byte arm window, per the claimable task.
- The deployed cluster order is (928:6023, 929:6085, 936:6085, 941:6023) while
  the candidate block order is (Overflow, CurveRun) per block. The 928/929/936
  closures live inside the unmatched worker window, so their line placement does
  not affect the metric; reconciling them is a follow-up for the worker window.
- A `#[inline(never)]` variant was measured first and gained nothing (657): the
  small helper does not get its cold arm outlined, so no 58-insn arm window is
  emitted. `#[inline(always)]` puts the closure back in the large caller, which
  outlines the arm exactly as the deployed build did (confirmed by the measure:
  +0xb92c8).
