# pump_fees — original source tree, panic sites, and the `sol_memmove_` user

Measured on the deployed program only (`evidence/original/pump_fees/deployed.so`,
`programs/pump-fees` = `pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ`). No build was
performed for this note. Addresses are `.text` byte addresses; `insn` = byte / 8
(sbftool's pc unit). Everything below is reproducible with the tools listed in §7.

## 0. What this adds

1. **The original crate's file tree is recoverable from the binary** — not from
   string greps alone. Rust panic `Location` records survive in `.data.rel.ro`
   (63 records here), and each is loaded by exactly one `lddw`, so every panic site
   is attributable to a *function* and to a *file:line:col*. 50 functions carry at
   least one; 26 records name `programs/pump-fees/src/...` across 11 files.
2. **`sol_memmove_` has exactly one call site** and it is *not* in the admin/tier
   path: insn `0x184de` (byte `0xc26f0`) inside the 4-insn syscall thunk at insn
   `0x184dd` (byte `0xc26e8`), reached only through the inlined SBF bump allocator
   at insn `0x1636` (byte `0xb1b0`), which only **`update_fee_shares`** and
   **`update_fee_shares_v2`** can reach.
3. At that call site the copy is an **in-place overlapping shift**: `dst = [fp-0x68]`,
   `src = dst + 0x10`, `len = (a - b - 1) * 16`. That is a gap-closing copy
   (`Vec::remove` / `drain` / `retain` / `slice::copy_within`), not a realloc copy.
4. **`upsert_fee_tiers` and `extend_fee_config` do not reach `sol_memmove_`.** Both
   are measured to reach only the `sol_memcpy_` thunk, through account
   deserialization. That falsifies the hypothesis named in the P0 brief.
5. Census corrections for pump_fees: **489** functions (sbftool reports 488 — the
   ELF entry is not a call target), **555** `exit`, **4741** `call` instructions of
   which **155** are relocated syscall sites (**16** distinct syscalls), **121**
   `callx` sites (all dynamic-drop form), **0** functions unreachable from
   entry + dispatcher.

## 1. Method — decoding panic `Location` records

A `core::panic::Location` is `{ file: &'static str, line: u32, col: u32 }`, i.e. a
24-byte record. In this ELF the records live in `.data.rel.ro`
(`addr 0xc8718`, size `0x1a58`) and are referenced from the panic path by an
`lddw` that carries an `R_BPF_64_RELATIVE` relocation (type 8). Two encoding
quirks have to be handled — they are *opposite* between data slots and text
instructions:

| where | how the 32-bit target VA is stored | evidence |
|---|---|---|
| `.data.rel.ro` record slot (8 bytes) | **high** dword, low dword zero (`va << 32`) | a 4-byte search for a known path VA hits 4 slots, an 8-byte search hits none |
| `.text` `lddw` addend | **low** 32 bits of sbftool's decoded `imm` | 74 sites match a record address through the low half, 0 through the high half |

Record fields, confirmed by decoding: `+0` pointer `<va<<32>`, `+8` `len: u64`,
`+16` `line: u32`, `+20` `col: u32`, stride 24. Plain `&str` constants in the same
region are the same shape with stride 16 (no line/col); 20 of those were decoded
as a control. Decoding is validated three ways: the record's `len` must equal the
byte length of the path at the pointed-to address, the slice must end in `.rs`, and
`line`/`col` must be in range. `.rel.dyn` holds 2748 entries: 2593 type-8 and 155
type-10 (the call sites of §4).

## 2. Recovered source tree (measured)

20 distinct `programs/pump-fees/src/...` paths are embedded; 11 of them carry at
least one panic `Location`, 9 do not. "Absent from this table" therefore means
"no panic site in that file", **not** "file not in the crate".

```
programs/pump-fees/src/common/mod.rs
programs/pump-fees/src/instructions/admin/extend_fee_config.rs
programs/pump-fees/src/instructions/admin/initialize_fee_config.rs
programs/pump-fees/src/instructions/admin/initialize_fee_program_global.rs
programs/pump-fees/src/instructions/admin/update_buyback_authority.rs
programs/pump-fees/src/instructions/admin/update_fee_config.rs
programs/pump-fees/src/instructions/admin/update_fee_program_global.rs
programs/pump-fees/src/instructions/admin/upsert_fee_tiers.rs
programs/pump-fees/src/instructions/buyback/mod.rs
programs/pump-fees/src/instructions/fee_sharing/admin_cto_sharing_config.rs
programs/pump-fees/src/instructions/fee_sharing/claim_social_fee_pda.rs
programs/pump-fees/src/instructions/fee_sharing/create_donation_fee_pda.rs
programs/pump-fees/src/instructions/fee_sharing/create_fee_sharing_config.rs
programs/pump-fees/src/instructions/fee_sharing/create_social_fee_pda.rs
programs/pump-fees/src/instructions/fee_sharing/mod.rs
programs/pump-fees/src/instructions/fee_sharing/update_fee_shares.rs
programs/pump-fees/src/instructions/fee_sharing/update_fee_shares_v2.rs
programs/pump-fees/src/instructions/withdraw.rs
programs/pump-fees/src/lib.rs
programs/pump-fees/src/state.rs
```

Two files of the tree are **implied but not visible**: `instructions/mod.rs` and
`instructions/admin/mod.rs`. A module file only gets a `.rodata` path when the
compiler emits a panic site for it, so a `mod.rs` that is pure `pub mod ...`
declarations leaves no string. Their existence is inferred from the directory
shape, not measured.

## 3. Per-file panic anchors

| source file (under `programs/pump-fees/src/`) | panic sites | line:col | first record VA |
|---|---|---|---|
| `common/mod.rs` | 3 | 21:48, 21:56, 33:56 | `0xc8a50` |
| `instructions/admin/update_fee_config.rs` | 2 | 7:1, 16:1 | `0xc8c38` |
| `instructions/admin/upsert_fee_tiers.rs` | 2 | 6:1, 15:1 | `0xc8c68` |
| `instructions/fee_sharing/admin_cto_sharing_config.rs` | 1 | 53:1 | `0xc8c98` |
| `instructions/fee_sharing/claim_social_fee_pda.rs` | 1 | 100:1 | `0xc8cb0` |
| `instructions/fee_sharing/create_fee_sharing_config.rs` | 2 | 37:1, 119:1 | `0xc8cc8` |
| `instructions/fee_sharing/create_social_fee_pda.rs` | 1 | 36:1 | `0xc8cf8` |
| `instructions/fee_sharing/update_fee_shares.rs` | 2 | 114:1, 228:55 | `0xc8af0` |
| `instructions/fee_sharing/update_fee_shares_v2.rs` | 2 | 236:18, 278:55 | `0xc8b08` |
| `lib.rs` | 2 | 27:1, 28:1 | `0xc8d88` |
| `state.rs` | 8 | 50:1, 67:32, 113:1, 135:1, 154:1, 398:19, 398:33, 451:19 | `0xc8b70` |

Line numbers are lower bounds for the original file length and are the concrete
target for a source reconstruction: e.g. `common/mod.rs` has three unwrap/panic
sites at lines 21 and 33 only, so the file is short and those two lines must
match; `state.rs` has sites at 50, 67, 113, 135, 154, 398, 451, so it is a
450+ line file with account/state code near 50–154 and more code near 398–451.

Paths with no `Location` record (still part of the tree, per §2):
`instructions/admin/extend_fee_config.rs`,
`instructions/admin/initialize_fee_config.rs`,
`instructions/admin/initialize_fee_program_global.rs`,
`instructions/admin/update_buyback_authority.rs`,
`instructions/admin/update_fee_program_global.rs`,
`instructions/buyback/mod.rs`,
`instructions/fee_sharing/create_donation_fee_pda.rs`,
`instructions/fee_sharing/mod.rs`,
`instructions/withdraw.rs`.

Note the *shape* of the tree: `lib.rs`, `state.rs`, `common/mod.rs`, one file per
instruction under `instructions/{admin,fee_sharing}`, `instructions/buyback/mod.rs`,
`instructions/withdraw.rs`. There is no `contexts.rs`, `types.rs`, `donation.rs`,
`social.rs` or `sharing*.rs` in the original — account contexts and events live in
the instruction files (and `state.rs`), and shared helpers live in `common/mod.rs`.

## 4. Function → source file:line:col (program files only)

| function insn | function byte | size (insns) | file:line:col referenced |
|---|---|---|---|
| `0x250d` | `0x012868` | 60 | `common/mod.rs` 21:48, `common/mod.rs` 21:56 |
| `0x3afe` | `0x01d7f0` | 848 | `state.rs` 67:32 |
| `0x500a` | `0x028050` | 1641 | `common/mod.rs` 33:56 |
| `0x6134` | `0x0309a0` | 597 | `instructions/fee_sharing/update_fee_shares.rs` 228:55 |
| `0x673a` | `0x0339d0` | 974 | `common/mod.rs` 33:56 |
| `0x6b1e` | `0x0358f0` | 786 | `instructions/fee_sharing/update_fee_shares_v2.rs` 236:18, `instructions/fee_sharing/update_fee_shares_v2.rs` 278:55 |
| `0x7fd7` | `0x03feb8` | 485 | `state.rs` 398:19, `state.rs` 398:33 |
| `0x81df` | `0x040ef8` | 485 | `state.rs` 451:19 |
| `0xa4f0` | `0x052780` | 103 | `instructions/admin/update_fee_config.rs` 7:1 |
| `0xa561` | `0x052b08` | 103 | `instructions/admin/update_fee_config.rs` 16:1 |
| `0xa802` | `0x054010` | 115 | `instructions/admin/upsert_fee_tiers.rs` 6:1 |
| `0xa87f` | `0x0543f8` | 115 | `instructions/admin/upsert_fee_tiers.rs` 15:1 |
| `0xbd36` | `0x05e9b0` | 237 | `instructions/fee_sharing/admin_cto_sharing_config.rs` 53:1 |
| `0xc64d` | `0x063268` | 48 | `instructions/fee_sharing/claim_social_fee_pda.rs` 100:1 |
| `0xd8a5` | `0x06c528` | 176 | `instructions/fee_sharing/create_fee_sharing_config.rs` 37:1 |
| `0xe41c` | `0x0720e0` | 172 | `instructions/fee_sharing/create_fee_sharing_config.rs` 119:1 |
| `0xec2c` | `0x076160` | 132 | `instructions/fee_sharing/create_social_fee_pda.rs` 36:1 |
| `0xf498` | `0x07a4c0` | 136 | `instructions/fee_sharing/update_fee_shares.rs` 114:1 |
| `0x102e5` | `0x081728` | 125 | `state.rs` 50:1 |
| `0x103c1` | `0x081e08` | 108 | `state.rs` 113:1 |
| `0x1048c` | `0x082460` | 220 | `state.rs` 135:1 |
| `0x105c5` | `0x082e28` | 149 | `state.rs` 154:1 |
| `0x106b7` | `0x0835b8` | 177 | `lib.rs` 27:1 |
| `0x107c7` | `0x083e38` | 493 | `lib.rs` 27:1 |
| `0x11951` | `0x08ca88` | 361 | `lib.rs` 28:1 |

Reading of the pairs: two twin functions of *identical* size sit back to back per
admin instruction file (`0xa4f0`/`0xa561` = 103 insns each for
`update_fee_config.rs` 7:1 / 16:1; `0xa802`/`0xa87f` = 115 each for
`upsert_fee_tiers.rs` 6:1 / 15:1). Identical size plus one Location each is the
signature of one generic function instantiated twice, each instantiation carrying
a different call-site `Location`. They are compact (48–237 insns), so they are the
`#[derive(Accounts)]` monomorphizations of the instruction, not its handler
(handlers are 104–249 insns at `0x12d72..0x141aa` and carry no `Location`). A
build that reproduces the tree but not these spans will differ in `.rodata` /
`.data.rel.ro` even when `.text` matches.

## 5. The `sol_memmove_` user (P0 "FIX 2"), measured

Syscall census of the deployed program (relocation-resolved):

```
155 reloc'd syscall sites, 16 syscalls:
  73 abort            66 sol_log_         2 sol_memcpy_      2 sol_memset_
   1 custom_panic      1 sol_memcmp_      1 sol_log_data     1 sol_get_clock_sysvar
   1 sol_get_rent_sysvar   1 sol_invoke_signed_rust   1 sol_set_return_data
   1 sol_try_find_program_address   1 sol_create_program_address
   1 sol_log_pubkey    1 sol_sha256       1 sol_memmove_
```

The single `sol_memmove_` site and its call chain:

```
syscall sol_memmove_   @ insn 0x184de (byte 0xc26f0)   <- the 4-insn thunk at insn 0x184dd (byte 0xc26e8)
  thunk called from    insn 0x171f  in fn @ insn 0x1636 (byte 0xb1b0, 636 insns)
    fn 0x1636 called from  insn 0x658c in fn @ insn 0x6479 (byte 0x323c8, 669 insns)
                           insn 0x6f63 in fn @ insn 0x6e50 (byte 0x37280, 671 insns)
      fn 0x6479 called from insn 0x60e6, 0x612e in fn @ insn 0x5e6f (byte 0x2f378, 696 insns)
      fn 0x6e50 called from insn 0x6ad5, 0x6b12 in fn @ insn 0x673a (byte 0x339d0, 974 insns)
        fn 0x5e6f called from insn 0x13925 in update_fee_shares     @ insn 0x138d4 (byte 0x9c6a0, 129 insns)
        fn 0x673a called from insn 0x139ad in update_fee_shares_v2  @ insn 0x1395a (byte 0x9cad0, 134 insns)
        both handler entries called from the dispatcher @ insn 0x1240e (byte 0x92070)
          which is called from the ELF entry @ insn 0x14299 (byte 0xa14c8, = e_entry)
```

Full reachability over the direct-call graph (`maps/fees_handler_reach.txt`, 31
handlers × 489 functions): the allocator function `0x1636` is reachable from
**exactly two** handlers —

```
handler                         entry      insns   fn 0xb1b0   memcpy thunk 0xc26c8   memmove thunk 0xc26e8
update_fee_shares               0x138d4      129        YES                 YES                     YES
update_fee_shares_v2            0x1395a      134        YES                 YES                     YES
(all 29 other handlers)                                    -                 YES                       -
```

No other entry point exists for that function: `fees_addr_taken.py` finds **0**
`lddw` references and **0** relocated data slots holding any of
`0xb1b0 / 0x323c8 / 0x2f378 / 0x339d0 / 0x9c6a0 / 0x9cad0`, and the only direct
calls are the ones listed above. The 121 `callx` sites in the program are all of
the dynamic-drop form (`and 0x3; add -0x2; ldxdw [x-1]; ldxdw [x+7]; callx`) used
for `drop_in_place` of `dyn` values, so they are not a hidden edge class here.

### 5.1 What the target function is

`0x1636` is the Rust-for-SBF default bump allocator inlined with a `Vec` grow:

```
lddw r2, 0x300000000      ; heap cursor
ldxdw r2, [r2]
lddw r3, 0x300008000      ; heap end (0x300000000 + 32 KiB, the default heap)
...
call 0x17816              ; panic helper on failure: loads "called `Option::unwrap()` on a `None` value" (len 0x2b) from .rodata 0xc7a2c and formats it
```

The heap window `[0x300000000, 0x300008000)` and the message both come from the
standard entrypoint allocator, not from crate code.

### 5.2 What the copy at the call site is

```
170c: sub64 r3, r9
170d: mov64 r1, r7          ; dst
170e: mov64 r2, r9          ; src
170f: call -> 0xc26c8       ; sol_memcpy_  (non-overlapping copy above)
...
1713: ldxdw r1, [r10 -0x80]
1714: ldxdw r3, [r10 -0x48]
1715: add64 r1, r3
1716: stxdw [r2 +0x0], r1
1717: ldxdw r1, [r10 -0x60]
1718: xor64 r1, -0x1        ; r1 = ~len_a
1719: ldxdw r3, [r10 -0x58]
171a: add64 r3, r1          ; r3 = len_b - len_a - 1
171b: lsh64 r3, 0x4         ; r3 = (len_b - len_a - 1) * 16
171c: ldxdw r1, [r10 -0x68] ; dst = base
171d: mov64 r2, r1
171e: add64 r2, 0x10        ; src = dst + 16
171f: call -> 0xc26e8       ; sol_memmove_  (overlapping: src > dst)
```

So: 16-byte stride, `src = dst + 16`, `count = len_b - len_a - 1`. LLVM emits
`memmove` only when it cannot prove the ranges disjoint, i.e. the source code
performed an overlapping copy of a `&mut` slice — `Vec::remove`, `drain`,
`retain`'s gap-closing copy, `splice`, or `slice::copy_within`. A `Vec` that only
grows through `extend_from_slice` / `push` produces `sol_memcpy_`, as the call at
`0x170f` in the same function shows.

What is **not** proven here: which Rust construct produced it. The discriminating
experiment is a rebuild of the two shareholder handlers with (a) a
`Vec::retain`-style filter and (b) an explicit `copy_within`, and checking whether
the `sol_memmove_` site appears; the 16-byte stride also constrains the element
type, which does not match the 40-byte `{ Pubkey, u16 }` shareholder shape used by
the current reconstruction candidate.

## 6. Census and boundary corrections

| quantity | value | how |
|---|---|---|
| functions | **489** | call targets + first insn + `e_entry` |
| `exit` instructions | **555** | op `0x95` count |
| `call` instructions | **4741** | op `0x85`: 4586 internal + 155 relocated syscalls |
| distinct syscalls | 16 | `.rel.dyn` type 10 |
| `callx` | 121 | dynamic drop dispatch |
| `.text` | `0x120..0xc34c0`, 799 648 B | ELF |
| `.rodata` / `.data.rel.ro` / `.rel.dyn` | 21 079 / 6 744 / 43 968 B | ELF |
| panic `Location` records | 63 (26 program / 37 dependency) | §1 |
| functions referencing a `Location` | 50 | §1 |

Two earlier figures are reproduced exactly (555 exits, 4741 calls); the
"555 vs 552 functions" comparison is **488 vs 489**, not 555 — 555 is the `exit`
count. sbftool's start set gives 488 because the ELF entry point
(`e_entry = 0xa14c8`, insn `0x14299`) is never a call target; without that start,
`entry` is folded into the preceding 65-insn helper at insn `0x14258`
(byte `0xa12c0`), which also made the 12-insn deprecated stubs at `0x138ba` /
`0x138c7` look like they reached the allocator. With the boundary repaired there
is **no** unreachable function in the program.

A second, unrelated boundary defect: sbftool's `func_body()` ends the *last*
function at `base + len(order)` — an instruction *count* added to an *address* —
so the final function is truncated to zero insns. That is where the 555th `exit`
went (insn `0x18697`, byte `0xc34b8`, the last 8 bytes of `.text`);
`tools/fees_prog.py` bounds function ranges by the last decoded pc instead. Both
defects are localised in `tools/fees_prog.py`, not worked around in `sbftool.py`.

## 7. Reproduction

```
python3 tools/fees_locations.py evidence/original/pump_fees/deployed.so --json maps/fees_locations.json --md /tmp/fn.md
python3 tools/gen_fees_report.py                       # tables of §3 and §4
python3 tools/fees_handler_reach.py evidence/original/pump_fees/deployed.so   # §5 reachability
python3 tools/fees_addr_taken.py <so> 0xb1b0 0x323c8 0x2f378 0x339d0 0x9c6a0 0x9cad0
python3 tools/fees_p0_probe.py sites <so>               # syscall inventory + memmove chain
python3 tools/fees_exit_check.py <so>                    # exit accounting / boundary check
python3 tools/sbftool.py func <so> 0x1636               # the allocator function
```

`tools/fees_*.py` import `tools/fees_prog.py`, which re-does `.rel.dyn` parsing on
top of `tools/sbftool.py`'s decoder (relocated `call` sites, `lddw` addends,
function starts + `e_entry`). They therefore run against the unmodified
`sbftool.py` in this repository. Without relocation awareness every syscall site
reads as `call -1` and function boundaries collapse (see the S1b note).

## 8. Limitations

* No compiler in this container: nothing here is a byte-identity claim, and the
  line/column anchors are requirements for a rebuild, not evidence of its contents.
* `Location` records only exist for panic sites, so the recovered tree is partial
  by construction (20 embedded paths, 11 with anchors, 9 without).
* The identification of insn `0x1636` as the allocator + `Vec` grow is inferred
  from the heap window and the panic message; the 16-byte element behind the
  `memmove` is not resolved to a Rust construct (§5.2).
* Function boundaries outside the memmove chain are bounded by "next call target",
  so an undetected function start can still shift a size by a few instructions;
  `e_entry` was the only such boundary found to matter here.
