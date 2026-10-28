# chantier-T5: `tools/data_layout.py`, data-section layout solver (813/161 reference)

Refs T5 (#19, pump `.rodata` / data layout). Stacks on `chantier-T3-init-user-volume` (#41).

## What the tool measures

A matched window that raw-fails on an `lddw` (opcode `0x18`) carries a 64-bit data address. That address is `section_base + intra_offset`:

- `section_base` is set by everything linked before the section (`.text` length first).
- `intra_offset` is set by the order, size and dedup of the records inside `.rodata` / `.data.rel.ro`: strings, discriminators, error tables and `core::panic::Location` records (24 B: `&str` file, line, column).

`tools/data_layout.py` pairs windows exactly like `measure.py` / `drift_solver.py`, then for every differing `lddw` resolves both targets to `(section, intra offset)` (or, for a `.text` target, to the offset inside the paired function) and classifies each matched raw-failing window:

- `data_aligned`: every differing `lddw` already points to the same record. The remaining residual is section bases and call immediates (T6 / relayout).
- `data_residual`: at least one differing `lddw` points to a different record (T5).

It also decodes every `Location` record on both sides and lists the paired ones that differ in file, line or column (the source-line worklist), the `.rs` path strings present on one side only, and how far `.rodata` and `.data.rel.ro` are equal from the section start (pointers compared as section plus intra offset).

Usage:

```
python3 tools/data_layout.py DEPLOYED.so symbols.so --cand-stripped candidate.so -o data-layout.json [--window 0xADDR]
```

## Reference on the #41 build (813 matched / 161 raw)

| metric | value |
|---|---:|
| matched / exact | 813 / 161 |
| `data_aligned` windows (residual = bases + calls) | 231 |
| `data_residual` windows | 421 |
| `other` windows | 0 |
| differing `lddw` sites / intra-aligned | 3087 / 527 |
| `.rodata` sites aligned | 1 of 2046 |
| `.data.rel.ro` sites aligned | 427 of 938 |
| `.text` sites aligned (inside the paired function) | 99 of 103 |
| `Location` records deployed / candidate | 142 / 200 |
| paired `Location` records equal / line / file | 90 / 14 / 8 |
| files with identical `Location` line sets | 25 of 41 |
| `.rodata` equal prefix | 216 B |
| `.data.rel.ro` equal prefix (rebased) | 104 B |

Section bases: `.rodata` -42352, `.data.rel.ro` -42520 (the `.text` length). Section sizes: `.rodata` -172 B, `.data.rel.ro` +1440 B.

The first `.rodata` divergence is at offset `0xd8`: the deployed record there is an error string, the candidate record is the 32-byte path `programs/pump/src/volume_sync.rs`. The deployed program has no `volume_sync.rs` or `set_creator.rs` path. Its `GlobalVolumeAccumulator` and `UserVolumeAccumulator` `#[account]` lines are `token_incentives/volume_accumulator.rs` lines 8 and 19.

`location_worklist` in `data-layout-ref.json` lists all 22 paired `Location` differences with their windows. The three `transfer_from_user` bodies (`0x97930`, `0x97bf0`, `0x97eb0`) share one deployed pair of `unwrap` locations (`lib.rs` 1477:42 and 1478:40), and the candidate emits three pairs. The `#[program]` attribute is `lib.rs` line 90 in the deployed program (four `__idl` windows), line 66 in the candidate.

## Measure

No source change. Build, `ordered.ld` and measure are the #41 packet: matched 813, exact 161, candidate sha256 `1ce9df3a268c600b11341d1ae8822b5d34e4f92cb27cd246f85edb73bab7513c`. Gained raw: none. Lost matched: none. Lost raw: none.

Details: `data-layout-ref.json`, `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
