# Build recipe (chantier-T4-close-burn-helpers)

1. Materialize the T4 workspace: s7p as in `research/chantier-T0/tools/build-recipe.md` (step 1), then from the workspace root:
   `patch -p1 < research/chantier-T4-with-account-name/source.patch`
   `patch -p1 < research/chantier-T4-whitelist-resync/source.patch`
   `patch -p1 < research/chantier-T4-shareholder-copy/source.patch`
   `patch -p1 < research/chantier-T4-pk7-borsh-serialize/source.patch`
   `patch -p1 < research/chantier-T4-pk8-setparams-serialize/source.patch`
   `patch -p1 < research/chantier-T4-transfer-with-seed/source.patch`
   `patch -p1 < research/chantier-T4-harvest-withheld/source.patch`
   `patch -p1 < research/chantier-T4-refund-seeds/source.patch`
2. Apply this packet on top:
   `patch -p1 < research/chantier-T4-close-burn-helpers/source.patch`
3. Build the `ordered.ld` exactly as in `research/chantier-T4-refund-seeds/build-recipe.md` (step 3), then:
   `patch ordered.ld < research/chantier-T4-close-burn-helpers/ordered-ld.patch`
4. Build, copy, strip and measure as in the T0 recipe steps 2 to 5, with `PUMP_TEXT_SCRIPT` pointing to that `ordered.ld`:
   `python3 research/chantier-T0/metric/measure.py DEPLOYED.so candidate.so symbols.so --dump m.json`.
   Expect matched 802 / exact 161 / original_windows 1035,
   candidate sha256 `c964dbd9835c98f1d8456a775c6d073c477548e927ae01c39718d1610878bf68`,
   symbols sha256 `08f489f2b43773667d17fc44c0e409bd94a8a5655844d208df83a9fd1381d2fa`.
5. Drift solver: `python3 tools/drift_solver.py DEPLOYED.so symbols.so --cand-stripped candidate.so -o drift.json`.
   Expect `call_only_raw_fail` 205, `potential_if_delta0` 366, `intervals_nonzero` 88.
