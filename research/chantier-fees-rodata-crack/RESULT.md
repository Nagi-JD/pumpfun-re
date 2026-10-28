# Fees `.rodata` layout crack on the window-complete (585/585) build

End-to-end measurement of the `.rodata` layout layer on the Fees window-complete
program, continuing from the `.text` + `.data.rel.ro` plateau of
`research/chantier-fees-layout-wholeelf` (raw 403/585). Every number below is
from a real Anza platform-tools v1.44 build + v1.52 `llvm-objcopy` strip,
measured with the shipped window metric.

**Bottom line.** Deployed-order `.rodata`, folded onto the accepted
`.text` + `.data.rel.ro` skeleton, lifts raw **403 → 585 / 585**.
`matched_normalized` stays 585; `unmatched_original` stays `[]`. The stripped
candidate is byte-identical to the deployed meaningful ELF
(`sha256 5b6ceda5…b3dcf`).

---

## Ladder (same source, layout only)

| layout | symbols sha256 (12) | stripped sha256 (12) | matched | raw |
|---|---|---|---:|---:|
| default catch-alls | `e9f6fde23c37` | `1c07f6c58603` | 585 | **253** |
| deployed-order `.text` | `ad6ff4adc837` | `31e46d90e939` | 585 | **393** |
| `.text` + `.data.rel.ro` (prior plateau) | `3e20ec0d5869` | `8fb0a24d372d` | 585 | **403** |
| + deployed-order `.rodata` | `7ec99a6915bc` | `5b6ceda57863` | 585 | **585** |

The 403-row symbols sha matches the prior packet's best build
(`3e20ec0d…04695`). The 585-row stripped sha matches the deployed meaningful ELF.

Measure receipts: `V_default-m.json`, `V_textonly-m.json`,
`V_norodata-m.json`, `U585b-m.json`.

---

## `tools/data_layout.py` on the 403 plateau

```
python3 tools/data_layout.py DEPLOYED.so V_norodata-symbols.so \
  --cand-stripped V_norodata-candidate.so -o dl_403.json
```

Summary (from `dl_403.json`):

| field | value |
|---|---:|
| matched | 585 |
| exact (raw) | 403 |
| data_aligned | 0 |
| data_residual | 182 |
| other | 0 |
| lddw_sites | 1079 |
| lddw_sites_aligned | 0 |
| `lddw_sites` class | `.rodata:unaligned` × 1079 |
| `rodata_order.runs` / `shift_runs` | 64 |
| `.text` / `.rodata` / `.data.rel.ro` base_delta | 0 / 0 / 0 |
| section size_delta | 0 / 0 / 0 |

Section bases and sizes already match deployed at the 403 plateau. Every raw
miss is an `lddw` whose immediate points into `.rodata` at the wrong
intra-offset. `data_layout.py` reports the shift-run boundaries; closing them
is a selector-order problem inside `.rodata`.

---

## Closing `.rodata`

Selectors for `.rodata` follow the deployed input-section order (per-object
`*obj("section")` lines, with plain `*(".rodata.cstN")` for SHF_MERGE pools).
The skeleton keeps the accepted `.text` and `.data.rel.ro` selectors from the
403 plateau. Relink (touch a source file so cargo re-runs the linker; `ordered.ld`
is outside cargo's input tracking):

| | value |
|---|---|
| raw before | 403 |
| raw after | **585** |
| `lost_matched` | `[]` |
| `lost_raw` | `[]` |
| `matched_normalized` | 585 (unchanged) |
| stripped sha256 | `5b6ceda57863f0dcc3e0e3623052f8342c2c81883379699e71d7ed5383cb3dcf` |

Scripts in this packet:

- `ordered.text-datarelro.ld` - 403 plateau (`.text` + `.data.rel.ro`)
- `ordered.full.ld` - full deployed-order (`.text` + `.rodata` + `.data.rel.ro`) → 585

Both are build-specific (CGU hash `85ade9ce1584ca93`). Rebuild with the same
window-complete source and the same `-C metadata` / vendor path so the selectors
bind.

---

## Files

| path | role |
|---|---|
| `RESULT.md` | this write-up |
| `ordered.text-datarelro.ld` | 403-raw layout |
| `ordered.full.ld` | 585-raw layout |
| `V_default-m.json` | measure @ default |
| `V_textonly-m.json` | measure @ `.text` only |
| `V_norodata-m.json` | measure @ 403 plateau |
| `U585b-m.json` | measure @ full order |
| `dl_403.json` | `data_layout.py` receipt on the 403 build |
| `shas.txt` | symbols + stripped digests for each step |

No `.so` is committed.

## Attribution

Layout technique and window metric: [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT).
Prior Fees layout packet: `research/chantier-fees-layout-wholeelf`.
`tools/data_layout.py` on `master`.
