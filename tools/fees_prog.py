#!/usr/bin/env python3
"""Loader shared by the pump_fees analysis tools.

sbftool.py (as of upstream/master) decodes .text and resolves syscall *names* from
.dynsym, but it does not read `.rel.dyn`. Two consequences on the deployed
pump_fees program (and on every program whose build keeps unapplied relocations):

  * a relocated `call` carries `imm = -1`, so `pc + 1 + imm == pc` and sbftool's
    function-start detection turns every syscall site into a bogus function start,
    truncating the enclosing function at its prologue;
  * function pointers / rodata addresses loaded with `lddw` are not resolvable.

This module re-does the two passes properly on top of sbftool's decoder:

  * `.rel.dyn` type 10 (`R_BPF_64_32`) -> `p.call_sym[pc] = symbol name`
  * `.rel.dyn` type 8  (`R_BPF_64_RELATIVE`) -> `p.data_ptr[pc] = True`; the addend
    is the LOW 32 bits of the decoded `lddw` immediate on this ELF
  * function starts = first insn + internal call targets (syscall sites excluded)
    + `e_entry` (a function that is never called, e.g. the entry point, would
    otherwise be folded into its predecessor)

Everything else (instruction decode, syscall hashing, field analysis) stays in
sbftool.
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sbftool import Prog  # noqa: E402


def _dynsym(p):
    ds, dss = p.sec.get('.dynsym'), p.sec.get('.dynstr')
    names = []
    if not ds or not dss:
        return names
    for k in range(ds[5] // 24):
        stn = struct.unpack_from('<I', p.b, ds[4] + k * 24)[0]
        names.append(p.b[dss[4] + stn:p.b.index(b'\0', dss[4] + stn)].decode('latin1'))
    return names


def relocs(p):
    names = _dynsym(p)
    call_sym, data_ptr = {}, {}
    for sname in ('.rel.dyn', '.rela.dyn'):
        sec = p.sec.get(sname)
        if not sec:
            continue
        ent = 24 if sname.endswith('a.dyn') else 16
        for k in range(sec[5] // ent):
            off, info = struct.unpack_from('<QQ', p.b, sec[4] + k * ent)
            typ, sy = info % (2 ** 32), info >> 32
            pc = off // 8
            if typ == 10:
                call_sym[pc] = names[sy] if sy < len(names) else '?'
            elif typ == 8:
                data_ptr[pc] = True
    return call_sym, data_ptr


def handler_table(root=None):
    """name -> handler entry insn, reading either the S1 map (`fees_handlers.json`,
    keys `handler`) or the S1b map (`fees_handlers_full.json`, key `handler_pc`)."""
    root = root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for name in ('fees_handlers_full.json', 'fees_handlers.json'):
        path = os.path.join(root, 'maps', name)
        if not os.path.exists(path):
            continue
        d = json.load(open(path))
        out = []
        for ix, v in d.items():
            if not isinstance(v, dict):
                continue
            st = v.get('handler_pc', v.get('handler'))
            if st is None:
                continue
            out.append((ix, int(st, 0) if isinstance(st, str) else st))
        return sorted(out, key=lambda x: x[1])
    raise SystemExit('no handler map under maps/ (fees_handlers*.json)')


def load(path):
    p = Prog(path)
    p.call_sym, p.data_ptr = relocs(p)
    starts = {p.base}
    for pc, ins in p.ins.items():
        if ins.op != 0x85 or pc in p.call_sym:
            continue
        tgt = pc + 1 + ins.imm
        if tgt in p.ins:
            starts.add(tgt)
    entry = struct.unpack_from('<Q', p.b, 0x18)[0] // 8
    p.entry = entry if entry in p.ins else None
    if p.entry is not None:
        starts.add(p.entry)
    p.starts = sorted(starts)
    # sbftool.func_body() ends the last function at `base + len(order)`, i.e. it
    # assumes the instruction stream is contiguous from the first insn. It is not
    # (pc = base + byte_offset/8), so that bound truncates the final function to
    # zero insns. Bound function ranges by the last decoded pc instead.
    last = max(p.order) + 1
    p.func_of = {}
    for a, b in zip(p.starts, p.starts[1:] + [last]):
        for pc in range(a, b):
            if pc in p.ins:
                p.func_of[pc] = a

    def func_body(start, _p=p, _last=last):
        nxt = [x for x in _p.starts if x > start]
        stop = nxt[0] if nxt else _last
        return [_p.ins[pc] for pc in range(start, stop) if pc in _p.ins]

    p.func_body = func_body
    return p
