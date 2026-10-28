# Build recipe (chantier-T4-refund-seeds)

1. Materialize the T4 workspace: s7p as in `research/chantier-T0/tools/build-recipe.md` (step 1), then from the workspace root:
   `patch -p1 < research/chantier-T4-with-account-name/source.patch`
   `patch -p1 < research/chantier-T4-whitelist-resync/source.patch`
   `patch -p1 < research/chantier-T4-shareholder-copy/source.patch`
   `patch -p1 < research/chantier-T4-pk7-borsh-serialize/source.patch`
   `patch -p1 < research/chantier-T4-pk8-setparams-serialize/source.patch`
   `patch -p1 < research/chantier-T4-transfer-with-seed/source.patch`
   `patch -p1 < research/chantier-T4-harvest-withheld/source.patch`
2. Apply this packet on top:
   `patch -p1 < research/chantier-T4-refund-seeds/source.patch`
3. Build the `ordered.ld` exactly as in `research/chantier-T4-harvest-withheld/build-recipe.md` (step 3). This packet's `ordered-ld.patch` is empty: no placement change.
4. Build, copy, strip and measure as in the T0 recipe steps 2 to 5, with `PUMP_TEXT_SCRIPT` pointing to that `ordered.ld`:
   `python3 research/chantier-T0/metric/measure.py DEPLOYED.so candidate.so symbols.so --dump m.json`.
   Expect matched 800 / exact 161 / original_windows 1035,
   candidate sha256 `10108020c61f670c4418da7850d2f5cf7a011adcdcd541f31a095c23ea5a9bb4`,
   symbols sha256 `e814eb629dd6306a5dc1283e7823a93a18414e473b098b670b2b9c37c10edfb1`.
5. Drift solver: `python3 tools/drift_solver.py DEPLOYED.so symbols.so --cand-stripped candidate.so -o drift.json`.
   Expect `call_only_raw_fail` 205, `potential_if_delta0` 366, `intervals_nonzero` 86.
