#!/usr/bin/env python3
"""resolve.py MERGED OUT [OLD NEW]... : take the Round34 side ("<<<<<<<" part) of every conflict and
apply the given literal replacements (each must hit exactly once inside the conflict sides).
"\\n" in NEW means newline."""
import sys, re
s = open(sys.argv[1]).read(); out = sys.argv[2]
reps = [(sys.argv[i], sys.argv[i + 1].replace('\\n', '\n')) for i in range(3, len(sys.argv), 2)]
parts = re.split(r'^<<<<<<< [^\n]*\n(.*?)^=======\n(.*?)^>>>>>>> [^\n]*\n', s, flags=re.S | re.M)
res = []; used = [0] * len(reps)
for k, p in enumerate(parts):
    if k % 3 == 0: res.append(p); continue
    if k % 3 == 2: continue
    for i, (a, b) in enumerate(reps):
        c = p.count(a)
        if c: assert c == 1, (a, c); p = p.replace(a, b); used[i] += 1
    res.append(p)
assert all(used), used
open(out, 'w').write(''.join(res))
print('resolved', len(parts) // 3, 'conflicts')
