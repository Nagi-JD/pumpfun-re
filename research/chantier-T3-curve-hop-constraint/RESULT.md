# chantier-T3: CurveHop try_accounts quote mint constraint order, 1 window matched

Refs T3 (#17, pump Anchor wrappers) and #19. Stacks on `chantier-T3-quote-control-state` (#61).

## What the deployed program does

- `CurveHop::try_accounts` (multi-hop curve swap) checks the bonding curve quote mint as `quote_mint.key() == bonding_curve.quote_mint`, so the 32-byte compare takes the quote mint key as its first operand and the stored curve field as its second. The WSOL fallback for a default quote mint is unchanged.

## Change

- `source.patch`: one line in `multi_hop_curve_swap.rs` swaps the operands of the `CurveHop.bonding_curve` constraint to the lalalune main ordering. Line count unchanged.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-quote-control-state` | 882 | 162 | `4684fae3bcd76b9d9a3c51189d78722ee5ede9eef56780c20ec3344cc49924ff` |
| this packet | **883** | **162** | `6265eae205b3f684060a9e9ec34e033422f073a8766dd43952f2bf152b66928f` |

Gained matched (1): `0xdd700` (`CurveHop::try_accounts`). Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `unique_pairs` 881 to 882, `intervals_nonzero` 126 to 126.

No `ordered.ld` change.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Constraint form ported from [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), `main@6e6ac0fe` (`programs/pump/src/multi_hop_curve_swap.rs`).
