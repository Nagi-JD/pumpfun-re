#!/usr/bin/env python3
"""Per-handler call-graph reachability on the deployed pump_fees program.

BFS over direct `call` edges (op 0x85, relocation-free targets) from each handler
entry, recording which of a set of interesting functions is reachable. Also
reports the functions that no handler reaches (dead code / vtable-only), which is
the candidate set for the "~3 missing functions" question.

Indirect edges: the program has 121 `callx` sites, all of the dynamic-dispatch
form (`and 0x3; add -0x2; ldxdw [r-1]; ldxdw [r+7]; callx`) used for
drop_in_place of `dyn` values; they are not function-pointer tables, so the direct
closure is the whole static graph. `fees_addr_taken.py` checks the stronger claim
for specific functions (none of the allocator chain has its address taken).

Usage: fees_handler_reach.py SO [--watch ADDR ...]
"""
import json
import os
import sys
from collections import deque

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from fees_prog import load, handler_table  # noqa: E402


def direct_callees(p):
    out = {}
    for pc, i in p.ins.items():
        if i.op != 0x85 or pc in getattr(p, 'call_sym', {}):
            continue
        t = pc + 1 + i.imm
        if t in p.ins:
            out.setdefault(p.func_of.get(pc, p.base), set()).add(t)
    return out


def reach(edges, start):
    seen, q = set(), deque([start])
    while q:
        f = q.popleft()
        if f in seen:
            continue
        seen.add(f)
        for t in edges.get(f, ()):
            if t not in seen:
                q.append(t)
    return seen


def main():
    so = sys.argv[1]
    p = load(so)
    edges = direct_callees(p)
    handlers = []
    for name, st in handler_table(ROOT):
        st = st // 8 if st > len(p.order) else st
        handlers.append((name, st))

    watch = {}
    for k, a in enumerate(sys.argv):
        if a == '--watch':
            break
    if '--watch' in sys.argv:
        for a in sys.argv[sys.argv.index('--watch') + 1:]:
            va = int(a, 0)
            insn = va // 8 if va > len(p.order) else va
            watch[f'{va:#x}'] = insn
    if not watch:
        watch = {'alloc/memmove fn 0xb1b0': 0x1636,
                 'memcpy thunk 0xc26c8': 0x184d9,
                 'memmove thunk 0xc26e8': 0x184dd}

    print(f'# direct-call graph: {len(edges)} functions with callees')
    header = f'{"handler":34s} {"entry":>9s} insns  ' + '  '.join(f'{k}' for k in watch)
    print(header)
    all_reach = set()
    for name, st in sorted(handlers, key=lambda x: x[1]):
        r = reach(edges, st)
        all_reach |= r
        marks = '  '.join(f'{"YES" if v in r else "-":>{len(k)}}' for k, v in watch.items())
        print(f'{name:34s} {st:#9x} {len(p.func_body(st)):5d}  {marks}')

    # dispatcher reachability too (0x1240e = entry dispatch)
    disp = 0x1240e
    dr = reach(edges, disp)
    er = reach(edges, p.entry) if p.entry else set()
    print(f'\ndispatcher @ {disp:#x} reaches {len(dr)} functions;'
          f' ELF entry @ {p.entry and hex(p.entry)} reaches {len(er)}'
          f' ({len(all_reach)} reachable from handlers)')

    unreached = [f for f in p.starts if f not in all_reach and f not in dr and f not in er]
    print(f'\n# functions not reachable from the dispatcher or any handler: {len(unreached)}')
    for f in unreached:
        body = p.func_body(f)
        sysc = sorted({p.call_sym[i.pc] for i in body if i.pc in getattr(p, 'call_sym', {})})
        print(f'  fn {f:#07x} byte {f*8:#08x} {len(body):4d} insns'
              + (f'  syscalls={sysc}' if sysc else ''))


if __name__ == '__main__':
    main()
