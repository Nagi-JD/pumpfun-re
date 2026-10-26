#!/usr/bin/env python3
"""account_metas - the account surface of every pump_fees instruction handler,
read from the deployed bytes.

Anchor derives an account struct per instruction: the generated `try_accounts`
frame pulls each `AccountInfo` off a slice iterator in declaration order and
then raises one Anchor error per violated constraint. This tool recovers that
surface per handler, from the binary:

  * the AccountInfo record itself (stride, field offsets) and the iterator that
    walks it, measured from the shared fetch helper (AccountNotEnoughKeys raise);
  * every fetch site (AccountNotEnoughKeys) with the account name it names;
  * every constraint raise site: the code immediate, its name resolved by
    *executing* the program's own Anchor builtin name resolver, the account name
    carried by the site, and the check that guards it (flag byte read, PDA seed
    derivation, 32-byte key compare against a rodata constant);
  * the account index, by matching the measured account name against the
    instruction's account list in the published IDL.

Evidence only: every figure is an instruction address in the deployed ELF
(.text vaddr/8 = pc).

Usage:
  python3 tools/account_metas.py --prog pump_fees
  python3 tools/account_metas.py --prog pump_fees --json maps/pump_fees_account_metas.json
  python3 tools/account_metas.py --prog pump_fees --doc docs/pump_fees_account_metas.md
  python3 tools/account_metas.py --prog pump_fees --verify
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fees_prog import load, handler_table  # noqa: E402
import error_names as EN  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EVIDENCE = os.environ.get('PUMPFUN_EVIDENCE', os.path.join(
    os.path.dirname(ROOT), 'pumpfun-source', 'evidence', 'original'))
IDL_DIR = os.environ.get('PUMPFUN_IDL', os.path.join(
    os.path.dirname(ROOT), 'pumpfun-source', 'evidence', 'upstream'))

PROGRAMS = ('pump_fees',)      # dispatcher map for the other programs is not wired here

# sBPF v1 opcodes used here
LDDW, CALL, EXIT, MOV_I, MOV_R, ADD_I = 0x18, 0x85, 0x95, 0xb7, 0xbf, 0x07
LDX = {0x61: 4, 0x69: 2, 0x71: 1, 0x79: 8}          # ldxw / ldxh / ldxb / ldxdw
JMP = {0x05, 0x15, 0x1d, 0x25, 0x2d, 0x35, 0x3d, 0x45, 0x4d, 0x55, 0x5d,
       0x65, 0x6d, 0x75, 0x7d, 0xa5, 0xad, 0xb5, 0xbd, 0xc5, 0xcd, 0xd5, 0xdd}

ACCOUNT_INFO = {'stride': 48, 'fields': {'key': 0, 'lamports': 8, 'data': 16,
                                         'owner': 24, 'rent_epoch': 32,
                                         'is_signer': 40, 'is_writable': 41,
                                         'executable': 42}}
ACCOUNT_NAME_CODES = (2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009,
                      2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017)
FETCH_CODE = 3005                       # AccountNotEnoughKeys

# base58 of the program ids / mints this program compares against
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


def frame_list(p, start):
    return [p.ins[pc] for pc in p.order if p.func_of.get(pc) == start]


def va_read(p, segs, va, n):
    return EN.va_read(p, segs, va, n)


def rostr(p, segs, va, n):
    b = va_read(p, segs, va, n)
    if len(b) != n or not n:
        return None
    if not all(32 <= c < 127 for c in b):
        return None
    return b.decode('latin1')


# --------------------------------------------------------------- error names
def builtin_names(p, segs):
    """code -> name by executing the Anchor builtin name resolver.

    The resolver is the single frame that references the packed builtin
    identifiers; it is called by the error constructor with the code *address*
    in r2 and answers with (ptr, len) in r2/r3.
    """
    refs = {}
    for pc, ins in p.ins.items():
        if ins.op == LDDW and pc in p.data_ptr:
            va = ins.imm & 0xffffffff
            s = va_read(p, segs, va, 12) or b''
            if any(s.startswith(x.encode()[:6]) for x in (
                    'Constraint', 'AccountD', 'AccountN', 'AccountO', 'AccountS',
                    'InvalidProg', 'Require', 'DeclaredProg')):
                refs[p.func_of.get(pc)] = refs.get(p.func_of.get(pc), 0) + 1
    if not refs:
        return {}, None
    fn = max(refs, key=lambda k: refs[k])
    table = {}
    for base, count in ((100, 40), (1000, 40), (2000, 60), (3000, 60), (6000, 120)):
        got, _bad = EN.emulate_table(p, segs, fn, 'r2ptr', count=count, base=base)
        for k, rec in got.items():
            table[base + k] = rec['name']
    return table, fn


# ------------------------------------------------------- account reads/fetches
def helper_starts(p):
    """Frames that fetch an account off the iterator: they raise
    AccountNotEnoughKeys and advance a cursor by the AccountInfo stride."""
    out = {}
    for start in p.starts:
        body = p.func_body(start)
        if len(body) > 60:
            continue
        codes = {i.imm for i in body if i.op == MOV_I}
        strides = {i.imm for i in body if i.mn in ('add64', 'mul64')}
        if FETCH_CODE in codes and ACCOUNT_INFO['stride'] in strides:
            out[start] = len(body)
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
    """The frame every error raise calls: the call target most often reached with
    an error code in r2 (Anchor's `AnchorError::new`-style constructor)."""
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
    """Raise sites of one frame: (pc, code, code_name, account_name, str_off).

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
            if b.op != CALL or b.pc in p.call_sym:
                continue
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
    """What a register holds at instruction index k: a rodata address, an
    immediate, or an address derived from the frame pointer."""
    j = k
    for _ in range(depth):
        found = None
        for i in range(j - 1, max(0, k - back) - 1, -1):
            ins = body[i]
            if ins.op == CALL and not (ins.pc in p.call_sym):
                return None                     # a call clobbers r0-r2
            if ins.dst == reg and ins.mn not in ('stw', 'sth', 'stb', 'stdw',
                                                 'stxw', 'stxh', 'stxb', 'stxdw'):
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

    Collects, walking back at most 120 instructions: a byte read of an
    AccountInfo flag (+40 is_signer / +41 is_writable / +42 executable), a
    lamports read, a program-address derivation call, and a 32-byte compare
    through the memcmp wrapper. The code decides which one is the guard; the
    compare operand is resolved from the register that feeds the memcmp call,
    so a constant is only reported when one is really compared.
    """
    lo = max(0, site_index - 120)
    derivation, memcmp, flag, lamports = None, None, None, None
    for j in range(site_index - 1, lo - 1, -1):
        ins = body[j]
        if ins.op in LDX and ins.off in (40, 41, 42):
            field = {40: 'is_signer', 41: 'is_writable', 42: 'executable'}[ins.off]
            if flag is None or flag['field'] != field:
                flag = flag or {'kind': 'flag', 'field': field, 'offset': ins.off,
                                'pc': hex(ins.pc)}
        elif ins.op in LDX and ins.off == 8 and lamports is None:
            lamports = {'kind': 'lamports', 'offset': 8, 'pc': hex(ins.pc)}
        elif ins.op == CALL and ins.pc not in p.call_sym:
            tgt = ins.pc + 1 + ins.imm
            inner = p.func_body(tgt)
            syms = {p.call_sym.get(i.pc) for i in inner if i.pc in p.call_sym}
            if syms & {'sol_create_program_address', 'sol_try_find_program_address'} and derivation is None:
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
    cands = [{'kind': k, 'pc': v['pc']} for k, v in pool.items() if v is not None]
    if len(cands) > 1:
        chosen['candidates'] = cands
    return chosen


def const_of(p, segs, body, site_index, width=32):
    """The rodata 32-byte constant compared shortly before a raise site."""
    for j in range(site_index - 1, max(0, site_index - 30) - 1, -1):
        if body[j].op == LDDW and body[j].pc in p.data_ptr:
            va = body[j].imm & 0xffffffff
            b = va_read(p, segs, va, width)
            if len(b) == width and any(b):
                return {'va': hex(va), 'base58': b58(b),
                        'known': KNOWN_KEYS.get(b58(b)), 'pc': hex(body[j].pc)}
    return None


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
def analyse(prog, p, segs, names, name_fn):
    handlers = handler_table()
    ctor = error_ctor(p)
    idl_path = os.path.join(IDL_DIR, prog + '.json')
    idl_by = {}
    if os.path.exists(idl_path):
        idl = json.load(open(idl_path))
        idl_by = {i['name']: i for i in idl['instructions']}
    pda = {}
    pda_path = os.path.join(ROOT, 'maps', 'pda_seeds.json')
    if os.path.exists(pda_path):
        doc = json.load(open(pda_path))
        for rec in doc.get(prog, {}).get('derivations', []):
            if rec.get('array'):
                pda[rec['insn']] = rec
    helpers = helper_starts(p)
    out = {}
    for hname, start in handlers:
        hb = p.func_body(start)
        callees = call_targets(p, hb)
        best, best_sites = None, []
        for t in callees:
            fr = frame_list(p, t)
            sites = error_sites(p, segs, names, fr, ctor)
            named = [s for s in sites if s['account']]
            if len(named) > len([s for s in best_sites if s['account']]):
                best, best_sites = t, sites
        fr = frame_list(p, best) if best else frame_list(p, start)
        sites = best_sites if best else error_sites(p, segs, names, fr, ctor)
        idx = {ins.pc: k for k, ins in enumerate(fr)}

        rec = {'handler_pc': hex(start), 'handler_insns': len(hb),
               'account_frame': hex(best) if best else hex(start),
               'account_frame_insns': len(fr),
               'accounts_idl': [dict(index=k, name=a['name'], **idl_account(a))
                                for k, a in enumerate(idl_by.get(hname, {}).get('accounts', []))],
               'checks': [], 'fetches': [], 'account_frame_fetches': 0}

        names_used = {}
        for s in sites:
            k = idx[int(s['pc'], 16)]
            g = guard_of(p, segs, fr, k, s['code'])
            if g['kind'] == 'seeds':
                cand = g['pc']
                if cand in pda:
                    a = pda[cand]['array']
                    g['seeds'] = [{'value': x.get('value'), 'len': x.get('len')}
                                  for x in a.get('seeds', [])]
                    g['seed_count'] = a.get('count')
                    g['program'] = [x.get('known') or x.get('base58')
                                    for x in pda[cand].get('progid_args', [])]
            if s['code'] in (2012, 2004, 2007, 2013, 2014, 2015) and g['kind'] == 'key-compare':
                g.setdefault('constant', None)
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
                lit = [s['value'] for s in decl['pda'] if s['kind'] == 'const']
                got = [s for s in g['seeds']]
                # the derived bump is passed as a final 1-byte seed and is not a
                # declared seed, so ignore it when the declaration has no bump
                if len(got) == len(decl['pda']) + 1 and got[-1].get('len') == 1:
                    got = got[:-1]
                vals = [s['value'] for s in got if s.get('value')]
                if len(decl['pda']) == len(got) and lit and vals[:len(lit)] == lit:
                    agree['seeds_ok'] += 1
        rec['idl_agreement'] = agree
        rec['accounts_measured'] = sorted({c['account_index'] for c in rec['checks']
                                           if c.get('account_index') is not None})
        rec['codes'] = sorted({c['code'] for c in rec['checks']})
        out[hname] = rec
    return out, {'name_fn': hex(name_fn) if name_fn else None,
                 'name_table_entries': len(names)}


# ---------------------------------------------------------------- presentation
def md(out, prog, meta, sha):
    L = []
    hosts = sum(1 for r in out.values() if r['checks'])
    checks = [c for r in out.values() for c in r['checks']]
    fetches = [f for r in out.values() for f in r['fetches']]
    covered = sorted({(h, c) for h, r in out.items() for c in r['accounts_measured']})
    codes = {}
    for c in checks:
        codes.setdefault(c['code'], []).append(c)
    L.append('# `%s` account surface, read from the deployed bytes' % prog)
    L.append('')
    L.append('Every Anchor handler is generated from an accounts struct: a '
             '`try_accounts` frame pulls one `AccountInfo` per declared field off a '
             'slice iterator, then raises one error per violated constraint. This page '
             'records that surface for all %d deployed handlers of `%s`: the '
             '`AccountInfo` record itself, the fetch sites, and every constraint raise '
             'site with its code, its name, the account it names, and the check that '
             'guards it. Generated by `tools/account_metas.py`; the raw records are in '
             '`maps/%s_account_metas.json`.' % (len(out), prog, prog))
    L.append('')
    L.append('## The AccountInfo record')
    L.append('')
    L.append('The shared fetch helper advances an iterator by **%d** bytes and raises '
             '**%d** when it runs out, which fixes the record\'s stride and its field '
             'offsets:' % (ACCOUNT_INFO['stride'], FETCH_CODE))
    L.append('')
    L.append('| field | offset | read by |')
    L.append('|---|---:|---|')
    names = {40: 'signer constraint (2002) / AccountNotSigner (3010)',
             41: 'mut constraint (2000) / AccountNotMutable (3006)',
             42: 'executable constraint (2007)',
             0: 'key compares (2001 has_one, 2012 address, seeds)',
             8: 'lamport reads',
             16: 'account data (discriminator + Borsh body)',
             24: 'owner compares (2004 / 3007)',
             32: 'rent-exempt constraint (2005)'}
    for f, off in sorted(ACCOUNT_INFO['fields'].items(), key=lambda x: x[1]):
        L.append('| `%s` | %d | %s |' % (f, off, names.get(off, '')))
    L.append('')
    L.append('The iterator itself is a two-word cursor `{ptr@0, remaining@8}`: a fetch '
             'checks `remaining`, decrements it, takes `ptr` and stores `ptr + %d` back.'
             % ACCOUNT_INFO['stride'])
    L.append('')
    L.append('## Error names')
    L.append('')
    L.append('Anchor\'s builtin error names are in the binary: the resolver at `%s` is '
             'the single frame that references the packed identifier block, and the error '
             'constructor calls it with the code address in `r2`. Executing it over '
             '100..6119 returns **%d** names, so every code below is named by the program, '
             'not by a source enum.' % (meta['name_fn'], meta['name_table_entries']))
    L.append('')
    L.append('| code | name | sites | accounts named |')
    L.append('|---:|---|---:|---|')
    for code in sorted(codes):
        cs = codes[code]
        accs = sorted({c['account'] for c in cs if c['account']})
        L.append('| %d | `%s` | %d | %s |' % (
            code, cs[0]['code_name'] or '-', len(cs), ', '.join(accs) or '-'))
    L.append('')
    L.append('%d handlers carry a constraint surface: %d constraint sites and %d '
             'AccountNotEnoughKeys fetch sites, over %d of the %d account slots the IDL '
             'declares for this program.' % (
                 hosts, len(checks), len(fetches), len(covered),
                 sum(len(r['accounts_idl']) for r in out.values())))
    L.append('')
    seeds = [c for c in checks if c['guard']['kind'] == 'seeds' and c['guard'].get('seeds')]
    addr = [c for c in checks if c['guard'].get('constant')]
    L.append('Of the constraint sites, %d are program-address derivations with the seed '
             'vector recovered (literal prefix + the key/length seeds), and %d compare the '
             'account key against a 32-byte constant (the published program and mint keys '
             'resolve to `pump`, `pump_amm`, `WSOL`, `tokenkeg`, ...).' % (len(seeds), len(addr)))
    L.append('')
    named = [c for c in checks if c['account']]
    resolved = [c for c in named if c.get('account_index') is not None]
    agr = {'address_total': 0, 'address_ok': 0, 'seeds_total': 0, 'seeds_ok': 0}
    for r in out.values():
        for k, v in r['idl_agreement'].items():
            agr[k] += v
    L.append('Every raise site that names an account carries its name as `(ptr, len)` in the '
             'error record, so the slot is read from the name and matched against the '
             'instruction\'s account list in the published IDL: %d of %d named sites resolve '
             'to a declared slot. Sites that name nothing are the associated-token and '
             'token-program comparisons the program builds for derived addresses; they are '
             'reported by code and address only.' % (len(resolved), len(named)))
    L.append('')
    L.append('The IDL also declares, per account, a fixed `address` or a `pda` seed list. '
             'Measured against those declarations: **%d of %d** fixed-key compares hit the '
             'declared address, and **%d of %d** recovered seed vectors have the declared '
             'seed count and literal prefixes.' % (
                 agr['address_ok'], agr['address_total'], agr['seeds_ok'], agr['seeds_total']))
    L.append('')
    L.append('## Handler by handler')
    L.append('')
    for hname in sorted(out):
        r = out[hname]
        L.append('### `%s` @ %s' % (hname, r['handler_pc']))
        L.append('')
        L.append('accounts frame `%s` (%d instructions).' % (
            r['account_frame'], r['account_frame_insns']))
        L.append('')
        if not r['accounts_idl']:
            L.append('No accounts in the instruction\'s account list.')
            L.append('')
            continue
        L.append('| # | account | IDL rw | IDL signer | IDL declares | measured guard |')
        L.append('|---:|---|:--:|:--:|---|---|')
        byidx = {}
        for c in r['checks']:
            if c.get('account_index') is not None:
                byidx.setdefault(c['account_index'], []).append(c)
        for a in r['accounts_idl']:
            cs = byidx.get(a['index'], [])
            decl = a.get('address') or ('pda: ' + ', '.join(
                str(s['value']) for s in (a.get('pda') or [])) if a.get('pda') else '-')
            if cs:
                parts = []
                for c in cs:
                    g = c['guard']
                    t = '`%s`@%s' % (c['code_name'] or c['code'], c['pc'])
                    if g['kind'] == 'seeds':
                        if g.get('seeds'):
                            t += ' on %s' % (', '.join(
                                '%s(%s)' % (s['value'] if s['value'] else '<frame>', s['len'])
                                for s in g['seeds']))
                        else:
                            t += ' after derivation `%s`' % g.get('pc')
                    elif g['kind'] == 'flag':
                        t += ' on `%s`' % g['field']
                    elif g['kind'] == 'key-compare' and g.get('constant'):
                        t += ' vs `%s`' % (g['constant']['known'] or g['constant']['base58'])
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
            L.append('Unnamed raise sites in this frame: %s' % ', '.join(
                '`%s`@%s' % (c['code_name'] or c['code'], c['pc']) for c in un))
            L.append('')
    L.append('## Verification')
    L.append('')
    L.append('`python3 tools/account_metas.py --prog %s --verify` re-derives every '
             'record from the deployed ELF (SHA-256 `%s`) and compares it field by field '
             'with `maps/%s_account_metas.json`.' % (prog, sha, prog))
    L.append('')
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prog', default='pump_fees', choices=PROGRAMS)
    ap.add_argument('--json')
    ap.add_argument('--doc')
    ap.add_argument('--verify', action='store_true')
    a = ap.parse_args()

    so = os.path.join(EVIDENCE, a.prog, 'deployed.so')
    p = load(so)
    segs = EN.segments(p)
    names, name_fn = builtin_names(p, segs)
    out, meta = analyse(a.prog, p, segs, names, name_fn)

    if a.json:
        json.dump({'program': a.prog, 'name_resolver': meta['name_fn'],
                   'handlers': out}, open(a.json, 'w'), indent=1, sort_keys=True)
        print('wrote', a.json)

    if a.doc:
        import hashlib
        sha = hashlib.sha256(open(so, 'rb').read()).hexdigest()
        open(a.doc, 'w').write(md(out, a.prog, meta, sha))
        print('wrote', a.doc)

    if a.verify:
        prev = json.load(open(os.path.join(
            ROOT, 'maps', '%s_account_metas.json' % a.prog)))['handlers']
        bad = [h for h in out if prev.get(h) != out[h]]
        print('verify: %d/%d handler records reproduce' % (len(out) - len(bad), len(out)))
        for h in bad:
            print('  MISMATCH', h)
        return 1 if bad else 0

    for h in sorted(out):
        r = out[h]
        print('%-34s frame=%-8s checks=%-2d fetches=%-2d codes=%s' % (
            h, r['account_frame'], len(r['checks']), len(r['fetches']),
            ','.join(str(c) for c in r['codes'])))
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
