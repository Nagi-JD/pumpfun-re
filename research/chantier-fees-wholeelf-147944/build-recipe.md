# Build recipe (chantier-fees-wholeelf-147944)

Run on the Fees byte-race worker (Anza platform-tools v1.44 + strip v1.52 +
vendored `anchor-attribute-program` with `#[used]` at `/work/next637/vendor/used-public`).
Source tree: `/work/next649/extend-qualified`. Deployed:
`feesr34/evidence/original/pump_fees/deployed.so`.

1. Start from the verified `extend-qualified` parent (582 normalized / 200 raw,
   symbols sha256 `ca9e6a93…`).
2. Apply this packet from the program source root:
   `patch -p1 < research/chantier-fees-wholeelf-147944/source.patch`
   (touches `programs/pump-fees/src/donation.rs` and `programs/pump-fees/src/lib.rs`).
3. Rebuild + measure (the box primitive):
   `bash ~/rebuild_measure.sh`
   which runs `cargo rustc --release --locked --offline --target sbpf-solana-solana`
   with `-Zremap-cwd-prefix=` + `--remap-path-prefix` for the math subcrate, copies
   `pump_fees_candidate.so` to `extend-qualified-symbols.so`, and prints
   `MEASURE:{json}` from `measure_thin.py` (→ `research/fees-composed-frontier188/window_map.py`).
4. Expect: `normalized 583`, `raw 200`, `unmatched_original [120816, 163920]`,
   symbols sha256 `5381eb4008c5e13efdc91b55e1b40e88da6ce9c2ba26fac5413c0bd25effc95d`.

No ordered.ld / linker-wrapper is used in this measure; the whole-ELF layout
layer (ordered.ld + relayout.py) is orthogonal and is not part of this packet.
No assembly, captured fragments, padding, or post-link rewriting.
