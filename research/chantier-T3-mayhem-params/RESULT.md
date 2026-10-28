# chantier-T3: set_mayhem_virtual_params, 4 windows matched

Refs T3 (#17, pump Anchor wrappers) and #19. Stacks on `chantier-T3-creator-sync-lines` (#59).

## What the deployed program does

- `SetMayhemVirtualParams` takes `sol_vault_authority` as a plain `AccountInfo`, `global` as an unboxed `Account<Global>` and `token_program` as `Program<Token2022>`, so the accounts `exit` path and the `__global` wrapper carry no box or interface checks.
- `execute` passes `global.initial_real_token_reserves` and `mayhem_token_vault.amount` straight into `BondingCurve::sync_virtual_quote_reserves` and emits the event by value.
- `sync_virtual_quote_reserves` builds the numerator with `checked_add` and returns `PumpError::Overflow` on wrap.

## Change

- `source.patch`: `mayhem_virtual_params.rs` replaced by the lalalune Round37 layout-30 version.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-creator-sync-lines` | 877 | 162 | `d5a07ef1a8201d117b1c43ba383fded2591d261c9f13636ca5dc56af9948e897` |
| this packet | **881** | **162** | `133d57a00dc0ff4f8c9e50316a750bf96faf76cf76dc67f64256277d0d439166` |

Gained matched (4): `0xa23f0` (`BondingCurve::sync_virtual_quote_reserves`), `0xcf510` (`SetMayhemVirtualParams::exit`), `0x1255a8` (`__global::set_mayhem_virtual_params`), `0x137fc0` (`pump_recovered::set_mayhem_virtual_params`). Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `unique_pairs` 876 to 880, `intervals_nonzero` 125 to 125.

No `ordered.ld` change.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Source ported from [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/claude-pump-integration-20261027/r37-layout-30` (`source/programs/pump/src/mayhem_virtual_params.rs`), on top of `research/pump-r34-bodies-verified`.
