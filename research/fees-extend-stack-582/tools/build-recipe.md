# Build recipe (fees-extend-stack-582)

- Platform-tools: v1.44, direct `cargo rustc` (path-sensitive `/work/next649` sources, `/work/next637/vendor/used-public`).
- Strip: v1.52 `llvm-objcopy --strip-all`.
- Materialize: `python3 -B research/fees-extend-integration/verify.py --materialize DIR`
- Linker: packet `layout/ordered.ld` and `linker.sh` from `builds/candidate/`.
- Exact rustc/cargo argv and remaps: packet `builds/candidate/launch.json`.
