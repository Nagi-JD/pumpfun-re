#!/usr/bin/env python3
"""bindiff_report - classify every divergence between a RECOVERED .so and the
DEPLOYED .so of a Solana sBPF (v1) program into one of six measured classes.

The point is to answer, per byte gap, WHICH KIND of difference it is, so the
team edits the reconstruction on evidence instead of guessing.

The six classes (see docstrings on each detector for how it is measured):
  1 ELF-STRUCTURE        ELF header / program headers / section table layout
  2 RELOCATION           .rel.dyn entries / loader-patched addresses
  3 DIFFERENT-DATA       .rodata / .data.rel.ro / .dynstr byte differences
  4 MOVED-FUNCTION       same function, different address; bytes match once
                         position + relocation are normalized (a relink)
  5 COMPILATION-DECISION same behavior, different codegen (reg-alloc, branch
                         layout, constant materialized at call-site vs baked,
                         clone-to-bake, inline) - normalized seq differs but
                         every differing region is a codegen artifact
  6 DIFFERENT-INSTRUCTION a genuinely different opcode/operand that changes a
                         comparison, branch condition, data write, or callee -
                         the real "reconstruction does something different"
  (MISSING / EXTRA        a function in only one binary - a program-level
                         sub-case of DIFFERENT-INSTRUCTION)
  (UNCLASSIFIED           a normalized difference we could not confidently
                         attribute to codegen OR semantics - never forced)

Usage:
  bindiff_report.py <recovered.so> <deployed.so> [--full] [--limit N]

Reuses tools/sbftool.py Prog for decode + function recovery; all ELF
section-header, program-header, and relocation parsing is added here.
Measure, don't guess: every classification is derived from parsed bytes.
"""
import importlib.util, struct, re, difflib, sys, os, bisect
from collections import defaultdict, Counter

# --------------------------------------------------------------------------- #
#  import sbftool.Prog (robust to where this file is dropped)
# --------------------------------------------------------------------------- #
def _load_sbftool():
    here = os.path.dirname(os.path.abspath(__file__))
    cands = [os.path.join(here, 'sbftool.py'),
             os.path.join(here, '..', 'sbftool.py'),
             'D:/dev/pumpfun-re/sbftool.py',
             '/d/dev/pumpfun-re/sbftool.py',
             'D:/dev/pumpfun-re-public/tools/sbftool.py']
    for c in cands:
        if os.path.exists(c):
            spec = importlib.util.spec_from_file_location('sbftool', c)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            return m
    raise SystemExit('bindiff_report: cannot locate sbftool.py next to this script')

S = _load_sbftool()
JMP, LD, ST, ALU = S.JMP, S.LD, S.ST, S.ALU

# sBPF relocation types (Elf64_Rel; r_info low 32 bits)
RELOC_TYPE = {1: 'R_BPF_64_64', 8: 'R_BPF_64_RELATIVE', 10: 'R_BPF_64_32'}


# --------------------------------------------------------------------------- #
#  ELF wrapper: header, program headers, section table, relocations
# --------------------------------------------------------------------------- #
class Elf:
    """Thin ELF64 (little-endian) view layered on top of an sbftool.Prog.

    Prog already parsed the section table into .sec / .secs; here we add the
    ELF header fields, the program-header table, and the .rel.dyn relocations,
    plus a byte-offset -> section attribution helper.
    """
    def __init__(self, path):
        self.path = path
        self.p = S.Prog(path)
        self.b = self.p.b
        self.hdr = self._header()
        self.phdrs = self._phdrs()
        self.relocs = self._relocs()                 # [(r_off, r_sym, r_type)]
        self.reloc_off = {r[0] for r in self.relocs}  # file offsets patched
        # instruction-slot file offset -> True if its immediate is relocated
        self.text_off = self.p.toff
        self.text_base = self.p.base

    def _header(self):
        b = self.b
        g = lambda f, o: struct.unpack_from(f, b, o)[0]
        return dict(
            e_ident=b[:16],
            e_type=g('<H', 0x10), e_machine=g('<H', 0x12), e_version=g('<I', 0x14),
            e_entry=g('<Q', 0x18), e_phoff=g('<Q', 0x20), e_shoff=g('<Q', 0x28),
            e_flags=g('<I', 0x30), e_ehsize=g('<H', 0x34),
            e_phentsize=g('<H', 0x36), e_phnum=g('<H', 0x38),
            e_shentsize=g('<H', 0x3a), e_shnum=g('<H', 0x3c), e_shstrndx=g('<H', 0x3e))

    def _phdrs(self):
        b, h, out = self.b, self.hdr, []
        for i in range(h['e_phnum']):
            o = h['e_phoff'] + i * h['e_phentsize']
            (p_type, p_flags, p_offset, p_vaddr, p_paddr,
             p_filesz, p_memsz, p_align) = struct.unpack_from('<IIQQQQQQ', b, o)
            out.append(dict(type=p_type, flags=p_flags, offset=p_offset,
                            vaddr=p_vaddr, filesz=p_filesz, memsz=p_memsz, align=p_align))
        return out

    def _relocs(self):
        rd = self.p.sec.get('.rel.dyn')
        out = []
        if rd:
            off, size = rd[4], rd[5]
            for k in range(size // 16):
                r_off, r_info = struct.unpack_from('<QQ', self.b, off + k * 16)
                out.append((r_off, r_info >> 32, r_info & 0xffffffff))
        return out

    def insn_fileoff(self, pc):
        return self.text_off + (pc - self.text_base) * 8

    def section_bytes(self, name):
        s = self.p.sec.get(name)
        if not s or s[1] == 8:          # missing or SHT_NOBITS
            return b''
        return self.b[s[4]:s[4] + s[5]]

    def section_at(self, off):
        for nm, s in self.p.secs:
            if not nm or s[1] == 8:
                continue
            if s[4] <= off < s[4] + s[5]:
                return nm
        return None


# --------------------------------------------------------------------------- #
#  finding record
# --------------------------------------------------------------------------- #
class Item:
    __slots__ = ('cls', 'loc', 'why', 'nbytes', 'heur')
    def __init__(self, cls, loc, why, nbytes=0, heur=''):
        self.cls, self.loc, self.why, self.nbytes, self.heur = cls, loc, why, nbytes, heur


CLASSES = ['ELF-STRUCTURE', 'RELOCATION', 'DIFFERENT-DATA', 'MOVED-FUNCTION',
           'COMPILATION-DECISION', 'DIFFERENT-INSTRUCTION', 'MISSING/EXTRA',
           'UNCLASSIFIED']


def _bytediff(a, b):
    """positional byte-mismatch count up to min length, plus |len| delta."""
    n = min(len(a), len(b))
    d = sum(1 for i in range(n) if a[i] != b[i])
    return d + abs(len(a) - len(b))


# --------------------------------------------------------------------------- #
#  (1) ELF-STRUCTURE
# --------------------------------------------------------------------------- #
def diff_elf_structure(er, ed):
    """Compare ELF header fields, program headers, and the section table.

    Detection: field-by-field equality on parsed ELF64 structures. Any field
    that differs is a structural (layout/linking) divergence, not a content
    one. e_entry lives at byte 24, which is the first whole-file byte that
    differs between these two binaries.
    """
    items = []
    FIELD_BYTE = {'e_entry': 24, 'e_phoff': 32, 'e_shoff': 40, 'e_flags': 48,
                  'e_phnum': 56, 'e_shentsize': 58, 'e_shnum': 60, 'e_shstrndx': 62}
    FIELD_W = {'e_entry': 8, 'e_phoff': 8, 'e_shoff': 8, 'e_flags': 4,
               'e_phnum': 2, 'e_shentsize': 2, 'e_shnum': 2, 'e_shstrndx': 2}
    for f in ['e_type', 'e_machine', 'e_version', 'e_entry', 'e_phoff', 'e_shoff',
              'e_flags', 'e_phnum', 'e_shnum', 'e_shstrndx']:
        if er.hdr[f] != ed.hdr[f]:
            byte = FIELD_BYTE.get(f)
            loc = f'ELF.{f}' + (f'(byte {byte})' if byte is not None else '')
            why = f'{hex(er.hdr[f]) if er.hdr[f] > 9 else er.hdr[f]} -> ' \
                  f'{hex(ed.hdr[f]) if ed.hdr[f] > 9 else ed.hdr[f]}'
            items.append(Item('ELF-STRUCTURE', loc, why, FIELD_W.get(f, 8)))

    # program headers
    if len(er.phdrs) != len(ed.phdrs):
        items.append(Item('ELF-STRUCTURE', 'program-headers',
                          f'{len(er.phdrs)} -> {len(ed.phdrs)} segments',
                          abs(len(er.phdrs) - len(ed.phdrs)) * er.hdr['e_phentsize']))
    for i, (pr, pd) in enumerate(zip(er.phdrs, ed.phdrs)):
        changed = [k for k in pr if pr[k] != pd[k]]
        if changed:
            nb = sum(1 for _ in changed) * 8
            items.append(Item('ELF-STRUCTURE', f'phdr[{i}] type={pr["type"]}',
                              'segment layout: ' + ','.join(changed), nb))

    # section table (match by name)
    rn = {nm: s for nm, s in er.p.secs if nm}
    dn = {nm: s for nm, s in ed.p.secs if nm}
    if list(rn) != list(dn):
        only_r = [n for n in rn if n not in dn]
        only_d = [n for n in dn if n not in rn]
        if only_r or only_d:
            items.append(Item('ELF-STRUCTURE', 'section-table',
                              f'section set differs rec-only={only_r} dep-only={only_d}',
                              er.hdr['e_shentsize']))
    for nm in rn:
        if nm not in dn:
            continue
        sr, sd = rn[nm], dn[nm]
        # fields: 3=addr 4=offset 5=size 9=entsize ; type/flags = 1/2
        lab = []
        if sr[3] != sd[3]: lab.append(f'addr {hex(sr[3])}->{hex(sd[3])}')
        if sr[4] != sd[4]: lab.append(f'off {hex(sr[4])}->{hex(sd[4])}')
        if sr[5] != sd[5]: lab.append(f'size {hex(sr[5])}->{hex(sd[5])}')
        if sr[1] != sd[1] or sr[2] != sd[2]: lab.append('type/flags')
        if lab:
            items.append(Item('ELF-STRUCTURE', f'shdr {nm}', '; '.join(lab),
                              er.hdr['e_shentsize']))
    return items


# --------------------------------------------------------------------------- #
#  (2) RELOCATION
# --------------------------------------------------------------------------- #
def diff_relocations(er, ed):
    """Compare the .rel.dyn relocation tables.

    Detection: parse both tables into (r_offset, r_sym, r_type) tuples and
    compare counts + a positional byte diff of the raw table. Relocations are
    loader-patched addresses; because .text and the data sections shifted, the
    r_offset of nearly every entry moved. This is address/linking noise, never
    a semantic change in its own right.
    """
    items = []
    br = er.section_bytes('.rel.dyn')
    bd = ed.section_bytes('.rel.dyn')
    if not br and not bd:
        return items
    tr = Counter(RELOC_TYPE.get(t, t) for _, _, t in er.relocs)
    td = Counter(RELOC_TYPE.get(t, t) for _, _, t in ed.relocs)
    why = (f'{len(er.relocs)} -> {len(ed.relocs)} entries; '
           f'types rec={dict(tr)} dep={dict(td)}; r_offsets shift with .text/.data growth')
    items.append(Item('RELOCATION', '.rel.dyn', why, _bytediff(br, bd)))
    return items


# --------------------------------------------------------------------------- #
#  (3) DIFFERENT-DATA
# --------------------------------------------------------------------------- #
_BUILD_RE = re.compile(rb'(/home/|/root/|/runner/|\.cargo|rustc/|/platform-tools/|registry/src)')

def _strings(blob, minlen=5):
    return set(re.findall(rb'[\x20-\x7e]{%d,}' % minlen, blob))

def diff_data(er, ed):
    """Diff the read-only / data sections byte-for-byte.

    Detection: for each data section (.rodata, .data.rel.ro, .dynstr) take the
    section bytes from each binary and positional-diff them. For .rodata we
    additionally extract printable string runs and surface the symmetric
    difference, flagging baked build-path strings (/home/runner/..., .cargo,
    rustc, platform-tools) which are a hallmark of the real build environment.
    """
    items = []
    for nm in ['.rodata', '.data.rel.ro', '.dynstr']:
        br, bd = er.section_bytes(nm), ed.section_bytes(nm)
        if not br and not bd:
            continue
        nb = _bytediff(br, bd)
        if nb == 0:
            continue
        why = f'{len(br)} -> {len(bd)} bytes; {nb} differ'
        if nm == '.rodata':
            sr, sd = _strings(br), _strings(bd)
            ro = sorted(s for s in sr - sd)
            do = sorted(s for s in sd - sr)
            bpr = [s for s in ro if _BUILD_RE.search(s)]
            bpd = [s for s in do if _BUILD_RE.search(s)]
            why += f'; strings rec-only={len(ro)} dep-only={len(do)}'
            if bpr or bpd:
                sample = (bpd or bpr)[0][:70].decode('latin1', 'replace')
                why += f'; BAKED BUILD-PATH strings differ (e.g. "{sample}")'
        items.append(Item('DIFFERENT-DATA', nm, why, nb))
    return items


# --------------------------------------------------------------------------- #
#  .text normalization
# --------------------------------------------------------------------------- #
def normalize_insn(elf, ins):
    """Reduce one instruction to a position/relocation-independent token.

    Blanked (set to a placeholder) because they are position/relocation noise:
      - lddw immediates whose slot is relocated      -> ('lddw', dst, 'ADDR')
      - call targets that are relocated / imm == -1   -> ('call', 'RELOC')
      - local relative call targets                   -> ('call', 'LOCAL')
    Kept (semantically meaningful):
      - branch relative offsets (position-independent; layout handled later)
      - load/store field offsets and immediate values
      - lddw literal immediates that are NOT relocated (real constants / discs)
      - ALU opcodes and immediates, registers
    """
    op, mn = ins.op, ins.mn
    foff = elf.insn_fileoff(ins.pc)
    if op == 0x18:                                   # lddw
        if foff in elf.reloc_off:
            return ('lddw', ins.dst, 'ADDR')
        return ('lddw', ins.dst, ins.imm)
    if op == 0x85:                                   # call
        if (ins.imm & 0xffffffff) == 0xffffffff or foff in elf.reloc_off:
            return ('call', 'RELOC')
        return ('call', 'LOCAL')
    if op == 0x8d:
        return ('callx', ins.imm)
    if op == 0x95:
        return ('exit',)
    if op in JMP:
        src = ('r', ins.src) if (op & 0x08) else ('i', ins.imm)
        return (mn, ins.dst, src, ins.off)           # keep relative off
    if op in LD:
        return (mn, ins.dst, ins.src, ins.off)
    if op in ST:
        val = ('r', ins.src) if (op & 0x3) == 3 else ('i', ins.imm)
        return (mn, ins.dst, ins.off, val)
    if op in ALU:
        src = ('r', ins.src) if (op & 0x08) else ('i', ins.imm)
        return (mn, ins.dst, src)
    return ('.byte', op)


def norm_seq(elf, start):
    return [normalize_insn(elf, i) for i in elf.p.func_body(start)]


def helper_set(elf, start):
    """Set of callees by identity (syscall name, else RELOC / LOCAL)."""
    hs = set()
    for i in elf.p.func_body(start):
        if i.op == 0x85:
            if (i.imm & 0xffffffff) == 0xffffffff:
                hs.add('RELOC')
            else:
                t = i.pc + 1 + i.imm
                hs.add(elf.p.name.get(t, 'LOCAL'))
        elif i.op == 0x8d:
            hs.add('callx')
    return hs


def func_bytes(elf, start):
    body = elf.p.func_body(start)
    if not body:
        return b''
    lo = elf.insn_fileoff(body[0].pc)
    last = body[-1]
    hi = elf.insn_fileoff(last.pc) + (16 if last.op == 0x18 else 8)
    return elf.b[lo:hi]


# --------------------------------------------------------------------------- #
#  region-level codegen vs semantic decision (the heuristic core)
# --------------------------------------------------------------------------- #
_MOV = {'mov32', 'mov64'}

def _canon(region, strip_regs=True, drop_branchoff=False, drop_imm_movs=False):
    """Project a token region onto a canonical form for equality tests."""
    out = []
    for t in region:
        mn = t[0]
        if drop_imm_movs and mn in _MOV and t[2][0] == 'i':
            continue
        if drop_imm_movs and mn == 'lddw' and t[2] != 'ADDR':
            continue
        out.append(_canon_tok(t, strip_regs, drop_branchoff))
    return out

def _canon_tok(t, strip_regs, drop_branchoff):
    mn = t[0]
    R = 'R'
    if mn == 'lddw':
        return ('lddw', R if strip_regs else t[1], t[2])
    if mn in ('call', 'callx', 'exit', '.byte'):
        return t
    if mn in JMP or mn == 'ja':
        # (mn, dst, srctuple, off)
        dst = R if strip_regs else t[1]
        src = ('r', R) if (strip_regs and t[2][0] == 'r') else t[2]
        off = 'B' if drop_branchoff else t[3]
        return (mn, dst, src, off)
    if mn in ('ldxw', 'ldxh', 'ldxb', 'ldxdw'):
        dst = R if strip_regs else t[1]
        src = R if strip_regs else t[2]
        return (mn, dst, src, t[3])
    if mn in ('stw', 'sth', 'stb', 'stdw', 'stxw', 'stxh', 'stxb', 'stxdw'):
        dst = R if strip_regs else t[1]
        val = ('r', R) if (strip_regs and t[3][0] == 'r') else t[3]
        return (mn, dst, t[2], val)
    # ALU: (mn, dst, srctuple)
    dst = R if strip_regs else t[1]
    src = ('r', R) if (strip_regs and t[2][0] == 'r') else t[2]
    return (mn, dst, src)


def _semantic_cores(region):
    """Multiset of MEANING-bearing cores, with register identity, branch
    distance, and stack-frame (r10-relative) spill offsets removed. Equal core
    multisets => same observable behavior (differences are codegen). A store
    or load through a NON-frame base register keeps its field offset because
    that selects which struct field is touched (semantic)."""
    c = Counter()
    for t in region:
        mn = t[0]
        if mn in ('stw', 'sth', 'stb', 'stdw', 'stxw', 'stxh', 'stxb', 'stxdw'):
            if t[1] == 10:
                continue                                    # stack spill: pure codegen, ignore
            val = 'r' if t[3][0] == 'r' else t[3]
            c[('ST', mn, t[2], val)] += 1                   # struct field write
        elif mn in ('ldxw', 'ldxh', 'ldxb', 'ldxdw'):
            if t[2] == 10:
                continue                                    # stack reload: pure codegen, ignore
            c[('LD', mn, t[3])] += 1                         # struct field read
        elif mn in JMP or mn == 'ja':
            src = 'r' if t[2][0] == 'r' else t[2]            # keep compared literal
            c[('J', mn, src)] += 1
        elif mn in ('call', 'callx'):
            c[('C', t[1] if len(t) > 1 else '')] += 1
        elif mn == 'lddw':
            c[('K', t[2])] += 1                              # ADDR or literal
        elif mn in ('exit', '.byte'):
            c[(mn,)] += 1
        else:  # ALU (incl mov)
            src = 'r' if t[2][0] == 'r' else t[2]            # keep ALU literal
            c[('A', mn, src)] += 1
    return c


_CORE_LABEL = {'ST': 'changed-field-write', 'LD': 'changed-field-read',
               'J': 'changed-branch-condition', 'A': 'changed-computation',
               'C': 'changed-callee', 'K': 'changed-literal'}


def classify_region(ra, rb):
    """Return (kind, labelset) for one differing region. kind in
    {'codegen','semantic'}; labelset is a set of atomic reason strings."""
    # 1. pure register allocation
    if _canon(ra) == _canon(rb):
        return 'codegen', {'register-allocation'}
    # 2. branch layout only (relative offsets shifted by nearby insertions)
    if _canon(ra, drop_branchoff=True) == _canon(rb, drop_branchoff=True):
        return 'codegen', {'branch-layout'}
    # 3. constant materialized at call-site vs baked (add/remove imm movs/lddw)
    if _canon(ra, drop_branchoff=True, drop_imm_movs=True) == \
       _canon(rb, drop_branchoff=True, drop_imm_movs=True):
        return 'codegen', {'constant-materialization'}
    # 4. meaning-bearing core comparison (frame spills + regs + layout ignored)
    ca, cb = _semantic_cores(ra), _semantic_cores(rb)
    if ca != cb:
        delta = (cb - ca) + (ca - cb)
        labels = {_CORE_LABEL.get(k[0], str(k[0])) for k in delta}
        return 'semantic', labels
    # 5. cores identical -> same behavior, only spill/schedule/layout differs
    return 'codegen', {'frame-or-schedule'}


def classify_func_pair(er, ed, sr, sd):
    """Classify an aligned function pair. Returns (cls, why, heur, raw_bytes)."""
    a, b = norm_seq(er, sr), norm_seq(ed, sd)
    raw = _bytediff(func_bytes(er, sr), func_bytes(ed, sd))
    if a == b:
        if raw == 0 and sr == sd:
            return 'IDENTICAL', '', '', 0
        reasons = []
        if sr != sd:
            reasons.append('relinked address')
        if raw:
            reasons.append('relocated immediates')
        return ('MOVED-FUNCTION',
                'normalized-identical; differs only in ' + (' + '.join(reasons) or 'position'),
                'normalized-equal', raw)

    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    delta = len(b) - len(a)
    hr, hd = helper_set(er, sr), helper_set(ed, sd)
    sem = set(); cg = set(); amb = set()
    if hr != hd:
        # a changed callee identity (syscall gained/lost) is semantic; a change
        # only in the LOCAL/RELOC split is position noise, not a new callee.
        if (hr - {'LOCAL', 'RELOC'}) != (hd - {'LOCAL', 'RELOC'}):
            sem.add('changed-callee')
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        kind, labels = classify_region(a[i1:i2], b[j1:j2])
        (sem if kind == 'semantic' else cg if kind == 'codegen' else amb).update(labels)

    def cap(rs, n=4):
        rs = sorted(rs)
        return ','.join(rs[:n]) + (f',+{len(rs) - n}' if len(rs) > n else '')

    if sem:
        why = f'{len(a)}->{len(b)} insns (delta {delta:+d}); SEMANTIC: {cap(sem)}'
        if cg:
            why += f' (+codegen: {cap(cg, 2)})'
        return 'DIFFERENT-INSTRUCTION', why, cap(sem), raw
    if amb:
        why = f'{len(a)}->{len(b)} insns (delta {delta:+d}); ambiguous: {cap(amb)}'
        return 'UNCLASSIFIED', why, 'ambiguous', raw
    why = f'{len(a)}->{len(b)} insns (delta {delta:+d}); codegen: {cap(cg)}'
    return 'COMPILATION-DECISION', why, cap(cg), raw


# --------------------------------------------------------------------------- #
#  function alignment
# --------------------------------------------------------------------------- #
def norm_hash(seq):
    return hash(tuple(seq))


def k2_hash(seq):
    """Register-allocation and branch-layout insensitive content hash. Two
    functions with the same logic but different register choices / branch
    distances (pure codegen) collapse to the same K2 hash; literal immediates,
    field offsets, opcodes and callee kinds are kept so distinct logic does
    not collide."""
    return hash(tuple(_canon(seq, strip_regs=True, drop_branchoff=True)))


def skel_seq(elf, start):
    """Mnemonic-only skeleton (no registers, no offsets, no immediates). Used
    ONLY for fuzzy alignment across builds that drifted in stack layout /
    baked constants; classification always uses the full normalized tokens."""
    return [('lddw' if i.op == 0x18 else i.mn) for i in elf.p.func_body(start)]


def _kgrams(sk, k=6):
    """Set of k-grams of a mnemonic skeleton, for containment similarity."""
    if len(sk) < k:
        return frozenset([tuple(sk)]) if sk else frozenset()
    return frozenset(tuple(sk[i:i + k]) for i in range(len(sk) - k + 1))


def _real_disc(v):
    """True only for a plausible REAL Anchor discriminator: the first 8 bytes
    of sha256('global:<name>'), i.e. high-entropy. Rejects synthetic/structured
    ids (leading-zero most-significant byte, or >=3 zero bytes) that sbftool or
    a stray lddw constant can produce - those are NOT identity evidence."""
    b = (v & 0xffffffffffffffff).to_bytes(8, 'little')
    if b[7] == 0:              # most-significant byte zero -> not a sha256 disc
        return False
    if b.count(0) >= 3:        # too many zero bytes -> structured / synthetic
        return False
    return True


def _prologue_ok(ska, skb, n=8, thresh=0.75):
    """Both functions must share a frame-setup prologue to be the same function.
    Compares the first n normalized mnemonics; incompatible prologues (e.g.
    `mov,add,lddw,call` vs `mov,mov,mov,call`) are rejected regardless of
    overall containment."""
    pa, pb = ska[:n], skb[:n]
    if not pa or not pb:
        return False
    return difflib.SequenceMatcher(None, pa, pb, autojunk=False).ratio() >= thresh


def anchor_handlers(elf):
    """Map dispatcher discriminator -> handler stub start, for anchor programs.
    Reuses the sha256('global:'+name) discriminator model; we do not need the
    IDL names, only the stub start each discriminator dispatches to."""
    out = {}
    order = elf.p.order
    ins = elf.p.ins
    for idx, pc in enumerate(order):
        i = ins[pc]
        if i.op != 0x18:
            continue
        dd = (i.imm & 0xffffffffffffffff)
        if not _real_disc(dd):          # reject synthetic/structured ids
            continue
        # scan the next few insns for the jeq that selects this handler
        for pc2 in order[idx + 1: idx + 4]:
            j = ins.get(pc2)
            if j and j.mn == 'jeq':
                t = pc2 + 1 + j.off
                h = t
                for q in range(t, t + 40):
                    k = ins.get(q)
                    if k and k.op == 0x85:
                        h = q + 1 + k.imm
                        break
                out.setdefault(dd, h)
                break
    return out


def align_functions(er, ed):
    """Greedy multi-key alignment, strongest key first. Returns
    (pairs, rec_only, dep_only, rec_k2, dep_k2) where pairs=[(sr,sd,how)] and
    rec_k2/dep_k2 are {k2_hash: [starts]} used by the caller to tell clones
    (a leftover whose logic still exists on the other side) from genuinely
    added/removed functions."""
    rstarts = list(er.p.starts)
    dstarts = list(ed.p.starts)
    rseq = {s: norm_seq(er, s) for s in rstarts}
    dseq = {s: norm_seq(ed, s) for s in dstarts}
    rh = {s: norm_hash(q) for s, q in rseq.items()}
    dh = {s: norm_hash(q) for s, q in dseq.items()}
    rk2 = {s: k2_hash(q) for s, q in rseq.items()}
    dk2 = {s: k2_hash(q) for s, q in dseq.items()}

    pairs = []
    d_used = set()

    def exact_pass(key_r, key_d, how):
        bucket = defaultdict(list)
        for s in dstarts:
            if s not in d_used:
                bucket[key_d[s]].append(s)
        for h in bucket:
            bucket[h].sort()
        r_un = []
        for s in sorted(r_un_ref):
            cand = [x for x in bucket.get(key_r[s], []) if x not in d_used]
            if cand:
                pick = min(cand, key=lambda x: abs(x - s))
                d_used.add(pick)
                pairs.append((s, pick, how))
            else:
                r_un.append(s)
        return r_un

    # Pass 1: exact normalized hash (near-identical => MOVED / relink).
    r_un_ref = rstarts
    r_un = exact_pass(rh, dh, 'exact')
    # Pass 1b: register/branch-insensitive hash (pure codegen differences).
    r_un_ref = r_un
    r_un = exact_pass(rk2, dk2, 'k2')

    # Pass 2: anchor-discriminator pairing for still-unmatched handler stubs.
    ah_r, ah_d = anchor_handlers(er), anchor_handlers(ed)
    r_un_set = set(r_un)
    for disc, hr in ah_r.items():
        hd = ah_d.get(disc)
        if hd is None:
            continue
        sr, sd = er.p.func_start(hr), ed.p.func_start(hd)
        if sr in r_un_set and sd not in d_used:
            pairs.append((sr, sd, 'disc'))
            r_un_set.discard(sr); d_used.add(sd)
    r_un = sorted(r_un_set)
    d_un = [s for s in dstarts if s not in d_used]

    # Pass 3: greedy k-gram CONTAINMENT alignment of the leftover functions.
    # Containment = |shared k-grams| / |k-grams of the SMALLER function|, over
    # the mnemonic skeleton (register/offset/immediate/address insensitive).
    # Containment (not symmetric ratio) is used so a function that was inlined
    # into a larger one on the other side still scores high against its core.
    # Score all candidate pairs within a size-ratio window, then pair greedily
    # highest-first, each function used at most once.
    rskel = {s: skel_seq(er, s) for s in r_un}
    dskel = {s: skel_seq(ed, s) for s in d_un}
    rgrams = {s: _kgrams(rskel[s]) for s in r_un}
    dgrams = {s: _kgrams(dskel[s]) for s in d_un}
    d_by_len = defaultdict(list)
    for s in d_un:
        d_by_len[len(dskel[s])].append(s)
    d_lens = sorted(d_by_len)
    scored = []
    budget = 3000000
    CONT_MIN = 0.75
    for s in r_un:
        la = max(1, len(rskel[s]))
        ga = rgrams[s]
        if not ga:
            continue
        lo, hi = la * 0.70, la * 1.43        # deployed/recovered length window
        for L in d_lens[bisect.bisect_left(d_lens, int(lo)):
                        bisect.bisect_right(d_lens, int(hi) + 1)]:
            for ds in d_by_len[L]:
                if budget <= 0:
                    break
                budget -= 1
                gb = dgrams[ds]
                if not gb:
                    continue
                inter = len(ga & gb)
                if not inter:
                    continue
                cont = inter / min(len(ga), len(gb))
                if cont >= CONT_MIN and _prologue_ok(rskel[s], dskel[ds]):
                    scored.append((cont, -abs(la - L), s, ds))
    scored.sort(reverse=True)
    rtaken, dtaken = set(), set()
    for cont, _, s, ds in scored:
        if s in rtaken or ds in dtaken:
            continue
        rtaken.add(s); dtaken.add(ds)
        pairs.append((s, ds, 'similar'))

    paired_r = {s for s, _, _ in pairs}
    paired_d = {d for _, d, _ in pairs}
    rec_only = [s for s in rstarts if s not in paired_r]
    dep_only = [s for s in dstarts if s not in paired_d]
    rec_k2 = defaultdict(list)
    for s in rstarts:
        rec_k2[rk2[s]].append(s)
    dep_k2 = defaultdict(list)
    for s in dstarts:
        dep_k2[dk2[s]].append(s)
    return pairs, rec_only, dep_only, dict(rec_k2), dict(dep_k2)


# --------------------------------------------------------------------------- #
#  driver
# --------------------------------------------------------------------------- #
def run(rec_path, dep_path):
    er, ed = Elf(rec_path), Elf(dep_path)

    items = []
    items += diff_elf_structure(er, ed)
    items += diff_relocations(er, ed)
    items += diff_data(er, ed)

    # .text
    pairs, rec_only, dep_only, rec_k2, dep_k2 = align_functions(er, ed)
    name_r = _handler_names(er)
    name_d = _handler_names(ed)
    text_items = []
    for sr, sd, how in pairs:
        cls, why, heur, raw = classify_func_pair(er, ed, sr, sd)
        if cls == 'IDENTICAL':
            continue
        nm = name_r.get(sr) or name_d.get(sd) or ''
        loc = f'fn {nm + " " if nm else ""}@{hex(sr)}/{hex(sd)}'
        text_items.append(Item(cls, loc, why + (f' [{how}-match]' if how == 'similar' else ''),
                               raw, heur))

    # Leftovers: a function whose skeleton still closely matches SOME function
    # on the other side is a clone/duplicate of it (function-count difference
    # from cloning = COMPILATION-DECISION). A function whose shape exists
    # nowhere on the other side is genuinely added/removed (MISSING/EXTRA =
    # a program-level sub-case of DIFFERENT-INSTRUCTION).
    rpool = _grams_pool(er)
    dpool = _grams_pool(ed)

    def leftover(elf, s, pool, side):
        nm = (name_r if side == 'rec' else name_d).get(s, '')
        tail = 'recovered-only' if side == 'rec' else 'deployed-only'
        lab = f'fn {nm + " " if nm else ""}@{hex(s)} ({tail})'
        n = len(elf.p.func_body(s)); nb = len(func_bytes(elf, s))
        cont = _best_twin_containment(skel_seq(elf, s), pool)
        # Only a near-exact duplicate (containment >= 0.90) is a clone: its
        # logic is genuinely present on the other side, it just lost the 1:1
        # greedy claim (e.g. deployed cloned a generic builder N times).
        if cont >= 0.90:
            why = ('recovered keeps a generic function deployed cloned/specialized away'
                   if side == 'rec' else
                   'deployed clone/specialization of a function the recovered build shares (clone-to-bake)')
            return Item('COMPILATION-DECISION', lab, f'{why}; skel-containment {cont:.2f}', nb,
                        'clone-source' if side == 'rec' else 'clone')
        # Otherwise genuinely unmatched. Distinguish a possible same-function
        # that the stage-2 gates (length / prologue) blocked (0.75-0.90) from a
        # true non-correspondence (< 0.75).
        absent = ('logic present only in recovered build (absent from deployed)'
                  if side == 'rec' else 'logic present only in deployed build (absent from recovered)')
        if cont >= 0.75:
            return Item('MISSING/EXTRA', lab,
                        f'{absent}; {n} insns, containment {cont:.2f} - POSSIBLE same fn blocked by '
                        f'length/prologue gate (review)', nb, 'gated')
        return Item('MISSING/EXTRA', lab,
                    f'{absent}; {n} insns, best cross-build containment {cont:.2f} - genuinely unmatched',
                    nb, 'unmatched')

    for s in rec_only:
        text_items.append(leftover(er, s, dpool, 'rec'))
    for s in dep_only:
        text_items.append(leftover(ed, s, rpool, 'dep'))
    items += text_items

    whole = _first_wholefile_diff(er.b, ed.b)
    return er, ed, items, pairs, rec_only, dep_only, whole


def _handler_names(elf):
    """Map handler-stub start AND the function right after it (the builder) to
    an anchor label, so the report can name the instruction a diff belongs to.
    Names are the discriminator hex (IDL-free) unless an IDL is available."""
    labels = {}
    disc_names = _idl_disc_names()
    ah = anchor_handlers(elf)
    starts = elf.p.starts
    for disc, h in ah.items():
        s = elf.p.func_start(h)
        nm = disc_names.get(disc.to_bytes(8, 'little'), 'disc_%016x' % disc)
        labels[s] = nm
        # the builder is the function immediately following a thin stub
        body = elf.p.func_body(s)
        if len(body) <= 10:
            nxt = [x for x in starts if x > s]
            if nxt:
                labels.setdefault(nxt[0], nm + '.builder')
    return labels


def _idl_disc_names():
    """Best-effort: load anchor discriminator -> name from a nearby IDL. Pure
    convenience for labeling; classification never depends on it."""
    import hashlib, json, glob
    out = {}
    pats = ['D:/dev/ext/pumpfun-source/programs/*/idls/*.json',
            '/d/dev/ext/pumpfun-source/programs/*/idls/*.json']
    for pat in pats:
        for f in glob.glob(pat):
            try:
                idl = json.load(open(f))
                for ins in idl.get('instructions', []):
                    n = ins['name']
                    out[hashlib.sha256(('global:' + n).encode()).digest()[:8]] = n
            except Exception:
                pass
    return out


def _grams_pool(elf):
    """List of (len, kgram-set) for every function, for clone/twin lookup."""
    return [(len(sk), _kgrams(sk)) for sk in (skel_seq(elf, s) for s in elf.p.starts)]


def _best_twin_containment(sk, pool):
    """Max containment of sk's k-grams inside any pooled function. High value
    => this function's logic still exists on the other side (a clone)."""
    g = _kgrams(sk)
    if not g:
        return 0.0
    best = 0.0
    for L, gb in pool:
        if not gb:
            continue
        inter = len(g & gb)
        if inter:
            c = inter / min(len(g), len(gb))
            if c > best:
                best = c
                if best >= 0.999:
                    break
    return best


def _first_wholefile_diff(a, b):
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    return n if len(a) != len(b) else None


# --------------------------------------------------------------------------- #
#  reporting
# --------------------------------------------------------------------------- #
def summarize(items):
    cnt = Counter(); byt = Counter()
    for it in items:
        cnt[it.cls] += 1; byt[it.cls] += it.nbytes
    return cnt, byt


def print_report(er, ed, items, pairs, rec_only, dep_only, whole, full=False, limit=60):
    cnt, byt = summarize(items)
    out = []
    out.append('=' * 78)
    out.append('BINARY DIVERGENCE REPORT  (Solana sBPFv1)')
    out.append('=' * 78)
    out.append(f'recovered : {er.path}')
    out.append(f'            {len(er.b):,} bytes | {len(er.p.order):,} insns | '
               f'{len(er.p.starts)} functions | e_entry {hex(er.hdr["e_entry"])}')
    out.append(f'deployed  : {ed.path}')
    out.append(f'            {len(ed.b):,} bytes | {len(ed.p.order):,} insns | '
               f'{len(ed.p.starts)} functions | e_entry {hex(ed.hdr["e_entry"])}')
    if whole is not None:
        sec = er.section_at(whole) or ed.section_at(whole) or 'ELF-header'
        tag = 'ELF-STRUCTURE (e_entry)' if whole == 24 else f'{sec}'
        out.append(f'first whole-file byte diff: offset {whole} (0x{whole:x}) -> {tag}')
    out.append('')
    out.append('Counts per class:')
    out.append(f'  {"CLASS":<22}{"ITEMS":>7}{"BYTES":>14}')
    total = 0
    for c in CLASSES:
        if cnt[c]:
            out.append(f'  {c:<22}{cnt[c]:>7}{byt[c]:>14,}')
            total += byt[c]
    out.append(f'  {"-"*43}')
    out.append(f'  {"TOTAL differing bytes":<22}{"":>7}{total:>14,}')
    out.append('')

    def row(it, show_heur=False):
        why = it.why
        if show_heur and it.heur:
            why += f'  [heuristic: {it.heur}]'
        loc = it.loc if len(it.loc) <= 45 else it.loc[:44] + '~'
        return f'  {loc:<46}{it.cls:<22}{why}'

    # Group 1 (always fully listed): the high-signal, low-volume classes.
    out.append('Structural / data / semantic divergences (full list):')
    out.append(f'  {"LOCATION":<46}{"CLASS":<22}WHY')
    head = ['ELF-STRUCTURE', 'RELOCATION', 'DIFFERENT-DATA']
    for c in head:
        for it in [i for i in items if i.cls == c]:
            out.append(row(it))
    # DIFFERENT-INSTRUCTION pairwise (the real semantic diffs) + clone-free
    # COMPILATION-DECISION pairwise, both fully listed up to `limit`.
    diff = [i for i in items if i.cls == 'DIFFERENT-INSTRUCTION']
    diff.sort(key=lambda it: -it.nbytes)
    out.append('')
    out.append(f'  -- DIFFERENT-INSTRUCTION ({len(diff)}) : genuine opcode/operand/callee changes --')
    for it in diff[:limit] if not full else diff:
        out.append(row(it, show_heur=False))
    if not full and len(diff) > limit:
        out.append(f'  ... (+{len(diff) - limit} more; --full)')

    comp = [i for i in items if i.cls == 'COMPILATION-DECISION']
    comp_pairs = [i for i in comp if i.heur not in ('clone', 'clone-source')]
    comp_clone = [i for i in comp if i.heur in ('clone', 'clone-source')]
    comp_pairs.sort(key=lambda it: -it.nbytes)
    out.append('')
    out.append(f'  -- COMPILATION-DECISION, aligned pairs ({len(comp_pairs)}) : same behavior, codegen differs --')
    for it in comp_pairs[:limit] if not full else comp_pairs:
        out.append(row(it))
    if not full and len(comp_pairs) > limit:
        out.append(f'  ... (+{len(comp_pairs) - limit} more; --full)')

    uncl = [i for i in items if i.cls == 'UNCLASSIFIED']
    out.append('')
    out.append(f'  -- UNCLASSIFIED ({len(uncl)}) : could not confidently classify --')
    for it in (uncl if full else sorted(uncl, key=lambda it: -it.nbytes)[:12]):
        out.append(row(it))
    if not full and len(uncl) > 12:
        out.append(f'  ... (+{len(uncl) - 12} more; --full)')

    # Group 2 (summarized unless --full): the bulk, address/boundary classes.
    moved = [i for i in items if i.cls == 'MOVED-FUNCTION']
    me = [i for i in items if i.cls == 'MISSING/EXTRA']
    out.append('')
    out.append('Bulk classes (address / boundary; summarized):')
    out.append(f'  MOVED-FUNCTION        : {len(moved):>4} functions, {sum(i.nbytes for i in moved):>10,} bytes '
               f'(normalized-identical; relink + relocated immediates only)')
    out.append(f'  COMPILATION-DECISION  : {len(comp_clone):>4} clones,    {sum(i.nbytes for i in comp_clone):>10,} bytes '
               f'(function-count-from-cloning; skeleton twin on other side)')
    me_bytes = sum(i.nbytes for i in me)
    rt = er.p.sec.get('.text'); dt = ed.p.sec.get('.text')
    real_delta = abs(dt[5] - rt[5]) if rt and dt else 0
    gated = [i for i in me if i.heur == 'gated']
    unm = [i for i in me if i.heur != 'gated']
    out.append(f'  MISSING/EXTRA         : {len(me):>4} functions, {me_bytes:>10,} bytes '
               f'(no cross-build twin -> genuinely added/removed)')
    out.append(f'  MISSING/EXTRA after 2-stage alignment: {len(me)} fns / {me_bytes:,} bytes '
               f'(real .text delta = {real_delta:,} B)')
    out.append(f'     - genuinely unmatched (containment <0.75) : {len(unm)} fns / '
               f'{sum(i.nbytes for i in unm):,} bytes  [true non-correspondence / boundary difference]')
    out.append(f'     - possible same-fn, gate-blocked (0.75-0.90): {len(gated)} fns / '
               f'{sum(i.nbytes for i in gated):,} bytes  [review - length/prologue gate]')
    named_me = [it for it in me if 'disc_' not in it.loc and '@' in it.loc][:10]
    for it in (me if full else named_me):
        out.append(row(it))
    if full:
        out.append('')
        out.append('MOVED-FUNCTION (full):')
        for it in moved:
            out.append(row(it))
        out.append('COMPILATION-DECISION clones (full):')
        for it in comp_clone:
            out.append(row(it))
    return '\n'.join(out)


def main(argv):
    args = [a for a in argv if not a.startswith('--')]
    full = '--full' in argv
    limit = 60
    for a in argv:
        if a.startswith('--limit'):
            limit = int(a.split('=')[1]) if '=' in a else 60
    if len(args) < 2:
        print(__doc__); return 1
    er, ed, items, pairs, rec_only, dep_only, whole = run(args[0], args[1])
    print(print_report(er, ed, items, pairs, rec_only, dep_only, whole, full, limit))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
