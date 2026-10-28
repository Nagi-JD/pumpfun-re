#!/bin/bash
# Rebind lalalune deployed-order seed to OUR symbols, relink, measure raw.
set -e
O=/home/nagi/ammlayout
T=$O/tools
DEP=/home/nagi/pumpre/repo/evidence/original/pump_amm/deployed.so
DEF=/home/nagi/pumpround34/scripts/pump_text_layout_default.ld
SYM=$O/amm_seed-symbols.so
MAP=$O/link/link.map
INV=$O/link/linker-invocation.json
echo "=== inputs present? ==="
ls -la "$SYM" "$MAP" "$INV" 2>&1
echo "=== rebind ==="
cd "$T"
python3 "$T/relayout.py" "$DEP" "$SYM" "$MAP" \
  --rebind-ld "$O/seed_text_only.ld" \
  --default-ld "$DEF" \
  -o "$O/ordered_rebound.ld" \
  --report "$O/rebind_report.json" 2>&1 | tail -20
echo "=== rebind report ==="
python3 -c "import json;d=json.load(open('$O/rebind_report.json'));print({k:d[k] for k in list(d)[:25]})" 2>&1 | head
echo "=== relink with rebound ordered.ld ==="
python3 /home/nagi/t6work/dorelink.py "$INV" "$O/ordered_rebound.ld" "$O/relinked-symbols.so" "$O/relinked.map"
echo "relink rc=$?"
echo "=== measure relinked ==="
python3 /home/nagi/ammresearch/tools/measure.py "$O/relinked-symbols.so" > "$O/relinked.json" 2>"$O/relinked.err"
if [ -s "$O/relinked.err" ]; then echo "measure err:"; tail -5 "$O/relinked.err"; fi
python3 -c "import json;d=json.load(open('$O/relinked.json'));print('RELINKED matched',d['matched'],'raw',d['raw'],'unmatched',len(d['unmatched']))"
echo "=== lost vs clean 701 baseline ==="
python3 /home/nagi/chantier-matched/lost.py /home/nagi/chantier-matched/out/btree_clean.json "$O/relinked.json"
