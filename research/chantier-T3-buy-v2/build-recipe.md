# Build recipe (chantier-T3-buy-v2)

1. Materialize the 802/161 workspace and its `ordered.ld` as in `research/chantier-T4-close-burn-helpers/build-recipe.md` (steps 1 to 3).
2. Apply this packet:
   `patch -p1 < research/chantier-T3-buy-v2/source.patch`
3. Build, copy, strip and measure as in the T0 recipe steps 2 to 5, with `PUMP_TEXT_SCRIPT` pointing to that `ordered.ld`:
   `python3 research/chantier-T0/metric/measure.py DEPLOYED.so candidate.so symbols.so --dump m.json`.
   Expect matched 803 / exact 161 / original_windows 1035,
   candidate sha256 `85dc4036a846148e10d6f1c6724f3ca9caef386b9b6388b60207dd6fba07fd28`,
   symbols sha256 `e81855b179c90146c713b48551c7b4f911a0c4123f908630a94394378b8712f2`.
4. Drift solver: `python3 tools/drift_solver.py DEPLOYED.so symbols.so --cand-stripped candidate.so -o drift.json`.
   Expect `call_only_raw_fail` 205, `potential_if_delta0` 366, `intervals_nonzero` 88.
