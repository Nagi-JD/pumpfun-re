# pl.py FILE "srcline:target,..." : place the error!( on each given source line at target line (in text order)
import sys, json, subprocess, re
f = sys.argv[1]
pairs = [tuple(map(int, p.split(":"))) for p in sys.argv[2].split(",")]
s = open(f).read()
offs = [m.start() for m in re.finditer(r"error!\(", s)]
lines = [s[:o].count("\n") + 1 for o in offs]
spec = []; prev = -1
for src, tgt in pairs:
    # pick the first error! on src line after prev index (allow "src.k" not needed)
    idx = next(i for i, l in enumerate(lines) if l == src and i > prev)
    spec.append(["err", idx - prev - 1, tgt]); prev = idx
json.dump(spec, open("/tmp/pl.json", "w"))
print(subprocess.run(["python3", "/home/nagi/ammresearch/tools/place.py", f, "/tmp/pl.json"], capture_output=True, text=True).stdout.strip())
