#!/usr/bin/env python3
"""REAL reconstruction: multi_hop 941 Overflow closure.

1. Extract block-2's checked_add chain into `expected_destination` (behavior
   identical: same checks, same error variant, same evaluation results).
2. Keep 579/586/636/671/718 (+307) closure lines intact via compensating
   padding in the 518-closure.
3. Join the two event-literal field blocks (pure whitespace - no baked lines).
4. Place the helper at the tail so its error! lands exactly on line 941,
   matching the deployed multi_hop_swap.rs:941 Overflow closure.
"""
import shutil, sys

SRC = '/home/tc147/pumpwork/u2/programs/pump-amm/src/multi_hop.rs'
DST = '/home/tc147/pumpwork/u4b/programs/pump-amm/src/multi_hop.rs'

shutil.copyfile(SRC, DST)
lines = open(DST).read().split('\n')

def find(sub, start=0):
    for i in range(start, len(lines)):
        if sub in lines[i]:
            return i
    raise AssertionError(f'not found: {sub!r}')

# ---- 1. replace block-2 (lines 318-330, 1-based) with the helper call -------
i0 = find('if !output_native && source.key() != destination.key() {')
i1 = find('}', find('PumpAmmError::MultiHopCurveRunMismatch', i0))
# block2 spans i0..i1 (0-based) = the if statement incl. closing brace
assert 'require_eq!' in lines[i0 + 1] or 'expected' in lines[i0 + 1], lines[i0 + 1]
new_block = [
    '            if !output_native && source.key() != destination.key() {',
    '                let expected = expected_destination(before, output, buyback, destination.key() == a.buyback_fee_recipient.key())?;',
    '                require_eq!(',
    '                    token_amount(&destination)?, expected,',
    '                    PumpAmmError::MultiHopCurveRunMismatch',
    '                );',
    '            }',
]
removed = i1 - i0 + 1
lines[i0:i1 + 1] = new_block
delta = len(new_block) - removed
print(f'step1: block2 {removed} -> {len(new_block)} lines (delta {delta})')

# ---- 2. compensate delta inside the 518-closure (keeps 579..718) -----------
j = find('let received = amount.checked_sub(input_tf).ok_or_else(||')
if delta < 0:
    lines[j + 1:j + 1] = [''] * (-delta)
    print(f'step2: inserted {-delta} padding lines after line {j + 1}')

# ---- 3. join event-literal statements (whitespace only) -------------------
for label in ('SellEvent {', 'BuyEvent {'):
    s = find(label)
    a = s
    while 'emit_event(' not in lines[a]:
        a -= 1
    b = find(')?;', s)
    joined = ' '.join(x.strip() for x in lines[a:b + 1])
    lines[a:b + 1] = [joined]
    print(f'step3: emit_event {label} {b - a + 1} -> 1 line')

# ---- 4. append helper with error! on line 941 -----------------------------
helper_head = [
    '',
    '#[inline(always)]',
    'fn expected_destination(before: u64, output: u64, buyback: u64, dest_is_buyback: bool) -> Result<u64> {',
    '    before',
    '        .checked_add(output)',
    '        .and_then(|v| v.checked_add(if dest_is_buyback {',
    '            buyback',
    '        } else {',
    '            0',
    '        }))',
    '        .ok_or_else(||',
]
helper_tail = ['error!(PumpAmmError::Overflow))', '}']
start = len(lines)  # helper head begins at 1-based line start+1
err_line = start + len(helper_head) + 1  # first blank line index+... computed below
# error! must be at 1-based 941 => index 940
pad = 940 - (start + len(helper_head))
assert pad >= 0, f'no room: helper would need error! before {start + len(helper_head) + 1}'
lines[start:start] = helper_head + [''] * pad + helper_tail
assert 'error!(PumpAmmError::Overflow))' in lines[940], lines[940]
print(f'step4: helper at line {start + 1}, error! verified at line 941')

# ---- asserts: matched closure lines preserved -----------------------------
for ln, needle in [(307, 'NotEnoughRemainingAccounts'), (579, 'error!(PumpAmmError::Overflow)'),
                   (586, 'error!(PumpAmmError::Overflow)'), (636, 'error!(PumpAmmError::Overflow)'),
                   (671, 'error!(PumpAmmError::Overflow)'), (718, 'error!(PumpAmmError::Overflow)')]:
    assert needle in lines[ln - 1], f'line {ln} broken: {lines[ln - 1]!r}'
print('asserts: 307/579/586/636/671/718 preserved, 941 placed')

open(DST, 'w').write('\n'.join(lines))
print('written:', DST, 'total lines', len(lines) - 1)
