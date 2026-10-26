#!/usr/bin/env python3
"""account_surface - the account surface of every deployed pump and pump_amm
instruction handler, read from the bytes.

Anchor generates one accounts struct per instruction. The generated
`try_accounts` frame pulls one `AccountInfo` per declared field off a slice
iterator and raises one Anchor error per violated constraint. This tool
recovers that surface per handler from the deployed ELF:

  * the dispatcher entry itself: the discriminator constant, its `lddw` site,
    the `jeq` that branches to the stub and the handler the stub reaches, so
    every handler is attributed by the bytes that dispatch it;
  * the `AccountInfo` record (stride, field offsets) and the iterator that
    walks it, measured from the shared fetch helper (AccountNotEnoughKeys);
  * every fetch site with the account name it names;
  * every constraint raise site: the code immediate, its name resolved by
    *executing* the program's own name resolver, the account name carried by
    the site, and the check that guards it (flag byte read, lamport read,
    program-address derivation with its seed vector, or a 32-byte key compare
    against a rodata constant);
  * the account index, by matching the raised account name against the
    instruction's account list in the published IDL;
  * the accounts frame each handler shares with its siblings.

Evidence only: every figure is an instruction index in the deployed ELF
(`insn = byte_offset / 8`).

Usage:
  python3 tools/account_surface.py --prog pump
  python3 tools/account_surface.py --prog pump --json maps/pump_account_surface.json
  python3 tools/account_surface.py --prog pump --verify
  python3 tools/account_surface.py --doc docs/account_surface_pump_amm.md
"""
import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fees_prog import load  # noqa: E402
import error_names as EN  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EVIDENCE = os.environ.get('PUMPFUN_EVIDENCE', os.path.join(
    os.path.dirname(ROOT), 'pumpfun-source', 'evidence', 'original'))
IDL_DIR = os.environ.get('PUMPFUN_IDL', os.path.join(
    os.path.dirname(ROOT), 'pumpfun-source', 'evidence', 'upstream'))

PROGRAMS = ('pump', 'pump_amm')

# sBPF v1 opcodes used here
LDDW, CALL, MOV_I, MOV_R, ADD_I = 0x18, 0x85, 0xb7, 0xbf, 0x07
JA = 0x05
# jumps: `off` carries the displacement, `imm` the comparison constant; the
# dispatcher compares two registers, so it uses the 0x1d form
CMP_JUMPS = {0x15: 'jeq', 0x1d: 'jeq', 0x55: 'jne', 0x5d: 'jne'}
LDX = {0x61: 4, 0x69: 2, 0x71: 1, 0x79: 8}          # ldxw / ldxh / ldxb / ldxdw
STORE_MN = ('stw', 'sth', 'stb', 'stdw', 'stxw', 'stxh', 'stxb', 'stxdw')

ACCOUNT_INFO = {'stride': 48, 'fields': {'key': 0, 'lamports': 8, 'data': 16,
                                         'owner': 24, 'rent_epoch': 32,
                                         'is_signer': 40, 'is_writable': 41,
                                         'executable': 42}}
FETCH_CODE = 3005                       # AccountNotEnoughKeys

# base58 of the program ids / mints these programs compare against
KNOWN_KEYS = {
    '6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P': 'pump',
    'pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA': 'pump_amm',
    'pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ': 'pump_fees',
    'MAyhS8jPGv2f5bQwjCLJ8VdBcxvSJGgKpV8qX7rGq1P': 'mayhem',
    'So11111111111111111111111111111111111111112': 'WSOL',
    'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v': 'USDC',
    'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA': 'tokenkeg',
    'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb': 'token2022',
    'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL': 'associated_token',
    '8LWu7QM2dGR1G8nKDHthckea57bkCzXyBTAKPJUBDHo8': 'fixed_admin',
}

B58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


def b58(b):
    n = int.from_bytes(b, 'big')
    s = ''
    while n:
        n, r = divmod(n, 58)
        s = B58[r] + s
    return '1' * (len(b) - len(b.lstrip(b'\0'))) + s


def vis(x):
    """Printable rendering of a seed value: const seeds are raw bytes."""
    if x is None:
        return '<frame>'
    s = x if isinstance(x, str) else str(x)
    return ''.join(c if 32 <= ord(c) < 127 else '\\x%02x' % ord(c) for c in s)


def va_read(p, segs, va, n):
    return EN.va_read(p, segs, va, n)


def rostr(p, segs, va, n):
    b = va_read(p, segs, va, n)
    if len(b) != n or not n:
        return None
    if not all(32 <= c < 127 for c in b):
        return None
    return b.decode('latin1')


# --------------------------------------------------------------- frame index
def index_frames(p):
    """start -> body (instruction order) and pc -> position inside that body.

    `fees_prog.load` gives the reloc-aware starts and `func_of`; both the frame
    listing and the per-frame position are needed once per raise site, so build
    them once instead of scanning the whole program each time.
    """
    bodies = {}
    for pc in sorted(p.ins):
        s = p.func_of.get(pc)
        if s is None:
            continue
        bodies.setdefault(s, []).append(p.ins[pc])
    p.bodies = bodies
    p.fpos = {}
    for s, body in bodies.items():
        for k, ins in enumerate(body):
            p.fpos[ins.pc] = (s, k)
    return p


def body_of(p, start):
    return p.bodies.get(start, [])


# ------------------------------------------------------- dispatcher entries
def dispatch_entries(p, idl):
    """Every IDL instruction resolved to its handler through the dispatcher.

    The dispatcher is a chain of `lddw r4, <disc>` + `jeq r3, r4, +off` pairs;
    the branch target is a stub that sets the instruction index up and reaches
    the handler with a call or a jump.
    """
    disc2name = {}
    for ix in idl['instructions']:
        d = hashlib.sha256(('global:' + ix['name']).encode()).digest()[:8]
        disc2name[d] = ix['name']
    order = sorted(p.ins)
    pos = {pc: k for k, pc in enumerate(order)}
    out, seen = [], {}
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
            if jins.op in CMP_JUMPS and jins.mn == CMP_JUMPS[jins.op]:
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
        seen[name] = True
        out.append({'name': name, 'disc': raw.hex(), 'lddw_pc': hex(pc),
                    'cmp_pc': hex(cmp_pc), 'cmp': p.ins[cmp_pc].mn,
                    'stub': hex(stub), 'handler_pc': hex(tgt),
                    'handler_insns': len(body_of(p, tgt))})
    return sorted(out, key=lambda r: int(r['handler_pc'], 16)), disc2name


def map_table(prog):
    """The published map under maps/ (name -> handler pc), for cross-checking."""
    for fname, key in (('handlers.json', None), ('amm_handlers_full.json', 'handler_pc')):
        if prog == 'pump' and fname != 'handlers.json':
            continue
        if prog == 'pump_amm' and fname != 'amm_handlers_full.json':
            continue
        path = os.path.join(ROOT, 'maps', fname)
        if not os.path.exists(path):
            continue
        d = json.load(open(path))
        out = {}
        for name, v in d.items():
            if key is None:
                out[name] = int(v, 0) if isinstance(v, str) else v
            elif isinstance(v, dict) and v.get(key):
                out[name] = int(v[key], 0)
        return out
    return {}


# --------------------------------------------------------------- error names
def builtin_names(p, segs):
    """code -> name by executing the Anchor builtin name resolver.

    The resolver is the single frame that references the packed builtin
    identifiers (ConstraintMut, AccountNotEnoughKeys, ...); the error
    constructor calls it with the code address in r2 and it answers with
    (ptr, len) in r2/r3.
    """
    refs = {}
    for pc, ins in p.ins.items():
        if ins.op == LDDW and pc in p.data_ptr:
            va = ins.imm & 0xffffffff
            s = va_read(p, segs, va, 12) or b''
            if any(s.startswith(x.encode()[:6]) for x in (
                    'Constraint', 'AccountD', 'AccountN', 'AccountO', 'AccountS',
                    'InvalidProg', 'Require', 'DeclaredProg')):
                fn = p.func_of.get(pc)
                refs[fn] = refs.get(fn, 0) + 1
    if not refs:
        return {}, None
    fn = max(refs, key=lambda k: refs[k])
    table = {}
    for base, count in ((100, 40), (1000, 40), (2000, 60), (3000, 60), (6000, 120)):
        got, _bad = EN.emulate_table(p, segs, fn, 'r2ptr', count=count, base=base)
        for k, rec in got.items():
            table[base + k] = rec['name']
    return table, fn


def program_names(p, segs, codes):
    """code -> name for the program's own #[error_code] enum (6000 range)."""
    if not codes:
        return {}, None
    tab = EN.recover_name_table(p, segs, p.starts, p.func_of, codes)
    if not tab:
        return {}, None
    return {6000 + int(d): rec['name'] for d, rec in tab['table'].items()}, tab['fn']


# ------------------------------------------------------- account reads/fetches
def helper_starts(p):
    """Frames that fetch one account off the iterator: they raise
    AccountNotEnoughKeys and advance a cursor by the AccountInfo stride."""
    out = {}
    for start in p.starts:
        body = body_of(p, start)
        if not body or len(body) > 60:
            continue
        codes = {i.imm for i in body if i.op == MOV_I}
        strides = {i.imm for i in body if i.mn in ('add64', 'mul64')}
        if FETCH_CODE in codes and ACCOUNT_INFO['stride'] in strides:
            out[start] = {'insns': len(body), 'strides': sorted(strides)}
    return out


def call_targets(p, body):
    out = []
    for ins in body:
        if ins.op == CALL and ins.pc not in p.call_sym:
            t = ins.pc + 1 + ins.imm
            if t in p.ins and t not in out:
                out.append(t)
    return out


def error_ctor(p):
    """The frame every error raise calls: the call target most often reached
    with an error code in r2 (Anchor's AnchorError constructor)."""
    hits = {}
    for pc, ins in p.ins.items():
        if ins.op != CALL or pc in p.call_sym:
            continue
        for j in range(1, 6):
            prev = p.ins.get(pc - j)
            if prev is None:
                break
            if prev.op == MOV_I and prev.dst == 2 and 100 <= prev.imm <= 9999:
                t = pc + 1 + ins.imm
                hits[t] = hits.get(t, 0) + 1
                break
    return max(hits, key=lambda k: hits[k]) if hits else None


def error_sites(p, segs, names, body, ctor):
    """Raise sites of one frame: code, code name, account name, name constant.

    The constructor takes the code in r2 and is followed by the account-name
    formatter call, which receives (ptr, len) in r4/r5.
    """
    out = []
    for k, ins in enumerate(body):
        if ins.op != CALL or ins.pc in p.call_sym:
            continue
        if ins.pc + 1 + ins.imm != ctor:
            continue
        code = None
        for j in range(max(0, k - 5), k):
            if body[j].op == MOV_I and body[j].dst == 2 and 100 <= body[j].imm <= 9999:
                code = body[j].imm
        if code is None:
            continue
        name, str_off, fmt_pc = None, None, None
        for j in range(k, min(k + 22, len(body))):
            b = body[j]
            if j > k and b.op in (JA, 0x95):
                break                       # the block ends: a later site's name
            if b.op != CALL or b.pc in p.call_sym:
                continue
            if j > k and b.pc + 1 + b.imm == ctor:
                break                       # the next raise site starts here
            for i2 in range(max(0, j - 5), j):
                if body[i2].op == LDDW and body[i2].pc in p.data_ptr:
                    va = body[i2].imm & 0xffffffff
                    for i3 in range(i2 + 1, j):
                        if body[i3].op == MOV_I and body[i3].dst == 5 and 0 < body[i3].imm < 200:
                            cand = rostr(p, segs, va, body[i3].imm)
                            if cand and cand.replace('_', '').isalnum():
                                name, str_off, fmt_pc = cand, hex(va), hex(b.pc)
                            break
                    break
            if name:
                break
        out.append({'pc': hex(ins.pc), 'code': code,
                    'code_name': names.get(code), 'account': name,
                    'name_str': str_off, 'name_fmt_pc': fmt_pc})
    return out


def reg_source(p, body, k, reg, back=60, depth=8):
    """What a register holds at body[k]: a rodata address, an immediate, or an
    address derived from the frame pointer."""
    j = k
    for _ in range(depth):
        found = None
        for i in range(j - 1, max(0, k - back) - 1, -1):
            ins = body[i]
            if ins.op == CALL and not (ins.pc in p.call_sym):
                return None                     # a call clobbers r0-r2
            if ins.dst == reg and ins.mn not in STORE_MN:
                found = (i, ins)
                break
        if not found:
            return None
        i, ins = found
        if ins.op == LDDW:
            return {'kind': 'rodata', 'va': ins.imm & 0xffffffff, 'pc': hex(ins.pc)}
        if ins.op == MOV_R:
            reg, j = ins.src, i
            continue
        if ins.op == MOV_I:
            return {'kind': 'imm', 'value': ins.imm, 'pc': hex(ins.pc)}
        if ins.op in (ADD_I, 0x17):
            return {'kind': 'pointer', 'delta': ins.imm, 'pc': hex(ins.pc)}
        return {'kind': ins.mn, 'pc': hex(ins.pc)}
    return None


EVIDENCE_FOR_CODE = {
    2000: 'flag',          # ConstraintMut            -> is_writable byte
    2002: 'flag',          # ConstraintSigner         -> is_signer byte
    2007: 'flag',          # ConstraintExecutable     -> executable byte
    2005: 'lamports',      # ConstraintRentExempt     -> lamports
    2006: 'seeds',         # ConstraintSeeds          -> program-address derivation
    2001: 'key-compare',   # ConstraintHasOne
    2004: 'key-compare',   # ConstraintOwner
    2012: 'key-compare',   # ConstraintAddress
    3006: 'flag',          # AccountNotMutable
    3010: 'flag',          # AccountNotSigner
}


def guard_of(p, segs, body, site_index, code):
    """The check that guards one raise site, from the instructions before it.

    Walks back at most 120 instructions collecting a byte read of an
    AccountInfo flag (+40 is_signer / +41 is_writable / +42 executable), a
    lamports read, a program-address derivation call and a 32-byte compare
    through the memcmp wrapper. The code decides which one is the guard; the
    compare operand is resolved from the register that feeds the memcmp call,
    so a constant is only reported when one is really compared.
    """
    lo = max(0, site_index - 300)
    derivation, memcmp, flag, lamports = None, None, None, None
    for j in range(site_index - 1, lo - 1, -1):
        ins = body[j]
        if ins.op in LDX and ins.off in (40, 41, 42):
            field = {40: 'is_signer', 41: 'is_writable', 42: 'executable'}[ins.off]
            if flag is None:
                flag = {'kind': 'flag', 'field': field, 'offset': ins.off,
                        'pc': hex(ins.pc)}
        elif ins.op in LDX and ins.off == 8 and lamports is None:
            lamports = {'kind': 'lamports', 'offset': 8, 'pc': hex(ins.pc)}
        elif ins.op == CALL and ins.pc not in p.call_sym:
            tgt = ins.pc + 1 + ins.imm
            inner = body_of(p, tgt)
            syms = {p.call_sym.get(i.pc) for i in inner if i.pc in p.call_sym}
            if syms & {'sol_create_program_address', 'sol_try_find_program_address'} \
                    and derivation is None:
                derivation = {'kind': 'seeds', 'pc': hex(ins.pc), 'target': hex(tgt)}
            elif 'sol_memcmp_' in syms and memcmp is None:
                memcmp = {'kind': 'key-compare', 'pc': hex(ins.pc), 'target': hex(tgt)}
                src = reg_source(p, body, j, 2)
                if src and src['kind'] == 'rodata':
                    b = va_read(p, segs, src['va'], 32)
                    if len(b) == 32 and any(b):
                        kid = b58(b)
                        memcmp['constant'] = {'va': hex(src['va']), 'base58': kid,
                                              'known': KNOWN_KEYS.get(kid),
                                              'pc': src['pc']}
                elif src:
                    memcmp['operand'] = src['kind']
    want = EVIDENCE_FOR_CODE.get(code)
    pool = {'flag': flag, 'lamports': lamports, 'seeds': derivation,
            'key-compare': memcmp}
    order = [want] if want else []
    order += [k for k in ('seeds', 'key-compare', 'flag', 'lamports') if k != want]
    chosen = None
    for k in order:
        if pool.get(k) is not None:
            chosen = dict(pool[k])
            break
    if chosen is None:
        return {'kind': 'unknown'}
    if want is not None and chosen['kind'] != want:
        # the check the code implies is not in the window: keep the nearest
        # evidence but mark it so the record does not claim it as the guard
        chosen['fallback'] = True
    cands = [{'kind': k, 'pc': v['pc']} for k, v in pool.items() if v is not None]
    if len(cands) > 1:
        chosen['candidates'] = cands
    return chosen


def idl_account(ix):
    """One declared account of an instruction, from the published IDL."""
    out = {'writable': bool(ix.get('writable') or ix.get('isMut')),
           'signer': bool(ix.get('signer') or ix.get('isSigner')),
           'address': ix.get('address')}
    pda = ix.get('pda') or {}
    seeds = []
    for s in pda.get('seeds', []) or []:
        if s.get('kind') == 'const':
            raw = bytes(s.get('value') or [])
            try:
                seeds.append({'kind': 'const', 'value': raw.decode()})
            except Exception:
                seeds.append({'kind': 'const', 'value': raw.hex()})
        elif s.get('kind') == 'account':
            seeds.append({'kind': 'account', 'value': s.get('path')})
        else:
            seeds.append({'kind': s.get('kind') or '?', 'value': None})
    out['pda'] = seeds or None
    return out


# ------------------------------------------------------------------ per handler
def analyse(prog, p, segs, names, meta, idl):
    ctor = error_ctor(p)
    pda = {}
    pda_path = os.path.join(ROOT, 'maps', 'pda_seeds.json')
    if os.path.exists(pda_path):
        doc = json.load(open(pda_path))
        for rec in doc.get(prog, {}).get('derivations', []):
            if rec.get('array'):
                pda[rec['insn']] = rec
    idl_by = {i['name']: i for i in idl['instructions']}
    entries, _disc = dispatch_entries(p, idl)
    published = map_table(prog)
    out = {}
    for e in entries:
        hname, start = e['name'], int(e['handler_pc'], 16)
        hb = body_of(p, start)
        callees = call_targets(p, hb)
        best, best_sites = None, []
        for t in callees:
            fr = body_of(p, t)
            sites = error_sites(p, segs, names, fr, ctor)
            named = [s for s in sites if s['account']]
            if len(named) > len([s for s in best_sites if s['account']]):
                best, best_sites = t, sites
        fr = body_of(p, best) if best else body_of(p, start)
        sites = best_sites if best else error_sites(p, segs, names, fr, ctor)

        rec = {'handler_pc': hex(start), 'handler_insns': len(hb),
               'disc': e['disc'], 'disc_lddw': e['lddw_pc'], 'disc_cmp': e['cmp_pc'],
               'stub': e['stub'],
               'published_map_pc': (hex(published[hname]) if hname in published else None),
               'account_frame': hex(best) if best else hex(start),
               'account_frame_insns': len(fr),
               'accounts_idl': [dict(index=k, name=a['name'], **idl_account(a))
                                for k, a in enumerate(idl_by.get(hname, {}).get('accounts', []))],
               'checks': [], 'fetches': [], 'account_frame_fetches': 0}

        names_used = {}
        for s in sites:
            k = p.fpos.get(int(s['pc'], 16), (None, 0))[1]
            g = guard_of(p, segs, fr, k, s['code'])
            if g['kind'] == 'seeds' and g.get('pc') in pda:
                a = pda[g['pc']]['array']
                g['seeds'] = [{'value': x.get('value'), 'len': x.get('len')}
                              for x in a.get('seeds', [])]
                g['seed_count'] = a.get('count')
                g['program'] = [x.get('known') or x.get('base58')
                                for x in pda[g['pc']].get('progid_args', [])]
            s = dict(s)
            s['guard'] = g
            if s['account']:
                acc = None
                for a in rec['accounts_idl']:
                    if a['name'] == s['account'] and a['index'] not in names_used.values():
                        acc = a
                        break
                if acc is None:
                    for a in rec['accounts_idl']:
                        if a['name'] == s['account']:
                            acc = a
                            break
                if acc is not None:
                    names_used[s['pc']] = acc['index']
                    s['account_index'] = acc['index']
            if s['code'] == FETCH_CODE:
                s.pop('account_index', None)
                rec['fetches'].append({'pc': s['pc'], 'account': s['account'],
                                       'guard': g})
            else:
                rec['checks'].append(s)
        rec['account_frame_fetches'] = len(rec['fetches'])
        agree = {'address_total': 0, 'address_ok': 0, 'seeds_total': 0, 'seeds_ok': 0}
        for c in rec['checks']:
            g, i = c['guard'], c.get('account_index')
            decl = next((a for a in rec['accounts_idl'] if a['index'] == i), None)
            if decl is None:
                continue
            if g.get('constant') and decl.get('address'):
                agree['address_total'] += 1
                if g['constant']['base58'] == decl['address']:
                    agree['address_ok'] += 1
            if g.get('seeds') and decl.get('pda'):
                agree['seeds_total'] += 1
                lit = [x['value'] for x in decl['pda'] if x['kind'] == 'const']
                got = list(g['seeds'])
                # the derived bump is passed as a final 1-byte seed and is not a
                # declared seed, so ignore it when the declaration has no bump
                if len(got) == len(decl['pda']) + 1 and got[-1].get('len') == 1:
                    got = got[:-1]
                vals = [x['value'] for x in got if x.get('value')]
                if len(decl['pda']) == len(got) and lit and vals[:len(lit)] == lit:
                    agree['seeds_ok'] += 1
        rec['idl_agreement'] = agree
        rec['accounts_measured'] = sorted({c['account_index'] for c in rec['checks']
                                           if c.get('account_index') is not None})
        rec['codes'] = sorted({c['code'] for c in rec['checks']})
        out[hname] = rec

    frames = {}
    for hname, r in out.items():
        frames.setdefault(r['account_frame'], []).append(hname)
    for f, hs in frames.items():
        for hname in hs:
            out[hname]['frame_shared_by'] = sorted(hs)
    meta = dict(meta)
    meta['error_ctor'] = hex(ctor) if ctor else None
    meta['handlers'] = len(out)
    meta['published_map_entries'] = len(published)
    meta['published_map_agree'] = sum(
        1 for h, r in out.items() if h in published
        and published[h] == int(r['handler_pc'], 16))
    meta['published_map_extra'] = [h for h in out if h not in published]
    meta['published_map_only'] = sorted(h for h in published if h not in out)
    meta['shared_frames'] = {f: sorted(hs) for f, hs in frames.items() if len(hs) > 1}
    return out, meta


# ---------------------------------------------------------------- presentation
def md_program(L, out, prog, meta, sha):
    checks = [c for r in out.values() for c in r['checks']]
    fetches = [f for r in out.values() for f in r['fetches']]
    covered = {(h, c) for h, r in out.items() for c in r['accounts_measured']}
    slots = sum(len(r['accounts_idl']) for r in out.values())
    codes = {}
    for c in checks:
        codes.setdefault(c['code'], []).append(c)
    L.append('### `%s` (%d handlers, %d declared account slots)' % (prog, len(out), slots))
    L.append('')
    L.append('| | measured |')
    L.append('|---|---:|')
    L.append('| instruction handlers | %d |' % len(out))
    L.append('| declared account slots (IDL) | %d |' % slots)
    L.append('| constraint raise sites | %d |' % len(checks))
    L.append('| AccountNotEnoughKeys fetch sites | %d |' % len(fetches))
    L.append('| account slots carrying a measured guard | %d |' % len(covered))
    L.append('| accounts frames | %d |' % len({r['account_frame'] for r in out.values()}))
    L.append('| distinct Anchor codes raised | %d |' % len(codes))
    L.append('')
    seeds = [c for c in checks if c['guard']['kind'] == 'seeds' and c['guard'].get('seeds')
             and not c['guard'].get('fallback')]
    addr = [c for c in checks if c['guard'].get('constant') and not c['guard'].get('fallback')]
    flags = [c for c in checks if c['guard']['kind'] == 'flag'
             and not c['guard'].get('fallback')]
    lamps = [c for c in checks if c['guard']['kind'] == 'lamports'
             and not c['guard'].get('fallback')]
    near = [c for c in checks if c['guard'].get('fallback')]
    named = [c for c in checks if c['account']]
    resolved = [c for c in named if c.get('account_index') is not None]
    agr = {'address_total': 0, 'address_ok': 0, 'seeds_total': 0, 'seeds_ok': 0}
    for r in out.values():
        for k, v in r['idl_agreement'].items():
            agr[k] += v
    L.append('Guard mix over the %d constraint sites: %d flag-byte reads, %d lamport '
             'reads, %d program-address derivations with the seed vector recovered, '
             '%d 32-byte key compares against a rodata constant. %d sites carry the '
             'nearest evidence of another check family inside their window and are '
             'marked `near` in the tables below.' % (
                 len(checks), len(flags), len(lamps), len(seeds), len(addr), len(near)))
    L.append('')
    line = ('%d of %d named raise sites resolve to a declared account slot of their '
            'instruction, measured against the published IDL' % (len(resolved), len(named)))
    if agr['address_total']:
        line += (': %d of %d fixed-key compares hit the declared address' % (
            agr['address_ok'], agr['address_total']))
    if agr['seeds_total']:
        line += ('%s %d of %d recovered seed vectors have the declared seed count and '
                 'literal prefixes' % (', and' if agr['address_total'] else ':',
                                       agr['seeds_ok'], agr['seeds_total']))
    L.append(line + '.')
    L.append('')
    L.append('| code | name | sites | accounts named |')
    L.append('|---:|---|---:|---|')
    for code in sorted(codes):
        cs = codes[code]
        accs = sorted({c['account'] for c in cs if c['account']})
        L.append('| %d | `%s` | %d | %s |' % (
            code, cs[0]['code_name'] or '-', len(cs), ', '.join(accs) or '-'))
    L.append('')
    shared = meta['shared_frames']
    if shared:
        L.append('Accounts frames shared by several handlers (same accounts struct):')
        L.append('')
        L.append('| frame | instructions | handlers |')
        L.append('|---|---:|---|')
        seen = set()
        for f, hs in sorted(shared.items(), key=lambda x: -len(x[1])):
            if len(hs) < 2 or f in seen:
                continue
            seen.add(f)
            ins = out[hs[0]]['account_frame_insns']
            L.append('| `%s` | %d | %s |' % (f, ins, ', '.join('`%s`' % h for h in hs)))
        L.append('')
    L.append('#### Handler by handler')
    L.append('')
    for hname in sorted(out):
        r = out[hname]
        L.append('##### `%s` @ %s (disc `%s`)' % (hname, r['handler_pc'], r['disc']))
        L.append('')
        L.append('%d instructions; dispatcher `lddw` %s, `%s` %s, stub %s; accounts '
                 'frame `%s` (%d instructions); %d constraint sites, %d fetch sites.' % (
                     r['handler_insns'], r['disc_lddw'], 'jeq', r['disc_cmp'],
                     r['stub'], r['account_frame'], r['account_frame_insns'],
                     len(r['checks']), r['fetches'].__len__()))
        L.append('')
        if not r['accounts_idl']:
            L.append('No accounts in the instruction account list.')
            L.append('')
            continue
        L.append('| # | account | rw | signer | IDL declares | measured guard |')
        L.append('|---:|---|:--:|:--:|---|---|')
        byidx = {}
        for c in r['checks']:
            if c.get('account_index') is not None:
                byidx.setdefault(c['account_index'], []).append(c)
        for a in r['accounts_idl']:
            cs = byidx.get(a['index'], [])
            decl = a.get('address') or ('pda: ' + ', '.join(
                vis(s['value']) for s in (a.get('pda') or [])) if a.get('pda') else '-')
            if cs:
                parts = []
                for c in cs:
                    g = c['guard']
                    t = '`%s`@%s' % (c['code_name'] or c['code'], c['pc'])
                    if g.get('fallback'):
                        t += ' near %s@%s' % (g['kind'], g.get('pc'))
                    elif g['kind'] == 'seeds':
                        if g.get('seeds'):
                            t += ' on %s' % ', '.join(
                                '%s(%s)' % (vis(s['value']), s['len'])
                                for s in g['seeds'])
                        else:
                            t += ' after derivation `%s`' % g.get('pc')
                    elif g['kind'] == 'flag':
                        t += ' on `%s`' % g['field']
                    elif g.get('constant'):
                        t += ' vs `%s`' % (g['constant']['known'] or g['constant']['base58'])
                    parts.append(t)
                L.append('| %d | `%s` | %s | %s | %s | %s |' % (
                    a['index'], a['name'], 'x' if a['writable'] else '-',
                    'x' if a['signer'] else '-', decl, '<br>'.join(parts)))
            else:
                L.append('| %d | `%s` | %s | %s | %s | - |' % (
                    a['index'], a['name'], 'x' if a['writable'] else '-',
                    'x' if a['signer'] else '-', decl))
        L.append('')
        un = [c for c in r['checks'] if c.get('account_index') is None]
        if un:
            L.append('Raise sites that name no declared slot in this frame: %s' % ', '.join(
                '`%s`@%s' % (c['code_name'] or c['code'], c['pc']) for c in un))
            L.append('')
    L.append('Verification: `python3 tools/account_surface.py --prog %s --verify` '
             're-derives every record from the deployed ELF (SHA-256 `%s`) and compares '
             'it field by field with `maps/%s_account_surface.json`.' % (prog, sha, prog))
    L.append('')


def md(docs, metas, shas, dispatch):
    L = []
    L.append('# `pump` and `pump_amm` account surface, read from the deployed bytes')
    L.append('')
    L.append('Anchor generates one accounts struct per instruction. The generated '
             '`try_accounts` frame pulls one `AccountInfo` per declared field off a slice '
             'iterator and raises one Anchor error per violated constraint. This page '
             'records that surface for the two largest deployed programs, handler by '
             'handler: the dispatcher entry, the `AccountInfo` record, the fetch sites, '
             'and every constraint raise site with its code, its name, the account it '
             'names, and the check that guards it. Generated by '
             '`tools/account_surface.py`; the raw records are in '
             '`maps/pump_account_surface.json` and `maps/pump_amm_account_surface.json`.')
    L.append('')
    L.append('## Dispatcher entries')
    L.append('')
    L.append('Each handler is attributed by the bytes that dispatch it: the '
             'discriminator constant is `sha256("global:" + name)[:8]` carried as the '
             '`lddw` immediate, the following `jeq` branches to a stub, and the stub '
             'reaches the handler with a call or a jump.')
    L.append('')
    L.append('| program | handlers resolved | published map agrees | entries beyond the published map |')
    L.append('|---|---:|---:|---|')
    for prog in PROGRAMS:
        m = metas[prog]
        L.append('| `%s` | %d | %d | %s |' % (
            prog, m['handlers'], m['published_map_agree'],
            ', '.join('`%s`' % h for h in m['published_map_extra']) or '-'))
    L.append('')
    extra = [(prog, e) for prog in PROGRAMS for e in metas[prog].get('extra_entries', [])]
    if extra:
        L.append('Dispatcher entries resolved from the bytes that the published handler '
                 'map does not list:')
        L.append('')
        L.append('| program | instruction | disc | lddw | cmp | stub | handler | instructions |')
        L.append('|---|---|---|---|---|---|---|---:|')
        for prog, e in extra:
            L.append('| `%s` | `%s` | `%s` | %s | %s %s | %s | %s | %d |' % (
                prog, e['name'], e['disc'], e['lddw_pc'], e['cmp'], e['cmp_pc'],
                e['stub'], e['handler_pc'], e['handler_insns']))
        L.append('')
    L.append('## The `AccountInfo` record')
    L.append('')
    L.append('The shared fetch helper advances an iterator by **%d** bytes and raises '
             '**%d** when it runs out, which fixes the record stride and its field '
             'offsets:' % (ACCOUNT_INFO['stride'], FETCH_CODE))
    L.append('')
    L.append('| field | offset | read by |')
    L.append('|---|---:|---|')
    uses = {0: 'key compares (2001 has_one, 2012 address, seeds)',
            8: 'lamport reads',
            16: 'account data (discriminator + Borsh body)',
            24: 'owner compares (2004 / 3007)',
            32: 'rent-exempt constraint (2005)',
            40: 'signer constraint (2002) / AccountNotSigner (3010)',
            41: 'mut constraint (2000) / AccountNotMutable (3006)',
            42: 'executable constraint (2007)'}
    for f, off in sorted(ACCOUNT_INFO['fields'].items(), key=lambda x: x[1]):
        L.append('| `%s` | %d | %s |' % (f, off, uses.get(off, '')))
    L.append('')
    L.append('The iterator is a two word cursor `{ptr@0, remaining@8}`: a fetch checks '
             '`remaining`, decrements it, takes `ptr` and stores `ptr + %d` back. Fetch '
             'helpers measured per program:' % ACCOUNT_INFO['stride'])
    L.append('')
    L.append('| program | fetch helper frames | first frames |')
    L.append('|---|---:|---|')
    for prog in PROGRAMS:
        m = metas[prog]
        L.append('| `%s` | %d | %s |' % (prog, len(m['fetch_helpers']),
                                         ', '.join('`%s`' % h
                                                   for h in m['fetch_helpers'][:6])))
    L.append('')
    L.append('## Error names')
    L.append('')
    L.append('Every code below is named by the program itself. Anchor builds a name '
             'resolver per code family and the error constructor calls it with the code '
             'address in `r2`; executing it returns the identifier, so the table is '
             'recovered from the bytes rather than from a source enum.')
    L.append('')
    L.append('| program | name resolver | builtin names | program names | error constructor |')
    L.append('|---|---|---:|---:|---|')
    for prog in PROGRAMS:
        m = metas[prog]
        L.append('| `%s` | `%s` | %d | %d | `%s` |' % (
            prog, m['name_fn'], m['name_table_entries'], m['program_table_entries'],
            m['error_ctor']))
    L.append('')
    for d in dispatch:
        L.append(d)
        L.append('')
    for prog in PROGRAMS:
        md_program(L, docs[prog], prog, metas[prog], shas[prog])
    return '\n'.join(L)


# ------------------------------------------------------------------------ main
def run_prog(prog):
    so = os.path.join(EVIDENCE, prog, 'deployed.so')
    p = index_frames(load(so))
    segs = EN.segments(p)
    idl = json.load(open(os.path.join(IDL_DIR, prog + '.json')))
    names, name_fn = builtin_names(p, segs)
    codes = {c for _pc, c, _off in EN.raise_sites(p)}
    EN.CAMEL_BLOCK = EN.camel_block(p, segs)
    pnames, pfn = program_names(p, segs, codes)
    names = dict(names)
    names.update(pnames)
    meta = {'name_fn': hex(name_fn) if name_fn else None,
            'name_table_entries': len(names) - len(pnames),
            'program_table_entries': len(pnames),
            'program_name_fn': hex(pfn) if pfn else None,
            'fetch_helpers': [hex(x) for x in sorted(helper_starts(p))],
            'sha256': hashlib.sha256(open(so, 'rb').read()).hexdigest()}
    out, meta = analyse(prog, p, segs, names, meta, idl)
    entries, _disc = dispatch_entries(p, idl)
    by_name = {e['name']: e for e in entries}
    meta['extra_entries'] = [by_name[h] for h in meta['published_map_extra']]
    return out, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prog', default='pump', choices=PROGRAMS)
    ap.add_argument('--json')
    ap.add_argument('--doc')
    ap.add_argument('--verify', action='store_true')
    a = ap.parse_args()

    if a.doc:
        docs, metas, shas, dispatch = {}, {}, {}, []
        for prog in PROGRAMS:
            out, meta = run_prog(prog)
            docs[prog], metas[prog], shas[prog] = out, meta, meta['sha256']
            dispatch.append(
                '`%s`: %d dispatcher entries resolved, %d agree with the published '
                'handler map; accounts frame shared by at most %d handlers.' % (
                    prog, meta['handlers'], meta['published_map_agree'],
                    max([len(v) for v in meta['shared_frames'].values()] or [1])))
        open(a.doc, 'w').write(md(docs, metas, shas, dispatch))
        print('wrote', a.doc)
        return 0

    out, meta = run_prog(a.prog)
    if a.json:
        json.dump({'program': a.prog, 'name_resolver': meta['name_fn'],
                   'program_name_resolver': meta['program_name_fn'],
                   'error_ctor': meta['error_ctor'],
                   'fetch_helpers': meta['fetch_helpers'],
                   'published_map_agrees': meta['published_map_agree'],
                   'published_map_extra': meta['published_map_extra'],
                   'handlers': out},
                  open(a.json, 'w'), indent=1, sort_keys=True)
        print('wrote', a.json)
    if a.verify:
        prev = json.load(open(os.path.join(
            ROOT, 'maps', '%s_account_surface.json' % a.prog)))['handlers']
        bad = [h for h in out if prev.get(h) != out[h]]
        print('verify: %d/%d handler records reproduce' % (len(out) - len(bad), len(out)))
        for h in bad:
            print('  MISMATCH', h)
        return 1 if bad else 0
    for h in sorted(out):
        r = out[h]
        print('%-36s frame=%-9s checks=%-3d fetches=%-2d accts=%s' % (
            h, r['account_frame'], len(r['checks']), len(r['fetches']),
            r['accounts_measured']))
    print('handlers=%d published_map_agree=%d extra=%s' % (
        meta['handlers'], meta['published_map_agree'], meta['published_map_extra']))
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
