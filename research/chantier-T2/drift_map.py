#!/usr/bin/env python3
"""research/chantier-T2/drift_map.py: full drift map on top of tools/drift_solver.py.

Usage:
  python3 research/chantier-T2/drift_map.py DEPLOYED.so CANDIDATE-SYMBOLS.so \
      [--cand-stripped CANDIDATE.so] -o drift-map.json [--md drift-map.md]

Lists every interval with delta != 0 between consecutive uniquely paired
functions (deployed address order), ranked by call-only raw windows it keeps
locked, and classifies each one. Also lists matched raw-fail windows whose
diff touches lddw (data/relocation targets).

Classes (first rule that applies):
  order_island     candidate right anchor sits before the left anchor, or
                   |delta| > text/4: a paired body placed out of deployed order
                   (comes as a cancelling pair).
  anchor_wrapper   an involved symbol is an Anchor try_accounts /
                   try_deserialize / AccountsExit::exit / Accounts impl.
  monomorph        an involved symbol is a generic instantiation (core, alloc,
                   borsh, anchor_lang crate paths, FnOnce shims, closures),
                   or a deployed gap window has the size of an already paired
                   window (extra instantiation of the same body).
  source_fn_size   everything else (body present on both sides, sizes differ,
                   or a deployed body without candidate counterpart).
Involved symbols = candidate names inside the candidate gap, plus the name of
the unpaired candidate window when exactly one has the size of a deployed gap
window. The rule that fired is recorded per interval.
"""
from __future__ import annotations
import argparse, collections, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import drift_solver as ds  # noqa: E402

WRAP = re.compile(r"try_accounts|try_deserialize|AccountsExit|anchor_lang\.\.Accounts\$LT")
MONO = re.compile(r"^_ZN(4core|5alloc|11anchor_lang|5borsh)|FnOnce|call_once|\$u7b\$\$u7b\$closure")


def build(dep: Path, syms: Path, stripped: Path | None):
    O = ds.Elf(dep); S = ds.Elf(syms)
    C = ds.Elf(stripped) if stripped else S
    if C.b[C.lo:C.hi] != S.b[S.lo:S.hi]:
        raise SystemExit("candidate-stripped .text differs from symbols .text")
    os_ = ds.enrich(O, ds.windows(O)); cs = ds.enrich(C, ds.windows(C, S.funcs))
    ob = {r["start"]: r for r in os_}; cb = {r["start"]: r for r in cs}
    pairs = ds.unique_pairs(os_, cs)
    o2c = {oa: ca for ca, oa in pairs}; c2o = {ca: oa for ca, oa in pairs}
    mo = sorted(o2c)
    ivs = []
    for i, (oa, obr) in enumerate(zip(mo, mo[1:])):
        ca, cbr = o2c[oa], o2c[obr]
        gd = obr - ob[oa]["end"]; gc = cbr - cb[ca]["end"]
        ud = [r for r in os_ if ob[oa]["end"] <= r["start"] and r["end"] <= obr and r["start"] not in o2c]
        uc = [r for r in cs if cb[ca]["end"] <= r["start"] and r["end"] <= cbr and r["start"] not in c2o]
        ivs.append(dict(i=i, dep_left=oa, dep_right=obr, cand_left=ca, cand_right=cbr,
                        gap_dep=gd, gap_cand=gc, delta=gc - gd, ud=ud, uc=uc))
    cum = 0; drift = {mo[0]: 0}
    for iv in ivs:
        cum += iv["delta"]; drift[iv["dep_right"]] = cum
    spoil = collections.Counter()
    for oa, ca in o2c.items():
        if ob[oa]["raw_sha256"] == cb[ca]["raw_sha256"] or not ds.call_only_diff(O, C, oa, ca, ob[oa]["size"]):
            continue
        sp = set()
        for call in ob[oa]["calls"]:
            if call["kind"] != "signed_relative":
                continue
            ot = call["target"]
            callee = ot if ot in o2c else next((m for m in mo if ob[m]["start"] <= ot < ob[m]["end"]), None)
            if callee is None or drift.get(callee, 0) - drift.get(oa, 0) == 0:
                continue
            lo, hi = sorted((oa, callee))
            sp |= {iv["i"] for iv in ivs if lo <= iv["dep_left"] and iv["dep_right"] <= hi and iv["delta"]}
        for s in sp:
            spoil[s] += 1
    # data/reloc census: matched pairs, raw-fail, diff not call-only, some lddw slot differs
    data = []
    for oa, ca in o2c.items():
        if ob[oa]["raw_sha256"] == cb[ca]["raw_sha256"] or ds.call_only_diff(O, C, oa, ca, ob[oa]["size"]):
            continue
        n = ob[oa]["size"]; lddw = 0; i = 0
        while i < n:
            if O.b[oa + i] == 0x18:
                lddw += O.b[oa + i:oa + i + 16] != C.b[ca + i:ca + i + 16]; i += 16
            else:
                i += 8
        if lddw:
            data.append(dict(dep=hex(oa), cand=hex(ca), size=n, lddw_slots_differ=lddw,
                             names=cb[ca]["names"][:2]))
    unpaired_c = [r for r in cs if r["start"] not in c2o]
    paired_sizes = {ob[o]["size"] for o in o2c}
    text = O.hi - O.lo
    out = []
    for iv in ivs:
        if not iv["delta"]:
            continue
        same = []
        for u in iv["ud"]:
            m = [n for r in unpaired_c if r["size"] == u["size"] for n in r["names"][:1]]
            if len(m) == 1:
                same += m
        involved = [n for r in iv["uc"] for n in r["names"][:1]] + same
        if iv["cand_right"] < iv["cand_left"] or abs(iv["delta"]) > text // 4:
            cls, why = "order_island", "anchor order / magnitude"
        elif any(WRAP.search(n) for n in involved):
            cls, why = "anchor_wrapper", next(n for n in involved if WRAP.search(n))
        elif any(MONO.search(n) for n in involved):
            cls, why = "monomorph", next(n for n in involved if MONO.search(n))
        elif any(u["size"] in paired_sizes for u in iv["ud"]):
            cls, why = "monomorph", "deployed gap window size equals a paired window size"
        else:
            cls, why = "source_fn_size", "no generic or wrapper symbol in the gap"
        out.append(dict(
            spoiled_call_only=spoil[iv["i"]], cls=cls, rule=why, delta=iv["delta"],
            dep_left=hex(iv["dep_left"]), dep_right=hex(iv["dep_right"]),
            cand_left=hex(iv["cand_left"]), cand_right=hex(iv["cand_right"]),
            gap_dep=iv["gap_dep"], gap_cand=iv["gap_cand"],
            left_name=(cb[iv["cand_left"]]["names"] or [""])[0],
            right_name=(cb[iv["cand_right"]]["names"] or [""])[0],
            unmatched_dep=[dict(start=hex(u["start"]), size=u["size"],
                                same_size_unpaired_cand=[n for r in unpaired_c if r["size"] == u["size"] for n in r["names"][:1]][:3])
                           for u in iv["ud"]],
            unmatched_cand=[dict(start=hex(u["start"]), size=u["size"], names=u["names"][:2]) for u in iv["uc"]]))
    out.sort(key=lambda d: (-d["spoiled_call_only"], int(d["dep_left"], 16)))
    by = collections.defaultdict(lambda: dict(intervals=0, spoiled_call_only=0, abs_delta=0))
    for d in out:
        b = by[d["cls"]]; b["intervals"] += 1; b["spoiled_call_only"] += d["spoiled_call_only"]; b["abs_delta"] += abs(d["delta"])
    data.sort(key=lambda d: int(d["dep"], 16))
    return dict(inputs=dict(deployed_sha256=ds.sha(O.b), symbols_sha256=ds.sha(S.b), candidate_sha256=ds.sha(C.b)),
                summary=dict(unique_pairs=len(pairs), intervals_nonzero=len(out),
                             data_reloc_windows=len(data), by_class=dict(sorted(by.items()))),
                intervals=out, data_reloc=data)


def md(r):
    s = r["summary"]; L = ["# Drift map (pump, s7p)", "",
        f"unique pairs {s['unique_pairs']}, intervals with delta != 0: {s['intervals_nonzero']}, "
        f"matched raw-fail windows with lddw diffs: {s['data_reloc_windows']}", "",
        "| class | intervals | call-only locks (sum, overlapping) | sum abs delta (B) |", "|---|---:|---:|---:|"]
    for k, v in s["by_class"].items():
        L.append(f"| {k} | {v['intervals']} | {v['spoiled_call_only']} | {v['abs_delta']} |")
    L += ["", "| rank | locked | class | delta | deployed interval | candidate left anchor |", "|---:|---:|---|---:|---|---|"]
    for i, d in enumerate(r["intervals"], 1):
        nm = d["left_name"]; nm = (nm[:70] + "...") if len(nm) > 73 else nm
        L.append(f"| {i} | {d['spoiled_call_only']} | {d['cls']} | {d['delta']} | `{d['dep_left']}`..`{d['dep_right']}` | `{nm}` |")
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deployed", type=Path); ap.add_argument("symbols", type=Path)
    ap.add_argument("--cand-stripped", type=Path); ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--md", type=Path)
    a = ap.parse_args(argv)
    r = build(a.deployed, a.symbols, a.cand_stripped)
    a.output.write_text(json.dumps(r, indent=1) + "\n")
    if a.md:
        a.md.write_text(md(r))
    print(json.dumps(r["summary"], indent=1))


if __name__ == "__main__":
    raise SystemExit(main())
