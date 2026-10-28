# chantier-T3: QuoteControl::validate_new_mint, 1 window matched

Refs T3 (#17, pump Anchor wrappers) and #19. Stacks on `chantier-T3-mayhem-params` (#60).

## What the deployed program does

- `QuoteControl::validate_new_mint` checks for a duplicate with an inline `mints.iter().position(..).is_some()` scan instead of calling the out-of-line `contains` helper.
- The module also carries `control_entry`, which reads the first matching reserve entry straight from the account bytes (discriminator, `u32` count at offset 104, 40-byte entries from offset 108) without building the mint vector.

## Change

- `source.patch`: `quote_control/state.rs` replaced by the lalalune Round37 layout-30 version.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-mayhem-params` | 881 | 162 | `133d57a00dc0ff4f8c9e50316a750bf96faf76cf76dc67f64256277d0d439166` |
| this packet | **882** | **162** | `4684fae3bcd76b9d9a3c51189d78722ee5ede9eef56780c20ec3344cc49924ff` |

Gained matched (1): `0x68bd8` (`QuoteControl::validate_new_mint`). Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `unique_pairs` 880 to 881, `intervals_nonzero` 125 to 126.

No `ordered.ld` change.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Source ported from [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/claude-pump-integration-20261027/r37-layout-30` (`source/programs/pump/src/quote_control/state.rs`), on top of `research/pump-r34-bodies-verified`.
