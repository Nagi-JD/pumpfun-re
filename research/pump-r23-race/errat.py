#!/usr/bin/env python3
"""errat.py SRCDIR SPEC.json : explicit Anchor error origin at a site.
Adds err_at! macro to the start of lib.rs line 1 (no line shift) once, then for each
[file, needle_regex_on_error_call, occurrence, deployed_file, deployed_line] replaces the
`error!(X)` at that occurrence with err_at!(X,"programs/pump/src/<deployed_file>",line)."""
import sys, json, re, os
d = sys.argv[1]; spec = json.load(open(sys.argv[2]))
M = ('macro_rules! err_at{($e:expr,$f:literal,$l:literal)=>{anchor_lang::error::Error::from('
     'anchor_lang::error::AnchorError{error_name:$e.name(),error_code_number:$e.into(),'
     'error_msg:$e.to_string(),error_origin:Some(anchor_lang::error::ErrorOrigin::Source('
     'anchor_lang::error::Source{filename:$f,line:$l})),compared_values:None})}} ')
lib = os.path.join(d, "lib.rs"); s = open(lib).read()
if not s.startswith("macro_rules! err_at"): open(lib, "w").write(M + s)
for f, needle, occ, df, dl in spec:
    p = os.path.join(d, f); s = open(p).read()
    ms = list(re.finditer(r"error!\((" + needle + r")\)", s))
    if occ >= len(ms): print("SKIP", f, needle, occ); continue
    m = ms[occ]
    s = s[:m.start()] + 'err_at!(%s,"programs/pump/src/%s",%d)' % (m.group(1), df, dl) + s[m.end():]
    open(p, "w").write(s); print("ok", f, dl)
