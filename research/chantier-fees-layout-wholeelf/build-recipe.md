# Build recipe — chantier-fees-layout-wholeelf

Run on the Fees byte-race worker. Anza platform-tools v1.44 build + strip v1.52
`llvm-objcopy`. Source: `/work/next649/extend-qualified`. Deployed:
`feesr34/evidence/original/pump_fees/deployed.so`. Metric:
`research/fees-composed-frontier188/window_map.py` via `~/measure_thin.py`
(invoked by `~/rebuild_measure.sh`, which prints `MEASURE:{json}`).

## 0. Window-complete parent (Step 1)

From the verified `extend-qualified` baseline (582/200), apply in lineage order
(these close windows 147944, 163920, 120816 respectively):

```
cd /work/next649/extend-qualified
patch -p1 < ~/crank_source.patch        # 147944  (merged on master: PR #48)
patch -p1 < ~/create_rs_only.patch      # 163920
patch -p1 < ~/sweep_source.patch        # 120816
bash ~/rebuild_measure.sh               # -> normalized 585, raw 288, unmatched []
```

## 1. Generate the deployed-order ordered.ld (layout layer)

Inputs: the window-complete `symbols.so`, its rust-lld `-Map` link map, the SDK
default linker script (captured by `linker.sh` to `/work/next649/sdk-default.ld`),
and the deployed `.so`.

```
# .text only  (-> raw 393)
python3 gen_ordered.py  deployed.so  symbols.so  link.map  sdk-default.ld  ordered.ld

# .text + .data.rel.ro  (BEST, -> raw 403)
python3 gen_ordered2.py deployed.so  symbols.so  link.map  sdk-default.ld  ordered.ld
```

`gen_ordered.py` bins candidate `.text` input sections to deployed window order
by content-identity signature pairing (the metric's own signature).
`gen_ordered2.py` additionally orders `.data.rel.ro` (and attempts `.rodata`) by
deriving each data section's deployed base from the `lddw` pointer correspondence
in the paired `.text` windows. SHF_MERGE `.rodata.cstN` pools are left to the
catch-all (per-object selectors on merge sections make the link fail).

## 2. Rebuild WITH A FORCED RELINK, then measure

`ordered.ld` is **not** a cargo build input — changing it alone will NOT relink.
Force it:

```
cp ordered.ld /work/next649/extend-qualified/ordered.ld
touch /work/next649/extend-qualified/programs/pump-fees/src/lib.rs   # MANDATORY
bash ~/rebuild_measure.sh
```

`linker.sh` intercepts the final `.so` link, saves the SDK script to
`sdk-default.ld`, and substitutes `extend-qualified/ordered.ld`.

## 3. Whole-ELF comparison

```
STRIP=~/.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objcopy
$STRIP --strip-all extend-qualified-symbols.so candidate.so
$STRIP --strip-all deployed.so                 deployed.stripped.so
sha256sum candidate.so deployed.stripped.so      # byte-identical iff whole-ELF
cmp -l candidate.so deployed.stripped.so | wc -l # residual byte count
```

Best measured: raw 403/585; stripped 873256 B both; 7783 bytes differ
(99.11 % identical); residual .rodata 5592 / .text 2102 / .data.rel.ro 89;
dynsym/reloc/headers byte-identical.

No `.so`, no secrets committed. `ordered.text-datarelro.ld` is the concrete best
script for this build (references this build's CGU hash).
