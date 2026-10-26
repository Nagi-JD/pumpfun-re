#!/usr/bin/env python3
"""Decode the pump_fees .data.rel.ro string/Location table empirically and attribute
records to the functions that load them.

Observed on-disk encoding (pump_fees deployed.so, platform-tools v1.4x): a pointer
slot in .data.rel.ro holds the target VA in its HIGH 32 bits with a zero low dword
(the linker stores no addend for data; this is how the deployed ELF was emitted).
A record is then:
    u64 ptr_hi    -> .rodata path VA
    u64 len       -> byte length of that path
   [u32 line, u32 col]  -> only for panic Location records (24-byte stride);
                            plain &str constants are 16-byte stride.
"""
import json
import struct
import sys
from collections import defaultdict

sys.path.insert(0, __file__.rsplit('/', 2)[0] + '/tools')
from fees_prog import load  # noqa: E402


def short(path, keep=2):
    """Compact a source path for tables: drop the program prefix, keep trailing segments."""
    if path.startswith('programs/pump-fees/src/'):
        return path[len('programs/pump-fees/src/'):]
    parts = path.split('/')
    return '/'.join(parts[-keep:])


def build(p):
    b = p.b
    ro = p.sec['.rodata']
    lo, hi = ro[3], ro[3] + ro[5]
    blob = b[ro[4]:ro[4] + ro[5]]
    path_at = {}
    for off in range(len(blob) - 8):
        if blob.startswith((b'programs/', b'src/', b'library/', b'core/', b'alloc/', b'sdk', b'vendor/'), off):
            j = blob.find(b'\0', off)
            path_at[lo + off] = blob[off:j if j >= 0 else len(blob)]
    drr = p.sec['.data.rel.ro']
    addr, off, size = drr[3], drr[4], drr[5]
    slots = {}
    for o in range(0, size - 16, 8):
        v = struct.unpack_from('<Q', b, off + o)[0]
        va = v >> 32
        if (v & 0xffffffff) == 0 and va in path_at:
            raw = path_at[va]
            slen = struct.unpack_from('<Q', b, off + o + 8)[0]
            if 0 < slen < len(raw) and raw[:slen].endswith(b'.rs'):
                slots[addr + o] = raw[:slen].decode('latin1')
    recs = {}
    strings = {}
    order = sorted(slots)
    for i, va in enumerate(order):
        gap = (order[i + 1] - va) if i + 1 < len(order) else None
        if gap == 24:
            o = va - addr
            line, col = struct.unpack_from('<II', b, off + o + 16)
            if 0 < line < 100000 and 0 < col < 40000:
                recs[va] = {'va': va, 'file': slots[va], 'line': line, 'col': col}
                continue
        strings[va] = {'va': va, 'file': slots[va]}
    return recs, strings


def main():
    p = load(sys.argv[1])
    recs, strings = build(p)
    # lddw sites carrying R_BPF_64_RELATIVE whose target is a record address.
    # Encoding measured on this file: the addend is the LOW 32 bits of the lddw
    # immediate as decoded by sbftool (74 matches; the high half matches nothing).
    refs = defaultdict(list)
    for pc in getattr(p, 'data_ptr', {}):
        ins = p.ins.get(pc)
        if not ins or ins.op != 0x18:
            continue
        va = ins.imm & 0xffffffff
        if va in recs:
            refs[p.func_of.get(pc, p.base)].append((pc, va))
    print(f'# Location records={len(recs)}  plain &str consts={len(strings)}  '
          f'functions referencing a Location={len(refs)}')
    by_file = defaultdict(list)
    for r in recs.values():
        by_file[r['file']].append((r['line'], r['col'], r['va']))
    for f in sorted(by_file):
        pts = sorted(by_file[f])
        print(f'{f}: {len(pts)} location(s)')
        print('   ' + ' '.join(f'{l}:{c}' for l, c, _ in pts))
    print()
    for st in p.starts:
        if st not in refs:
            continue
        body = p.func_body(st)
        print(f'fn @ {st:#x} (byte {st*8:#x}, {len(body)} insns):')
        for pc, va in sorted(refs[st]):
            r = recs[va]
            print(f'   lddw {pc:#x} -> {r["file"]}:{r["line"]}:{r["col"]}')
    if '--json' in sys.argv:
        out = sys.argv[sys.argv.index('--json') + 1]
        json.dump({'locations': sorted(recs.values(), key=lambda r: r['va']),
                   'functions': {hex(k): [{'pc': pc, **recs[va]} for pc, va in v] for k, v in refs.items()}},
                  open(out, 'w'), indent=1)
        print(f'json -> {out}')
    if '--md' in sys.argv:
        out = sys.argv[sys.argv.index('--md') + 1]
        lines = ['| .text insn | .text byte | fn size (insns) | records referenced |',
                 '|---|---|---|---|']
        for st in p.starts:
            if st not in refs:
                continue
            body = p.func_body(st)
            sites = sorted({(recs[va]['file'], recs[va]['line'], recs[va]['col']) for _, va in refs[st]})
            cited = ', '.join(f'`{short(f)}` {l}:{c}' for f, l, c in sites)
            lines.append(f'| `{st:#06x}` | `{st*8:#08x}` | {len(body)} | {cited} |')
        open(out, 'w').write('\n'.join(lines) + '\n')
        print(f'md -> {out}')


if __name__ == '__main__':
    main()
