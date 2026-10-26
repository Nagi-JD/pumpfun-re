#!/usr/bin/env python3
"""Print a window of the deployed pump_fees .text around a given insn index."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fees_prog import load  # noqa: E402

p = load(sys.argv[1])
lo = int(sys.argv[2], 0)
hi = int(sys.argv[3], 0)
for pc in range(lo, hi):
    i = p.ins.get(pc)
    if not i:
        continue
    extra = ''
    if i.op == 0x85:
        if pc in getattr(p, 'call_sym', {}):
            extra = f'   -> syscall {p.call_sym[pc]}'
        else:
            t = pc + 1 + i.imm
            extra = f'   -> {t:#x} byte {t*8:#x}'
    print(f'{pc:>6x} {pc*8:>8x}: {i!r}{extra}')
