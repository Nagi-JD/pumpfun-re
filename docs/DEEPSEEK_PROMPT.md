# Task: private reverse-engineering of pump.fun Solana programs (NO public PRs)

You are working PRIVATELY for the user. Everything you produce goes back to the user —
do NOT open pull requests, do NOT contribute to any public repo, do NOT post anywhere.
This is analysis of public on-chain bytecode kept for the user's own use.

## Context
pump.fun's four Solana programs (pump, pump_amm/PumpSwap, pump_fees, mayhem) are
closed-source. Deployed bytecode is public; the Rust source is not. A community repo
`lalalune/pumpfun-source` hosts a behavioral reconstruction (clone it READ-ONLY, as a
reference only). Whole-file byte-identity is unsolved (0/4). The user is reversing these
for themselves. A second agent (Claude) is doing build + differential-harness + fuzzing
locally; YOU take the parts below so there's no overlap.

## Your assigned scope (complementary to Claude)
### 1. MAYHEM — finish the instruction map + reverse the handlers
- Binary: the mayhem deployed .so (program id MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e).
  Claude mapped 8/16 instructions; these are UNMAPPED (name-guess failures):
  update_global_params, initialize_global_params, update_trader, buy, withdraw_admin,
  burn_tokens, sweep_fees (+ the real name behind each).
- Resolve each: the Anchor discriminator is sha256("global:"+snake_name)[:8], emitted in
  the dispatcher as a split lddw immediate. Read the binary's "Instruction: X" strings and
  the dispatcher to find the true snake_case names, then map each to its handler address.
- For each handler, write a short behavioral spec: accounts, args, errors, CPIs, state writes.
- Reference (read-only): `programs/mayhem/` in the lalalune repo.

### 2. BYTE-STRUCTURE analysis (for the user's own byte-identity interest)
- For ONE function in pump_amm or pump_fees that the repo's pass-index marks
  "not normalized-identical", compare the deployed llvm-objdump vs the recovered build,
  and propose the specific SOURCE-STRUCTURE change (function split/merge, inline, item
  order) that would move the compiled bytes toward the original. Explain WHY.
- You do NOT build/verify (Claude has the toolchain). Produce the proposal + reasoning;
  the user hands it to Claude to build and measure.

## Output (hand back to the user as text/files — no PRs)
- `mayhem_map.md`: the completed 16/16 instruction→discriminator→handler map + per-handler spec.
- `structure_proposals.md`: your byte-structure change proposals with before/after reasoning.

## Rules
- NO pull requests, NO public posting. Private only.
- Verify every claim against the binary/disassembly; cite addresses. Never fabricate a
  byte-identity or behavioral claim — if unsure, say so.
