# chantier-T1: transfer-fee post_fee_amount Location line, 1 window matched

Refs T1 (SPECS §4.1, `util/transfer_fee.rs` re-lines) and #19. Stacks on `chantier-T1-curve-apply-lines` (#78).

## What the deployed program does

- `util/transfer_fee.rs` holds the Token-2022 transfer-fee helpers. `calculate_fee` returns zero when the mint has no fee and otherwise the epoch fee for the amount.
- `post_fee_amount` is an out-of-line helper that subtracts that fee from the amount, reporting `Overflow` on `util/transfer_fee.rs` line 56.
- The v3 exact-quote buy computes its spendable quote after the transfer fee through `post_fee_amount`.

## Change

- `source.patch`:
  - new `util/transfer_fee.rs` with `calculate_fee` (line 5) and `#[inline(never)] post_fee_amount` (lines 53 to 57), declared from `lib.rs` line 63 as `transfer_fee_recovered` (the line was blank).
  - `trade_v3.rs`: the exact-quote buy gets its post-fee spendable amount from `quote_post_fee_amount` (line 909), an inline adapter from the cached fee snapshot to `post_fee_amount` (line 1311, previously blank).

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T1-curve-apply-lines` | 905 | 162 | `7e71290795a8a8096b654ada33d25cd6c81eac73edc960cd9cf32adbea571096` |
| this packet | **906** | **162** | `0fbc0ebb632522bc94204d008926f6def6e6859c9ec2569118607af0b030ed09` |

Gained matched (1): `0x950e0` (`post_fee_amount`). Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `unique_pairs` 904 to 905, `intervals_nonzero` 140 to 141.

No `ordered.ld` change.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Shapes from [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), `main@6e6ac0fe` (`programs/pump/src/util/transfer_fee.rs`, `trade_v3.rs`).
