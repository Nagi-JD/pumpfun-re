# chantier-T1: trade v3 validate_trade and add Location lines, 2 windows matched

Refs T1 (SPECS §4.2, Location re-lines) and #19. Stacks on `chantier-T1-constant-product-lines` (#71).

## What the deployed program does

- `validate_trade(complete: u8, cashback: u64, allow_cashback: u64)` is out of line. It checks `BondingCurveComplete` on line 149 and `CashbackCoinNotSupported` on line 150 of a 29-byte source path. `allow_cashback` is tested as a full word and `cashback` as its low byte, so the cashback check is a single `require!(allow_cashback != 0 || cashback as u8 == 0)`.
- The v3 `add(a, b)` helper reports its `Overflow` on line 390 of the same path.

## Change

- `source.patch`:
  - new `v3_check.rs` (declared from `trade_v3.rs`) holds `validate_trade` with lines 149/150 and `add` with line 390. Same path length as `trade_v3.rs`.
  - `trade_v3.rs`: the old definitions become blank lines. The three call sites and the multi-hop call pass `u64` flags in the original form. Line counts unchanged.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T1-constant-product-lines` | 893 | 162 | `d37303deb66741617937fe7c63923a9f8a45db71fef16c9a9bbb775e52adf225` |
| this packet | **895** | **162** | `4e2ce8fe1b3c0a9c2e3347d9fc1240933f3d2693855fa0638099533efdb329d8` |

Gained matched (2): `0x7e0b0` (`validate_trade`), `0x81848` (`add`). Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `unique_pairs` 892 to 894, `intervals_nonzero` 133 to 135.

No `ordered.ld` change.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Shapes from [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), `main@6e6ac0fe` (`programs/pump/src/trade_v3.rs`, `programs/pump/src/multi_hop_curve_swap.rs`).
