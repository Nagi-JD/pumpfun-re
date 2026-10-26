#!/usr/bin/env python3
"""trade_arg_frames - instruction-data frames of the deployed pump and pump_amm
programs, read from the bytes.

Anchor strips the 8-byte discriminator before dispatch, so every handler works
on a reader over the instruction bytes that follow it. This tool recovers, per
handler, what the deployed code does with that reader:

  * the reader regime: the handler frame itself (caller frame pointer in r5,
    reader at `[r5-0x1000]` / length at `[r5-0xff8]`) or a generated
    argument-deserialiser frame reached with `r2 = &mut &[u8]`;
  * every length gate the reader is held to (the immediates of the `jlt`/`jeq`
    taken against the remaining length);
  * every fixed-offset load off the reader pointer, with width and byte offset,
    merged into the byte spans the declared arguments occupy;
  * for Borsh `Vec`/`String`/`bytes` arguments: the `u32` length prefix load,
    the element cap and the element stride of the deserialiser;
  * the declared argument frame from the published IDL (Borsh, tightly
    packed), and which of its fields the bytes actually load.

Handlers are attributed through the DISPATCHER, not through a map column:
`disc = sha256("global:" + name)[:8]` is compared as a little-endian `lddw`
immediate followed by a register-form `jeq` (op 0x1d); the branch reaches a
stub that calls or jumps to the handler body.

Evidence only: every figure is an instruction index in the deployed ELF
(`insn = byte_offset / 8`).

Usage:
  python3 tools/trade_arg_frames.py --prog pump
  python3 tools/trade_arg_frames.py --prog pump --json maps/pump_arg_frames.json
  python3 tools/trade_arg_frames.py --prog pump_amm --json maps/pump_amm_arg_frames.json
  python3 tools/trade_arg_frames.py --doc docs/arg_frames_pump_pump_amm.md
  python3 tools/trade_arg_frames.py --prog pump --verify
"""
import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fees_prog import load  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EVIDENCE = os.environ.get('PUMPFUN_EVIDENCE', os.path.join(
    os.path.dirname(ROOT), 'pumpfun-source', 'evidence', 'original'))
IDL_DIR = os.environ.get('PUMPFUN_IDL', os.path.join(
    os.path.dirname(ROOT), 'pumpfun-source', 'evidence', 'upstream'))

PROGRAMS = ('pump', 'pump_amm')

# sBPF v1 opcodes
LD = {0x61: 4, 0x69: 2, 0x71: 1, 0x79: 8}          # ldxw / ldxh / ldxb / ldxdw
MOV_I, MOV_R, ADD_I, ADD_R, SUB_I, MUL_I = 0xb7, 0xbf, 0x07, 0x0f, 0x17, 0x27
LDDW, CALL, EXIT, JA = 0x18, 0x85, 0x95, 0x05
# jumps carry the displacement in `off`; `imm` is the comparison constant
JMP = {0x05, 0x15, 0x1d, 0x25, 0x2d, 0x35, 0x3d, 0x45, 0x4d, 0x55, 0x5d,
       0x65, 0x6d, 0x75, 0x7d, 0xa5, 0xad, 0xb5, 0xbd, 0xc5, 0xcd, 0xd5, 0xdd}
STORE_OPS = (0x62, 0x6a, 0x72, 0x7a, 0x63, 0x6b, 0x73, 0x7b)
DEBUG = set()


def elf_sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def frame_list(p, start):
    """Instructions of one reloc-aware frame, in pc order (cached per program)."""
    if not hasattr(p, '_bodies'):
        bodies = {}
        for pc in sorted(p.ins):
            s = p.func_of.get(pc)
            if s is not None:
                bodies.setdefault(s, []).append(p.ins[pc])
        p._bodies = bodies
    return p._bodies.get(start, [])


def find_reader_base(body):
    """Which register carries the reader descriptor, and in which regime."""
    for ins in body:
        if ins.op == 0x79 and ins.off == -0xff8:
            return ins.src, 'owned'
        if ins.op == 0x79 and ins.off == -0x1000:
            return ins.src, 'owned'
    return None, None


def trace(body, base_reg, regime):
    """Symbolic dataflow over one frame, following both sides of every branch.

    Register values:
      ('D',)          reader descriptor base
      ('P', delta)    reader pointer + delta  (delta None once the reader moved)
      ('L',)          reader length / remaining length
      ('C', v)        constant
      ('F', off)      frame pointer + off
    """
    ins_by_pc = {ins.pc: ins for ins in body}
    order = [ins.pc for ins in body]
    nx = {pc: (order[k + 1] if k + 1 < len(order) else None) for k, pc in enumerate(order)}
    reads, gates, muls, len32, advances = [], [], [], [], []
    ptr_slots, helper_calls = [], []
    fp_reader = {}
    seen = {}

    def join(a, b):
        if a is None:
            return dict(b)
        if b is None:
            return dict(a)
        return {r: v for r, v in a.items() if b.get(r) == v}

    work = [(order[0], {base_reg: ('D',), 10: ('F', 0)})] if order else []
    while work:
        pc, st = work.pop()
        ins = ins_by_pc.get(pc)
        if ins is None:
            continue
        if DEBUG and pc in DEBUG:
            print('[debug] visit', hex(pc), sorted((r, v) for r, v in st.items()))
        if pc in seen:
            j = join(seen[pc], st)
            if j == seen[pc]:
                continue
            seen[pc] = j
            st = j
        else:
            seen[pc] = dict(st)
        dst, src, off = ins.dst, ins.src, ins.off
        out = dict(st)
        succ = []
        if ins.op == EXIT:
            succ = []
        elif ins.op == CALL:
            v = out.get(2)
            if v and v[0] == 'F':
                tgt = pc + 1 + ins.imm
                if tgt != pc:
                    helper_calls.append({'pc': hex(pc), 'target': hex(tgt), 'slot': v[1],
                                         'delta': fp_reader.get(v[1])})
                    if v[1] in fp_reader:
                        fp_reader[v[1]] = None      # the callee advances it
            elif v and v[0] == 'D':
                tgt = pc + 1 + ins.imm
                if tgt != pc:
                    helper_calls.append({'pc': hex(pc), 'target': hex(tgt), 'slot': None,
                                         'delta': None})
            for r in (0, 1, 2):
                out.pop(r, None)
            n = nx.get(pc)
            succ = [n] if n is not None else []
        elif ins.op in JMP:
            tgt = pc + 1 + ins.off
            if ins.op == 0x05:
                succ = [tgt if tgt in ins_by_pc else None]
            else:
                v = out.get(dst)
                if v and v[0] == 'L':
                    gates.append({'pc': hex(pc), 'op': ins.mn, 'imm': ins.imm})
                succ = [nx.get(pc), tgt if tgt in ins_by_pc else None]
            succ = [s for s in succ if s is not None]
        elif ins.op in LD:
            w = LD[ins.op]
            v = out.get(src)
            if v is None:
                out.pop(dst, None)
            elif v[0] == 'F' and (v[1] + off) in fp_reader:
                out[dst] = ('P', fp_reader[v[1] + off])
            elif v[0] == 'D':
                if regime == 'owned':
                    if ins.op == 0x79 and off == -0x1000:
                        out[dst] = ('P', 0)
                    elif ins.op == 0x79 and off == -0xff8:
                        out[dst] = ('L',)
                    else:
                        out.pop(dst, None)
                else:                                   # &mut &[u8] in r2
                    if ins.op == 0x79 and off == 0:
                        out[dst] = ('P', 0)
                    elif ins.op == 0x79 and off == 8:
                        out[dst] = ('L',)
                    else:
                        out.pop(dst, None)
            elif v[0] == 'P':
                delta = None if v[1] is None else v[1] + off
                reads.append({'off': delta, 'width': w, 'pc': hex(pc), 'op': ins.mn})
                out.pop(dst, None)
            elif v[0] == 'L':
                if ins.op == 0x61 and off == 0:
                    len32.append({'pc': hex(pc)})
                out.pop(dst, None)
            else:
                out.pop(dst, None)
            n = nx.get(pc)
            succ = [n] if n is not None else []
        elif ins.op == MOV_I:
            out[dst] = ('C', ins.imm)
            n = nx.get(pc)
            succ = [n] if n is not None else []
        elif ins.op == MOV_R:
            if src == 10:
                out[dst] = ('F', 0)
            elif src in out:
                out[dst] = out[src]
            elif dst == base_reg:
                out[dst] = ('D',)
            else:
                out.pop(dst, None)
            n = nx.get(pc)
            succ = [n] if n is not None else []
        elif ins.op in (ADD_I, SUB_I):
            k = ins.imm if ins.op == ADD_I else -ins.imm
            v = out.get(dst)
            if v and v[0] == 'C':
                out[dst] = ('C', v[1] + k)
            elif v and v[0] == 'P':
                out[dst] = ('P', None if v[1] is None else v[1] + k)
            elif v and v[0] == 'F':
                out[dst] = ('F', v[1] + k)
            else:
                out.pop(dst, None)
            n = nx.get(pc)
            succ = [n] if n is not None else []
        elif ins.op == MUL_I:
            v = out.get(dst)
            if v and v[0] == 'C':
                muls.append({'pc': hex(pc), 'imm': ins.imm})
                out[dst] = ('C', v[1] * ins.imm)
            else:
                muls.append({'pc': hex(pc), 'imm': ins.imm})
                out.pop(dst, None)
            n = nx.get(pc)
            succ = [n] if n is not None else []
        elif ins.op == LDDW:
            out.pop(dst, None)
            n = nx.get(pc)
            succ = [n] if n is not None else []
        elif ins.op in STORE_OPS:
            v = out.get(dst)
            if v and v[0] == 'D':
                val = out.get(src) if ins.op & 0x3 == 3 else None
                if val and val[0] == 'P' and val[1]:
                    advances.append({'pc': hex(pc), 'store_off': off})
            if v and v[0] == 'F' and ins.op & 0x3 == 3:
                val = out.get(src)
                if val and val[0] == 'P':
                    ptr_slots.append({'fp_slot': v[1] + off, 'pc': hex(pc),
                                      'delta': val[1]})
                    fp_reader[v[1] + off] = val[1]
            n = nx.get(pc)
            succ = [n] if n is not None else []
        else:
            out.pop(dst, None)
            n = nx.get(pc)
            succ = [n] if n is not None else []
        for s in succ:
            work.append((s, out))
    return {'reads': reads, 'gates': gates, 'muls': muls, 'len32': len32,
            'advances': advances, 'ptr_slots': ptr_slots, 'helper_calls': helper_calls}


def resolve_deserialiser(p, handler_tr, max_depth=4):
    """Follow the `&mut &[u8]` reference from the handler frame into the frame
    that actually loads argument bytes. Returns (frame, chain, trace, base) or
    None.

    `base` is the reader offset the handler had already consumed when it passed
    the descriptor, so the loads inside the deserialiser frame sit at
    `base + off` in the instruction-data frame.
    """
    queue = []
    slots = {s['fp_slot'] for s in handler_tr['ptr_slots']}
    for h in handler_tr['helper_calls']:
        if h['slot'] is None or h['slot'] in slots or h['slot'] + 8 in slots:
            queue.append((int(h['target'], 16), 0, [h['pc']], h.get('delta')))
    seen = set()
    while queue:
        tgt, depth, chain, base = queue.pop(0)
        if tgt in seen or depth > max_depth or tgt not in p.ins:
            continue
        seen.add(tgt)
        hb = frame_list(p, tgt)
        tr = trace(hb, 2, 'byref')
        if tr['reads']:
            return tgt, chain, tr, base
        inner = {s['fp_slot'] for s in tr['ptr_slots']}
        for h in tr['helper_calls']:
            if h['slot'] is None or h['slot'] in inner or h['slot'] + 8 in inner:
                queue.append((int(h['target'], 16), depth + 1, chain + [h['pc']],
                              base if h.get('delta') is None else base + h['delta']
                              if base is not None else None))
    return None


# ------------------------------------------------------------------ dispatcher
def dispatch_entries(p, idl):
    """Every IDL instruction resolved to its handler through the dispatcher."""
    disc2name = {}
    for ix in idl['instructions']:
        d = hashlib.sha256(('global:' + ix['name']).encode()).digest()[:8]
        disc2name[d] = ix['name']
    order = sorted(p.ins)
    pos = {pc: k for k, pc in enumerate(order)}
    out, seen = [], set()
    for pc in order:
        ins = p.ins[pc]
        if ins.op != LDDW:
            continue
        raw = (ins.imm & 0xffffffffffffffff).to_bytes(8, 'little')
        name = disc2name.get(raw)
        if name is None or name in seen:
            continue
        k = pos[pc]
        cmp_pc = cmp_off = None
        for j in range(k + 1, min(k + 5, len(order))):
            jins = p.ins[order[j]]
            if jins.op == 0x1d:                     # reg-form jeq
                cmp_pc, cmp_off = jins.pc, jins.off
                break
        if cmp_pc is None:
            continue
        stub = cmp_pc + 1 + cmp_off
        tgt = stub
        for q in range(stub, stub + 40):
            qins = p.ins.get(q)
            if qins is None:
                continue
            if qins.op == CALL and q not in p.call_sym:
                tgt = q + 1 + qins.imm
                break
            if qins.op == JA:
                tgt = q + 1 + qins.off
                break
        seen.add(name)
        out.append({'name': name, 'disc': raw.hex(), 'lddw_pc': hex(pc),
                    'cmp_pc': hex(cmp_pc), 'stub': hex(stub), 'handler_pc': hex(tgt)})
    return sorted(out, key=lambda r: int(r['handler_pc'], 16))


# --------------------------------------------------------------- declared args
FIXED = {'bool': 1, 'u8': 1, 'i8': 1, 'u16': 2, 'i16': 2, 'u32': 4, 'i32': 4,
         'u64': 8, 'i64': 8, 'u128': 16, 'i128': 16, 'pubkey': 32}
OPTIONS = {'OptionBool': 1, 'OptionU64': 8}          # newtype structs: tag + payload


def arg_shape(t):
    """('fixed', bytes) | ('opt', payload bytes) | ('var', None) for a Borsh type."""
    if isinstance(t, str):
        if t in ('string', 'bytes'):
            return 'var', None
        sz = FIXED.get(t)
        return ('fixed', sz) if sz is not None else ('var', None)
    if 'defined' in t:
        n = t['defined']['name']
        if n in OPTIONS:
            return 'opt', OPTIONS[n]
        return 'var', None
    if 'array' in t:
        inner, n = t['array']
        kind, sz = arg_shape(inner)
        return ('fixed', sz * n) if kind == 'fixed' else ('var', None)
    return 'var', None                                # vec / option / any


def expected_frame(args):
    """The Borsh frame the declared arguments imply; Borsh does not pad.

    An `Option` contributes its tag byte and, on the `Some` path, its payload;
    only the tag is placed, so a handler that loads the payload keeps its
    measured offset. Once a variable-length argument is reached every later
    offset is run-time only.
    """
    out, off = [], 0
    for a in args:
        kind, sz = arg_shape(a['type'])
        if kind == 'fixed':
            out.append({'name': a['name'], 'type': a['type'], 'off': off,
                        'size': sz, 'kind': 'fixed'})
            if off is not None:
                off += sz
        elif kind == 'opt':
            out.append({'name': a['name'], 'type': a['type'], 'off': off,
                        'size': 1, 'payload': sz, 'kind': 'opt'})
            if off is not None:
                off += 1                                      # the tag
        else:
            out.append({'name': a['name'], 'type': a['type'], 'off': off,
                        'size': None, 'kind': 'var'})
            off = None
    return out


def spans(reads):
    """Merge the byte loads off the reader into maximal contiguous spans."""
    rs = sorted({(r['off'], r['off'] + r['width']) for r in reads if r['off'] is not None})
    out = []
    for a, b in rs:
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b - a) for a, b in out]


def find_caps(body):
    """Borsh length prefixes: the element cap that precedes the stride multiply,
    and the byte cap a String / byte-vector reader applies."""
    caps = []
    for k, ins in enumerate(body):
        if ins.mn not in ('jlt', 'jle') or ins.imm <= 0:
            continue
        for j in range(k + 1, min(k + 5, len(body))):
            nxt = body[j]
            if nxt.op == MUL_I:
                caps.append({'cap': ins.imm, 'stride': nxt.imm,
                             'gate_pc': hex(ins.pc), 'mul_pc': hex(nxt.pc),
                             'bytes': ins.imm * nxt.imm})
                break
            if nxt.mn in ('jlt', 'jle', 'ja'):
                break
        if ins.imm >= 0x10000:
            caps.append({'cap': ins.imm, 'stride': None, 'gate_pc': hex(ins.pc),
                         'mul_pc': None, 'bytes': None})
    return caps


# ------------------------------------------------------------------- per program
def analyse(prog):
    p = load(os.path.join(EVIDENCE, prog, 'deployed.so'))
    idl = json.load(open(os.path.join(IDL_DIR, prog + '.json')))
    idl_by = {i['name']: i for i in idl['instructions']}
    entries = dispatch_entries(p, idl)
    if len(entries) != len(idl['instructions']):
        print('WARNING %s: %d of %d IDL instructions resolved through the dispatcher'
              % (prog, len(entries), len(idl['instructions'])))

    out = {}
    for e in entries:
        name, start = e['name'], int(e['handler_pc'], 16)
        body = frame_list(p, start)
        base, regime = find_reader_base(body)
        declared = [{'name': x['name'], 'type': x['type']}
                    for x in idl_by.get(name, {}).get('args', [])]
        rec = {'handler_pc': e['handler_pc'], 'stub': e['stub'], 'disc': e['disc'],
               'lddw_pc': e['lddw_pc'], 'cmp_pc': e['cmp_pc'], 'insns': len(body),
               'args_declared': declared, 'levels': [],
               'reader': 'none', 'reads': [], 'gates': [], 'muls': [], 'len32': [],
               'advances': [], 'caps': []}
        tr_handler = {'reads': [], 'gates': [], 'muls': [], 'len32': [], 'advances': [],
                      'ptr_slots': [], 'helper_calls': []}
        if base is not None:
            tr_handler = trace(body, base, regime)
            rec['reader'] = {'kind': 'own', 'reg': base}
        levels = [{'frame': 'handler', 'insns': len(body), 'base': 0,
                   'reads': tr_handler['reads'], 'gates': tr_handler['gates'],
                   'muls': tr_handler['muls'], 'caps': []}]
        tr = tr_handler
        found = resolve_deserialiser(p, tr_handler)
        if found is not None:
            tgt, chain, trh, hbase = found
            rec['reader'] = {'kind': 'helper', 'frame': hex(tgt),
                             'insns': len(frame_list(p, tgt)), 'chain': chain,
                             'base': hbase, 'tail_reads': len(tr_handler['reads'])}
            hcaps = find_caps(frame_list(p, tgt))
            levels.append({'frame': hex(tgt), 'insns': len(frame_list(p, tgt)),
                           'base': hbase, 'reads': trh['reads'], 'gates': trh['gates'],
                           'muls': trh['muls'], 'caps': hcaps})
            rec['caps'] = hcaps
            tr = {k: trh[k] + tr_handler[k]
                  for k in ('reads', 'gates', 'muls', 'len32', 'advances')}
        elif base is not None:
            rec['caps'] = find_caps(body)
            levels[0]['caps'] = rec['caps']
        # per level: absolute offsets, so a load in a deserialiser frame that was
        # handed an already advanced reader lands where the frame puts it
        for lv in levels:
            for r in lv['reads']:
                r['frame'] = lv['frame']
                if r['off'] is not None and lv['base'] is not None:
                    r['off'] += lv['base']
            for g in lv['gates']:
                g['frame'] = lv['frame']
        rec['levels'] = [{'frame': lv['frame'], 'insns': lv['insns'], 'base': lv['base'],
                          'reads': sorted(lv['reads'], key=lambda x: (x['off'] if x['off'] is not None else -1, x['pc'])),
                          'gates': lv['gates'], 'muls': lv['muls'], 'caps': lv['caps']}
                         for lv in levels]
        for k in ('reads', 'gates', 'muls', 'len32', 'advances'):
            ded = {json.dumps(x, sort_keys=True): x for x in tr[k]}
            rec[k] = sorted(ded.values(),
                            key=lambda x: (x.get('off') if x.get('off') is not None else -1, x['pc']))
        rec['unplaced_reads'] = [r for r in rec['reads'] if r['off'] is None]
        exp = expected_frame(declared)
        rec['args_expected'] = exp
        rec['spans'] = [{'off': o, 'width': w} for o, w in spans(rec['reads'])]
        cov = set()
        for s in rec['spans']:
            cov.update(range(s['off'], s['off'] + s['width']))
        placed = [e2 for e2 in exp if e2['off'] is not None and e2['size'] is not None]
        varf = [e2 for e2 in exp if e2['size'] is None]
        prefix_end = max([e2['off'] + e2['size'] for e2 in placed], default=0)
        if not declared:
            rec['frame_check'] = ('no arguments declared, reader untouched'
                                  if not rec['reads'] else 'no arguments declared, reader read')
        elif not rec['reads']:
            rec['frame_check'] = 'no argument bytes loaded'
        else:
            unloaded = ['%s@%d+%d' % (f['name'], f['off'], f['size'])
                        for f in placed
                        if not set(range(f['off'], f['off'] + f['size'])) <= cov]
            rec['fields_unloaded'] = unloaded
            n_unp = len(rec['unplaced_reads'])
            parts = ['%d B measured' % (max((s['off'] + s['width'] for s in rec['spans']), default=0))]
            if unloaded and not n_unp:
                parts.append('not loaded: ' + ', '.join(unloaded))
            elif unloaded:
                parts.append('%d field(s) after a reader advance: %s'
                             % (len(unloaded), ', '.join(f.split('@')[0] for f in unloaded)))
            if varf:
                parts.append('%d variable-length argument(s)' % len(varf))
            if n_unp:
                parts.append('%d load(s) after a reader advance' % n_unp)
            if not unloaded and not varf and not n_unp:
                parts.append('all declared fields loaded')
            rec['frame_check'] = ', '.join(parts)
        out[name] = rec
    return p, idl, entries, out


def summary(prog, out):
    own = [n for n, r in out.items() if isinstance(r['reader'], dict) and r['reader']['kind'] == 'own']
    deleg = [n for n, r in out.items() if isinstance(r['reader'], dict) and r['reader']['kind'] == 'helper']
    none = [n for n, r in out.items() if r['reader'] == 'none']
    frames = {}
    for n, r in out.items():
        if isinstance(r['reader'], dict) and r['reader']['kind'] == 'helper':
            frames.setdefault(r['reader']['frame'], []).append(n)
    s = {
        'prog': prog, 'handlers': len(out),
        'own': len(own), 'owned_handlers': sorted(own),
        'delegated': len(deleg), 'delegated_frames': {k: sorted(v) for k, v in sorted(frames.items())},
        'untouched': len(none), 'untouched_handlers': sorted(none),
        'gates': sum(len(r['gates']) for r in out.values()),
        'reads': sum(len(r['reads']) for r in out.values()),
        'frames_with_args': sum(1 for r in out.values() if r['args_declared']),
        'checks': {},
        'caps': [dict(c, handler=n) for n, r in out.items() for c in r['caps']],
        'len32': [dict(c, handler=n) for n, r in out.items() for c in r['len32']],
    }
    for r in out.values():
        s['checks'][r['frame_check'].split(':')[0]] = s['checks'].get(r['frame_check'].split(':')[0], 0) + 1
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prog', choices=sorted(PROGRAMS))
    ap.add_argument('--json')
    ap.add_argument('--doc')
    ap.add_argument('--verify', action='store_true')
    ap.add_argument('--only')
    ap.add_argument('--summary', action='store_true')
    a = ap.parse_args()

    progs = [a.prog] if a.prog else list(PROGRAMS)
    allout, allsum = {}, {}
    for prog in progs:
        p, idl, entries, out = analyse(prog)
        if a.only:
            out = {k: v for k, v in out.items() if k == a.only}
        allout[prog] = out
        allsum[prog] = summary(prog, out)
        allsum[prog]['elf_sha256'] = elf_sha(os.path.join(EVIDENCE, prog, 'deployed.so'))
        if a.json:
            path = a.json if a.prog else 'maps/%s_arg_frames.json' % prog
            meta = dict(allsum[prog])
            meta.pop('owned_handlers', None)
            meta.pop('untouched_handlers', None)
            meta['idl'] = os.path.basename(os.path.join(IDL_DIR, prog + '.json'))
            with open(path, 'w') as f:
                json.dump({'_program': meta, **out}, f, indent=1, sort_keys=True)
            print('wrote', path)
        if a.verify:
            prev = json.load(open(os.path.join(ROOT, 'maps', '%s_arg_frames.json' % prog)))
            prev.pop('_program', None)
            bad = [n for n in out if prev.get(n) != out[n]]
            print('verify %s: %d/%d handlers reproduce the recorded frames'
                  % (prog, len(out) - len(bad), len(out)))
            if bad:
                print('  MISMATCH', ', '.join(bad))
        if a.summary:
            s = allsum[prog]
            print('=== %s: %d handlers, %d own-frame, %d delegated, %d untouched'
                  % (prog, s['handlers'], s['own'], s['delegated'], s['untouched']))
            print('  delegated frames:', json.dumps(s['delegated_frames']))
            print('  checks:', json.dumps(s['checks']))
            print('  gates %d reads %d' % (s['gates'], s['reads']))
            for c in s['caps']:
                print('  cap', c)
            print('  len32 sites:', len(s['len32']))

    if a.doc:
        import trade_arg_frames_doc
        with open(a.doc, 'w') as f:
            f.write(trade_arg_frames_doc.render(allout, allsum))
        print('wrote', a.doc)
    if a.summary:
        json.dump(allsum, open('/tmp/arg_frames_summary.json', 'w'), indent=1)
        print('summary -> /tmp/arg_frames_summary.json')


if __name__ == '__main__':
    main()
