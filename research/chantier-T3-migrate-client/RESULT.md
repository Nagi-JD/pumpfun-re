# chantier-T3: migrate and migrate_v2 on the generated pump_amm client, 26 windows matched

Refs T3 (#17, pump Anchor wrappers) and #19. Stacks on `chantier-T3-admin-cto-client` (#56).

## What the deployed program does

`migrate` and `migrate_v2` build the Pump AMM pool through the Anchor `declare_program!(pump_amm)` client: `pump_amm::cpi::create_pool` and `pump_amm::cpi::init_boost`, each with its generated `ToAccountMetas` / `ToAccountInfos` accounts struct. Around those CPIs, `migrate` runs `create_pool_token_account`, `fund_quote_token_account`, `create_pool`, `init_pump_amm_boost` and `close_pool_authority_token_account`; `migrate_v2` runs `transfer_base_to_pool_authority`, `fund_quote_token_account_v2`, `create_pool`, `close_pool_authority_account`, `close_lp_account` and `burn_lp_tokens`. Native SOL legs go through `migration_native_payments`.

## Change

- `source.patch`: `migrate.rs`, `migrate_v2.rs` and `migration_native_payments.rs` replaced by the lalalune Round37 layout-30 versions (CPIs through the generated `pump_amm` client, per-step helpers as above).

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-admin-cto-client` | 844 | 161 | `05797ad6e7113f2ba73ef84b5f5bb94382d63ed60516d6a7fb13e43224b920d5` |
| this packet | **870** | **162** | `85a29bbacbc596dc8d24277090ac0840253246cadc3bd46f73981355f57c2698` |

Gained matched (26): `0x414c0` (`migrate::create_pool_token_account`), `0x42618`, `0x43060` (`migrate::fund_quote_token_account`), `0x43ea0` (`migrate::create_pool`), `0x45fa0` (`migrate::init_pump_amm_boost`), `0x47d00`, `0x47e28`, `0x48128` (`migrate::close_pool_authority_token_account`), `0x48e10`, `0x4e208` (`migrate_v2::transfer_base_to_pool_authority`), `0x4eb28` (`migrate_v2::fund_quote_token_account_v2`), `0x502f0` (`migrate_v2::create_pool`), `0x524f0`, `0x54c90`, `0x54f30` (`migrate_v2` close helpers), `0x55d30` (`migrate_v2::burn_lp_tokens`), `0xd5af0` (`MigrateV2` `try_accounts`), `0x109488`, `0x10c0b8` (`pump_amm::cpi::create_pool`), `0x10d638` (`pump_amm::cpi::init_boost`), `0x1113c8`, `0x112220`, `0x1133c8` (generated accounts structs), `0x113f00`, `0x12ba48`, `0x17c0f0`. Gained raw (1): `0x17c0f0`. Lost matched: none. Lost raw: none.

Drift solver: `call_only_raw_fail` 219 to 228, `potential_if_delta0` 380 to 390, `unique_pairs` 843 to 869, `intervals_nonzero` 111 to 123.

No `ordered.ld` change.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Source ported from [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/claude-pump-integration-20261027/r37-layout-30` (`source/programs/pump`: `src/migrate.rs`, `src/migrate_v2.rs`, `src/migration_native_payments.rs`), on top of `research/pump-r34-bodies-verified`.
