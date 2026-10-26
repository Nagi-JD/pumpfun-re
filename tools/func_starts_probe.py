#!/usr/bin/env python3
"""func_starts_probe.py - quantify how many function spans the syscall-relocation
artifact (sbftool `_funcs` before the fix) truncated.

Old rule: starts = {base} + every call target, including syscall call sites whose
on-disk imm is -1 (pc+1+imm == pc). New rule: same, minus type-10 reloc sites.

Usage: func_starts_probe.py PROG.so
"""
import sys

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from sbftool import Prog  # noqa: E402


def main():
    p = Prog(sys.argv[1])
    fake = set(p.call_sym)
    internal = set()
    for pc, ins in p.ins.items():
        if ins.op == 0x85 and pc not in p.call_sym:
            t = pc + 1 + ins.imm
            if t in p.ins and t != pc:
                internal.add(t)
    old_starts = sorted({p.base} | internal | fake)
    new_starts = sorted({p.base} | internal)
    hi = p.base + len(p.order)

    def span(a, starts):
        nxt = [x for x in starts if x > a]
        end = nxt[0] if nxt else hi
        return sum(1 for pc in range(a, end) if pc in p.ins)

    grew = sum(1 for a in new_starts if span(a, new_starts) > span(a, old_starts))
    print('%s: syscall_sites=%d internal_targets=%d fake_also_real=%d '
          'old_starts=%d new_starts=%d removed=%d spans_grown=%d' % (
              sys.argv[1].rsplit('/', 2)[-2], len(fake), len(internal),
              len(fake & internal), len(old_starts), len(new_starts),
              len(old_starts) - len(new_starts), grew))


if __name__ == '__main__':
    main()
