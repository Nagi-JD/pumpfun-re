# Build recipe (chantier-T5-data-layout)

1. Build the #41 candidate exactly as in `research/chantier-T3-init-user-volume/build-recipe.md`.
   Expect matched 813 / exact 161, candidate sha256 `1ce9df3a268c600b11341d1ae8822b5d34e4f92cb27cd246f85edb73bab7513c`,
   symbols sha256 `3cd921aa5d8853feb111ad7a62a406333512173199558695e653cef169bf3afd`.
2. Run the solver:
   `python3 tools/data_layout.py DEPLOYED.so symbols.so --cand-stripped candidate.so -o data-layout.json`.
   Expect the `summary` block of `data-layout-ref.json`: `data_aligned` 231, `data_residual` 421, `projected_raw` 161, `projected_raw_after_calls` 392,
   `lddw_sites_aligned` 527 of 3087, `location_pairs` equal 90 / line 14 / file 8,
   `rodata_prefix_equal` 216, `data_rel_ro_prefix_equal` 104.
3. Detail one window: add `--window 0x101448` (any deployed window start); its differing slots appear under `windows[].slots`.
