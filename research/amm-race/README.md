# AMM race: error-closure placement on top of upstream 599 checkpoint

Base: upstream `main` 2a2820e26, `programs/pump-amm` (checkpoint
`repro/pump_amm/native-fee-cpi-recovery-20261027`, published 599/785, 125 exact).

| build | matched | exact (raw) | note |
|---|---:|---:|---|
| upstream published | 599 | 125 | their recipe |
| u0: native Linux direct-path v1.44, unchanged source | 617 | 128 | `build.sh` |
| u1: + path remaps + closure line placement | **648** | 128 | +31 over u0, +49 over 599 |

All 34 deployed PumpAmmError 520-byte closures already exist in the upstream
source; they were unmatched only because the `file!()` path and the `line!()`
literals differ. u1 does three things:

1. **Path remaps.** `remap-path-prefix.txt` is passed as rustc args through `EXTRA=`. `src/` maps to
   `programs/pump-amm/src/`, and legacy_buy, legacy_sell, multi_hop, trade and boost_burn map to their
   deployed `instructions/swap/*.rs` and `instructions/boost.rs` paths.
2. **Collision fix.** The real `instructions/swap/sell.rs` and `trade_v2.rs` collided
   with the remap targets: rustc dedups source files by remapped name and fails to
   compile. They are renamed to `*_ix.rs` and loaded with `#[path]`.
3. **Line placement.** Each `error!` is moved to its deployed line by inserting newlines inside the
   closure (`tools/pl.py FILE src:target,...`, which drives `tools/place.py`).

Matched now: deposit 8/8, withdraw 4/7, buy 3/5, sell 3/4, multi_hop 5/7,
trade_v2 1/1, boost 1/1.

Still open:
- **withdraw 162/166/170:** the candidate has one fewer Overflow closure before the Truncation closure.
- **buy 395:** the site falls 2 lines too low, so lines must be joined.
- **sell 183:** same problem as buy 395.
- **buy 409:** belongs to a separate helper.
- **multi_hop 307:** NotEnoughRemainingAccounts. The candidate site 309/325 order doesn't match.
- **multi_hop 941**
- **create_pool 290:** needs `checked_sub(100).ok_or_else(error!(TooLittlePoolTokenLiquidity))`. This worked on the old base and is not applied here yet.

Apply: `git archive main programs/pump-amm | tar -x -C W`, `patch -p? < closure-placement.patch`
(diff is u0/…/src → u1/…/src), rename the two swap files as in the patch, then
`EXTRA="$(cat remap-path-prefix.txt)" ./build.sh u1 W`.
