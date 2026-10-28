# chantier-mayhem-sweeps — close 3 Mayhem windows (432 → 435)

Reconstructs the Anchor source for three unmatched Mayhem windows (the fee-sweep /
validate-sweep family) so the generated `.text` normalizes to the deployed
program byte-for-byte.

- **Deployed image:** `evidence/original/mayhem/deployed.so`
  SHA256 `a87fa9f866272514e6acb852b668c4a08aeb173d56c883039991d114d1199bdb`
- **Metric:** `window_map.py` normalized-signature window match
  (`research/fees-composed-frontier188/window_map.py`), run by `maymeasure.py`.
- **Mayhem build env:** `mayhem-fg` (`maybuild_fg.sh`, `LDMODE=glob`), candidate
  crate `mayhem-recovered` (= the `src432` reconstruction tree).

## Measured result (real build, not claimed)

| | matched | raw | unmatched |
|---|---:|---:|---|
| base (`src432`) | 432 | 82 | 9 windows |
| **this packet**  | **435** | **82** | 6 windows |

**Δ matched = +3. lost[] = [] on both sets (raw unchanged at 82).**

Windows closed (deployed vaddr → instruction):

| deployed vaddr | bytes | instruction (candidate symbol) |
|---:|---:|---|
| 65472  (0xffc0)  | 912  | `FeeRecipient::validate_sweep` |
| 69192  (0x10e48) | 8008 | `sweep_fees_admin` |
| 77200  (0x12d90) | 8400 | `sweep_fees` |

## Source change (`source.patch`, 2 files)

- **`src/instructions/fee_recipients.rs`** — the sweep logic is reconstructed as
  `impl SweepFees::sweep` / `impl SweepFeesAdmin::sweep` plus the `sweepable`
  helper and top-level `sweep_fees` / `sweep_fees_admin` entrypoints; `SweepEvent`
  moves here. `validate_sweep` takes the `let flag=&native;` indirection and hoists
  `interval` inside the rate-limit branch — the forms that reproduce the deployed
  branch triangle and the quote-first store order.
- **`src/lib.rs`** — `sweep_fees` / `sweep_fees_admin` route to the new
  `instructions::fee_recipients::*`; the old inline `SweepEvent` + `sweep_remaining`
  are removed.

No ELF bytes are patched; this is ordinary Rust whose compiled normalized windows
equal the deployed ones. The three windows were already mapped to their
instructions by prior dispatch-stub analysis.

## Reproduce

```
# build the candidate tree (src432 + this patch) and measure
LDMODE=glob TD=mayhem-fg/target-repro bash mayhem-fg/maybuild_fg.sh sweeps <SRC>
python3 mayhem-fg/tools/maymeasure.py mayhem-fg/out/sweeps-symbols.so
# -> {"matched":435,"raw":82,"unmatched":[6 trade windows]}
```

## Attribution

The source forms are ported from upstream public MIT research
(`lalalune/pumpfun-source`, packet `research/claude-mayhem-441-20261028/`,
`sources/source.tar.gz`) and independently verified here by a real build +
measurement on the Nagi Mayhem env against the `src432` base. Credit: lalalune
Mayhem lanes.
