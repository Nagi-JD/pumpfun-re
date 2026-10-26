# P0 pump_fees rebuild checklist

Companion to [`../fees_locations_and_memmove.md`](../fees_locations_and_memmove.md).
Everything in this file is measured on
`evidence/original/pump_fees/deployed.so` in the `pumpfun-source` tree.

## Measured on the deployed binary

| item | value | artifact |
|---|---|---|
| original source tree recovered from panic `Location` records | 20 embedded `programs/pump-fees/src/...` paths, 11 with anchors | `../fees_locations_and_memmove.md` §2–§3 |
| panic `Location` records | 63 (26 program, 37 dependency), 50 functions reference one | `maps/fees_locations.json` |
| per-file panic anchors (line:col the rebuild must reproduce) | `common/mod.rs` 21:48, 21:56, 33:56; `state.rs` 50:1, 67:32, 113:1, 135:1, 154:1, 398:19, 398:33, 451:19; `lib.rs` 27:1, 28:1; … | §3 |
| `sol_memmove_` call sites | **1**, insn `0x184de` (byte `0xc26f0`), thunk `0x184dd` (`0xc26e8`) | §5 |
| handlers that can reach it | `update_fee_shares` (`0x138d4`) and `update_fee_shares_v2` (`0x1395a`) only | `maps/fees_handler_reach.txt` |
| total functions / exits / call insns / syscall sites | 489 / 555 / 4741 / 155 (16 syscalls) | §6 |

## What this means for a byte-identical build

1. **FIX 1 (tree) is now a checklist.** The original layout is
   `lib.rs`, `state.rs`, `common/mod.rs`, `instructions/{admin,fee_sharing}/*`,
   `instructions/buyback/mod.rs`, `instructions/withdraw.rs` — one file per
   instruction, contexts and events inside the instruction files / `state.rs`.
   A rebuild that keeps `contexts.rs`, `types.rs`, `donation.rs`, `social.rs`,
   `sharing*.rs` cannot land the `.rodata` / `.data.rel.ro` anchors above even if
   `.text` matches, because every `file!()`/`Location` string and its
   line/column are part of the image.
2. **FIX 2 (the `sol_memmove_` user) is localised.** The copy is inside the
   shareholder path, at a 16-byte stride with `src = dst + 16`
   (`len = (a - b - 1) * 16`): an in-place gap-closing copy, i.e. the source
   needs one overlapping `&mut` copy over a 16-byte element type. `upsert_fee_tiers`
   and `extend_fee_config` are measured **not** to reach it (they reach only the
   `sol_memcpy_` thunk). The current candidate's `{ Pubkey, u16 }` shareholder
   shape is 40 bytes and does not match the 16-byte stride, so the element type
   behind that vector is still open (`fees_locations_and_memmove.md` §5.2).
3. **FIX 3 (the "~3 missing functions") is located by a build-side diff.**
   The deployed program has **no** unreachable function (489/489 reachable from
   `entry` + dispatcher), so the gap cannot be found by dead-code analysis; it
   needs a build-side per-function diff (size + hash, smallest deltas first).
   Also correct the figure: the deployed program has **489** functions and
   **555** `exit`s — 555 is the exit count, not the function count.

## Rebuild steps

1. Build the current candidate unchanged, dump its function index with the same
   census (`fees_p0_probe.py summary`), and diff against the 489-function index:
   report only the functions whose size differs by ≤ 8 insns first.
2. Re-run `fees_locations.py` on the candidate `.so`. Every anchor listed in §3
   must be present at the same line:col; missing anchors name the files still
   laid out wrongly.
3. Confirm the `sol_memmove_` site exists in the candidate after the shareholder
   path is adjusted (16-byte element, overlapping copy); if the site count is 0
   the tree step is not finished, if it is > 1 look for a second gap-closing copy.
