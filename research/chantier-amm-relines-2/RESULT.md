# chantier-amm-matched: trade_v2.rs Location re-line batch 2 (+4 matched)

Line-placement-only reconstruction of 4 same-side normalized-UNMATCHED PumpSwap
(`pump_amm`) windows in `instructions/swap/trade_v2.rs` on the `amm-r34-verified` g3
profile. Each window's sole divergence from its deployed twin was the baked anchor
`Location{line}` immediate; fixed by moving the `error!`/`require!` statement onto its
exact deployed source line. No check / arithmetic / control-flow / error-code change; no
file/line-hardcoding macro; deployed `.so` never a build input. The `TradeV2` accounts
struct (line-locked `try_accounts`/`exit` windows) and `validate_cashback_coin` (already
matched at its deployed line) are untouched; only functions after them are re-lined.

## Windows recovered (cand line -> deployed line)

| window (dep) | function | site move(s) |
|---|---|---|
| `0x4f1d8` (324056) | `validate_buyback_token_account` | require_keys_eq 114->138, require_keys_eq 119->146 |
| `0x4ff18` (327448) | `total_quote` | Overflow 145->241 |
| `0x50ca8` (331368) | `BuyResult::total_user_quote` | Overflow 188->302 |
| `0x516e0` (333536) | `calculate_sell_quote` | Overflow 226->376, require_gte 227->377, Overflow 231->385 |

## Measurement (tools/measure.py vs evidence/original/pump_amm/deployed.so)

| state | matched/785 | raw |
|---|---:|---:|
| base (g3 profile, prior chantier) | 685 | 148 |
| + trade_v2.rs re-lines (this batch, standalone) | **689** | **148** |

Composes additively with re-line batch 1 (constant_product + global_config + fees, +10):
combined state measures **699 / 148**. Clean-room reproduced; `lost[]` empty on BOTH the
matched set and the raw set (raw parity 148). PR-only; no `.so`, no secrets. Form oracle
credit: lalalune/pumpfun-source (MIT).

## Reproduce

```sh
cp -r <recovered pump-amm g3 source> $W/programs/pump-amm
patch -p1 -d $W/programs/pump-amm < patches/trade_v2.patch
EXTRA="$(cat r34_r2.remap)" ./build.sh relines2 $W   # tools/measure.py vs deployed.so
```
