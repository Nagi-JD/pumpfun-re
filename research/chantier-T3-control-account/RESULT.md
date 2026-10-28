# chantier-T3: create_v2 quote control read through control_account, 1 window matched

Refs T3 (#17, pump Anchor wrappers) and #19. Stacks on `chantier-T3-constant-product` (#67).

## What the deployed program does

- When `create_v2` admits a non-whitelisted quote mint, it reads the quote-control entry through an out-of-line `control_account(account, mint)`. That helper borrows the account data and returns `control_entry(&data, mint)`.

## Change

- `source.patch`:
  - `pump_quote.rs`: adds `control_account` on a blank line.
  - `create_v2.rs`: calls it in place of the inline borrow. Line counts unchanged.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-constant-product` | 891 | 162 | `42919ff8bcdca25b566994e19c6ec96b3a6c48ed0c92e7f0873c2b2fa432d4d7` |
| this packet | **892** | **162** | `1ed4c63fe6c9a70f60875c667b2dd694a173f801cbd255b4cb0b39da0575fb38` |

Gained matched (1): `0x18568` (`control_account`). Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `unique_pairs` 890 to 891, `intervals_nonzero` 131 to 132.

No `ordered.ld` change.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Ported from [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), `main@6e6ac0fe` (`programs/pump/src/create_v2.rs`).
