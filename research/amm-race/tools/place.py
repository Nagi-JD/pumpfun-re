#!/usr/bin/env python3
"""place.py FILE SPEC.json : rewrite helper calls into per-site closures with error! on a target line.
SPEC: list of [func, occurrence_index_after_cursor, target_line]. Pads with newlines inside the
expression, or joins earlier statement lines (after the cursor) when the site is already too low."""
import sys, json, re
NL = "\n"
FORMS = {"add": ("({0}).checked_add({1}).ok_or_else(||{pad}error!(PumpAmmError::Overflow))", 2),
         "sub": ("({0}).checked_sub({1}).ok_or_else(||{pad}error!(PumpAmmError::Overflow))", 2),
         "n": ("u64::try_from({0}).map_err(|_|{pad}error!(PumpAmmError::Truncation))", 1),
         "narrow": ("u64::try_from({0}).map_err(|_|{pad}error!(PumpAmmError::Truncation))", 1)}

def args(s, i):
    d = 0; out = []; st = i + 1
    for j in range(i, len(s)):
        c = s[j]
        if c in "([{": d += 1
        elif c in ")]}":
            d -= 1
            if d == 0:
                out.append(s[st:j]); return out, j + 1
        elif c == "," and d == 1:
            out.append(s[st:j]); st = j + 1
    raise ValueError

def main():
    path, spec = sys.argv[1], json.load(open(sys.argv[2]))
    s = open(path).read(); cur = 0
    for fn, occ, line in spec:
        if fn in ("okor", "err"):
            rx = re.compile(r"\.ok_or\(PumpAmmError::Overflow\)" if fn == "okor" else r"error!\(")
            m = list(rx.finditer(s, cur))[occ]
            pre = s[:m.start()]; curline = pre.count(NL) + 1; k = line - curline
            if k < 0: print("SKIP", fn, line, curline); continue
            new = (".ok_or_else(||" + NL * k + "error!(PumpAmmError::Overflow))") if fn == "okor" else (NL * k + "error!(")
            s = pre + new + s[m.end():]; cur = len(pre) + len(new); continue
        rx = re.compile(r"(?<![\w.:])" + fn + r"\(")
        ms = [m for m in rx.finditer(s, cur) if s[max(0, m.start() - 3):m.start()] != "fn "]
        m = ms[occ]; a, end = args(s, m.end() - 1)
        form, n = FORMS[fn]; assert len(a) == n, (fn, a)
        pre = s[:m.start()]; curline = pre.count(NL) + 1
        k = line - curline - "".join(a).count(NL)
        if k < 0:
            lines = pre[cur:].split(NL); need = -k; i = len(lines) - 2
            while need and i >= 0:
                x, y = lines[i], lines[i + 1]
                if x.rstrip().endswith((";", "{", "}", ",")) and "//" not in x and not y.lstrip().startswith(("#", "//")):
                    lines[i] = x + " " + y.lstrip(); del lines[i + 1]; need -= 1
                i -= 1
            if need:
                print("SKIP %s at %d (at %d)" % (fn, line, curline)); continue
            pre = pre[:cur] + NL.join(lines); k = 0
        new = form.format(*a, pad=NL * k)
        s = pre + new + s[end:]
        cur = len(pre) + len(new)
    open(path, "w").write(s)
    print("ok")

main()
