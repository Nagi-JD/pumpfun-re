# Build recipe (chantier-T3-initialize-quote-control)

1. Materialize the 802/161 workspace and its `ordered.ld` as in `research/chantier-T4-close-burn-helpers/build-recipe.md` (steps 1 to 3).
2. Apply the earlier T3 packets from the workspace root, in order:
   `patch -p1 < research/chantier-T3-buy-v2/source.patch`
   `patch -p1 < research/chantier-T3-sell-v2/source.patch`
   `patch -p1 < research/chantier-T3-sell-v3/source.patch`
   `patch -p1 < research/chantier-T3-create-v2/source.patch`
3. Apply this packet:
   `patch -p1 < research/chantier-T3-initialize-quote-control/source.patch`
4. Build, copy, strip and measure as in the T0 recipe steps 2 to 5, with `PUMP_TEXT_SCRIPT` pointing to that `ordered.ld`:
   `python3 research/chantier-T0/metric/measure.py DEPLOYED.so candidate.so symbols.so --dump m.json`.
   Expect matched 808 / exact 161 / original_windows 1035,
   candidate sha256 `4aec881f86f617486662141e5fbadda36e4aee712bda6c52a22f674efe6da23e`,
   symbols sha256 `61418414b4482be8f5974bd3611e72ee364cf4ac3195c4d3b8d3f282dcfa23b5`.
5. Drift solver: `python3 tools/drift_solver.py DEPLOYED.so symbols.so --cand-stripped candidate.so -o drift.json`.
   Expect `call_only_raw_fail` 205, `potential_if_delta0` 366, `intervals_nonzero` 88.
