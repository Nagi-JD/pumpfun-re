# Open tasks — byte-identity race

Contributions are **PR-only** (`master` is protected). Fork, branch, open a PR. One task = one PR
= one research packet under `research/<your-task-name>/`.

This is a race to raise **matched function windows** (and raw byte-exact bodies) on the four core
pump.fun programs, measured with lalalune/pumpfun-source's own window metric, stacking changes on
their latest published checkpoints (MIT). No core program is whole-ELF identical yet; that is the
open wall, bounded by the lost original source — do not claim it.

## Current standing (vs lalalune's latest checkpoints)

| Program | Theirs (Round36, 27 Oct) | Here (verified) | Status |
|---|---:|---:|---|
| Pump | 738 / 1035 (145 raw) | **786 / 1035** (137 raw) | lead **+48** normalized; raw behind (whole-ELF, see below) |
| PumpSwap | 651 / 785 (148 raw) | **681 / 785** (148 raw) | lead **+30**; raw tie |
| Fees | 582 / 585 (200 raw) | 582 / 585 (200 raw) | tie; native byte-identical repro in `research/fees-extend-stack-582/` (PR #13). The 3 hard windows (sweep_buyback reg-alloc, crank/create_donation wrapper codegen) are confirmed whole-ELF, not per-site |
| Mayhem | 432 / 441 (100 raw) | 429 / 441 | behind **−3** (whole-ELF, same wall) |

**Per-site ceiling reached; the whole-ELF / raw wall is confirmed by measurement.** A block-reorder
experiment (reordering a 118-function size-identical run to the deployed internal order via `ordered.ld`)
**regressed** raw 137→128: a function's position is the cumulative sum of all preceding function sizes, so
symbol-order alone cannot place a callee at its deployed offset. Do not re-attempt order-only reorder for
raw — it is the open whole-function-layout problem (bounded by lost source), the same wall as Mayhem's 9 and
Pump's raw gap. Normalized-window gains per-site are exhausted on all four programs.

## How it works here (read first)
- `research/README.md` — what each existing packet did and how it was measured.
- `research/pump-r23-race-2/`, `research/amm-race-2/`, `research/fees-progid-579-raw/` — worked
  examples: patch + build recipe + measure JSON + RESULT.md.
- `tools/sbftool.py` — sBPF disassembler. `tools/bindiff_report.py` — divergence classifier.
- Method that works: (1) build natively, direct `cargo rustc` with the exact platform-tools
  version (NOT the `cargo-build-sbf` wrapper — it changes layout); (2) place each `error!` closure
  on its DEPLOYED source line (file path + line are baked into the binary), using `--remap-path-prefix`
  so compiled paths match the deployed workspace; (3) for leftover block-order diffs (`jne` vs
  `jeq;ja`), use the LLVM-IR method: emit IR, reorder blocks with `llc` until 0 diff, then find the
  source form. Blind source-shape guessing does not work.

## Claimable tasks
Comment on an issue (or note in your PR) which you're taking, to avoid collisions.

**Pump (Round34 base):**
- `pump_quote` module — 12 unmatched windows; logic folded into `nested_create.rs`. Reconstruct it.
- `buy_v2` 959/983 — the partial-fill branch (`computed > real_token_reserves && partial`).
- `trade_v3` 1140, `lib.rs` 629 — differently-shaped caller bodies.

**PumpSwap (their 643 base):**
- `multi_hop` 941 closure (lives in a helper the candidate doesn't split out).
- The 520-byte window with no error tuple (0x89d0).

**Fees (their 582 base):** Sweep, Crank, CreateDonation — multi-region / missing-code, hard.

**Mayhem (their 432 base):** the 9 remaining are whole-function codegen divergences — only take one
if you can recover the missing source semantics (the upstream authors flag these as open too).

## Hard rules (a PR that breaks any of these will not be merged)
1. **Measured, or it didn't happen.** Paste the before/after window counts from the metric script.
   Keep a change only if it gains windows with **no regression** (matched set AND raw set).
2. **Behavior must match the DEPLOYED binary**, not "clean" logic. Restoring a check/closure the
   deployed binary provably contains (cite the address + error variant) is faithful; never add a
   check it lacks, remove one it has, or change an error code.
3. **No cheating the metric.** No macro that hardcodes the deployed file/line as a literal. The
   deployed `.so` is never a build input (recovered must come from compiling source).
4. **No PRs to lalalune/pumpfun-source**, and don't embed or patch their captured `.so`.
5. Credit: these build on lalalune/pumpfun-source (MIT) — keep the attribution in your packet.
