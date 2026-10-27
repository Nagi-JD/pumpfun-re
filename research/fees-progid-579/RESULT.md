# fees-progid-579

Stacked on upstream `research/fees-program-id-references` (main 2a2820e26, 578/585).

## Change
`let_bind.patch` (1 line, `programs/pump-fees/src/instructions/fee_sharing/mod.rs`): binds the result in `admit_associated_token_account` to a local. This applies on top of the materialized program-id sources.

## Measured (tools/measure.py, same toolchain, native build)
| | upstream shipped | native base | + let_bind |
|---|---|---|---|
| matched | 578 | 578 | **579** |
| raw | 198 | 141 | 141 |
| equal_locations | 182 | 182 | 183 |
| equal_edges | 3935 | 3935 | 3965 |

Gained: 243184 (admit_associated_token_account). Lost: none (matched or raw).
Remaining unmatched (6): 76384, 120816 (sweep_buyback), 137280, 147944, 163920, 249264.

## Reproduce
1. `python3 -B research/fees-program-id-references/verify.py --materialize DIR`
2. In `DIR/Cargo.toml`, set the `anchor-attribute-program` patch path to `DIR/vendor`.
3. `git apply let_bind.patch`
4. Run `tools/build.sh` (platform-tools v1.44, cargo rustc --release, sbpf-solana-solana).
5. `python3 -B tools/measure.py <symbols.so>`

Note: raw 198 depends on upstream`s container paths (`/work`) plus `ordered.ld`. A native build gives raw 141 (131 with ordered.ld forced), so raw here is compared native-to-native. The normalized match count and the unmatched set are reproduced exactly.
