# chantier-T1: bonding-curve reserve and fee accrual Location lines, 3 windows matched

Refs T1 (SPECS §4.1, `lib.rs` re-lines) and #19. Stacks on `chantier-T1-buy-quote-lines` (#77).

## What the deployed program does

- `apply_buy` is an out-of-line helper that debits the virtual and real token reserves and credits the virtual and real quote reserves, reporting `Overflow` on `lib.rs` lines 2496, 2501, 2506 and 2511.
- `apply_sell` is the mirror helper, reporting `Overflow` on lines 2520, 2525, 2530 and 2535.
- `accrue_fees` splits the protocol fee into buyback and retained parts (no buyback in mayhem mode), credits `protocol_fees` (line 2550) and `creator_fee` (line 2554), and returns the buyback part.
- The v2 and v3 trade handlers call these helpers instead of writing the curve fields inline.

## Change

- `source.patch` (line counts unchanged):
  - `lib.rs`: new `#[inline(never)]` free functions `apply_buy` (lines 2494 to 2513), `apply_sell` (2518 to 2537) and `accrue_fees` (2541 to 2556).
  - `trade_v3.rs`: the sell and exact-quote buy paths update the curve through `apply_sell` / `apply_buy` and `accrue_fees` (twice on the exact-quote path, for the first fill and the post-complete fill).
  - `buy_v2.rs`, `sell_v2.rs`: the curve reserve writes become `apply_buy` / `apply_sell` calls.
  - Free functions rather than new `impl` blocks, so later impl blocks keep their symbol hashes and `ordered.ld` placement.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T1-buy-quote-lines` | 902 | 162 | `0a7e646406dd161973c04bb00ab8c60a339f55aca2b81817e1d615df59fda0cb` |
| this packet | **905** | **162** | `7e71290795a8a8096b654ada33d25cd6c81eac73edc960cd9cf32adbea571096` |

Gained matched (3): `0xa0bf0` (`apply_buy`), `0xa13e0` (`apply_sell`), `0xa1bd8` (`accrue_fees`). Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `unique_pairs` 901 to 904, `intervals_nonzero` 140 to 140.

No `ordered.ld` change.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Shapes from [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), `main@6e6ac0fe` (`programs/pump/src/lib.rs`, `trade_v3.rs`, `buy_v2.rs`, `sell_v2.rs`).
