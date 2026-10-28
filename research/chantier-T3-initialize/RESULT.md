# chantier-T3: `Initialize::try_accounts` derive line, 0x164e40 matched

Refs T3 (#17, pump Anchor wrappers). Stacks on `chantier-T3-initialize-quote-control` (#37).

## What the deployed program does

The `Initialize` parser window `0x164e40` (5896 B) raises Anchor error 4101 with an `anchor_lang::error::Location` built inline from the `lddw` of `programs/pump/src/lib.rs`, its length and `line` = **2778**. That line is the `#[derive(Accounts)]` attribute of the struct. The candidate builds the same body from `programs/pump/src/global_init.rs`, and every other instruction already matches (field order, field types and constraints). The deployed path is `lib.rs`, so the struct is declared in `lib.rs` at line 2778.

## Change

- `source.patch`, `lib.rs` and `global_init.rs`: the `pub mod global_init;` declaration becomes an inline `pub mod global_init{include!("global_init.rs"); ... }` placed after the last item of `lib.rs`, and the `Initialize` struct moves from `global_init.rs` into that inline module with its `#[derive(Accounts)]` at `lib.rs` line 2778. The vacated lines in `global_init.rs` become blank, so every other line in that file keeps its number. The struct stays in module `global_init`, so its def path and every mangled symbol in `ordered.ld` are unchanged. Tokens, fields, attributes and constraints are unchanged.
- `ordered.ld`: unchanged. No `ordered-ld.patch`.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-initialize-quote-control` | 808 | 161 | see that packet |
| this packet | **809** | **161** | `c13e68c4f734bde0253411b988524d875ed0c1ae331d830d595cf62f01c88c70` |

Gained matched: `0x164e40`. Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `call_only_raw_fail` 205 to 205, `potential_if_delta0` 366 to 366, `unique_pairs` 807 to 808, `intervals_nonzero` 88 to 88.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
