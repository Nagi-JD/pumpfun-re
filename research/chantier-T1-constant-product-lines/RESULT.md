# chantier-T1: constant_product::output Location lines, 1 window matched

Refs T1 (SPECS §4, Location re-lines) and #19. Stacks on `chantier-T3-control-account` (#69).

## What the deployed program does

- `constant_product::output` (`amount_in * reserve_out / (reserve_in + amount_in)` over u128) reports its `Overflow` and `DivisionByZero` errors at lines 13, 17 and 19 of its source file. The body was already identical; only the three line immediates differed.

## Change

- `source.patch`: `util/constant_product.rs` places the numerator, denominator and division sites on lines 13, 17 and 19. `tokens_for_quote` keeps its lines.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-control-account` | 892 | 162 | `1ed4c63fe6c9a70f60875c667b2dd694a173f801cbd255b4cb0b39da0575fb38` |
| this packet | **893** | **162** | `d37303deb66741617937fe7c63923a9f8a45db71fef16c9a9bbb775e52adf225` |

Gained matched (1): `0x880b0` (`constant_product::output`). Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `unique_pairs` 891 to 892, `intervals_nonzero` 132 to 133.

No `ordered.ld` change.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Shape from [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), `main@6e6ac0fe` (`programs/pump/src/util/constant_product.rs`).
