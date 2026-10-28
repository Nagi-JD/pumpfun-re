# Build recipe (chantier-T4-transfer-with-seed)

1. Materialize the T4 workspace: s7p as in `research/chantier-T0/tools/build-recipe.md` (step 1), then from the workspace root:
   `patch -p1 < research/chantier-T4-with-account-name/source.patch`
   `patch -p1 < research/chantier-T4-whitelist-resync/source.patch`
   `patch -p1 < research/chantier-T4-shareholder-copy/source.patch`
   `patch -p1 < research/chantier-T4-pk7-borsh-serialize/source.patch`
   `patch -p1 < research/chantier-T4-pk8-setparams-serialize/source.patch`
2. Apply this packet on top:
   `patch -p1 < research/chantier-T4-transfer-with-seed/source.patch`
3. Build the `ordered.ld` from the round34 base, the five prior T4 patches, then this one:
   `patch ordered.ld < research/chantier-T4-with-account-name/ordered-ld.patch`
   `patch ordered.ld < research/chantier-T4-whitelist-resync/ordered-ld.patch`
   `patch ordered.ld < research/chantier-T4-shareholder-copy/ordered-ld.patch`
   `patch ordered.ld < research/chantier-T4-pk7-borsh-serialize/ordered-ld.patch`
   `patch ordered.ld < research/chantier-T4-pk8-setparams-serialize/ordered-ld.patch`
   `patch ordered.ld < research/chantier-T4-transfer-with-seed/ordered-ld.patch`
4. Build, copy, strip and measure as in the T0 recipe steps 2 to 5, with `PUMP_TEXT_SCRIPT` pointing to the patched `ordered.ld`:
   `python3 research/chantier-T0/metric/measure.py DEPLOYED.so candidate.so symbols.so --dump m.json`.
   Expect matched 794 / exact 148 / original_windows 1035,
   candidate sha256 `31162d65ed5a56fb60c2beaa62b754b758516411b7b07149c96616bf578f8ae2`,
   symbols sha256 `f6401e8a92dba8990a2c2003632c2a1a944bc47d8d720b5ae8ced3da3ade22a9`.
5. Drift solver: `python3 tools/drift_solver.py DEPLOYED.so symbols.so --cand-stripped candidate.so -o drift.json`.
   Expect `call_only_raw_fail` 215, `potential_if_delta0` 363, `intervals_nonzero` 86.
