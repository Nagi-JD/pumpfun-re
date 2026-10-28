# chantier-T3: exact-SOL legacy buy through constant_product::tokens_for_quote, 1 window matched

Refs T3 (#17, pump Anchor wrappers) and #19. Stacks on `chantier-T3-legacy-sell-payments` (#66).

## What the deployed program does

- For `buy_exact_sol_in`, the legacy buy body computes the token amount through an out-of-line `tokens_for_quote(curve, quote)`. It takes `quote - 1` (checked, `Overflow` on zero) and evaluates the constant-product output `effective * virtual_token_reserves / (virtual_quote_reserves + effective)` with checked multiply, add and divide (`Overflow`, `DivisionByZero`).

## Change

- `source.patch`:
  - new `util/constant_product.rs` (`output`, `tokens_for_quote`), declared as `crate::constant_product` on a blank line of `lib.rs`.
  - the legacy buy body calls it in place of the inline division. Line count of `lib.rs` unchanged.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-legacy-sell-payments` | 890 | 162 | `e308790de6e769912b88eb5e4484eb38b5b9875ff95c3b3053cd693cc66d72f3` |
| this packet | **891** | **162** | `42919ff8bcdca25b566994e19c6ec96b3a6c48ed0c92e7f0873c2b2fa432d4d7` |

Gained matched (1): `0xa0838` (`tokens_for_quote`). Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `unique_pairs` 889 to 890, `intervals_nonzero` 130 to 131.

No `ordered.ld` change.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Ported from [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), `main@6e6ac0fe` (`programs/pump/src/util/constant_product.rs`, `programs/pump/src/buy.rs`).
