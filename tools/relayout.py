#!/usr/bin/env python3
"""tools/relayout.py  -  regenerate the whole-ELF layout linker script (ordered.ld)
that binds every candidate input section to its DEPLOYED window order.

This is the T6 layout enabler from lalalune's whole-ELF method (fees 585/585):
after ANY source change, the deployed .text order must be re-bound so the script
stays complete (new sections listed, vanished sections dropped) and so relative
call immediates line up for raw byte-exactness. relayout tracks the deployed
order as function bodies change.

It fits the pumpround34 recipe, it does not replace it. The build runs rust-lld
through pump_text_layout.py with PUMP_TEXT_SCRIPT=ordered.ld, where ordered.ld =
pump_text_layout_default.ld with its `.text : { *(.text*) }` rule expanded into an
explicit, ordered list of per-function input-section selectors followed by the
`*(.text*)` catch-all. relayout regenerates that ordered list.

==============================================================================
TWO MODES
==============================================================================

(1) REBIND mode  [--rebind-ld EXISTING.ld]   -- the T6 keystone for pump raw
----------------------------------------------------------------------------
Problem it solves: every window closed on a program (pump, pump_amm, fees)
changes the MIR of the patched functions, which changes their Rust symbol-hash
suffix (`...17h<16hex>E`). The DEPLOYED-slot order in `ordered.ld` is encoded by
each selector's LINE POSITION, but each selector names its function by the OLD
mangled name (old hash). rust-lld cannot place a selector that matches no current
section, so the rehashed function falls through to the `*(.text*)` catch-all at
the TAIL of .text instead of its deployed slot. Every such stale selector costs
the raw match of that window AND every window whose relative call crosses the
resulting gap. (Fees: 3 window-completion patches rehashed 9 functions -> raw
collapsed 585 -> 288 until the 9 selectors were refreshed.)

REBIND regenerates `ordered.ld` by keeping every selector's LINE POSITION fixed
(= its deployed slot) and re-binding each STALE selector to the CURRENT symbol
that now occupies that slot. A current section is bound to a stale selector by:

  1. content identity   -- the current function's body (size, normalized_sha256,
                           relocation pattern) pairs 1:1 with a deployed window
                           (drift_solver.unique_pairs). That deployed window's
                           address IS the deployed slot. The deployed .so is
                           stripped, so content identity is the name-stable
                           equivalent of symbol binding across a hash change.
  2. name-base identity -- the demangled prefix (everything except `17h<hex>E`)
                           is stable across a MIR change, so it groups each stale
                           selector with its rehashed orphan. For a group of size
                           >1 (several instantiations sharing a demangled name),
                           the members are ordered by their paired deployed VMA
                           (content) so slot i binds to the i-th deployed window.
  3. call-graph color   -- when two orphans in a group have IDENTICAL normalized
                           bodies (a dup pool) so content cannot order them, they
                           are disambiguated by caller/callee identity: each
                           orphan's callee-name-set is matched to the callee-set
                           the deployed slot expects (deployed callees mapped back
                           through the content pairing).

Only STALE selectors are rewritten; every LIVE selector line is kept BYTE-FOR-BYTE.
This is idempotent (a good build has no stale selectors -> zero edits -> identical
file) and non-regressing by construction (correct slots are never touched). A
stale selector whose function was genuinely DELETED (no orphan shares its
demangled name) is left untouched and reported (an inert selector matching nothing
is harmless). Data families (.rodata / .data.rel.ro) are rebound by the same
stale-detection, using name-base identity (their records are not .text windows);
when no data selector is stale (the common case once T5 data layout is clean) they
are left byte-identical.

Usage:
  python3 tools/relayout.py DEPLOYED.so SYMBOLS.so LINK.map \
          --rebind-ld ordered.stale.ld -o ordered.ld [--report report.json]

(2) PRESERVE / RELOCATE mode  [default]
----------------------------------------------------------------------------
Regenerate the ordered list from scratch, pinning the live build's physical order
(from link.map) as the backbone (idempotent, non-regressing) and optionally moving
named sections to their deployed slot with `--to-deployed PATTERN`. A global
deployed-ADDRESS sort is NOT safe on a partial reconstruction (dense dup-normalized
stubs scatter and regress already-raw windows -- measured 127 -> 115 on pump
round-34), so relayout moves a section ONLY on request. This mode is the
maintenance / from-scratch generator; REBIND is the in-place slot-preserving
refresh used to convert a closed-window normalized build to raw.

  --to-deployed PATTERN   relocate each content-matched section whose section
                          name contains PATTERN to its deployed-order position.

Inputs (both modes):
  DEPLOYED.so            deployed reference (window-order target, read-only)
  SYMBOLS.so             candidate build with symbols (.text must match stripped)
  LINK.map               the build's rust-lld -Map output
                         (PUMP_TEXT_RECORD_DIR/link.map): the authoritative
                         selector catalog -- every emitted .text.<sec> section ->
                         owning object file + VMA, in physical order.

Options:
  --rebind-ld PATH       existing (possibly-stale) ordered.ld to rebind in place
  --cand-stripped S.so   stripped candidate (asserts .text identity with SYMBOLS)
  --default-ld PATH      pump_text_layout_default.ld skeleton to wrap (preserve mode)
  --to-deployed PATTERN  relocate matched sections whose name contains PATTERN
                         (repeatable, preserve mode only)
  -o OUT.ld              output (default stdout)
  --report PATH          JSON placement / rebind report
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import drift_solver as DS  # Elf, windows, enrich, unique_pairs

DEFAULT_LD = (
    "/home/nagi/pumpround34/repro/pump/main-contract-round34-20261027/"
    "inputs/scripts/pump_text_layout_default.ld"
)

# A link.map input-section placement line, after str.split():
#   [VMA, LMA, SIZE, ALIGN, "<objpath>:(.text.<sec>)"]
# Mangled section names never contain a literal ')' (parens are encoded $LP$/$RP$),
# so ":(.text ... )" is an unambiguous wrapper.
_SEC = re.compile(r"^(?P<obj>.+):\((?P<sec>\.text(?:\.[^)]*)?)\)$")
_RLIB = re.compile(r".*/(?P<rlib>[^/]+\.rlib)\((?P<mem>[^)]+)\)$")

# Any family's map line (.text / .rodata / .data.rel.ro).
_SEC_ANY = re.compile(
    r"^(?P<obj>.+):\((?P<sec>\.(?:text|rodata|data\.rel\.ro)(?:\.[^)]*)?)\)$"
)
# An ordered.ld selector line:  <indent>*<objtoken>(".text.<mangled>")
_SEL_LINE = re.compile(
    r'^(?P<indent>\s*)\*(?P<obj>[^(]+)\("(?P<sec>\.(?:text|rodata|data\.rel\.ro)(?:\.[^"]*)?)"\)\s*$'
)
# Rust symbol-hash suffix (trailing); stripping it gives a MIR-change-stable
# "base". Anchored at end: a MIR change rehashes only this final component.
_HASH = re.compile(r"17h[0-9a-f]{16}E$")

FAMILIES = (".text", ".rodata", ".data.rel.ro")


def fam_of(sec: str) -> str:
    if sec.startswith(".data.rel.ro"):
        return ".data.rel.ro"
    if sec.startswith(".rodata"):
        return ".rodata"
    return ".text"


def strip_hash(sec: str) -> str:
    """Section name with the trailing rust symbol-hash removed (stable across MIR
    edits). Same base-key the manual T5 refresh used to pair stale<->orphan."""
    return _HASH.sub("", sec)


def selector_token(objpath: str) -> str:
    """link.map object path -> ordered.ld selector object token.

    plain  : <dir>/base.rcgu.o          -> base.rcgu.o
    archive: <dir>/libX.rlib(member.o)  -> libX.rlib:member.o
    """
    m = _RLIB.match(objpath)
    if m:
        return f"{m.group('rlib')}:{m.group('mem')}"
    return objpath.rsplit("/", 1)[-1]


def parse_link_map(path: Path):
    """[(vma:int, size:int, section:str, selector:str)] of .text, physical order."""
    out = []
    for line in path.read_text(errors="replace").splitlines():
        toks = line.split()
        if len(toks) < 5 or ":(.text" not in toks[4]:
            continue
        m = _SEC.match(toks[4])
        if not m:
            continue
        try:
            vma = int(toks[0], 16)
            size = int(toks[2], 16)
        except ValueError:
            continue
        sec = m.group("sec")
        sel = f'    *{selector_token(m.group("obj"))}("{sec}")'
        out.append((vma, size, sec, sel))
    return out


def current_sections(link_map: Path):
    """fam -> {section_name: {'tok': selector_token, 'vma': int}} for the live build.

    The authoritative current-section catalog across all three families.
    """
    out = {f: {} for f in FAMILIES}
    for line in Path(link_map).read_text(errors="replace").splitlines():
        toks = line.split()
        if len(toks) < 5 or ":(" not in toks[4]:
            continue
        m = _SEC_ANY.match(toks[4])
        if not m:
            continue
        try:
            vma = int(toks[0], 16)
        except ValueError:
            continue
        sec = m.group("sec")
        out[fam_of(sec)][sec] = {"tok": selector_token(m.group("obj")), "vma": vma}
    return out


def wrap_script(default_text: str, selectors: list[str]) -> str:
    """Expand the default.ld `.text` rule with ordered selectors + catch-all.
    Mirrors pump_text_layout.check_script so the linker wrapper accepts it."""
    rule = "  .text : { *(.text*) } :text"
    assert default_text.count(rule) == 1, "default.ld .text rule not found"
    head, tail = default_text.split(rule)
    body = "\n".join(selectors)
    return head + "  .text : {\n" + body + "\n    *(.text*)\n  } :text" + tail


# ---------------------------------------------------------------------------
# PRESERVE / RELOCATE mode (original behaviour)
# ---------------------------------------------------------------------------
def relayout(deployed: Path, symbols: Path, link_map: Path,
             cand_stripped: Path | None, default_ld: Path,
             to_deployed: list[str] | None):
    O = DS.Elf(deployed)
    S = DS.Elf(symbols)
    if cand_stripped is not None:
        C = DS.Elf(cand_stripped)
        if C.b[C.lo:C.hi] != S.b[S.lo:S.hi]:
            raise SystemExit("candidate-stripped .text differs from symbols .text")
    else:
        C = S

    # Content-identity binding: candidate window vma -> deployed window vma.
    os_ = DS.enrich(O, DS.windows(O))
    cs = DS.enrich(C, DS.windows(C, S.funcs))
    pairs = DS.unique_pairs(os_, cs)            # [(cand_vma, dep_vma)]
    cand_to_dep = {ca: oa for ca, oa in pairs}
    # Which deployed windows are already raw-exact in the candidate (pinned hard).
    cand_raw = {r["raw_sha256"] for r in cs}

    sections = parse_link_map(link_map)          # physical order (backbone)
    # annotate each section with its deployed vma (if content-matched)
    nodes = []
    for vma, size, sec, sel in sections:
        nodes.append({"vma": vma, "size": size, "sec": sec, "sel": sel,
                      "dep": cand_to_dep.get(vma)})

    patterns = to_deployed or []
    reloc = []
    if patterns:
        keep = []
        for n in nodes:
            if n["dep"] is not None and any(p in n["sec"] for p in patterns):
                reloc.append(n)
            else:
                keep.append(n)
        # Insert each relocated section after the nearest kept matched section
        # whose deployed vma precedes it (deployed-order anchor).
        for f in sorted(reloc, key=lambda n: n["dep"]):
            idx = 0
            for i, n in enumerate(keep):
                if n["dep"] is not None and n["dep"] < f["dep"]:
                    idx = i + 1
            keep.insert(idx, f)
        nodes = keep

    # Emit selectors in computed order, de-duplicated (first occurrence wins).
    seen = set()
    selectors = []
    for n in nodes:
        if n["sel"] in seen:
            continue
        seen.add(n["sel"])
        selectors.append(n["sel"])

    default_text = Path(default_ld).read_text()
    script = wrap_script(default_text, selectors)

    matched = sum(1 for n in nodes if n["dep"] is not None)
    report = {
        "mode": "preserve" + (f"+relocate({len(reloc)})" if reloc else ""),
        "deployed": str(deployed),
        "symbols": str(symbols),
        "link_map": str(link_map),
        "sections_total": len(sections),
        "content_matched": matched,
        "relocated": [n["sec"] for n in reloc],
        "selectors_emitted": len(selectors),
        "deployed_windows": len(os_),
        "candidate_windows": len(cs),
        "unique_pairs": len(pairs),
        "already_raw_candidate_windows": len(cand_raw & {r["raw_sha256"] for r in os_}),
    }
    return script, report


# ---------------------------------------------------------------------------
# REBIND mode  -- the T6 keystone
# ---------------------------------------------------------------------------
def _rebuild_line(indent: str, tok: str, sec: str, newline: str) -> str:
    return f'{indent}*{tok}("{sec}"){newline}'


def _callee_bases_cand(win, vma_to_sec_text):
    """Set of callee demangled-bases for a CANDIDATE window (call -> target vma)."""
    out = set()
    for c in win.get("calls", []):
        t = c.get("target")
        if t is None:
            continue
        sec = vma_to_sec_text.get(t)
        if sec:
            out.add(strip_hash(sec))
    return out


def _expected_bases_for_dep(dep_start, dep_win, dep_to_cand, vma_to_sec_text):
    """Callee demangled-bases a DEPLOYED slot expects, mapped back through pairing.

    deployed callee target (a deployed window start) -> paired candidate window
    -> its current section -> demangled base.
    """
    out = set()
    w = dep_win.get(dep_start)
    if not w:
        return out
    for c in w.get("calls", []):
        t = c.get("target")
        if t is None:
            continue
        cvma = dep_to_cand.get(t)
        if cvma is None:
            continue
        sec = vma_to_sec_text.get(cvma)
        if sec:
            out.add(strip_hash(sec))
    return out


def _order_dup_pool(orphs, cands_sorted, orph_info, dep_win, dep_to_cand,
                    cand_win, vma_to_sec_text):
    """Order a same-base orphan group so orphan i -> stale-slot i (deployed order).

    Default order is by paired deployed VMA (content). Where a sub-group of orphans
    shares an identical normalized body (a dup pool) the content VMA order can be
    arbitrary (unique_pairs resolves it greedily), so that sub-group is re-ordered
    by matching each orphan's callee-name-set to the callee-set its candidate slot
    expects (call-graph color). Fully deterministic; falls back to VMA order.
    """
    order = sorted(orphs, key=lambda o: (orph_info[o]["dep"], o))
    # group the VMA-ordered orphans by identical normalized body
    by_norm = collections.defaultdict(list)
    for o in order:
        by_norm[orph_info[o]["normsha"]].append(o)
    dup_pools = [g for g in by_norm.values() if len(g) > 1]
    if not dup_pools:
        return order
    # the deployed slots for this group, in the same positional order as `order`
    slot_deps = [orph_info[o]["dep"] for o in order]
    pos = {o: i for i, o in enumerate(order)}
    for pool in dup_pools:
        positions = sorted(pos[o] for o in pool)
        slots = [slot_deps[p] for p in positions]
        want = [_expected_bases_for_dep(s, dep_win, dep_to_cand, vma_to_sec_text)
                for s in slots]
        have = {o: _callee_bases_cand(cand_win.get(orph_info[o]["vma"], {}),
                                      vma_to_sec_text) for o in pool}
        remaining = list(pool)
        assign = {}
        for si, w in enumerate(want):
            best, bo = -1, None
            for o in remaining:
                score = len(w & have[o])
                if score > best:
                    best, bo = score, o
            if bo is None:
                bo = remaining[0]
            assign[positions[si]] = bo
            remaining.remove(bo)
        for p, o in assign.items():
            order[p] = o
    return order


def rebind(deployed: Path, symbols: Path, link_map: Path, existing_ld: Path,
           cand_stripped: Path | None):
    O = DS.Elf(deployed)
    S = DS.Elf(symbols)
    if cand_stripped is not None:
        C = DS.Elf(cand_stripped)
        if C.b[C.lo:C.hi] != S.b[S.lo:S.hi]:
            raise SystemExit("candidate-stripped .text differs from symbols .text")
    else:
        C = S

    os_ = DS.enrich(O, DS.windows(O))
    cs = DS.enrich(C, DS.windows(C, S.funcs))
    pairs = DS.unique_pairs(os_, cs)                   # [(cand_vma, dep_vma)]
    cand_to_dep = {ca: oa for ca, oa in pairs}
    dep_to_cand = {oa: ca for ca, oa in pairs}
    cand_win = {w["start"]: w for w in cs}
    dep_win = {w["start"]: w for w in os_}

    cur = current_sections(link_map)
    vma_to_sec_text = {d["vma"]: sec for sec, d in cur[".text"].items()}

    text = Path(existing_ld).read_text()
    lines = text.splitlines(keepends=True)

    # Index existing selectors per family: (line_idx, indent, obj, sec, newline).
    existing = {f: [] for f in FAMILIES}
    for i, ln in enumerate(lines):
        m = _SEL_LINE.match(ln.rstrip("\n"))
        if not m:
            continue
        nl = "\n" if ln.endswith("\n") else ""
        sec = m.group("sec")
        existing[fam_of(sec)].append(
            (i, m.group("indent"), m.group("obj"), sec, nl)
        )

    edits = {}  # line_idx -> new line text
    report = {
        "mode": "rebind",
        "deployed": str(deployed),
        "symbols": str(symbols),
        "link_map": str(link_map),
        "existing_ld": str(existing_ld),
        "deployed_windows": len(os_),
        "candidate_windows": len(cs),
        "unique_pairs": len(pairs),
        "families": {},
    }

    for fam in FAMILIES:
        cur_secs = cur[fam]
        sel_secs = set(e[3] for e in existing[fam])
        live_secs = set(s for s in sel_secs if s in cur_secs)
        stale = [e for e in existing[fam] if e[3] not in cur_secs]
        orphans = [s for s in cur_secs if s not in live_secs]

        orph_info = {}
        for s in orphans:
            vma = cur_secs[s]["vma"]
            dep = cand_to_dep.get(vma) if fam == ".text" else None
            orph_info[s] = {
                "tok": cur_secs[s]["tok"],
                "vma": vma,
                "dep": dep,
                "normsha": cand_win.get(vma, {}).get("normalized_sha256")
                if fam == ".text" else None,
            }

        stale_by_base = collections.defaultdict(list)
        for e in stale:
            stale_by_base[strip_hash(e[3])].append(e)
        orph_by_base = collections.defaultdict(list)
        for s in orphans:
            orph_by_base[strip_hash(s)].append(s)

        used_orph = set()
        bindings = []
        unresolved = []
        for b, cands in stale_by_base.items():
            cands_sorted = sorted(cands, key=lambda e: e[0])  # line order
            orphs = [o for o in orph_by_base.get(b, []) if o not in used_orph]
            if not orphs or len(orphs) != len(cands_sorted):
                for e in cands_sorted:
                    unresolved.append({
                        "line": e[0] + 1, "sec": e[3],
                        "reason": "no 1:1 same-base orphan "
                                  f"(stale={len(cands_sorted)}, orphans={len(orphs)})"
                                  " -- function deleted or renamed; selector left inert",
                    })
                continue

            if fam == ".text":
                deps_known = all(orph_info[o]["dep"] is not None for o in orphs)
                if deps_known:
                    order = _order_dup_pool(
                        orphs, cands_sorted, orph_info, dep_win, dep_to_cand,
                        cand_win, vma_to_sec_text)
                    method = ("name+content" if len(orphs) == 1
                              else "name+content(dep-order)")
                else:
                    order = sorted(orphs)  # content could not confirm; name only
                    method = "name-only(content-unconfirmed)"
            else:
                order = sorted(orphs)      # data families: name-base identity
                method = "name-base(data)"

            for e, o in zip(cands_sorted, order):
                i, indent, obj, sec, nl = e
                tok = orph_info[o]["tok"]
                edits[i] = _rebuild_line(indent, tok, o, nl)
                used_orph.add(o)
                bindings.append({
                    "line": i + 1,
                    "old": sec,
                    "new": o,
                    "dep_slot": hex(orph_info[o]["dep"])
                    if orph_info[o]["dep"] is not None else None,
                    "cand_vma": hex(orph_info[o]["vma"]),
                    "method": method,
                    "obj_changed": tok != obj,
                    "base_match": True,
                })

        unplaced = sorted(o for o in orphans if o not in used_orph)
        report["families"][fam] = {
            "ld_selectors": len(existing[fam]),
            "current_sections": len(cur_secs),
            "stale_selectors": len(stale),
            "orphan_sections": len(orphans),
            "rebound": len(bindings),
            "unresolved_stale": unresolved,
            "unplaced_orphans": unplaced,
            "bindings": sorted(bindings, key=lambda d: d["line"]),
        }

    for i, new in edits.items():
        lines[i] = new
    out_text = "".join(lines)

    report["edits"] = len(edits)
    report["idempotent"] = len(edits) == 0
    report["total_rebound"] = sum(
        report["families"][f]["rebound"] for f in FAMILIES)
    report["total_unresolved"] = sum(
        len(report["families"][f]["unresolved_stale"]) for f in FAMILIES)
    report["total_unplaced"] = sum(
        len(report["families"][f]["unplaced_orphans"]) for f in FAMILIES)
    return out_text, report


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("deployed", type=Path)
    ap.add_argument("symbols", type=Path)
    ap.add_argument("link_map", type=Path)
    ap.add_argument("--rebind-ld", type=Path, default=None,
                    help="existing (possibly-stale) ordered.ld to rebind in place")
    ap.add_argument("--cand-stripped", type=Path, default=None)
    ap.add_argument("--default-ld", type=Path, default=Path(DEFAULT_LD))
    ap.add_argument("--to-deployed", action="append", default=None,
                    help="relocate matched sections whose name contains this substring")
    ap.add_argument("-o", "--output", type=Path, default=None)
    ap.add_argument("--report", type=Path, default=None)
    args = ap.parse_args(argv)

    if args.rebind_ld is not None:
        script, report = rebind(
            args.deployed, args.symbols, args.link_map, args.rebind_ld,
            args.cand_stripped
        )
    else:
        script, report = relayout(
            args.deployed, args.symbols, args.link_map, args.cand_stripped,
            args.default_ld, args.to_deployed
        )

    if args.output:
        args.output.write_text(script)
    else:
        sys.stdout.write(script)
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    sys.stderr.write(json.dumps(report) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
