#!/usr/bin/env python3
"""fees_p0_probe - toolchain-free measurements for the pump_fees P0 (byte-identical) unit.

Answers, from evidence/original/pump_fees/deployed.so only:
  * syscall inventory (call sites per syscall name) and the sol_memmove_ users
    (enclosing function + transitive caller chain up to a handler entry),
  * function index (start, insns, exits, calls, syscalls) + totals,
  * panic-Location records in .rodata: (file, line, col) -> which source file a
    panic site claims to live in (feeds FIX 1: module tree + line/column match).

Usage:
  fees_p0_probe.py sites     SO   # sol_memmove_/sol_memcpy_ call sites + caller chains
  fees_p0_probe.py syscalls  SO   # full syscall inventory
  fees_p0_probe.py index     SO   # per-function index as JSON to stdout
  fees_p0_probe.py locations SO   # panic Location records grouped by file
  fees_p0_probe.py summary   SO   # totals (functions/exits/calls) + both above counts
"""
import json
import os
import struct
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fees_prog import load  # noqa: E402


def func_start_of(p, pc):
    return p.func_of.get(pc, p.base)


def callers_of(p, target):
    return [pc for pc, i in p.ins.items() if i.op == 0x85 and pc + 1 + i.imm == target]


def chain(p, pc, depth=4):
    """Walk up callers to find the outermost enclosing entry point."""
    cur, out, seen = pc, [], set()
    for _ in range(depth):
        cs = callers_of(p, func_start_of(p, cur))
        if not cs:
            break
        nxt = cs[0]
        if nxt in seen:
            break
        seen.add(nxt)
        out.append((func_start_of(p, nxt), nxt))
        cur = nxt
    return out


def syscalls(p):
    c = Counter()
    for pc, name in getattr(p, 'call_sym', {}).items():
        c[name] += 1
    return c


def cmd_sites(p):
    c = syscalls(p)
    print('# syscall inventory (call sites)')
    for name, n in c.most_common():
        print(f'  {n:5d}  {name}')
    print()
    for want in ('sol_memmove_', 'sol_memcpy_', 'memmove', 'memcpy'):
        if want not in c:
            print(f'{want}: 0 call sites')
            continue
        print(f'# {want}: {c[want]} call site(s)')
        for pc, name in sorted((pc, n) for pc, n in p.call_sym.items() if n == want):
            st = func_start_of(p, pc)
            body = p.func_body(st)
            print(f'  site insn {pc:#x} (byte {pc*8:#x})  in function @ {st:#x} '
                  f'(byte {st*8:#x}, {len(body)} insns, {sum(1 for i in body if i.op == 0x95)} exits)')
            ch = chain(p, pc)
            for st2, cs in ch:
                print(f'      <- called from {cs:#x} in function @ {st2:#x} (byte {st2*8:#x})')
        print()


def cmd_syscalls(p):
    for name, n in syscalls(p).most_common():
        print(f'{n:5d}  {name}')


def index(p):
    out = []
    for st in p.starts:
        body = p.func_body(st)
        out.append({
            'start_insn': st,
            'start_byte': st * 8,
            'insns': len(body),
            'exits': sum(1 for i in body if i.op == 0x95),
            'calls': sum(1 for i in body if i.op == 0x85 and i.pc not in getattr(p, 'call_sym', {})),
            'syscall_calls': sum(1 for i in body if i.pc in getattr(p, 'call_sym', {})),
            'syscalls': sorted({p.call_sym[i.pc] for i in body if i.pc in getattr(p, 'call_sym', {})}),
            'callers': len(callers_of(p, st)),
        })
    return out


def cmd_index(p):
    print(json.dumps(index(p), indent=1))


def locations(p):
    """Scan .rodata for Rust panic Location records {file_ptr,file_len,line:u32,col:u32}."""
    b = p.b
    sec = p.sec.get('.rodata')
    if not sec:
        print('no .rodata')
        return
    ro_addr, ro_off, ro_size = sec[3], sec[4], sec[5]
    blob = b[ro_off:ro_off + ro_size]
    # The embedded paths are NOT NUL-terminated runs: several `.rs` paths sit in one
    # concatenated run, so index every offset where a known prefix starts and match the
    # Location's (ptr, len) pair against the raw substring.
    prefixes = (b'programs/', b'library/', b'src/', b'core/', b'alloc/', b'sdk')
    starts = {}
    for off in range(0, len(blob) - 4, 8):
        if blob.startswith(prefixes, off):
            starts[ro_addr + off] = off
    recs = []
    for off in range(0, len(blob) - 23, 8):
        ptr, slen = struct.unpack_from('<QQ', blob, off)
        if ptr not in starts or not (4 < slen < 200):
            continue
        so = starts[ptr]
        raw = blob[so:so + slen]
        if len(raw) != slen or not raw.endswith(b'.rs') or b'\0' in raw:
            continue
        try:
            name = raw.decode('utf-8')
        except UnicodeDecodeError:
            continue
        line, col = struct.unpack_from('<II', blob, off + 16)
        if not (0 < line < 100000 and 0 < col < 10000):
            continue
        recs.append({'ro_off': off, 'ro_va': ro_addr + off, 'file': name, 'line': line, 'col': col})
    by_file = defaultdict(list)
    for r in recs:
        by_file[r['file']].append((r['line'], r['col'], r['ro_va']))
    print(f'# panic Location records: {len(recs)} across {len(by_file)} files')
    for f in sorted(by_file):
        pts = sorted(by_file[f])
        print(f'  {f}: {len(pts)} site(s)')
        print('    ' + ' '.join(f'{l}:{c}@{va:#x}' for l, c, va in pts))
    print()
    print(f'# embedded source paths seen in .rodata (prefix-matched, {len(starts)} starts)')
    for va in sorted(starts):
        so = starts[va]
        j = blob.find(b'\0', so)
        print(f'  {va:#08x}  {blob[so:min(j, so + 120)].decode("latin1")}')
    print()
    print(json.dumps(recs, indent=1))


def cmd_summary(p):
    idx = index(p)
    print(f'functions={len(p.starts)} insns={len(p.order)} text_bytes={p.tsize}')
    print(f'exits={sum(f["exits"] for f in idx)} internal_calls={sum(f["calls"] for f in idx)} '
          f'syscall_calls={sum(f["syscall_calls"] for f in idx)}')
    print(f'distinct_syscalls={len(syscalls(p))}')
    print(f'sol_memmove_={syscalls(p).get("sol_memmove_", 0)} sol_memcpy_={syscalls(p).get("sol_memcpy_", 0)}')


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    cmd, path = sys.argv[1], sys.argv[2]
    p = load(path)
    {'sites': cmd_sites, 'syscalls': cmd_syscalls, 'index': cmd_index,
     'locations': locations, 'summary': cmd_summary}[cmd](p)


if __name__ == '__main__':
    main()
