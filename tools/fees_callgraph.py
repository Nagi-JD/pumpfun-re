#!/usr/bin/env python3
"""pump_fees: handler table + upward call chains in the deployed program.

Prints the 31 handlers (entry insn / byte / body size) from
`maps/fees_handlers_full.json`, then every call chain that reaches the function
given on the command line (depth-limited, one line per level).

Usage: fees_callgraph.py <so> [TARGET]
"""
import json
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from fees_prog import load, handler_table  # noqa: E402


def handlers():
    return handler_table(ROOT)


def fn_of(p, pc):
    return p.func_of.get(pc, p.base)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    p = load(sys.argv[1])
    hs = handlers()
    by_start = {}
    for name, st in hs:
        st_i = st // 8 if st > len(p.order) else st
        by_start[st_i] = name
    print(f'# handlers={len(hs)} (entry = handler_pc from fees_handlers_full.json)')
    for name, st in sorted(hs, key=lambda x: x[1]):
        st_i = st // 8 if st > len(p.order) else st
        print(f'  {name:34s} insn {st_i:#07x} byte {st_i*8:#08x} '
              f'body={len(p.func_body(st_i))} insns')
    print()
    if len(sys.argv) < 3:
        return
    target = int(sys.argv[2], 0)
    t = target // 8 if target > len(p.order) else target
    print(f'# callers of fn @ {t:#x} (byte {t*8:#x})')
    level = {t}
    for depth in range(8):
        nxt = set()
        for f in sorted(level):
            cs = [pc for pc, i in p.ins.items() if i.op == 0x85 and pc + 1 + i.imm == f]
            if not cs:
                continue
            names = []
            for c in sorted(cs):
                cf = fn_of(p, c)
                nm = by_start.get(cf, '')
                names.append(f'{c:#x}(fn {cf:#x}{", " + nm if nm else ""})')
                nxt.add(cf)
            print(f'  depth{depth} fn {f:#x} ({len(p.func_body(f))} insns) <- ' + ' '.join(names))
        if not nxt:
            break
        level = nxt


if __name__ == '__main__':
    main()
