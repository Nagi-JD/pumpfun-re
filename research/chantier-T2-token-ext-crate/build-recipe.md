# Build recipe (chantier-T2-token-ext-crate)

1. Materialize the `chantier-T2-v2-rent-size` workspace and its `ordered.ld` as in `research/chantier-T2-v2-rent-size/build-recipe.md` (steps 1 to 3).
2. Apply this packet from the workspace root (creates `programs/pump/pump-token-ext/`):
   `patch -p1 < research/chantier-T2-token-ext-crate/source.patch`
3. From the directory holding `ordered.ld`:
   `patch -p1 < research/chantier-T2-token-ext-crate/ordered-ld.patch`
   The result is identical to `research/chantier-T2-token-ext-crate/ordered.ld`.
4. Build, copy, strip and measure as in the T0 recipe steps 2 to 5, with `PUMP_TEXT_SCRIPT` pointing to that `ordered.ld` (`cargo build --locked`, the patched `Cargo.lock` lists `pump-token-ext`):
   `python3 research/chantier-T0/metric/measure.py DEPLOYED.so candidate.so symbols.so --dump m.json`.
   Expect matched 917 / exact 163 / original_windows 1035 / candidate_windows 1049,
   candidate sha256 `76159da3a2421b4da87934845d356cd6f7b72af8646720762553bd2cd357d300`,
   symbols sha256 `caf2798a784d02e72837e8eb859439deb5c7fa26ddbf186c024afbbd9fd8a948`.
5. Drift solver: `python3 tools/drift_solver.py DEPLOYED.so symbols.so --cand-stripped candidate.so -o drift.json`.
   Expect `call_only_raw_fail` 239, `potential_if_delta0` 402, `intervals_nonzero` 88.
