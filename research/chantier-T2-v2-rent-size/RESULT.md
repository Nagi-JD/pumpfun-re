# chantier-T2: v2 rent top-up ignores its size argument, 1 window matched

Refs T2 (SPECS §5, frame and argument-passing forms) and #19. Stacks on `chantier-T2-native-payments-pub`.

## What the deployed program does

- Window `0x3b598` is the v2 `native_payments::ensure_rent_exempt`. It takes four arguments; the first one is never read.
- The rent minimum is computed with `minimum_balance(0)` (a constant 0 in the deployed call), then the shared `transfer` tops the destination up to it.

## Change

- `source.patch` (line counts unchanged):
  - `v2_native_payments.rs` line 5: the parameter becomes `_size: usize`.
  - `v2_native_payments.rs` line 10: `minimum_balance(size)` becomes `minimum_balance(0)`.
- Every caller already passes 0, so behavior is unchanged.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T2-native-payments-pub` | 911 | 162 | `8cf8d6e15028b2533a1b82e7e895ffd81cf03deaa6ec4a3f6ec3d60e52989195` |
| this packet | **912** | **162** | `3abd4e44dd75b116f3b74d3460e2a66412297fdeebb814695b82d37393c9d487` |

Gained matched (1): `0x3b598` (v2 `native_payments::ensure_rent_exempt`). Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `unique_pairs` 910 to 911, `intervals_nonzero` 151 to 150.

No `ordered.ld` change.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Ported from [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), `main@6e6ac0fe` (`programs/pump/src/legacy_native_payments.rs`, `programs/pump/src/v2_native_payments.rs`).
