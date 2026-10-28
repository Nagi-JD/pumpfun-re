# chantier-T2: public native-payments helpers keep their reference arguments, 2 windows matched

Refs T2 (SPECS §5, frame and argument-passing forms) and #19. Stacks on `chantier-T2-fees-decl-line` (#83).

## What the deployed program does

- The rent top-up helper and the System transfer helper are public items reachable from the crate root.
- With `crate-type = ["cdylib", "lib"]` and `lto = false`, public reachable functions stay exported, so their reference arguments are passed as written: `transfer` (window `0x8cc58`) receives `payer` as `&Signer` and reads the inner `AccountInfo` itself.
- The legacy `ensure_rent_exempt` (window `0x3b738`) passes `&Signer` straight through to that shared `transfer`.

## Change

- `source.patch` (line counts unchanged):
  - `buy.rs` line 35 and `buy_v2.rs` line 1040: `pub(crate) mod native_payments;` becomes `pub mod native_payments;`.
  - `legacy_native_payments.rs` and `v2_native_payments.rs`: `ensure_rent_exempt` and `transfer` become `pub fn`.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T2-fees-decl-line` | 909 | 162 | `d2cfe83bf22c8d20564cab6c3fa8ef3755d530ec868a6eb9216b1fbf93d2da2a` |
| this packet | **911** | **162** | `8cf8d6e15028b2533a1b82e7e895ffd81cf03deaa6ec4a3f6ec3d60e52989195` |

Gained matched (2): `0x3b738` (legacy `native_payments::ensure_rent_exempt`), `0x8cc58` (`native_payments::transfer`). Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `unique_pairs` 908 to 910, `intervals_nonzero` 149 to 151.

No `ordered.ld` change.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Ported from [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), `main@6e6ac0fe` (`programs/pump/src/legacy_native_payments.rs`, `programs/pump/src/v2_native_payments.rs`).
