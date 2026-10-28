# chantier-fees whole-ELF layout layer — validated on the window-complete (585/585) Fees program

End-to-end validation of the whole-ELF **layout layer** (lalalune's T6
`ordered.ld` deployed-order technique) on `pump_fees`, measured on the box with
the shipped window metric. Every number here was produced by a real
build+measure on the Fees byte-race worker (Anza platform-tools v1.44 build +
strip v1.52 `llvm-objcopy`); none is asserted.

**Bottom line.** The layout layer is **real and effective but plateaus below
whole-ELF on Fees**: deployed-order `.text` + `.data.rel.ro` drives raw
**288 → 403 / 585** (99.11 % byte-identical stripped ELF). It does **not** reach
585/585. The residual is dominated by `.rodata` layout, whose deployed-order
reconstruction *regresses* under naive content pairing.

---

## Step 1 — window completion: 585/585 normalized CONFIRMED

Parent: the verified `extend-qualified` baseline (582 normalized / 200 raw,
unmatched `[120816, 147944, 163920]`, symbols sha `ca9e6a93…`). Three source
patches applied in lineage order, each rebuilt+measured with `~/rebuild_measure.sh`:

| state | normalized | raw | unmatched_original |
|---|---:|---:|---|
| pristine baseline | 582 | 200 | `[120816, 147944, 163920]` |
| + crank (`crank_donation_fee_pda`, window **147944**) | 583 | 200 | `[120816, 163920]` |
| + create (`create_donation_fee_pda`, window **163920**) | 584 | 200 | `[120816]` |
| + sweep (`sweep_buyback`, window **120816**) | **585** | **288** | **`[]`** |

**`normalized 585, unmatched_original []` — window-complete.** raw = **288** at
completion (matching the ~288 expectation).

> Provenance note (honest): on `Nagi-JD/pumpfun-re` master only the **147944**
> packet is merged (PR #48, `research/chantier-fees-wholeelf-147944`). The
> **163920** and **120816** patches are **not** in the repo; they were applied
> from the box's working patches (`create_rs_only.patch`, `sweep_source.patch`).
> The box `sweep-120816-result/NOTE.md` had recorded 120816 as *unclosed* after
> 8 register-allocation hypotheses — the box's current `sweep_source.patch` is a
> working successor that **does** close it (585).

---

## Methodology trap (important for the pump push)

`cargo`/`rustc` does **not** track `ordered.ld` as a build input. Swapping
`ordered.ld` alone never triggers a relink — the cached `.so` is silently reused.
We first measured *four* different scripts (default / deployed-order / reversed /
single-move / even a syntactically **broken** script) and got a **byte-identical**
`.so` every time. The fix: **`touch` a source file before each rebuild** to force
`rustc` to re-run the linker with the new script. Every Step-2 number below is a
forced relink of the **identical** window-complete source (same input objects),
so the only variable is the linker-script section ordering.

---

## Step 2 — the layout layer

The fees `ordered.ld` is the SDK default script with its `.text`, `.rodata` and
`.data.rel.ro` `*(…*)` catch-all rules expanded into explicit, deployed-order
per-section selector lists (each followed by the catch-all). Selectors are bound
to deployed slots by **content identity** (the window metric's normalized
signature — the deployed `.so` is stripped, so content identity is the
name-stable equivalent of symbol binding), reusing the exact pairing the metric
uses. Generators: `gen_ordered.py` (`.text` only) and `gen_ordered2.py`
(`.text`+`.rodata`+`.data.rel.ro`, with the lddw-pointer correspondence binding
for data sections).

Measured ladder (all forced relinks, identical source, raw = byte-exact windows;
`normalized` stays 585 and `unmatched_original` stays `[]` throughout):

| layout | raw | Δ vs default |
|---|---:|---:|
| pure default catch-all | 253 | — |
| stale shipped `ordered.ld` (box pristine, ~586 stale selectors) | 288 | +35 |
| deployed-order **`.text`** (438/585 content-paired) | **393** | **+140** |
| deployed-order **`.text` + `.data.rel.ro`** (BEST) | **403** | **+150** |
| deployed-order `.text` + `.data.rel.ro` + `.rodata` | 269 | −(regress) |

**Deployed-order `.text` is the big lever: raw 288 → 393 (+105 over the box
baseline).** Adding `.data.rel.ro` → **403** (`.data.rel.ro` residual is then only
89 B). Adding `.rodata` **regresses** to 269 — the T6 failure mode: the 611
anonymous `.rodata..L*` constant pools are duplicate-content, so content pairing
cannot disambiguate which copy owns which deployed slot and a reorder scatters
them, breaking already-raw pointer windows. (SHF_MERGE `.rodata.cstN` pools are
excluded from explicit selectors — listing per-object selectors for merge
sections makes lld mis-assign orphan sections and the link fails.)

### Residual is entirely data-address-bound after `.text` layout

At the 393-raw (`.text`-only) build, of the 438 uniquely content-paired windows:

- **262 raw-exact**, **176 non-raw**;
- of the 176 non-raw: **176 pointer-bearing** (contain an `lddw` opaque relocated
  pointer into `.rodata`/`.data.rel.ro`), **0 call-offset-only**.

I.e. deployed-order `.text` **fully solved the relative-call-offset problem** —
every remaining miss is a data-pointer value that only matches if the pointed-to
`.rodata`/`.data.rel.ro` object sits at its deployed address. This is exactly why
the recipe must also order those two sections, and exactly why `.rodata` is the
hard part.

---

## Whole-ELF comparison (stripped, v1.52 `llvm-objcopy --strip-all`)

Best layout (`.text` + `.data.rel.ro`, raw 403/585):

| | value |
|---|---|
| candidate stripped sha256 | `8fb0a24d…6d955` |
| deployed stripped sha256 | `5b6ceda5…b3dcf` |
| **byte-identical** | **NO** |
| stripped size (both) | 873 256 B (identical) |
| differing bytes | **7 783 (0.891 %) → 99.109 % identical** |

Residual attribution (byte diff mapped to deployed sections):

| section | differing bytes |
|---|---:|
| `.rodata` | 5 592 |
| `.text` | 2 102 |
| `.data.rel.ro` | 89 |
| everything else (`.dynsym`, `.dynstr`, `.rel.dyn`, `.dynamic`, `.gnu.hash`, `.hash`, ELF/program headers) | **0 (byte-identical)** |

**Characterised residual.** Whole-ELF byte-identity is **not** reached on Fees
with this recipe. Note the dynamic-linking metadata (`.dynsym` ordering,
relocation tables, `.dynamic`, hashes, headers) is **byte-identical** — the
~30-byte dynsym-ordering / reloc residual lalalune reported on the pump *Mayhem*
build **does not exist here** (that class of residual is zero). The entire 7 783-byte
gap is **content/layout**: `.rodata` (5 592 B — its deployed order is unsolved and
regresses) and the `.text` windows that point into it (2 102 B), plus a tiny
`.data.rel.ro` tail (89 B).

---

## What this means for the pump whole-ELF push

- **The layout layer is validated as a genuine mechanism**, not a no-op:
  deployed-order `.text` is monotonic and large (+140 raw), `.data.rel.ro` is
  essentially solvable (+10, 89 B residual), and the binding is non-regressing
  for uniquely-content-paired sections.
- **The open problem is `.rodata` deployed-order reconstruction.** Pure content
  pairing scatters the many duplicate-content anonymous constant pools and
  regresses. Closing it needs reference/call-graph-based disambiguation of which
  `.rodata..L` copy owns which deployed slot (the T6 "preserve + targeted
  relocation" discipline, applied to data), not a global content sort.
- **Operational gotcha to carry over:** `ordered.ld` is not a cargo dependency —
  force a relink (touch a source file) or every layout iteration silently
  measures the stale cached `.so`.
- SHF_MERGE `.rodata.cstN` pools must stay in the catch-all, never explicit
  per-object selectors (the link fails otherwise).

## Reproduction

See `build-recipe.md`. Generators: `gen_ordered.py`, `gen_ordered2.py`. The best
measured script is `ordered.text-datarelro.ld` (build-specific: references the
CGU hash `85ade9ce…` of this window-complete build). No `.so` is committed.

## Attribution

Layout technique reproduces lalalune/pumpfun-source (MIT) T6 `ordered.ld` /
`relayout.py` whole-ELF method. The three window-closing source patches reproduce
lalalune's crank / create / sweep patches. Credit: lalalune.
