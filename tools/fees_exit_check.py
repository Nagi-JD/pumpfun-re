#!/usr/bin/env python3
"""Check that per-function exit counts sum to the program total; list uncovered exits."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fees_prog import load  # noqa: E402

p = load(sys.argv[1])
tot = sum(1 for i in p.ins.values() if i.op == 0x95)
seen = set()
for st in p.starts:
    for i in p.func_body(st):
        seen.add(i.pc)
missing = [pc for pc, i in p.ins.items() if i.op == 0x95 and pc not in seen]
print(f'exits total={tot} covered by function bodies={tot - len(missing)} missing={len(missing)}')
for pc in sorted(missing):
    print(f'  exit @ insn {pc:#x} byte {pc*8:#x} outside every detected function body')
print(f'functions={len(p.starts)} base={p.base:#x} last_insn={max(p.order):#x}')
