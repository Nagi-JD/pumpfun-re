# chantier-T4: whitelist post-trade resync in the buy/sell handlers

Refs T4 (function sizes). Resolves the root interval left by `chantier-T4-with-account-name` (`0x6e78`..`0x7b40`, delta -688): deployed window `0x7890` (688 B) is `anchor_lang::accounts::account::Account<T>::reload` (Anchor 0.31.1), monomorphized for the SPL token account.

## What the deployed program does

`0x7890` has 16 call sites in the deployed `.text`, two per handler body, in all 8 buy/sell bodies (trade v3 `sell`, `buy`, `buy_exact_quote`; `buy_v2` (two monomorphs); `sell_v2`; legacy `buy`; legacy `sell`). Each body compares `user` with `global.whitelist_pda` (`global+0x288`) and, on equality, runs:

1. `associated_bonding_curve.reload()?`
2. `associated_user.reload()?`
3. `bonding_curve.sync_virtual_quote_reserves(associated_bonding_curve.amount, associated_user.amount, &bonding_curve.quote_mint)?`

The TradeEvent is then emitted with the bonding curve's post-resync virtual quote reserves. `sync_virtual_quote_reserves` already exists in the reconstruction (`mayhem_virtual_params.rs`); before this packet only `set_mayhem_virtual_params` called it, so `reload` had no caller and the window was absent.

## Change

- `source.patch`:
  - `mayhem_virtual_params.rs`: `sync_virtual_quote_reserves` becomes `pub(crate)` (body unchanged).
  - `trade_v3.rs`, `buy_v2.rs`, `sell_v2.rs`, `lib.rs` (legacy buy/sell exec): the whitelist resync block above, after the bonding curve update in each handler. The TradeEvent `virtual_sol_reserves` / `virtual_quote_reserves` fields read the bonding curve after the resync. Every edit stays on its existing source line, so `error!` line numbers are unchanged.
- `ordered-ld.patch` (on top of the T4 `ordered.ld`): places `Account<T>::reload` between `exit_with_expected_owner` `h558d33b` and `try_from` `h135ae06`, its deployed neighbours.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| T4 (#24) | 788 | 138 | `ec3f7295a9ef5ad47244c1bf747c02142fe2e22e40a62063ee3630703a0484cd` |
| resync, inserted on new lines, + `ordered-ld.patch` | 774 | 138 | `a5c74fbf382b3291c038764d0234025eee9c9df93bc5b1ccea302578e59a538b` |
| resync on existing lines, + `ordered-ld.patch` | 789 | 138 | `3ab6805231c2139b981e9d6036399b722e6f3e3a46efeccb6d31afed6cd5c875` |
| resync + post-resync event fields, T4 `ordered.ld` | 789 | 138 | `94f16f6f7c351107c0fe6c094d4d6ee8038d72d939d0e97f03a72f3663bec354` |
| resync + post-resync event fields + `ordered-ld.patch` (this packet) | **789** | **138** | `c152d81d7010078e97530d24aaa96715b0f35de68f16cc89f798994d882d7724` |

Gained matched: `0x7890`. Lost: none (matched and raw). The 774 row shows the line-number sensitivity: 15 error closures of 520 B each embed `error!` line numbers.

In this packet's build `reload` sits at `0x7890` and `try_from` `h135ae06` at `0x7b40`, as deployed. The 688 B body is identical to the deployed bytes except 5 call immediates, which point into regions still shifted by downstream drift.

Drift solver: `call_only_raw_fail` 219 → 220, `potential_if_delta0` 357 → 358, nonzero intervals 75 → 74. New root: `0xce88`..`0xd068`, delta -336. Without `ordered-ld.patch` the same source measures 789/138 with 76 nonzero intervals and `reload` placed after the last ordered section.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
