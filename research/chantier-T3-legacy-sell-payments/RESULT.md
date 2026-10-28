# chantier-T3: legacy sell lamport moves through curve quote helpers, 2 windows matched

Refs T3 (#17, pump Anchor wrappers) and #19. Stacks on `chantier-T3-legacy-buy-payments` (#64).

## What the deployed program does

- The legacy sell body moves lamports out of the bonding curve through the shared `trade::quote_payments` helpers instead of inline `sub_lamports`/`add_lamports` pairs:
  - creator fee to the creator vault: `move_native`
  - sale proceeds to the user: `transfer_native_unchecked`
  - buyback fee to the buyback recipient: `move_native`
- Each call is guarded by its `!= 0` check at the call site. The cashback branch and the protocol fee stay inline.

## Change

- `source.patch`: same-line replacements in the legacy sell body in `lib.rs`. The curve debit for the creator fee moves inside the cashback branch. Line count unchanged.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-legacy-buy-payments` | 888 | 162 | `903cc6e9db20c4608c9556d99e5b42879a8b87d0bc9eb93c0a9c9ac4481e93fc` |
| this packet | **890** | **162** | `e308790de6e769912b88eb5e4484eb38b5b9875ff95c3b3053cd693cc66d72f3` |

Gained matched (2): `0x95f38`, `0x96280` (`move_native` instances). Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `unique_pairs` 887 to 889, `intervals_nonzero` 128 to 130.

No `ordered.ld` change.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Call shape ported from [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), `main@6e6ac0fe` (`programs/pump/src/lib.rs`, legacy sell).
