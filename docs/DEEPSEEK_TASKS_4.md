# DeepSeek — task batch 4 (pivot off the byte grind)

Byte-identity experiment #01 (docs/byte_experiment_01.md) measured that the T11 local
structure proposals CANNOT close that delta class: the gap is a whole-program compiler
specialization (a generic builder cloned to bake a shared constant across 13 callers),
not local source structure. So STOP producing T11 byte proposals — they don't converge.

Instead, do a **reconstruction-fidelity audit**: find where the recovered SOURCE behaves
differently from the DEPLOYED binary. This is binary-verifiable analysis and directly
complements Claude's execution-based bug hunting. You already found two such divergences
(admin_cto guard-set revision; PumpError enum revision 6010 vs 6022) — generalize that.

## TASK — reconstruction-fidelity audit → `fidelity_audit.md`
For each program, compare the recovered source (github.com/Nagi-JD/pumpfun-re `recovered-fixes/`
+ the lalalune repo's program source as reference) against the DEPLOYED binary behavior, and
flag every divergence where the reconstruction would behave differently from the deployed program:
- Wrong/missing error codes or guard sets (like admin_cto, the PumpError revision).
- Missing or extra account constraints (like the v3 USDC over-restriction, the missing seeds
  constraint on SellV3 index 7 that Claude's fuzzer found).
- Wrong fee/accounting direction (like the Token-2022 transfer-fee direction Claude fixed in buy).
- Branches the reconstruction stubs/rejects that the binary actually implements (create_v2 Mayhem,
  set_mayhem_virtual_params, multi-hop modes).
- Discriminator/layout mismatches (you already caught BondingCurve — note: that one was a
  decimal/hex read, the recon is actually correct; don't re-flag it).

For each finding: program, handler + address, the deployed behavior [B], the reconstruction
behavior [R], the concrete divergence, and severity (does it change economics / security / just
an error code?). This gives Claude a prioritized list to confirm by execution and fix.

## Rules
Binary-grounded, cite addresses, [B]/[R] tags, no fabrication, no PRs — hand `fidelity_audit.md`
back to the user. Do NOT add more byte-structure proposals.
