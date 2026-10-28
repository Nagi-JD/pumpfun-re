# chantier-T4: `anchor_lang::system_program::transfer_with_seed` CPI for the IDL account, `drop_in_place<[AccountInfo; 3]>` at 0x199db8

Refs T4 (#18, equalize function sizes). Resolves the interval `0x199bf8`..`0x19a020` (delta -616, 167 call-only spoiled windows) left by `chantier-T4-pk8-setparams-serialize`: deployed window `0x199db8` (616 B) is the `anchor_lang` monomorph of `core::ptr::drop_in_place<[AccountInfo; 3]>`, called once (`0x19e630`) from `anchor_lang::system_program::transfer_with_seed` at `0x19e3b0` (896 B).

## What the deployed program does

`0x199db8` releases three `AccountInfo` values laid out 48 B apart (offsets `0x00`, `0x30`, `0x60`): for each, the `Rc` strong and weak counts of `lamports` (dealloc 0x20) and `data` (dealloc 0x28). It sits between `drop_in_place<[AccountInfo; 2]>` (`0x199bf8`, 448 B) and `drop_in_place<Vec<AccountInfo>>` (`0x19a020`, 360 B), all from the `anchor_lang` codegen unit.

Its only caller, `0x19e3b0`, is `anchor_lang::system_program::transfer_with_seed`: it builds the instruction through `solana_system_interface::instruction::transfer_with_seed` (`0x1a7558`, variant 11, metas `from` writable, `base` signer, `to` writable), runs `invoke_signed` with the three accounts `[from, base, to]`, then drops the array. It follows `anchor_lang::system_program::transfer` (`0x19e090`) in `.text`. The single call into it comes from the `admin_set_idl_authority` handler (`0x156278` inside `0x1557e8`), on the branch where the IDL account is still owned by the system program.

In the baseline layout that branch called `system_instruction::transfer_with_seed` and `invoke_signed` directly from the handler, so the `anchor_lang` wrapper and its `[AccountInfo; 3]` drop were never instantiated.

## Change

- `source.patch`: the system-owned IDL branch of `idl_authority::execute` calls `anchor_lang::system_program::transfer_with_seed` with `CpiContext::new_with_signer(system_program, TransferWithSeed { from: idl_account, base: program_signer, to: authority }, &[&[&[bump]]])`, seed `"anchor:idl"`, owner `crate::ID` and the IDL account lamports. The edit stays on the existing lines 19 to 25 of `admin_set_idl_authority.rs`, so every `require!` line number is unchanged. The CPI carries the same instruction and the same three accounts as the deployed wrapper.
- `ordered-ld.patch` (on top of the T4 `ordered.ld` from #28): places `drop_in_place<[AccountInfo; 3]>` (`hf6805be87556f7fc`) right after `drop_in_place<[AccountInfo; 2]>` (`hfb00dca503880918`), and `transfer_with_seed` (`haef1e0871362152f`) right after `anchor_lang::system_program::transfer`, their deployed neighbours.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| pk8-setparams-serialize (#28) | 793 | 140 | `1d77749f01ea68e705f2fc7cf339ff1a2fc57a43de98ac544091fc76d4afe6af` |
| wrapper, #28 `ordered.ld` (no placement) | 794 | 140 | `05c3d37376485e60f70ba926260f2f3f7bf11aa8695b58386b54c7a9aed26b27` |
| wrapper + `ordered-ld.patch` (this packet) | **794** | **148** | `31162d65ed5a56fb60c2beaa62b754b758516411b7b07149c96616bf578f8ae2` |

Gained matched: `0x19e3b0`. Gained raw: `0x194998`, `0x194ae0`, `0x197508`, `0x198fe8`, `0x1991e0`, `0x19a758`, `0x19a8a0`, `0x19b4e0`. Lost: none. In this packet's build the three drops sit at `0x128188` (448 B), `0x128348` (616 B), `0x1285b0` (360 B), the same relative layout as deployed `0x199bf8` / `0x199db8` / `0x19a020`, and `transfer_with_seed` (896 B) directly follows `transfer` (800 B).

Drift solver: `call_only_raw_fail` 222 to 215, `potential_if_delta0` 362 to 363, `intervals_nonzero` 88 to 86. The `0x199bf8`..`0x19a020` interval closes. Next root with a missing function: `0x17c548`..`0x17cae8` (deployed `0x17c850`, 664 B, 165 spoiled).

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
