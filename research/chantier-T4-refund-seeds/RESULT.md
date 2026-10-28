# chantier-T4: inline signer-seed temporaries in `refund_pool_authority` (`migrate` and `migrate_v2`), 0x49708 and 0x56658 matched

Refs T4 (#18, equalize function sizes). Stacks on `chantier-T4-harvest-withheld` (#30).

## What the deployed program does

- `0x56658` (384 B) is `migrate_v2::refund_pool_authority`. Callers: `0x4ac10` in `0x49888` (the `migrate_v2` handler) and `0x54808` in `0x52660` (the boost-liquidity block of `migrate_v2`). It returns early on `amount == 0`, otherwise calls `0x8c770` (`migrate::transfer_native`) with the signer seeds `[b"pool-authority", base_mint, [bump]]`.
- `0x49708` (384 B) is `migrate::refund_pool_authority`, same body with `mint`. Its only caller is `0x40740` in `0x3fb70`.
- Frame layout in both: the outer `[&[&[u8]]; 1]` at `r10-0x68`, the seed array `[&[u8]; 3]` at `r10-0x58`, the mint key copy at `r10-0x28`, the bump byte at `r10-0x1`. The `system_program` field load (`[a + 0x40]`) is scheduled after the seeds are built.

The baseline bound `mint`, `bump` and `signer_seeds` with `let` before the call. The key and bump locals were allocated first, so the frame came out as seeds at `r10-0x30`, outer at `r10-0x40`, bump at `r10-0x41`, key at `r10-0x68`. Same instruction count and size, different normalized bytes, so both windows stayed unmatched.

## Change

- `source.patch`: in both `refund_pool_authority` bodies, the seeds are built as one expression `&[&[&b"pool-authority"[..], mint.key().as_ref(), &[bump][..]][..]]`, the scrutinee of a `match` whose single arm calls `crate::migrate::transfer_native(...)`. The temporaries are created in the deployed order (outer, seed array, key, bump) and live for the whole call, and the `system_program` argument is evaluated after them. Same callee, same arguments, same seeds, same early return. Each edit replaces two lines with one line plus an empty line, so every line number in both files is unchanged.
- `ordered-ld.patch`: empty. Both functions keep their existing `ordered.ld` slots (symbol hashes `h3015e1e66d769fc0` and `h805c04c892222bce` unchanged).

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| harvest-withheld (#30) | 798 | 161 | `b19d4c722b3a13281ee0aaca73f210eddab5b29fb1f3b8e8aa8fa2075fb1d6f2` |
| seeds in a call argument (no `match`) | 798 | 161 | `32cc9a3cf9f193ba5b709cbab7b345171a38b40e30d4a42e8caca663458c2007` |
| seeds as `match` scrutinee (this packet) | **800** | **161** | `10108020c61f670c4418da7850d2f5cf7a011adcdcd541f31a095c23ea5a9bb4` |

The intermediate row fixes the frame layout but loads `system_program` before the seeds, so the bytes still differ.

Gained matched: `0x49708`, `0x56658`. Gained raw: none. Lost: none.

Landing: `migrate::refund_pool_authority` at candidate `0x349f8`, `migrate_v2::refund_pool_authority` at candidate `0x35100`, both 384 B, same slots as the baseline.

Drift solver: `call_only_raw_fail` 205 to 205, `potential_if_delta0` 366 to 366, `unique_pairs` 797 to 799, `intervals_nonzero` 84 to 86 (the two new pairs split their intervals; in the deployed order `0x56658` follows `0x54f30`, `0x55630` and `0x55d30`, which have no candidate yet).

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
