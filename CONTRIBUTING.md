# Contributing

This is behavioral reverse-engineering of public on-chain bytecode. Contributions
are welcome, but the project holds a hard line on **honesty of evidence**.

## Ground rules

1. **Verify against the binary.** Every claim about a program's behavior or layout
   must be backed by the disassembly (cite the instruction address) or by an
   executed differential-harness run. "It looks like X" is not a finding.
2. **Never fabricate a match.** Do not claim byte-identity, behavioral equivalence,
   or a passing test you did not mechanically produce. A *matched rejection* (both
   binaries failing identically) and a *documented blocker* are valid, honest results.
3. **Keep the distinction.** "Compiles" / "dispatches the instruction" is NOT
   "verified behaviorally equivalent on executed paths." Say which one you mean.
4. **No original bytes as a build input.** Byte comparisons must come from compiling
   recovered *source*, never from embedding or patching a captured `.so`.
5. **No secrets.** Never commit RPC endpoints, API keys, or `.env`/`.rpc` files
   (they are gitignored). Scanners read the RPC URL from the `SOLANA_RPC` env var.

## Workflow

- The task board is `docs/COORDINATION.md`. Pick an open item; update it when you
  start and when you finish so work isn't duplicated.
- Deployed `.so` are not committed — pull them with
  `solana program dump <PROGRAM_ID> out.so --url mainnet-beta`.
- For a behavioral claim, add/extend a harness under `harness/` and paste the
  executed per-instruction output (ok/err/state-match) in your PR.
- For a structural finding, run `tools/sbftool.py` and cite the addresses.

## Good first tasks

- Finish the `mayhem` instruction map (8 of 16 instructions are still name-guessed —
  see `docs/MAP_ALL4.md`).
- Seed the pump_amm `fee_config` with stored bump 255 and verify `buy`/`sell` swap
  pricing end-to-end in `harness/ammharness` (see `docs/VERIFICATION.md` UPDATE 2/3).
- Extend the fuzzer corpus (`fuzzer/`) to drive uncovered branches and report any
  reconstruction divergence as a minimized, reproduced fixture.
