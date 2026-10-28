# chantier-T3: `SellV3::try_accounts` derive line, 0x105b78 matched

Refs T3 (#17, pump Anchor wrappers). Stacks on `chantier-T3-sell-v2` (#34).

## What the deployed program does

The `SellV3` parser window `0x105b78` (8128 B) raises Anchor error 4101 with an `anchor_lang::error::Location` built inline from the `lddw` of `programs/pump/src/trade_v3.rs`, its length and `line` = **38**. That line is the `#[derive(Accounts)]` attribute of the struct. The candidate builds the same body with `line` = 7, and every other instruction already matches (field order, field types and constraints).

## Change

- `source.patch`, `trade_v3.rs`: the `SellV3` struct moves from line 7 to line 38 (31 lines above it). The same number of lines is absorbed between the struct and line 382 by joining adjacent lines that carry no comment, so every line from 382 to the end of the file keeps its number and every other `Location` in the file is unchanged. Tokens, fields, attributes and constraints are unchanged.
- `ordered.ld`: unchanged. No `ordered-ld.patch`.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-sell-v2` | 804 | 161 | see that packet |
| this packet | **805** | **161** | `2eec30e91c5047ba42ed8ef8230d33ce539919b9eb4b6440bd90f8a4db5ccfe3` |

Gained matched: `0x105b78`. Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `call_only_raw_fail` 205 to 205, `potential_if_delta0` 366 to 366, `unique_pairs` 803 to 804, `intervals_nonzero` 88 to 88.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
