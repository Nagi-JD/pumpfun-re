# Build recipe (chantier-T3-volume-accumulator)

1. Materialize the 802/161 workspace and its `ordered.ld` as in `research/chantier-T4-close-burn-helpers/build-recipe.md` (steps 1 to 3).
2. Apply the earlier T3 packets from the workspace root, in order:
   `patch -p1 < research/chantier-T3-buy-v2/source.patch`
   `patch -p1 < research/chantier-T3-sell-v2/source.patch`
   `patch -p1 < research/chantier-T3-sell-v3/source.patch`
   `patch -p1 < research/chantier-T3-create-v2/source.patch`
   `patch -p1 < research/chantier-T3-initialize-quote-control/source.patch`
   `patch -p1 < research/chantier-T3-initialize/source.patch`
   `patch -p1 < research/chantier-T3-create/source.patch`
   `patch -p1 < research/chantier-T3-legacy-buy/source.patch`
   `patch -p1 < research/chantier-T3-init-user-volume/source.patch`
3. Apply this packet:
   `patch -p1 < research/chantier-T3-volume-accumulator/source.patch`
   and, from the directory holding `ordered.ld`, `patch -p1 < research/chantier-T3-volume-accumulator/ordered-ld.patch`
4. Build, copy, strip and measure as in the T0 recipe steps 2 to 5, with `PUMP_TEXT_SCRIPT` pointing to that `ordered.ld`:
   `python3 research/chantier-T0/metric/measure.py DEPLOYED.so candidate.so symbols.so --dump m.json`.
   Expect matched 815 / exact 161 / original_windows 1035,
   candidate sha256 `e4a5ef1016bed9b6eacdd535067f22844835e1da3bf8f491fda1d9924692e1e7`,
   symbols sha256 `b7620cc299e572abb7ea5586ead4a1ff9b59067bf33a1670fe51932aec200890`.
5. Drift solver: `python3 tools/drift_solver.py DEPLOYED.so symbols.so --cand-stripped candidate.so -o drift.json`.
   Expect `call_only_raw_fail` 205, `potential_if_delta0` 366, `intervals_nonzero` 91.
