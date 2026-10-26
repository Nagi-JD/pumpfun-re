#!/usr/bin/env python3
"""b1_transfer_fee.py - B1 measurement: does each pump handler transitively reach
the cited Token-2022 transfer-fee helper @0x12a1c, and how does that compare with
what docs/analysis/B1_transfer_fee.md assumed?

Emits a markdown table (stdout) plus JSON. Every claim is a cited pc.

Usage: b1_transfer_fee.py PROG.so MAPS_JSON HELPER_PC [CPI_WRAPPER_PC]
"""
import json
import sys

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from handler_bodies import load  # noqa: E402

CASES = [
    # name, why it is in the table
    ('buy_v2', 'quote leg v2'),
    ('buy_exact_quote_in_v2', 'quote leg v2 exact-in'),
    ('buy_v3', 'quote leg v3'),
    ('buy_exact_quote_in_v3', 'quote leg v3 exact-in'),
    ('migrate_v2', 'migrate_v2 harvest'),
    ('migrate', 'control: v1 migrate'),
    ('create', 'control: create'),
    ('create_v2', 'control: create_v2'),
    ('multi_hop_curve_swap', 'control: router'),
    ('buy', 'control: SOL buy'),
    ('buy_exact_sol_in', 'control: SOL buy exact-in'),
    ('sell', 'control: SOL sell'),
    ('sell_v2', 'control: sell_v2 (B1 note claims NO helper)'),
    ('sell_v3', 'control: sell_v3'),
]


def main():
    path, maps_json = sys.argv[1], sys.argv[2]
    helper = int(sys.argv[3], 0)
    cpi = int(sys.argv[4], 0) if len(sys.argv) > 4 else None
    p = load(path)
    with open(maps_json) as f:
        hm = json.load(f)

    # 1) who calls the helper directly (instruction sites) and in which function
    sites = sorted(pc for pc, ins in p.ins.items()
                   if ins.op == 0x85 and (pc not in p.call_sym)
                   and pc + 1 + ins.imm == helper)
    by_fn = {}
    for s in sites:
        fn = s if s in p.entries_set else p.func_start_internal(s)
        by_fn.setdefault(fn, []).append(s)

    rows = []
    targets = {helper} | ({cpi} if cpi else set())
    for name, role in CASES:
        if name not in hm:
            rows.append({'name': name, 'role': role, 'missing': True})
            continue
        hp = int(hm[name]['handler_pc'], 16)
        body, _, _ = p.body(hp)
        found, visited = p.reach(hp, targets)
        h = found.get(helper)
        c = found.get(cpi) if cpi else None
        rows.append({
            'name': name, 'role': role,
            'handler_pc': hex(hp), 'body_insns': len(body),
            'graph_nodes': len(visited),
            'helper_reachable': bool(h),
            'helper_depth': h[0] if h else None,
            'helper_chain': [hex(x) for x in h[1]] if h else [],
            'cpi_reachable': bool(c) if cpi else None,
            'cpi_depth': c[0] if c else None,
        })

    # 2) strict vs loose body bounds: is the over-approximation material?
    p.strict_bounds = True
    p._callee_cache = {}
    strict = {r['name']: len(p.body(int(hm[r['name']]['handler_pc'], 16))[0])
              for r in rows if not r.get('missing')}
    p.strict_bounds = False
    p._callee_cache = {}
    loose = {r['name']: len(p.body(int(hm[r['name']]['handler_pc'], 16))[0])
             for r in rows if not r.get('missing')}
    p.strict_bounds = True
    p._callee_cache = {}
    for r in rows:
        if r.get('missing'):
            continue
        r['body_insns_loose'] = loose[r['name']]
        r['body_insns_strict'] = strict[r['name']]

    out = {
        'program': path.split('/')[-3] if path.endswith('/deployed.so') else path,
        'helper_pc': hex(helper),
        'cpi_wrapper_pc': hex(cpi) if cpi else None,
        'helper_caller_sites': [hex(s) for s in sites],
        'helper_caller_functions': {hex(k): [hex(x) for x in v] for k, v in sorted(by_fn.items())},
        'cases': rows,
    }
    print(json.dumps(out, indent=1))

    print('\n| handler | handler_pc | body insns (strict/loose) | helper @%s | depth | chain | CPI wrapper |' % hex(helper))
    print('|---|---|---:|---|---:|---|---|')
    for r in rows:
        if r.get('missing'):
            print('| `%s` | — | — | map entry missing | — | — | — |' % r['name'])
            continue
        print('| `%s` | `%s` | %d / %d | %s | %s | %s | %s |' % (
            r['name'], r['handler_pc'], r['body_insns_strict'], r['body_insns_loose'],
            'REACHED' if r['helper_reachable'] else 'not reached',
            r['helper_depth'] if r['helper_reachable'] else '—',
            ' -> '.join(r['helper_chain']) if r['helper_chain'] else '—',
            ('REACHED d=%s' % r['cpi_depth']) if r['cpi_reachable'] else ('not reached' if cpi else 'n/a')))


if __name__ == '__main__':
    main()
