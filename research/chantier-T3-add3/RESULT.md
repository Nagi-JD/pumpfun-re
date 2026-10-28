# chantier-T3: `v3_check::add3` as its own function, 1 window matched (918/163)

Refs T3 (SPECS §5). Stacks on `chantier-T2-token-ext-crate`.

## What the deployed program does

- `0x801f8` is a 3-operand checked add, `a + b + c`, returning `Result<u64>` with `PumpError::Overflow` at `trade_v3.rs` line 285.
- It is not inlined. The v3 buy paths (`buy_v3`, `buy_exact_quote_in_v3` and the shared v3 helpers around them) call it for every three-term cost sum.

## Change

- `source.patch`:
  - `v3_check.rs` line 284/285: `#[inline(never)] pub(super) fn add3(a, b, c) -> Result<u64>`, built from `checked_add` twice and `error!(PumpError::Overflow)`, so the error location is line 285 as in the deployed program.
  - `trade_v3.rs`: the 7 nested `add(add(x, y)?, z)?` sums in `trade::buy` and `trade::buy_exact_quote` call `add3(x, y, z)?`. The `net_quote` sum keeps its two-step form. `use v3_check::{add, add3};`.
- `ordered.ld` (full file) and `ordered-ld.patch` (against the `chantier-T2-token-ext-crate` `ordered.ld`): one selector for `trade::v3_check::add3`, inserted after `validate_trade`, at the deployed slot of `0x801f8`.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T2-token-ext-crate` | 917 | 163 | `76159da3a2421b4da87934845d356cd6f7b72af8646720762553bd2cd357d300` |
| this packet | **918** | **163** | `f7f04ff6d9d5fbd23d11e3b3cfe5b94d1febd9f826f1c7b1f9368598e1b3da45` |

Gained matched (1): `0x801f8` (`trade::v3_check::add3`). Lost matched: none. Gained raw: none. Lost raw: none.

Drift solver: `unique_pairs` 916 to 917, `intervals_nonzero` 88 to 89, `call_only_raw_fail` 239, `potential_if_delta0` 402.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Ported and adapted from [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), `main@6e6ac0fe` (`programs/pump/src/trade_v3.rs`: `add3`).
