# chantier-T2: pump_fees client declaration Location line, 1 window matched

Refs T2 (SPECS §5, client-declaration Location lines) and #19. Stacks on `chantier-T2-fee-config-client` (#82).

## What the deployed program does

- `declare_program!(pump_amm)` sits on `lib.rs` line 83: the generated `GlobalConfig::try_deserialize` reports its discriminator mismatch at line 83.
- `declare_program!(pump_fees)` sits on line 84: window `0x1156f0`, the generated `pump_fees` `FeeConfig::try_deserialize` (744 bytes), reports its discriminator mismatch at line 84.
- The hand-written `SharingConfig` deserializer reports its discriminator mismatch on line 84 as well, so it shares that line with the `pump_fees` declaration.

## Change

- `source.patch` (line counts unchanged):
  - `lib.rs` line 83: `declare_program!(pump_amm);` alone.
  - `lib.rs` line 84: `declare_program!(pump_fees);` followed by the full `SharingConfig` `AccountDeserialize` impl, previously spread over lines 83 to 85.
  - Lines 85 and 86 are blank.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T2-fee-config-client` | 908 | 162 | `f4263d3d5e026003f0db82e1084eddf1b995fd76a553063c0e5b051bf2814f99` |
| this packet | **909** | **162** | `d2cfe83bf22c8d20564cab6c3fa8ef3755d530ec868a6eb9216b1fbf93d2da2a` |

Gained matched (1): `0x1156f0` (`pump_fees` `FeeConfig::try_deserialize`). Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `unique_pairs` 907 to 908, `intervals_nonzero` 149 to 149.

No `ordered.ld` change.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Client declarations follow [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), `main@6e6ac0fe` (`programs/pump/src/lib.rs`).
