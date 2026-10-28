#!/usr/bin/env python3
"""tools/relayout.py  -  regenerate the whole-ELF layout linker script (ordered.ld)
that binds every candidate .text input section to its DEPLOYED window order.

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

------------------------------------------------------------------------------
Binding model (why it is order-PRESERVING by default)
------------------------------------------------------------------------------
A candidate section that is already raw-exact (its bytes, including every call
immediate, equal a deployed window) is BY DEFINITION already in its correct
deployed slot: moving it can only break it. So relayout pins the current
physical order of the live build as its backbone -- this is idempotent (a
regenerate from a good build reproduces that build's layout byte-for-byte) and
non-regressing by construction.

A global deployed-ADDRESS sort is NOT safe on a partial reconstruction: the
deployed .text is dense with tiny duplicate-normalized stubs (e.g. 13 distinct
16-byte windows that share one normalized body). Their raw match depends on
which copy sits in which slot, which pure content pairing cannot disambiguate,
so a global sort scatters them and regresses already-raw windows (measured:
127 -> 115 raw on the pump round-34 build). relayout therefore moves a section
ONLY on request, to its deployed slot relative to stable anchors:

  --to-deployed PATTERN   relocate each content-matched section whose section
                          name matches PATTERN to its deployed-order position
                          (immediately after the nearest matched section whose
                          deployed VMA precedes it). Used to pull a body whose
                          normalized form matches but whose raw fails purely on a
                          relative-call offset (drift_solver flags these) into the
                          slot that zeroes that call's delta.

Binding priority for the deployed slot of a relocated/placed section:
  1. exact content identity : (size, normalized_sha256, relocation pattern) 1:1
                              greedy pairing, deployed-address first -- the same
                              signature measure.py / drift_solver use (reused
                              here). The deployed .so is stripped, so content
                              identity is the name-stable equivalent of symbol
                              binding (a body keeps its slot across edits because
                              its normalized form is stable).
  2. call-graph adjacency   : a section with no deployed content-match keeps the
                              deployed neighbourhood of its surrounding matched
                              sections (its current anchor interval).

Inputs:
  DEPLOYED.so            deployed reference (window-order target, read-only)
  SYMBOLS.so             candidate build with symbols (.text must match stripped)
  LINK.map               the build's rust-lld -Map output
                         (PUMP_TEXT_RECORD_DIR/link.map): the authoritative
                         selector catalog -- every emitted .text.<sec> section ->
                         owning object file + VMA, in physical order.

Options:
  --cand-stripped S.so   stripped candidate (asserts .text identity with SYMBOLS)
  --default-ld PATH      pump_text_layout_default.ld skeleton to wrap
  --to-deployed PATTERN  relocate matched sections whose name contains PATTERN
                         (repeatable)
  -o OUT.ld              output (default stdout)
  --report PATH          JSON placement report

Usage:
  python3 tools/relayout.py DEPLOYED.so SYMBOLS.so LINK.map -o ordered.ld
"""
from __future__ import annotations

import argparse
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
    """[(vma:int, size:int, section:str, selector:str)] in physical order."""
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


def wrap_script(default_text: str, selectors: list[str]) -> str:
    """Expand the default.ld `.text` rule with ordered selectors + catch-all.
    Mirrors pump_text_layout.check_script so the linker wrapper accepts it."""
    rule = "  .text : { *(.text*) } :text"
    assert default_text.count(rule) == 1, "default.ld .text rule not found"
    head, tail = default_text.split(rule)
    body = "\n".join(selectors)
    return head + "  .text : {\n" + body + "\n    *(.text*)\n  } :text" + tail


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
        "deployed": str(deployed),
        "symbols": str(symbols),
        "link_map": str(link_map),
        "mode": "preserve" + (f"+relocate({len(reloc)})" if reloc else ""),
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


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("deployed", type=Path)
    ap.add_argument("symbols", type=Path)
    ap.add_argument("link_map", type=Path)
    ap.add_argument("--cand-stripped", type=Path, default=None)
    ap.add_argument("--default-ld", type=Path, default=Path(DEFAULT_LD))
    ap.add_argument("--to-deployed", action="append", default=None,
                    help="relocate matched sections whose name contains this substring")
    ap.add_argument("-o", "--output", type=Path, default=None)
    ap.add_argument("--report", type=Path, default=None)
    args = ap.parse_args(argv)

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
