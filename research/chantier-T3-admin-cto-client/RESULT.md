# chantier-T3: admin_cto and collect_creator_fee_v2 on the generated pump_amm / pump_fees clients, 16 windows matched

Refs T3 (#17, pump Anchor wrappers) and #19. Stacks on `chantier-T3-pump-quote-path` (#53).

## What the deployed program does

`admin_cto` reaches Pump AMM and Pump Fees through the Anchor `declare_program!` clients: `pump_amm::cpi::admin_cto_pool`, `pump_amm::cpi::collect_coin_creator_fee`, `pump_amm::cpi::transfer_creator_fees_to_pump_v2` and `pump_fees::cpi::admin_cto_sharing_config`, each with its generated `ToAccountMetas` / `ToAccountInfos` accounts struct. Its creator vault payouts go through the `collect_creator_fee_v2` helpers (`collect_v2::collect`, `transfer_native`, `transfer_tokens`, `transfer_vault_tokens`), which the `collect_creator_fee_v2` handler shares.

## Change

- `source.patch`:
  - `idls/pump_amm.json` and `idls/pump_fees.json` added; `lib.rs` lines 80 and 81 (blank) become `declare_program!(pump_amm);` and `declare_program!(pump_fees);`, so every other `lib.rs` line keeps its number.
  - `creator/admin_cto.rs` and `creator/collect_creator_fee.rs` replaced by the lalalune Round37 layout-30 versions: CPIs through the generated clients, and the shared `collect` / transfer helpers.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-pump-quote-path` | 828 | 161 | `2ec5872da9e3cee77a288ffbc6ceb5738fe5bb46fb4f98cd37a9d8ffb2f4c771` |
| this packet | **844** | **161** | `05797ad6e7113f2ba73ef84b5f5bb94382d63ed60516d6a7fb13e43224b920d5` |

Gained matched (16): `0x29518`, `0x2a8e8` (`collect_v2::execute`), `0x2b490` (`collect_v2::collect`), `0x90638`, `0x93898` (vault token transfers), `0xca628`, `0x10a0e0` (`pump_amm::cpi::admin_cto_pool`), `0x10b0b8` (`collect_coin_creator_fee`), `0x10e938` (`transfer_creator_fees_to_pump_v2`), `0x10fb38`, `0x1100f8`, `0x110d40`, `0x114d48` (generated accounts structs), `0x116718` (`pump_fees::cpi::admin_cto_sharing_config`), `0x118360`, `0x119c50`. Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `call_only_raw_fail` 205 to 219, `potential_if_delta0` 366 to 380, `unique_pairs` 827 to 843, `intervals_nonzero` 93 to 111.

No `ordered.ld` change.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Source ported from [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/claude-pump-integration-20261027/r37-layout-30` (`source/programs/pump`: `src/creator/admin_cto.rs`, `src/creator/collect_creator_fee.rs`, `idls/`), on top of `research/pump-r34-bodies-verified`.
