#!/usr/bin/env python3
"""gen_ordered.py - fees-native whole-ELF .text layout generator.

Places candidate .text input sections in DEPLOYED window order, binding by
content identity (fees window_map signature, the same metric used to MEASURE).
Unpaired sections keep their physical neighbourhood (relayout binding model 2).

Usage:
  gen_ordered.py DEPLOYED.so SYMBOLS.so LINK.map DEFAULT_LD OUT.ld
Prints a JSON stats line to stderr.
"""
import importlib.util, json, re, sys, collections

WM = "/home/Saturn/feesr34/research/fees-composed-frontier188/window_map.py"
spec = importlib.util.spec_from_file_location("window_map", WM)
wm = importlib.util.module_from_spec(spec); spec.loader.exec_module(wm)

dep_path, sym_path, mapf, default_ld, out_ld = sys.argv[1:6]

D = wm.windows(open(dep_path, 'rb').read())
C = wm.windows(open(sym_path, 'rb').read())

# unique-signature content pairing: candidate .text addr -> deployed .text addr
da = collections.defaultdict(list); ca = collections.defaultdict(list)
for r in D: da[r['signature']].append(r)
for r in C: ca[r['signature']].append(r)
cand_to_dep = {}
for sig in (da.keys() & ca.keys()):
    if len(da[sig]) == 1 and len(ca[sig]) == 1:
        cand_to_dep[ca[sig][0]['address']] = da[sig][0]['address']

# parse link.map .text sections in physical order
_SEC = re.compile(r"^(?P<obj>.+):\((?P<sec>\.text(?:\.[^)]*)?)\)$")
_RLIB = re.compile(r".*/(?P<rlib>[^/]+\.rlib)\((?P<mem>[^)]+)\)$")
def selector_token(objpath):
    m = _RLIB.match(objpath)
    if m: return f"{m.group('rlib')}:{m.group('mem')}"
    return objpath.rsplit("/", 1)[-1]

sections = []  # (vma, size, sec, selector)
for line in open(mapf, errors="replace").read().splitlines():
    toks = line.split()
    if len(toks) < 5 or ":(.text" not in toks[4]:
        continue
    m = _SEC.match(toks[4])
    if not m: continue
    try:
        vma = int(toks[0], 16); size = int(toks[2], 16)
    except ValueError:
        continue
    sel = f'    *{selector_token(m.group("obj"))}("{m.group("sec")}")'
    sections.append((vma, size, m.group("sec"), sel))

# assign each section its deployed addr (if the window at its vma pairs uniquely)
nodes = []
for vma, size, sec, sel in sections:
    nodes.append({"vma": vma, "size": size, "sec": sec, "sel": sel,
                  "dep": cand_to_dep.get(vma)})

paired = sum(1 for n in nodes if n["dep"] is not None)

# sort key: paired -> deployed addr; unpaired -> interpolate from nearest
# preceding paired section in physical order (keep neighbourhood). Ties broken
# by physical index so unpaired sections stay right after their phys predecessor.
key = [0.0] * len(nodes)
last_dep = -1.0
run = 0
for i, n in enumerate(nodes):
    if n["dep"] is not None:
        key[i] = float(n["dep"]); last_dep = float(n["dep"]); run = 0
    else:
        run += 1
        # place just after last paired deployed slot, preserving phys order
        key[i] = last_dep + 1e-6 * run
order = sorted(range(len(nodes)), key=lambda i: (key[i], i))

# emit selectors (dedup, first occurrence wins)
seen = set(); selectors = []
for i in order:
    s = nodes[i]["sel"]
    if s in seen: continue
    seen.add(s); selectors.append(s)

default_text = open(default_ld).read()
rule = "  .text : { *(.text*) } :text"
assert default_text.count(rule) == 1, "default.ld .text rule not found"
head, tail = default_text.split(rule)
body = "\n".join(selectors)
script = head + "  .text : {\n" + body + "\n    *(.text*)\n  } :text" + tail
open(out_ld, "w").write(script)

sys.stderr.write(json.dumps(dict(
    deployed_windows=len(D), candidate_windows=len(C),
    sections_total=len(nodes), paired=paired, unpaired=len(nodes) - paired,
    selectors_emitted=len(selectors))) + "\n")
