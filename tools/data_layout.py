#!/usr/bin/env python3
"""tools/data_layout.py  -  data-section layout solver for sBPF whole-ELF matching.

Usage:
  python3 tools/data_layout.py DEPLOYED.so CANDIDATE-SYMBOLS.so [--cand-stripped STRIPPED.so]
                               [-o out.json] [--window 0xADDR ...]

Purpose:
  drift_solver.py ranks the .text intervals that spoil call immediates. This tool
  is its data counterpart. A matched window whose raw bytes differ in an lddw
  (opcode 0x18, 64-bit immediate = data address) reaches raw only when the
  referenced record sits at the deployed address. That address is
      section_base + intra_offset
  so a data reference is fixed by two independent layers:
    * section_base  : set by the size of everything linked before the section
                      (.text length first). Closed by .text layout work.
    * intra_offset  : set by the order, size and dedup of the records inside
                      .rodata / .data.rel.ro. Closed by data layout work
                      (source line numbers, declaration order, record dedup).

Reported (JSON):
  sections           base/size of .text, .rodata, .data.rel.ro on both sides
  windows            per class counts over matched, raw-failing windows:
                       data_aligned  every differing lddw points to the same
                                     section and the same intra offset (or, for
                                     .text targets, the same offset inside the
                                     paired function); remaining residual is
                                     section bases and call immediates only
                       data_residual at least one differing lddw points to a
                                     different record
                       other         a differing slot that is neither call nor lddw
  lddw_sites         paired differing lddw sites: total, intra-aligned, by section
  locations          core::panic::Location records (24 B: &str file, line, col) in
                     .data.rel.ro; counts per side and the paired list from lddw
                     residuals, split into equal / line / column / file mismatches
                     (the source-line worklist)
  paths              .rs path strings present on one side only
  prefix             bytes of .rodata equal from the section start, and 8-byte
                     slots of .data.rel.ro equal from the section start with
                     pointers compared as (section, intra offset)
  detail             per requested --window: every differing slot

Window pairing and normalization are the ones in drift_solver.py / measure.py
(size, normalized sha256, relocation pattern).
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drift_solver import Elf, enrich, pattern_pairs, sha, unique_pairs, windows  # noqa: E402

DATA = (".text", ".rodata", ".data.rel.ro")


def bounds(e: Elf):
    out = {}
    for n in DATA:
        s = e.secs.get(n)
        if s:
            out[n] = {"addr": s[3], "offset": s[4], "size": s[5]}
    return out


def where(sec, addr):
    for n, s in sec.items():
        if s["addr"] <= addr < s["addr"] + s["size"]:
            return n, addr - s["addr"]
    return None, addr


def read_at(e: Elf, sec, addr, n):
    name, intra = where(sec, addr)
    if name is None:
        return b""
    s = sec[name]
    o = s["offset"] + intra
    return e.b[o : o + min(n, s["size"] - intra)]


def lddw_imm(b, at):
    return struct.unpack_from("<I", b, at + 4)[0] | (struct.unpack_from("<I", b, at + 12)[0] << 32)


def locations(e: Elf, sec):
    """Location records: {addr: (file, line, col)}."""
    out = {}
    if ".rodata" not in sec or ".data.rel.ro" not in sec:
        return out
    r = sec[".rodata"]
    d = sec[".data.rel.ro"]
    b = e.b
    for a in range(d["addr"], d["addr"] + d["size"] - 23, 8):
        o = d["offset"] + (a - d["addr"])
        lo, p = struct.unpack_from("<II", b, o)
        n = struct.unpack_from("<Q", b, o + 8)[0]
        if lo or not (r["addr"] <= p < r["addr"] + r["size"]) or not 0 < n < 256:
            continue
        s = read_at(e, sec, p, n)
        if len(s) == n and s.endswith(b".rs"):
            line, col = struct.unpack_from("<II", b, o + 16)
            try:
                out[a] = (s.decode(), line, col)
            except UnicodeDecodeError:
                pass
    return out


PATH_RE = re.compile(rb"(?:programs/|(?<![A-Za-z0-9_/])src/)[A-Za-z0-9_/-]+\.rs")


def rs_paths(e: Elf, sec):
    s = sec.get(".rodata")
    if not s:
        return set()
    blob = e.b[s["offset"] : s["offset"] + s["size"]]
    found = {loc[0] for loc in locations(e, sec).values()}
    found.update(m.group().decode() for m in PATH_RE.finditer(blob))
    return found


def slot_diffs(O, C, oa, ca, n):
    out = []
    i = 0
    while i < n:
        if O.b[oa + i] == 0x18:
            if O.b[oa + i : oa + i + 16] != C.b[ca + i : ca + i + 16]:
                if C.b[ca + i] == 0x18:
                    out.append(("lddw", i, lddw_imm(O.b, oa + i), lddw_imm(C.b, ca + i)))
                else:
                    out.append(("other", i, None, None))
            i += 16
            continue
        if O.b[oa + i : oa + i + 8] != C.b[ca + i : ca + i + 8]:
            kind = "call" if O.b[oa + i] == 0x85 and C.b[ca + i] == 0x85 else "other"
            out.append((kind, i, None, None))
        i += 8
    return out


def rebased_prefix(O, C, so, sc, locate_o, locate_c, name):
    """8-byte slots of `name` equal from the start; pointers compared as (section, intra)."""
    a = so[name]
    b = sc[name]
    n = min(a["size"], b["size"]) // 8
    for k in range(n):
        x = O.b[a["offset"] + 8 * k : a["offset"] + 8 * k + 8]
        y = C.b[b["offset"] + 8 * k : b["offset"] + 8 * k + 8]
        if x == y:
            continue
        px = struct.unpack_from("<Q", x)[0] >> 32
        py = struct.unpack_from("<Q", y)[0] >> 32
        if x[:4] == y[:4] == bytes(4):
            wx, wy = locate_o(px), locate_c(py)
            if wx[0] is not None and wx == wy:
                continue
        return 8 * k
    return 8 * n


def solve(dep: Path, syms: Path, stripped: Path | None = None, detail=()):
    O = Elf(dep)
    S = Elf(syms)
    if stripped is not None:
        C = Elf(stripped)
        if C.b[C.lo : C.hi] != S.b[S.lo : S.hi]:
            raise SystemExit("candidate-stripped .text differs from symbols .text")
    else:
        C = S
    so, sc = bounds(O), bounds(C)

    os_ = enrich(O, windows(O))
    cs = enrich(C, windows(C, S.funcs))
    ob = {r["start"]: r for r in os_}
    cb = {r["start"]: r for r in cs}
    rawset = {r["raw_sha256"] for r in cs}
    byo = collections.defaultdict(list)
    for ca, oa in pattern_pairs(os_, cs):
        byo[oa].append(ca)
    up = unique_pairs(os_, cs)
    o2c = {oa: ca for ca, oa in up}
    c2o = {ca: oa for ca, oa in up}
    o_starts = sorted(ob)
    c_starts = sorted(cb)

    import bisect

    def owner(starts, table, addr):
        i = bisect.bisect_right(starts, addr) - 1
        if i < 0:
            return None
        r = table[starts[i]]
        return r["start"] if addr < r["end"] else None

    def locate_o(p):
        n, intra = where(so, p)
        if n == ".text":
            w = owner(o_starts, ob, p)
            return ("text", w, p - w) if w is not None else (None, p)
        return (n, intra)

    def locate_c(p):
        n, intra = where(sc, p)
        if n == ".text":
            w = owner(c_starts, cb, p)
            if w is None or w not in c2o:
                return (None, p)
            return ("text", c2o[w], p - w)
        return (n, intra)

    lo_o, lo_c = locations(O, so), locations(C, sc)
    classes = collections.Counter()
    sites = collections.Counter()
    loc_pairs = {}
    per_window = []
    want = {int(x, 16) for x in detail}
    for oa, cas in sorted(byo.items()):
        if ob[oa]["raw_sha256"] in rawset:
            classes["exact"] += 1
            continue
        best = None
        for ca in ([o2c[oa]] if oa in o2c and o2c[oa] in cas else []) + cas:
            d = slot_diffs(O, C, oa, ca, ob[oa]["size"])
            if best is None or len(d) < len(best[1]):
                best = (ca, d)
        ca, d = best
        kinds = collections.Counter(k for k, *_ in d)
        unaligned = 0
        for k, off, po, pc in d:
            if k != "lddw":
                continue
            lo_, lc_ = locate_o(po), locate_c(pc)
            sec_name = lo_[0] or "unmapped"
            ok = lo_[0] is not None and lo_ == lc_
            sites[sec_name, ok] += 1
            if not ok:
                unaligned += 1
            if po in lo_o or pc in lo_c:
                loc_pairs.setdefault((po, pc), set()).add(oa)
        if kinds["other"]:
            cls = "other"
        elif unaligned:
            cls = "data_residual"
        else:
            cls = "data_aligned"
        classes[cls] += 1
        rec = {
            "dep": hex(oa),
            "cand": hex(ca),
            "size": ob[oa]["size"],
            "class": cls,
            "calls": kinds["call"],
            "lddw": kinds["lddw"],
            "lddw_unaligned": unaligned,
            "names": cb[ca]["names"][:2],
        }
        per_window.append(rec)
        if oa in want:
            rec["slots"] = [
                {
                    "kind": k,
                    "offset": off,
                    "dep_target": hex(po) if po is not None else None,
                    "cand_target": hex(pc) if pc is not None else None,
                    "dep_where": list(map(str, locate_o(po))) if po is not None else None,
                    "cand_where": list(map(str, locate_c(pc))) if pc is not None else None,
                    "dep_location": lo_o.get(po),
                    "cand_location": lo_c.get(pc),
                }
                for k, off, po, pc in d
            ]

    lc = collections.Counter()
    worklist = []
    for (po, pc), ws in sorted(loc_pairs.items()):
        a, b = lo_o.get(po), lo_c.get(pc)
        if a == b:
            k = "equal"
        elif a is None or b is None:
            k = "unpaired"
        elif a[0] != b[0]:
            k = "file"
        elif a[1] != b[1]:
            k = "line"
        else:
            k = "column"
        lc[k] += 1
        if k != "equal":
            worklist.append(
                {"kind": k, "deployed": a, "candidate": b, "windows": sorted(hex(w) for w in ws)}
            )

    def per_file(L):
        f = collections.defaultdict(list)
        for file, line, col in L.values():
            f[file].append([line, col])
        return {k: sorted(v) for k, v in sorted(f.items())}

    pf_o, pf_c = per_file(lo_o), per_file(lo_c)
    po_, pc_ = rs_paths(O, so), rs_paths(C, sc)

    rod_o = O.b[so[".rodata"]["offset"] : so[".rodata"]["offset"] + so[".rodata"]["size"]]
    rod_c = C.b[sc[".rodata"]["offset"] : sc[".rodata"]["offset"] + sc[".rodata"]["size"]]
    rp = 0
    while rp < min(len(rod_o), len(rod_c)) and rod_o[rp] == rod_c[rp]:
        rp += 1

    summary = {
        "matched": len(byo),
        "exact": classes["exact"],
        "data_aligned": classes["data_aligned"],
        "data_residual": classes["data_residual"],
        "other": classes["other"],
        "lddw_sites": sum(sites.values()),
        "lddw_sites_aligned": sum(v for (s, ok), v in sites.items() if ok),
        "locations_deployed": len(lo_o),
        "locations_candidate": len(lo_c),
        "location_pairs": dict(sorted(lc.items())),
        "location_files_equal": sum(1 for k in pf_o if pf_o.get(k) == pf_c.get(k)),
        "location_files_deployed": len(pf_o),
        "rodata_prefix_equal": rp,
        "data_rel_ro_prefix_equal": rebased_prefix(O, C, so, sc, locate_o, locate_c, ".data.rel.ro"),
    }
    return {
        "inputs": {
            "deployed_sha256": sha(O.b),
            "symbols_sha256": sha(S.b),
            "stripped_sha256": sha(C.b) if stripped else None,
        },
        "summary": summary,
        "sections": {
            n: {
                "deployed": {k: hex(v) for k, v in so[n].items() if k != "offset"},
                "candidate": {k: hex(v) for k, v in sc[n].items() if k != "offset"},
                "base_delta": sc[n]["addr"] - so[n]["addr"],
                "size_delta": sc[n]["size"] - so[n]["size"],
            }
            for n in DATA
            if n in so and n in sc
        },
        "lddw_sites": {
            f"{s}:{'aligned' if ok else 'unaligned'}": v for (s, ok), v in sorted(sites.items())
        },
        "location_worklist": worklist,
        "location_files": {
            k: {"deployed": pf_o.get(k, []), "candidate": pf_c.get(k, [])}
            for k in sorted(set(pf_o) | set(pf_c))
            if pf_o.get(k) != pf_c.get(k)
        },
        "paths": {"deployed_only": sorted(po_ - pc_), "candidate_only": sorted(pc_ - po_)},
        "windows": per_window,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deployed", type=Path)
    ap.add_argument("symbols", type=Path, help="candidate-symbols.so")
    ap.add_argument("--cand-stripped", type=Path, default=None)
    ap.add_argument("--window", action="append", default=[], help="deployed window start (hex) to detail")
    ap.add_argument("-o", "--output", type=Path, default=None)
    args = ap.parse_args(argv)
    result = solve(args.deployed, args.symbols, args.cand_stripped, args.window)
    text = json.dumps(result, indent=1) + "\n"
    if args.output:
        args.output.write_text(text)
        sys.stdout.write(json.dumps(result["summary"], indent=1) + "\n")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
