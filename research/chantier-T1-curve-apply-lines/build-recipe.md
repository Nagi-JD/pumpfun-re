# Build recipe (chantier-T1-curve-apply-lines)

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
   `patch -p1 < research/chantier-T3-mayhem-params/source.patch`
   `patch -p1 < research/chantier-T3-quote-control-state/source.patch`
   `patch -p1 < research/chantier-T3-curve-hop-constraint/source.patch`
   `patch -p1 < research/chantier-T3-legacy-buy-generic/source.patch`
   `patch -p1 < research/chantier-T3-legacy-buy-payments/source.patch`
   `patch -p1 < research/chantier-T3-legacy-sell-payments/source.patch`
   `patch -p1 < research/chantier-T3-constant-product/source.patch`
   `patch -p1 < research/chantier-T3-control-account/source.patch`
   `patch -p1 < research/chantier-T1-constant-product-lines/source.patch`
   `patch -p1 < research/chantier-T1-v3-check-lines/source.patch`
   `patch -p1 < research/chantier-T1-global-lib-lines/source.patch`
   `patch -p1 < research/chantier-T1-curve-quote-lines/source.patch`
   `patch -p1 < research/chantier-T1-buyback-validate-lines/source.patch`
   `patch -p1 < research/chantier-T1-buy-quote-lines/source.patch`
   and, from the directory holding `ordered.ld`, in order:
   `patch -p1 < research/chantier-T3-volume-accumulator/ordered-ld.patch`
   `patch -p1 < research/chantier-T3-global-lines/ordered-ld.patch`
   `patch -p1 < research/chantier-T3-reserved-fees/ordered-ld.patch`
   `patch -p1 < research/chantier-T3-sharing-config-line/ordered-ld.patch`
3. Apply this packet:
   `patch -p1 < research/chantier-T1-curve-apply-lines/source.patch`
4. Build, copy, strip and measure as in the T0 recipe steps 2 to 5, with `PUMP_TEXT_SCRIPT` pointing to that `ordered.ld`:
   `python3 research/chantier-T0/metric/measure.py DEPLOYED.so candidate.so symbols.so --dump m.json`.
   Expect matched 905 / exact 162 / original_windows 1035,
   candidate sha256 `7e71290795a8a8096b654ada33d25cd6c81eac73edc960cd9cf32adbea571096`,
   symbols sha256 `63397248e4a4ea00ac2107f3b6bffd000b30531106ed005f1355c0eb290efcfa`.
5. Drift solver: `python3 tools/drift_solver.py DEPLOYED.so symbols.so --cand-stripped candidate.so -o drift.json`.
   Expect `call_only_raw_fail` 236, `potential_if_delta0` 398, `intervals_nonzero` 140.
