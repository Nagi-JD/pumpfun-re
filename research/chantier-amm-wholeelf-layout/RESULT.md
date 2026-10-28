# chantier-amm-wholeelf: PumpSwap (pump_amm) layout layer + whole-ELF gap assessment

> **Nature.** BUILD + MEASURE on OUR harness (WSL, native `cargo rustc` v1.44 +
> `r34_r2.remap`). Every number below is measured with
> `ammresearch/tools/measure.py` vs `evidence/original/pump_amm/deployed.so`
> (SHA of deployed matches lalalune's `6a7ad345…`). Source oracle:
> lalalune/pumpfun-source (MIT), packet `research/claude-amm-union7-20261028`.
> Reconstruct source / link layout only; the deployed `.so` is never a build input.

## TL;DR (measured)

| state | matched/785 | raw | note |
|---|---:|---:|---|
| OUR AMM, clean build (bare `cargo rustc`) | **701** | **148** | `measure/before_701_148.json` |
| OUR AMM + ported text-layout profile (deployed-order `ordered.ld`, rebound to our symbols) | **701** | **167** | `measure/after_701_167.json`, **CLEAN** `lost[]==[]` both sets |
| lalalune union7 (reference, their built `.so` under OUR measure.py) | 780 | 220 | source-only; 248 with their layout layer |

- **Layout layer gain on our tree: raw 148 → 167 (+19), matched 701 unchanged, `lost[]==[]`** on
  both the matched set and the raw set — a clean, keepable raw gain from porting the
  pump text-layout profile to AMM.
- **Whole-ELF AMM is NOT in reach on this harness.** The remaining raw (167 → 248) and
  the 79-window normalized gap (701 → 780) both require lalalune's full per-file
  reconstruction *forms*, whose source does not build on our harness (see §3). This is
  the honest frontier, not a tooling gap.

---

## 1. Baseline correction (measured)

The composite chantier-amm-matched state (685 base + relines batches 1/2/3) measures
**701/785, 148 raw** on a CLEAN build (dedicated `CARGO_TARGET_DIR`). An intermediate
687 reading was a **stale cross-tree incremental-cache artifact**: the shared
`target-v1.44` dir served 685-base objects (e.g. `global_config` setters built with
`Location{line:7}` instead of the relined 220) because the ammr34 (685) and btree (701)
trees share the package identity `pump-amm-recovered v0.1.0`. Fix: build each source tree
into its own target dir. **The brief's 701/148 is correct.**

## 2. Gap vs lalalune 780 (measured)

- lalalune union7 built `.so` measured under OUR `measure.py`: **matched 780, raw 220,
  5 unmatched** = `0x19138 0x2ba60 0x351a8 0x4c750 0x6db20` (exactly their claim — our
  measurement harness is validated against theirs).
- OUR 701 matched set is a **strict subset** of lalalune's 780 (`weird == 0`: no window
  we match that they don't). Gap = **79 windows**, distributed **program-wide** across
  84 pump_amm functions (curve, admin, boost, coin_creator, create_pool, liquidity,
  swap/trade_v2/multi_hop, sweep, token_incentives, global_config, volume_accumulator,
  utils, `__global` entries) — not a localized residual.

## 3. Why porting lalalune's closures to ~780 is BLOCKED on this harness

Step 2 of the mission (port their window closures to reach ~780) does not reproduce:

1. **Their maintained source does not compile on our harness.** `shaw-src/programs/pump-amm`
   built with our toolchain fails with 7 errors (`E0061` arg-count mismatch at
   `lib.rs` → `legacy_sell::execute`, `E0412/E0432/E0433` unresolved types/imports,
   `E0603` private) — it needs their exact module wiring + the `native-transfer-fee`
   workspace crate API.
2. **Their 780 source is not the maintained tree.** `boost::calculate_virtual_quote_reserves`
   is byte-identical in our tree AND the maintained shaw tree (error on line 30), yet the
   780 binary wants it on line 22 — i.e. the union7 780 source is a *different lineage*,
   reconstructable only through the deep parent-packet chain (union7←union6←…), not sitting
   in any checked-out tree.
3. **Their 780 is built in a podman `solana-verifiable-build` container** (recipe
   `builds/recipe.json`), not bare `cargo rustc` — different codegen/hash lineage.
4. **Our remaining PURE-reline candidates (24) are not cleanly closeable.** Their deployed
   line targets reflect lalalune's full-file layout (e.g. `multi_hop_swap::vault_for_mint`
   → line 777, `sell::validate_pool_v2` → 520): closing one requires adopting lalalune's
   whole-file form, which shifts every already-matched window in that file (regression).
   Several others are duplicate monomorphized closures (one deployed window, many candidate
   copies). This is why the chantier correctly capped at 701 — the achievable pure relines
   (global_config/pool/fees/trade_v2/constant_product) were already taken.

**Conclusion:** advancing 701 → 780 on our harness = redoing lalalune's entire composite
positioning-device lineage per file, which is exactly the blocked source path. Noted and
not forced (per discipline).

## 4. Layout layer — PORTED to AMM and measured (the reproducible win)

AMM previously had no text-layout profile (bare `cargo rustc`). Ported the pump profile:

- Built our 701 tree through `RUSTC_WRAPPER=pump_text_layout_rustc.py` with
  `PUMP_TEXT_ROOT_CRATE=pump_amm_recovered`, `PUMP_TEXT_SCRIPT=<seed ordered.ld>`,
  `pump_text_layout_default.ld`. The SDK `sbpf-solana-solana` link script **equals**
  `default.ld` (shim gate passed), so the swap is valid. Recorded `link.map` +
  `linker-invocation.json`.
- **Seed `ordered.ld`**: lalalune's union7 `layout/ordered.ld` `.text` selectors (deployed
  window order), re-expressed as a `.text`-only script that passes the shim's `check_script`
  (`layout/seed_text_only.ld`, 785 selectors).
- **`relayout.py --rebind-ld`** (merged master #80) rebound 325 `.text` selectors from
  lalalune's hashes to OUR current symbols by content-identity pairing (699 unique pairs);
  117 stale left inert, 133 orphans in the catch-all (`layout/rebind_report.json`).
- **`dorelink.py`** relinked the recorded objects with the rebound `ordered.ld` (no
  recompile) → `relinked-symbols.so`.

**Measured: matched 701, raw 167 (+19 vs bare 148), `lost[]==[]`** on both sets
(`measure/lost_clean.txt`). Also tested the FULL union7 `ordered.ld` (text+data rebind):
identical 701/167 — data families barely rebind (`.rodata` 5/142, `.data.rel.ro` 0/73)
because our unnamed-constant section names don't pair to lalalune's.

**Why the deployed-order reorder itself adds 0 beyond +19:** at 701/785 the **84 unmatched
sections perturb addresses**, so relative-call immediates (`call rel32`) don't line up with
deployed even when `.text` is ordered — exactly the partial-reconstruction limit the
autobind packet (`chantier-T6-relayout-autobind`) documents. The +19 is the layout
profile's intrinsic section-handling gain (19 high-address data windows). Full layout
yield (→248) needs ~780 matched.

## 5. The 5 residual (per `ds-residual` SPECS, commit 308204e)

All 5 are large bodies (6–10 KB) and are defined against lalalune's **780** lineage, so
they presuppose being at 780 (not applicable to our 701 tree as-is):

| addr | id | class | n | containment |
|---|---|---|---:|---:|
| 0x4c750 | legacy_sell::cashback | forme de fonction (closeable) | 712 | 0.961 |
| 0x19138 | admin::set_reserved_fee_recipients | T3 body | 152 | 0.823 |
| 0x6db20 | GlobalVolumeAccumulator (impl) | T3 body | 235 | 0.652 |
| 0x351a8 | buy::distribute_cashback | T3 body | 539 | 0.687 |
| 0x2ba60 | create_pool::execute | T3 body | 877 | 0.658 |

0x4c750 is the one "form" window (owned/`&mut AccountInfo` reload + 59 Location lines, same
lever as mg-P-cash-01); closing it requires the 780 source form for `sell.rs`.

## 6. Reproduce

```sh
# baseline (clean)
bash build_btree_clean.sh                 # -> 701/148
# layout profile build (records link.map + linker-invocation.json)
bash build_amm_layout.sh                  # seed ordered.ld; -> 701/167
# rebind lalalune deployed order to our symbols + relink + measure
bash do_rebind.sh                         # relayout --rebind-ld + dorelink -> 701/167, lost[]==[]
```

Harness: `ammresearch/tools/measure.py`, `chantier-matched/lost.py`. Layout:
`tools/relayout.py` + `tools/drift_solver.py` (master #80), `pump_text_layout*.py`
(pre-existing worker scripts, referenced not copied), `t6work/dorelink.py`.

---

*Credit: form + layout oracle lalalune/pumpfun-source (MIT), `research/claude-amm-union7-20261028`.
Source/link-layout reconstruction only; deployed `.so` never a build input. No `.so`, no
secrets in this packet. PR-only — left for human review, not pushed.*
