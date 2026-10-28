# Build recipe (chantier-T3-sell-v2)

1. Materialize the 802/161 workspace and its `ordered.ld` as in `research/chantier-T4-close-burn-helpers/build-recipe.md` (steps 1 to 3).
2. Apply the earlier T3 packets from the workspace root, in order:
   `patch -p1 < research/chantier-T3-buy-v2/source.patch`
3. Apply this packet:
   `patch -p1 < research/chantier-T3-sell-v2/source.patch`
4. Build, copy, strip and measure as in the T0 recipe steps 2 to 5, with `PUMP_TEXT_SCRIPT` pointing to that `ordered.ld`:
   `python3 research/chantier-T0/metric/measure.py DEPLOYED.so candidate.so symbols.so --dump m.json`.
   Expect matched 804 / exact 161 / original_windows 1035,
   candidate sha256 `d72aa9375fe777a00a7f26f4f700747640374573dad87b924871648a5497e601`,
   symbols sha256 `d998f7754d89fd935ef0d19b1fd27b7048115d55c409c479d0be96313924ee00`.
5. Drift solver: `python3 tools/drift_solver.py DEPLOYED.so symbols.so --cand-stripped candidate.so -o drift.json`.
   Expect `call_only_raw_fail` 205, `potential_if_delta0` 366, `intervals_nonzero` 88.
