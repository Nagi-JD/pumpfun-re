# Build recipe (chantier-T4-whitelist-resync)

1. Materialize the T4 workspace: s7p as in `research/chantier-T0/tools/build-recipe.md` (step 1), then `patch -p1 < research/chantier-T4-with-account-name/source.patch`.
2. From the workspace root: `patch -p1 < research/chantier-T4-whitelist-resync/source.patch`.
3. Patch the round34 `ordered.ld` with the T4 patch, then this one:
   `patch ordered.ld < research/chantier-T4-with-account-name/ordered-ld.patch`
   `patch ordered.ld < research/chantier-T4-whitelist-resync/ordered-ld.patch`
4. Build, copy, strip and measure as in the T0 recipe steps 2 to 5, with `PUMP_TEXT_SCRIPT` pointing to the patched `ordered.ld`:
   `python3 research/chantier-T0/metric/measure.py DEPLOYED.so candidate.so symbols.so --dump m.json`.
   Expect matched 789 / exact 138 / original_windows 1035, candidate sha256 `c152d81d7010078e97530d24aaa96715b0f35de68f16cc89f798994d882d7724`.
5. Drift solver: `python3 tools/drift_solver.py DEPLOYED.so symbols.so --cand-stripped candidate.so -o drift.json`.
   Expect `call_only_raw_fail` 220, `potential_if_delta0` 358, 74 nonzero intervals, root `0xce88` (delta -336).
