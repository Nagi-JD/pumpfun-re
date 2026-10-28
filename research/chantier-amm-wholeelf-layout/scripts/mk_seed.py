import sys
sys.path.insert(0, "/home/nagi/pumpround34/scripts")
import pump_text_layout as PTL
from pathlib import Path

SCR = Path("/home/nagi/pumpround34/scripts")
U7 = Path("/home/nagi/shaw-src/research/claude-amm-union7-20261028/layout/ordered.ld")
OUT = Path("/home/nagi/ammlayout/seed_text_only.ld")
OUT.parent.mkdir(parents=True, exist_ok=True)

default = (SCR / "pump_text_layout_default.ld").read_text()
u7 = U7.read_text().split("\n")

# Extract .text selector lines: between '  .text : {' and the catch-all '*(.text*)' / '} :text'
start = next(i for i, l in enumerate(u7) if l.strip() == ".text : {")
# collect following lines until we hit the catch-all or '} :text'
sels = []
i = start + 1
while i < len(u7):
    l = u7[i]
    if l.strip() == "*(.text*)" or l.strip().startswith("} :text"):
        break
    sels.append(l)
    i += 1
# normalize indentation to 4 spaces as SELECTOR regex expects '^    \*...'
norm = []
seen = set()
for s in sels:
    t = s.strip()
    if not t:
        continue
    line = "    " + t
    if line in seen:
        continue
    seen.add(line)
    norm.append(line)
print("extracted .text selectors:", len(norm))
RULE = '  .text : { *(.text*) } :text'
assert default.count(RULE) == 1, "default .text rule not found"
head, tail = default.split(RULE)
script = head + '  .text : {\n' + '\n'.join(norm) + '\n    *(.text*)\n  } :text' + tail
# validate
n = PTL.check_script(default, script)
print("check_script OK, selectors:", n)
OUT.write_text(script)
print("wrote", OUT, len(script), "bytes")
