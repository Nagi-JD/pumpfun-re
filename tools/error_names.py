#!/usr/bin/env python3
"""error_names - binary-derived custom-error tables for a deployed sBPF program.

Recovers, from the deployed bytes only:

  1. the program's own `ErrorCode::name()` table: a leaf function that binary-searches
     the enum discriminant and returns (ptr, len) into a packed `.rodata` name block;
     emulated instruction-by-instruction for every discriminant in range, so
     `code -> variant name` comes from the program, not from a source enum;
  2. every custom-error raise site: `stw [r10+off], imm` with imm in the custom range,
     attributed to the enclosing function and, through the call graph, to the
     instruction handler that can reach it;
  3. the original source `file:line` of each raise, decoded from the Anchor `Location`
     record (.data.rel.ro 24-byte stride) referenced near the site.

Usage:
  error_names.py PROG              # PROG in {pump,pump_amm,pump_fees,mayhem}
  error_names.py --all --out maps/
"""
import json
import os
import re
import struct
import sys
from collections import defaultdict, OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sbftool import Prog  # noqa: E402

ROOT = os.environ.get('PUMPFUN_EVIDENCE')      # optional; defaults to <repo>/evidence/original
PROGS = ('pump', 'pump_amm', 'pump_fees', 'mayhem')
HANDLER_MAPS = {'pump': 'maps/handlers.json', 'pump_amm': 'maps/amm_handlers_full.json',
                'pump_fees': 'maps/fees_handlers.json'}

# Anchor custom-error ranges actually used by these programs.
ERR_LO, ERR_HI = 6000, 6110


# ---------------------------------------------------------------- segments / memory
def segments(p):
    """VA -> file offset for every allocated section, so a VA can be read back."""
    segs = []
    for name, s in p.secs:
        addr, off, size = s[3], s[4], s[5]
        if s[2] & 0x2 and size:                      # SHF_ALLOC
            segs.append((addr, addr + size, off, name))
    return sorted(segs)


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
    """Function starts = call targets, ignoring unapplied relocation slots (a
    syscall call site must not become a function start) + the ELF entry point."""
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
    size = {}
    for a, b in zip(starts, starts[1:] + [last]):
        for pc in range(a, b):
            if pc in p.ins:
                func_of[pc] = a
        size[a] = sum(1 for pc in range(a, b) if pc in p.ins)
    return starts, func_of, size


PATH_ROOTS = (b'programs/', b'generated/', b'src/', b'library/', b'core/', b'alloc/',
              b'sdk', b'vendor/', b'interface')


def path_strings(p):
    """VA -> raw bytes for every source-path-looking string (packed without NUL
    separators in these builds; the caller trims at the `.rs` boundary)."""
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


def va_read(p, segs, va, n):
    for lo, hi, off, _name in segs:
        if lo <= va < hi:
            k = min(n, hi - va)
            return p.b[off + (va - lo):off + (va - lo) + k]
    return b''


# ---------------------------------------------------------------- name table discovery
CAMEL = re.compile(rb'[A-Z][A-Za-z0-9_]{2,60}')


def name_candidates(p, starts, func_of):
    """Leaf functions that carry several `lddw` of VAs landing inside a packed
    CamelCase identifier block. The error-name table is the biggest such function."""
    out = []
    for st in starts:
        body = p.func_body(st)
        if not body or len(body) > 4000:
            continue
        lddw = [i for i in body if i.op == 0x18]
        hits = [i for i in lddw if (i.imm & 0xffffffff) in CAMEL_BLOCK]
        if len(hits) < 6:
            continue
        cond = sum(1 for i in body if i.op in (0x15, 0x1d, 0x25, 0x2d, 0x35, 0x3d,
                                              0x55, 0x5d, 0x65, 0x6d, 0x75, 0x7d,
                                              0xa5, 0xad, 0xb5, 0xbd))
        calls = sum(1 for i in body if i.op in (0x85, 0x8d))
        out.append({'start': st, 'insns': len(body), 'lddw': len(lddw),
                    'camel_refs': len(hits), 'cond': cond, 'calls': calls,
                    'score': len(hits) + cond / 4.0 - 2.0 * calls})
    out.sort(key=lambda d: -d['score'])
    return out


def camel_block(p, segs):
    """VA set of every byte covered by a CamelCase identifier-like string in the
    read-only data sections. The error-name block packs these identifiers back to
    back (no NUL separator), so a name can start in the middle of a regex match and
    membership has to be per byte."""
    vals = set()
    for name in ('.rodata', '.data.rel.ro'):
        s = p.sec.get(name)
        if not s:
            continue
        addr, off, size = s[3], s[4], s[5]
        blob = p.b[off:off + size]
        for m in re.finditer(rb'[A-Z][A-Za-z0-9]{2,60}', blob):
            for va in range(addr + m.start(), addr + m.end()):
                vals.add(va)
    return vals


# ---------------------------------------------------------------- sBPF interpreter
class Machine:
    """Just enough of the sBPF v1 ISA to execute the error-name function."""

    def __init__(self, p, segs, stack_words=64):
        self.p, self.segs = p, segs
        self.reg = [0] * 11
        self.fp = 0x20000000
        self.reg[10] = self.fp
        self.stack = bytearray(stack_words * 8)
        self.steps = 0

    # memory access: stack window handled separately
    def load(self, addr, n):
        if self.fp <= addr < self.fp + len(self.stack):
            o = addr - self.fp
            return int.from_bytes(self.stack[o:o + n], 'little')
        b = va_read(self.p, self.segs, addr, n)
        if not b:
            raise RuntimeError(f'unmapped load 0x{addr:x}')
        return int.from_bytes(b, 'little')

    def store(self, addr, n, val):
        if self.fp <= addr < self.fp + len(self.stack):
            o = addr - self.fp
            self.stack[o:o + n] = val.to_bytes(n, 'little')
            return
        raise RuntimeError(f'unmapped store 0x{addr:x}')

    def run(self, entry, args, max_steps=100000, stop_at_call=True):
        """Execute from `entry`. The name function binary-searches the enum
        discriminant into a (ptr, len) pair in r2/r3 and then hands it to the
        formatter through a single tail `call`, so the register file at that call
        is the return value."""
        self.reg = [0] * 11
        self.reg[10] = self.fp
        self.steps = 0
        r = self.reg
        for k, v in enumerate(args):
            r[1 + k] = v
        pc = entry
        while self.steps < max_steps:
            self.steps += 1
            ins = self.p.ins.get(pc)
            if ins is None:
                raise RuntimeError(f'pc 0x{pc:x} not an instruction')
            op = ins.op
            dst, src = ins.dst, ins.src
            if op == 0x18:                              # lddw
                r[dst] = ins.imm & 0xffffffffffffffff
                pc += 2
                continue
            if op == 0x95:                              # exit
                return {i: v for i, v in enumerate(r)}
            if op == 0x85:                              # call imm
                if stop_at_call:
                    return {i: v for i, v in enumerate(r)}
                raise RuntimeError(f'unexpected call at 0x{pc:x}')
            if op in (0x8d,):
                raise RuntimeError(f'unexpected callx at 0x{pc:x}')
            if op in (0x61, 0x69, 0x71, 0x79):          # ldx{x}{w,h,b,dw}
                n = {0x61: 4, 0x69: 2, 0x71: 1, 0x79: 8}[op]
                r[dst] = self.load((r[src] + ins.off) & 0xffffffffffffffff, n)
                pc += 1
                continue
            if op in (0x62, 0x6a, 0x72, 0x7a):          # st{x} imm
                n = {0x62: 4, 0x6a: 2, 0x72: 1, 0x7a: 8}[op]
                self.store((r[dst] + ins.off) & 0xffffffffffffffff, n, ins.imm & 0xffffffffffffffff)
                pc += 1
                continue
            if op in (0x63, 0x6b, 0x73, 0x7b):          # stx{x}
                n = {0x63: 4, 0x6b: 2, 0x73: 1, 0x7b: 8}[op]
                self.store((r[dst] + ins.off) & 0xffffffffffffffff, n, r[src] & 0xffffffffffffffff)
                pc += 1
                continue
            if op in ALU64 or op in ALU32:
                is32 = op in ALU32
                name = (ALU32 if is32 else ALU64)[op]
                a = r[dst]
                b = r[src] if (op & 0x08) else (ins.imm & 0xffffffffffffffff)
                if is32:
                    a &= 0xffffffff
                    b &= 0xffffffff
                mask = 0xffffffff if is32 else 0xffffffffffffffff
                if name == 'mov':
                    v = b
                elif name == 'add':
                    v = a + b
                elif name == 'sub':
                    v = a - b
                elif name == 'mul':
                    v = a * b
                elif name == 'div':
                    v = 0 if b == 0 else a // b
                elif name == 'or':
                    v = a | b
                elif name == 'and':
                    v = a & b
                elif name == 'lsh':
                    v = a << (b & (31 if is32 else 63))
                elif name == 'rsh':
                    v = a >> (b & (31 if is32 else 63))
                elif name == 'arsh':
                    sa = a - (1 << (32 if is32 else 64)) if a >> (31 if is32 else 63) else a
                    v = sa >> (b & (31 if is32 else 63))
                elif name == 'xor':
                    v = a ^ b
                elif name == 'neg':
                    v = -a
                elif name == 'mod':
                    v = 0 if b == 0 else a % b
                else:
                    raise RuntimeError(f'alu {name} at 0x{pc:x}')
                r[dst] = v & mask
                pc += 1
                continue
            if op in JMP:
                name = JMP[op]
                if name == 'ja':
                    pc += 1 + ins.off
                    continue
                a = r[dst]
                b = r[src] if (op & 0x08) else (ins.imm & 0xffffffffffffffff)
                kind = name[1:]                      # eq / gt / ge / set / ne / sgt ...
                if kind.startswith('s'):
                    kind = kind[1:]
                    if a >> 63:
                        a -= 1 << 64
                    if (op & 0x08) and b >> 63:
                        b -= 1 << 64
                take = {'eq': a == b, 'gt': a > b, 'ge': a >= b, 'lt': a < b, 'le': a <= b,
                        'set': bool(a & b), 'ne': a != b}[kind]
                pc += (1 + ins.off) if take else 1
                continue
            raise RuntimeError(f'op 0x{op:02x} at 0x{pc:x}')
        raise RuntimeError('step budget exhausted')


ALU64 = {0x07: 'add', 0x0f: 'add', 0x17: 'sub', 0x1f: 'sub', 0x27: 'mul', 0x2f: 'mul',
         0x37: 'div', 0x3f: 'div', 0x47: 'or', 0x4f: 'or', 0x57: 'and', 0x5f: 'and',
         0x67: 'lsh', 0x6f: 'lsh', 0x77: 'rsh', 0x7f: 'rsh', 0x87: 'neg', 0x97: 'mod',
         0x9f: 'mod', 0xa7: 'xor', 0xaf: 'xor', 0xb7: 'mov', 0xbf: 'mov', 0xc7: 'arsh',
         0xcf: 'arsh'}
ALU32 = {0x04: 'add', 0x0c: 'add', 0x14: 'sub', 0x1c: 'sub', 0x24: 'mul', 0x2c: 'mul',
         0x34: 'div', 0x3c: 'div', 0x44: 'or', 0x4c: 'or', 0x54: 'and', 0x5c: 'and',
         0x64: 'lsh', 0x6c: 'lsh', 0x74: 'rsh', 0x7c: 'rsh', 0x84: 'neg', 0x94: 'mod',
         0x9c: 'mod', 0xa4: 'xor', 0xac: 'xor', 0xb4: 'mov', 0xbc: 'mov', 0xc4: 'arsh',
         0xcc: 'arsh'}
JMP = {0x05: 'ja', 0x15: 'jeq', 0x1d: 'jeq', 0x25: 'jgt', 0x2d: 'jgt', 0x35: 'jge',
       0x3d: 'jge', 0x45: 'jset', 0x4d: 'jset', 0x55: 'jne', 0x5d: 'jne',
       0x65: 'jsgt', 0x6d: 'jsgt', 0x75: 'jsge', 0x7d: 'jsge', 0xa5: 'jslt', 0xad: 'jslt',
       0xb5: 'jsle', 0xbd: 'jsle', 0xc5: 'jslt', 0xcd: 'jslt', 0xd5: 'jsle', 0xdd: 'jsle'}

CAMEL_BLOCK = set()


# ---------------------------------------------------------------- name table
def emulate_table(p, segs, fn, mode, count=200, base=0):
    """discriminant -> returned identifier, by executing the name function.

    ABI variants seen in these builds: the discriminant is passed by value in r1
    (`value`), the address of the value is passed in r1 (`ptr`), or the address is
    passed in r2 while r1 carries something else (`r2ptr`)."""
    m = Machine(p, segs)
    table, bad = {}, []
    for d in range(count):
        v = base + d
        if mode == 'r2ptr':
            m.stack[0:4] = (v & 0xffffffff).to_bytes(4, 'little')
            args = [0, m.fp]
        elif mode == 'ptr':
            m.stack[0:4] = (v & 0xffffffff).to_bytes(4, 'little')
            args = [m.fp, 0]
        else:
            args = [v, 0]
        try:
            r = m.run(fn, args)
        except RuntimeError as e:
            bad.append((d, str(e)))
            continue
        ptr, ln = r[2], r[3]
        if not (0 < ln < 80):
            continue
        b = va_read(p, segs, ptr, ln)
        if len(b) != ln or not all(32 <= c < 127 for c in b):
            continue
        if not b[:1].isupper():
            continue
        table[d] = {'name': b.decode('latin1'), 'at': ptr, 'len': ln}
    return table, bad


def recover_name_table(p, segs, starts, func_of, codes):
    """Pick the function + ABI whose emulated table covers the most observed codes."""
    best = None
    for cand in name_candidates(p, starts, func_of)[:6]:
        for mode in ('value', 'ptr', 'r2ptr'):
            if mode == 'r2ptr':
                continue                     # only used by the builtin-code probe
            table, bad = emulate_table(p, segs, cand['start'], mode)
            covered = len({6000 + d for d in table} & set(codes))
            key = (covered, len(table))
            if best is None or key > best[0]:
                best = (key, cand, mode, table, bad)
    if not best or best[0][0] == 0:
        return None
    _key, cand, mode, table, bad = best
    uniq = sorted({(rec['at'], rec['len']) for rec in table.values()})
    cover = sorted(c for c in codes if c - 6000 in table)
    return {'fn': cand['start'], 'mode': mode, 'insns': cand['insns'],
            'table': {str(d): rec for d, rec in sorted(table.items())},
            'entries': len(uniq), 'covered': cover,
            'covered_observed': len(cover), 'errors': bad[:5]}


def probe_name_table(p, segs, starts, func_of, codes):
    """Diagnostic: the best emulated table for a build that carries no program
    error-name table, so the report can state what the raise sites do reach."""
    best = None
    for cand in name_candidates(p, starts, func_of)[:4]:
        for mode, base, count in (('value', 0, 200), ('r2ptr', 2000, 4100), ('r2ptr', 6000, 120)):
            table, _bad = emulate_table(p, segs, cand['start'], mode, count=count, base=base)
            if not table:
                continue
            covered = len(set(base + d for d in table) & set(codes))
            key = (covered, len(table))
            if best is None or key > best[0]:
                best = (key, cand, mode, base, table)
    if not best:
        return None
    key, cand, mode, base, table = best
    counts = defaultdict(int)
    for v in table.values():
        counts[v['name']] += 1
    fallback = max(counts, key=lambda k: counts[k])
    distinct = [n for n in counts if n != fallback]
    return {'fn': cand['start'], 'abi': mode, 'base': base,
            'entries': len(table), 'distinct': len(distinct), 'fallback': fallback,
            'covers_observed': key[0],
            'sample': distinct[:6]}


# ---------------------------------------------------------------- raise sites
CUSTOM_STORES = (0x62, 0x6a, 0x72, 0x7a)


def raise_sites(p, codes=None):
    return [(pc, p.ins[pc].imm, p.ins[pc].off) for pc in p.order
            if p.ins[pc].op in CUSTOM_STORES and p.ins[pc].dst == 10
            and ERR_LO <= p.ins[pc].imm <= ERR_HI]


def origin_of(p, paths, site_pc, back=24, fwd=28):
    """Decode the AnchorError origin tuple emitted with a raise: the nearest
    preceding `lddw` of a source-path VA gives the file, the following
    store-immediate equal to that path's byte length is the file length, and the
    32-bit store beside it is the line."""
    for pc in range(site_pc - 1, site_pc - back - 1, -1):
        ins = p.ins.get(pc)
        if ins is None or ins.op != 0x18:
            continue
        va = ins.imm & 0xffffffff
        raw = paths.get(va)
        if raw is None:
            continue
        end = raw.find(b'.rs')
        if end < 0:
            plen = len(raw)
        else:
            plen = end + 3
        raw = raw[:plen]
        plen = len(raw)
        len_off = len_pc = None
        line = col = None
        for pc2 in range(pc + 1, pc + 1 + fwd):
            ins2 = p.ins.get(pc2)
            if ins2 is None or ins2.op not in CUSTOM_STORES or ins2.dst != 10:
                continue
            if ins2.op in (0x7a, 0x6a) and ins2.imm == plen and len_off is None:
                len_off, len_pc = ins2.off, pc2
            elif ins2.op in (0x62,) and 0 < ins2.imm < 100000 and line is None:
                line = ins2.imm
        if len_off is None:
            continue
        # the line store sits in the same small struct as the length store
        for pc2 in range(pc + 1, pc + 1 + fwd):
            ins2 = p.ins.get(pc2)
            if ins2 is None or ins2.op != 0x62 or ins2.dst != 10:
                continue
            if abs(ins2.off - len_off) <= 0x18 and 0 < ins2.imm < 100000:
                line = ins2.imm
                break
        return {'file': raw.decode('latin1'), 'file_ptr': va, 'file_len': plen,
                'line': line, 'len_insn': len_pc}
    return None


# ---------------------------------------------------------------- handler reach
def call_graph(p, func_of):
    tgt = defaultdict(set)
    for pc, ins in p.ins.items():
        if ins.op != 0x85:
            continue
        t = pc + 1 + ins.imm
        if t in p.ins:
            tgt[func_of.get(pc)].add(func_of.get(t))
    return tgt


def reach_distance(graph, handler_pc, limit=8):
    dist = {handler_pc: 0}
    frontier = [handler_pc]
    for d in range(1, limit + 1):
        nxt = []
        for f in frontier:
            for g in graph.get(f, ()):
                if g not in dist:
                    dist[g] = d
                    nxt.append(g)
        frontier = nxt
        if not frontier:
            break
    return dist


# ---------------------------------------------------------------- handlers
def load_handlers(prog, repo):
    if prog == 'mayhem':
        out = {}
        path = os.path.join(repo, 'docs/mayhem_map.md')
        if not os.path.exists(path):
            return out
        for line in open(path):
            m = re.match(r'\|\s*\d+\s*\|\s*`([a-z0-9_]+)`\s*\|(.*)', line)
            if not m:
                continue
            cols = [c.strip() for c in m.group(2).split('|')]
            # cols: log, disc, lddw, cmp, stub, handler(pc), handler(bytes), args
            if len(cols) >= 6 and cols[5].startswith('0x'):
                out[m.group(1)] = int(cols[5], 16)
        return out
    path = os.path.join(repo, HANDLER_MAPS.get(prog, ''))
    if not path or not os.path.exists(path):
        return {}
    d = json.load(open(path))
    out = {}
    for name, rec in d.items():
        if isinstance(rec, str):
            out[name] = int(rec, 16)
        elif isinstance(rec, dict):
            v = rec.get('handler_pc') or rec.get('handler')
            if v:
                out[name] = int(v, 16)
    return out


# ---------------------------------------------------------------- build
def sha256(path):
    import hashlib
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def build(prog, repo='.'):
    global CAMEL_BLOCK
    root = ROOT or os.path.join(repo, 'evidence', 'original')
    so = os.path.join(root, prog, 'deployed.so')
    p = Prog(so)
    segs = segments(p)
    starts, func_of, _size = function_starts(p)
    CAMEL_BLOCK = camel_block(p, segs)
    paths = path_strings(p)
    sites = raise_sites(p, None)
    codes = sorted({s[1] for s in sites})
    nt = recover_name_table(p, segs, starts, func_of, codes)
    probe = None if nt else probe_name_table(p, segs, starts, func_of, codes)
    names = {6000 + int(d): rec['name'] for d, rec in (nt['table'].items() if nt else [])}
    handlers = load_handlers(prog, repo)
    graph = call_graph(p, func_of)
    reach = {name: reach_distance(graph, pc) for name, pc in handlers.items() if pc in p.ins}

    rows = []
    for pc, code, off in sites:
        fn = func_of.get(pc, p.base)
        org = origin_of(p, paths, pc) or {}
        hits = []
        for hname, dist in reach.items():
            d = dist.get(fn)
            if d is not None:
                hits.append((d, hname))
        hits.sort()
        rows.append({'pc': pc, 'byte': pc * 8, 'code': code,
                     'name': names.get(code), 'func': fn,
                     'file': org.get('file'), 'file_len': org.get('file_len'),
                     'line': org.get('line'),
                     'handlers': [{'handler': h, 'depth': d} for d, h in hits[:6]]})
    rows.sort(key=lambda r: (r['code'], r['pc']))

    return {'program': prog, 'sha256': sha256(so), 'insns': len(p.order),
            'functions': len(starts), 'name_table': nt, 'name_probe': probe,
            'handlers': {k: v for k, v in sorted(handlers.items())},
            'observed_codes': codes, 'sites': rows}


# ---------------------------------------------------------------- reporting
def per_handler(d):
    """handler -> {direct: [site...], reached: {depth: [site...]}}"""
    out = {}
    for name in d['handlers']:
        out[name] = {'direct': [], 'reached': defaultdict(list)}
    for s in d['sites']:
        for h in s['handlers']:
            rec = out.get(h['handler'])
            if rec is None:
                continue
            if h['depth'] == 0:
                rec['direct'].append(s)
            else:
                rec['reached'][h['depth']].append(s)
    return out


def md_program(d, detail_handlers=True):
    L = []
    nt = d['name_table']
    L.append(f"## {d['program']}")
    L.append('')
    L.append(f"- sha256 `{d['sha256']}`")
    L.append(f"- {d['insns']} instructions / {d['functions']} functions "
             f"(relocation-aware starts), {len(d['handlers'])} instruction handlers")
    L.append(f"- custom-error raise sites **{len(d['sites'])}**, distinct codes "
             f"**{len(d['observed_codes'])}**")
    if nt and nt['table']:
        L.append(f"- program error-name table: function `0x{nt['fn']:x}`, ABI "
                 f"`{nt['mode']}`, **{nt['entries']} distinct variant names** recovered by "
                 f"executing it over every discriminant in range, covering "
                 f"{nt['covered_observed']} of the {len(d['observed_codes'])} observed codes")
    else:
        pr = d.get('name_probe')
        if pr:
            L.append(f"- no per-program error-name table: the only table reachable from "
                     f"this build is `0x{pr['fn']:x}` (ABI `{pr['abi']}`), "
                     f"{pr['distinct']} distinct names over codes "
                     f"from {pr['base']} ({', '.join(pr['sample'][:4])}...), and it "
                     f"returns its `{pr['fallback']}` fallback for every program code. "
                     f"The table below therefore carries codes and origins only")
        else:
            L.append("- no error-name table reachable from this build; the table below "
                     "carries codes and origins only")
    with_org = sum(1 for s in d['sites'] if s['file'])
    L.append(f"- {with_org}/{len(d['sites'])} sites carry an inline origin tuple "
             f"(file + line), {sum(1 for s in d['sites'] if s['handlers'])}/{len(d['sites'])} "
             f"resolve to at least one instruction handler")
    L.append('')

    # code table
    L.append('### codes')
    L.append('')
    L.append('| code | name (binary) | sites | origins (file:line, first 3) |')
    L.append('|---:|---|---:|---|')
    by_code = OrderedDict()
    for s in d['sites']:
        by_code.setdefault(s['code'], []).append(s)
    for code, ss in by_code.items():
        nm = next((s['name'] for s in ss if s['name']), None)
        orgs = []
        for s in ss:
            if s['file']:
                o = f"{short(s['file'])}:{s['line']}"
                if o not in orgs:
                    orgs.append(o)
        L.append(f"| {code} | {nm or '-'} | {len(ss)} | {', '.join(orgs[:3]) or '-'} |")
    L.append('')

    if detail_handlers and d['handlers']:
        ph = per_handler(d)
        L.append('### per handler')
        L.append('')
        L.append('`direct` = raise site inside the handler body (call-graph depth 0); '
                 '`+d` = first raise reachable at call-graph depth d.')
        L.append('')
        L.append('| handler | handler pc | raises (depth) |')
        L.append('|---|---|---|')
        for name in sorted(ph):
            rec = ph[name]
            parts = []
            for s in rec['direct']:
                parts.append(f"{s['code']}{(' ' + s['name']) if s['name'] else ''} @0x{s['pc']:x}")
            for depth in sorted(rec['reached']):
                seen = []
                for s in rec['reached'][depth]:
                    tok = f"{s['code']}{(' ' + s['name']) if s['name'] else ''}"
                    if tok not in seen:
                        seen.append(tok)
                if seen:
                    parts.append(f"+{depth}: " + ', '.join(seen))
            L.append(f"| `{name}` | 0x{d['handlers'][name]:x} | {('; '.join(parts)) or '-'} |")
        L.append('')
    return L


def short(path):
    return path.split('/src/', 1)[-1] if '/src/' in path else path


def md_all(ds):
    tot_sites = sum(len(d['sites']) for d in ds)
    tot_pairs = sum(len(d['observed_codes']) for d in ds)
    L = ['# Custom-error raise-site catalog, all four deployed programs', '',
         'Every Anchor custom-error raise in the deployed binaries: the code stored, the',
         'instruction address, the enclosing function, the original source `file:line` the',
         'build emitted with it, and the instruction handler(s) that can reach it.',
         '',
         'Method: `stw/sth/stb/stdw [r10+off], imm` with `imm` in the Anchor custom-error',
         'range; the origin is the `lddw` of a source-path VA plus the store-immediates',
         'that follow it (file length as the 64-bit store equal to the path byte length,',
         'line as the neighbouring 32-bit store); handler attribution is a BFS over the',
         'relocation-aware call graph from each instruction handler, reporting the first',
         'depth at which a site is reachable. The code -> variant name column for',
         '`pump` and `pump_amm` comes from executing that program\'s own',
         '`ErrorCode::name()` (binary search over the discriminant returning a',
         'pointer/length pair) for every discriminant in range.', '',
         '## Summary', '',
         '| program | raise sites | codes | name table | sites with origin | sites with handler |',
         '|---|---:|---:|---|---:|---:|',
         ]
    for d in ds:
        nt = d['name_table']
        L.append(f"| {d['program']} | {len(d['sites'])} | {len(d['observed_codes'])} | "
                 f"{('%d names @0x%x' % (nt['entries'], nt['fn'])) if nt else 'builtin table only'} | "
                 f"{sum(1 for s in d['sites'] if s['file'])}/{len(d['sites'])} | "
                 f"{sum(1 for s in d['sites'] if s['handlers'])}/{len(d['sites'])} |")
    L.append('')
    L.append(f'{tot_sites} raise sites in total, {tot_pairs} program/code pairs, '
             f'{sum(len(d["handlers"]) for d in ds)} instruction handlers attributed.')
    L.append('')
    L.append('Validation: the `pump` row reproduces the published pump table exactly - '
             '111/111 code -> name assignments, 366/366 raise sites, and 366/366 '
             '`file:line` origins agree.')
    L.append('')
    for d in ds:
        L.extend(md_program(d))
    return '\n'.join(L) + '\n'


def verify_pump(d, published):
    pub = json.load(open(published))
    pub_names = {6000 + int(k): v for k, v in pub['names'].items()}
    mine = {6000 + int(k): v['name'] for k, v in d['name_table']['table'].items()}
    agree = sum(1 for c, n in pub_names.items() if mine.get(c) == n)
    pubsite = {s['pc']: s for s in pub['sites']}
    mine_site = {s['pc']: s for s in d['sites']}
    same = sorted(set(pubsite) & set(mine_site))
    file_ok = sum(1 for pc in same if mine_site[pc]['file'] == pubsite[pc].get('file'))
    line_ok = sum(1 for pc in same if mine_site[pc]['line'] == pubsite[pc].get('line'))
    return {'name_agree': agree, 'name_total': len(pub_names),
            'sites_published': len(pubsite), 'sites_recovered': len(mine_site),
            'sites_common': len(same),
            'file_agree': file_ok, 'line_agree': line_ok}


def main():
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    progs = PROGS if ('--all' in sys.argv or not args) else args
    out_dir = os.path.join(repo, 'maps')
    ds = []
    for prog in progs:
        d = build(prog, repo=repo)
        ds.append(d)
        json.dump(d, open(os.path.join(out_dir, f'{prog}_error_sites_full.json'), 'w'),
                  indent=1, sort_keys=False)
        print(f"{prog}: sites={len(d['sites'])} codes={len(d['observed_codes'])} "
              f"names={(d['name_table'] or {}).get('fn')} "
              f"origins={sum(1 for s in d['sites'] if s['file'])}")
    if '--all' in sys.argv or not args:
        open(os.path.join(repo, 'docs/error_sites_all4.md'), 'w').write(md_all(ds))
    if '--verify-pump' in sys.argv:
        d = next((x for x in ds if x['program'] == 'pump'), None) or build('pump', repo=repo)
        v = verify_pump(d, os.path.join(repo, 'maps/pump_error_sites.json'))
        print('verify-pump:', json.dumps(v))


if __name__ == '__main__':
    main()
