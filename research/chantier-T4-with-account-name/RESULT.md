# chantier-T4: with_account_name<String> out of line in set_reserved_fee_recipients

Resolves the T0/T2 root interval (`0x2930`..`0x2ca8`, delta -232): deployed window `0x2bc0` (232 B) is `anchor_lang::error::Error::with_account_name::<String>`, and `0xd300` (448 B) is `alloc::fmt::format`, both out of line.

## Why the deployed build keeps them out of line

`with_account_name::<String>` has three callers: `set_params::execute` and two sites in `set_reserved_fee_recipients` (executable check, rent check). LLVM inline remarks on s7p:

| site | callee | cost / threshold | result |
|---|---|---|---|
| executable check | `with_account_name` | 180 / 250 | inlined |
| rent check | `alloc::fmt::format` | 185 / 325 | inlined |
| rent check | `with_account_name` | -14820 / 250 (last-call bonus) | inlined |

The deployed handler body (`0x6fef8`, 9176 B) inlines the executable-check site (format_inner + two String clones) and, on the rent-check site, calls `format` (`0xd300`) and `with_account_name` (`0x2bc0`) out of line. Both costs (185, 180) sit under the default thresholds, so the deployed rent-check site was costed at the cold call-site threshold (45). A diagnostic build with `-Cllvm-args=-cold-callsite-rel-freq=25` reproduces both windows (+`0x2bc0`, +`0xd300`) while regressing elsewhere, confirming that the rent-check error block is cold in the deployed build.

The deployed handler also follows the Anchor `rent_exempt` constraint form: `Rent::get()?` once before the loop, `is_exempt(lamports(), try_data_len()?)`, and `Error::from(ErrorCode::...)` for both errors (`mov r2, 0x7d7` / `0x7d5` into `From<ErrorCode>`).

## Change

- `source.patch` (`programs/pump/src/lib.rs`): the loop in `set_reserved_fee_recipients` takes the deployed constraint form above, and the rent-check error block calls an empty `#[cold] #[inline(never)] fn cold_path()` defined at the end of the file (no line shift). The call marks the block cold for the inliner, then is removed as a no-op; `cold_path` emits no code. Error codes, account names and log output are unchanged; the check order matches the deployed body.
- `ordered-ld.patch`: places the two new sections at their deployed neighbours (`with_account_name::<String>` after `with_account_name` `hb6c5748`, `format` after `String::write_str`).

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| s7p baseline | 786 | 137 | `d51bb0650c4f6e2ff945001d79c49d299045b7bc8428f97bac9d71d92d67dcf7` |
| constraint form only | 786 | 137 | `60025733eab228aa89a25b81344e02acbd49f4b9683a447f1e490d36d7e4da38` |
| + cold marker, stock `ordered.ld` | 788 | 137 | `17c781f4df80b4d86afcd6abe7624c77d81e12b619ea5573ebaded00a6c9910b` |
| + cold marker + `ordered-ld.patch` (this packet) | **788** | **138** | `ec3f7295a9ef5ad47244c1bf747c02142fe2e22e40a62063ee3630703a0484cd` |

Gained matched: `0x2bc0`, `0xd300`. Gained raw: `0xd240`. Lost: none (matched and raw).

Drift solver: `call_only_raw_fail` 218 → 219, `potential_if_delta0` 355 → 357, nonzero intervals 77 → 75. New root: `0x6e78`..`0x7b40`, delta -688.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
