# chantier T6 — `tools/relayout.py`, the whole-ELF layout regenerator

**Goal.** Build the T6 layout enabler lalalune used on Fees (585/585): a tool that
regenerates the linker script `ordered.ld` so the `.text` layout tracks the
deployed binary's window order after any source change, binding input sections
(functions) by name / content identity / call-graph color. This is the layer that
makes relative-call offsets line up for raw byte-exactness (order-only reorder
without it is measured regressive).

**Scope discipline.** Canonical `s7` was never modified; all builds run from a copy
(`/home/nagi/t6work/s7copy`). Every number below was MEASURED with
`pumpround34/metric/measure.py` (the shipped window metric) and
`tools/drift_solver.py`; none is asserted.

---

## What `relayout.py` does

`ordered.ld` is `pump_text_layout_default.ld` with its `.text : { *(.text*) }`
rule expanded into an explicit, ordered list of per-function input-section
selectors (`*<objfile>(".text.<mangled>")`) followed by the `*(.text*)`
catch-all. The build consumes it through `pump_text_layout.py` →
`rust-lld` (`PUMP_TEXT_SCRIPT=ordered.ld`). `relayout.py` regenerates that ordered
list; it does **not** replace the recipe or the default skeleton, and its output
passes `pump_text_layout.check_script` verbatim.

Inputs: `DEPLOYED.so` (window-order target), `SYMBOLS.so` (candidate build with
symbols), and the build's `LINK.map` (rust-lld `-Map`, the authoritative catalog
mapping every emitted `.text.<sec>` → owning object file + VMA, in physical order).

**Binding model (and why it is order-preserving by default).**
A candidate section that is already raw-exact is, by definition, already at its
correct deployed slot — moving it can only break it. So `relayout` pins the live
build's physical order (from `link.map`) as its backbone: idempotent and
non-regressing by construction. A section's deployed slot, when it must be placed,
is bound by:

1. **exact content identity** — `(size, normalized_sha256, relocation-pattern)`
   1:1 greedy pairing, deployed-address first (the same signature
   `measure.py`/`drift_solver` use, reused here). The deployed `.so` is stripped,
   so content identity is the name-stable equivalent of symbol binding.
2. **call-graph adjacency** — a section with no deployed content-match keeps the
   deployed neighbourhood of its surrounding matched sections.

A global deployed-**address** sort is explicitly **not** safe on a *partial*
reconstruction and `relayout` does not do one by default: see the regression note
below.

Targeted relocation: `--to-deployed PATTERN` moves each content-matched section
whose name contains `PATTERN` to its deployed-order position (immediately after
the nearest matched section whose deployed VMA precedes it). This is used to pull
a body whose normalized form matches but whose raw fails purely on a relative-call
offset into the slot that zeroes that call's delta.

---

## Baseline (measured, this environment)

Build: `s7copy` + merged-chain recipe (`-C passes=mergefunc`), shipped
`repro/.../ordered.ld`, re-linked through the recorded `linker-invocation.json`
so only the linker script varies (identical cached objects ⇒ pure layout delta).

| build | matched | raw (`exact`) | candidate `.so` sha256 |
|-------|---------|---------------|------------------------|
| **B0** baseline | 782 | 127 | `af8d44…013ba6` |
| identity re-link control (shipped `ordered.ld` via receipt) | 782 | 127 | `af8d44…013ba6` (byte-identical) |

> Note on `802/161`. The repo's recorded frontier is `802/161`; this isolated
> environment measures `782/127` from the same recipe. The gap is embedded build-
> path strings in `.rodata` (the build runs from a different absolute path than the
> reference environment), which shifts raw matches on path-bearing windows. It is
> **constant across every re-link here** because all re-links share the same cached
> objects, so the layout-only, no-regression property the gate tests is unaffected.
> The identity control above (byte-identical re-link) confirms the harness is
> faithful.

---

## Idempotency test (the correctness gate) — PASS

Regenerate `ordered.ld` from the current good build and re-link:

```
python3 tools/relayout.py DEPLOYED.so  out/t6base-symbols.so  link-t6base/link.map \
        --cand-stripped out/t6base-candidate.so  -o ordered_preserve.ld
# re-link cached objects with the regenerated script → t6pre
```

Result — the regenerated script re-links to a **byte-identical** binary:

| metric | B0 | after relayout regenerate | Δ |
|--------|----|--------------------------:|---|
| matched | 782 | 782 | 0 |
| raw (`exact`) | 127 | 127 | 0 |
| candidate sha256 | `af8d44…013ba6` | `af8d44…013ba6` | identical |
| **lost[]** | — | **[]** | — |

`cmp2.py out/t6base-m.json out/t6pre-m.json` →
`matched 782 -> 782 +[] -[]` · `raw 127 -> 127 +[] -[]`.

Regenerating from the current good state does not regress. The regenerate lists
all 993 live sections explicitly (993 selectors, `content_matched = 780`,
`unique_pairs = 780`) yet reproduces the exact physical order — proving the
`link.map` parse, the selector reconstruction (plain `.rcgu.o` and
`libX.rlib:member.o` forms), and the content binding are all correct.

---

## Movement test — PASS (measured +1 raw, byte-identical recovery)

Demonstrates `relayout` placing a function at its deployed slot to zero a
relative-call delta. Target: `solana_borsh::v1::get_instance_packed_len`
(unique section, currently raw).

1. **Perturb** — move its selector to the top of the `.text` list
   (`perturb.py`), re-link → `t6perturb`:

   `cmp2 B0 → perturb` → `raw 127 -> 126  +[]  -['0x1966f0']`.
   matched stays 782 (the body still normalizes-matches its deployed window) —
   i.e. a pure call-only raw-fail. `drift_solver` on the perturbed build:
   `intervals_nonzero 359 → 361`, `call_only_raw_fail 228 → 229`.

2. **Relocate** — `relayout … --to-deployed get_instance_packed_len17h29d07d87687fe6d3`
   on the perturbed build (report: `mode preserve+relocate(1)`), re-link → `t6fix`:

   `cmp2 perturb → fix` → `raw 126 -> 127  +['0x1966f0']  -[]`.
   `cmp2 B0 → fix` → `raw 127 -> 127  +[] -[]`, and `t6fix` candidate sha256 =
   `af8d44…013ba6` — **byte-identical to B0**.

`ordered_movement.diff` (included) is the whole change relayout made: the single
selector moves from line 14 (perturbed top) back to line 846 (its deployed slot).
Measured raw delta of the relocation: **+1** (`0x1966f0` recovered), the window's
relative-call offset re-zeroed by placement alone.

---

## Finding: the shipped round-34 `ordered.ld` is ~85% stale for a live build

Of the shipped script's 952 selectors, only **142 are live** in this build; **810
are stale** (their mangled-hash section names belong to a different codegen state),
so for this build the shipped script is largely inert and the layout is mostly
governed by the `*(.text*)` catch-all. This is why a naive from-scratch
deployed-**address** sort regresses here (measured `raw 127 → 115`, 12 windows
lost): the deployed `.text` is dense with tiny duplicate-normalized stubs (e.g. 13
distinct 16-byte windows sharing one normalized body — dup-multiplicity up to 13),
and content pairing alone cannot disambiguate which copy owns which slot, so a
global sort scatters them and breaks already-raw windows. `relayout`'s
preserve-order backbone plus targeted relocation avoids this: it regenerates a
**complete, live** 993-selector script (the maintenance value across source edits)
and only moves what is explicitly requested, each move verifiable by measurement.

---

## Usage

```
python3 tools/relayout.py DEPLOYED.so SYMBOLS.so LINK.map \
        [--cand-stripped STRIPPED.so] [--default-ld pump_text_layout_default.ld] \
        [--to-deployed PATTERN ...] [-o ordered.ld] [--report report.json]
```

- `DEPLOYED.so`   — deployed reference (read-only), e.g.
  `pumpre/repo/evidence/original/pump/deployed.so`.
- `SYMBOLS.so`    — the native build output (`out/<label>-symbols.so`).
- `LINK.map`      — the build's `PUMP_TEXT_RECORD_DIR/link.map`.
- `--to-deployed` — repeatable; relocate matched sections whose name contains the
  substring to their deployed slot.

Default (no `--to-deployed`) = regenerate the current layout faithfully
(idempotent). Feed the result back as `PUMP_TEXT_SCRIPT` on the next build.

## Reproduction harness (in this packet)

- `t6build.sh LABEL WORKDIR ORDERED_LD [EXTRA_RUSTFLAGS]` — mirrors
  `pumpround34/b34-merge.sh` into an isolated `/home/nagi/t6work` area (never
  touches canonical `s7`). Full compile.
- `relink.sh LINKDIR ORDERED_LD LABEL` + `dorelink.py` — re-link the cached input
  objects recorded in `LINKDIR/linker-invocation.json` with a different script.
  Identical objects ⇒ pure layout delta (seconds, not minutes). This is how every
  measurement above isolates layout from codegen.
- `perturb.py INPUT OUTPUT PATTERN` — move one selector to the top (the movement-
  test perturbation).
- `report_preserve.json`, `report_fix.json` — `relayout` placement reports.
- `ordered_movement.diff` — the one-selector move relayout performed to recover the
  raw window.

Full run:

```
# baseline
./t6build.sh t6base  s7copy  repro/.../ordered.ld
# idempotency
python3 tools/relayout.py DEP out/t6base-symbols.so link-t6base/link.map \
        --cand-stripped out/t6base-candidate.so -o ordered_preserve.ld
./relink.sh link-t6base ordered_preserve.ld t6pre
python3 pumpround34/cmp2.py out/t6base-m.json out/t6pre-m.json     # expect lost[]=[]
# movement
python3 perturb.py ordered_preserve.ld ordered_perturb.ld get_instance_packed_len17h29d07d87687fe6d3
./relink.sh link-t6base ordered_perturb.ld t6perturb               # raw -1
python3 tools/relayout.py DEP out/t6perturb-symbols.so relink-t6perturb/link.map \
        --cand-stripped out/t6perturb-candidate.so \
        --to-deployed get_instance_packed_len17h29d07d87687fe6d3 -o ordered_fix.ld
./relink.sh link-t6base ordered_fix.ld t6fix                       # raw back to baseline
```

## Bottom line

- **Idempotency gate: PASS** — regenerate from the current good build re-links
  byte-identical (`782/127`, `lost[] = []`). (Repo frontier is `802/161`; the raw
  offset is an environment path artifact, constant across re-links — the
  no-regression property is unaffected.)
- **Movement: PASS** — relayout relocated one function to its deployed slot,
  measured raw **+1** (recovered `0x1966f0`), re-link byte-identical to baseline;
  the whole change is the single selector in `ordered_movement.diff`.
- `relayout.py` fits the existing `pump_text_layout` pipeline (output accepted by
  `check_script`) and regenerates a complete, live 993-selector script where the
  shipped one is 810/952 stale.
