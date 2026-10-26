#!/usr/bin/env python3
"""Recover the original Rust source reference table of a deployed pump.fun program.

Two reference encodings occur across the four deployed ELFs and both are decoded here:

  A. pointer-slot form (pump, pump_amm, pump_fees)
     `.data.rel.ro` holds (path_ptr, path_len) pairs; a `Location` record is the same
     pair followed by (line: u32, col: u32), i.e. a 24-byte stride instead of 16.
     The pointer slot stores the `.rodata` VA in its HIGH 32 bits with a zero low
     dword (measured; see the pump_fees map).

  B. direct-immediate form (mayhem)
     `.data.rel.ro` carries no string pairs at all (0x1e68 bytes) and the
     `(path_ptr, path_len)` pair is materialised in the handler body: an `lddw`
     carrying the `.rodata` VA in its LOW 32 bits, and a store-immediate carrying
     the length within the next few instructions.

Function starts are computed relocation-aware: `.rel.dyn` type 10 marks a `call`
whose target is an unapplied relocation (imm = -1), so those sites are excluded
from start detection (otherwise every syscall site becomes a function start and
truncates its enclosing function at the prologue).

Outputs (stdout, plus optional --json / --md):
  record table (file, line, col) -> referencing instruction -> function
  per-file location list
  per-function anchor list

usage:
  python3 tools/source_locations.py pump_amm mayhem
  python3 tools/source_locations.py pump_amm --so path/to/deployed.so --json maps/x.json
"""
import argparse
import hashlib
import json
import os
import struct
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sbftool import Prog  # noqa: E402

PATH_ROOTS = (b'programs/', b'generated/', b'src/', b'library/', b'core/', b'alloc/',
              b'sdk', b'vendor/', b'interface')
DEFAULT_ROOT = 'evidence/original'


def reloc_calls(p):
    """pc set of `call` instructions whose imm is an unapplied R_BPF_64_32 relocation."""
    rel = p.sec.get('.rel.dyn') or p.sec.get('.rela.dyn')
    sites = set()
    if not rel:
        return sites
    ent = 24 if '.rela.dyn' in p.sec else 16
    for k in range(rel[5] // ent):
        off, info = struct.unpack_from('<QQ', p.b, rel[4] + k * ent)
        if info % (2 ** 32) == 10:
            sites.add(off // 8)
    return sites


def function_starts(p):
    reloc = reloc_calls(p)
    starts = {p.base}
    for pc, ins in p.ins.items():
        if ins.op != 0x85 or pc in reloc:
            continue
        tgt = pc + 1 + ins.imm
        if tgt in p.ins:
            starts.add(tgt)
    entry = struct.unpack_from('<Q', p.b, 0x18)[0] // 8
    if entry in p.ins:
        starts.add(entry)
    starts = sorted(starts)
    last = max(p.order) + 1
    func_of = {}
    for a, b in zip(starts, starts[1:] + [last]):
        for pc in range(a, b):
            if pc in p.ins:
                func_of[pc] = a
    size = {a: sum(1 for pc in range(a, b) if pc in p.ins)
            for a, b in zip(starts, starts[1:] + [last])}
    return starts, func_of, size


def path_strings(p):
    """VA -> raw NUL-terminated bytes for every source-path-looking string."""
    out = {}
    for name in ('.rodata', '.data.rel.ro'):
        sec = p.sec.get(name)
        if not sec:
            continue
        lo, off, size = sec[3], sec[4], sec[5]
        blob = p.b[off:off + size]
        for i in range(len(blob) - 8):
            if blob.startswith(PATH_ROOTS, i):
                j = blob.find(b'\0', i)
                out[lo + i] = blob[i:j if j >= 0 else len(blob)]
    return out


def pointer_slots(p, paths):
    """A. (path_ptr, path_len) pairs held in .data.rel.ro, split into 24-byte Location
    records and 16-byte plain &str constants."""
    drr = p.sec.get('.data.rel.ro')
    if not drr:
        return {}, {}
    addr, off, size = drr[3], drr[4], drr[5]
    slots = {}
    for o in range(0, size - 16, 8):
        v = struct.unpack_from('<Q', p.b, off + o)[0]
        va = v >> 32
        if (v & 0xffffffff) == 0 and va in paths:
            raw = paths[va]
            slen = struct.unpack_from('<Q', p.b, off + o + 8)[0]
            if 0 < slen < len(raw) and raw[:slen].endswith(b'.rs'):
                slots[addr + o] = (raw[:slen].decode('latin1'), slen)
    order = sorted(slots)
    records, strings = {}, {}
    for i, va in enumerate(order):
        nxt = order[i + 1] if i + 1 < len(order) else None
        if nxt is not None and nxt - va == 24:
            o = va - addr
            line, col = struct.unpack_from('<II', p.b, off + o + 16)
            if 0 < line < 100000 and 0 < col < 40000:
                records[va] = {'addr': va, 'file': slots[va][0], 'len': slots[va][1],
                               'line': line, 'col': col}
                continue
        strings[va] = {'addr': va, 'file': slots[va][0], 'len': slots[va][1]}
    return records, strings


def direct_refs(p, paths):
    """B. (path_ptr, path_len) pairs materialised inside the code: lddw carries the
    `.rodata` VA in its low 32 bits, the length is the first store-immediate in the
    next six instructions that slices the string at (or past) the `.rs` boundary of
    the path. A slice that runs past the boundary is a path+message payload: the
    message text is stored immediately after the path with no NUL separator, so the
    file identity is the path prefix and the recorded length is the whole payload."""
    refs = {}
    for pc, ins in sorted(p.ins.items()):
        if ins.op != 0x18:
            continue
        va = ins.imm & 0xffffffff
        if va not in paths:
            continue
        raw = paths[va]
        end = raw.find(b'.rs')
        if end < 0:
            continue
        plen = end + 3
        exact, combined = None, None
        for pc2 in range(pc + 1, pc + 7):
            ins2 = p.ins.get(pc2)
            if not ins2 or ins2.op not in (0x62, 0x6a, 0x72, 0x7a):
                continue
            n = ins2.imm & 0xffffffff
            if n == plen:
                exact = (pc2, n)
                break
            if combined is None and plen < n < min(len(raw), plen + 200):
                tail = raw[plen:n]
                if all(32 <= c < 127 for c in tail):
                    combined = (pc2, n)
        pick = exact or combined
        if pick:
            pc2, n = pick
            refs[pc] = {'addr': va, 'file': raw[:plen].decode('latin1'), 'len': n,
                        'kind': 'path' if n == plen else 'path+message',
                        'len_store': pc2}
    return refs


def attribute(p, func_of, sites):
    """site pc -> (function start, anchor dict)."""
    out = defaultdict(list)
    for site, rec in sites.items():
        out[func_of.get(site, p.base)].append((site, rec))
    return out


PROG_PREFIX = {
    'pump': 'programs/pump/src/',
    'pump_amm': 'programs/pump-amm/src/',
    'pump_fees': 'programs/pump-fees/src/',
    'mayhem': 'programs/mayhem-program/src/',
}


def handler_files(p, func_of, rec_of_pc, handlers, prefix, depth=3):
    """For each handler entry, the program source files whose anchors are reachable
    through the direct call graph (depth <= 3). Anchor-syn / core frames are skipped:
    they are reachable from every handler and carry no handler identity."""
    calls = defaultdict(set)
    for pc, ins in p.ins.items():
        if ins.op == 0x85:
            tgt = pc + 1 + ins.imm
            if tgt in p.ins:
                calls[func_of.get(pc, p.base)].add(tgt)
    anchor_fn = {func_of.get(pc, p.base) for pc in rec_of_pc}
    out = {}
    for name, entry in handlers.items():
        if isinstance(entry, dict):
            entry = entry.get('handler') or entry.get('stub')
        if entry is None:
            continue
        st = int(entry, 16) if isinstance(entry, str) else entry
        seen, frontier = {st}, [st]
        for _ in range(depth):
            nxt = []
            for f in frontier:
                for t in calls.get(f, ()):
                    if t not in seen:
                        seen.add(t)
                        nxt.append(t)
            frontier = nxt
        files = defaultdict(int)
        for pc, rec in rec_of_pc.items():
            if func_of.get(pc, p.base) in seen and rec['file'].startswith(prefix):
                files[rec['file']] += 1
        out[name] = {'entry': f'{st:#x}', 'reach': len(seen),
                     'program_files': {f: n for f, n in sorted(files.items())}}
    return out


def build(so_path, prog_name, handlers=None):
    p = Prog(so_path)
    starts, func_of, size = function_starts(p)
    paths = path_strings(p)
    records, strings = pointer_slots(p, paths)
    # A record is referenced by any lddw whose low 32 bits equal its VA (the addend
    # form measured on these ELFs).
    refs = defaultdict(list)
    for pc, ins in p.ins.items():
        if ins.op != 0x18:
            continue
        va = ins.imm & 0xffffffff
        if va in records:
            refs[va].append(pc)
    direct = direct_refs(p, paths) if not records else {}

    rec_of_pc = {}
    fn_records = defaultdict(list)
    for va, rec in records.items():
        for pc in refs.get(va, []):
            rec_of_pc[pc] = rec
            fn_records[func_of.get(pc, p.base)].append(
                {'pc': pc, 'addr': va, **{k: records[va][k] for k in ('file', 'line', 'col')}})
    fn_direct = defaultdict(list)
    direct_of_pc = {}
    for pc, rec in direct.items():
        direct_of_pc[pc] = rec
        fn_direct[func_of.get(pc, p.base)].append({'pc': pc, **rec})

    d = {
        'program': prog_name,
        'binary': f'evidence/original/{prog_name}/deployed.so',
        'sha256': hashlib.sha256(open(so_path, 'rb').read()).hexdigest(),
        'text_insns': len(p.ins),
        'functions': len(starts),
        'path_strings': len(paths),
        'location_records': len(records),
        'plain_str_consts': len(strings),
        'location_functions': len(fn_records),
        'direct_refs': len(direct),
        'direct_functions': len(fn_direct),
        'files': sorted({r['file'] for r in records.values()} |
                        {r['file'] for r in direct.values()}),
        'program_files': sorted({r['file'] for r in records.values()
                                 if r['file'].startswith(PROG_PREFIX.get(prog_name, ''))} |
                                {r['file'] for r in direct.values()
                                 if r['file'].startswith(PROG_PREFIX.get(prog_name, ''))}),
        'runtime_files': sorted({r['file'] for r in records.values()} |
                                {r['file'] for r in direct.values()}),
        'records': sorted(records.values(), key=lambda r: (r['file'], r['line'], r['col'])),
        'strings': sorted(strings.values(), key=lambda r: r['file']),
        'functions_records': {f'{k:#x}': sorted(v, key=lambda x: (x['file'], x['line']))
                              for k, v in sorted(fn_records.items())},
        'functions_direct': {f'{k:#x}': sorted(v, key=lambda x: x['file'])
                             for k, v in sorted(fn_direct.items())},
        'func_sizes': {f'{k:#x}': size[k] for k in sorted(set(fn_records) | set(fn_direct))},
    }
    d['runtime_files'] = sorted(set(d['runtime_files']) - set(d['program_files']))
    if handlers:
        d['handler_files'] = handler_files(p, func_of, {**rec_of_pc, **direct_of_pc},
                                           handlers, PROG_PREFIX.get(prog_name, ''))
    return d


def short(path):
    for pre in ('programs/pump-amm/src/', 'programs/pump_fees/src/', 'programs/pump-fees/src/',
                'programs/pump/src/', 'programs/mayhem-program/src/', 'programs/mayhem/src/'):
        if path.startswith(pre):
            return path[len(pre):]
    return path


def report(d):
    print(f"## {d['program']}")
    print(f"   sha256 {d['sha256']}")
    print(f"   text insns {d['text_insns']}  functions {d['functions']}  "
          f"path strings {d['path_strings']}  Location records {d['location_records']}  "
          f"plain &str {d['plain_str_consts']}")
    if d['location_records']:
        print(f"   {d['location_records']} Location records in {len(d['files'])} files, "
              f"referenced from {d['location_functions']} functions")
        by_file = defaultdict(list)
        for r in d['records']:
            by_file[r['file']].append(r)
        for f in sorted(by_file):
            pts = by_file[f]
            print(f'   {f}  ({len(pts)})')
            print('      ' + ' '.join(f"{r['line']}:{r['col']}@{r['addr']:#x}" for r in pts))
    if d['direct_refs']:
        print(f"   {d['direct_refs']} (path,len) references in {d['direct_functions']} "
              f"functions, {len(d['files'])} files")
        by_file = defaultdict(list)
        for fns in d['functions_direct'].values():
            for r in fns:
                by_file[r['file']].append(r)
        for f in sorted(by_file):
            pts = by_file[f]
            print(f'   {f}  ({len(pts)})  len ' +
                  ' '.join(f"{r['len']}@{r['pc']:#x}" for r in pts[:12]) +
                  (' ...' if len(pts) > 12 else ''))
    print(f"   program files {len(d['program_files'])}  runtime/Anchor frames "
          f"{len(d['runtime_files'])}")
    if d.get('handler_files'):
        print('   handler -> program files (call-graph depth 3):')
        for name, v in d['handler_files'].items():
            files = ', '.join(short(f) for f in v['program_files'])
            print(f"     {name:34s} {v['entry']:>9s} reach={v['reach']:3d} {files}")
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('programs', nargs='+')
    ap.add_argument('--so', help='explicit deployed.so (single program)')
    ap.add_argument('--root', default=DEFAULT_ROOT)
    ap.add_argument('--json', help='write the per-program JSON here (dir or file for one program)')
    ap.add_argument('--md')
    ap.add_argument('--handlers', action='append', default=[],
                    help='NAME=PATH handler table (repeatable); default maps/<program>_handlers.json')
    a = ap.parse_args()
    handler_tables = {}
    for spec in a.handlers:
        name, _, path = spec.partition('=')
        handler_tables[name] = json.load(open(path))
    out = {}
    for prog in a.programs:
        so = a.so or os.path.join(a.root, prog, 'deployed.so')
        if not os.path.exists(so):
            raise SystemExit(f'no such file: {so}')
        handlers = handler_tables.get(prog)
        if handlers is None:
            guess = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 'maps', f'{prog}_handlers.json')
            if os.path.exists(guess):
                handlers = json.load(open(guess))
        d = build(so, prog, handlers)
        out[prog] = d
        report(d)
        if a.json:
            target = a.json
            if len(a.programs) > 1 or os.path.isdir(a.json or ''):
                os.makedirs(a.json, exist_ok=True)
                target = os.path.join(a.json, f'{prog}_source_locations.json')
            json.dump(d, open(target, 'w'), indent=1)
            print(f'json -> {target}')
        if a.md:
            lines = [f'## {prog}', '', f"sha256 `{d['sha256']}`", '',
                     '| function (.text insn) | byte | size (insns) | anchors (file:line:col) |',
                     '|---|---|---|---|']
            for fn, recs in d['functions_records'].items():
                cited = ', '.join(f"`{short(r['file'])}` {r['line']}:{r['col']}" for r in recs)
                lines.append(f"| `{fn}` | `{int(fn, 16) * 8:#x}` | "
                             f"{d['func_sizes'][fn]} | {cited} |")
            for fn, recs in d['functions_direct'].items():
                cited = ', '.join(f"`{short(r['file'])}` len {r['len']}" for r in recs)
                lines.append(f"| `{fn}` | `{int(fn, 16) * 8:#x}` | "
                             f"{d['func_sizes'][fn]} | {cited} |")
            open(a.md, 'w').write('\n'.join(lines) + '\n')
            print(f'md -> {a.md}')


if __name__ == '__main__':
    main()
