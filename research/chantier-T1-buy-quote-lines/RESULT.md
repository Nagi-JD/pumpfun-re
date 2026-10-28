# chantier-T1: bonding-curve buy quote Location lines, 1 window matched

Refs T1 (SPECS §4.1, `lib.rs` re-lines) and #19. Stacks on `chantier-T1-buyback-validate-lines` (#76).

## What the deployed program does

- `buy_quote` lives in the `lib.rs` bonding-curve math region as an out-of-line helper returning `u128`: `Overflow` on line 2428 (the `checked_sub` of the input amount from the virtual token reserves) and `DivisionByZero` on line 2430.
- The legacy buy entry point narrows the `u128` quote to `u64` with a `Truncation` error at the call site.

## Change

- `source.patch` (line counts unchanged):
  - `lib.rs`: new `#[inline(never)]` free function `buy_quote` at lines 2424 to 2432; the legacy buy call site narrows the result with `u64::try_from`.
  - `fee_cpi.rs`: the local `buy_quote` is replaced by a re-export of the `lib.rs` helper.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T1-buyback-validate-lines` | 901 | 162 | `d2233d419a93d344aeb329ac3d40a8918b73b7aa43f2c8bbba4d8ac624eeb9e9` |
| this packet | **902** | **162** | `0a7e646406dd161973c04bb00ab8c60a339f55aca2b81817e1d615df59fda0cb` |

Gained matched (1): `0xa0070` (`buy_quote`). Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `unique_pairs` 900 to 901, `intervals_nonzero` 140 to 140.

No `ordered.ld` change.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Shapes from [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), `main@6e6ac0fe` (`programs/pump/src/lib.rs`, `fee_cpi.rs`).
