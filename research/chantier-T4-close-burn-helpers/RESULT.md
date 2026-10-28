# chantier-T4: pool-authority close and LP burn helpers in `migrate` and `migrate_v2`, 0x48710 and 0x55630 matched

Refs T4 (#18, equalize function sizes). Stacks on `chantier-T4-refund-seeds` (#31).

## What the deployed program does

The `migrate_v2` handler `0x49888` ends with four out-of-line calls before `refund_pool_authority` (`0x56658`):

- `0x54f30` (1792 B), called twice: `(a, bump, a.pool_authority_mint_account, &a.base_token_program)` and, inside the quote block after the withheld-fee harvest, `(a, bump, a.pool_authority_quote_account, &a.quote_token_program)`. It builds the signer seeds `[b"pool-authority", base_mint, [bump]]` and calls `anchor_spl::token_2022::close_account` (`0x181428`) with `destination = a.withdraw_authority`, `authority = a.pool_authority`.
- `0x55d30` (2344 B), `(a, bump)`: borrows `a.user_pool_token_account.data`, unpacks it with `StateWithExtensions::<spl_token_2022::state::Account>::unpack` (error mapped through `From<ProgramError>`), drops the borrow, builds the same seeds and calls `anchor_spl::token_2022::burn` (`0x180cc0`) on `a.lp_mint` with the unpacked `amount`, program `a.token_2022_program`.
- `0x55630` (1792 B), `(a, bump, a.user_pool_token_account)`: same body as `0x54f30` with the program read from `a.token_2022_program`.

Call order in the handler: `0x54f30` (base), quote block (`0x54f30` quote), `0x55d30`, `0x55630`, then `refund_pool_authority`.

The `migrate` handler `0x3fb70` has the same tail: `0x48e10` (2296 B, burn) and `0x48710` (1792 B, close of the LP account with `a.token_2022_program`), then `0x49708` (`migrate::refund_pool_authority`). `0x48128` (1512 B, the base/quote close pair) has a different body and is not covered here.

The baseline issued these CPIs inline in `execute` (raw `invoke_signed` with tag 9 for close, `anchor_spl::token_2022::burn` with a raw slice read of the amount), so no candidate function existed for any of these windows.

## Change

- `source.patch`:
  - `migrate_v2.rs`: three `#[inline(never)]` helpers appended at the end of the file: `close_pool_authority_account(a, bump, account, token_program)`, `close_lp_account(a, bump, account)` and `burn_lp(a, bump)`. Seeds are built as the single-arm `match` scrutinee used by `refund_pool_authority`. The close helpers call `anchor_spl::token_2022::close_account` with the same accounts as before (account, `withdraw_authority`, `pool_authority`). `burn_lp` reads the amount through `StateWithExtensions::<Account>::unpack` on the borrowed account data, as the deployed program does, then calls `anchor_spl::token_2022::burn`. The four inline CPIs in `execute` are replaced by calls to these helpers in the deployed order.
  - `migrate.rs`: `close_lp_account(a, bump, account)` and `burn_lp(a, bump)` with the same bodies over `Migrate` (`a.mint` seeds), replacing the inline burn and LP close. The base/quote close loop is unchanged.
  - Existing lines are replaced in place and the helpers are appended after the last line, so every existing line number in both files is unchanged.
- `ordered-ld.patch`: `migrate::close_lp_account` and `migrate::burn_lp` placed before `migrate::refund_pool_authority`; `migrate_v2::close_pool_authority_account`, `migrate_v2::close_lp_account` and `migrate_v2::burn_lp` placed between `migrate_v2::quote_amount` and `migrate_v2::refund_pool_authority`.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| refund-seeds (#31) | 800 | 161 | `10108020c61f670c4418da7850d2f5cf7a011adcdcd541f31a095c23ea5a9bb4` |
| `migrate_v2` helpers, burn amount via `TokenAccount::try_deserialize`, placed | 801 | 161 | `76660762394129bf442a7d4e31e4256f8a2611396e017770eade701d1c5229d4` |
| `migrate_v2` helpers, burn amount via `StateWithExtensions::unpack`, placed | 801 | 161 | `288d698dee1e14f878c0adad13acfaf1d234a50b12eaea4e3e2e2eb7cc51636b` |
| plus `migrate` helpers, unplaced | 802 | 161 | `30eded32cdcfda41c925c93a0ca382a67435487f0bc39f5118a2ebef039e6924` |
| plus `migrate` helpers, placed (this packet) | **802** | **161** | `c964dbd9835c98f1d8456a775c6d073c477548e927ae01c39718d1610878bf68` |

Gained matched: `0x48710`, `0x55630`. Gained raw: none. Lost: none.

Landing (candidate): `migrate::close_lp_account` `0x341f8` (1792 B), `migrate::burn_lp` `0x348f8` (2312 B), `migrate::refund_pool_authority` `0x35200`; `migrate_v2::quote_amount` `0x35790`, `close_pool_authority_account` `0x35908` (1800 B), `close_lp_account` `0x36010` (1792 B), `burn_lp` `0x36710` (2360 B), `migrate_v2::refund_pool_authority` `0x37048`.

Remaining gaps: `close_pool_authority_account` is one instruction longer than `0x54f30` (the deployed body loads the token program through the `&Interface` argument, the candidate receives the inner pointer directly). Both `burn_lp` bodies are two instructions longer than `0x48e10` / `0x55d30` (the candidate keeps the `user_pool_token_account` pointer in a stack slot where the deployed body reloads it from `a`).

Drift solver: `call_only_raw_fail` 205 to 205, `potential_if_delta0` 366 to 366, `unique_pairs` 799 to 801, `intervals_nonzero` 86 to 88 (the two new pairs split their intervals; their unmatched neighbors differ in size by 8 and 16 bytes).

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
