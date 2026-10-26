# Pump.fun behavioral-clone gap list (synthesis of 11-agent RE pass)

Built from `spec/01..11-*.md`, each binary-verified with `sbftool` against
`evidence/original/pump/deployed.so` and cross-checked vs the recovered source.
Scope: the `pump` program (53/53 instructions mapped). "Gap" = deployed binary
does something the reconstruction does not.

## Clusters that MATCH the reconstruction (no behavioral gap)
- 01 admin/config, 02 config (set_params etc.), 03 quote-control (both whitelists),
  06 sell (all three), 09 fees/sweep, 11 volume-accumulator/idl.
- These are deployable as-is from the recovered source.

## TRACK 1 — behavioral-clone blockers, ranked

### B1. `util/transfer_fee.rs` missing entirely  (HIGH — 5 handlers)
The module is baked into the binary (links spl-token-2022 transfer-fee ext,
rodata 0x1ba1e0) but absent from the recovered `src/` tree. Affected:
- buy_v2, buy_exact_quote_in_v2, buy_v3, buy_exact_quote_in_v3 quote legs use
  plain `transfer_checked` with no gross-up → fee-bearing quote mints
  under-deliver under the reconstructed math.
- migrate_v2 performs the actual harvest (op `26,4`) + extension-aware
  `quote_account_size`; recovered `migrate` is native-only.
- NOTE: `sell_v2` does NOT use it (verified: 0 transfer-fee opcodes in its 1714
  insns) — the sell slippage/event mismatch is real program behavior present
  identically in binary and source, not a reconstruction gap.
Work: write `util/transfer_fee.rs` (fee calc + gross-up + harvest) and wire it
into the four buy quote legs and migrate_v2.

### B2. `create_v2` Mayhem branch is a reconstruction stub  (HIGH)
Recovered `create_v2.rs:39` placeholder-rejects `is_mayhem_mode`; the binary
implements it: 5 hard-wired Mayhem accounts + CPIs into MAyhS…MD4e, errors
CpitializeMayhemFailed / MayhemModeDisabled / MayhemModeQuoteMintNotAllowed.
Work: reconstruct the mayhem create path + its CPI sequence.

### B3. v3 quote-route over-restriction  (HIGH)
Recovered `trade.rs::check_quote` hardcodes non-SOL quote = USDC and rejects the
rest. Binary: USDC appears in ONE lddw in all of .text and never in the v3 core;
only the WSOL sentinel gates native. Deployed program accepts general whitelisted
quote mints (quote_control). Work: replace the USDC hardcode with the whitelist
check the binary actually uses.

### B4. multi_hop_curve_swap — depth cap + adapter delta  (MEDIUM)
- Binary defines CurveDepthExceeded + SetMaxCurveDepth admin ix, but the depth
  check is enforced in the OUTER router, absent from reconstructed
  `multi_hop_curve.rs`.
- Trailing TradeEvent field +0x198 = `quote_before_adapter − quote_after_adapter`
  (adapter diff / withheld T2022 fee, helper 0x12a1c). Reconstruction hardcodes
  it 0 (Tokenkeg identity). Work: port cap enforcement + the real adapter delta.
- Completion/migration-mid-route, holder/cashback/mayhem curve modes: still PARTIAL.

### B5. set_mayhem_virtual_params — no source; persistence unresolved  (MEDIUM)
Reconstructed as validate-and-emit over a 6–8×u64 virtual-param block (lamport
bounds 1e6/1e7/1e12, dual emit, event disc 757be4b6a1a8dcd6). Open: no param
write-back found in the handler frame — persistence is via Anchor serialize or a
Mayhem CPI not yet traced. Work: trace 0x19a7b / 0x1447e to locate persistence.

### B6. token-incentives handlers — SPECIFIED, ready to port  (was unrecovered)
admin_update_token_incentives (@0x25c54) and claim_token_incentives (@0x25d0e)
are now fully reconstructed (spec 10): account order, GlobalVolumeAccumulator
layout, 8 schedule guards, reward = current_sol_volume *
total_token_supply[prev_day] / sol_volumes[prev_day], PDA-signed transfer,
events. Cross-validates Shaw's §3 decompile. Work: write the Rust from the spec.

### B7. cosmetic divergences (LOW)
- cashback zero path logs "No cashback to claim" where source returns silently.
- recovered `migrate.rs` lists token_program twice where binary passes two
  distinct programs.
- buy_v3 parses then discards partial_fill (matches `lib.rs:104 let _`); not a gap.

## TRACK 2 — byte-identity signal
### admin_cto is a DIFFERENT REVISION than the recovered source  (IMPORTANT)
Deployed `admin_cto` execute (0x4542) omits guards 6088
(CtoNotAllowedForMayhemCoin) and 6092 (CtoCreatorAccountNotWritable) that the
recovered `admin_cto.rs` raises, AND raises 6080/6095 that the source does not,
with several shared guards reordered. The rodata strings for the absent codes
still exist. This means the recovered source tree does not correspond to the
exact deployed revision for at least this handler — a concrete obstacle to
whole-program byte-identity independent of the source-structure wall. Any
byte-identity attempt must first resolve which revision each handler targets.

## What this means for the two goals
- Behavioral clone: B1–B6 are the finite worklist; B6 is already specified,
  B1/B2/B3 are the substantive writing. After these + the differential harness,
  a deployable clone (your own program id/keys) is reachable.
- Byte-identical: the admin_cto revision mismatch + the known source-structure
  wall (pump_fees: all handlers done, still not byte-identical) mean this stays
  an open research grind, not a finite task.
