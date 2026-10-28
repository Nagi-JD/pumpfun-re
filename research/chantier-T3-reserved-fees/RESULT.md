# chantier-T3: `reserved_bonding_curve_fees` in `lib.rs`, 0xa2188 matched

Refs T3 (#17, pump Anchor wrappers) and #19. Stacks on `chantier-T3-fee-lines` (#47).

## What the deployed program does

The deployed window `0xa2188` (616 B, `reserved_bonding_curve_fees`) raises 6024 (`Overflow`) with an `anchor_lang::error::Location` built inline from `programs/pump/src/lib.rs` (length 24), `line` = **2562**. The candidate defined the function in `trade_types.rs`, so the window carried that path (length 32) and line 334.

## Change

- `source.patch`:
  - `lib.rs` lines 2559 to 2563 (previously blank): `#[inline(never)] pub fn reserved_bonding_curve_fees(curve: &trade_types::BondingCurve) -> Result<u64>`, body unchanged, with the `ok_or_else(|| error!(..Overflow))` on line 2562.
  - `trade_types.rs` line 331 re-exports it with `pub use crate::reserved_bonding_curve_fees;`, lines 332 to 335 become blank, so every other line in both files keeps its number and the caller in `trade_types` is unchanged.
- `ordered-ld.patch`: the function now lives at the crate root, which changes its mangled name. The selector is renamed in place, so placement order is unchanged.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-fee-lines` | 825 | 161 | `0c07f93cd4edf64bedc7810122c81e0a26a8da3598350d884c3edfe328f7cf61` |
| this packet | **826** | **161** | `7f0607972851da19a51aa02664d8cfbcd0a64736697ae6f31050268eda75c482` |

Gained matched: `0xa2188`. Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `call_only_raw_fail` 205 to 205, `potential_if_delta0` 366 to 366, `unique_pairs` 824 to 825, `intervals_nonzero` 92 to 92.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
