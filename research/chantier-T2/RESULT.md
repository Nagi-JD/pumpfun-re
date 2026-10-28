# chantier-T2: full drift map (pump, native s7p)

`drift-map.json` lists all 77 intervals with `delta != 0` between consecutive uniquely paired functions, in deployed address order, ranked by the call-only raw-fail windows each one keeps locked. Each interval carries its class, the rule that assigned it, both anchors, gap sizes, the unmatched deployed windows (with the unpaired candidate windows of identical size) and the unmatched candidate windows. A second list, `data_reloc`, holds the 431 matched raw-fail windows whose diff touches an `lddw` slot (input for T5).

Generator: `drift_map.py`, built on `tools/drift_solver.py` (#22). Human-readable table: `drift-map.md`.

## Classes

| class | intervals | call-only locks (sum, overlapping) | sum abs delta (B) |
|---|---:|---:|---:|
| anchor_wrapper | 6 | 591 | 63288 |
| monomorph | 30 | 2123 | 189792 |
| order_island | 24 | 1594 | 25975960 |
| source_fn_size | 17 | 1156 | 156184 |

Rules, first match wins:
- `order_island`: candidate right anchor precedes the left anchor, or `|delta|` exceeds a quarter of `.text`. These come as cancelling pairs (a paired body placed away from its deployed neighbourhood) and feed T6.
- `anchor_wrapper`: a symbol in the gap is an Anchor `try_accounts`, `try_deserialize`, `AccountsExit::exit` or `Accounts` impl. Feeds T3.
- `monomorph`: a symbol in the gap is a generic instantiation (`core`, `alloc`, `borsh`, `anchor_lang` paths, `FnOnce` shims, closures), or a deployed gap window has the size of an already paired window.
- `source_fn_size`: remaining intervals. Feeds T4.

Gap symbols are the candidate names inside the candidate gap, plus the unpaired candidate window when exactly one has the size of a deployed gap window.

## Top intervals

| rank | locks | class | delta | deployed interval |
|---:|---:|---|---:|---|
| 1 | 162 | monomorph | -616 | `0x199bf8`..`0x19a020` |
| 2 | 158 | monomorph | -664 | `0x17c548`..`0x17cae8` |
| 3 | 158 | monomorph | -3424 | `0x18f7a8`..`0x1909f8` |
| 4 | 156 | anchor_wrapper | -1936 | `0x17bc38`..`0x17c3d8` |
| 5 | 156 | anchor_wrapper | -896 | `0x19e090`..`0x19e730` |
| 6 | 154 | monomorph | -1040 | `0x163bf0`..`0x1642b8` |
| 7 | 154 | order_island | 556568 | `0x177138`..`0x1774f8` |
| 8 | 154 | order_island | -557608 | `0x177700`..`0x177908` |
| 9 | 152 | source_fn_size | -2664 | `0x184a60`..`0x1858a0` |
| 10 | 94 | monomorph | -40 | `0x1ab1f8`..`0x1ab248` |
| 11 | 73 | anchor_wrapper | -51368 | `0x107f78`..`0x116158` |
| 12 | 73 | monomorph | -8712 | `0x116158`..`0x118920` |

Root interval (first `delta != 0` in address order): `0x2930`..`0x2ca8`, `delta` -232, deployed window `0x2bc0` (232 B) without candidate counterpart.

## Measure (native s7p)

| | before | after |
|---|---:|---:|
| matched | 786 | 786 |
| raw (exact) | 137 | 137 |
| unmatched | 249 | 249 |

Program source equals the s7p baseline. Clean native rebuild (platform-tools v1.44 `cargo build`, strip with v1.52 `llvm-objcopy`) reproduces candidate sha256 `d51bb0650c4f6e2ff945001d79c49d299045b7bc8428f97bac9d71d92d67dcf7` and symbols sha256 `fc1968de412baaa7a315d2d929dce40ba2d024b282ab5307f5ff1e7e12ce35b2`.

## Reproduce

```
python3 research/chantier-T2/drift_map.py evidence/original/pump/deployed.so s7p-symbols.so \
  --cand-stripped s7p-candidate.so -o research/chantier-T2/drift-map.json --md research/chantier-T2/drift-map.md
```

Build steps for the s7p artifacts: `research/chantier-T0/tools/build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
