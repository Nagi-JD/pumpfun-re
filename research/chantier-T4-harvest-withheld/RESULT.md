# chantier-T4: `anchor_spl` transfer-fee harvest CPI in `migrate_v2`, `TransferFeeInstruction::pack` at 0x18fc98 and `harvest_withheld_tokens_to_mint` at 0x1905a8

Refs T4 (#18, equalize function sizes). Resolves the interval `0x18f7a8`..`0x1909f8` (delta -3424, 165 call-only spoiled windows) and the interval `0x184a60`..`0x1858a0` (delta -2664, 159 call-only spoiled windows) left by `chantier-T4-transfer-with-seed`.

## What the deployed program does

- `0x18fc98` (2320 B) is `spl_token_2022::extension::transfer_fee::instruction::TransferFeeInstruction::pack`. It grows its output `Vec<u8>` through `0x18ec88` and `0x18e878`.
- `0x1905a8` (1104 B) is `spl_token_2022::extension::transfer_fee::instruction::harvest_withheld_tokens_to_mint`: `check_program_account`, metas `[mint writable]` plus each source writable, data `TokenInstruction::TransferFeeExtension` (`0x191338`) followed by `TransferFeeInstruction::pack` (`0x18fc98`). Both sit between `metadata_pointer::instruction::initialize` (`0x18f7a8`) and `transfer_hook::instruction::initialize` (`0x1909f8`).
- `0x184e38` (2664 B) is `anchor_spl::token_2022_extensions::transfer_fee::harvest_withheld_tokens_to_mint`, the only caller of `0x1905a8`. It runs `invoke_signed` with `[token_program_id, mint]` plus the sources. It sits between `token_metadata_update_authority` (`0x184a60`) and `transfer_hook_initialize` (`0x1858a0`).
- `0x95610` (1480 B), the only caller of `0x184e38`, is a pump helper taking `(token_program, mint, source)`. It builds `CpiContext::new(token_program, HarvestWithheldTokensToMint { token_program_id: token_program, mint })` with `vec![source]` and returns the `anchor_spl` result. Its only caller is `0x4b068` inside `0x49888`, the `migrate_v2` handler (`programs/pump/src/migrate_v2.rs`): when the quote mint carries the Token-2022 transfer fee extension, after the `QuoteMintNotWritable` (6110) check, the withheld fees of the temporary quote account are harvested to the quote mint.

In the baseline the same harvest was emitted as a raw `call(&qt, [(quote_mint, writable), (temp_quote, writable)], vec![26, 4])`, so the `anchor_spl` wrapper, the `spl_token_2022` builder and `TransferFeeInstruction::pack` were never instantiated.

## Change

- `source.patch`: line 331 of `migrate_v2.rs` calls `harvest_withheld(&qt, &wsol, &tmpq)` in place of the raw `call`, on the same line, so every `err!` / `require!` line number is unchanged. `harvest_withheld` (`#[inline(never)]`, appended after the last line) calls `anchor_spl::token_2022_extensions::harvest_withheld_tokens_to_mint(CpiContext::new(token_program.clone(), HarvestWithheldTokensToMint { token_program_id: token_program.clone(), mint: mint.clone() }), vec![source.clone()])`. The CPI is the deployed one: program Token-2022, data `[26, 4]`, metas quote mint writable and temporary quote account writable, no signer seeds.
- `ordered-ld.patch` (on top of the T4 `ordered.ld` from #29): places `migrate_v2::harvest_withheld` (`hd13246a377082940`) right before `trade::quote_payments::transfer_native` (`h5f18ae913c082bd0`), the `anchor_spl` wrapper (`hc91da26ce2a822ab`) right after `token_metadata_update_authority`, and `TransferFeeInstruction::pack` (`h76088c49f144eab6`) then `harvest_withheld_tokens_to_mint` (`h9df957f235c92181`) right after `metadata_pointer::instruction::initialize`, their deployed neighbours.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| transfer-with-seed (#29) | 794 | 148 | `31162d65ed5a56fb60c2beaa62b754b758516411b7b07149c96616bf578f8ae2` |
| harvest, #29 `ordered.ld` (no placement) | 798 | 148 | `c730d31e5af5e4c023389c3fd7eda81217a499c82827d1076c73425ddacc7e37` |
| harvest + `ordered-ld.patch` (this packet) | **798** | **161** | `b19d4c722b3a13281ee0aaca73f210eddab5b29fb1f3b8e8aa8fa2075fb1d6f2` |

Gained matched: `0x95610`, `0x184e38`, `0x18fc98`, `0x1905a8`. Gained raw: `0x17ddb0`, `0x17df20`, `0x17f948`, `0x186760`, `0x1891d8`, `0x189340`, `0x189488`, `0x1895e8`, `0x18e878`, `0x18e9c0`, `0x18eb28`, `0x18ec88`, `0x18fc98`. Lost: none.

Landing in this packet's build, each with the same deployed-minus-candidate offset as its placed neighbours:

| function | deployed | candidate | offset | neighbour check |
|---|---|---|---|---|
| `migrate_v2::harvest_withheld` (1480 B) | `0x95610` | `0x56f68` | `0x3e6a8` | `transfer_native` `0x95bd8` / `0x57530` |
| `anchor_spl` `harvest_withheld_tokens_to_mint` (2664 B) | `0x184e38` | `0x115158` | `0x6fce0` | `token_metadata_update_authority` `0x184a60` / `0x114d80`, `transfer_hook_initialize` `0x1858a0` / `0x115bc0` |
| `TransferFeeInstruction::pack` (2320 B) | `0x18fc98` | `0x11ffb8` | `0x6fce0` | `metadata_pointer::instruction::initialize` `0x18f7a8` / `0x11fac8` |
| `spl_token_2022` `harvest_withheld_tokens_to_mint` (1104 B) | `0x1905a8` | `0x1208c8` | `0x6fce0` | `transfer_hook::instruction::initialize` `0x1909f8` / `0x120d18` |

Drift solver: `call_only_raw_fail` 215 to 205, `potential_if_delta0` 363 to 366, `intervals_nonzero` 86 to 84. Both intervals close. Next roots with missing functions: `0x17c548`..`0x17cae8` (deployed `0x17c850`, 664 B, 167 spoiled) and `0x17bc38`..`0x17c3d8` (deployed `0x17bc48` 1192 B and `0x17c0f0` 744 B, 165 spoiled).

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
