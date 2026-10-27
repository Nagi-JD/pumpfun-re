"""Compute the fees-sharing-slice-recovery verify.py metrics for an arbitrary symbol-bearing candidate.
Logic copied from research/fees-sharing-slice-recovery/verify.py (lalalune/pumpfun-source, MIT)."""
import sys, json, struct, importlib.util
from pathlib import Path
from functools import lru_cache
ROOT = Path("/home/nagi/pumpre/repo")
spec = importlib.util.spec_from_file_location("wm", ROOT/"research/fees-composed-frontier188/window_map.py")
w = importlib.util.module_from_spec(spec); spec.loader.exec_module(w)
w.m.elf_layout = lru_cache(maxsize=8)(w.m.elf_layout); w.m.relocations = lru_cache(maxsize=8)(w.m.relocations)
def location(image, target):
    assert dict(w.m.relocations(image)).get(target, 0) & 0xffffffff == 8
    low, ptr, n, line, column = struct.unpack("<IIQII", w.m.at_address(image, target, 24))
    assert low == 0 and 0 < n <= 300 and 0 < line <= 100000 and 0 < column <= 300
    name = w.m.at_address(image, ptr, n); assert name.endswith(b".rs") and all(32 <= c < 127 for c in name)
    return name.decode(), line, column
original = (ROOT/"evidence/original/pump_fees/deployed.so").read_bytes()
image = Path(sys.argv[1]).read_bytes()
ow = w.windows(original); oi = {x["address"]: x for x in ow}; rel = dict(w.m.relocations(original))
cw = w.windows(image); ci = {x["address"]: x for x in cw}
result = w.compare(ow, cw)
sigs, raw = {x["signature"] for x in cw}, {x["raw_sha256"] for x in cw}
covered = sorted(x["address"] for x in ow if x["signature"] in sigs)
rawc = sorted(x["address"] for x in ow if x["raw_sha256"] in raw)
edges, locs, badloc = {}, 0, []
for pair in result["unique_pairs"]:
    a, b = pair["original"], pair["candidate"]
    for x, y in zip(w.m.instructions(original, a["address"], a["bytes"]), w.m.instructions(image, b["address"], b["bytes"])):
        kind = rel.get(a["address"] + x["offset"], 0) & 0xffffffff
        if kind == 8:
            try: left = location(original, x["lddw_value"])
            except (AssertionError, ValueError, StopIteration, struct.error): continue
            try: right = location(image, y["lddw_value"])
            except Exception: right = None
            if left == right: locs += 1
            else: badloc.append((a["address"], x["offset"], left, right))
        if "call_target" in x and kind != 10:
            edges[a["address"], x["offset"]] = oi[x["call_target"]]["signature"] == ci[y["call_target"]]["signature"]
unmatched = sorted(x["address"] for x in ow if x["signature"] not in sigs)
out = {"total": len(ow), "matched": len(covered), "raw": len(rawc), "unique_pairs": len(result["unique_pairs"]),
       "equal_locations": locs, "unequal_locations": len(badloc), "equal_edges": sum(edges.values()),
       "unequal_edges": sorted([list(k) + [oi_t] for k, v in edges.items() if not v for oi_t in [None]]),
       "unmatched": [[a, oi[a]["bytes"]] for a in unmatched], "matched_set": covered, "raw_set": rawc}
print(json.dumps(out))
