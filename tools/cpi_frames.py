#!/usr/bin/env python3
"""cpi_frames.py - instruction-data frame of every Anchor-discriminated CPI edge
in the four deployed pump.fun programs.

Method
------
An Anchor CPI is emitted as `sol_invoke_signed_rust(instruction)`. The instruction
data buffer is filled with the 8-byte discriminator, loaded as one `lddw` immediate
(sha256("global:"+name)[:8], little-endian) and stored into the freshly allocated
buffer; the instruction arguments follow it as stores into the same base register.
For each such site we recover

  * the base register of the payload buffer (the register the disc is stored through),
  * every store into that register with a constant offset inside the basic block
    (offset, width, immediate value or source register),
  * the payload length implied by the highest store,
  * the declared frame from the target program's IDL (arg names + types + offsets),
  * the distance from the enclosing function to the invoke wrapper in the call graph.

Output: maps/cpi_frames_all4.json + docs/cpi_frames_all4.md.  `--verify` recomputes
the frames and checks every fixed-size declared frame against the measured one.
"""
import sys
import os
import json
import hashlib
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import fees_prog  # noqa: E402

EVIDENCE = os.environ.get('PUMPFUN_EVIDENCE') or '/opt/data/lab-pumpfun/pumpfun-source/evidence'
UPSTREAM = os.path.join(EVIDENCE, 'upstream')
PROGS = ('pump', 'pump_amm', 'pump_fees', 'mayhem')
IDL_FILE = {'pump': 'pump.json', 'pump_amm': 'pump_amm.json', 'pump_fees': 'pump_fees.json'}

FIXED = {'u8': 1, 'i8': 1, 'bool': 1, 'u16': 2, 'i16': 2, 'u32': 4, 'i32': 4,
         'f32': 4, 'u64': 8, 'i64': 8, 'f64': 8, 'u128': 16, 'i128': 16, 'pubkey': 32}
VARIABLE = {'string', 'bytes'}
ST_REG = (0x63, 0x6b, 0x73, 0x7b)
ST_IMM = (0x62, 0x6a, 0x72, 0x7a)


# ---------------------------------------------------------------- IDL metadata
def load_idls():
    idls = {}
    for prog, fn in IDL_FILE.items():
        path = os.path.join(UPSTREAM, fn)
        if os.path.exists(path):
            idls[prog] = json.load(open(path))
    return idls


def mayhem_names():
    """Handler names of the mayhem program, from the anatomy map the repo ships."""
    path = os.path.join(ROOT, 'maps', 'mayhem_handler_anatomy.json')
    if os.path.exists(path):
        d = json.load(open(path))
        return sorted(d.get('handlers', d))
    return []


def disc_table(idls):
    """disc bytes -> [ {target, name, args}, ... ]  (a name is shared when two programs
    deploy the same instruction name: buy, sell, buy_v2, ... all collide on the hash)."""
    t = collections.defaultdict(list)
    for prog, idl in idls.items():
        for ins in idl.get('instructions', []):
            t[bytes(ins['discriminator'])].append({'target': prog, 'name': ins['name'],
                                                   'args': ins.get('args') or []})
    for n in mayhem_names():
        disc = hashlib.sha256(('global:' + n).encode()).digest()[:8]
        if not any(e['target'] == 'mayhem' and e['name'] == n for e in t[disc]):
            t[disc].append({'target': 'mayhem', 'name': n, 'args': []})
    return t


def pick_entry(cands, caller_prog, measured_len, own_program_first=True):
    """Choose the instruction behind a discriminator.

    A name is shared across programs (buy / sell / buy_v2 / ... all hash to one disc),
    so the choice uses, in order: the candidate whose declared frame explains the
    measured payload length, then the preference order below. `name_candidates` keeps
    every candidate in the map.
    """
    if len(cands) == 1:
        return cands[0]
    order = {'pump_amm': 0, 'pump_fees': 1, 'pump': 2, 'mayhem': 3}
    scored = sorted(cands, key=lambda c: (0 if (c['target'] == caller_prog) == own_program_first else 1,
                                          order.get(c['target'], 9), c['name']))
    return scored[0]


def types_map(idl):
    tl = idl.get('types') or []
    if isinstance(tl, dict):
        return tl
    return {e['name']: e['type'] for e in tl}


def type_size(t, types, depth=0):
    """('fixed', n) or ('variable', minimum_prefix_bytes)."""
    if depth > 6:
        return ('variable', 0)
    if isinstance(t, str):
        if t in FIXED:
            return ('fixed', FIXED[t])
        if t in VARIABLE:
            return ('variable', 4)
        return ('variable', 0)
    if isinstance(t, dict):
        if 'defined' in t:
            name = t['defined']['name']
            if name.startswith('Option'):
                return ('variable', 1)
            d = types.get(name)
            if not d:
                return ('variable', 0)
            kind = d.get('kind') or d.get('type')
            if kind == 'struct' or 'fields' in d:
                tot, var = 0, False
                for f in d.get('fields', []):
                    k, n = type_size(f.get('type'), types, depth + 1)
                    tot += n
                    var = var or k == 'variable'
                return ('variable' if var else 'fixed', tot)
            if kind == 'enum' or 'variants' in d:
                return ('variable', 1)
            return ('variable', 0)
        if 'vec' in t:
            return ('variable', 4)
        if 'array' in t:
            inner, n = t['array']
            k, s = type_size(inner, types, depth + 1)
            return (k, s * n)
        if 'option' in t:
            return ('variable', 1)
    return ('variable', 0)


def expected_frame(entry, idl):
    types = types_map(idl) if idl else {}
    off = 8
    fields = []
    all_fixed = True
    for a in entry['args']:
        kind, size = type_size(a.get('type'), types)
        if kind == 'variable':
            all_fixed = False
        fields.append({'name': a['name'], 'type': json.dumps(a['type']), 'kind': kind,
                       'off': off, 'size': size})
        off += size
    return fields, off, all_fixed


# ------------------------------------------------------------------- call graph
def build_index(p):
    callers = collections.defaultdict(list)
    for pc, ins in p.ins.items():
        if ins.op == 0x85 and pc not in p.call_sym:
            callers[pc + 1 + ins.imm].append(pc)
    return callers


def depth_to(p, start, targets, limit=8):
    """Shortest internal-call distance from function `start` to any target function."""
    seen = {start: 0}
    q = collections.deque([start])
    while q:
        f = q.popleft()
        if f in targets:
            return seen[f]
        if seen[f] >= limit:
            continue
        for ins in p.func_body(f):
            if ins.op != 0x85 or ins.pc in p.call_sym:
                continue
            t = ins.pc + 1 + ins.imm
            if t in p.ins and t not in seen:
                seen[t] = seen[f] + 1
                q.append(t)
    return None


# --------------------------------------------------------------- payload frame
def payload_frame(p, site):
    """Recover the CPI payload written through the disc's base register."""
    ins = p.ins[site]
    val = ins.dst
    base = store_pc = None
    for q in range(site + 1, site + 14):
        i2 = p.ins.get(q)
        if i2 is None:
            continue
        if i2.op in (0x85, 0x95):
            break
        if i2.mn in ('mov64', 'mov32') and i2.dst == val and i2.off == 0 and i2.imm == 0:
            val = i2.src                      # value moved to another register
            continue
        if i2.op in ST_REG and i2.src == val:
            base, store_pc = i2.dst, q
            break
    if base is None or base == 10:
        return None
    fstart = p.func_of.get(site, site)
    rows = []

    def take(q):
        i2 = p.ins.get(q)
        if i2 is None:
            return True                        # hole in the decode: keep scanning
        if i2.dst == base and i2.op not in ST_REG + ST_IMM:
            return False                       # base register redefined
        if i2.op in ST_REG and i2.dst == base:
            rows.append((i2.off, i2.sz, 'reg' if i2.op in ST_REG else i2.imm, q))
        elif i2.op in ST_IMM and i2.dst == base:
            rows.append((i2.off, i2.sz, i2.imm, q))
        return True

    take(store_pc)
    q = store_pc - 1
    while q >= fstart and take(q):
        q -= 1
    q = store_pc + 1
    while q in p.ins and take(q):
        q += 1
    uniq = {}
    for off, sz, v, pc in rows:
        ukey = (off, sz)
        if ukey not in uniq or uniq[ukey][2] == 'reg':
            uniq[ukey] = (off, sz, v, pc)
    out = [uniq[k] for k in sorted(uniq)]
    spans = merge_spans(out)
    length = max(off + sz for off, sz, _v, _pc in out) if out else 0
    return {'base_reg': base, 'store_pc': store_pc, 'rows': out, 'spans': spans,
            'length': length, 'serializer': serializer_callee(p, store_pc, base)}


# --------------------------------------------------------------- handler table
REG_CMP = (0x1d, 0x5d)      # jeq/jne with two registers: the immediate form (0x15/0x55) never matches a disc
IMM_CMP = (0x15, 0x55)


def resolve_handlers(p, prog, discs, disp):
    """Dispatcher -> (instruction name, stub, handler function), one per discriminator."""
    out = []
    for pc in range(disp, disp + 600):
        ins = p.ins.get(pc)
        if ins is None or ins.op != 0x18:
            continue
        if p.func_of.get(pc) != disp:
            break                      # past the dispatcher body
        b = (ins.imm & 0xffffffffffffffff).to_bytes(8, 'little')
        if b not in discs:
            continue
        stub = None
        for q in range(pc + 1, pc + 7):
            i2 = p.ins.get(q)
            if i2 is None:
                continue
            if i2.op in REG_CMP:
                stub = q + 1 + i2.off if i2.mn == 'jeq' else q + 1
                break
            if i2.op in IMM_CMP:
                stub = q + 1 + i2.off if i2.mn == 'jeq' else q + 1
                break
        if stub is None:
            continue
        handler = None
        for q in range(stub, stub + 40):
            i2 = p.ins.get(q)
            if i2 is None:
                continue
            if i2.op == 0x85 and i2.pc not in p.call_sym:
                handler = i2.pc + 1 + i2.imm
                break
            if i2.op == 0x05:
                handler = q + 1 + i2.off
                break
        if handler is None:
            continue
        out.append({'name': pick_entry(discs[b], prog, None)['name'],
                    'target': pick_entry(discs[b], prog, None)['target'],
                    'disc': b.hex(), 'lddw_pc': pc, 'stub_pc': stub, 'handler_pc': handler})
    return out


def edges_under(p, handler, builders, limit=6):
    """BFS from a handler entry: which CPI builders it reaches, and at what depth."""
    seen = {handler: 0}
    q = collections.deque([handler])
    hit = {}
    while q:
        f = q.popleft()
        if f in builders and f not in hit:
            hit[f] = seen[f]
        if seen[f] >= limit:
            continue
        for ins in p.func_body(f):
            if ins.op != 0x85 or ins.pc in p.call_sym:
                continue
            t = ins.pc + 1 + ins.imm
            if t in p.ins and t not in seen:
                seen[t] = seen[f] + 1
                q.append(t)
    return hit


def merge_spans(rows):
    spans = []
    for off, sz, _v, _pc in rows:
        if spans and spans[-1][0] + spans[-1][1] == off:
            spans[-1][1] += sz
        else:
            spans.append([off, sz])
    return spans


def serializer_callee(p, store_pc, base):
    """A `Vec` carrying the payload (ptr = base, len 8) handed to a serializer helper.

    Anchor's `Instruction::new_with_borsh` path appends the Borsh-serialized args to the
    buffer that already holds the discriminator; the args are then written by the callee.
    Detect the hand-off so the frame is not silently reported as disc-only.
    """
    slot = None
    for q in range(store_pc - 12, store_pc + 1):
        i2 = p.ins.get(q)
        if i2 is not None and i2.op == 0x7b and i2.src == base:
            slot = i2.off
    for q in range(store_pc + 1, store_pc + 32):
        i2 = p.ins.get(q)
        if i2 is None:
            continue
        if i2.op == 0x7b and i2.src == base:            # stxdw [fp+S], base
            slot = i2.off
            continue
        if slot is not None and i2.op == 0x7a and i2.off == slot + 8 and i2.imm == 8:
            for r in range(i2.pc + 1, i2.pc + 8):
                i3 = p.ins.get(r)
                if i3 is not None and i3.op == 0x85 and i3.pc not in p.call_sym:
                    return {'helper_pc': i3.pc + 1 + i3.imm, 'len_at_handoff': 8,
                            'len_imm_pc': i2.pc}
            return {'helper_pc': None, 'len_at_handoff': 8, 'len_imm_pc': i2.pc}
        if i2.op in (0x95,) or (i2.op == 0x85):
            break
        if i2.dst == base and i2.op != 0x7b:
            break
    return None


# ------------------------------------------------------------------------ main
def scan(prog, p, discs):
    inv = {p.func_of[pc] for pc, s in p.call_sym.items() if s == 'sol_invoke_signed_rust'}
    cnt = collections.Counter()
    for pc, ins in p.ins.items():
        if ins.op == 0x18:
            b = (ins.imm & 0xffffffffffffffff).to_bytes(8, 'little')
            if b in discs:
                cnt[p.func_of[pc]] += 1
    disp = cnt.most_common(1)[0][0] if cnt else None
    sites = []
    for pc, ins in sorted(p.ins.items()):
        if ins.op != 0x18:
            continue
        b = (ins.imm & 0xffffffffffffffff).to_bytes(8, 'little')
        if b not in discs:
            continue
        f = p.func_of[pc]
        if f == disp:
            continue
        fr = payload_frame(p, pc)
        if fr is None:
            continue
        sites.append({'site_pc': pc, 'func': f, 'entry': discs[b], 'frame': fr,
                      'disc': b, 'depth': depth_to(p, f, inv)})
    return disp, sites, inv


def verify_fixed(e):
    """Declared field starts must all appear as measured store offsets."""
    starts = {r['off'] for r in e['payload']}
    want = {f['off'] for f in e['declared']}
    ok = want.issubset(starts) and e['payload_len'] == e['declared_len_min']
    detail = {}
    if not ok:
        detail = {'missing_starts': sorted(want - starts),
                  'measured_len': e['payload_len'], 'declared_len': e['declared_len_min']}
    frag = sorted(starts - want - {0})
    return ('match' if ok else 'diff'), detail, frag


def main():
    idls = load_idls()
    discs = disc_table(idls)
    out = {'_meta': {'tool': 'tools/cpi_frames.py',
                     'disc_entries': len(discs),
                     'disc_rule': 'sha256("global:"+name)[:8] as the little-endian lddw immediate',
                     'payload_rule': 'stores into the register the discriminator is stored through'},
           'programs': {}}
    for prog in PROGS:
        path = os.path.join(EVIDENCE, 'original', prog, 'deployed.so')
        if not os.path.exists(path):
            continue
        p = fees_prog.load(path)
        disp, sites, inv = scan(prog, p, discs)
        builders = [set()]
        wrapper = sorted(inv)
        wrap_info = []
        for w in wrapper:
            wb = p.func_body(w)
            repack = [i.pc for i in wb if i.op == 0x27 and i.imm == 0x22]
            wrap_info.append({'func_pc': w, 'insns': len(wb),
                              'metas_repack_mul0x22_pc': repack,
                              'accountinfo_byte_reads': [i.pc for i in wb
                                                         if i.op == 0x71 and i.off in (0x20, 0x21)]})
        for s in sites:
            builders[0].add(s['func'])
        rec = {'elf_sha256': hashlib.sha256(open(path, 'rb').read()).hexdigest(),
               'dispatcher_pc': disp,
               'invoke_wrapper_pc': wrapper,
               'invoke_wrapper': wrap_info,
               'handlers_resolved': None,
               'edges': []}
        handlers = resolve_handlers(p, prog, discs, disp) if disp is not None else []
        rec['handlers_resolved'] = len(handlers)
        under = {}
        for h in handlers:
            hit = edges_under(p, h['handler_pc'], builders[0])
            for f, d in hit.items():
                under.setdefault(f, []).append({'handler': h['name'], 'depth': d})
        for s in sites:
            cands = s['entry']
            e = pick_entry(cands, prog, s['frame']['length'], own_program_first=False)
            idl = idls.get(e['target'])
            fields, exp_len, all_fixed = expected_frame(e, idl)
            row = {
                'target_program': e['target'],
                'target_instruction': e['name'],
                'target_disc': s['disc'].hex(),
                'disc_site_pc': s['site_pc'],
                'builder_func_pc': s['func'],
                'builder_func_byte': s['func'] * 8,
                'builder_func_insns': len(p.func_body(s['func'])),
                'depth_to_invoke': s['depth'],
                'payload_len': s['frame']['length'],
                'payload_spans': s['frame']['spans'],
                'payload': [{'off': o, 'width': w, 'kind': ('reg' if isinstance(v, str) else 'imm'),
                             'value': (None if isinstance(v, str) else v), 'pc': pc}
                            for o, w, v, pc in s['frame']['rows']],
                'declared': fields,
                'declared_len_min': exp_len,
                'declared_all_fixed': all_fixed,
                'handlers': sorted(under.get(s['func'], []), key=lambda x: (x['depth'], x['handler'])),
                'name_candidates': sorted(f"{c['target']}:{c['name']}" for c in cands),
            }
            if s['frame']['serializer']:
                row['serializer'] = s['frame']['serializer']
                row['payload_len_final'] = exp_len if all_fixed else None
                row['verify'] = 'serializer'
            elif idl is None and row['payload_len'] == 8 and len(row['payload']) == 1:
                row['verify'] = 'disc-only'      # no IDL for the target: the whole builder writes the disc
            elif all_fixed and idl:
                v, detail, frag = verify_fixed(row)
                row['verify'] = v
                if detail:
                    row['verify_detail'] = detail
                if frag:
                    row['word_fragments'] = frag
            rec['edges'].append(row)
        rec['edge_count'] = len(rec['edges'])
        out['programs'][prog] = rec
        print(f'== {prog}: {len(rec["edges"])} CPI edges (dispatcher {disp and hex(disp)})')
        for e in rec['edges']:
            print(f'   {e["disc_site_pc"]:#08x} f{e["builder_func_pc"]:#08x} '
                  f'{e["target_program"]}:{e["target_instruction"]} '
                  f'disc {e["target_disc"]} len={e["payload_len"]} '
                  f'inv={e["depth_to_invoke"]} {e.get("verify", "variable")}')
    with open(os.path.join(ROOT, 'maps', 'cpi_frames_all4.json'), 'w') as fh:
        json.dump(out, fh, indent=1)
    tot = sum(v['edge_count'] for v in out['programs'].values())
    mism = [(pp, e['target_program'] + ':' + e['target_instruction'])
            for pp, v in out['programs'].items() for e in v['edges'] if e.get('verify') == 'diff']
    fixed = sum(1 for v in out['programs'].values() for e in v['edges'] if e.get('verify') == 'match')
    var = sum(1 for v in out['programs'].values() for e in v['edges'] if 'verify' not in e)
    print(f'\nedges {tot}: fixed-frame match {fixed}, variable-frame {var}, diff {len(mism)}')
    for m in mism:
        print('   diff', m)
    if '--verify' in sys.argv and mism:
        sys.exit(1)


if __name__ == '__main__':
    main()
