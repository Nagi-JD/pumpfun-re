#!/usr/bin/env python3
"""Is a function's address ever taken (so it can be called indirectly)?

Checks every R_BPF_64_RELATIVE lddw addend and every relocated data slot for the
given .text VAs, and prints the enclosing function of each reference.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fees_prog import load  # noqa: E402

p = load(sys.argv[1])
want = {int(a, 0) for a in sys.argv[2:]}
print(f'looking for taken addresses: {[hex(w) for w in sorted(want)]}')

hits = []
for pc in getattr(p, 'data_ptr', {}):
    ins = p.ins.get(pc)
    if not ins or ins.op != 0x18:
        continue
    for cand in (ins.imm & 0xffffffff, ins.imm >> 32):
        if cand in want:
            hits.append((pc, cand, 'text-lddw'))
print(f'text lddw references: {len(hits)}')
for pc, va, kind in hits:
    print(f'  {kind} @ insn {pc:#x} (fn {p.func_of.get(pc, p.base):#x}) -> {va:#x}')

# data slots hold the pointer in the high 32 bits on this ELF
drr = p.sec.get('.data.rel.ro')
n = 0
if drr:
    addr, off, size = drr[3], drr[4], drr[5]
    for o in range(0, size - 8, 8):
        v = struct.unpack_from('<Q', p.b, off + o)[0]
        for cand in (v & 0xffffffff, v >> 32):
            if cand in want:
                print(f'  .data.rel.ro slot {addr + o:#x} holds {cand:#x}')
                n += 1
print(f'.data.rel.ro slots holding a wanted VA: {n}')

# also: any internal call with that target is a direct reference
for w in sorted(want):
    t = w // 8
    c = [pc for pc, i in p.ins.items() if i.op == 0x85 and pc + 1 + i.imm == t]
    print(f'direct calls to {w:#x} (insn {t:#x}): {len(c)} ' + ' '.join(f'{x:#x}' for x in c))
