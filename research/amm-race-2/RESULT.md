# AMM race 2: more closure placements on top of the 648 packet

Base is `research/amm-race` (u1, 648/785, 128 raw-exact). Same toolchain, `build.sh`
and remap flags (`../amm-race/remap-path-prefix.txt`). The metric is the lalalune window metric
(`tools/measure.py`, copied from `fees-sharing-slice-recovery/verify.py`).

| build | matched | raw-exact |
|---|---:|---:|
| upstream published | 599 | 125 |
| u1, rebuilt and measured before any change (`u1-baseline-rebuild.json`) | 648 | 128 |
| **u2 (this packet, `u2-placed.json`)** | **657** | **128** |

Nothing was lost from the matched set or the raw set. The gained deployed windows, by byte address, are:
189024, 189544, 215952, 216472, 216992, 237968, 262400, 312128, 734304.

## Changes (`closure-placement-2.patch`, u1 src -> u2 src)

| site | change | matched before -> after | kept |
|---|---|---|---|
| buy 395 | join `.checked_sub(old_accrued).ok_or_else(\|\| error!)` onto line 395; move the try_from map_err closure to 404 and pad to keep line 411 | 648 -> 649 | yes |
| sell 183 | same pattern: real_quote check on 183, `total` closure on 196, padded so line 206 is unchanged (first try landed on 195: no net gain, reverted) | 649 -> 650 | yes |
| create_pool 290 | `require!(liquidity >= 100, TooLittle..); liquidity - 100` becomes `liquidity.checked_sub(100).ok_or_else(\|\| error!(TooLittlePoolTokenLiquidity))?`, placed on 290. The check and the error code are the same. | 650 -> 651 | yes |
| create_pool 339 (Truncation, 696 B) | joined the `CreatePoolEvent` struct fields and the first 21 event-literal lines so the `initial_liquidity` map_err sits on 339 | 651 -> 652 | yes |
| withdraw 162/166/170 | the candidate already had O,T,O; it was only 4/4/3 lines too low. Joined the `checked_mul` closure onto 162 and moved the next two up, with padding so line 175 is unchanged | 652 -> 655 | yes |
| multi_hop 307 | `remaining[start*5..i*5]` becomes `remaining.get(start*5..i*5).ok_or_else(\|\| error!(NotEnoughRemainingAccounts))?`, placed on 307. Two expressions below were joined to keep the line count. **FLAG:** this adds a check. It cannot fire, because `i <= count` and `len == 5*count`, so behavior is unchanged, but it is a new check. | 655 -> 656 | yes (flagged) |
| buy 409 | the inner `.checked_add(old_virtual).ok_or(Overflow)?` becomes `.ok_or_else(\|\| error!(Overflow))?` on 404, and the try_from map_err moves to 409. Same error code. | 656 -> 657 | yes |
| multi_hop 941 | not placed. The deployed closure sits after the event emission in a helper our source does not split out. No candidate has the same behavior. | - | - |
| 0x89d0 (no error tuple) | not investigated | - | - |

None of these changes uses a macro with a hardcoded file or line. All placement is real code on the deployed line, using newlines or joined lines.
`ok_or(E)?` and `ok_or_else(|| error!(E))?` produce the same error code. The `error!` form also logs the file and line.

Reproduce: start from the amm-race tree (u1), apply `closure-placement-2.patch`, then run
`EXTRA="$(cat ../amm-race/remap-path-prefix.txt)" ./build.sh u2 <tree>`.
