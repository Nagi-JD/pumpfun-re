# chantier-T1: bonding-curve sell quote and fee market cap Location lines, 2 windows matched

Refs T1 (SPECS §4.1, `lib.rs` re-lines) and #19. Stacks on `chantier-T1-global-lib-lines` (#73).

## What the deployed program does

- `sell_quote` is an out-of-line helper that reports `DivisionByZero` on `lib.rs` line 2454 through a `checked_div` on the `u128` product of the quote reserves and the input amount.
- `buy_fee_market_cap` is an out-of-line helper that reports `DivisionByZero` on `lib.rs` line 2481; it selects `token_total_supply` in mayhem mode and the mint supply otherwise, then divides by the virtual token reserves with `checked_div`.

## Change

- `source.patch` (line counts unchanged):
  - `lib.rs`: new free functions `sell_quote` (lines 2451 to 2455) and `buy_fee_market_cap` (lines 2478 to 2482), both `#[inline(never)]`.
  - `trade_v3.rs`: the sell path quotes through `crate::sell_quote`; the local `buy_fee_market_cap` is replaced by an import of the `lib.rs` helper.
  - Free functions rather than new `impl` blocks, so later impl blocks keep their symbol hashes and `ordered.ld` placement.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T1-global-lib-lines` | 898 | 162 | `fe26b03c24e7f579348f18dd11f44868d034ea2aa7b5ece7f08202f73d27fe6b` |
| this packet | **900** | **162** | `c439531883071d34cde4f913942791afb2d0851ae846694c4ea753e4975c8510` |

Gained matched (2): `0xa0538` (`sell_quote`), `0xa08f8` (`buy_fee_market_cap`). Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `unique_pairs` 897 to 899, `intervals_nonzero` 137 to 139.

No `ordered.ld` change.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Shapes from [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), `main@6e6ac0fe` (`programs/pump/src/lib.rs`).
