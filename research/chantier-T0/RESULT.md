# chantier-T0

Publishes `tools/drift_solver.py`, a reusable layout-drift solver for sBPF whole-ELF matching.

Input: `deployed.so` + `candidate-symbols.so` (optional stripped twin for text equality check).
Output JSON:
- `summary.potential_if_delta0` = `exact` + `call_only_raw_fail`
- `top_spoilers`: intervals ranked by how many `call_only` windows they keep locked
- `root`: first interval with `delta != 0` in deployed address order

Interval math: between consecutive uniquely paired functions,
`delta = gap_cand - gap_dep`. For a signed-relative call,
`delta_call` is the sum of those deltas between caller and callee.
A matched window is `call_only_raw_fail` when every differing 8-byte slot is a `call` immediate.

## Measured window metric (native s7p)

| | before | after |
|---|---:|---:|
| matched | 786 | 786 |
| raw (exact) | 137 | 137 |
| unmatched | 249 | 249 |

Program source equals the s7p baseline (`research/pump-r34-bodies-verified`). The deliverable adds the solver; the candidate `.so` is unchanged.

Native s7p candidate sha256 `d51bb0650c4f6e2ff945001d79c49d299045b7bc8428f97bac9d71d92d67dcf7` (see SHA256SUMS). Measure summary: `measure-s7p-summary.json`.

## Solver reference (same native s7p artifacts)

| field | value |
|---|---:|
| matched | 786 |
| exact | 137 |
| call_only_raw_fail | 218 |
| potential_if_delta0 | 355 |
| unique_pairs | 784 |
| intervals_nonzero | 77 |

Root interval:
- `dep_left` `0x2930` → `dep_right` `0x2ca8`
- `delta` `-232` (`gap_dep` 232, `gap_cand` 0)
- unmatched deployed window at `0x2bc0` (232 B)

Full ranking: `drift-s7p-ref.json`.

## Reproduce

See `tools/build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
