# Build recipe (chantier-T3-add3)

1. Materialize the `chantier-T2-token-ext-crate` workspace and its `ordered.ld` as in `research/chantier-T2-token-ext-crate/build-recipe.md` (steps 1 to 3).
2. Apply this packet from the workspace root:
   `patch -p1 < research/chantier-T3-add3/source.patch`
3. From the directory holding `ordered.ld`:
   `patch -p1 < research/chantier-T3-add3/ordered-ld.patch`
   The result is identical to `research/chantier-T3-add3/ordered.ld`.
4. Build, copy, strip and measure as in the T0 recipe steps 2 to 5, with `PUMP_TEXT_SCRIPT` pointing to that `ordered.ld`:
   `python3 research/chantier-T0/metric/measure.py DEPLOYED.so candidate.so symbols.so --dump m.json`.
   Expect matched 918 / exact 163 / original_windows 1035 / candidate_windows 1050,
   candidate sha256 `f7f04ff6d9d5fbd23d11e3b3cfe5b94d1febd9f826f1c7b1f9368598e1b3da45`,
   symbols sha256 `9dc544c133a7008e73a82153246ec5b65bd8a6a7216309f5f7b761896b4e4be7`.
5. Drift solver: `python3 tools/drift_solver.py DEPLOYED.so symbols.so --cand-stripped candidate.so -o drift.json`.
   Expect `call_only_raw_fail` 239, `potential_if_delta0` 402, `intervals_nonzero` 89.
