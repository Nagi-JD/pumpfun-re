# Build recipe (fees-extend-stack-582)

Native from source (materialized workspace).

- Materialize: `python3 -B research/fees-extend-integration/verify.py --materialize DIR`
- Layout: the path-sensitive remaps from upstream `builds/candidate/launch.json` (source root, vendor `anchor-attribute-program` under `used-public`, real `CARGO_HOME` directory, shared `CARGO_TARGET_DIR`, SDK symlink to platform-tools v1.44).
- Build: direct `cargo rustc --release --target sbpf-solana-solana --locked --lib` with `RUSTFLAGS=-Zremap-cwd-prefix=` and the three `pump-fees-math` remaps from `launch.json`; linker `linker.sh` + `ordered.ld`.
- Strip: platform-tools v1.52 `llvm-objcopy --strip-all`.
- Measure: `python3 tools/measure_local.py <symbols.so>` against `evidence/original/pump_fees/deployed.so`.
