# chantier-T1: Global buyback-recipient validation Location lines, 1 window matched

Refs T1 (SPECS §4.1, `lib.rs` re-lines) and #19. Stacks on `chantier-T1-curve-quote-lines` (#75).

## What the deployed program does

- `Global::validate_buyback_fee_recipient` is an out-of-line method that reports `BuybackFeeRecipientMissing` on `lib.rs` line 1879 (`require_keys_neq!` against the default key) and `BuybackFeeRecipientNotAuthorized` on line 1884 (membership in `buyback_fee_recipients`).
- The buy and sell handlers call it instead of repeating the two checks inline.

## Change

- `source.patch` (line counts unchanged):
  - `lib.rs`: `validate_buyback_fee_recipient` added inside the existing `impl Global` block at lines 1877 to 1886; the legacy buy entry points call it.
  - `trade_v3.rs`, `buy_v2.rs`, `sell_v2.rs`: the inline buyback-recipient checks become calls to the method.
  - No new `impl` block, so later impl blocks keep their symbol hashes and `ordered.ld` placement.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T1-curve-quote-lines` | 900 | 162 | `c439531883071d34cde4f913942791afb2d0851ae846694c4ea753e4975c8510` |
| this packet | **901** | **162** | `d2233d419a93d344aeb329ac3d40a8918b73b7aa43f2c8bbba4d8ac624eeb9e9` |

Gained matched (1): `0x98438` (`validate_buyback_fee_recipient`). Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `unique_pairs` 899 to 900, `intervals_nonzero` 139 to 140.

No `ordered.ld` change.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Shapes from [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), `main@6e6ac0fe` (`programs/pump/src/lib.rs`, `trade_v3.rs`, `buy_v2.rs`, `sell_v2.rs`).
