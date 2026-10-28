# Build recipe (chantier-T3-create-v2)

1. Materialize the 802/161 workspace and its `ordered.ld` as in `research/chantier-T4-close-burn-helpers/build-recipe.md` (steps 1 to 3).
2. Apply the earlier T3 packets from the workspace root, in order:
   `patch -p1 < research/chantier-T3-buy-v2/source.patch`
   `patch -p1 < research/chantier-T3-sell-v2/source.patch`
   `patch -p1 < research/chantier-T3-sell-v3/source.patch`
3. Apply this packet:
   `patch -p1 < research/chantier-T3-create-v2/source.patch`
4. Build, copy, strip and measure as in the T0 recipe steps 2 to 5, with `PUMP_TEXT_SCRIPT` pointing to that `ordered.ld`:
   `python3 research/chantier-T0/metric/measure.py DEPLOYED.so candidate.so symbols.so --dump m.json`.
   Expect matched 807 / exact 161 / original_windows 1035,
   candidate sha256 `bde51f7da35b05518440b12b4f6a729840c7b534622dda78beaac8919b1cd73e`,
   symbols sha256 `76c423239b2d2c8350ebd570fa6f8469f9f9f20f7bd30b0b09f1d43f2ad22a96`.
5. Drift solver: `python3 tools/drift_solver.py DEPLOYED.so symbols.so --cand-stripped candidate.so -o drift.json`.
   Expect `call_only_raw_fail` 205, `potential_if_delta0` 366, `intervals_nonzero` 88.
