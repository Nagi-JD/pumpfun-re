#!/usr/bin/env python3
"""compare_dispositions.py - quantify the defect the body recovery fixes.

Reads maps/dispositions.json (old, linear-span heuristic) and maps/<prog>_bodies.json
(new, CFG descent) and prints the before/after metric table used in
docs/analysis/S1b_handler_bodies.md.

Usage: compare_dispositions.py maps/dispositions.json maps/pump_bodies.json [more...]
"""
import json
import sys


def main():
    with open(sys.argv[1]) as f:
        old = json.load(f)
    print('| program | handlers | insns old (min/med/max) | insns new (min/med/max) | has_cpi old | has_cpi new | syscalls old | syscalls new |')
    print('|---|---:|---|---|---:|---:|---:|---:|')
    for path in sys.argv[2:]:
        prog = path.split('/')[-1].replace('_bodies.json', '')
        with open(path) as f:
            new = json.load(f)
        newrows = new['handlers']
        newmap = {r['name']: r for r in newrows}
        oldrows = [v for k, v in old.get(prog, {}).items() if k in newmap]
        def med(xs):
            xs = sorted(xs)
            return xs[len(xs) // 2] if xs else 0
        oi = [r['func_insns'] for r in oldrows]
        ni = [r['body_insns'] for r in newrows]
        print('| %s | %d | %d / %d / %d | %d / %d / %d | %d | %d | %d | %d |' % (
            prog, len(newrows), min(oi), med(oi), max(oi), min(ni), med(ni), max(ni),
            sum(1 for r in oldrows if r['has_cpi']),
            sum(1 for r in newrows if r['has_cpi']),
            sum(sum(len(v) for v in r['syscalls'].values()) for r in oldrows),
            sum(sum(len(v) for v in r['syscalls_transitive'].values()) for r in newrows)))
        # name-level detail for the handlers whose body was most understated
        detail = []
        for r in sorted(oldrows, key=lambda x: x['func_insns'] - newmap[x['name']]['body_insns']):
            detail.append((r['name'], r['func_insns'], newmap[r['name']]['body_insns']))
        worst = sorted(detail, key=lambda t: t[2] - t[1], reverse=True)[:5]
        print('  worst understated in %s: %s' % (prog, ', '.join(
            '`%s` %d->%d' % (n, a, b) for n, a, b in worst)))


if __name__ == '__main__':
    main()
