# Build recipe (chantier-fees-wholeelf-120816)

Run on the Fees byte-race worker (platform-tools v1.44 + strip v1.52 + vendored
`anchor-attribute-program` with `#[used]`). Source tree:
`/work/next649/extend-qualified`. Deployed:
`feesr34/evidence/original/pump_fees/deployed.so`.

1. Apply the two parent packets first, in order:
   `patch -p1 < research/chantier-fees-wholeelf-147944/source.patch`
   `patch -p1 < research/chantier-fees-wholeelf-163920/source.patch`
   (584 normalized / 200 raw, symbols sha256 `57e11a5e…`).
2. Apply this packet:
   `patch -p1 < research/chantier-fees-wholeelf-120816/source.patch`
   (touches `programs/pump-fees/src/instructions/buyback/mod.rs` and
   `programs/pump-fees/src/state.rs`).
3. Rebuild + measure: `bash ~/rebuild_measure.sh` → `MEASURE:{json}`.
4. Expect: `normalized 585`, `raw 288`, `unmatched_original []`, symbols sha256
   `e7a233d207589e7a2082d22084ab512d05facd969ad43682f824bb76b8e8860f`.

All three packets applied together reach 585/585 normalized (every deployed Fees
function window matched). The orthogonal whole-ELF layout layer (ordered.ld +
relayout.py, pinned v1.52 strip) is what then yields byte-identical raw/stripped
identity and is not part of these normalized-window packets. No assembly,
captured fragments, padding, or post-link rewriting.
