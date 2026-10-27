#!/usr/bin/env python3
"""tools/drift_solver.py  -  layout-drift solver for sBPF whole-ELF matching.

Usage:
  python3 tools/drift_solver.py DEPLOYED.so CANDIDATE-SYMBOLS.so [--cand-stripped STRIPPED.so] [-o out.json]

Inputs:
  DEPLOYED.so            comparison target (read-only)
  CANDIDATE-SYMBOLS.so   native build with symbols (text must match stripped)

Outputs JSON with:
  (a) summary.potential_if_delta0   = exact + call_only_raw_fail
  (b) top_spoilers                 = intervals ranked by call-only windows spoiled
  (c) root                         = first interval with delta != 0 in deployed address order

Definitions (docs/CHANTIER.md, docs/WHOLE_ELF_FRONTIER.md):
  Between consecutive uniquely paired functions (deployed address order):
      delta = gap_cand - gap_dep
  For a signed-relative call from paired caller to paired callee:
      delta_call = sum of deltas of intervals strictly between them
  A matched window is call-only raw-fail when bodies differ solely in call
  immediates (opcode 0x85 imm32). Those windows become raw once every
  crossed delta is zeroed.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import struct
import sys
from pathlib import Path

sha = lambda b: hashlib.sha256(b).hexdigest()


class Elf:
    """Minimal read-only sBPF ELF view (VA == file offset for .text)."""

    def __init__(self, path: Path):
        self.path = path
        self.b = path.read_bytes()
        b = self.b
        off = struct.unpack_from("<Q", b, 40)[0]
        size, count, ni = struct.unpack_from("<HHH", b, 58)
        self.raw = [struct.unpack_from("<IIQQQQIIQQ", b, off + i * size) for i in range(count)]
        ns = self.raw[ni]
        names = b[ns[4] : ns[4] + ns[5]]
        self.secs = {names[s[0] :].split(b"\0", 1)[0].decode(): s for s in self.raw}
        self.text = self.secs[".text"]
        self.lo = self.text[4]
        self.hi = self.lo + self.text[5]
        self.symbols = {}
        self.funcs = []
        for kind in (".dynsym", ".symtab"):
            if kind not in self.secs:
                continue
            s = self.secs[kind]
            st = self.raw[s[6]]
            strings = b[st[4] : st[4] + st[5]]
            for i, p in enumerate(range(s[4], s[4] + s[5], 24)):
                n, info, _, idx, value, length = struct.unpack_from("<IBBHQQ", b, p)
                name = strings[n:].split(b"\0", 1)[0].decode()
                if kind == ".dynsym":
                    self.symbols[i] = name
                if info & 15 == 2 and length and self.lo <= value < self.hi:
                    self.funcs.append({"name": name, "start": value, "size": length})
        self.relocations = {}
        self.entries = {f["start"] for f in self.funcs}
        entry = struct.unpack_from("<Q", b, 24)[0]
        if self.lo <= entry < self.hi:
            self.entries.add(entry)
        if ".rel.dyn" in self.secs:
            s = self.secs[".rel.dyn"]
            for i in range(s[4], s[4] + s[5], 16):
                at, info = struct.unpack_from("<QQ", b, i)
                typ = info & 0xFFFFFFFF
                symbol = self.symbols.get(info >> 32, "")
                self.relocations[at] = {"type": typ, "symbol": symbol}
                if typ == 8:
                    if self.lo <= at < self.hi and b[at] == 0x18:
                        ptr = struct.unpack_from("<I", b, at + 4)[0] | (
                            struct.unpack_from("<I", b, at + 12)[0] << 32
                        )
                    else:
                        ptr = struct.unpack_from("<Q", b, at)[0] >> 32
                    if self.lo <= ptr < self.hi and ptr % 8 == 0:
                        self.entries.add(ptr)
        self.calls = {}
        norm = bytearray(b)
        for at in range(self.lo, self.hi, 8):
            if b[at] == 0x85 and b[at + 1] == 0x10 and self.relocations.get(at, {}).get("type") != 10:
                imm = struct.unpack_from("<i", b, at + 4)[0]
                target = at + 8 + imm * 8
                self.calls[at] = target
                norm[at + 4 : at + 8] = bytes(4)
                if self.lo <= target < self.hi and target % 8 == 0:
                    self.entries.add(target)
            if at in self.relocations:
                typ = self.relocations[at]["type"]
                if typ == 8 and b[at] == 0x18:
                    norm[at + 4 : at + 8] = bytes(4)
                    norm[at + 12 : at + 16] = bytes(4)
                elif typ == 10 and b[at] == 0x85:
                    norm[at + 4 : at + 8] = bytes(4)
        self.normalized = bytes(norm)
        self.entries = sorted(self.entries)

    def pattern(self, start, size):
        return [
            {"offset": at - start, **r}
            for at, r in sorted(self.relocations.items())
            if start <= at < start + size
        ]


def windows(e: Elf, funcs=None):
    if funcs is None:
        return [
            {"start": a, "size": b - a, "names": []}
            for a, b in zip(e.entries, e.entries[1:] + [e.hi])
        ]
    groups = collections.defaultdict(list)
    for f in funcs:
        groups[f["start"], f["size"]].append(f["name"])
    return [
        {"start": a, "size": s, "names": sorted(set(ns))}
        for (a, s), ns in sorted(groups.items())
    ]


def enrich(e: Elf, rs):
    for r in rs:
        a = r["start"]
        b = a + r["size"]
        r.update(
            end=b,
            raw_sha256=sha(e.b[a:b]),
            normalized_sha256=sha(e.normalized[a:b]),
            calls=[],
            relocations=e.pattern(a, r["size"]),
        )
        for at in range(a, b, 8):
            if at + 8 > len(e.b):
                continue
            op, regs, off, imm = struct.unpack_from("<BBhi", e.b, at)
            if op == 0x85:
                reloc = e.relocations.get(at)
                target = e.calls.get(at)
                r["calls"].append(
                    {
                        "offset": at - a,
                        "signed_immediate": imm,
                        "target": target,
                        "relocation": reloc,
                        "kind": (
                            "signed_relative"
                            if target is not None
                            else "relocated_external"
                            if reloc
                            else "unresolved_call"
                        ),
                    }
                )
    return rs


def unique_pairs(os_, cs):
    """1:1 greedy pairs by (size, normalized_sha256, relocations), deployed-address first."""
    idx = collections.defaultdict(list)
    for r in os_:
        idx[r["size"], r["normalized_sha256"]].append(r)
    cand = []
    for r in cs:
        for v in idx[r["size"], r["normalized_sha256"]]:
            if v["relocations"] == r["relocations"]:
                cand.append((r["start"], v["start"]))
    used_o, used_c = set(), set()
    pairs = []
    for ca, oa in sorted(cand, key=lambda t: (t[1], t[0])):
        if oa in used_o or ca in used_c:
            continue
        used_o.add(oa)
        used_c.add(ca)
        pairs.append((ca, oa))
    return pairs


def pattern_pairs(os_, cs):
    """All pattern pairs (same key as measure.py); used for call-only census."""
    idx = collections.defaultdict(list)
    for r in os_:
        idx[r["size"], r["normalized_sha256"]].append(r)
    out = []
    for r in cs:
        for v in idx[r["size"], r["normalized_sha256"]]:
            if v["relocations"] == r["relocations"]:
                out.append((r["start"], v["start"]))
    return out


def call_only_diff(O: Elf, C: Elf, oa: int, ca: int, n: int) -> bool:
    """True iff every differing 8-byte slot is a call (0x85) immediate."""
    i = 0
    while i < n:
        if O.b[oa + i] == 0x18:
            if O.b[oa + i : oa + i + 16] != C.b[ca + i : ca + i + 16]:
                return False
            i += 16
            continue
        if O.b[oa + i : oa + i + 8] != C.b[ca + i : ca + i + 8]:
            if O.b[oa + i] != 0x85 or C.b[ca + i] != 0x85:
                return False
        i += 8
    return True


def hx(n: int) -> str:
    return hex(n)


def solve(dep: Path, syms: Path, stripped: Path | None = None) -> dict:
    O = Elf(dep)
    S = Elf(syms)
    if stripped is not None:
        C = Elf(stripped)
        if C.b[C.lo : C.hi] != S.b[S.lo : S.hi]:
            raise SystemExit("candidate-stripped .text differs from symbols .text")
    else:
        C = S

    os_ = enrich(O, windows(O))
    cs = enrich(C, windows(C, S.funcs))
    ob = {r["start"]: r for r in os_}
    cb = {r["start"]: r for r in cs}
    rawset = {r["raw_sha256"] for r in cs}

    # Census on pattern pairs (measure-compatible): unique deployed windows.
    byo = collections.defaultdict(set)
    for ca, oa in pattern_pairs(os_, cs):
        byo[oa].add(ca)
    matched = len(byo)
    exact = sum(1 for oa in byo if ob[oa]["raw_sha256"] in rawset)
    call_only = 0
    for oa, cas in byo.items():
        if ob[oa]["raw_sha256"] in rawset:
            continue
        if any(call_only_diff(O, C, oa, ca, ob[oa]["size"]) for ca in cas):
            call_only += 1

    # Drift intervals on 1:1 unique pairing.
    pairs = unique_pairs(os_, cs)
    o2c = {oa: ca for ca, oa in pairs}
    c2o = {ca: oa for ca, oa in pairs}
    matched_o = sorted(o2c)
    intervals = []
    for i in range(len(matched_o) - 1):
        oa = matched_o[i]
        obr = matched_o[i + 1]
        ca = o2c[oa]
        cbr = o2c[obr]
        gap_d = obr - ob[oa]["end"]
        gap_c = cbr - cb[ca]["end"]
        delta = gap_c - gap_d
        u_d = [
            r
            for r in os_
            if ob[oa]["end"] <= r["start"] and r["end"] <= obr and r["start"] not in o2c
        ]
        u_c = [
            r
            for r in cs
            if cb[ca]["end"] <= r["start"] and r["end"] <= cbr and r["start"] not in c2o
        ]
        intervals.append(
            {
                "i": i,
                "dep_left": oa,
                "dep_right": obr,
                "cand_left": ca,
                "cand_right": cbr,
                "gap_dep": gap_d,
                "gap_cand": gap_c,
                "delta": delta,
                "unmatched_dep": [{"start": r["start"], "size": r["size"], "names": r["names"]} for r in u_d],
                "unmatched_cand": [{"start": r["start"], "size": r["size"], "names": r["names"]} for r in u_c],
            }
        )

    cum = 0
    drift_before = {matched_o[0]: 0}
    for iv in intervals:
        cum += iv["delta"]
        drift_before[iv["dep_right"]] = cum

    spoil = collections.Counter()
    # Per call-only window, credit each nonzero interval it crosses once
    # (raw windows that interval keeps locked).
    for oa, ca in o2c.items():
        if ob[oa]["raw_sha256"] == cb[ca]["raw_sha256"]:
            continue
        if not call_only_diff(O, C, oa, ca, ob[oa]["size"]):
            continue
        r = ob[oa]
        spoilers = set()
        for call in r["calls"]:
            if call["kind"] != "signed_relative":
                continue
            ot = call["target"]
            callee = None
            if ot in o2c:
                callee = ot
            else:
                for mo in matched_o:
                    if ob[mo]["start"] <= ot < ob[mo]["end"]:
                        callee = mo
                        break
            if callee is None or oa not in drift_before or callee not in drift_before:
                continue
            dc = drift_before[callee] - drift_before[oa]
            if dc == 0:
                continue
            lo, hi = sorted((oa, callee))
            for iv in intervals:
                if lo <= iv["dep_left"] and iv["dep_right"] <= hi and iv["delta"] != 0:
                    spoilers.add(iv["i"])
        for si in spoilers:
            spoil[si] += 1

    first = next((iv for iv in intervals if iv["delta"] != 0), None)
    ranked = sorted(
        ((spoil[iv["i"]], iv) for iv in intervals if iv["delta"] != 0),
        key=lambda t: (-t[0], t[1]["dep_left"]),
    )

    def iv_view(iv, spoiled=None):
        d = {
            "dep_left": hx(iv["dep_left"]),
            "dep_right": hx(iv["dep_right"]),
            "cand_left": hx(iv["cand_left"]),
            "cand_right": hx(iv["cand_right"]),
            "delta": iv["delta"],
            "gap_dep": iv["gap_dep"],
            "gap_cand": iv["gap_cand"],
            "unmatched_dep": [
                {"start": hx(x["start"]), "size": x["size"], "names": x["names"][:3]}
                for x in iv["unmatched_dep"]
            ],
            "unmatched_cand": [
                {"start": hx(x["start"]), "size": x["size"], "names": x["names"][:3]}
                for x in iv["unmatched_cand"]
            ],
        }
        if spoiled is not None:
            d["spoiled_call_only"] = spoiled
        return d

    return {
        "inputs": {
            "deployed": str(dep),
            "symbols": str(syms),
            "stripped": str(stripped) if stripped else None,
            "deployed_sha256": sha(O.b),
            "symbols_sha256": sha(S.b),
        },
        "summary": {
            "original_windows": len(os_),
            "candidate_windows": len(cs),
            "matched": matched,
            "exact": exact,
            "call_only_raw_fail": call_only,
            "potential_if_delta0": exact + call_only,
            "unique_pairs": len(pairs),
            "intervals_nonzero": sum(1 for iv in intervals if iv["delta"] != 0),
        },
        "root": iv_view(first) if first else None,
        "top_spoilers": [iv_view(iv, n) for n, iv in ranked[:25]],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deployed", type=Path)
    ap.add_argument("symbols", type=Path, help="candidate-symbols.so")
    ap.add_argument("--cand-stripped", type=Path, default=None)
    ap.add_argument("-o", "--output", type=Path, default=None)
    args = ap.parse_args(argv)
    result = solve(args.deployed, args.symbols, args.cand_stripped)
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
