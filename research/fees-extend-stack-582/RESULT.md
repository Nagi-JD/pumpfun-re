# fees-extend-stack-582

Fees program stacked onto upstream `research/fees-extend-integration` ([lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) MIT, main `0cc61d6`, PR #278). That checkpoint composes Extend with the accepted ATA and Withdraw recoveries.

Build is native from source: materialized `fees-extend-integration` workspace, platform-tools v1.44 direct `cargo rustc` (target `sbpf-solana-solana`), strip with v1.52 `llvm-objcopy --strip-all`. The deployed `deployed.so` is the comparison target for window counts.

## Measured window metric

| | prior (`fees-progid-579-raw`, exact env) | after (native rebuild of extend stack) |
|---|---:|---:|
| matched | 579 | **582** |
| raw | 198 | **200** |
| unmatched | 6 | **3** |

### Windows gained
- `76384` / 6312 B / `extend_fee_config` (deployed)
- `137280` / 10664 B / `claim_v2` (deployed)
- `249264` / 8000 B / `withdraw` (deployed)

`raw_lost` empty. Prior matched windows retained.

Native symbols sha256 `ca9e6a933d1406743689f7bad609ce6b5e95ea91c064e0233cbd4db100afb335`, candidate sha256 `7fdeefd6a7f36e1d312b7429f826fe4c5118440a059ee3fb49399b8799d3fc3d` (byte-identical to the upstream qualified artifacts).

### Remaining unmatched
- `120816` / 6960 B / `sweep_buyback`
- `147944` / 15976 B / `crank_donation`
- `163920` / 13800 B / `create_donation`

Evidence: `measure-before-579.json`, `measure-extend-582.json` / `measure-native-582.json` (window_map of the native symbols against `evidence/original/pump_fees/deployed.so`).

## Stacking step
1. Checkout `lalalune/pumpfun-source` at a revision with `research/fees-extend-integration` (main `0cc61d6`).
2. `python3 -B research/fees-extend-integration/verify.py`
3. `python3 -B research/fees-extend-integration/verify.py --materialize DIR` (parent `research/fees-ata-prefix-integration`).
4. Arrange the path-sensitive layout required by upstream `builds/candidate/launch.json` (source root, vendor `used-public`, `CARGO_HOME`, `CARGO_TARGET_DIR`, SDK symlink to platform-tools v1.44).
5. Direct `cargo rustc --release --target sbpf-solana-solana --locked --lib` with the remaps and linker script from the materialize output; strip with v1.52 `llvm-objcopy --strip-all`.
6. Measure with `tools/measure_local.py`. Expect 582 / 200 and the three remaining addresses above.

The ATA `needs_create` local from `let_bind.patch` is already absorbed in the ATA parent of this checkpoint.

## Attribution
Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/fees-extend-integration`.
