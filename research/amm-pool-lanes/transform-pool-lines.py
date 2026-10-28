#!/usr/bin/env python3
"""pool.rs line layout v2: place each error! closure on its deployed line.

Segments (lines before the first error!, between two error!s) are adjusted to
the exact deployed spacing by joining lines (whitespace-only, zero codegen
impact) or inserting blank lines. Per-block asserts verify every target line.

Deployed map: 386 DivisionByZero (market_cap), 408/417/426/484 Overflow
(singles), 439/440 (effective_quote_reserves), 458/462/465/469 (accrue_fees).
"""
import shutil

SRC = '/home/tc147/pumpwork/u4b/programs/pump-amm/src/state/pool.rs'
DST = '/home/tc147/pumpwork/u5/programs/pump-amm/src/state/pool.rs'

lines = open(SRC).read().split('\n')

order = ['accrue_fees', 'effective_quote_reserves', 'total_accrued_fees',
         'available_quote_reserves', 'take_accrued_fees', 'market_cap',
         'total_virtual_quote_reserves', 'can_boost']
fns = {}
for name in order:
    a = next(i for i in range(len(lines)) if f'pub fn {name}' in lines[i])
    if '#[inline(never)]' in lines[a - 1]:
        a -= 1
    b = next(i for i in range(a + 1, len(lines)) if lines[i] == '    }')
    fns[name] = lines[a:b + 1]

seq = [('market_cap', [386]),
       ('total_accrued_fees', [408]),
       ('available_quote_reserves', [417]),
       ('total_virtual_quote_reserves', [426]),
       ('can_boost', []),
       ('effective_quote_reserves', [439, 440]),
       ('accrue_fees', [458, 462, 465, 469]),
       ('take_accrued_fees', [484])]


def adjust(seg, needed):
    """Return seg with exactly `needed` lines. Whitespace-only removal first,
    then join adjacent non-blank lines (never drops tokens)."""
    seg = [l for l in seg]
    while len(seg) > needed and any(not l.strip() for l in seg):
        k = next(i for i, l in enumerate(seg) if not l.strip())
        del seg[k]
    while len(seg) > needed:
        k = next((i for i in range(len(seg) - 1)
                  if seg[i].strip() and seg[i + 1].strip() and '//' not in seg[i]), None)
        assert k is not None, f'cannot shrink segment to {needed}: {seg}'
        seg[k:k + 2] = [seg[k].rstrip() + ' ' + seg[k + 1].strip()]
    while len(seg) < needed:
        seg.append('')
    return seg


out = ['use super::*;', 'use crate::PumpAmmError;', '', 'impl Pool {']
for bi, (name, targets) in enumerate(seq):
    blk = list(fns[name])
    cl = [i for i, l in enumerate(blk) if 'error!(' in l]
    assert len(cl) == len(targets), (name, cl, targets)
    if targets:
        newblk = []
        newblk += adjust(blk[0:cl[0]], targets[0] - 1 - len(out))
        newblk.append(blk[cl[0]])
        for j in range(1, len(cl)):
            newblk += adjust(blk[cl[j - 1] + 1:cl[j]], targets[j] - targets[j - 1] - 1)
            newblk.append(blk[cl[j]])
        newblk += blk[cl[-1] + 1:]
        blk = newblk
    out += blk
    out += ['']
out += ['}', '']

open(DST, 'w').write('\n'.join(out))
chk = open(DST).read().split('\n')
for name, targets in seq:
    for tgt in targets:
        assert 'error!(' in chk[tgt - 1], f'line {tgt}: {chk[tgt - 1]!r}'
print('laid out:', {n: t for n, t in seq if t})
print('total lines', len(chk) - 1)
