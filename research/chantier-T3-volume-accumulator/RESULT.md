# chantier-T3: `GlobalVolumeAccumulator` / `UserVolumeAccumulator` account lines, 0x101170 and 0x101c20 matched

Refs T3 (#17, pump Anchor wrappers) and #19. Stacks on `chantier-T3-init-user-volume` (#41).

## What the deployed program does

The deployed `try_deserialize` windows `0x101170` (728 B, `GlobalVolumeAccumulator`) and `0x101c20` (728 B, `UserVolumeAccumulator`) raise Anchor error 3002 (`AccountDidNotDeserialize`) with an `anchor_lang::error::Location` built inline from the `lddw` of `programs/pump/src/token_incentives/volume_accumulator.rs`, its length 56 and `line` = **8** and **19**. Those lines are the `#[account]` attributes of the two structs. The candidate declared `GlobalVolumeAccumulator` in `volume_sync.rs` line 2 and `UserVolumeAccumulator` in `lib.rs` line 461, so both windows carried another path and line.

## Change

- `source.patch`:
  - `token_incentives/volume_accumulator.rs`: `#[account] #[derive(Debug)] pub struct GlobalVolumeAccumulator` at line 8 and `#[account] #[derive(Default)] pub struct UserVolumeAccumulator` at line 19, ahead of the existing body. Fields, field order and attributes are unchanged.
  - `volume_sync.rs` line 2 and `lib.rs` line 461 re-export the structs with `pub use`. The vacated lines become blank, so every other line in both files keeps its number.
- `ordered-ld.patch`: the structs now live in `token_incentives::volume_accumulator`, which changes 25 mangled names (their `AccountDeserialize` and `Debug` impls, the generic `Account<T>` helpers instantiated on them, and the parsers and `volume_accumulator` functions that take them). Each selector is renamed in place to the new name, so placement order is unchanged.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-init-user-volume` | 813 | 161 | `1ce9df3a268c600b11341d1ae8822b5d34e4f92cb27cd246f85edb73bab7513c` |
| this packet | **815** | **161** | `e4a5ef1016bed9b6eacdd535067f22844835e1da3bf8f491fda1d9924692e1e7` |

Gained matched: `0x101170`, `0x101c20`. Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `call_only_raw_fail` 205 to 205, `potential_if_delta0` 366 to 366, `unique_pairs` 812 to 814, `intervals_nonzero` 88 to 91.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
