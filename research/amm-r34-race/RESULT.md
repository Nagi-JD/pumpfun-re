# AMM r34 race: beating the newest PumpSwap checkpoint (643) on the window metric

Base: upstream `main` 4df2641ad, `programs/pump-amm` — their maintained source, the
"native-quote and execution" checkpoint referenced by `programs/pump-amm/README.md`
(candidate `be10ca1a…`). Their published claim: **643/785 normalized windows, 148 raw bodies**.

Metric: the lalalune window metric (`tools/measure.py`, copied from
`research/fees-sharing-slice-recovery/verify.py`), candidate `*-symbols.so` vs
`evidence/original/pump_amm/deployed.so`.

Toolchain: native Linux direct-path v1.44 build (`build.sh`); offline cargo home
prepared from the pinned `programs/pump-amm/Cargo.lock`; `--remap-path-prefix`
flags from `r34_r2.remap`. (Their shipped 643 is a macOS recipe build.)

## Step table (all measured; see `measure/*.json`)

| build | matched | raw | eqloc | note |
|---|---:|---:|---:|---|
| their shipped (their recipe) | 643 | 148 | — | `programs/pump-amm/README.md` claim |
| base: native rebuild, unchanged source, **no remap** | 630 | 148 | 92 | plain `build.sh`, no `EXTRA` |
| r1: + base path remap `src/=programs/pump-amm/src/` | 643 | 148 | 125 | reproduces their 643 exactly |
| r2: + `legacy_buy`/`legacy_sell` → `swap/{buy,sell}.rs` remap (+ `_ix` renames) | 643 | 148 | 125 | path fixed, no gain without line placement |
| r3: + `withdraw` closure placement (line-162 skipped) | 647 | 148 | 129 | +4 (213872,214392,214912,215432) |
| r4: + `withdraw` line-162 `checked_mul` join | 650 | 148 | 132 | +3 (215952,216472,216992) |
| **r5: + `legacy_sell` closure placement** | **654** | **148** | **136** | +4 (311088,311608,312128,312648) |

**Final: 654/785 matched, 148 raw. +11 matched over their 643, raw parity (148).**
Nothing was lost from the matched set or the raw set at any step.

Shipped vs native: their recipe's 643 is reproduced natively by r1 — the single
decisive ingredient is the base path-prefix remap `src/=programs/pump-amm/src/`.
A plain native build without it is 630 (13 windows below shipped), not above.

## What they already adopted (vs our older 599-base stack, u2 = 657/128)

- They adopted **none** of our error!-closure line placements and **none** of the
  `_ix` collision renames.
- They **independently** moved `multi_hop` and `create_pool` to the deployed paths
  (`instructions/swap/multi_hop_swap.rs`, `instructions/create_pool.rs`), gaining
  20 raw bodies our u2 lacked: their raw set (148) strictly ⊇ u2's (128).
- Their 643 comes almost entirely from the base path-prefix remap (r1 reproduces it).

## Changes (`amm-r34.patch`, their src → r5 src) — behavior-preserving

1. **`instructions/swap/buy.rs` → `buy_ix.rs`, `instructions/swap/sell.rs` → `sell_ix.rs`**,
   loaded via `#[path]` in `swap/mod.rs`. These deployed-path files are event-struct /
   helper stubs with **zero** error closures, so renaming frees the `buy.rs`/`sell.rs`
   remap targets for the real handlers in `legacy_buy.rs`/`legacy_sell.rs` (remapped
   in `r34_r2.remap`). No dedup collision, no behavior change.
2. **`instructions/liquidity/withdraw.rs`**: the existing Overflow/Truncation/Overflow
   closures moved to their deployed lines 98,106,150,160,162,166,170 by inserting
   newlines inside the closures; the `virtual_reserve.checked_mul(amount as u128)
   .ok_or_else(|| error!(Overflow))` pair joined onto 162. Recovered 7 windows.
3. **`legacy_sell.rs`**: the quote-path closures moved to deployed lines
   128,130,167,179,183,196; the `real_quote ….checked_sub(old_accrued).ok_or_else(||
   error!(Overflow))` pair joined onto 183. Recovered 4 windows.

All placements are real code on the deployed line (newlines / joined lines), same
error codes, same control flow. **No check was removed or weakened; no file- or
line-hardcoding macro was used.** `ok_or(E)?` and `ok_or_else(|| error!(E))?` produce
the same error code (the `error!` form also logs file+line). Each placement restores
a deployed closure-window position — the target lines are the positions at which our
earlier u2 build matched these exact deployed windows (so u2's matched error! line ==
the deployed `line!()`), re-applied to this base's own, structurally-identical
withdraw/sell quote logic.

## Still open (not ported — new-base refactor)

- **buy quote region** (8 windows 202512–206152): the buy handler was refactored on
  this base; its closures no longer map 1:1 to the deployed `buy.rs` closure
  positions, so the older buy restructuring is not directly portable here.
- `multi_hop` 307, `create_pool` 290/339, and misc (142464, 189024, 189544,
  236928–238488, 262400, 280224–282840, 359968, 734304) remain unmatched.

## Reproduce

```sh
W=/path/to/tree
git archive main programs/pump-amm | tar -x -C $W
cd $W/programs/pump-amm && patch -p1 < amm-r34.patch   # their src -> r5 src (incl. buy/sell -> *_ix renames)
# prepare an offline cargo home from $W/programs/pump-amm/Cargo.lock, then:
EXTRA="$(cat r34_r2.remap)" ./build.sh r5 $W
# build.sh strips the .so and runs tools/measure.py against evidence/original/pump_amm/deployed.so
```
