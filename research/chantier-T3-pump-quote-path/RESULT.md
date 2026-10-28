# chantier-T3: create_v2 nested quote helper file is `pump_quote.rs`, 0x63530 matched

Refs T3 (#17, pump Anchor wrappers) and #19. Stacks on `chantier-T3-sharing-config-line` (#52).

## What the deployed program does

The deployed window `0x63530` (520 B, the `overflow()` error constructor of the nested create quote walk) raises 6024 (`Overflow`) with an `anchor_lang::error::Location` built inline from `programs/pump/src/pump_quote.rs` (length 31), `line` = **212**. Sixteen deployed windows between `0x60a80` and `0x65238` carry that same path. The candidate module file was `nested_create.rs` (length 34) with `overflow()` on line 19.

## Change

- `source.patch`:
  - `create_v2.rs` line 3: `#[path = "pump_quote.rs"] mod nested_create;`, so the module path and every mangled name stay the same.
  - `nested_create.rs` is renamed to `pump_quote.rs`. `fn overflow()` moves from line 19 to line 212; line 19 becomes blank, so every other line keeps its number.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-sharing-config-line` | 827 | 161 | `b03922b4f3edeed92bc8cadf63ca78104777582c39ccdb4981ac6a61ecb5ae76` |
| this packet | **828** | **161** | `2ec5872da9e3cee77a288ffbc6ceb5738fe5bb46fb4f98cd37a9d8ffb2f4c771` |

Gained matched: `0x63530`. Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `call_only_raw_fail` 205 to 205, `potential_if_delta0` 366 to 366, `unique_pairs` 826 to 827, `intervals_nonzero` 92 to 93 (the new matched pair adds one placement interval).

The deployed twin `0x63738` (same body, line 222) is a second `overflow()` instance with its own call site in the deployed quote walk.

No `ordered.ld` change: the selectors are unchanged.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
