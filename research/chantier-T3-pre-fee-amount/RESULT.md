# chantier-T3: v3 buy grosses the pool quote with `pre_fee_amount`, 1 window matched (919/163)

Refs T3 (SPECS §5). Stacks on `chantier-T3-add3`.

## What the deployed program does

- `0x95360` is `transfer_fee_recovered::pre_fee_amount(&Option<Fee>, amount) -> Result<u64>`: the Token-2022 gross amount whose post-fee value is `amount`.
- The v3 buy path computes the pool quote as `pre_fee_amount(fee, net_pool_quote)` and the quote transfer fee as `pool_quote - net_pool_quote`. It does not add a forward `calculate_fee` result to the net amount.
- `pre_fee_amount` was already present in `util/transfer_fee.rs` with `#[inline(never)]`, but had no caller and was not emitted.

## Change

- `source.patch`:
  - `trade_v3.rs`, `trade::buy`: `pool_quote` is `net_pool_quote` for SOL and `quote_pre_fee_amount(&quote_fee, net_pool_quote)?` otherwise; `quote_transfer_fee = sub(pool_quote, net_pool_quote)?`.
  - `trade_v3.rs`: `quote_pre_fee_amount`, an `#[inline(always)]` adapter from the quote fee snapshot to `transfer_fee_recovered::pre_fee_amount`, next to `quote_post_fee_amount`.
- `ordered.ld` (full file) and `ordered-ld.patch` (against the `chantier-T3-add3` `ordered.ld`): one selector for `transfer_fee_recovered::pre_fee_amount`, inserted after `post_fee_amount`, at the deployed slot of `0x95360`.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-add3` | 918 | 163 | `f7f04ff6d9d5fbd23d11e3b3cfe5b94d1febd9f826f1c7b1f9368598e1b3da45` |
| this packet | **919** | **163** | `4f257fdc235936365e8d3b014eac164192a22b15c16c1df19e866f9a07c1d1dc` |

Gained matched (1): `0x95360` (`transfer_fee_recovered::pre_fee_amount`). Lost matched: none. Gained raw: none. Lost raw: none.

Drift solver: `unique_pairs` 917 to 918, `intervals_nonzero` 89, `call_only_raw_fail` 239, `potential_if_delta0` 402.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Ported and adapted from [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), `main@6e6ac0fe` (`programs/pump/src/trade_v3.rs` and `programs/pump/src/util/transfer_fee.rs`: `pre_fee_amount`).
