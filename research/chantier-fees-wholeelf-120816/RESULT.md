# chantier-fees whole-ELF: `sweep_buyback` handler body, window 120816 matched — 585/585 normalized

Refs the Fees whole-ELF frontier. Third and final packet of the Fees close-out.
Stacks on `chantier-fees-wholeelf-163920` (window 163920). With this packet every
deployed Fees function window has a normalized byte-equal counterpart:
**585 / 585 normalized, 0 unmatched.**

## What the deployed program does

The deployed `sweep_buyback` handler window **120816 (848 instructions /
6,960 B)** diverged from the candidate only by **register allocation / stack-slot
coloring** (an r7↔r8 coin-flip and shifted frame slots across the entry /
accounts-load / context-spill / bump-load / bump-spill sequence at offsets
40–64). Same instructions, same calls — a scheduling/allocation difference driven
by source evaluation order.

The deployed body reads the bump and takes the vault and **destination** borrows
**before** the index guard; it uses temporary signer-seed arrays inline in the
`transfer_checked` call, propagates the `claim()` error at the caller (so
`claim` returns `core::result::Result<(), FeeError>`), and keeps the
claimed-counter updates in small `BuybackVault` state methods.

## Change

`source.patch` (two files, applies with `patch -p1`):

- `programs/pump-fees/src/instructions/buyback/mod.rs`: in `sweep_buyback`, read
  `bump_value` and take `&mut destination` before `require_gt!(8u8,index,…)`
  (the guard keeps its original source line — no behavior change). Build the
  signer seeds inline (`&[&[b"buyback-vault",&[index],&[bump_value]]]`) and call
  the three `add_total_claimed*` state methods.
- `programs/pump-fees/src/state.rs`: `BuybackVault::claim` returns
  `core::result::Result<(), crate::FeeError>` and returns the bare error; add
  `add_total_claimed`, `add_total_claimed_token1`, `add_total_claimed_token2`
  (checked adds with `MathOverflow`).

These are ordinary Rust ownership/evaluation choices. Behavior is unchanged:
same guard, same CPI, same checked accounting, same event.

## Measure (box: `window_map.py` normalized/raw over the deployed Fees ELF)

| build | normalized | raw (exact) | candidate (symbols.so) sha256 |
|---|---:|---:|---|
| parent (after 163920) | 584 | 200 | `57e11a5e…a701a02` |
| this packet | **585** | **288** | `e7a233d2…e8860f` |

Gained normalized: `120816` → **585/585, unmatched_original = []**. Lost
normalized: none. Raw not dropped — it rises 200→288 in lineage order.

Standalone note: applied alone on the 582 baseline, this change still closes
120816 (582→583) but dips raw 200→195 under the plain linker (incidental layout);
in the intended lineage order (after 147944 + 163920) raw holds then rises to
288. Whole-ELF raw/byte identity is produced by the orthogonal `ordered.ld` +
`relayout.py` layout layer, which is not part of this normalized-window packet.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Reproduces the method of
[lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT),
packet `research/fees-sweep-integration` (entry-order borrow before the index
guard + small state methods). `source.patch` is lalalune's sweep source patch,
applied verbatim to the identical parent. Credit: lalalune.
