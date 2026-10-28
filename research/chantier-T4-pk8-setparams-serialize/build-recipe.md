# Build recipe (chantier-T4-pk8-setparams-serialize)

1. Materialize the T4 workspace: s7p as in `research/chantier-T0/tools/build-recipe.md` (step 1), then from the workspace root:
   `patch -p1 < research/chantier-T4-with-account-name/source.patch`
   `patch -p1 < research/chantier-T4-whitelist-resync/source.patch`
   `patch -p1 < research/chantier-T4-shareholder-copy/source.patch`
   `patch -p1 < research/chantier-T4-pk7-borsh-serialize/source.patch`
2. Apply this packet on top:
   `patch -p1 < research/chantier-T4-pk8-setparams-serialize/source.patch`
3. Build the `ordered.ld` from the round34 base, the four prior T4 patches, then this one:
   `patch ordered.ld < research/chantier-T4-with-account-name/ordered-ld.patch`
   `patch ordered.ld < research/chantier-T4-whitelist-resync/ordered-ld.patch`
   `patch ordered.ld < research/chantier-T4-shareholder-copy/ordered-ld.patch`
   `patch ordered.ld < research/chantier-T4-pk7-borsh-serialize/ordered-ld.patch`
   `patch ordered.ld < research/chantier-T4-pk8-setparams-serialize/ordered-ld.patch`
4. Build, copy, strip and measure as in the T0 recipe steps 2 to 5, with `PUMP_TEXT_SCRIPT` pointing to the patched `ordered.ld`:
   `python3 research/chantier-T0/metric/measure.py DEPLOYED.so candidate.so symbols.so --dump m.json`.
   Expect matched 793 / exact 140 / original_windows 1035,
   candidate sha256 `1d77749f01ea68e705f2fc7cf339ff1a2fc57a43de98ac544091fc76d4afe6af`,
   symbols sha256 `9166bc551402dfa168ffd335fe94fa8c1727dba4a431edcb5948d3f537573b50`.
5. Drift solver: `python3 tools/drift_solver.py DEPLOYED.so symbols.so --cand-stripped candidate.so -o drift.json`.
   Expect `call_only_raw_fail` 222, `potential_if_delta0` 362, `intervals_nonzero` 88.
