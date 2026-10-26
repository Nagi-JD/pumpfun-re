# Original-source reference maps for the four deployed programs

Every `Location` / `&str` the deployed code hands to the panic and error-formatting paths
is a `(path, len)` pair, and a `Location` additionally carries `(line, col)`. Those pairs
are still present in the shipped ELF, so the original crate file tree and per-file line
anchors can be read straight out of the binary instead of being inferred.

This document publishes the full table for the four programs, with the emphasis on
**pump_amm** and **mayhem**, and a per-handler attribution derived from the direct call
graph.

Tool: `tools/source_locations.py` (sbftool decoder + relocation-aware function starts).
Machine-readable output: `maps/<program>_source_locations.json`.

```bash
python3 tools/source_locations.py pump_amm pump pump_fees mayhem \
    --root evidence/original \
    --handlers pump_amm=maps/amm_handlers.json \
    --handlers pump=maps/handlers.json \
    --handlers pump_fees=maps/fees_handlers.json \
    --json maps
```

`evidence/original/<program>/deployed.so` is the mainnet deployment dump; the SHA-256 of
each input is recorded inside its JSON (and in the tables below) so the tables are pinned
to a specific capture.

---

## 1. The two encodings

The four programs do not store these pairs the same way, and the difference is itself a
build fact worth recording.

**A. Pointer-slot form** — `pump`, `pump_amm`, `pump_fees`.

`.data.rel.ro` holds the pairs as data. Each pair is
`(u64 path_ptr, u64 path_len)` where the pointer slot stores the `.rodata` VA in its high
32 bits with a zero low dword; a `Location` record is the same pair followed by
`(u32 line, u32 col)`, i.e. a 24-byte stride instead of a 16-byte one. The code reaches a
record with an `lddw` whose low 32 bits carry the record VA, e.g. pump_amm
`0x8af2  lddw r3, 0x1224d8` followed by `0x8af4 call 0x19a74` (the panic formatter).
Paths are packed back to back in `.rodata` with no NUL separator, so it is the `path_len`
in the pair, not a terminator, that delimits them (see section 5).

**B. Direct-immediate form** — `mayhem`.

`mayhem` has no string table in `.data.rel.ro` at all (that section is 0x1e68 bytes for
83947 instructions), and the pair is materialised inside the handler body: an `lddw`
carrying the `.rodata` VA in its **low** 32 bits, then a store-immediate carrying the
length. At `0x1b40` the sequence is

```
0x1b40  lddw r1, 0xad4c4        ; -> "programs/mayhem-program/src/instructions/burn.rs"
0x1b42  stxdw [r10 -0x148], r1  ; the pointer
0x1b45  stw   [r10 -0x138], 0x4e ; 78 = path (48) + the message text that follows it
```

The path and the panic message are stored back to back in `.rodata` with **no NUL
separator**, so a reference either takes exactly the path bytes (the file identity) or the
whole path+message slice. Both classes occur: 31 of the 32 mayhem references take the pure
path, and `0x1b40` takes 78 bytes = the 48-byte path plus the 30-byte message
`called ``Result::unwrap()`` on an `. The slice boundary is therefore validated by the
path byte length, not by a terminator. Consequently the mayhem table carries file
identity but **no line/column**: the deployed mayhem build emits panic payloads without
`Location` line data. pump, pump_amm and pump_fees do carry line/col.

---

## 2. pump_amm (PumpSwap)

- binary SHA-256 `6a7ad34596d83b4c435b32f458a56e718e9f82eb4ad38e4316616d15d24d8ff7`
- 139,524 instructions, 663 functions, 25,715-byte `.rodata`, 8,584-byte `.data.rel.ro`
- 123 path-looking strings, 100 `(path,len)` pointer slots, **72 `Location` records**
  plus 28 plain `&str` constants
- the 72 records live in **18 files** and are referenced from **46 functions**
- crate root: `programs/pump-amm/src/` (hyphenated directory name)

### 2.1 Program files with anchors (7)

| file (`programs/pump-amm/src/`) | anchors | line:col |
|---|---:|---|
| `instructions/swap/multi_hop_swap.rs` | 12 | 233:17 315:28 344:32 353:40 359:34 363:41 369:32 772:20 773:10 775:10 814:45 815:58 |
| `state/volume_accumulator.rs` | 16 | 25:1 54:14 79:17 109:14 137:14 271:13 285:14 300:13 334:18 339:18 348:18 359:17 387:14 391:43 393:14 398:28 |
| `lib.rs` | 2 | 22:1 23:1 |
| `state/global_config.rs` | 1 | 388:45 |
| `instructions/swap/buy.rs` | 1 | 233:1 |
| `instructions/swap/sell.rs` | 1 | 439:13 |
| `instructions/extend_account.rs` | 1 | 96:57 |

Anchor density follows the panic surface of each file: `multi_hop_swap.rs` and
`state/volume_accumulator.rs` are the two files whose arithmetic is guarded by explicit
panic/expect sites in this revision.

### 2.2 Anchor functions (program files only)

`functions_records` in the JSON, filtered to `programs/pump-amm/src/`. One record can be
referenced from several functions (the same assertion inlined at more than one site), hence
the repeated file names.

| function | size (insns) | anchors |
|---|---:|---|
| `0x16393` | 751 | `buy.rs` 233:1 |
| `0x5ce4` | 617 | `extend_account.rs` 96:57 |
| `0x7b1a` | 84 | `multi_hop_swap.rs` 233:17 |
| `0x7b78` | 1145 | `multi_hop_swap.rs` 315:28 344:32 353:40 359:34 (x2) 363:41 369:32 |
| `0x8a5c` | 147 | `multi_hop_swap.rs` 772:20 773:10 775:10 |
| `0x8b28` | 2083 | `multi_hop_swap.rs` 814:45 815:58 |
| `0x98ea` | 1075 | `sell.rs` 439:13 |
| `0x268b` | 274 | `lib.rs` 23:1 (x2) |
| `0x1ae64` | 190 | `lib.rs` 22:1 |
| `0x1b096` | 36 | `lib.rs` 22:1 (x2) |
| `0x1b415` | 142 | `lib.rs` 23:1 |
| `0x1b505` | 176 | `lib.rs` 23:1 |
| `0xa0b3`, `0xc99b`, `0xd8ed` | 210 / 36 / 288 | `global_config.rs` 388:45 |
| `0xb4ae` | 497 | `volume_accumulator.rs` 137:14 |
| `0xda81` | 209 | `volume_accumulator.rs` 54:14 79:17 109:14 391:43 393:14 398:28 |
| `0xdb64` | 736 | `volume_accumulator.rs` 271:13 285:14 300:13 334:18 339:18 348:18 359:17 398:28 |
| `0xde79` | 24 | `volume_accumulator.rs` 387:14 398:28 |
| `0x1aa4d` | 184 | `volume_accumulator.rs` 25:1 |

### 2.3 Anchor / IDL frames linked into pump_amm (11)

`library/core/src/{escape,fmt/mod,fmt/num,unicode/unicode_data}.rs`,
`src/{lib,state,encode,ser/mod,de/mod,common,bpf_writer}.rs` — counts are in
`maps/pump_amm_source_locations.json` (`functions_records`).

### 2.4 Handler -> program file, from the direct call graph

Handler entries are `maps/amm_handlers.json`; the walk follows direct `call` edges to
depth 3 and keeps the program files that own a reachable anchor. Anchor/IDL frames are
excluded from this table because every handler reaches them.

| handler | entry | reachable program files |
|---|---|---|
| `buy` | `0x1cec9` | `instructions/swap/buy.rs`, `lib.rs`, `state/global_config.rs` |
| `buy_exact_quote_in` | `0x1cfb1` | `instructions/swap/buy.rs`, `lib.rs`, `state/global_config.rs` |
| `sell` | `0x1d099` | `instructions/swap/sell.rs`, `lib.rs`, `state/global_config.rs` |
| `boost_buy_and_burn` | `0x1c8e7` | `instructions/swap/buy.rs` |
| `admin_update_token_incentives` | `0x1cb9d` | `state/volume_accumulator.rs` |
| `claim_token_incentives` | `0x1cc57` | `state/volume_accumulator.rs` |
| `extend_account` | `0x1d47e` | `instructions/extend_account.rs` |

The remaining 23 handlers reach only the shared Anchor/IDL frames; their program-file
anchor coverage starts at the functions in 2.2. `multi_hop_swap.rs` belongs to the
`multi_hop_swap` instruction, which is not in the 30-entry `amm_handlers.json` table (the
deployed program carries 38 instructions, `docs/MAP_ALL4.md`). Its body is reached through
the stub at `0x1d2ec`, which sits in the gap `0x1d099` (`sell`) .. `0x1d47e`
(`extend_account`) of the handler table, and the ancestry of the anchor function `0x8a5c`
is `0x7b78 -> 0x1d2ec -> 0x1b793 -> entry 0x1dc05`.

---

## 3. mayhem

- binary SHA-256 `a87fa9f866272514e6acb852b668c4a08aeb173d56c883039991d114d1199bdb`
- 83,947 instructions, 374 functions, `.rodata` 0x47dc, `.data.rel.ro` 0x1e68
- 85 path-looking strings, **32 inline `(path,len)` references in 29 functions**
- crate root: `programs/mayhem-program/src/` (the directory is `mayhem-program`, not
  `mayhem`)

### 3.1 Program files with references (9)

| file (`programs/mayhem-program/src/`) | refs | lengths (path = `len` of the file path) | reference insn |
|---|---:|---:|---|
| `state.rs` | 11 | 36 x11 | `0x56c9 0x5729 0x5852 0x5898 0x599f 0x59d4 0x5bca 0x5c78 0xcf12 0xd152 0xd885` |
| `instructions/fee_recipients.rs` | 6 | 58 x6 | `0x2038 0x2090 0x220a 0x25f2 0x79e2 0x7e7c` |
| `instructions/extend_account.rs` | 2 | 58 x2 | `0x1e28 0x1f3e` |
| `instructions/pump_amm_interface.rs` | 2 | 62 x2 | `0x2eb2 0x3766` |
| `instructions/pump_interface.rs` | 2 | 58 x2 | `0x3ccf 0x4333` |
| `instructions/pump_interface_v2.rs` | 2 | 61 x2 | `0x4c0e 0x54e6` |
| `lib.rs` | 2 | 34 x2 | `0xdc08 0xe8c8` |
| `instructions/burn.rs` | 2 | 48, 78 (path+message) | `0x1b6c 0x1b40` |
| `instructions/admin.rs` | 1 | 49 | `0x61ff` |

Plus one runtime frame, `src/lib.rs` (2 references, len 10). The path lengths are the
self-check that the slice boundary was taken correctly: 28 + `state.rs`(8) = 36,
28 + `burn.rs`(7) = 48, 28 + `admin.rs`(8) = 49, 28 + `fee_recipients.rs`(14) = 58,
28 + `extend_account.rs`(15) = 58, 28 + `pump_interface.rs`(17) = 58,
28 + `pump_interface_v2.rs`(20) = 61, 28 + `pump_amm_interface.rs`(21) = 62,
28 + `lib.rs`(6) = 34, and the two `src/lib.rs` frames sit at 10 bytes.

The mayhem program file set is visible from the binary alone: `admin.rs`, `burn.rs`,
`extend_account.rs`, `fee_recipients.rs`, `pump_amm_interface.rs`, `pump_interface.rs`,
`pump_interface_v2.rs`, `lib.rs`, `state.rs` — the two interface modules show that the
mayhem program carries its own serializers for the pump and PumpSwap instruction sets
instead of depending on a shared crate.

---

## 4. Cross-program fingerprint

Same extraction, all four binaries, so the tables are comparable:

| program | sha256 (16) | insns | functions | Location records | files | program files | Anchor/IDL frames |
|---|---|---:|---:|---:|---:|---:|---:|
| pump | `7a19affaa2c6187e` | 215,873 | 906 | 89 | 26 | 12 | 14 |
| pump_amm | `6a7ad34596d83b4c` | 139,524 | 663 | 72 | 18 | 7 | 11 |
| pump_fees | `4f2955d0f6b40cc9` | 96,083 | 489 | 63 | 22 | 11 | 11 |
| mayhem | `a87fa9f866272514` | 83,947 | 374 | 0 (32 inline pairs) | 10 | 9 | 1 |

Frame differences that identify the build configuration of each program:

| Anchor/IDL frame | pump | pump_amm | pump_fees | mayhem |
|---|:-:|:-:|:-:|:-:|
| `src/idl.rs` | yes | – | – | – |
| `src/v1.rs` | yes | – | – | – |
| `src/generated/instructions/create_metadata_account_v3.rs` | yes | – | – | – |
| `src/instruction.rs` | yes (7 anchors) | – | yes (1) | – |
| `src/encode.rs` | yes (4) | yes (4) | yes (4) | – |
| `src/ser/mod.rs` | yes (2) | yes (2) | yes (2) | – |
| `src/de/mod.rs` | yes (2) | yes (2) | yes (1) | – |
| `src/state.rs` | yes (2) | yes (1) | yes (2) | – |
| `src/common.rs` | yes (2) | yes (2) | yes (2) | – |
| `src/bpf_writer.rs` | yes (1) | yes (1) | yes (1) | – |
| `library/core/src/fmt/num.rs` | yes (7) | yes (7) | yes (7) | – |

`pump` is the only one of the four that carries the IDL codegen frames (`src/idl.rs`,
`src/v1.rs`, `src/generated/...`, `src/instruction.rs`), i.e. it is the only program built
with the IDL path enabled. pump_amm and pump_fees share the `encode`/`ser`/`de` trio
without any IDL frame. mayhem carries a single `src/lib.rs` runtime frame and no ser/de
pair, consistent with its inline-immediate reference encoding (section 1B).

---

## 5. Worked example: pump_amm `multi_hop_swap.rs:772:20`

Record VA `0x1224d8` in `.data.rel.ro`, 24 bytes:

```
00000000 c8cc1100  39000000 00000000  04030000  14000000
^ low dword 0        ^ ptr = 0x11ccc8  ^ len 57  ^ line 772  ^ col 20
```

`0x11ccc8` is `.rodata` `"programs/pump-amm/src/instructions/swap/multi_hop_swap.rs"`
(57 bytes, the path is stored there back to back with the next constant and no NUL), and
the 24-byte stride is what separates it from the 16-byte plain `&str` constants in the same
section. The next record, `0x1224f0`, is 775:10 for the same path.

The referencing site is a single `lddw`:

```
0x8af0  mov64 r1, 0x1
0x8af1  mov64 r2, r8
0x8af2  lddw  r3, 0x1224d8      ; -> Location { multi_hop_swap.rs, 772:20 }
0x8af4  call  0x19a74           ; panic formatter
0x8af5  mov64 r2, r8
0x8af6  lddw  r3, 0x1224f0      ; -> Location { multi_hop_swap.rs, 775:10 }
0x8af8  call  0x19a70
```

so the two adjacent records 772:20 and 775:10 are the two panic sites of one expression
pair in the hop loop. The referencing function is `0x8a5c` (147 instructions); the second
record (`0x1224f0`, 775:10) is reached from the same function at `0x8af6`, and the ancestry
of that function is `0x7b78 -> 0x1d2ec -> 0x1b793 -> entry 0x1dc05`.

---

## 6. Verification

- `pump_fees` through this tool returns **63 Location records referenced from 50
  functions**, the same figures as the pump_fees location table, so the extraction
  reproduces an already-published result on a program with an independent record table.
- Every record's `len` equals the byte length of the file path it slices, for all 224
  records across the three pointer-slot programs (enforced in `pointer_slots()`: the slice
  must end in `.rs`), and for all 32 mayhem references (enforced against the `.rs`
  boundary of the path).
- The 24-byte vs 16-byte stride split is stable: `pump` 89 Location / 38 plain `&str`,
  `pump_amm` 72 / 28, `pump_fees` 63 / 20.
- No orphan records: 89/89 (pump), 72/72 (pump_amm), 63/63 (pump_fees) records have at
  least one referencing `lddw` site. Shared records exist and are counted: 13 (pump), 11
  (pump_amm), 6 (pump_fees) records have more than one referencing site, 7 being the
  maximum (a shared assertion inlined across call sites).
- Function starts are relocation-aware: `.rel.dyn` type 10 sites (unapplied call relocs)
  are excluded from start detection and the ELF entry point is added, giving 906 (pump),
  663 (pump_amm), 489 (pump_fees), 374 (mayhem) functions.

## 7. JSON schema

`maps/<program>_source_locations.json`:

```
program, binary, sha256, text_insns, functions, path_strings,
location_records, plain_str_consts, location_functions,
direct_refs, direct_functions,
files, program_files, runtime_files,
records[]           {addr, file, len, line, col}
strings[]           {addr, file, len}
functions_records   {"0x..": [{pc, addr, file, line, col}]}
functions_direct    {"0x..": [{pc, addr, file, len, kind, len_store}]}
func_sizes          {"0x..": insn count}
handler_files       {name: {entry, reach, program_files{file: count}}}
```
