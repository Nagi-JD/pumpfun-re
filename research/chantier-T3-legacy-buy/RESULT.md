# chantier-T3: `LegacyBuy::try_accounts` derive line, 0x172110 matched

Refs T3 (#17, pump Anchor wrappers). Stacks on `chantier-T3-create` (#39).

## What the deployed program does

The `LegacyBuy` parser window `0x172110` (8128 B) raises Anchor error 4101 with an `anchor_lang::error::Location` built inline from the `lddw` of `programs/pump/src/lib.rs`, its length and `line` = **2871**. That line is the `#[derive(Accounts)]` attribute of the struct. The candidate builds the same body from `programs/pump/src/buy.rs`, and every other instruction already matches (field order, field types and constraints). The deployed path is `lib.rs`, so the struct is declared in `lib.rs` at line 2871.

## Change

- `source.patch`, `lib.rs` and `buy.rs`: the `pub mod legacy_buy;` declaration becomes an inline `pub mod legacy_buy{include!("buy.rs"); ... }` placed after the last item of `lib.rs`, and the `LegacyBuy` struct moves from `buy.rs` into that inline module with its `#[derive(Accounts)]` at `lib.rs` line 2871. The vacated lines in `buy.rs` become blank, so every other line in that file keeps its number. The struct stays in module `legacy_buy`, so its def path and every mangled symbol in `ordered.ld` are unchanged. Tokens, fields, attributes and constraints are unchanged. The inline module carries `#[path=""]` so its nested `#[path]` module declarations resolve as before.
- `ordered.ld`: unchanged. No `ordered-ld.patch`.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-create` | 811 | 161 | see that packet |
| this packet | **812** | **161** | `d91d4cb0162569faebd07071fbfd91b46406d66322e2122d51969ed00d651c20` |

Gained matched: `0x172110`. Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `call_only_raw_fail` 205 to 205, `potential_if_delta0` 366 to 366, `unique_pairs` 810 to 811, `intervals_nonzero` 88 to 88.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
