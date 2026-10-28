# chantier T6 — relayout.py auto-binds `ordered.ld` (Fees whole-ELF reproduced from scratch)

**Goal.** Turn the just-proven Fees `.text`-selector refresh into a reusable tool:
enhance `tools/relayout.py` so it AUTOMATICALLY regenerates `ordered.ld` by
re-binding every stale input-section selector to the CURRENT symbol that occupies
its deployed slot, after source patches change symbol-hash suffixes. This is the
pump raw keystone — every window closed on pump rehashes the patched functions, and
a stale `ordered.ld` selector sends that function to the `.text` tail instead of its
deployed slot, so raw does NOT follow normalized until the selector is rebound.

**Bottom line (MEASURED on the Webdock Fees worker, not asserted):**
`relayout.py --rebind-ld` regenerates the Fees `ordered.ld` from the **stale**
(raw-288) script with **zero hand-editing** and the build reaches
**raw 585 / normalized 585, `unmatched_original == []`**, stripped `.so`
**byte-identical to `deployed.so`** over its 873,256-byte meaningful prefix,
SHA256 **`5b6ceda57863f0dcc3e0e3623052f8342c2c81883379699e71d7ed5383cb3dcf`** — the
`WRAPPER_RECONSTRUCTION.md` endstate hash. The regenerated script is **byte-identical
to the hand-fixed `ordered.ld`**. The tool is **idempotent** (re-binding a good build
produces zero edits) and **non-regressing by construction** (correct selector lines
are never touched). **It is ready to run on pump after each window-closure patch.**

Scope discipline: canonical sources/scripts were not modified. All work ran in an
isolated `~/t6auto` workspace plus the collision-free Fees build tree
`/work/next649/extend-qualified`; the build tree was returned to its starting
(hand-fixed) `ordered.ld`. No `.so` is committed to this packet.

---

## The bug relayout automates away

The deployed `.text` order is encoded in `ordered.ld` as an explicit, ordered list
of per-function input-section selectors
(`*<objtoken>(".text.<mangled>")`), each selector's **line position = its deployed
slot**, followed by the `*(.text*)` catch-all. A selector names its function by the
**full mangled name**, which ends in a Rust symbol-hash `…17h<16hex>E`.

When a source patch changes a function's MIR, only that hash suffix changes. The
selector still names the OLD hash → it matches no current section → rust-lld drops
it and the rehashed function falls through the catch-all to the **tail of `.text`**,
far from its deployed slot. That single misplacement breaks the raw match of the
window itself AND of every window whose relative call (`0x85 imm32`) crosses the
resulting address gap.

Fees, measured here: the three window-completion patches rehashed **9** functions
(`Vec::from_iter`, and `try_deserialize{,_unchecked}` for BuybackVault / SocialFeePda
/ DonationFeePda / FeeProgramGlobal). The stale script therefore scored
**normalized 585 but raw 288** (`drift_before_raw288.json`:
`exact 288, call_only_raw_fail 271, intervals_nonzero 4` — four tail gaps spoiling
271 call-only windows). The data layer was already clean (T5): `data_residual 0`.

---

## How the binder works (`--rebind-ld`)

`relayout.py DEPLOYED.so SYMBOLS.so LINK.map --rebind-ld ordered.stale.ld -o ordered.ld`

It keeps every selector's **line position fixed** and rewrites only the STALE ones.
A current section is bound to a stale selector by three layered identities:

1. **Content identity (primary gate).** Each current `.text` function pairs 1:1 with
   a deployed window by `(size, normalized_sha256, relocation-pattern)`
   (`drift_solver.unique_pairs` — the same signature `measure.py` uses). The paired
   deployed window's address IS the deployed slot. Because `deployed.so` is stripped,
   content identity is the name-stable equivalent of symbol binding: a body keeps its
   slot across a hash change. A rebind is only accepted when the orphan's body pairs
   to a deployed window (else it is reported, not guessed).

2. **Name-base identity (grouping).** The demangled prefix (everything except the
   trailing `17h<hex>E`) is stable across a MIR change, so it groups each stale
   selector with its rehashed "orphan" (a current section no live selector names).
   For a group of size 1 this binds directly; for a group of size > 1 (several
   instantiations sharing a demangled name) the members are ordered by their paired
   deployed VMA (content) so slot *i* binds to the *i*-th deployed window.

3. **Call-graph color (dup-pool tie-break).** When two orphans in a group have
   IDENTICAL normalized bodies (content cannot order them), they are disambiguated by
   caller/callee identity: each orphan's callee-name-set is matched to the callee-set
   its candidate slot EXPECTS (the deployed window's callees mapped back through the
   content pairing). Deterministic, with a VMA-order fallback.

Stale selectors whose function was genuinely **deleted/renamed** (no orphan shares
its demangled base) are left untouched and reported (a selector matching nothing is
inert → harmless). Data families (`.rodata` / `.data.rel.ro`) use the same
stale-detection with name-base identity; when none is stale (the common case once T5
data layout is clean) they are left byte-identical. Only STALE lines change, so the
tool is **idempotent** and **non-regressing**: it never reorders the already-correct
backbone (which the T6 experiments proved a global deployed-address sort would
regress — 127→115 raw on pump — because of dup-stub scatter).

---

## Fees reproduction (MEASURED, step by step)

Build tree `/work/next649/extend-qualified`, `~/rebuild_measure.sh`
(custom `linker.sh` swaps the SDK default script for the build-tree `ordered.ld`),
deployed ref `~/feesr34/evidence/original/pump_fees/deployed.so`. Source =
window-complete (585-normalized) Fees.

| step | ordered.ld | normalized | raw | unmatched | artifact |
|---|---|---|---|---|---|
| 1. baseline (stale script) | `ordered.stale.ld` | 585 | **288** | `[]` | `measure_before.json`, `drift_before_raw288.json` |
| 2. **regenerate** (relayout `--rebind-ld`) | `ordered.regen.ld` | — | — | — | `rebind_report.json`, `regen_vs_stale.diff` |
| 3. rebuild with regenerated script | `ordered.regen.ld` | 585 | **585** | `[]` | `measure_after.json`, `drift_after_raw585.json`, `data_layout_after_raw585.json` |

- **relayout output == hand-fixed script, byte-for-byte** (`cmp` identical). The tool
  made exactly the 9 edits in `regen_vs_stale.diff` (the same diff as the manual
  `ld.patch`): 9 selectors rebound, the inert `DonationFeePdaCreated::data` selector
  left alone, data families untouched. `rebind_report.json`:
  `edits 9, total_rebound 9, total_unresolved 1, total_unplaced 4`
  (`.text`: stale 10 / orphan 9 / rebound 9 / unresolved 1 = the deleted `…::data`;
  `.rodata`: 4 "unplaced" = the `.cst{4,8,16,32}` SHF_MERGE pools that correctly stay
  in the catch-all; `.data.rel.ro`: nothing stale).
- **raw 288 → 585** after rebuild; `drift_after_raw585.json`:
  `exact 585, call_only_raw_fail 0, intervals_nonzero 0`.
- **`lost[] == []`**: both measures report `unmatched_original: []`;
  `data_layout_after_raw585.json`: `data_residual 0, lddw_sites 0, exact 585`.
- **stripped `.so`**: `llvm-objcopy --strip-all` → 873,256 B, SHA256
  `5b6ceda5…cb3dcf`, equal to `deployed.so`'s first 873,256 B (deployed's trailing
  75,688 B are loader zero-pad).

### Idempotency gate — PASS
Re-binding the GOOD (raw-585) script against the raw-585 build:
`idem_report.json` → `edits 0, idempotent true`, output byte-identical to input
(`cmp` identical). A clean build produces no changes.

### Call-graph color — validated load-bearing
`callgraph_validation.txt`: for all 9 rebound orphans the candidate callee-name-set
(3–7 callees each) EXACTLY matches the deployed slot's expected callee-set — the
signal that disambiguates a dup pool. On Fees every orphan has a distinct demangled
base, so the dup-pool permutation is not *needed* to break a tie here; the primitive
is nonetheless exercised and proven correct on real data (several
`…AccountDeserialize>::try_deserialize` instantiations share a truncated suffix and
are told apart by their callee-sets + struct-name prefix).

---

## Applying to pump

Pump's raw frontier is gated the same way: Shuai-Qing's converging analysis closes
windows (normalized ↑) but each closure patch rehashes its functions, so the shipped
`ordered.ld` selectors go stale and the functions drop to the `.text` tail — raw does
NOT follow normalized. Run relayout after each window-closure patch to convert the
closed (normalized) windows to raw:

```
# 1. build pump with the CURRENT (now-stale-for-this-patch) ordered.ld, recording the map
#    (rust-lld -Map=link.map, as rebuild_measure.sh / the pump recipe already do)
# 2. rebind the selectors to the just-built symbols:
python3 tools/relayout.py \
    evidence/original/pump/deployed.so \
    <pump>-symbols.so \
    <pump>.map \
    --rebind-ld <current>/ordered.ld \
    -o <current>/ordered.ld.rebound \
    --report rebind_report.json
# 3. install ordered.ld.rebound, touch a source (defeat the build cache), rebuild + measure
```

Read `rebind_report.json`: `rebound` is how many closed windows were pulled back into
their deployed slots; `unresolved_stale` are selectors whose function was deleted/
renamed (left inert — inspect if a closed window is missing); `unplaced_orphans`
should be only SHF_MERGE `.cst*` pools. Because pump is a PARTIAL reconstruction
(unmatched sections exist), relayout will NOT recover windows whose call drift comes
from *unmatched* sections it cannot move (that remains T3 wrapper reconstruction) — but
every window that is normalized-complete and merely sent to the tail by a stale
selector is recovered mechanically, which is exactly the yield each new closed window
produces. Run it after every window Shuai-Qing closes.

Pre-reqs on the box: `tools/relayout.py` imports `tools/drift_solver.py` (both in
`~/tools/` on the worker); `data_layout.py` / `drift_solver.py` are the residual-class
checks to run after each measure.

---

## Honest scope notes

- The tool rebinds **hash-churned** selectors (demangled base stable) — the pump
  window-closure case. A fully-**renamed** function (base changed) has no reliable
  deployed slot to infer from these inputs alone and is reported as `unresolved_stale`
  for human review rather than guessed.
- Data-family (`.rodata` / `.data.rel.ro`) rebind uses name-base identity only; a
  deployed-order data-record content matcher (the `gen_ordered2.py` lddw-pointer
  correspondence) is the next step if a future patch ever makes a data selector stale.
  For Fees the data layer is clean (0 stale) so the families stay byte-identical.
- Measured on the isolated Fees worker; numbers are reproduced from
  `rebuild_measure.sh` + `drift_solver.py` + `data_layout.py`, not asserted.
