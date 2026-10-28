# chantier T6-apply — relayout.py raw yield on the canonical pump profile (MEASURED)

**Goal.** Apply the merged T6 tool `tools/relayout.py` to the canonical pump
profile and measure its *real* raw yield: how many normalized-matched-but-raw-fail
windows it converts to raw-exact by relocating them to their deployed `.text`
slots. This is the push to regain raw (lalalune leads 203 vs 161).

**Bottom line (measured, not asserted): relayout recovers `0` raw on pump.
161 → 161. Zero windows converted. The raw gaters are structurally outside
relayout's reach (unmatched spoilers it cannot move, plus duplicate-stub
ambiguity); they need T3 wrapper reconstruction and T5 data layout.**

Scope discipline: canonical `s7` (`/home/nagi/pumpround34/s7`) was never modified.
All work ran from an isolated copy (`/home/nagi/t6apply/s7copy`) with its own
target/out/link dirs. No other agent's dir was written. No `.so` committed.

---

## Baseline reproduction

The canonical frontier is **802 / 161 / 1035** (merged chain #22–#32, culminating
in `chantier-T4-close-burn-helpers`). The exact reference artifact was found
on-disk at `/home/nagi/pumpround34/target/sbf-solana-solana/release/pump_recovered.so`
and MEASURED:

| artifact | matched | raw(exact) | orig windows | symbols sha256 | candidate sha256 |
|---|---|---|---|---|---|
| on-disk reference | **802** | **161** | 1035 | `08f489f2…1381d2fa` | `c964dbd9…0878bf68` |

Independent from-source rebuild (hermetic recipe: darwin rustc shim +
`pump_text_layout_rustc.py` + cumulative `ordered.ld` + platform-tools v1.44,
`--locked --offline`, `-Zremap-cwd-prefix= -C passes=mergefunc`, logical registry),
own target dir:

| build | matched | raw(exact) | call_only_raw_fail | potential_if_delta0 | intervals_nonzero | candidate_windows |
|---|---|---|---|---|---|---|
| my s7copy + full T4 patch chain | **798** | **161** | **205** | **366** | 87 | 1008 |
| reference close-burn (recipe) | 802 | 161 | 205 | 366 | 88 | 1012 |

The raw frontier is reproduced **exactly** (raw=161 — NOT a 127/137 build-path
artifact → build paths correct; `call_only_raw_fail=205` and
`potential_if_delta0=366` identical to the reference). The 4-window `matched`
gap (798 vs 802) is in **matched-but-not-raw** windows (candidate_windows 1008
vs 1012: 4 migrate/close/burn helper sections that differ because
`/home/nagi/pumpround34/s7` is a live shared workspace that drifted after the
10:50 reference build). It is **outside the relocation pool** and does not affect
the raw measurement.

### Correctness gates (both PASS, byte-identical, `lost[] = []`)

- relink with the as-built `ordered.ld`:            `matched 798→798 raw 161→161 +[] −[]`
- relink with `relayout` **regenerated** `ordered.ld` (preserve, 1008 selectors,
  797 content-matched): `matched 798→798 raw 161→161 +[] −[]`

relayout's `link.map` parse, selector reconstruction, and content binding are
correct on this build.

---

## The relocation experiment

Relocation candidates = the `call_only_raw_fail` windows (body + data already
match; only a relative-call `imm32` is off — lddw/0x18 residual windows are
excluded by construction of `call_only_diff`).

| pool | count |
|---|---|
| call-only raw-fail (relayout class) | **205** |
| — unambiguous (unique `(size, normalized_sha256)` on BOTH sides) | 112 |
| — ambiguous duplicate-stub (cannot disambiguate which copy owns which slot) | **93** |
| matched-but-raw-fail that are NON-call-only (lddw/data → **T5**, not relayout) | 432 |

### Individual relocation sweep over all 112 unambiguous candidates

Each candidate relocated alone (`relayout --to-deployed <section>`), relinked,
measured vs the 161-raw baseline:

| outcome | count |
|---|---|
| **winner** (raw↑ AND `lost[] = []`) | **0** |
| pure no-op (Δ0, no loss) | 59 |
| regress (broke 1–23 currently-raw windows) | 53 |
| gain-but-also-lost | 0 |

### Bulk relocation of all 112 unambiguous (one relink)

`raw 161 → 115  +[]  −[46 windows]` — regresses, as the T6 RESULT predicted for a
global sort (reverted, not kept).

---

## Why relayout cannot gain raw here (mechanism)

1. **relayout only moves content-matched sections.** The call drift on these 205
   windows is produced by **unmatched** sections — candidate-only helpers that do
   not exist in deployed, and deployed-only windows not yet reconstructed —
   lying between a matched caller and its matched callee. relayout cannot move
   the unmatched spoilers, so it cannot zero the crossed deltas.
2. **The backbone already equals deployed content-order** for the movable
   windows → relocating one is a no-op (59/112).
3. **Any move that does change position shifts every subsequent address**, breaking
   already-raw tail windows (53/112 regress; bulk −46). There is no "free" move
   that zeroes a call delta without displacing a raw window.
4. **93/205 are duplicate-normalized stubs** (dup-multiplicity up to 13): content
   pairing cannot say which copy owns which slot, so they are unmovable by
   construction.

relayout's value is what its own RESULT claimed — a complete, live, idempotent
`ordered.ld` (maintenance across source edits) — **not** raw recovery on an
already-good pump build.

## Honest relayout raw ceiling on pump

**0 of 205.** Decomposition of the 205 call-only raw-fail windows:
- **93** blocked by duplicate-stub ambiguity (unmovable).
- **112** unambiguous but **0** relayout-recoverable (every single move is a
  no-op or breaks a raw window; drift source is unmatched sections relayout
  cannot touch).
- plus **432** matched-but-raw-fail windows are non-call-only (lddw/data) → **T5
  data layout**, never relayout.

To regain raw toward lalalune's 203, the path is **T3** (reconstruct the Anchor
wrapper / helper windows so the unmatched candidate-only and deployed-only
sections disappear) and **T5** (data layout for the 432 lddw/data residuals) —
not layout reordering.

## Reproduction

```
# materialize isolated 802/161-class workspace (canonical s7 untouched)
cp -r /home/nagi/pumpround34/s7 /home/nagi/t6apply/s7copy
cd /home/nagi/t6apply/s7copy
for p in with-account-name whitelist-resync shareholder-copy pk7-borsh-serialize \
         pk8-setparams-serialize transfer-with-seed harvest-withheld refund-seeds \
         close-burn-helpers; do
  patch -p1 < research/chantier-T4-$p/source.patch
done
# cumulative ordered.ld = round34 base + the 8 non-empty ordered-ld patches
# build (hermetic): build.sh base ordered.ld   -> 798/161 (raw frontier = reference)
# gates + sweep:
python3 tools/relayout.py DEP base-symbols.so link-base/link.map \
        --cand-stripped base-candidate.so -o ordered_regen.ld   # idempotent
python3 sweep.py pat_all.txt sweep_all.json    # 112 unambiguous, 0 winners
```

Evidence JSONs in this packet: `drift-base.json`, `candidates.json`,
`sweep_all.json`, `report_all112.json`, `regen-report.json`.
