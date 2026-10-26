# pump.fun RE — coordination board

Goal (2026-10-26): a **byte-for-byte identical** reconstruction of the four
deployed pump.fun programs (`pump`, `pump_amm`/PumpSwap, `pump_fees`, `mayhem`). The single
target repo is **Nagi-JD/pumpfun-re**, contributed via our fork **Shuai-Qing/pumpfun-re**.

## Contribution model (approved by the owner)
- **Fork + PR.** Work on a branch in `Shuai-Qing/pumpfun-re`, then open a PR to
  `upstream = Nagi-JD/pumpfun-re` (`master`). This is public, owner-approved — it is **not**
  private/no-PR anymore.
- **One repo only.** `lalalune/pumpfun-source` is **no longer a contribution target**: no PRs
  and no branches there. Keep the local `pumpfun-source` clone ONLY as a local tooling/evidence
  source — reuse `scripts/compare.py` + the byte-identity machinery and `evidence/original/*/deployed.so`
  locally. The deliverable (byte-identical reconstruction + its build/compare pipeline) lands here,
  in Nagi's repo.

## Scope — RE / reconstruction ONLY
- Reverse-engineering and byte-identical reconstruction only.
- **NO vulnerability / bug-finding, no exploit, no armed PoC until the RE is complete.** Any
  fuzzer stays coverage / behavioral-diff only, never "fuzzer as attack".
- Honesty of evidence is a hard line (see `CONTRIBUTING.md`): cite instruction addresses
  (sbftool) and/or executed differential-harness output; never claim a byte-identity or
  behavioral match that was not mechanically produced.

## Toolchain / build-host status (blocker)
Byte-identical builds need the SBF toolchain (Rust, solana platform-tools / cargo-build-sbf
v1.44/v1.52/v1.54, llvm-objdump). It is **NOT installed and must not be installed on the current
lab host**: disk is ~91% full and shared with other workloads. The critical path is a
build host with disk headroom; until then only the toolchain-free RE (sbftool maps, specs,
structural analysis) can proceed, and no byte-identical build can actually be produced yet.

## Status board
| Program    | Mapped | Claude: built | Claude: behavioral verify            | DeepSeek: assigned |
|------------|:------:|:-------------:|--------------------------------------|---------------------|
| pump       | 53/53  | yes           | core trade loop verified; 3 bugs fixed | (open)            |
| pump_amm   | 38/38  | yes           | FULLY verified: create/deposit/buy/sell/withdraw byte-id (swap pricing end-to-end) | DeepSeek: 38 specs |
| pump_fees  | 31/31  | building      | pending (get_fees / get_fees_with_quote_mint) | (open)       |
| mayhem     | 25/25  | no            | pending (DeepSeek: map done+verified; handler specs) | DeepSeek: fees specs + CPI graph (batch 3) |

## Handshake
- This file is the source of truth for what is verified and what is assigned.
- DeepSeek is the model for the analysis loop (budget rule). See `DEEPSEEK_PROMPT.md`.
- Never claim byte-identity without `compare.py` SHA-256 evidence; never claim behavioral match
  without an executed harness run.
