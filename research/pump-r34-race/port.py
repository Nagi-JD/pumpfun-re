#!/usr/bin/env python3
"""port.py BASE_OLD BASE_NEW TARGET [--write]
Port the BASE_OLD -> BASE_NEW changes (Round23 -> Round34) onto TARGET (our placed file) without
moving TARGET's lines: each hunk's old text is found whitespace-insensitively (TARGET may have joined
or padded those lines), top-down after the previous hunk, and replaced by the new text squeezed into
the same number of newlines as the matched span. Pure insertions are appended to the anchor line
(no new newline); an insertion at the very end of the file is appended as-is."""
import sys, re, difflib
old = open(sys.argv[1]).read().split('\n'); new = open(sys.argv[2]).read().split('\n')
tpath = sys.argv[3]; t = open(tpath).read()
def pat(lines):
    toks = [re.escape(x) for x in re.split(r'\s+', ' '.join(lines).strip()) if x]
    return r'\s*'.join(toks)
def squeeze(lines, k):
    if len(lines) > k + 1:
        assert not any('//' in x for x in lines[k:-1]), 'would join a // comment: %r' % lines
    if k <= 0: return ' '.join(x.strip() for x in lines if x.strip())
    if len(lines) <= k + 1: return '\n'.join(lines) + '\n' * (k + 1 - len(lines))
    return '\n'.join(lines[:k] + [' '.join(x.strip() for x in lines[k:] if x.strip())])
def ctxpos(i1, cur):
    # advance cursor to the end of the nearest preceding non-blank old line (bounded search)
    k = i1 - 1
    while k >= 0 and not old[k].strip(): k -= 1
    if k < 0: return cur
    m = re.compile(pat([old[k]])).search(t, cur)
    return m.end() if m else None
sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
cur = 0
LENIENT = '--lenient' in sys.argv; NOAPPEND = '--noappend' in sys.argv
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == 'equal': continue
    nl = new[j1:j2]
    if tag == 'insert':
        if i1 >= len(old) - 1 and NOAPPEND: print('SKIP append at end'); continue
        if i1 >= len(old) - 1:
            t = t.rstrip('\n') + '\n' + '\n'.join(nl).strip('\n') + '\n'; print('append at end'); continue
        e = ctxpos(i1, cur)
        if e is None:
            if LENIENT: print('SKIP insert at old line %d (anchor not found)' % i1); continue
            sys.exit('insert anchor not found for old line %d' % i1)
        body = ' '.join(x.strip() for x in nl if x.strip())
        assert '//' not in body, 'insert with // comment: %r' % body
        if body: t = t[:e] + ' ' + body + t[e:]
        cur = e + len(body) + 1
        print('insert at line %d (+0 lines)' % (t.count('\n', 0, e) + 1)); continue
    ol = old[i1:i2]
    if not any(x.strip() for x in ol):
        print('skip blank-only hunk %d-%d' % (i1 + 1, i2)); continue
    m = re.compile(pat(ol)).search(t, cur)
    if not m:
        if LENIENT: print('SKIP hunk %d-%d (not found)' % (i1 + 1, i2)); continue
        sys.exit('hunk %d-%d not found after cursor' % (i1 + 1, i2))
    k = t.count('\n', m.start(), m.end())
    rep = squeeze(nl, k) if nl else '\n' * k
    t = t[:m.start()] + rep + t[m.end():]; cur = m.start() + len(rep)
    print('%s %d-%d -> %d lines in %d newlines (line %d)' % (tag, i1 + 1, i2, len(nl), k, t.count('\n', 0, m.start()) + 1))
if '--write' in sys.argv: open(tpath, 'w').write(t); print('written')
