# chantier-T3: `InitUserVolume::try_accounts` derive line, 0xfdf20 matched

Refs T3 (#17, pump Anchor wrappers). Stacks on `chantier-T3-legacy-buy` (#40).

## What the deployed program does

The `InitUserVolume` parser window `0xfdf20` (7824 B) raises Anchor error 4101 with an `anchor_lang::error::Location` built inline from the `lddw` of `programs/pump/src/token_incentives/init_user_volume_accumulator.rs`, its length and `line` = **8**. That line is the `#[derive(Accounts)]` attribute of the struct. The candidate builds the same body inside `lib.rs`, and every other instruction already matches (field order, field types and constraints). The deployed path is `token_incentives/init_user_volume_accumulator.rs`, line 8.

## Change

- `source.patch`, `lib.rs` and `token_incentives/init_user_volume_accumulator.rs` (new): the `InitUserVolume` struct moves into `token_incentives/init_user_volume_accumulator.rs` with its `#[derive(Accounts)]` at line 8, and `lib.rs` pulls it back in with `include!("token_incentives/init_user_volume_accumulator.rs");` on the first vacated line. The remaining vacated lines in `lib.rs` become blank, so every other line in `lib.rs` keeps its number. The struct stays in the crate root, so its def path and every mangled symbol in `ordered.ld` are unchanged. Tokens, fields, attributes and constraints are unchanged.
- `ordered.ld`: unchanged. No `ordered-ld.patch`.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-legacy-buy` | 812 | 161 | see that packet |
| this packet | **813** | **161** | `1ce9df3a268c600b11341d1ae8822b5d34e4f92cb27cd246f85edb73bab7513c` |

Gained matched: `0xfdf20`. Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `call_only_raw_fail` 205 to 205, `potential_if_delta0` 366 to 366, `unique_pairs` 811 to 812, `intervals_nonzero` 88 to 88.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
