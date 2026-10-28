# chantier-T3: `SharingConfig` deserialize in `lib.rs`, 0x115e70 matched

Refs T3 (#17, pump Anchor wrappers) and #19. Stacks on `chantier-T3-reserved-fees` (#51).

## What the deployed program does

The deployed window `0x115e70` (744 B, `SharingConfig::try_deserialize`) raises 3002 (`AccountDiscriminatorMismatch`) with an `anchor_lang::error::Location` built inline from `programs/pump/src/lib.rs` (length 24), `line` = **84**. The candidate defined the impl in `distribution.rs`, so the window carried that path (length 33) and line 17.

## Change

- `source.patch`:
  - `lib.rs` lines 82 to 85 (previously blank): `impl AccountDeserialize for distribution::SharingConfig`, body unchanged and joined onto four lines so the `error!(..AccountDiscriminatorMismatch)` sits on line 84.
  - `distribution.rs` lines 10 to 26 become blank, so every other line in both files keeps its number.
- `ordered-ld.patch`: the impl now lives at the crate root, which changes its mangled name and the impl disambiguators of later crate-root impls. 13 selectors are renamed in place, so placement order is unchanged.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-reserved-fees` | 826 | 161 | `7f0607972851da19a51aa02664d8cfbcd0a64736697ae6f31050268eda75c482` |
| this packet | **827** | **161** | `b03922b4f3edeed92bc8cadf63ca78104777582c39ccdb4981ac6a61ecb5ae76` |

Gained matched: `0x115e70`. Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `call_only_raw_fail` 205 to 205, `potential_if_delta0` 366 to 366, `unique_pairs` 825 to 826, `intervals_nonzero` 92 to 92.

The neighbouring deployed windows `0x1156f0` (lib.rs:84) and `0x1091b0` (lib.rs:83) are `try_deserialize` bodies for account types with discriminators the candidate does not define yet.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
