# T5 — Reproduce pump's `.rodata` / data layout (the lddw-residual raw unlock)

> **Goal.** Flip the pump windows that are **normalized-matched but raw-fail with an `lddw`
> residual** into raw-exact, by reproducing the deployed `.rodata` / `.data.rel.ro` layout so
> every `lddw` immediate (a data address) matches. This is the data-layer complement to T6
> (`relayout.py` places `.text`; T5 places data). Together they convert the matched pile to raw.
>
> **Base:** pump s7p + merged chains = **~813 / 161** (after T3). Target raw: pass lalalune's 203.
> **Tool:** `tools/drift_solver.py` (classifies raw-fail as call-residual vs lddw-residual).

## Why this is the raw bottleneck

A normalized-matched window can fail raw for exactly two reasons (everything else is already
byte-equal): a **call imm32** (`.text` placement → T6) or an **`lddw` immediate** (a data address
→ T5). DeepSeek and the T3 wrappers keep flagging windows as "needs-T5": their only remaining
diff is `lddw` targets pointing into `.rodata` at different addresses than deployed. A data
address = the cumulative sum of the sizes/order of all `.rodata` records before it — so matching
the record **order, sizes, and dedup** makes the addresses (and thus the `lddw` immediates) match.

## Two parts

### Part A — source line-number preservation (load-bearing, do first)
Per lalalune's method (`WRAPPER_RECONSTRUCTION.md` §d.5): every statement must keep its **deployed
source line number**, because line numbers feed the `.rodata` `Location`/`Source` records (and
affect codegen). Reconstructed source that shifts lines by even one breaks these records.
- For each reconstructed file, pad with **blank lines** so `require!`/`error!`/panic sites land on
  their deployed lines (read the deployed line from the `Location` record the panic/error points
  to, or from the `--remap-path-prefix`'d path+line baked in the binary).
- This is cosmetic-looking but **load-bearing** — do not "clean up" blank lines.

### Part B — `.rodata` record order + dedup
Reproduce the order and dedup of the data records the `lddw`s target:
- **Strings** (log messages, `msg!`, error strings): declaration/use order and dedup.
- **Error-code tables / discriminants** (`#[account]`/`#[event]` discriminators, error enums).
- **`Location` records** (from Part A).
- Any `&[u8]`/const tables.

Method per window:
1. `tools/drift_solver.py` → take the raw-fail windows whose residual is **lddw** (not call).
2. For each `lddw`, resolve which `.rodata` record it targets (deployed) and which it targets
   (candidate); if they differ, find the source origin of that record (a string literal, an
   `error!(Code)`, a discriminator) and figure out what ordering/dedup difference moved it.
3. Fix the source so the record lands at the deployed address — usually a **declaration-order** or
   **dedup** change, or a line-number fix (Part A). Rebuild, re-measure.

## Possible tooling

A data analog of `relayout.py` may help: enumerate deployed vs candidate `.rodata` records, bind
by content, and report the minimal reordering. You may extend `tools/relayout.py` or add
`tools/data_layout.py`. Not required — per-window source fixes also work; the tool just scales it.

## Discipline

- **Faithful to deployed** — reproduce layout, never fabricate records or pad with junk bytes
  (blank **source** lines are fine — they are legitimate source; **binary** padding is not).
- **Measure every attempt** (`drift_solver` + window metric): raw (vs current), `lost[]` on both
  sets. Keep only if raw↑ with `lost[] = []` and matched not reduced. Revert otherwise.
- **One sub-claim = one coherent data fix = one PR = packet** `research/chantier-T5-<what>/`.
  Stack linearly like #22–#41. No `.so`, no secrets. PR-only.

## Interaction with T6

T5 (data addresses) and T6 (`.text` placement) are independent residual classes but both are
needed for a window with both a call- and an lddw-residual. Coordinate: T6/`relayout.py` is owned
by Nagi; T5 is yours. A window raw-fails until BOTH its residuals are zero — so expect some
windows to flip only after T5 **and** a relayout pass. Mark a window `needs-T6` if after your data
fix its only residual is a call imm32.
