# chantier-T2: Token-2022 extension helpers in their own crate, migrate_v2 execute and boost, 5 windows matched, 1 raw

Refs T2 (SPECS §5) and #19. Stacks on `chantier-T2-v2-rent-size`.

## What the deployed program does

- The Token-2022 mint parser `get_transfer_fee_config` at `0x17c850` is linked from a separate object, after the `pump_recovered` code. It reads the TransferFeeConfig TLV entry natively, without `StateWithExtensions::unpack`.
- `transfer_fee_recovered::get_transfer_fee` (`0x94908`) checks the mint owner, calls that parser and selects the epoch fee. `calculate_fee` (`0x94e28`) follows it.
- `migrate_v2::execute` (`0x49888`) and `migrate_v2::init_pump_amm_boost_v2` (`0x52660`) use the layout carried in this packet.

## Change

- `source.patch`:
  - New crate `programs/pump/pump-token-ext` (`Fee`, `TransferFeeConfig`, `get_transfer_fee_config`, `quote_extensions_supported`), added as a path dependency in `programs/pump/Cargo.toml` and in `Cargo.lock`.
  - `v3_native_transfer_fee.rs` re-exports `Fee`, `TransferFeeConfig` and `get_transfer_fee_config` from the crate.
  - `util/transfer_fee.rs`: `get_transfer_fee` reads the mint through the native parser, ahead of `calculate_fee`.
  - `migrate_v2.rs`: `execute`, `init_pump_amm_boost_v2`, `qsize` and `pay_migration_fee` in the deployed shape. The `quote_extensions` helper and its `StateWithExtensions::<Mint>::unpack` are removed.
- `ordered.ld` (full file) and `ordered-ld.patch` (against the `chantier-T2-v2-rent-size` `ordered.ld`):
  - Adding the crate renames the root codegen-unit object (`3ea6595f33b540c7-cgu.0` to `7e6f3912f6d83f89-cgu.0`) and the incremental object (`17klp79ozsiufwnj` to `4iacj00wxtou68k5`). Selectors are rewritten to the new object names.
  - Selectors whose symbol hash changed are rebound to the new symbol by normalized body hash, then size, in deployed slot order.
  - Without the object rename, `alloc::fmt::format`, `String::push`, the `ToString` pair at `0xa938`/`0xaa60` and the 7 `RawVec::grow_one` at `0xe018`..`0xe858` fall to the `*(.text*)` tail, and raw `0xa7e0`, `0xea68` and `0xf130` are lost.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T2-v2-rent-size` | 912 | 162 | `3abd4e44dd75b116f3b74d3460e2a66412297fdeebb814695b82d37393c9d487` |
| this packet | **917** | **163** | `76159da3a2421b4da87934845d356cd6f7b72af8646720762553bd2cd357d300` |

Gained matched (5): `0x49888` (`migrate_v2::execute`), `0x52660` (`migrate_v2::init_pump_amm_boost_v2`), `0x94908` (`get_transfer_fee`), `0x94e28` (`calculate_fee`), `0x17c850` (`pump_token_ext::get_transfer_fee_config`). Gained raw (1): `0x17c850`. Lost matched: none. Lost raw: none.

Drift solver: `unique_pairs` 911 to 916, `intervals_nonzero` 150 to 88, `potential_if_delta0` 401 to 402.

A clean build (empty target directory) gives the same candidate and symbols sha256.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Ported and adapted from [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), `main@6e6ac0fe` (`research/claude-mega-run-archive-20261028/pump/deliveries/mg-P-cash-01/src`: `pump-token-ext/src/lib.rs`, `src/migrate_v2.rs`, `src/util/transfer_fee.rs`).
