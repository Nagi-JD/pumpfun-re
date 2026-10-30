# chantier-T3: buy_exact_quote post fill helpers split out, 2 windows matched (921/163)

Refs T3 (SPECS §5). Stacks on `chantier-T3-pre-fee-amount`.

## What the deployed program does

- `0x80df8` is the v3 buy cost helper: buyback split (zero in mayhem mode), first fill cost plus post fill cost, net pool quote, Token-2022 gross pool quote through `pre_fee_amount`, quote transfer fee. Overflow sites at lines 371, 375 and 382.
- `0x80488` subtracts the protocol and creator fees from an amount, Overflow at line 294.
- `0x806c8` derives the post fill net quote from an amount and the fee basis points (creator basis points apply when the creator is set): `BuyNotEnoughSolToCoverFees` at line 317, two `fee` calls, a saturating cost and a `BuySlippageBelowMinTokensOut` site at line 326.
- `0x834c8` is the post fill base output: `quote - 1` through `constant_product::output` against the pool reserves, Truncation at line 591.
- `0x83088` builds the post fill estimate for `buy_exact_quote` (estimate below 2 or base 0 gives `None`), calling `0x806c8`, `0x80488` on the exact path and `0x834c8`.
- `0x837a8` fits the post fill to the budget: it loops over `0x80df8`, shrinks the post fill quote by the excess while it stays above 1, recomputes the base with `0x834c8`, and falls back to the first fill cost when the fit fails.

## Change

- `source.patch`:
  - `trade_v3.rs`: `v3_buy_cost`, `v3_sub_fees`, `v3_net_quote`, `v3_post_base`, `v3_post_fill` and `v3_fit_post` as `#[inline(never)]` functions; `V3PostFill` carries the pool reserves; `trade::buy` computes its pool quote and buyback through `v3_buy_cost`; `buy_exact_quote` calls `v3_post_fill` and `v3_fit_post` for the crossing case.
  - `lib.rs`: `v3_buyback_fee`, the buyback share of a protocol fee.
- `ordered.ld`: identical to the `chantier-T3-pre-fee-amount` file; `ordered-ld.patch` is empty.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-pre-fee-amount` | 919 | 163 | `4f257fdc235936365e8d3b014eac164192a22b15c16c1df19e866f9a07c1d1dc` |
| this packet | **921** | **163** | `7134efde2dad4f77d98d77c083c4ebf32012e1e99e541ffd0efdcd126322758e` |

Gained matched (2): `0x80488` (`v3_sub_fees`), `0x834c8` (`v3_post_base`). Lost matched: none. Gained raw: none. Lost raw: none.

Helper windows (best instruction ratio against the deployed window):

| deployed | size | function | candidate size | ratio |
|---|---:|---|---:|---:|
| `0x80df8` | 2120 | `v3_buy_cost` | 2160 | 0.9495 |
| `0x80488` | 576 | `v3_sub_fees` | 576 | 1.0 |
| `0x834c8` | 736 | `v3_post_base` | 736 | 1.0 |
| `0x806c8` | 1840 | `v3_net_quote` | 1848 | 0.9718 |
| `0x83088` | 1088 | `v3_post_fill` | 1032 | 0.8906 |
| `0x837a8` | 1112 | `v3_fit_post` | 1128 | 0.8143 |

Drift solver: `unique_pairs` 918 to 920, `intervals_nonzero` 89 to 95, `call_only_raw_fail` 239, `potential_if_delta0` 402.

Details: `measure.json`. Recipe: `build-recipe.md`.
