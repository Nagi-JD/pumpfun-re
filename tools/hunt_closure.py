#!/usr/bin/env python3
"""Find error-closure sites that reference a given source path string in an sBPF ELF.

Usage: hunt_closure.py PROG.so <path-substring> [LINE]

For every `lddw rX, <vaddr of path string>`, print the surrounding instructions
so the (file, line) closure construction is visible. If LINE is given, only sites
whose nearby immediate equals LINE are printed.
"""
import sys, struct
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from sbftool import Prog

def main():
    path, sub = sys.argv[1], sys.argv[2]
    want_line = int(sys.argv[3], 0) if len(sys.argv) > 3 else None
    p = Prog(path)
    b = p.b
    # section table: (name, type, flags, addr, offset, size, link, info, addralign, entsize)
    ro = p.sec.get('.rodata')
    assert ro, 'no .rodata'
    ro_addr, ro_off, ro_size = ro[3], ro[4], ro[5]
    blob = b[ro_off:ro_off + ro_size]
    # locate the path string inside .rodata
    hits = []
    start = 0
    while True:
        i = blob.find(sub.encode(), start)
        if i < 0: break
        # the (ptr,len) string data starts exactly at the match; show local context
        ctx0, ctx1 = max(0, i - 20), min(len(blob), i + len(sub) + 20)
        hits.append((ro_addr + i, blob[ctx0:ctx1].decode('latin1', 'replace')))
        start = i + 1
    if not hits:
        print('string not found'); return
    for vaddr, full in hits:
        print(f'string @ vaddr {hex(vaddr)}: {full}')
    wanted = {va for va, _ in hits}
    # find lddw loading those addresses
    for pc in p.order:
        ins = p.ins[pc]
        if ins.op == 0x18 and ins.imm in wanted:
            # context window
            lo = max(0, p.order.index(pc) - 10)
            ctx = p.order[lo:p.order.index(pc) + 16]
            interesting = False
            if want_line is not None:
                for c in ctx:
                    i2 = p.ins[c]
                    if i2.op in (0x62, 0xb7, 0x18) and (i2.imm & 0xffffffff) == want_line: interesting = True
                if not interesting: continue
            print(f'\n--- lddw site at pc {hex(pc)} (byte {hex(pc*8)}) ---')
            for c in ctx:
                i2 = p.ins[c]
                mark = ' <==' if c == pc else ''
                extra = ''
                if i2.op == 0x85:
                    t = c + 1 + i2.imm
                    extra = f'   -> {hex(t)} {p.name.get(t, "")}'
                if i2.op == 0x18 and i2.imm in wanted:
                    extra = '   ; PATH STRING'
                print(f'{c:>8x}: {i2!r}{extra}{mark}')

if __name__ == '__main__':
    main()
