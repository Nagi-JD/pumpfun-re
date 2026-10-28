# chantier-T1: Global quote-mint and buyback-recipient Location lines, 3 windows matched

Refs T1 (SPECS §4.1, `lib.rs` re-lines) and #19. Stacks on `chantier-T1-v3-check-lines` (#72).

## What the deployed program does

- `Global::set_buyback_fee_recipients` reports `AllBuybackFeeRecipientsShouldBeNonZero` on line 1895 and `NotUniqueBuybackFeeRecipients` on line 1905 (a `require_neq!` over the 8 keys).
- `Global::add_quote_mint` reports on lines 1950, 1955, 1960 and 1971; the free-slot scan is a `for` loop that returns early and ends in `err!(QuoteMintWhitelistFull)`.
- `Global::remove_quote_mint` reports on lines 1975 and 1986 with the same loop shape ending in `err!(QuoteMintNotWhitelisted)`.

## Change

- `source.patch` (`lib.rs` only, line count unchanged):
  - `set_buyback_fee_recipients` moves down inside its existing `impl Global` block to lines 1893 to 1908.
  - `add_quote_mint` and `remove_quote_mint` move to a new `impl Global` block at lines 1947 to 1988, in the loop form.
  - The old quote-mint block at line 517 becomes `impl Global {}`, so later impl blocks keep their symbol hashes and `ordered.ld` placement.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T1-v3-check-lines` | 895 | 162 | `4e2ce8fe1b3c0a9c2e3347d9fc1240933f3d2693855fa0638099533efdb329d8` |
| this packet | **898** | **162** | `fe26b03c24e7f579348f18dd11f44868d034ea2aa7b5ece7f08202f73d27fe6b` |

Gained matched (3): `0x98af0` (`set_buyback_fee_recipients`), `0x9a190` (`add_quote_mint`), `0x9ac28` (`remove_quote_mint`). Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `unique_pairs` 894 to 897, `intervals_nonzero` 135 to 137.

No `ordered.ld` change.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Shapes from [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), `main@6e6ac0fe` (`programs/pump/src/lib.rs`).
