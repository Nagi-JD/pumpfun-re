# pump_fees `admit_associated_token_account`: IR-level diagnosis of the `jeq +1; ja` gap

Date: 2026-10-27. Tree: `/home/nagi/pumpre/feesbuild/sharing-577-joint` (baseline stripped sha 39b8fc90…8cae).
Status: **diagnosis complete. The target IR shape is identified and proven with llc. The Rust source form is still not found.**
The session stopped early because host C: reached 0 bytes free and WSL started returning I/O errors (see the end of this file).

## 1. IR dump of the baseline is bit-exact

`tools/build_ir.sh` is a copy of build.sh. It uses `CARGO_TARGET_DIR=target-ir` and adds `--emit=llvm-ir,link` to the rustc args. The stripped output equals the baseline:

```
39b8fc901792a6fb67e3e10429e607788497eaf9d3d8848690f4ab0a4ded8cae  /tmp/irs.so            (target-ir build, stripped)
39b8fc901792a6fb67e3e10429e607788497eaf9d3d8848690f4ab0a4ded8cae  sharing-577-joint-candidate.so
```

IR is saved at `ir/base.ll`, and the function on its own at `ir/base_fn.ll` (`define … admit_associated_token_account17h0fc0eaa708d42eb2E`).

## 2. llc reproduces the candidate function exactly

`ir/objcmp.sh X.ll` runs `llc -O3 -relocation-model=pic -mattr=+store-imm,+jmp-ext -filetype=obj`. It then normalizes the admit function and the deployed window @243184/6080 the same way (call targets, lddw constants and jump offsets masked) and diffs them. The flags come from the target spec: PIE gives pic, and the features are `+store-imm,+jmp-ext`. With plain `llc -O3` the function comes out at 6232 B, so the reloc and feature flags are required.

```
$ ./objcmp.sh t0.ll          # t0 = base.ll, only renumbered
size 6072
700c700,701
< jne r2, r1, L
---
> jeq r2, r1, L
difflines 3
```

That is exactly the known gap and nothing else.

## 3. The construct that differs

The branch in the IR:

```
call void @_ZN14solana_program7program6invoke…(sret %_42, …)
%95 = load i64, ptr %_42          ; Result<(),ProgramError> niche tag
%96 = icmp eq i64 %95, -9223372036854775782   ; == Ok(())
br i1 %96, label %bb50, label %bb49           ; bb50 = Ok (drop [AccountInfo;6], drop Instruction -> bb23), bb49 = Err (From<ProgramError>, drops -> bb43)
```

Baseline IR block order: `…clone.exit107(invoke)`, `bb50`, `<drop chain>`, `bb49`, `<drop chain>`, `bb29`, …

Mechanism:
- In the baseline, the Ok block `bb50` is the next IR block when SelectionDAG runs. SelectionDAGBuilder therefore inverts the condition and falls through, which gives the single `jne r2,r1,→Err`.
- In the deployed binary, the Ok block was not the next block at ISel. ISel then emitted `jeq →Ok; ja →Err`. MachineBlockPlacement later moved Ok to sit right after the branch. The BPF backend cannot reverse branch conditions, so the pair was never folded, and the result is `jeq +1; ja +0x10`.

The same `jeq +1; ja` idiom appears at other points in this function in both binaries (diff lines 90-91, 167-168, 259-260). It is the normal BPF signature of "the true target was not the next IR block at ISel".

## 4. llc experiments: the target IR shape

`ir/swap2.py` renames `%N` to `%vN` inside the function so blocks can be reordered, then moves block B to just before block A. Measured results:

| IR edit (block moved before `bb50`) | size | diff vs deployed |
|---|---|---|
| none (t0) | 6072 | 3 lines (the gap) |
| `bb49` (Err) placed before `bb50` | — | `jne r2,r1,→Ok`, Err falls through: wrong |
| `bb29` | **6080** | **difflines 0** |
| `bb23` | **6080** | **difflines 0** |
| `bb43` | **6080** | **difflines 0** |
| `bb44` | **6080** | **difflines 0** |
| `bb24` | 6072 | a different site (line 90) loses its `ja`: wrong |

```
== move bb50 bb29  -> size 6080 / difflines 0
== move bb50 bb23  -> size 6080 / difflines 0
== move bb50 bb43  -> size 6080 / difflines 0
== move bb50 bb44  -> size 6080 / difflines 0
```

**Target shape:** in the IR, any surviving block other than Err (and other than `bb24`) must sit between the invoke/branch block and the Ok block. Everything else stays identical; MBP restores the final layout. The deployed function is therefore the same IR in a different block order. It is not a different computation.

Where the block order comes from: rustc 1.79 `codegen_mir` creates each LLVM block lazily, the first time a terminator references it, and codegens in MIR reverse post-order. Layout is therefore "first-reference order". For example, `bb7`'s bool switchInt is `[0: bb23, otherwise: bb8]`, so `bb23` is created before `bb8`, and the dump shows this. The `?` switch on the invoke result references Ok then Err straight away, so they become adjacent. A source form that wins must therefore make some other block get created after the invoke block but before Ok. That block has to be one that LLVM does not later merge away, or one created when Ok is first referenced earlier from another path.

## 5. Source candidates tried this session (fast path: IR build + llc compare)

`tools/irv.py <variant>` replaces the 12-line `invoke(..)?;` with the variant and pads it to keep the same line numbers, so location constants stay intact. `tools/irtry.sh <variant>` then builds, compares, and restores the source. Results:

| variant | size | result |
|---|---|---|
| `invoke(..)?` as the tail expression (no `;`) | 6072 | gap unchanged (jne) |
| `let _ = invoke(..)?;` | 6072 | gap unchanged |
| `let () = invoke(..)?;` | 6072 | gap unchanged |
| `invoke(..)?; drop(instruction);` | 6072 | gap unchanged |
| `Ok::<(),Error>(invoke(..)?)?;` | 6072 | gap unchanged |
| `let result = invoke(..); result?;` | 6688 | function diverges |
| `.map_err(anchor_lang::error::Error::from)?` | 6024 | diverges |
| `let infos=[..]; invoke(&ix,&infos)?; drop(infos);` | 6072 | diverges (987 lines) |
| same + `drop(instruction)` | 6072 | diverges (987) |
| helper `fn invoke_ata(..)->ProgramResult` (plain) | 6072 | gap unchanged |
| helper, `#[inline]` | 6072 | gap unchanged |
| helper `->Result<()> { invoke(..)?; Ok(()) }` (plain / `#[inline]` / `#[inline(always)]`) | 6088 | diverges |
| helper `->Result<()> { invoke(..).map_err(Into::into) }` | 6104 | diverges |
| `if let Err(e)=invoke(..){return Err(e.into())}` (earlier "+0x16" form, IR rebuilt) | 6024 | whole function diverges (371 lines). The +0x16 polarity is a different function, not a near miss. |

Earlier attempts (`tools/ata_variants.py`, `ata2.py`, `tries/a*,b*`) are not repeated here.

None of these flipped the branch. The forms that keep 6072 B and only this diff show that `?`-on-Result variants, `let` bindings, explicit drops and inlined ProgramResult helpers all lower to the same MIR switch with Ok referenced first.

**Window 40472 and the full measure.py run were not checked for any of these.** No variant reached the target shape, so try.sh was never run on one.

## 6. Next candidates (not run, because WSL went down)

What the target shape needs from the source: a block created in MIR or LLVM between the invoke continuation and the Ok arm.
1. Make the Ok arm reference a block that was created earlier, e.g. restructure so the Ok path jumps straight to the already-created join `bb23` and the drops are emitted elsewhere. Candidates: putting `instruction` / infos in an outer scope so the drop happens after the `if` join, or `if cond { …; invoke(..)? } else { () }` with the `else` placed first (`if !cond {} else {…}`).
2. Put an extra early-referenced block in the switch, e.g. `match invoke(..) { Ok(()) => (), Err(e) if true => return Err(e.into()), Err(e) => … }`. Also try the `Result<(), ProgramError>` matched by a `match` with an `_ =>` arm, which creates an otherwise target.
3. Inspect MIR directly. `build_ir.sh` has already been switched to `--emit=llvm-ir,mir,link`; run it and read `admit_associated_token_account` in `target-ir/.../pump_fees_candidate.mir` to see the switchInt target order. Then grep the deployed-equivalent jeq/ja sites at lines 90/167/259 in the base MIR: they are existing examples of the target shape in the same function, so the source constructs that produce them are the template.

## 7. Environment incident and tree state

- While the MIR build was running, host **C: reached 0 bytes free**. WSL (Ubuntu-22.04, vhdx on C:) now fails every process: `getpwuid failed 5 … I/O error @util.cpp:1358`. The most likely cause is my extra `target-ir/` full dependency rebuild growing the vhdx. To recover: free space on C:, then `wsl --shutdown`, restart, and delete `/home/nagi/pumpre/feesbuild/target-ir` (my artifact, safe to remove; `ir/` holds the useful .ll files).
- Source tree: `irtry.sh` restores `mod.rs` from `ir/mod.rs.orig` after every variant, and the last completed step was a restore. The tree should therefore be at baseline, but this **could not be re-verified after the outage**. Check with `sha256sum` of a `build.sh` output = 39b8fc90…8cae.
- No commit was made to `fees-race` and nothing was pushed. The research tools are in `feesbuild/tools/{build_ir.sh,irv.py,irtry.sh}` and `feesbuild/ir/{swap2.py,objcmp.sh,*.ll}`.

## 8. Resolution (session 2, 2026-10-27)

**Source form found.** Bind the owner test to a local before the `if`:

```rust
let needs_create = associated_account.owner == &anchor_lang::system_program::ID; if needs_create {
```

Kept on the same line, so all line numbers are unchanged. Patch: `feesbuild/ir/let_bind.patch`.

- **MIR (now emitted by `build_ir.sh`):** the invoke `?` is `bb19: switchInt -> [0: bb50, 1: bb49, otherwise: bb20]`. The owner check is `bb46: switchInt(_27) -> [0: bb23, otherwise: bb8]`. That second switch creates the join `bb23` early, ahead of the if-body. With the bool in a local, `bb23` ends up between the invoke block and Ok. That is the target shape found in section 4.
- **IR/llc:** `let_bind` gives size 6080 and difflines 0 against deployed. These single-line forms all stayed at 6072 with the gap: `!=`+else, `match bool`, `!(!=)`, `.eq()`, `*owner ==`.
- **try.sh/measure.py:** matched 577→578 (gained 243184, none lost), unique_pairs 430→431, equal_locations 181→182, unequal_locations 0, equal_edges 3870→3900, raw 143 unchanged. Window 40472 is still matched.
- **State:** `sharing-577-joint` is back at baseline, with `ir/mod.rs.orig` restored. `target-ir/` was deleted, which frees 367M.
- **Not committed:** `sharing-577-joint` is a scratch git repo on `master`. No tracked file in `repo` on `fees-race` matches the baseline `mod.rs`. The target path on `fees-race` needs to be decided before the patch is applied there.
