# Build recipe (chantier-T4-pk7-borsh-serialize)

1. Materialize the T4 workspace: s7p as in `research/chantier-T0/tools/build-recipe.md` (step 1), then from the workspace root:
   `patch -p1 < research/chantier-T4-with-account-name/source.patch`
   `patch -p1 < research/chantier-T4-whitelist-resync/source.patch`
   `patch -p1 < research/chantier-T4-shareholder-copy/source.patch`
2. Apply this packet on top:
   `patch -p1 < research/chantier-T4-pk7-borsh-serialize/source.patch`
3. Build the `ordered.ld` from the round34 base, the three prior T4 patches, then this one:
   `patch ordered.ld < research/chantier-T4-with-account-name/ordered-ld.patch`
   `patch ordered.ld < research/chantier-T4-whitelist-resync/ordered-ld.patch`
   `patch ordered.ld < research/chantier-T4-shareholder-copy/ordered-ld.patch`
   `patch ordered.ld < research/chantier-T4-pk7-borsh-serialize/ordered-ld.patch`
4. Build, copy, strip and measure as in the T0 recipe steps 2 to 5, with `PUMP_TEXT_SCRIPT` pointing to the patched `ordered.ld`:
   `python3 research/chantier-T0/metric/measure.py DEPLOYED.so candidate.so symbols.so --dump m.json`.
   Expect matched 791 / exact 139 / original_windows 1035,
   candidate sha256 `43912acb109f6e915329cfe830bb23e0bcc6d27e6d08ebd95829b5d0f7c8898b`,
   symbols sha256 `cce37ebcddff394b14a576c581c52f3ae424f9ed9800295d47a5e2256161a5cf`.
5. Drift solver: `python3 tools/drift_solver.py DEPLOYED.so symbols.so --cand-stripped candidate.so -o drift.json`.
   Expect `call_only_raw_fail` 221, `potential_if_delta0` 360, root `0xefc8` (delta -1424).
