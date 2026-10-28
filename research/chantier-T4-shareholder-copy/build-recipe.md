# Build recipe (chantier-T4-shareholder-copy)

1. Materialize the T4 workspace: s7p as in `research/chantier-T0/tools/build-recipe.md` (step 1), then from the workspace root:
   `patch -p1 < research/chantier-T4-with-account-name/source.patch`
   `patch -p1 < research/chantier-T4-whitelist-resync/source.patch`
2. Apply this packet on top:
   `patch -p1 < research/chantier-T4-shareholder-copy/source.patch`
3. Build the `ordered.ld` from the round34 base, the two prior T4 patches, then this one:
   `patch ordered.ld < research/chantier-T4-with-account-name/ordered-ld.patch`
   `patch ordered.ld < research/chantier-T4-whitelist-resync/ordered-ld.patch`
   `patch ordered.ld < research/chantier-T4-shareholder-copy/ordered-ld.patch`
4. Build, copy, strip and measure as in the T0 recipe steps 2 to 5, with `PUMP_TEXT_SCRIPT` pointing to the patched `ordered.ld`:
   `python3 research/chantier-T0/metric/measure.py DEPLOYED.so candidate.so symbols.so --dump m.json`.
   Expect matched 790 / exact 138 / original_windows 1035,
   candidate sha256 `3aa5b81f4d295c4f418150ad11d74b8f1c11f48c5196c8963ee2b4db160ced8a`,
   symbols sha256 `555414e5a72e1a0142fb605719b305d9226a19b4e533f7d91a99a6f5a67abd75`.
5. Drift solver: `python3 tools/drift_solver.py DEPLOYED.so symbols.so --cand-stripped candidate.so -o drift.json`.
   Expect `call_only_raw_fail` 221, `potential_if_delta0` 359, 75 nonzero intervals, root `0xe9e8` (delta -1240).
