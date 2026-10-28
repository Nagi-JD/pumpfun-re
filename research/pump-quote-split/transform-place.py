#!/usr/bin/env python3
"""pump_quote step 2-3 (final v3): per-site Overflow closures + greedy layout.

Only exact targets drive the layout (those whose deployed windows can match):
  constant_product -> 131, 134, 137, 139   (fn window 0x62170)
  price            -> 199, 201, 212, 222, 230, 235, 241
                     (fn window 0x62aa0 + standalone arms 0x63530/0x63738 at 212/222)
Everything else flows in natural order (whitespace-only compaction + padding).
"""
SRC = '/home/tc147/pumpwork/p1/programs/pump/src/pump_quote.rs'
DST = '/home/tc147/pumpwork/p2/programs/pump/src/pump_quote.rs'

lines = open(SRC).read().split('\n')

out = []
for l in lines:
    if l.strip().startswith('fn overflow()'):
        continue
    l = l.replace('.ok_or_else(overflow)', '.ok_or_else(|| error!(PumpError::Overflow))')
    l = l.replace('.map_err(|_| overflow())', '.map_err(|_| error!(PumpError::Overflow))')
    out.append(l)
lines = out


def balanced(l):
    return (l.count('(') + l.count('[') + l.count('{')
            == l.count(')') + l.count(']') + l.count('}'))


def is_anchor(l):
    return 'error!(' in l or 'require' in l


def compact(blk):
    out = []
    for l in blk:
        anc = is_anchor(l)
        prev_anc = bool(out) and is_anchor(out[-1])
        if (out and not anc and not prev_anc and not balanced(out[-1])
                and not out[-1].rstrip().endswith('{') and l.strip()
                and '//' not in out[-1] and not l.strip().startswith('//')):
            out[-1] = out[-1].rstrip() + ' ' + l.strip()
        else:
            out.append(l)
    return out


def fn_span(name):
    a = next(i for i in range(len(lines)) if f'fn {name}' in lines[i])
    if lines[a - 1].strip().startswith('#['):
        a -= 1
    depth, b = 0, None
    for i in range(a, len(lines)):
        depth += lines[i].count('{') - lines[i].count('}')
        if i > a and depth <= 0 and lines[i].strip() == '}':
            b = i
            break
    assert b, name
    return a, b


order = ['decode_curve', 'ancestor', 'control_entry', 'root_seed', 'walk',
         'convert', 'constant_product', 'price', 'vault_amount', 'pool_record']
spans = {n: fn_span(n) for n in order}
header = compact(lines[:min(a for a, _ in spans.values())])
fns = {n: compact(lines[a:b + 1]) for n, (a, b) in spans.items()}

EXACT = {
    'constant_product': [131, 134, 137, 139],
    'price': [199, 201, 212, 222, 241],
}

# price is rewritten to the deployed fingerprint (window 0x62aa0 carries exactly
# O@199 D@201 O@212 O@222 6104@241): the deployed computes `difference` once and
# divides by `real` without a separate guard. The duplicate checked_sub is
# value-identical (its check is already covered at 199), and the `real != 0`
# require is not present in the deployed closure set - keeping it would bake a
# 6th closure the deployed does not have.
PRICE_NEW = [
    '#[inline(never)]',
    'fn price(g: &Global, seed: u64, records: &[Record]) -> Result<u64> {',
    '    let real = g.initial_real_token_reserves;',
    '    let numerator = real as u128 * seed as u128;',
    '    let difference = g.initial_virtual_token_reserves.checked_sub(real).ok_or_else(|| error!(PumpError::Overflow))?;',
    '    require!(difference != 0, PumpError::DivisionByZero);',
    '    let mut amount = numerator / difference as u128;',
    '    for record in records.iter().rev() { amount = convert(*record, amount)?; }',
    '    #[inline(never)] fn mul_ovf() -> anchor_lang::error::Error { error!(PumpError::Overflow) }',
    '    #[inline(never)] fn try_ovf() -> anchor_lang::error::Error { error!(PumpError::Overflow) }',
    '    let numerator = amount.checked_mul(difference as u128).ok_or_else(mul_ovf)?;',
    '    let reserves = u64::try_from(numerator / real as u128).map_err(|_| try_ovf())?;',
    '    require_gte!(reserves, 1, PumpError::QuoteReservesOutOfRange);',
    '    Ok(reserves)',
    '}',
]
fns['price'] = PRICE_NEW

report = []
out = list(header)
for name in order:
    blk = fns[name]
    cl = [i for i, l in enumerate(blk) if is_anchor(l)]
    tg = EXACT.get(name)
    if tg:
        assert len(cl) == len(tg), (name, cl, tg)
    newblk = []
    for j, ci in enumerate(cl):
        seg = blk[0:ci] if j == 0 else blk[cl[j - 1] + 1:ci]
        newblk += seg
        if tg:
            base = len(out) + len(newblk)
            need = tg[j] - 1 - base
            if need < 0:
                report.append(f'{name}[{j}] target {tg[j]} already passed (pos {base})')
            else:
                newblk += [''] * need
        newblk.append(blk[ci])
    newblk += blk[cl[-1] + 1:]
    out += newblk
    out += ['']

open(DST, 'w').write('\n'.join(out))
chk = open(DST).read().split('\n')
for name, tg in EXACT.items():
    for t in tg:
        if not is_anchor(chk[t - 1]):
            report.append(f'MISSED {name} target {t}: {chk[t - 1]!r}')
print('\n'.join(report) if report else 'all exact targets hit')
print('total lines', len(chk) - 1)
