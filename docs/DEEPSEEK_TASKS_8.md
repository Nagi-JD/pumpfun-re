# DeepSeek — task set 8 (2026-10-27). Big batch, all four programs.

Base is now lalalune's NEWEST checkpoints (upstream main 2a2820e26 in `~/pumpre/repo` local `main`):
Pump Round23 712/1035 · PumpSwap native-fee 599/785 · Fees program-id 578/585 (198 exact) ·
Mayhem sizing-panic 429/441 (100 exact). Our own stacked results so far: Fees ATA fix
(`let needs_create = ...; if needs_create {`, window 243184), Pump per-site error closures on
deployed lines (+29 on the old base), and "native Linux build" (+5 on Pump and AMM vs their macOS
builds). Claude's agents are applying these on top of the new checkpoints right now.

Rules as always: read-only, cite addresses, tag [B]/[R]/[partial], no fabrication, Claude tests
every proposal with the real build + their window metric. Do NOT build in or modify
`~/pumpre/feesbuild`, `~/pumpround23`, `~/ammresearch`, `~/mayhemrace`; no `--tools-version`.
T7.12 (`pump_quote_module.md`) is still open — do it first, then these in order.

---

## T7.13 — Pump `trade_v3.rs`: why 15/15 still fail although the path is restored
Round23 compiles `trade_v3.rs` under its deployed path, yet all 15 windows stay unmatched. For each
of the 15: deployed address/size, the candidate symbol it should pair with, the exact deployed
line range of every error/Location inside it, and the dominant cause (line offset only / block
order like the Fees ATA / split-merge / real logic). If many share the same line shift, give the
shift. Deliverable `pump_trade_v3_windows.md`.

## T7.14 — Mayhem: the last 12 windows of THEIR newest checkpoint
Exact unmatched list measured on their `mayhem-sizing-panic-recovery` artifacts
(deployed address, size in bytes):
`65472 (912)`, `69192 (8008)`, `77200 (8400)`, `85600 (9736)`, `95848 (17312)`,
`113672 (13848)`, `127520 (12992)`, `140512 (18648)`, `159160 (18096)`, `185296 (1256)`,
`186552 (1120)`, `534840 (960)`.
Your T7.3 was on the older 426 base — redo the pairing for these 12. Priority: the 4 SMALL ones
(65472, 185296, 186552, 534840): exact pairing, full classification, and one concrete source change
each (inline condition → local, closure form, line placement, `?` vs explicit match). For the 8 big
trade handlers: which construct dominates the diff, and whether they share one root cause.
Deliverable `mayhem_last12.md`.

## T7.15 — PumpSwap: re-cluster on their 599 checkpoint
Your T7.2 clusters were on the 488 base. Redo on `repro/pump_amm/native-fee-cpi-recovery-20261027`
(186 unmatched): which clusters did they close, which of the 35 error-closure windows are still
open, and what the top-5 clusters are now, ranked by windows unlocked. Deliverable
`amm_599_clusters.md`.

## T7.16 — Fees: the 7 remaining windows, region by region
An IR study of `sweep_buyback` (deployed 120816) found its diff spread over 5 regions: prologue
(vault loaded before the bump byte), `Rent::get()?` Err fall-through (line 112), the inlined
`BuybackVault::claim` error block placed right after the Rent Err block in deployed, the
`TransferChecked` field read order (line 115), and the `checked_add` / native-mint branch
(lines 118-119). Hypothesis: the ORIGINAL `claim()` in `state.rs` is written differently. Propose
2–3 concrete alternative source forms of `BuybackVault::claim` (and of the Rent check) that would
put its error block next to the Rent Err block. Then the same region-by-region reading for
claim_v2 (137280), withdraw (249264), crank (147944). Deliverable `fees_remaining_regions.md`.

## T7.17 — The step after functions: data / rodata / relocations (whole-ELF)
Even with every function matched, whole-ELF equality needs `.rodata`, `.data.rel.ro`, relocations
and padding to match. For Fees (closest to done), compare deployed vs their 578 build section by
section: which `.rodata` bytes differ, and map each differing run to its source origin (panic
message strings, error-name tables, Location records, IDL/discriminator constants, string order
or dedup). Classify: will close automatically once functions match (address-only) vs needs its
own fix (string text/order/padding). Deliverable `fees_data_residue.md`. This is the map of what
stands between "all functions matched" and "byte-identical ELF".

---
Ping the user after each deliverable. Order: T7.12 → T7.14 (small Mayhem ones are fast wins) →
T7.13 → T7.16 → T7.15 → T7.17.
