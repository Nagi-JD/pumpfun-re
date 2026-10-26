# Contributing

Reverse-engineering of the four deployed pump.fun programs toward a **byte-for-byte identical**
reconstruction. Contributions come in by **fork + PR** (branch on a fork, PR to this repo,
`Nagi-JD/pumpfun-re:master`) and are held to a hard line on **honesty of evidence**.

## Scope (hard rules)

- **RE / reconstruction ONLY.** No vulnerability / bug-finding, no exploit, no armed PoC until
  the RE is complete. The coverage-guided fuzzer stays **coverage / behavioral-diff only** —
  never "fuzzer as attack".
- **One repo.** This is the single contribution target. The sibling `lalalune/pumpfun-source`
  clone is kept locally only as a tooling/evidence source (its `compare.py` byte-identity
  machinery and `evidence/original/*/deployed.so`); do not open PRs or branches there.

## Ground rules

1. **Verify against the binary.** Every claim about behavior or layout must be backed by the
   disassembly (cite the instruction address) or an executed differential-harness run.
   "It looks like X" is not a finding.
2. **Never fabricate a match.** Do not claim byte-identity, behavioral equivalence, or a passing
   test you did not mechanically produce. A *matched rejection* and a *documented blocker* are
   valid, honest results. Byte-identity means `scripts/compare.py` SHA-256 equality — nothing less.
3. **Keep the distinction.** "Compiles" / "dispatches the instruction" is NOT "verified
   byte-identical" and NOT "verified behaviorally equivalent on executed paths." Say which.
4. **No original bytes as a build input.** Byte comparisons must come from compiling recovered
   *source*, never from embedding, patching, or padding a captured `.so`.
5. **No secrets.** Never commit RPC endpoints, API keys, or `.env`/`.rpc` files (gitignored).

## Toolchain / build-host status

A byte-identical build needs the SBF toolchain (Rust + solana platform-tools / cargo-build-sbf +
llvm-objdump). It is intentionally **not installed on the lab host** (disk ~91%, shared with a
separate payout lane), so byte-identical builds are blocked until a build host with headroom
exists. Toolchain-free RE (maps, specs, structural proposals via `tools/sbftool.py`) proceeds now.

## Workflow

- The task board is `docs/COORDINATION.md`. Pick an open item; update it when you start/finish.
- Deployed `.so` are not committed — pull with `solana program dump <PROGRAM_ID> out.so --url mainnet-beta`.
- Fork + branch, then open a PR to `Nagi-JD/pumpfun-re:master`. For a behavioral claim, paste the
  executed per-instruction harness output; for a structural finding, cite `sbftool` addresses;
  for a byte-identity claim, attach the `compare.py` result. No empty PRs.

## Good first tasks

- Finish the `mayhem` instruction map and per-handler specs (see `docs/MAP_ALL4.md`).
- Extend the structural map / byte-structure proposals for `pump_amm` / `pump_fees`.
- Extend the fuzzer corpus (`fuzzer/`) for coverage and report any reconstruction divergence as a
  minimized, reproduced fixture (RE/behavioral only — not a security finding).
