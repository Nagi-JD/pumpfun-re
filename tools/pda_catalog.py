#!/usr/bin/env python3
"""PDA / seed catalog for the four deployed pump.fun programs.

For every PDA-derivation call the deployed code makes
(`sol_create_program_address`, `sol_try_find_program_address`) and every
PDA-signed CPI (`sol_invoke_signed_rust` / `sol_invoke_signed_c`), recover the
actual seed vector from the stack: Anchor builds a `SolBytes` array
`{addr: *const u8, len: u64}` in the frame, the literal parts are `lddw`s
carrying an `R_BPF_64_RELATIVE` relocation to `.rodata`, and the variable parts
are pointers into the frame (pubkeys loaded from accounts).

The recovery is mechanical, not ABI-guesswork: at each call site the argument
registers (r1..r5) are abstract-interpreted back to ("frame offset", "rodata VA",
"immediate") and the seed array is the `(base, n)` pair whose `n` 16-byte slots
all decode as `(literal-with-length | frame-pointer-with-length)`.

Read-only: opens the captured `deployed.so` files, never writes them.

Usage:
  pda_catalog.py json OUT.json
  pda_catalog.py md   OUT.md
  pda_catalog.py prog PROG        # stdout dump for one program
"""
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sbftool import Prog  # noqa: E402

REPO = os.path.dirname(HERE)
# The capture lives in a sibling checkout by default; override with
# PUMPFUN_EVIDENCE=/path/to/evidence/original.
ROOT = os.environ.get('PUMPFUN_EVIDENCE',
                      os.path.join(os.path.dirname(REPO), 'pumpfun-source',
                                   'evidence', 'original'))
PROGRAMS = ['pump', 'pump_amm', 'pump_fees', 'mayhem']

PDA_SYSCALLS = ('sol_create_program_address', 'sol_try_find_program_address')
SIGNED_SYSCALLS = ('sol_invoke_signed_rust', 'sol_invoke_signed_c')
INTERESTING = PDA_SYSCALLS + SIGNED_SYSCALLS

KNOWN_IDS = {
    '6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P': 'pump',
    'pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA': 'pump_amm',
    'pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ': 'pump_fees',
    'MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e': 'mayhem',
    'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA': 'spl_token',
    'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb': 'spl_token_2022',
    'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL': 'ata',
    'metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s': 'metaplex',
    '11111111111111111111111111111111': 'system',
    'RLAYHr9TRFcKB2ubYQhspcnXiaGpaVzNQvHytt47RZu': 'relay',
}

ALPHA = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
ST_IMM = {0x7a: 8, 0x62: 4, 0x6a: 2, 0x72: 1}
ST_REG = {0x7b: 8, 0x63: 4, 0x6b: 2, 0x73: 1}
LD = {0x61: 4, 0x69: 2, 0x71: 1, 0x79: 8}


def b58(data):
    n = int.from_bytes(data, 'big')
    out = ''
    while n:
        n, r = divmod(n, 58)
        out = ALPHA[r] + out
    pad = len(data) - len(data.lstrip(b'\0'))
    return '1' * pad + (out or '')


# ----------------------------------------------------------------- ELF plumbing
def sections(p):
    return [(nm, s[1], s[3], s[4], s[5]) for nm, s in p.secs]


def va_to_off(p, va):
    for nm, typ, addr, off, size in sections(p):
        if typ == 8 or size == 0:
            continue
        if addr <= va < addr + size:
            return nm, off + (va - addr)
    return None, None


def dynsym_names(p):
    ds, dss = p.sec.get('.dynsym'), p.sec.get('.dynstr')
    out = []
    if not ds or not dss:
        return out
    for k in range(ds[5] // 24):
        stn = struct.unpack_from('<I', p.b, ds[4] + k * 24)[0]
        out.append(p.b[dss[4] + stn:p.b.index(b'\0', dss[4] + stn)].decode('latin1'))
    return out


def load(path):
    """Reloc-aware load: apply .rel.dyn, exclude relocated call sites from the
    function starts, add e_entry back, bound the last function by the last
    decoded pc (the three sbftool.py corrections measured in PR #2)."""
    p = Prog(path)
    names = dynsym_names(p)
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
    p.call_sym, p.data_ptr = call_sym, data_ptr
    starts = {p.base}
    for pc, ins in p.ins.items():
        if ins.op != 0x85 or pc in call_sym:
            continue
        tgt = pc + 1 + ins.imm
        if tgt in p.ins:
            starts.add(tgt)
    entry = struct.unpack_from('<Q', p.b, 0x18)[0] // 8
    p.entry = entry if entry in p.ins else None
    if p.entry is not None:
        starts.add(p.entry)
    p.starts = sorted(starts)
    last = max(p.order) + 1
    p.func_of = {}
    for a, b in zip(p.starts, p.starts[1:] + [last]):
        for pc in range(a, b):
            if pc in p.ins:
                p.func_of[pc] = a
    p.last = last

    def func_body(start, _p=p, _last=last):
        nxt = [x for x in _p.starts if x > start]
        stop = nxt[0] if nxt else _last
        return [_p.ins[pc] for pc in range(start, stop) if pc in _p.ins]

    p.func_body = func_body
    return p


# --------------------------------------------------- abstract interpretation
def interp_to(p, start, stop_pc):
    """Walk one function start..stop_pc tracking
      regs:      reg -> ('fp', k) | ('rodata', va) | ('data', va) | ('imm', v) | None
      slot_ptr:  frame offset -> rodata/data VA stored there
      slot_fp:   frame offset -> frame offset whose address was stored there
      slot_imm:  frame offset -> stored immediate (u64)
    Caller-saved r0..r5 are clobbered at every call (the deployed code spills and
    reloads them, so this loses nothing it needs)."""
    regs = {10: ('fp', 0)}
    slot_ptr, slot_fp, slot_imm, slot_val = {}, {}, {}, {}
    for ins in p.func_body(start):
        if ins.pc >= stop_pc:
            break
        op = ins.op
        if op == 0x18:                                   # lddw
            if ins.pc in p.data_ptr:
                va = ins.imm & 0xffffffff
                snm, _ = va_to_off(p, va)
                regs[ins.dst] = ('rodata', va) if snm == '.rodata' else ('data', va)
            else:
                regs[ins.dst] = ('imm', ins.imm)
        elif op == 0xbf:
            regs[ins.dst] = regs.get(ins.src)
        elif op == 0xb7:
            regs[ins.dst] = ('imm', ins.imm)
        elif op == 0x07:
            v = regs.get(ins.dst)
            if v and v[0] == 'fp':
                regs[ins.dst] = ('fp', v[1] + ins.imm)
            elif v and v[0] == 'imm':
                regs[ins.dst] = ('imm', v[1] + ins.imm)
            else:
                regs[ins.dst] = None
        elif op == 0x0f:
            a, b = regs.get(ins.dst), regs.get(ins.src)
            if a and b and a[0] == 'fp' and b[0] == 'imm':
                regs[ins.dst] = ('fp', a[1] + b[1])
            else:
                regs[ins.dst] = None
        elif op in (0x85, 0x8d):                         # call / callx
            for r in range(6):
                regs[r] = None
            continue
        elif op in LD:
            regs[ins.dst] = None
        if op in ST_IMM or op in ST_REG:
            base = regs.get(ins.dst)
            if base and base[0] == 'fp':
                k = base[1] + ins.off
                if op in ST_REG:
                    v = regs.get(ins.src)
                    if v and v[0] in ('rodata', 'data'):
                        slot_ptr[k] = v[1]
                        slot_fp.pop(k, None)
                        slot_imm.pop(k, None)
                    elif v and v[0] == 'fp':
                        slot_fp[k] = v[1]
                        slot_ptr.pop(k, None)
                        slot_imm.pop(k, None)
                    elif v and v[0] == 'imm':
                        slot_imm[k] = v[1] & 0xffffffffffffffff
                        slot_ptr.pop(k, None)
                        slot_fp.pop(k, None)
                    else:
                        slot_ptr.pop(k, None)
                        slot_fp.pop(k, None)
                        slot_imm.pop(k, None)
                else:
                    slot_imm[k] = ins.imm & 0xffffffffffffffff
                    slot_ptr.pop(k, None)
                    slot_fp.pop(k, None)
    return regs, slot_ptr, slot_fp, slot_imm


def literal_at(p, va, ln):
    snm, off = va_to_off(p, va)
    if off is None or ln < 1 or ln > 64:
        return None
    raw = p.b[off:off + ln]
    if len(raw) != ln:
        return None
    if any(c < 0x20 or c > 0x7e for c in raw):
        return None
    return raw.decode('latin1')


def decode_seed_array(p, base, n, slot_ptr, slot_fp, slot_imm, allow_opaque=False):
    """Try to read an n-element SolBytes array at frame offset `base`.
    Returns a list of seed descriptors or None if the shape does not fit.
    With allow_opaque, a slot whose address register was lost (a value returned
    by a call, or an argument register) is kept as `opaque` as long as its length
    slot is an immediate - the count came from the ABI argument, so the shape is
    still authoritatively n elements."""
    seeds = []
    for i in range(n):
        a, l = base + 16 * i, base + 16 * i + 8
        ln = slot_imm.get(l)
        if ln is None or not (0 < ln <= 64):
            return None
        if a in slot_ptr:
            va = slot_ptr[a]
            lit = literal_at(p, va, ln)
            if lit is not None and re.match(r'^[A-Za-z0-9_\-:.$]+$', lit):
                seeds.append({'kind': 'literal', 'value': lit, 'len': ln,
                              'va': hex(va), 'rule': 'lddw+reloc'})
                continue
            snm, off = va_to_off(p, va)
            if ln == 32 and off is not None:
                raw = p.b[off:off + 32]
                if len(raw) == 32 and not all(0x20 <= c <= 0x7e for c in raw):
                    seeds.append({'kind': 'key', 'value': b58(raw), 'len': 32,
                                  'va': hex(va)})
                    continue
            return None
        elif a in slot_fp:
            seeds.append({'kind': 'frame', 'value': '<frame %+#x>' % slot_fp[a], 'len': ln})
        elif allow_opaque:
            seeds.append({'kind': 'opaque', 'value': '<?>', 'len': ln})
        else:
            return None
    return seeds


def seed_array_at_call(p, start, call_pc):
    regs, slot_ptr, slot_fp, slot_imm = interp_to(p, start, call_pc)
    args = {r: regs.get(r) for r in range(1, 6)}
    best = None
    # pass 1: an immediate argument names the seed count
    for rp, v in args.items():
        if not v or v[0] != 'fp':
            continue
        base = v[1]
        for rc, w in args.items():
            if rc == rp or not w or w[0] != 'imm':
                continue
            n = w[1]
            if not (1 <= n <= 8):
                continue
            seeds = decode_seed_array(p, base, n, slot_ptr, slot_fp, slot_imm,
                                      allow_opaque=True)
            if seeds is None:
                continue
            concrete = sum(1 for s in seeds if s['kind'] != 'opaque')
            if concrete == 0:
                continue        # shape fits but nothing was resolved: not evidence
            if best is None or concrete > best[0]:
                best = (concrete, rp, rc, base, n, seeds, 'arg-imm')
    # pass 2 (only if pass 1 failed): the count register is itself a value, so use
    # the array boundary - the largest n whose slots all decode and whose next
    # slot pair does not.
    if best is None:
        for rp, v in args.items():
            if not v or v[0] != 'fp':
                continue
            base = v[1]
            n = 0
            while n < 8 and decode_seed_array(p, base, n + 1, slot_ptr, slot_fp, slot_imm):
                n += 1
            if n < 1:
                continue
            seeds = decode_seed_array(p, base, n, slot_ptr, slot_fp, slot_imm)
            lit = sum(1 for s in seeds if s['kind'] == 'literal')
            if best is None or lit > best[0]:
                best = (lit, rp, None, base, n, seeds, 'boundary')
    # program id / extra pubkey args: a 32-byte constant, either .rodata or
    # materialised in the frame as four immediate words (what a hard-coded
    # program id compiles to).
    ids = []
    for r, v in args.items():
        if not v:
            continue
        raw = None
        if v[0] in ('rodata', 'data'):
            _, off = va_to_off(p, v[1])
            if off is not None:
                raw = p.b[off:off + 32]
                if len(raw) != 32 or all(0x20 <= c <= 0x7e for c in raw):
                    raw = None      # text, not a key
            src = 'rodata@%s' % hex(v[1])
        elif v[0] == 'fp':
            words = [slot_imm.get(v[1] + 8 * i) for i in range(4)]
            if any(w is None for w in words):
                continue
            raw = b''.join(struct.pack('<Q', w) for w in words)
            src = 'frame%+#x' % v[1]
        else:
            continue
        if raw is None or len(raw) != 32 or raw == b'\0' * 32:
            continue
        s = b58(raw)
        ids.append({'reg': 'r%d' % r, 'base58': s, 'known': KNOWN_IDS.get(s), 'from': src})
    if best is None:
        return None, ids, args
    _, rp, rc, base, n, seeds, src = best
    return {'frame_base': '%+#x' % base, 'count': n, 'ptr_reg': 'r%d' % rp,
            'count_reg': ('r%d' % rc) if rc else None, 'count_source': src,
            'seeds': seeds}, ids, args


# --------------------------------------------------------------- handler tables
def pump_handlers():
    d = json.load(open(os.path.join(REPO, 'maps', 'handlers.json')))
    return {k: int(v, 16) for k, v in d.items()}


def amm_handlers():
    full = os.path.join(REPO, 'maps', 'amm_handlers_full.json')
    if os.path.exists(full):
        d = json.load(open(full))
        return {k: int(v['handler_pc'], 16) for k, v in d.items()
                if isinstance(v, dict) and 'handler_pc' in v}
    d = json.load(open(os.path.join(REPO, 'maps', 'amm_handlers.json')))
    return {k: int(v, 16) for k, v in d.items()}


def fees_handlers():
    d = json.load(open(os.path.join(REPO, 'maps', 'fees_handlers.json')))
    out = {}
    for k, v in d.items():
        st = v.get('handler_pc', v.get('handler')) if isinstance(v, dict) else v
        if st:
            out[k] = int(st, 16)
    return out


def mayhem_handlers():
    """Handler-pc column of the table in docs/mayhem_map.md."""
    out = {}
    for line in open(os.path.join(REPO, 'docs', 'mayhem_map.md')):
        if not line.startswith('|'):
            continue
        cols = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cols) < 9:
            continue
        m = re.match(r'^`([a-z0-9_]+)`$', cols[1])
        if not m or not cols[7].startswith('0x'):
            continue
        out[m.group(1)] = int(cols[7], 16)
    return out


HANDLERS = {'pump': pump_handlers, 'pump_amm': amm_handlers,
            'pump_fees': fees_handlers, 'mayhem': mayhem_handlers}


# ------------------------------------------------------------------- the catalog
def analyse(prog):
    path = os.path.join(ROOT, prog, 'deployed.so')
    p = load(path)
    calls = dict(p.call_sym)

    internal = {}
    for pc, ins in p.ins.items():
        if ins.op != 0x85 or pc in p.call_sym:
            continue
        tgt = pc + 1 + ins.imm
        if tgt in p.ins:
            internal.setdefault(p.func_of.get(pc, p.base), set()).add(p.func_of.get(tgt, tgt))

    # The PDA syscalls live in tiny wrapper functions (one per syscall, mapping
    # the result to a Rust Result), so the seed array is built by the *caller* of
    # the wrapper. Resolve each syscall to its wrapper, then analyse every call
    # site that targets the wrapper.
    wrappers = {}
    derivs = []
    for pc in sorted(calls):
        nm = calls[pc]
        if nm not in INTERESTING:
            continue
        w = p.func_of.get(pc, p.base)
        wrappers.setdefault(w, nm)
        arr, ids, args = seed_array_at_call(p, w, pc)
        if arr is not None:
            derivs.append({'syscall': nm, 'wrapper': hex(w), 'insn': hex(pc),
                           'byte': hex(pc * 8), 'func': hex(w), 'via': 'direct',
                           'array': arr, 'progid_args': ids,
                           'arg_shapes': {('r%d' % r): (v[0] if v else None)
                                          for r, v in args.items()}})
    for w, nm in sorted(wrappers.items()):
        for pc, ins in sorted(p.ins.items()):
            if ins.op != 0x85 or pc in p.call_sym:
                continue
            tgt = pc + 1 + ins.imm
            if tgt != w or tgt not in p.ins:
                continue
            fn = p.func_of.get(pc, p.base)
            arr, ids, args = seed_array_at_call(p, fn, pc)
            derivs.append({'syscall': nm, 'wrapper': hex(w), 'insn': hex(pc),
                           'byte': hex(pc * 8), 'func': hex(fn), 'via': 'wrapper-call',
                           'array': arr, 'progid_args': ids,
                           'arg_shapes': {('r%d' % r): (v[0] if v else None)
                                          for r, v in args.items()}})

    handlers = HANDLERS[prog]()
    closure = {}
    for name, entry in sorted(handlers.items()):
        fn = p.func_of.get(entry, entry)
        seen, todo = set(), [fn]
        while todo:
            f = todo.pop()
            if f in seen:
                continue
            seen.add(f)
            for g in internal.get(f, ()):
                if g not in seen:
                    todo.append(g)
        closure[name] = seen

    per_handler = {}
    for name, seen in closure.items():
        mine = [d for d in derivs if int(d['func'], 16) in seen]
        direct = [d for d in derivs if int(d['func'], 16) == p.func_of.get(handlers[name], handlers[name])]
        per_handler[name] = {
            'entry': hex(handlers[name]),
            'entry_func': hex(p.func_of.get(handlers[name], handlers[name])),
            'derivations_reachable': len(mine),
            'derivations_direct': len(direct),
            'insns_reachable': sorted({d['insn'] for d in mine}),
        }

    return {
        'program': prog,
        'path': path,
        'text_bytes': p.tsize,
        'insns': len(p.order),
        'functions': len(p.starts),
        'call_sites': len(calls),
        'syscalls': sorted({calls[pc] for pc in calls}),
        'derivations': derivs,
        'handlers': per_handler,
        'handler_count': len(handlers),
    }


def build(progs=None):
    return {prog: analyse(prog) for prog in (progs or PROGRAMS)}


# ------------------------------------------------------------------------ output
def fmt_seeds(arr):
    if not arr:
        return '*(not recovered)*'
    out = []
    for s in arr['seeds']:
        if s['kind'] == 'literal':
            out.append('`%s`(%d)' % (s['value'], s['len']))
        elif s['kind'] == 'key':
            out.append('key:%s' % s['value'])
        else:
            out.append('%s(%d)' % (s['value'], s['len']))
    return ' + '.join(out)


def signature(arr):
    """Stable short signature of a seed vector: literal parts kept, dynamic parts
    collapsed to their kind and length."""
    if not arr:
        return None
    parts = []
    for s in arr['seeds']:
        if s['kind'] == 'literal':
            parts.append(s['value'])
        elif s['kind'] == 'key':
            parts.append('key:%s' % s['value'])
        elif s['kind'] == 'frame':
            parts.append('{%dB}' % s['len'])
        else:
            parts.append('<?>')
    return ' + '.join(parts)


def aggregate(cat):
    """Literal vocabulary and per-handler seed signatures across all programs."""
    vocab, keys = {}, {}
    for prog in PROGRAMS:
        for d in cat[prog]['derivations']:
            if not d['array']:
                continue
            owners = sorted({x['known'] for x in d['progid_args'] if x['known']})
            for s in d['array']['seeds']:
                if s['kind'] == 'key':
                    k = keys.setdefault(s['value'], {'sites': 0, 'programs': set(),
                                                     'vas': {}})
                    k['sites'] += 1
                    k['programs'].add(prog)
                    if s.get('va'):
                        k['vas'].setdefault(prog, s['va'])
                    continue
                if s['kind'] != 'literal':
                    continue
                v = vocab.setdefault(s['value'], {'len': s['len'], 'vas': {},
                                                  'sites': 0, 'programs': set(),
                                                    'owners': set()})
                v['sites'] += 1
                v['programs'].add(prog)
                v['owners'].update(owners)
                if s.get('va'):
                    v['vas'].setdefault(prog, s['va'])
    for v in vocab.values():
        v['programs'] = sorted(v['programs'])
        v['owners'] = sorted(v['owners'])
    for k in keys.values():
        k['programs'] = sorted(k['programs'])
    return vocab, keys


def md_report(cat):
    vocab, keys = aggregate(cat)
    L = []
    A = L.append
    A('# PDA / seed catalog (deployed programs)')
    A('')
    A('Read-only analysis of the captured `deployed.so` files. **[B]** = the seed literal')
    A('bytes, the `lddw`+`R_BPF_64_RELATIVE` site, the length immediates and the syscall')
    A('site are all in the deployed ELF; the seed *role* (which account the PDA is) is a')
    A('reading of the account resolution around the call. No behavioral MATCH is claimed.')
    A('')
    A('Method. `sbftool` decodes `.text` but not `.rel.dyn`; the loader here applies it')
    A('(`R_BPF_64_32` -> syscall name, `R_BPF_64_RELATIVE` -> the `lddw` whose low 32 bits')
    A('are the target VA), drops relocated call sites from the function starts, adds')
    A('`e_entry` back and bounds the last function by the last decoded pc (the corrections')
    A('measured in #2). For each PDA syscall the argument registers `r1..r5` are abstract-')
    A('interpreted from the enclosing function entry: a seed array is recognised as a')
    A('`(base, n)` pair where every one of the `n` 16-byte `SolBytes` slots decodes as')
    A('`{addr, len}` with `addr` a relocated `.rodata` pointer plus an immediate length (the')
    A('literal case) or a pointer into the frame (the variable case, e.g. a 32-byte pubkey).')
    A('Recognition therefore does not depend on the C ABI argument order, and a slot shape')
    A('that does not fit is rejected rather than guessed.')
    A('')
    A('Program ids are recovered when the derivation loads a 32-byte constant; the base58')
    A('value is given so the owning program is identified, not assumed.')
    A('')
    A('| program | insns | functions | PDA/signed sites | recovered vectors | unrecovered | handlers |')
    A('|---|---:|---:|---:|---:|---:|---:|')
    for prog in PROGRAMS:
        c = cat[prog]
        ok = sum(1 for d in c['derivations'] if d['array'])
        A(f"| {prog} | {c['insns']} | {c['functions']} | {len(c['derivations'])} | {ok} | "
          f"{len(c['derivations']) - ok} | {c['handler_count']} |")
    A('')
    A('## Seed / prefix vocabulary')
    A('')
    A('Every literal recovered as an element of a seed vector, with the number of sites that')
    A('load it, the programs whose code loads it, and the program ids recovered among the 32-byte')
    A('constant arguments of those calls. The program-id argument is one of them but the column')
    A('does not prove which: a call can also carry a second program id (e.g. a fees id in r1 next')
    A('to the ATA id in r4). Per-site argument shapes and registers are in `maps/pda_seeds.json`.')
    A('')
    A('| literal | len | rodata VA per program | sites | loaded by | program ids in args |')
    A('|---|---:|---|---:|---|---|')
    for lit in sorted(vocab):
        v = vocab[lit]
        vas = ', '.join('%s %s' % (p, v['vas'][p]) for p in sorted(v['vas']))
        A(f"| `{lit}` | {v['len']} | {vas} | {v['sites']} | "
          f"{', '.join(v['programs']) or '?'} | {', '.join(v['owners']) or 'not recovered'} |")
    A('')
    A('Addresses are virtual addresses inside *that* ELF, so they are only comparable')
    A('within one program.')
    A('')
    A('A 32-byte constant used *as a seed* is a key, not a prefix. These are the keys')
    A('recovered in that position (they are program ids, which is itself informative: a')
    A("program deriving another program's PDA needs its id as a seed):")
    A('')
    A('| key seed | rodata VA per program | sites | loaded by |')
    A('|---|---|---:|---|')
    for k in sorted(keys):
        v = keys[k]
        vas = ', '.join('%s %s' % (p, v['vas'][p]) for p in sorted(v['vas']))
        A(f"| `{k}` | {vas} | {v['sites']} | {', '.join(v['programs'])} |")
    A('')
    for prog in PROGRAMS:
        c = cat[prog]
        A(f'## {prog}')
        A('')
        A('### Derivation call sites and seed vectors')
        A('')
        A('`{32B}` = a seed byte string whose address is a frame slot (a pubkey or an')
        A('account field); the length is measured, not assumed. `-` in the program-id column')
        A('means no 32-byte constant argument was recovered at that site.')
        A('')
        A('| # | syscall | via | insn | byte | fn | seeds | program id | handlers reaching |')
        A('|---:|---|---|---:|---:|---:|---|---|---:|')
        for i, d in enumerate(c['derivations'], 1):
            ids = ', '.join('%s=%s(%s)' % (x['reg'], x['base58'], x['known'])
                            for x in d['progid_args'] if x['known']) or '-'
            reach = sum(1 for h in c['handlers'].values()
                        if d['insn'] in h['insns_reachable'])
            A(f"| {i} | `{d['syscall']}` | {d['via']} | {d['insn']} | {d['byte']} | "
              f"{d['func']} | {fmt_seeds(d['array'])} | {ids} | {reach} |")
        A('')
        A('### Handler -> derivations reachable (forward call closure)')
        A('')
        A('`body` = the derivation is inside the handler function itself; `closure` = it is')
        A('inside a helper the handler can reach. Signatures keep the literal parts and')
        A('collapse the dynamic ones to their length.')
        A('')
        A('| handler | entry | body | closure | seed signatures (body) |')
        A('|---|---|---:|---:|---|')
        for name, h in sorted(c['handlers'].items()):
            sigs = sorted({signature(d['array']) for d in c['derivations']
                           if d['array'] and d['insn'] in h['insns_reachable']
                           and int(d['func'], 16) == int(h['entry_func'], 16)})
            sigtxt = ', '.join('`%s`' % s for s in sigs) or '-'
            A(f"| `{name}` | {h['entry']} | {h['derivations_direct']} | "
              f"{h['derivations_reachable'] - h['derivations_direct']} | {sigtxt} |")
        A('')
    return '\n'.join(L) + '\n'


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    cmd, arg = sys.argv[1], sys.argv[2]
    if cmd == 'prog':
        c = analyse(arg)
        print(json.dumps(c, indent=1)[:400000])
        return
    cat = build()
    if cmd == 'json':
        json.dump(cat, open(arg, 'w'), indent=1)
        print('wrote', arg)
    elif cmd == 'md':
        open(arg, 'w').write(md_report(cat))
        print('wrote', arg)
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
