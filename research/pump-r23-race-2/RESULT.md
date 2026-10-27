## Round23 packet 2 (2026-10-27): err_at! removed, migrate post-complete quote restored

Stacked on cf3fd4823 (`research/pump-r23-race/`). Same build (`build.sh`, v1.44 direct-path cargo rustc, jobs 3) and the same metric (their analyze.py as `measure.py`) against `deployed.so`.

### Before / after

| State | matched / 1035 | exact | `err_at!` uses |
|---|---:|---:|---:|
| Round23 native rebuild | 712 | 118 | 0 |
| s6 (pure line placement, packet 1) | 753 | 118 | 0 |
| s10 (packet 1 final) | 759 | 118 | 6 (5 sites) |
| **uD (this packet: every err_at replaced by real placement)** | **759** | 118 | **0** |
| **uF (plus the migrate/migrate_v2 restore)** | **761** | 118 | **0** |

Compared with s10, uF loses no matched windows and gains 0x412b8 (migrate.rs:282) and 0x4bf50 (migrate_v2.rs:326). Compared with s6, uD gains the same six windows that s7–s10 gained, and loses none. The exact count is 118 at every step. The measure JSON has no per-window raw hash for the candidate, so the raw set is checked by count only.

### Per site

| Site (deployed origin) | Change | Deployed evidence | matched before → after | Kept |
|---|---|---|---|---|
| buy_v2.rs:498 / :500 | Line 469's `adjusted` closures padded with real newlines to 498 and 500. The same 31 padding lines are removed from line 470's expression, so nothing below moves. The creator-fee add between them (deployed :469) becomes a `fn creator_fee_add_overflow` item on line 469, because its expression sits textually after the 498 closure and evaluation order is kept. | closures 0xac2b8/0xac4c0, Overflow, caller 0x27737 (map) | 759 → 759 (macro-free). An all-closures variant put the middle add at 499 and lost 0x16dc0: 758 | yes |
| create_v2.rs:412 | `pub(crate) fn quote_chain_accounts_required()` on create_v2.rs line 412 (blank tail padding at the end of the file). `nested_create::walk` uses `ok_or_else(crate::create_v2::quote_chain_accounts_required)`, the same fn-item form Round23 already uses for `overflow` in nested_create.rs:19. | 0x19cc0, 6109 QuoteChainAccountsRequired, caller window 99960 (create_v2) | 759 → 759 | yes |
| lib.rs:1037 | `fn protocol_fee_underflow` item placed at the start of lib.rs line 1037 inside legacy sell `execute`. The pf `checked_sub` at line 985 calls it, so evaluation order is unchanged. | 0x1555e0, Overflow, caller 0x2aabc (lib) | 759 → 759 | yes |
| lib.rs:268 | `PumpError` enum lines joined (variants and order unchanged, the one `//` comment became `/* */`) so the enum ends at 267. `fn final_real_sol_reserves_truncation(_:TryFromIntError)` sits on line 268, then blank lines up to the old enum end, so lib.rs stays 1041 lines and nothing moves. set_params uses `map_err(crate::final_real_sol_reserves_truncation)`. | 0x137db8, 6025 Truncation, caller 0x26cf8 (lib; deployed set_params lives in lib.rs 222-270) | 759 → 759, macro removed | yes |
| migrate.rs:282 | `quote = (real_quote_reserves + post_complete_quote_in)` with checked_add, error at 280, then `- pool_migration_fee` with checked_sub, error at 282. Previously it was `real_quote - fee` only. | Deployed pc 32904-32926: `r7 = [bc+0x60] + [bc+0x98]`, carry → closure at 280 (0x410b0); `r7 < fee` → closure 0x412b8 at 282; then `sub64`. 0x60 = real_quote_reserves (our build's migrate loads it there). 0x98 = post_complete_quote_in: our trade_v3 stores the post pair at +0x90/+0x98 back to back. | 759 → 760 (+0x412b8) | yes |
| migrate_v2.rs:326 | Same add (309). The native fee sub moves to 313. The transfer code moves below it. `quote_amount(tmpq) - quote_before` has its error at 326. The non-native branch uses the same sum. Lines after 326 shift +13; no matched window depends on them. | pc 38134-38206: `[bc+0x98]+[bc+0x60]` → 309 (0x4bb40); `native && r8 < fee` → 313 (0x4bd48); two token-amount reads, `r7 < before` → 0x4bf50 (326). | 760 → 761 (+0x4bf50) | yes |

Behavior notes:
- The migrate change is a semantic fix toward deployed: post-complete quote is now included in the migrated quote.
- The fn-item sites keep the same variants, the same evaluation order and the origin produced by `error!` (`file!()`/`line!()`). No literal locations remain in the code.

### Not attempted (still unmatched)

- **buy_v2.rs 959/983.** Deployed (pc 164638-164659 and 165188-165192) runs these inside a `computed > real_token_reserves && partial` branch. Each converts a u128 result from an extra helper call that takes real_token_reserves (call -0x1431a) or computed. Our candidate has no such computation, and reconstructing it would mean re-deriving the partial-fill logic, so it was not done.
- **pump_quote 212/222, trade_v3 1140, lib.rs 629.** Unchanged, for the reasons in packet 1.

Remaining unmatched closures: 10, down from 12.

Files: `round23-noerrat.patch` (full diff vs Round23 source), `step-vs-packet1.patch` (diff vs packet-1 w1), `source/` (final tree = /home/nagi/pumpround23/w_F), `edit.py` and `run.sh` (reproduce: `run.sh A w1 "A A2" fn`, `B w_C B`, …), `measure/u*.json`, `SHA256SUMS`.
