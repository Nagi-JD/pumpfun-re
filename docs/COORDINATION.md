# pump.fun RE — two-agent coordination board

Goal (per @shawmakesmagic): reverse the 4 deployed pump.fun programs toward byte-identical
rebuilds; reverse them for the USER privately (NO public PRs). Repo state: 0/4 core byte-identical;
the wall is source STRUCTURE + compiler/dependency provenance, not behavior.

## Split of work (no overlap, edge preserved)

### DeepSeek — PRIVATE analysis (NO PRs): Mayhem + byte-structure
Owns (hands results to the user, never PRs):
- Finish Mayhem instruction map (8 unmapped) + per-handler specs.
- Byte-structure change PROPOSALS for one pump_amm/pump_fees fn (Claude builds/measures).
See DEEPSEEK_PROMPT.md. Reads public repo as reference only; output stays private.

### Claude — PRIVATE behavioral verification + bug-finding (local)
Owns: building each reconstruction, running the differential harness + fuzzer, finding
reconstruction bugs. Tooling (sbftool, diffharness, ammharness, sbfcov fuzzer) stays private.
- Produces: per-instruction MATCH/DIVERGE verdicts, and minimal FIX diffs for any bug.
- Hands FIX diffs (not tooling) to the user → the user keeps them (no public PRs).

## Status board
| Program    | Mapped | Claude: built | Claude: behavioral verify            | DeepSeek: assigned |
|------------|:------:|:-------------:|--------------------------------------|---------------------|
| pump       | 53/53  | yes           | core trade loop verified; 3 bugs fixed | (open)            |
| pump_amm   | 38/38  | yes           | create/deposit/withdraw byte-id; swap fee-gate cleared, buyback-gate next | DeepSeek: 38 specs |
| pump_fees  | 31/31  | building      | pending (get_fees / get_fees_with_quote_mint) | (open)       |
| mayhem     | 25/25  | no            | pending (DeepSeek: map done+verified; handler specs) | DeepSeek: fees specs + CPI graph (batch 3) |

## Handshake
- Claude maintains this file (source of truth for what's verified).
- User relays: DeepSeek's PR links / findings → here; Claude's FIX diffs → DeepSeek.
- Rule: DeepSeek never claims byte-identity without compare.py evidence; Claude never
  claims behavioral match without an executed harness run.
