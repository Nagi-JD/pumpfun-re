# chantier-T3: `Create::try_accounts` derive line, 0x16a3e0, 0x16bdf0 matched

Refs T3 (#17, pump Anchor wrappers). Stacks on `chantier-T3-initialize` (#38).

## What the deployed program does

The `Create` parser windows `0x16a3e0` (6672 B), `0x16bdf0` (6464 B) raise Anchor error 4101 with an `anchor_lang::error::Location` built inline from the `lddw` of `programs/pump/src/lib.rs`, its length and `line` = **2811**. That line is the `#[derive(Accounts)]` attribute of the struct. The candidate builds the same body from `programs/pump/src/create.rs`, and every other instruction already matches (field order, field types and constraints). The deployed path is `lib.rs`, so the struct is declared in `lib.rs` at line 2811.

## Change

- `source.patch`, `lib.rs` and `create.rs`: the `pub mod create;` declaration becomes an inline `pub mod create{include!("create.rs"); ... }` placed after the last item of `lib.rs`, and the `Create` struct moves from `create.rs` into that inline module with its `#[derive(Accounts)]` at `lib.rs` line 2811. The vacated lines in `create.rs` become blank, so every other line in that file keeps its number. The struct stays in module `create`, so its def path and every mangled symbol in `ordered.ld` are unchanged. Tokens, fields, attributes and constraints are unchanged.
- `ordered.ld`: unchanged. No `ordered-ld.patch`.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-initialize` | 809 | 161 | see that packet |
| this packet | **811** | **161** | `4b6e6d7210c739e651fe515ada4bf73d9b1004bb1125b1d4437f986f40912d10` |

Gained matched: `0x16a3e0`, `0x16bdf0`. Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `call_only_raw_fail` 205 to 205, `potential_if_delta0` 366 to 366, `unique_pairs` 808 to 810, `intervals_nonzero` 88 to 88.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
