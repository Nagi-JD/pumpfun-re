#!/usr/bin/env python3
"""Resolve sBPF `callx` sites (op 0x8d) to their target addresses.

For each callx, scan backwards in the same function for the last write to the
register used as the call target. If it is an `lddw` carrying an R_BPF_64_RELATIVE
addend (low 32 bits), the target is that .text VA; report it. This decides whether
indirect calls are a real edge class (function pointers / trait objects) or a
decoder artefact, and it can reveal functions that are only reachable indirectly.
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fees_prog import load  # noqa: E402

p = load(sys.argv[1])
text_lo, text_hi = 0, p.size if hasattr(p, 'size') else p.base + len(p.order)

sites = sorted(pc for pc, i in p.ins.items() if i.op == 0x8d)
print(f'callx sites: {len(sites)}')
resolved = Counter()
unresolved = 0
for pc in sites:
    i = p.ins[pc]
    reg = i.imm            # sbftool stores the register number in imm for callx
    fstart = p.func_of.get(pc, p.base)
    src = None
    for back in range(pc - 1, max(fstart, pc - 60), -1):
        j = p.ins.get(back)
        if not j:
            continue
        if j.dst == reg and j.op in (0x18, 0xb7, 0xbf, 0x07):
            src = (back, j)
            break
    if src and src[1].op == 0x18:
        va = src[1].imm & 0xffffffff
        hi = src[1].imm >> 32
        tgt = None
        for cand in (va, hi):
            if p.base <= cand // 8 < p.base + len(p.order):
                tgt = cand // 8
                break
        if tgt is not None:
            resolved[tgt] += 1
            continue
    unresolved += 1
    if unresolved <= 10:
        print(f'  unresolved callx @{pc:#x} reg r{reg} (fn {fstart:#x}) src={src and (hex(src[0]), repr(src[1]))}')
print(f'\nresolved to {len(resolved)} distinct targets; unresolved={unresolved}')
for tgt, n in resolved.most_common(40):
    known = tgt in p.func_of.values() or tgt in p.starts
    print(f'  target insn {tgt:#x} byte {tgt*8:#x} x{n}'
          f'{"  [known function start]" if tgt in p.starts else "  [NOT a detected function start]"}')
