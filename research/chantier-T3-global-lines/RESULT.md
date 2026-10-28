# chantier-T3: `Global` account and `set_buyback_basis_points` lines, 0x15fdd0 and 0x98210 matched

Refs T3 (#17, pump Anchor wrappers) and #19. Stacks on `chantier-T3-program-lines` (#45).

## What the deployed program does

| window | size | function | error | deployed line | candidate line |
|---|---:|---|---:|---:|---:|
| `0x15fdd0` | 728 | `Global` `try_deserialize` | 3002 | 1815 | 183 |
| `0x98210` | 552 | `Global::set_buyback_basis_points` | 6060 | 1870 | 504 |

Both build the `anchor_lang::error::Location` inline from `programs/pump/src/lib.rs` (length 24). Line 1815 is the `#[account]` attribute of `pub struct Global`, line 1870 the `require!` of `set_buyback_basis_points`.

## Change

- `source.patch`, `lib.rs` only:
  - `#[account] pub struct Global { .. }` moves from lines 183 to 215 to lines 1815 to 1847.
  - The `impl Global` block holding `set_buyback_basis_points` and `set_buyback_fee_recipients` moves from lines 501 to 515 to lines 1867 to 1881, so the `require!` sits on line 1870.
  - Both destinations were blank lines and the vacated lines become blank, so every other line in the file keeps its number. Fields, field order, attributes and bodies are unchanged.
- `ordered-ld.patch`: moving the `impl Global` block changes the impl order of the crate root, which changes the hash of 6 mangled names (`Global::set_buyback_basis_points`, `Global::set_buyback_fee_recipients`, `Global::add_quote_mint`, `Global::remove_quote_mint`, and `BorshSerialize::serialize` of `Pk7` and `Pk8`). Each selector is renamed in place to the new name, so placement order is unchanged.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-program-lines` | 821 | 161 | `3873b5d5d02b10138d9565ead76eabe1d4f93ee4ae61efb72049517cdffeb8f5` |
| this packet | **823** | **161** | `25bde639ab252c3565dc0ed32ca6efa77980c52aa66289419e7b676b8f04f1d9` |

Gained matched: `0x15fdd0`, `0x98210`. Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `call_only_raw_fail` 205 to 205, `potential_if_delta0` 366 to 366, `unique_pairs` 820 to 822, `intervals_nonzero` 91 to 91.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
