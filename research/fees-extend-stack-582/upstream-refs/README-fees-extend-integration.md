# Fees Extend recovery

The reconstructed Rust `extend_fee_config` handler matches all **750 original instructions / 6,312 bytes** after call and address normalization. Composed with the accepted ATA and Withdraw recoveries, Fees reaches **582 of 585 normalized functions** and **200 raw-local matches**, with no loss of previous matches.

The one-file source patch uses the declared FeeConfig discriminator, maps failed PDA derivation to the same custom error and evaluates the configuration key directly in the seed array. It preserves the existing guard/error source lines, borrow release, resize and event behavior. The new temporary ownership boundary reproduces the original stack allocation without assembly, binary rewriting, padding or private-layout access.

The verifier checks **4,437 direct calls** in matched original functions, **63 code pointers**, **2,075 data pointers**, all **379 relocated data fields** and every other compiled function against the original/parent mapping. The complete **21,079-byte readonly payload** and all **105 Source records** remain intact. The linker orders 1,474 complete compiler-emitted input sections.

Two fresh normal Cargo builds produce identical symbol and stripped files. All **17,331 runtime cases across 18 suites** pass. The packet retains the native execution receipts, source materialization and corruption guards. Sweep, Crank and CreateDonation remain unmatched. **Whole ELF and capture equality remain false.**

```sh
python3 -B research/fees-extend-integration/verify.py
python3 -B research/fees-extend-integration/test_verify.py
python3 -B research/fees-extend-integration/verify.py --materialize /absolute/new/source
```

The materializer writes all 46 workspace inputs, the inherited macro dependency and linker recipe. The captured build uses the pinned Linux v1.44 SDK, `/work/next649` sources and `/work/next637/vendor/used-public`; recreate those mounts or adapt paths consistently. The parent is the [ATA integration](../fees-ata-prefix-integration/README.md). Exploratory unqualified builds establish source/code shape only and are excluded from native acceptance evidence, which comes from the two fresh qualified builds included here.
