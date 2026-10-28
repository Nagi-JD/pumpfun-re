# Build recipe (chantier-T3-mayhem-params)

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
   `patch -p1 < research/chantier-T3-volume-accumulator/source.patch`
   `patch -p1 < research/chantier-T3-program-lines/source.patch`
   `patch -p1 < research/chantier-T3-global-lines/source.patch`
   `patch -p1 < research/chantier-T3-fee-lines/source.patch`
   `patch -p1 < research/chantier-T3-reserved-fees/source.patch`
   `patch -p1 < research/chantier-T3-sharing-config-line/source.patch`
   `patch -p1 -E < research/chantier-T3-pump-quote-path/source.patch` (`-E` removes the renamed `nested_create.rs`)
   `patch -p1 < research/chantier-T3-admin-cto-client/source.patch`
   `patch -p1 < research/chantier-T3-migrate-client/source.patch`
   `patch -p1 < research/chantier-T3-creator-sync-lines/source.patch`
   and, from the directory holding `ordered.ld`, in order:
   `patch -p1 < research/chantier-T3-volume-accumulator/ordered-ld.patch`
   `patch -p1 < research/chantier-T3-global-lines/ordered-ld.patch`
   `patch -p1 < research/chantier-T3-reserved-fees/ordered-ld.patch`
   `patch -p1 < research/chantier-T3-sharing-config-line/ordered-ld.patch`
3. Apply this packet:
   `patch -p1 < research/chantier-T3-mayhem-params/source.patch`
4. Build, copy, strip and measure as in the T0 recipe steps 2 to 5, with `PUMP_TEXT_SCRIPT` pointing to that `ordered.ld`:
   `python3 research/chantier-T0/metric/measure.py DEPLOYED.so candidate.so symbols.so --dump m.json`.
   Expect matched 881 / exact 162 / original_windows 1035,
   candidate sha256 `133d57a00dc0ff4f8c9e50316a750bf96faf76cf76dc67f64256277d0d439166`,
   symbols sha256 `44e4ff70d60232e7e7a551a96757744e4b1b04c205b4946895c76066c8543d91`.
5. Drift solver: `python3 tools/drift_solver.py DEPLOYED.so symbols.so --cand-stripped candidate.so -o drift.json`.
   Expect `call_only_raw_fail` 229, `potential_if_delta0` 391, `intervals_nonzero` 125.
