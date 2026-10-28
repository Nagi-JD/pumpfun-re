# Build recipe (chantier-T3-create)

1. Materialize the 802/161 workspace and its `ordered.ld` as in `research/chantier-T4-close-burn-helpers/build-recipe.md` (steps 1 to 3).
2. Apply the earlier T3 packets from the workspace root, in order:
   `patch -p1 < research/chantier-T3-buy-v2/source.patch`
   `patch -p1 < research/chantier-T3-sell-v2/source.patch`
   `patch -p1 < research/chantier-T3-sell-v3/source.patch`
   `patch -p1 < research/chantier-T3-create-v2/source.patch`
   `patch -p1 < research/chantier-T3-initialize-quote-control/source.patch`
   `patch -p1 < research/chantier-T3-initialize/source.patch`
3. Apply this packet:
   `patch -p1 < research/chantier-T3-create/source.patch`
4. Build, copy, strip and measure as in the T0 recipe steps 2 to 5, with `PUMP_TEXT_SCRIPT` pointing to that `ordered.ld`:
   `python3 research/chantier-T0/metric/measure.py DEPLOYED.so candidate.so symbols.so --dump m.json`.
   Expect matched 811 / exact 161 / original_windows 1035,
   candidate sha256 `4b6e6d7210c739e651fe515ada4bf73d9b1004bb1125b1d4437f986f40912d10`,
   symbols sha256 `26eff46fa6a71ae59af2434d4ad285c7bf80eb3e4d96acd7156b301bc763ec0b`.
5. Drift solver: `python3 tools/drift_solver.py DEPLOYED.so symbols.so --cand-stripped candidate.so -o drift.json`.
   Expect `call_only_raw_fail` 205, `potential_if_delta0` 366, `intervals_nonzero` 88.
