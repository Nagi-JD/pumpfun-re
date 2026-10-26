#!/usr/bin/env python3
"""Emit the pump_fees Location tables (per file, per function) for the report."""
import json
import os
import sys
from collections import defaultdict

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from fees_prog import load  # noqa: E402
from fees_locations import build, short  # noqa: E402

SO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(ROOT), 'pumpfun-source', 'evidence', 'original', 'pump_fees', 'deployed.so')
p = load(SO)
recs, strings = build(p)
refs = defaultdict(list)
for pc in getattr(p, 'data_ptr', {}):
    ins = p.ins.get(pc)
    if ins and ins.op == 0x18 and (ins.imm & 0xffffffff) in recs:
        refs[p.func_of.get(pc, p.base)].append((pc, ins.imm & 0xffffffff))

prog = {va: r for va, r in recs.items() if r['file'].startswith('programs/pump-fees/src/')}
print(f'# records total={len(recs)} program={len(prog)} dependency={len(recs) - len(prog)}')

print('\n## per-file table\n')
rows = defaultdict(list)
for va, r in prog.items():
    rows[short(r['file'], 1)].append((r['line'], r['col'], va))
print('| source file (under `programs/pump-fees/src/`) | panic sites | line:col | first record VA |')
print('|---|---|---|---|')
for f in sorted(rows):
    pts = sorted(rows[f])
    print(f'| `{f}` | {len(pts)} | ' + ', '.join(f'{l}:{c}' for l, c, _ in pts)
          + f' | `{min(v for _, _, v in pts):#x}` |')

print('\n## function table (program files only)\n')
print('| function insn | function byte | size (insns) | file:line:col referenced |')
print('|---|---|---|---|')
for st in p.starts:
    if st not in refs:
        continue
    sites = sorted({(recs[va]['file'], recs[va]['line'], recs[va]['col'])
                    for _, va in refs[st] if va in prog})
    if not sites:
        continue
    print(f'| `{st:#06x}` | `{st*8:#08x}` | {len(p.func_body(st))} | '
          + ', '.join(f'`{short(f, 1)}` {l}:{c}' for f, l, c in sites) + ' |')

print('\n## paths with no Location record\n')
allp = sorted({s.decode('latin1') for s in [p.b[0:0]]})  # placeholder
import re
paths = sorted({m.group(0) for m in re.finditer(
    rb'programs/pump-fees/src/[A-Za-z0-9_/]+\.rs', p.b)})
have = {r['file'] for r in recs.values()}
for x in paths:
    s = x.decode()
    if s not in have:
        print(f'- `{s}`')
