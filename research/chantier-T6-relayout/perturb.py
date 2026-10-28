import sys
inp, out, pat = sys.argv[1:4]
lines = open(inp).read().split('\n')
sel = [i for i, l in enumerate(lines) if l.startswith('    *') and pat in l]
assert len(sel) == 1, f"expected 1 match, got {len(sel)}: {sel}"
i = sel[0]
line = lines.pop(i)
first = next(j for j, l in enumerate(lines) if l.startswith('    *'))
lines.insert(first, line)
open(out, 'w').write('\n'.join(lines))
print(f"moved selector containing {pat!r} from line {i} to {first}")
