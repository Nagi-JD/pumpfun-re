# fees-extend-stack-582

Fees program stacked onto upstream `research/fees-extend-integration` ([lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) MIT, main `0cc61d6`, PR #278). That checkpoint composes Extend with the accepted ATA and Withdraw recoveries.

## Measured window metric

| | prior (`fees-progid-579-raw`, exact env) | after (`fees-extend-integration` qualified symbols) |
|---|---:|---:|
| matched | 579 | **582** |
| raw | 198 | **200** |
| unmatched | 6 | **3** |

### Windows gained
- `76384` / 6312 B / `extend_fee_config` (deployed)
- `137280` / 10664 B / `claim_v2` (deployed)
- `249264` / 8000 B / `withdraw` (deployed)

`raw_lost` empty. Prior matched windows retained.

### Remaining unmatched
- `120816` / 6960 B / `sweep_buyback`
- `147944` / 15976 B / `crank_donation`
- `163920` / 13800 B / `create_donation`

Evidence: `measure-before-579.json`, `measure-extend-582.json` (window_map of packet `builds/candidate/symbols.so` against `evidence/original/pump_fees/deployed.so`). Upstream `comparison.json`: `normalized_matches=582`, `raw_matches=200`, `remaining_original_functions=[120816,147944,163920]`, `gained_original=[76384]`, `raw_lost=[]`.

## Stacking step
1. Checkout `lalalune/pumpfun-source` at a revision with `research/fees-extend-integration` (main `0cc61d6`).
2. `python3 -B research/fees-extend-integration/verify.py`
3. `python3 -B research/fees-extend-integration/verify.py --materialize /abs/new/source` (parent `research/fees-ata-prefix-integration`).
4. Qualified build: Linux platform-tools **v1.44** direct `cargo rustc`, paths `/work/next649` + vendor `/work/next637/vendor/used-public`, strip with v1.52 `llvm-objcopy --strip-all` (see packet `builds/candidate/launch.json`, `linker.sh`, `layout/ordered.ld`).
5. Measure with `tools/measure_local.py`. Expect 582 / 200 and the three remaining addresses above.

The ATA `needs_create` local from `let_bind.patch` is already absorbed in the ATA parent of this checkpoint.

## Attribution
Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/fees-extend-integration`.
