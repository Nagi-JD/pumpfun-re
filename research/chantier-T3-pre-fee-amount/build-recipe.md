# Build recipe (chantier-T3-pre-fee-amount)

1. Materialize the `chantier-T3-add3` workspace and its `ordered.ld` as in `research/chantier-T3-add3/build-recipe.md` (steps 1 to 3).
2. Apply this packet from the workspace root:
   `patch -p1 < research/chantier-T3-pre-fee-amount/source.patch`
3. From the directory holding `ordered.ld`:
   `patch -p1 < research/chantier-T3-pre-fee-amount/ordered-ld.patch`
   The result is identical to `research/chantier-T3-pre-fee-amount/ordered.ld`.
4. Build, copy, strip and measure as in the T0 recipe steps 2 to 5, with `PUMP_TEXT_SCRIPT` pointing to that `ordered.ld`:
   `python3 research/chantier-T0/metric/measure.py DEPLOYED.so candidate.so symbols.so --dump m.json`.
   Expect matched 919 / exact 163 / original_windows 1035 / candidate_windows 1051,
   candidate sha256 `4f257fdc235936365e8d3b014eac164192a22b15c16c1df19e866f9a07c1d1dc`,
   symbols sha256 `c8c866b7264586d2c42d9bf410f931648596bacefbcbc2670f0c645f342a66f7`.
5. Drift solver: `python3 tools/drift_solver.py DEPLOYED.so symbols.so --cand-stripped candidate.so -o drift.json`.
   Expect `call_only_raw_fail` 239, `potential_if_delta0` 402, `intervals_nonzero` 89.
