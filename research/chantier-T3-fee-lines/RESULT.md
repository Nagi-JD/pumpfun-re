# chantier-T3: `util/fee.rs` lines, 0x88908 and 0x88f90 matched

Refs T3 (#17, pump Anchor wrappers) and #19. Stacks on `chantier-T3-global-lines` (#46).

## What the deployed program does

Both windows build the `anchor_lang::error::Location` inline from `programs/pump/src/util/fee.rs`:

| window | size | function | errors and lines (deployed) | candidate lines |
|---|---:|---|---|---|
| `0x88908` | 1672 | `legacy_sell::fee_math::checked_ceil_div` | 6024 @ 17, 6024 @ 15, 6026 @ 19 | 14, 12, 16 |
| `0x88f90` | 712 | `legacy_sell::fee_math::fee` | 6025 @ 34 | 5 |

So in the deployed file `checked_ceil_div` sits 3 lines lower than in the candidate and `fee` follows it, with its `map_err` on line 34.

## Change

`source.patch`, `util/fee.rs` only: `checked_ceil_div` (with its doc comment and `#[inline(never)]`) moves to lines 11 to 20, and `fee` moves after it to lines 32 to 35. Bodies, signatures and attributes are unchanged. No mangled name changes, so `ordered.ld` is unchanged.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-global-lines` | 823 | 161 | `25bde639ab252c3565dc0ed32ca6efa77980c52aa66289419e7b676b8f04f1d9` |
| this packet | **825** | **161** | `0c07f93cd4edf64bedc7810122c81e0a26a8da3598350d884c3edfe328f7cf61` |

Gained matched: `0x88908`, `0x88f90`. Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `call_only_raw_fail` 205 to 205, `potential_if_delta0` 366 to 366, `unique_pairs` 822 to 824, `intervals_nonzero` 91 to 92.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
