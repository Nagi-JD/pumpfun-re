#!/usr/bin/env python3
"""retarget.py REF_FILE NEW_FILE LINE[,LINE...] [--write]
Find, in REF_FILE (our placed Round23 version), the error!( occurrences that sit on the given
deployed lines. Locate the same occurrences in NEW_FILE by their preceding code context
(whitespace-insensitive), then add/remove the blank newlines directly before `error!(` so each one
sits on its deployed line again. Only padding newlines are touched; no code changes."""
import sys, re
ref = open(sys.argv[1]).read(); path = sys.argv[2]; new = open(path).read()
targets = [int(x) for x in sys.argv[3].split(',')]
write = '--write' in sys.argv
RX = re.compile(r'error!\(')
def key(s, i, n=120):
    t = re.sub(r'\s+', '', s[max(0, i - 4000):i]); return t[-n:]
def line(s, i): return s.count('\n', 0, i) + 1
refocc = {line(ref, m.start()): m.start() for m in RX.finditer(ref)}
plan = []
for t in targets:
    if t not in refocc: print('ref has no error! on line', t); continue
    k = key(ref, refocc[t])
    hits = [m.start() for m in RX.finditer(new) if key(new, m.start()) == k]
    if len(hits) != 1:
        hits = [m.start() for m in RX.finditer(new) if key(new, m.start(), 60) == key(ref, refocc[t], 60)]
    if len(hits) != 1: print('line', t, 'context hits', len(hits)); continue
    plan.append((t, hits[0]))
plan.sort(key=lambda p: p[1])
# apply top-down, recomputing offsets
done = 0
for t, _ in plan:
    k = key(ref, refocc[t])
    i = [m.start() for m in RX.finditer(new) if key(new, m.start()) == k or key(new, m.start(), 60) == key(ref, refocc[t], 60)][0]
    cur = line(new, i); d = t - cur
    j = i
    while j > 0 and new[j - 1] == '\n': j -= 1
    avail = i - j
    if d > 0: new = new[:i] + '\n' * d + new[i:]
    elif d < 0:
        if -d > avail: print('line', t, 'needs', -d, 'fewer lines, only', avail, 'padding'); continue
        new = new[:i + d] + new[i:]
    done += 1
    print('line %d: was %d, moved %+d' % (t, cur, d))
print('retargeted', done, 'of', len(targets))
if write: open(path, 'w').write(new)
