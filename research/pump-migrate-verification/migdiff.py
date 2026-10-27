#!/usr/bin/env python3
"""DEPLOYED vs BEFORE vs AFTER for pump migrate / migrate_v2 with post_complete_quote_in seeded."""
import sys, json, base64, hashlib
from pathlib import Path
ROOT = Path('/home/nagi/pumpre/repo'); sys.path.insert(0, str(ROOT / 'scripts'))
import pump_migrate_probe as p1
import pump_migrate_v2_probe as p2

OUT = Path('/home/nagi/pumpround23/out')
BIN = {'DEPLOYED': None, 'BEFORE': OUT / 'final-candidate.so', 'BEFORE_uD': OUT / 'uD-candidate.so', 'AFTER': OUT / 'uF-candidate.so'}
sha = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
print('deployed', sha(ROOT / 'evidence/original/pump/deployed.so'))
for k, v in BIN.items():
    if v: print(k, v, sha(v))

# IDL layout of BondingCurve (account bytes, independent of our struct)
idl = json.loads((ROOT / 'evidence/upstream/pump.json').read_text())
bc = next(t for t in idl['types'] if t['name'] == 'BondingCurve')
print('IDL BondingCurve fields:', [(f['name'], f['type']) for f in bc['type']['fields']])
SZ = {'u64': 8, 'bool': 1, 'pubkey': 32, 'u8': 1, 'i64': 8}
off = 8; OFFS = {}
for f in bc['type']['fields']:
    OFFS[f['name']] = off; off += SZ[f['type']] if isinstance(f['type'], str) else 999
print('IDL account offsets:', OFFS, 'end', off)
cd = base64.b64decode(p1.SAVED['curve']['data_base64'])
print('saved curve len', len(cd), 'lamports', p1.SAVED['curve']['lamports'])
u64 = lambda b, o: int.from_bytes(b[o:o + 8], 'little')
for n in ['real_token_reserves', 'real_quote_reserves', 'post_complete_base_out', 'post_complete_quote_in']:
    if n in OFFS: print('  saved', n, u64(cd, OFFS[n]) if OFFS[n] + 8 <= len(cd) else 'OOR')
gd = base64.b64decode(p1.SAVED['global']['data_base64']); print('saved global pool_migration_fee@146', u64(gd, 146))

PQ = OFFS['post_complete_quote_in']; RQ = OFFS['real_quote_reserves']
def case(post, rq=None, lamports_add=0, extra=None):
    patches = [(PQ, post.to_bytes(8, 'little').hex())]
    if rq is not None: patches.append((RQ, rq.to_bytes(8, 'little').hex()))
    m = {'bonding_curve': {'patches': patches, 'length': max(len(cd), PQ + 8)}}
    if lamports_add: m['bonding_curve']['lamports'] = p1.SAVED['curve']['lamports'] + lamports_add
    c = {'boost': True, 'mutations': m}
    if extra: c.update(extra)
    return c

CASES = [
    ('post=0', case(0)),
    ('post=12345', case(12345)),
    ('post=1e9 (+lamports)', case(10**9, lamports_add=10**9)),
    ('post=u64max (overflow)', case(2**64 - 1)),
    ('post=2^64-rq (exact overflow edge)', None),  # filled below
    ('post=2^64-1-rq (max no-overflow)', None),
]

def short(r):
    inner = r['inner']
    return {'error': r['error'], 'n_inner': sum(len(x) for x in inner) if inner else 0}

def amounts(r):
    """decode CPI data of inner ixs: program index + first bytes + u64 args"""
    out = []
    keys = r['account_keys']
    for grp in (r['inner'] or []):
        for ix in grp:
            ins = ix['instruction'] if 'instruction' in ix else ix
            d = base64.b64decode(ins['data']) if isinstance(ins.get('data'), str) else bytes(ins.get('data', []))
            try: import base58; d2 = base58.b58decode(ins['data'])
            except Exception: d2 = None
            out.append(ins)
    return out

def bal(r, which, name):
    k = r['names'].get(name); a = r[which].get(k) if k else None
    if not a: return None
    d = bytes.fromhex(a['data'])
    tok = u64(d, 64) if len(d) >= 72 and a['owner'] in (str(p1.TOKEN), str(p1.T22)) else None
    return {'lamports': a['lamports'], 'token_amount': tok}

def run_set(mod, label_cases, tag):
    print(f'\n######## {tag} ########')
    for label, c in label_cases:
        res = {k: mod.run(c, v) for k, v in BIN.items()}
        for r in res.values(): r['events'] = [l for l in r['logs'] if l.startswith('Program data:')]
        print(f'\n=== {tag} | {label} ===')
        for k, r in res.items():
            print(f'  {k:10s} error={r["error"]}')
        for k in ['BEFORE', 'BEFORE_uD', 'AFTER']:
            diff = [f for f in ['error', 'after', 'events', 'inner', 'return'] if res['DEPLOYED'][f] != res[k][f]]
            print(f'  DEPLOYED vs {k:10s}: mismatched_fields={diff}')
        for nm in ['pool_quote_token_account', 'pool_base_token_account', 'bonding_curve', 'pool_authority_wsol_account', 'pool_authority_quote_account']:
            if nm in res['DEPLOYED']['names']:
                print(f'  {nm}: ' + ' | '.join(f'{k}={bal(r, "after", nm)}' for k, r in res.items()))
        # first differing inner CPI between DEPLOYED and BEFORE
        d, b = json.dumps(res['DEPLOYED']['inner']), json.dumps(res['BEFORE']['inner'])
        if d != b:
            di, bi = res['DEPLOYED']['inner'], res['BEFORE']['inner']
            fl = lambda x: [i for g in (x or []) for i in g]
            for j, (x, y) in enumerate(zip(fl(di), fl(bi))):
                if x != y:
                    print(f'  first differing inner ix #{j}:\n    DEPLOYED {json.dumps(x)}\n    BEFORE   {json.dumps(y)}'); break
            if len(fl(di)) != len(fl(bi)): print('  inner count', len(fl(di)), len(fl(bi)))
        for k in ['DEPLOYED', 'BEFORE', 'AFTER']:
            tail = [l for l in res[k]['logs'] if 'Error' in l or 'error' in l or 'failed' in l][:3]
            if tail: print(f'  {k} err logs: {tail}')

cdlen_rq = u64(cd, RQ)
CASES[4] = (f'post=2^64-rq (rq={cdlen_rq}, overflow by 0)', case(2**64 - cdlen_rq))
CASES[5] = ('post=2^64-1-rq (sum=u64max, fee sub ok)', case(2**64 - 1 - cdlen_rq))
which = sys.argv[1] if len(sys.argv) > 1 else 'both'
if which in ('v1', 'both'): run_set(p1, CASES, 'migrate')
if which in ('v2', 'both'):
    # v2 probe: same saved curve source; verify identical
    assert p2.SAVED['curve']['data_base64'] == p1.SAVED['curve']['data_base64']
    run_set(p2, CASES, 'migrate_v2 native')
    run_set(p2, [(l, {**c, 'stable': True}) for l, c in CASES[:3]], 'migrate_v2 stable')

if which == 'stablefund':
    def sc(post):
        c = case(post); c['stable'] = True
        c['mutations']['associated_quote_bonding_curve'] = {'patches': [(64, (cdlen_rq + post).to_bytes(8, 'little').hex())]}
        return c
    run_set(p2, [('stable post=0 funded', sc(0)), ('stable post=12345 funded', sc(12345)), ('stable post=1e9 funded', sc(10**9))], 'migrate_v2 stable funded')
