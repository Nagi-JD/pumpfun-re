#!/usr/bin/env python3
"""Print the relocation (if any) attached to specific .text instruction indices."""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fees_prog import load  # noqa: E402

p = load(sys.argv[1])
rel = p.sec['.rel.dyn']
want = {int(a, 0) for a in sys.argv[2:]}
for k in range(rel[5] // 16):
    roff, info = struct.unpack_from('<QQ', p.b, rel[4] + k * 16)
    pc = roff // 8
    if pc in want:
        typ, sy = info % (2 ** 32), info >> 32
        nm = p.dynsym[sy][0] if sy < len(p.dynsym) else '?'
        print(f'reloc @ insn {pc:#x} (byte {roff:#x}) type={typ} sym={sy} name={nm}'
              f' imm={p.ins[pc].imm:#x}')
print('ELF e_entry =', hex(struct.unpack_from('<Q', p.b, 0x18)[0]))
