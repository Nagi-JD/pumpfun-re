# Build recipe (chantier-fees-wholeelf-163920)

Run on the Fees byte-race worker (platform-tools v1.44 + strip v1.52 + vendored
`anchor-attribute-program` with `#[used]`). Source tree:
`/work/next649/extend-qualified`. Deployed:
`feesr34/evidence/original/pump_fees/deployed.so`.

1. Apply the parent packet first:
   `patch -p1 < research/chantier-fees-wholeelf-147944/source.patch`
   (583 normalized / 200 raw, symbols sha256 `5381eb40…`).
2. Apply this packet:
   `patch -p1 < research/chantier-fees-wholeelf-163920/source.patch`
   (touches `programs/pump-fees/src/instructions/fee_sharing/create_donation_fee_pda.rs`).
3. Rebuild + measure: `bash ~/rebuild_measure.sh` → `MEASURE:{json}`.
4. Expect: `normalized 584`, `candidate_windows 585`, `raw 200`,
   `unmatched_original [120816]`, symbols sha256
   `57e11a5ee20b18438298101ba9375f9a187465926ad1dae9eebb5ab60a701a02`.

The upstream lalalune create patch also contains an `ordered.ld` hunk for the
whole-ELF layout layer; it is intentionally omitted here because this measure
uses the plain linker. No assembly, captured fragments, padding, or post-link
rewriting.
