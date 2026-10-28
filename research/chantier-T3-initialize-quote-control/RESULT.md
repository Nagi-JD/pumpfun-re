# chantier-T3: `InitializeQuoteControl::try_accounts` derive line, 0xdf2d8 matched

Refs T3 (#17, pump Anchor wrappers). Stacks on `chantier-T3-create-v2` (#36).

## What the deployed program does

The `InitializeQuoteControl` parser window `0xdf2d8` (5952 B) raises Anchor error 4101 with an `anchor_lang::error::Location` built inline from the `lddw` of `programs/pump/src/quote_control/initialize_quote_control.rs`, its length and `line` = **7**. That line is the `#[derive(Accounts)]` attribute of the struct. The candidate builds the same body with `line` = 5, and every other instruction already matches (field order, field types and constraints).

## Change

- `source.patch`, `quote_control/initialize_quote_control.rs`: the `InitializeQuoteControl` struct moves from line 5 to line 7 (2 lines above it). The same number of lines is absorbed between the struct and line 32 by joining adjacent lines that carry no comment, so every line from 32 to the end of the file keeps its number and every other `Location` in the file is unchanged. Tokens, fields, attributes and constraints are unchanged.
- `ordered.ld`: unchanged. No `ordered-ld.patch`.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-create-v2` | 807 | 161 | see that packet |
| this packet | **808** | **161** | `4aec881f86f617486662141e5fbadda36e4aee712bda6c52a22f674efe6da23e` |

Gained matched: `0xdf2d8`. Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `call_only_raw_fail` 205 to 205, `potential_if_delta0` 366 to 366, `unique_pairs` 806 to 807, `intervals_nonzero` 88 to 88.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
