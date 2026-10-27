"""Measure a Fees symbols.so against deployed using lalalune window_map (MIT).
Requires a local checkout of lalalune/pumpfun-source with:
  research/fees-composed-frontier188/{window_map.py,elf_helpers.py}
  scripts/analyze.py
  evidence/original/pump_fees/deployed.so
Usage: PUMPFUN_SOURCE=/path/to/pumpfun-source python3 tools/measure_local.py <symbols.so>
"""
import os, sys, json, importlib.util
from pathlib import Path
from functools import lru_cache
ROOT = Path(os.environ["PUMPFUN_SOURCE"]).resolve()
spec = importlib.util.spec_from_file_location("wm", ROOT/"research/fees-composed-frontier188/window_map.py")
w = importlib.util.module_from_spec(spec); spec.loader.exec_module(w)
w.m.elf_layout = lru_cache(maxsize=8)(w.m.elf_layout); w.m.relocations = lru_cache(maxsize=8)(w.m.relocations)
original = (ROOT/"evidence/original/pump_fees/deployed.so").read_bytes()
image = Path(sys.argv[1]).read_bytes()
ow = w.windows(original); oi = {x["address"]: x for x in ow}
cw = w.windows(image)
sigs, raw = {x["signature"] for x in cw}, {x["raw_sha256"] for x in cw}
covered = sorted(x["address"] for x in ow if x["signature"] in sigs)
rawc = sorted(x["address"] for x in ow if x["raw_sha256"] in raw)
unmatched = sorted(x["address"] for x in ow if x["signature"] not in sigs)
print(json.dumps({"total": len(ow), "matched": len(covered), "raw": len(rawc),
                  "unmatched": [[a, oi[a]["bytes"]] for a in unmatched],
                  "matched_set": covered, "raw_set": rawc}))
