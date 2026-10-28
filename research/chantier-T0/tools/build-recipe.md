# Build recipe (chantier-T0)

Solver PR: program source is the s7p baseline. Rebuild to refresh measure artifacts, then run the solver.

## Native s7p candidate

1. Materialize Round34 / s7p workspace (pump program + `research/pump-r34-bodies-verified` patch stack, `ordered.ld`, text-layout wrappers from `research/pump-r34-race`).
2. Host rustc shim reporting `aarch64-apple-darwin`; compile with platform-tools v1.44 `cargo build --release --target sbf-solana-solana --locked --jobs 2`.
3. Env: `RUSTC_WRAPPER=pump_text_layout_rustc.py`, `PUMP_TEXT_PHYSICAL_WRAPPER`, `PUMP_TEXT_LINKER` = v1.44 `rust-lld`, `PUMP_TEXT_SCRIPT=ordered.ld`, `CARGO_TARGET_SBF_SOLANA_SOLANA_RUSTFLAGS=-Zremap-cwd-prefix=`.
4. Copy `pump_recovered.so` → `s7p-symbols.so`. Strip with platform-tools v1.52 `llvm-objcopy --strip-all` → `s7p-candidate.so`.
5. Measure: `python3 research/chantier-T0/metric/measure.py DEPLOYED.so s7p-candidate.so s7p-symbols.so --dump measure-s7p.json`.
   Expect summary matched 786 / exact 137 / original_windows 1035.

## Drift solver

```
python3 tools/drift_solver.py \
  evidence/original/pump/deployed.so \
  s7p-symbols.so \
  --cand-stripped s7p-candidate.so \
  -o research/chantier-T0/drift-s7p-ref.json
```

Expect `summary.call_only_raw_fail` 218, `summary.potential_if_delta0` 355,
`root.dep_left` `0x2930` with `delta` -232 (unmatched deployed 232 B at `0x2bc0`).
