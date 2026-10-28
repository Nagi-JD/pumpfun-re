# chantier-T3: `BuyV2::try_accounts` derive line, 0xa9eb8 matched

Refs T3 (#17, pump Anchor wrappers). Stacks on `chantier-T4-close-burn-helpers` (master).

## What the deployed program does

The `BuyV2` parser window `0xa9eb8` (8128 B) raises Anchor error 4101 with an `anchor_lang::error::Location` built inline from the `lddw` of `programs/pump/src/buy_v2.rs`, its length and `line` = **129**. That line is the `#[derive(Accounts)]` attribute of the struct. The candidate builds the same body with `line` = 8, and every other instruction already matches (field order, field types and constraints).

## Change

- `source.patch`, `buy_v2.rs`: the `BuyV2` struct moves from line 8 to line 129 (121 lines above it). The same number of lines is absorbed between the struct and line 465 by joining adjacent lines that carry no comment, so every line from 465 to the end of the file keeps its number and every other `Location` in the file is unchanged. Tokens, fields, attributes and constraints are unchanged.
- `ordered.ld`: unchanged. No `ordered-ld.patch`.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T4-close-burn-helpers` | 802 | 161 | see that packet |
| this packet | **803** | **161** | `85dc4036a846148e10d6f1c6724f3ca9caef386b9b6388b60207dd6fba07fd28` |

Gained matched: `0xa9eb8`. Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `call_only_raw_fail` 205 to 205, `potential_if_delta0` 366 to 366, `unique_pairs` 801 to 802, `intervals_nonzero` 88 to 88.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
