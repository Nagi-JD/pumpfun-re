# chantier-T3: `#[program]` module lines, 6 windows matched

Refs T3 (#17, pump Anchor wrappers) and #19. Stacks on `chantier-T3-volume-accumulator` (#44).

## What the deployed program does

Six deployed windows build an `anchor_lang::error::Location` inline from the `lddw` of `programs/pump/src/lib.rs` (length 24) with a `line` taken from the `#[program]` module:

| window | size | function | deployed line | candidate line |
|---|---:|---|---:|---:|
| `0x120628` | 1376 | `__idl_write` | 90 | 66 |
| `0x120c00` | 1240 | `__idl_set_buffer` | 90 | 66 |
| `0x17b780` | 728 | IDL account `try_deserialize` | 90 | 66 |
| `0x135580` | 672 | `toggle_create_v2` | 114 | 90 |
| `0x135820` | 672 | `toggle_cashback_enabled` | 121 | 95 |
| `0x135ac0` | 672 | `toggle_mayhem_mode` | 149 | 105 |

Line 90 is the `#[program]` attribute (the IDL instructions and IDL account carry its span). Lines 114, 121 and 149 are the `require_neq!` of the three toggles.

## Change

`source.patch` rearranges `lib.rs` lines 66 to 172 only:

- `#[program]` moves from line 66 to line 90.
- `toggle_create_v2`, `toggle_cashback_enabled` and `toggle_mayhem_mode` start at lines 113, 120 and 148, so their `require_neq!` sit on 114, 121 and 149.
- `set_reserved_fee_recipients` and `update_buyback_config` are each joined onto one line, and blank lines are redistributed, so the closing brace of the module stays on line 172 and every line after it keeps its number.

Token stream, instruction order and every other file are unchanged. No mangled name changes, so `ordered.ld` is unchanged.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-volume-accumulator` | 815 | 161 | `e4a5ef1016bed9b6eacdd535067f22844835e1da3bf8f491fda1d9924692e1e7` |
| this packet | **821** | **161** | `3873b5d5d02b10138d9565ead76eabe1d4f93ee4ae61efb72049517cdffeb8f5` |

Gained matched: `0x120628`, `0x120c00`, `0x135580`, `0x135820`, `0x135ac0`, `0x17b780`. Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `call_only_raw_fail` 205 to 205, `potential_if_delta0` 366 to 366, `unique_pairs` 814 to 820, `intervals_nonzero` 91 to 91.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
