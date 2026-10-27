# Build recipe (chantier-T4-with-account-name)

1. Materialize the s7p workspace exactly as in `research/chantier-T0/tools/build-recipe.md` (step 1).
2. From the workspace root: `patch -p1 < research/chantier-T4-with-account-name/source.patch`.
3. Apply `ordered-ld.patch` to the round34 `ordered.ld` (`patch ordered.ld < ordered-ld.patch`). It adds the two sections this source now emits, at their deployed neighbours.
4. Build, copy, strip and measure as in the T0 recipe steps 2 to 5, with `PUMP_TEXT_SCRIPT` pointing to the patched `ordered.ld`:
   `python3 research/chantier-T0/metric/measure.py DEPLOYED.so candidate.so symbols.so --dump m.json`.
   Expect matched 788 / exact 138 / original_windows 1035, candidate sha256 `ec3f7295a9ef5ad47244c1bf747c02142fe2e22e40a62063ee3630703a0484cd`.
5. Drift solver: `python3 tools/drift_solver.py DEPLOYED.so symbols.so --cand-stripped candidate.so -o drift.json`.
   Expect `call_only_raw_fail` 219, `potential_if_delta0` 357, 75 nonzero intervals, root `0x6e78` (delta -688).
