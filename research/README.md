# Byte-identity research packets

Each packet stacks a change on top of a published checkpoint of
[lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT). Patches and
modified sources here are derived from that MIT-licensed reconstruction; credit goes to its
authors for the base checkpoints, recipes and window metric.

Counts are function windows matched against the deployed program with lalalune's window
metric (normalized windows / raw byte-exact bodies). Matched windows are **not** whole-ELF
equality; no core program is whole-ELF identical yet.

| Program | Base checkpoint (theirs) | Packet | Result |
|---|---|---|---|
| Fees | `research/fees-program-id-references` 578 / 198 raw | `fees-progid-579-raw/` | **579 / 198 raw**, built in a byte-exact reproduction of their build environment (their unchanged sources give their exact `result.json` hashes) |
| Fees | same, native build | `fees-progid-579/` | 579 (native build, 141 raw) |
| Fees | `research/fees-sharing-slice-recovery` 577 | `fees-ata-578/` | 578 (first stacking of the ATA fix) |
| PumpSwap | `repro/pump_amm/native-fee-cpi-recovery-20261027` 599 | `amm-race/`, `amm-race-2/` | **657** (native Linux build +18, `error!` closures on deployed lines +40) |
| Pump | `repro/pump/main-contract-round23-20261027` 712 | `pump-r23-race/`, `pump-r23-race-2/` | **761** (per-site error closures on deployed lines, no hardcoded-location macro; migrate fix) |
| Pump | older 528 checkpoint | `pump-race-567/` | 567 (historical) |

Behavioral check: `pump-migrate-verification/` runs lalalune's LiteSVM migrate probes on
DEPLOYED vs BEFORE vs AFTER. The `migrate`/`migrate_v2` change (migrated quote =
`real_quote_reserves + post_complete_quote_in` − fee) makes AFTER match DEPLOYED in every
case, including three error cases the previous source did not reproduce.

Each packet has a RESULT file (before/after counts), the patch, the build script and the
measure JSON. Deployed `.so` files are not committed (public on-chain).

## Notes
- `pump-r23-race/` (packet 1) still has the old `migrate`/`migrate_v2` quote computation
  (`real_quote_reserves - fee`, without `post_complete_quote_in`). That is the behavioral bug
  fixed and execution-verified in `pump-r23-race-2/`. Packet 1 is kept for history only.
- These sources reconstruct the **deployed** program's behavior, including its quirks. Example:
  the deployed pump binary never raises `DisabledMigrate` (it exists only in the error-name
  table, no raise site), so `migrate` does not check `global.enable_migrate`; adding that check
  would diverge from the deployed program.
- `token_incentives/volume_accumulator.rs` (unchanged from the upstream reconstruction): a local
  LiteSVM check against the deployed program confirms `current_sol_volume` carries across
  incentive seasons (the season-change reset clears `total_claimed_tokens` but not the volume),
  and the reconstruction reproduces this byte-for-byte. It is **latent**: in every path exercised,
  a new season's per-day `sol_volumes` stayed 0 (legacy `buy` wrote no volume; the only writer
  seen, claim, adds 0), so nothing accrued. Not shown reachable; buy_v2/v3, sell and the AMM's own
  volume accounts were not exercised, and whether pump.fun ever runs consecutive seasons is unknown.
  Treated as a latent observation, not a confirmed exploit.
