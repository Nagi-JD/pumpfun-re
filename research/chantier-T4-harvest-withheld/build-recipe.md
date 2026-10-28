# Build recipe (chantier-T4-harvest-withheld)

1. Materialize the T4 workspace: s7p as in `research/chantier-T0/tools/build-recipe.md` (step 1), then from the workspace root:
   `patch -p1 < research/chantier-T4-with-account-name/source.patch`
   `patch -p1 < research/chantier-T4-whitelist-resync/source.patch`
   `patch -p1 < research/chantier-T4-shareholder-copy/source.patch`
   `patch -p1 < research/chantier-T4-pk7-borsh-serialize/source.patch`
   `patch -p1 < research/chantier-T4-pk8-setparams-serialize/source.patch`
   `patch -p1 < research/chantier-T4-transfer-with-seed/source.patch`
2. Apply this packet on top:
   `patch -p1 < research/chantier-T4-harvest-withheld/source.patch`
3. Build the `ordered.ld` from the round34 base, the six prior T4 patches, then this one:
   `patch ordered.ld < research/chantier-T4-with-account-name/ordered-ld.patch`
   `patch ordered.ld < research/chantier-T4-whitelist-resync/ordered-ld.patch`
   `patch ordered.ld < research/chantier-T4-shareholder-copy/ordered-ld.patch`
   `patch ordered.ld < research/chantier-T4-pk7-borsh-serialize/ordered-ld.patch`
   `patch ordered.ld < research/chantier-T4-pk8-setparams-serialize/ordered-ld.patch`
   `patch ordered.ld < research/chantier-T4-transfer-with-seed/ordered-ld.patch`
   `patch ordered.ld < research/chantier-T4-harvest-withheld/ordered-ld.patch`
4. Build, copy, strip and measure as in the T0 recipe steps 2 to 5, with `PUMP_TEXT_SCRIPT` pointing to the patched `ordered.ld`:
   `python3 research/chantier-T0/metric/measure.py DEPLOYED.so candidate.so symbols.so --dump m.json`.
   Expect matched 798 / exact 161 / original_windows 1035,
   candidate sha256 `b19d4c722b3a13281ee0aaca73f210eddab5b29fb1f3b8e8aa8fa2075fb1d6f2`,
   symbols sha256 `6c7c1e1ac73db0e31ea7de9826dbd39c1db92f73a73f9a5ff89b11b26aeaed6b`.
5. Drift solver: `python3 tools/drift_solver.py DEPLOYED.so symbols.so --cand-stripped candidate.so -o drift.json`.
   Expect `call_only_raw_fail` 205, `potential_if_delta0` 366, `intervals_nonzero` 84.
