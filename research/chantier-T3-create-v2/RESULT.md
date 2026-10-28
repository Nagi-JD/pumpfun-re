# chantier-T3: `CreateV2::try_accounts` derive line, 0xb0158, 0xb3b90 matched

Refs T3 (#17, pump Anchor wrappers). Stacks on `chantier-T3-sell-v3` (#35).

## What the deployed program does

The `CreateV2` parser windows `0xb0158` (14904 B), `0xb3b90` (6464 B) raise Anchor error 4101 with an `anchor_lang::error::Location` built inline from the `lddw` of `programs/pump/src/create_v2.rs`, its length and `line` = **27**. That line is the `#[derive(Accounts)]` attribute of the struct. The candidate builds the same body with `line` = 14, and every other instruction already matches (field order, field types and constraints).

## Change

- `source.patch`, `create_v2.rs`: the `CreateV2` struct moves from line 14 to line 27 (13 lines above it). The same number of lines is absorbed between the struct and line 412 by joining adjacent lines that carry no comment, so every line from 412 to the end of the file keeps its number and every other `Location` in the file is unchanged. Tokens, fields, attributes and constraints are unchanged.
- `ordered.ld`: unchanged. No `ordered-ld.patch`.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-sell-v3` | 805 | 161 | see that packet |
| this packet | **807** | **161** | `bde51f7da35b05518440b12b4f6a729840c7b534622dda78beaac8919b1cd73e` |

Gained matched: `0xb0158`, `0xb3b90`. Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `call_only_raw_fail` 205 to 205, `potential_if_delta0` 366 to 366, `unique_pairs` 804 to 806, `intervals_nonzero` 88 to 88.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
