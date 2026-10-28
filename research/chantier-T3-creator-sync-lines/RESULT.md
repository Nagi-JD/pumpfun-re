# chantier-T3: set_creator, incentives, volume_sync and curve quote transfers, 7 windows matched

Refs T3 (#17, pump Anchor wrappers) and #19. Stacks on `chantier-T3-migrate-client` (#58).

## What the deployed program does

- `set_creator::set` and `set_creator::sync` read the curve and mint keys once, then branch with a `match` on the Metaplex `creators` list: the `Some` arm writes `creators[0]`, emits `SetMetaplexCreatorEvent` and returns early; the `None` arm sets the argument creator (`set`) or logs `Missing metaplex creators` (`sync`). Events are emitted by value.
- `incentives::execute` binds the mint key once and reuses it for the ATA derivation and the event.
- `volume_sync::execute` runs a separate `reset` helper, compares `total_claimed_tokens` before and after, and logs `No changes in accumulator for user={}` when they match, otherwise emits `SyncUserVolumeAccumulatorEvent`.
- `curve_quote_payments` passes the bonding curve signer seeds inline and adds the out-of-line `move_native` and `transfer_native_unchecked` lamport moves used by the quote transfers.

## Change

- `source.patch`: `set_creator.rs`, `incentives.rs`, `volume_sync.rs` and `curve_quote_payments.rs` replaced by the lalalune Round37 layout-30 versions.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-migrate-client` | 870 | 162 | `85a29bbacbc596dc8d24277090ac0840253246cadc3bd46f73981355f57c2698` |
| this packet | **877** | **162** | `d5a07ef1a8201d117b1c43ba383fded2591d261c9f13636ca5dc56af9948e897` |

Gained matched (7): `0x38fc0` (`set_creator::set`), `0x3a7b8` (`set_creator::sync`), `0x746a8` (`incentives::execute`), `0x7b250` (`volume_sync::execute`), `0x96d48`, `0x970f8` (`trade::quote_payments::transfer_to_owned`), `0x97580`. Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `call_only_raw_fail` 228 to 228, `potential_if_delta0` 390 to 390, `unique_pairs` 869 to 876, `intervals_nonzero` 123 to 125.

No `ordered.ld` change.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Source ported from [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/claude-pump-integration-20261027/r37-layout-30` (`source/programs/pump`: `src/set_creator.rs`, `src/incentives.rs`, `src/volume_sync.rs`, `src/curve_quote_payments.rs`), on top of `research/pump-r34-bodies-verified`.
