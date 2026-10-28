# chantier-T3: `SellV2::try_accounts` derive line, 0xebaa0 matched

Refs T3 (#17, pump Anchor wrappers). Stacks on `chantier-T3-buy-v2` (#33).

## What the deployed program does

The `SellV2` parser window `0xebaa0` (8128 B) raises Anchor error 4101 with an `anchor_lang::error::Location` built inline from the `lddw` of `programs/pump/src/sell_v2.rs`, its length and `line` = **32**. That line is the `#[derive(Accounts)]` attribute of the struct. The candidate builds the same body with `line` = 8, and every other instruction already matches (field order, field types and constraints).

## Change

- `source.patch`, `sell_v2.rs`: the `SellV2` struct moves from line 8 to line 32 (24 lines above it). The same number of lines is absorbed between the struct and line 341 by joining adjacent lines that carry no comment, so every line from 341 to the end of the file keeps its number and every other `Location` in the file is unchanged. Tokens, fields, attributes and constraints are unchanged.
- `ordered.ld`: unchanged. No `ordered-ld.patch`.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-buy-v2` | 803 | 161 | see that packet |
| this packet | **804** | **161** | `d72aa9375fe777a00a7f26f4f700747640374573dad87b924871648a5497e601` |

Gained matched: `0xebaa0`. Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `call_only_raw_fail` 205 to 205, `potential_if_delta0` 366 to 366, `unique_pairs` 802 to 803, `intervals_nonzero` 88 to 88.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
