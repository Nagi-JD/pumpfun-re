# chantier-mayhem-trades — close the 6 trade windows (435 → 441/441)

Stacked on `chantier-mayhem-sweeps`. Reconstructs the Anchor source for the six
remaining unmatched Mayhem windows — the legacy pump trade pair, the PumpSwap
(AMM) pair, and the v2 trade pair — reaching **441/441 normalized windows**.

- **Deployed image:** `evidence/original/mayhem/deployed.so`
  SHA256 `a87fa9f866272514e6acb852b668c4a08aeb173d56c883039991d114d1199bdb`
- **Metric / env:** identical to the sweeps packet (`window_map.py` via
  `maymeasure.py`; `mayhem-fg` / `maybuild_fg.sh`, `LDMODE=glob`; crate
  `mayhem-recovered`).

## Measured result (real build, not claimed)

| | matched | raw | unmatched |
|---|---:|---:|---|
| base (after sweeps packet) | 435 | 82 | 6 windows |
| **this packet** | **441** | **82** | **0** |

**Δ matched = +6 (cumulative 432 → 441/441). lost[] = [] on both sets
(raw unchanged at 82).**

Windows closed (deployed vaddr → instruction):

| deployed vaddr | bytes | instruction |
|---:|---:|---|
| 85600  (0x14e60) | 9736  | `buy_pump_swap`  (O0077) |
| 95848  (0x17668) | 17312 | `sell_pump_swap` (O0079) |
| 113672 (0x1bc08) | 13848 | `buy` (legacy)   |
| 127520 (0x1f220) | 12992 | `sell` (legacy)  |
| 140512 (0x224e0) | 18648 | `buy_v2`  (O0083) |
| 159160 (0x26db8) | 18096 | `sell_v2` (O0084) |

## Source change (`source.patch`, 8 files)

The six trade handlers are coupled through the shared `SellEvent` struct (defined
in `pump_interface.rs`) and the trade-math helpers in `state.rs`, so they are one
coherent change:

- **`src/state.rs`** — `initial_trade_output` / `buy_amounts` / `sell_amounts`
  become generic over a `TradeCap` trait (`&u64` reproduces the legacy late-`min`;
  `QuoteCap` applies the v2 early cap); they read reserves from `&BondingCurve`.
- **`src/instructions/pump_interface.rs`** — `SellEvent` becomes `side: bool` with
  the deployed field order; legacy buy/sell price-checks use the `let Some(..) else`
  forms; CPI builders are inlined with `.with_remaining_accounts`.
- **`src/instructions/pump_interface_v2.rs`** — adds `buy_v2_handler` beside
  `sell_v2_handler`; event values use deferred `let x; if native {…} else {…}`
  initialization (reverse-declaration phi order matches the original).
- **`src/instructions/sell_pump_swap.rs` / `buy_pump_swap.rs`** — `effective_quote`
  / `price_check` inline helpers, inline signer seeds, phased event assembly with
  quote-mint bound last.
- **`src/instructions/buy_v2.rs`** — old `handler` removed (routed to
  `pump_interface_v2::buy_v2_handler`).
- **`src/instructions/pump_amm_interface.rs`** — `#[inline(always)]` marker.
- **`src/lib.rs`** — `buy_v2` routes to `pump_interface_v2::buy_v2_handler`.

No ELF bytes are patched. The `curve-accounts` / `Cargo.toml` / IDL layer from the
upstream 441 tree is NOT required for normalized-window identity and is omitted
(it carries an extra `historical_anchor_program` dep and only affects raw / rodata
source coordinates).

## Reproduce

```
LDMODE=glob TD=mayhem-fg/target-repro bash mayhem-fg/maybuild_fg.sh trades <SRC>
python3 mayhem-fg/tools/maymeasure.py mayhem-fg/out/trades-symbols.so
# -> {"matched":441,"raw":82,"unmatched":[]}
```

## Attribution

Source forms ported from upstream public MIT research
(`lalalune/pumpfun-source`, `research/claude-mayhem-441-20261028/sources/source.tar.gz`
and the per-window lane notes in `claude-mayhem-437/439/441`), independently
verified here by real build + measurement on the Nagi Mayhem env.
