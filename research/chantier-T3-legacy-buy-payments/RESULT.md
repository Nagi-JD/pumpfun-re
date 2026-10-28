# chantier-T3: legacy buy payments through shared unchecked helpers, 3 windows matched

Refs T3 (#17, pump Anchor wrappers) and #19. Stacks on `chantier-T3-legacy-buy-generic` (#63).

## What the deployed program does

- The legacy buy body moves curve tokens through an out-of-line `transfer_curve_tokens_ref` (curve authority passed by double reference, zero amount returns early).
- The quote payment to the curve and the buyback fee payment go through two out-of-line `user_quote_payments` helpers, `transfer_native_curve_unchecked` and `transfer_native_unchecked`, which issue the system transfer with no zero check. The caller guards each with `> 0`.

## Change

- `source.patch`:
  - `v2_token_transfers.rs`: adds `transfer_curve_tokens_ref`; `buy_v2::token_transfers` is `pub`.
  - `lib.rs`: adds the two unchecked helpers to `user_quote_payments` on a blank line, and the legacy buy body calls the three helpers in place of the inline CPIs. Line count unchanged.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-legacy-buy-generic` | 885 | 162 | `451b503240ef6f475d4737c562e45eaab164f4abdb820afe096d5cf5e11f091d` |
| this packet | **888** | **162** | `903cc6e9db20c4608c9556d99e5b42879a8b87d0bc9eb93c0a9c9ac4481e93fc` |

Gained matched (3): `0x8c2d8` (`transfer_native_unchecked`), `0x8e908` (`transfer_native_curve_unchecked`), `0x91690` (`transfer_curve_tokens_ref`). Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `unique_pairs` 884 to 887, `intervals_nonzero` 125 to 128.

No `ordered.ld` change.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Helpers and call shape ported from [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), `main@6e6ac0fe` (`programs/pump/src/v2_token_transfers.rs`, `programs/pump/src/buy.rs`, `programs/pump/src/lib.rs`).
