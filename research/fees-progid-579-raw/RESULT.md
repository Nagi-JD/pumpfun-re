# fees-progid-579-raw

`let_bind.patch` built in a byte-exact reproduction of the upstream `research/fees-program-id-references` container environment, run natively in WSL Linux with no podman.

## Environment check: unchanged upstream sources
The native build gives symbols sha `af4c0e7c6e4d6215ac5fdac73df3d33252d74c3b0d6d589de97dd28e28d53c0b` and stripped candidate sha `0d7bde7b97959ca45a32aa1a3b350188afb120153637de401ae02ac4307b1de3`. Both are **identical** to upstream `builds/candidate/result.json`. `-C metadata=116e46ff7f3ee342` and the `--extern` rlib hashes also match. Measure: 578 / raw 198 / locations 182 / edges 3935.

## Result
| | upstream (exact) | + let_bind |
|---|---|---|
| matched | 578 | **579** |
| raw | 198 | 198 |
| equal_locations | 182 | 183 |
| equal_edges | 3935 | 3965 |

Gained: 243184 (admit_associated_token_account), matched but not raw-exact. Lost: none.
Unmatched (6): 76384, 120816, 137280, 147944, 163920, 249264.
let_bind build shas are in SHA256SUMS.

## Exact layout (everything is path-sensitive)
- `/work/sdk` -> platform-tools v1.44 (rustc 1.79.0-dev, LLVM 18.1.7). A symlink is fine here.
- `/cargo`: CARGO_HOME. It must be a **real directory, not a symlink**. `-Zremap-cwd-prefix=` trims registry paths only when the canonical working directory of rustc equals the `/cargo/...` prefix of the file paths. Through a symlink, the `/cargo/registry/...` panic paths stay untrimmed in .rodata (+1014 bytes, raw 198 -> 141).
- `/work/target`: CARGO_TARGET_DIR. Start from clean.
- `/work/next641/id578-program-ids-qualified`: sources from `verify.py --materialize`. Keep this exact path, because it feeds the crate metadata hash. Patch in place.
- `/work/next637/vendor/used-public`: the packet `vendor/` directory.
- `linker.sh` and `ordered.ld` verbatim (sha matches launch.json).
- Run `tools/build-exact.sh id578-program-ids-qualified`. It runs the cargo command and environment from controller.py without podman, then strips with v1.52 llvm-objcopy.
