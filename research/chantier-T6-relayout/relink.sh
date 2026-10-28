#!/bin/bash
# relink.sh LINKDIR ORDERED_LD LABEL
# Re-link the cached input objects recorded in LINKDIR/linker-invocation.json
# with a different linker script. Identical objects -> pure layout delta.
set -e
LINKDIR="$1"; ORD="$2"; L="$3"
R2=/home/nagi/t6work; R=/home/nagi/pumpround34
P=$HOME/.cache/solana/v1.44/platform-tools
DEP=/home/nagi/pumpre/repo/evidence/original/pump/deployed.so
mkdir -p "$R2/out" "$R2/relink-$L"
OUT="$R2/out/$L-symbols.so"
MAP="$R2/relink-$L/link.map"
python3 "$R2/dorelink.py" "$LINKDIR/linker-invocation.json" "$ORD" "$OUT" "$MAP"
"$P/llvm/bin/llvm-objcopy" --strip-all "$OUT" "$R2/out/$L-candidate.so"
echo -n "SHA "; sha256sum "$R2/out/$L-candidate.so" | cut -d' ' -f1
python3 "$R/metric/measure.py" "$DEP" "$R2/out/$L-candidate.so" "$OUT" --dump "$R2/out/$L-m.json" | tail -1
