# Build recipe (chantier-T3-post-fill-helpers)

1. Materialize the `chantier-T3-pre-fee-amount` workspace and its `ordered.ld` as in `research/chantier-T3-pre-fee-amount/build-recipe.md` (steps 1 to 3).
2. Apply this packet from the workspace root:
   `patch -p1 < research/chantier-T3-post-fill-helpers/source.patch`
3. `ordered.ld` stays the `chantier-T3-pre-fee-amount` file (`ordered-ld.patch` is empty); it is identical to `research/chantier-T3-post-fill-helpers/ordered.ld`.
4. Build, copy, strip and measure as in the T0 recipe steps 2 to 5, with `PUMP_TEXT_SCRIPT` pointing to that `ordered.ld`:
   `python3 research/chantier-T0/metric/measure.py DEPLOYED.so candidate.so symbols.so --dump m.json`.
   Expect matched 921 / exact 163 / original_windows 1035 / candidate_windows 1058,
   candidate sha256 `7134efde2dad4f77d98d77c083c4ebf32012e1e99e541ffd0efdcd126322758e`,
   symbols sha256 `a1fb9481747e7ea1cc45e6cd4183a1ac81e172eca4ada2e3dc67a6c53047b587`.
5. Drift solver: `python3 tools/drift_solver.py DEPLOYED.so symbols.so --cand-stripped candidate.so -o drift.json`.
   Expect `call_only_raw_fail` 239, `potential_if_delta0` 402, `intervals_nonzero` 95.
