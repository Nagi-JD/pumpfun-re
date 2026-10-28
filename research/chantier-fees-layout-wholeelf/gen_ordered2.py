#!/usr/bin/env python3
"""gen_ordered2.py - whole-ELF layout: deployed-order .text + .rodata + .data.rel.ro.

.text   : deployed window order (content-identity signature pairing).
rodata/ : deployed order derived from the lddw pointer correspondence in the
.data.rel.ro  paired .text windows (cand ptr target -> deployed ptr target),
          which maps each data section's candidate base to its deployed base.
Unpaired sections keep their physical neighbourhood.

Usage: gen_ordered2.py DEPLOYED.so SYMBOLS.so LINK.map DEFAULT_LD OUT.ld
"""
import importlib.util, json, re, sys, collections

WM = "/home/Saturn/feesr34/research/fees-composed-frontier188/window_map.py"
spec = importlib.util.spec_from_file_location("window_map", WM)
wm = importlib.util.module_from_spec(spec); spec.loader.exec_module(wm)
EH = "/home/Saturn/feesr34/research/fees-composed-frontier188/elf_helpers.py"
espec = importlib.util.spec_from_file_location("eh", EH)
eh = importlib.util.module_from_spec(espec); espec.loader.exec_module(eh)

dep_path, sym_path, mapf, default_ld, out_ld = sys.argv[1:6]
depb = open(dep_path, 'rb').read(); symb = open(sym_path, 'rb').read()

D = wm.windows(depb); C = wm.windows(symb)

# --- .text content pairing (cand addr -> dep addr) ---
da = collections.defaultdict(list); ca = collections.defaultdict(list)
for r in D: da[r['signature']].append(r)
for r in C: ca[r['signature']].append(r)
cand_to_dep = {}
pairs = []
for sig in (da.keys() & ca.keys()):
    if len(da[sig]) == 1 and len(ca[sig]) == 1:
        cand_to_dep[ca[sig][0]['address']] = da[sig][0]['address']
        pairs.append((ca[sig][0], da[sig][0]))

# --- lddw pointer correspondence: cand ptr target -> dep ptr target ---
def lddw_ptrs(image, win):
    """return list of (offset, value) for opaque_relocated_pointer annotations"""
    addr = win['address']; size = win['bytes']
    raw = eh.at_address(image, addr, size)
    out = []
    for a in win['annotations']:
        if len(a) >= 2 and a[1] == 'opaque_relocated_pointer':
            off = a[0]
            lo = int.from_bytes(raw[off+4:off+8], 'little')
            hi = int.from_bytes(raw[off+12:off+16], 'little')
            out.append((off, lo | (hi << 32)))
    return out

ptr_map = {}   # cand_target_addr -> dep_target_addr
for c, o in pairs:
    cp = lddw_ptrs(symb, c); op = lddw_ptrs(depb, o)
    if len(cp) != len(op):
        continue
    for (coff, cval), (ooff, oval) in zip(cp, op):
        if coff == ooff:
            ptr_map.setdefault(cval, set()).add(oval)
# keep only unambiguous correspondences
ptr_map = {k: next(iter(v)) for k, v in ptr_map.items() if len(v) == 1}

# --- parse link.map sections by output section family ---
_SEC = re.compile(r"^(?P<obj>.+):\((?P<sec>(?P<fam>\.text|\.rodata|\.data\.rel\.ro)(?:\.[^)]*)?)\)$")
_RLIB = re.compile(r".*/(?P<rlib>[^/]+\.rlib)\((?P<mem>[^)]+)\)$")
def tok(o):
    m = _RLIB.match(o)
    return f"{m.group('rlib')}:{m.group('mem')}" if m else o.rsplit("/", 1)[-1]

fam_sections = {'.text': [], '.rodata': [], '.data.rel.ro': []}
for line in open(mapf, errors="replace").read().splitlines():
    t = line.split()
    if len(t) < 5 or ":(" not in t[4]:
        continue
    m = _SEC.match(t[4])
    if not m:
        continue
    try:
        vma = int(t[0], 16); size = int(t[2], 16)
    except ValueError:
        continue
    fam = m.group('fam')
    sec = m.group('sec')
    # SHF_MERGE constant pools (.rodata.cstN) cannot take per-object selectors
    # (lld merges them); leave them to the catch-all.
    if '.cst' in sec:
        continue
    sel = f'    *{tok(m.group("obj"))}("{sec}")'
    fam_sections[fam].append({"vma": vma, "size": size, "sec": sec, "sel": sel})

def dep_of_text(vma):
    return cand_to_dep.get(vma)

def dep_of_data(vma, size):
    # find a mapped pointer that lands inside [vma, vma+size); deployed base =
    # dep_target - (cand_target - vma); require all consistent, take min offset
    best = None
    for cval, oval in ptr_map.items():
        if vma <= cval < vma + size:
            base = oval - (cval - vma)
            if best is None or (cval - vma) < best[0]:
                best = (cval - vma, base)
    return best[1] if best else None

def order_family(fam):
    nodes = fam_sections[fam]
    for n in nodes:
        n['dep'] = dep_of_text(n['vma']) if fam == '.text' else dep_of_data(n['vma'], n['size'])
    key = [0.0]*len(nodes); last = -1.0; run = 0
    for i, n in enumerate(nodes):
        if n['dep'] is not None:
            key[i] = float(n['dep']); last = float(n['dep']); run = 0
        else:
            run += 1; key[i] = last + 1e-6*run
    order = sorted(range(len(nodes)), key=lambda i: (key[i], i))
    seen = set(); sels = []
    for i in order:
        if nodes[i]['sel'] in seen: continue
        seen.add(nodes[i]['sel']); sels.append(nodes[i]['sel'])
    paired = sum(1 for n in nodes if n['dep'] is not None)
    return sels, len(nodes), paired

default_text = open(default_ld).read()
stats = {}
for fam, phdr in [('.text', ':text'), ('.rodata', ':rodata'), ('.data.rel.ro', ':rodata')]:
    sels, tot, paired = order_family(fam)
    stats[fam] = dict(total=tot, paired=paired)
    rule = f"  {fam} : {{ *({fam}*) }} {phdr}"
    assert default_text.count(rule) == 1, f"rule not found: {rule}"
    head, tail = default_text.split(rule)
    body = "\n".join(sels)
    default_text = head + f"  {fam} : {{\n" + body + f"\n    *({fam}*)\n  }} {phdr}" + tail

open(out_ld, "w").write(default_text)
stats['ptr_correspondences'] = len(ptr_map)
sys.stderr.write(json.dumps(stats) + "\n")
