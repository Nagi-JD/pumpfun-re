#!/usr/bin/env python3
"""helper_at.py FILE SEEK FUNC OCC DFILE DLINE : rewrite the OCC-th call of helper FUNC (add/sub/narrow)
after the first occurrence of SEEK into a per-site closure with an explicit err_at! origin."""
import sys, re
sys.path.insert(0, "/home/nagi/pumpround23")
from place import args
path, seek, fn, occ, df, dl = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5], int(sys.argv[6])
s = open(path).read(); cur = s.index(seek)
rx = re.compile(r"(?<![\w.:])" + fn + r"\(")
ms = [m for m in rx.finditer(s, cur) if s[max(0, m.start() - 3):m.start()] != "fn "]
m = ms[occ]; a, end = args(s, m.end() - 1)
o = 'err_at!(PumpError::%s,"programs/pump/src/%s",%d)' % ("Truncation" if fn == "narrow" else "Overflow", df, dl)
if fn == "add": new = "(%s).checked_add(%s).ok_or_else(||%s)" % (a[0], a[1], o)
elif fn == "sub": new = "(%s).checked_sub(%s).ok_or_else(||%s)" % (a[0], a[1], o)
else: new = "u64::try_from(%s).map_err(|_|%s)" % (a[0], o)
open(path, "w").write(s[:m.start()] + new + s[end:]); print("ok", fn, dl)
