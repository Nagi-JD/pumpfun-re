# chantier-T3: legacy buy entries as const-generic execute, 2 windows matched

Refs T3 (#17, pump Anchor wrappers) and #19. Stacks on `chantier-T3-curve-hop-constraint` (#62).

## What the deployed program does

- `buy` and `buy_exact_sol_in` share one legacy buy body, selected at compile time: the body is generic over a `const EXACT: bool`, so each entry gets its own monomorphized copy and the `__global` wrappers pass only the four instruction arguments (`amount`/`spendable_sol_in`, limit, `track_volume`, `partial_fill`) with no extra mode flag.

## Change

- `source.patch`: in `lib.rs`, `legacy_buy_exec::execute` takes `const EXACT: bool` in place of the trailing `exact: bool` argument (`let exact = EXACT;` on the same line), and the two entries call `execute::<false>` and `execute::<true>`. Line count unchanged.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| `chantier-T3-curve-hop-constraint` | 883 | 162 | `6265eae205b3f684060a9e9ec34e033422f073a8766dd43952f2bf152b66928f` |
| this packet | **885** | **162** | `451b503240ef6f475d4737c562e45eaab164f4abdb820afe096d5cf5e11f091d` |

Gained matched (2): `0x12a4e0` (`__global::buy`), `0x12abc8` (`__global::buy_exact_sol_in`). Gained raw: none. Lost matched: none. Lost raw: none.

Drift solver: `unique_pairs` 882 to 884, `intervals_nonzero` 126 to 125.

No `ordered.ld` change.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Entry form ported from [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), `main@6e6ac0fe` (`programs/pump/src/buy.rs`, `programs/pump/src/lib.rs`).
