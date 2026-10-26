#!/usr/bin/env python3
"""handler_anatomy - per-instruction-handler anatomy for a deployed sBPF program.

Recovers, from the deployed bytes only, a body-accurate anatomy of every instruction
handler the program's dispatcher exposes:

  * true body extent (`[start, next_start)`) using relocation-aware function starts:
    a call site that carries an unapplied R_BPF_64_32 relocation is never itself a
    function start, so a syscall inside a handler no longer splits the body;
  * the self-identifying `Instruction: <PascalCase>` string the frame materialises
    (`lddw ptr` + `mov len`) - mechanically checked against the handler name;
  * every other (ptr,len) string constant the frame builds: Anchor account names,
    seed prefixes, panic messages;
  * the frame's own runtime syscalls with their call sites (`.rel.dyn` -> `.dynsym`);
  * its direct callees with the syscalls and strings *they* own, kept in a separate
    column so nothing is claimed about a helper's frame from the handler's;
  * custom-error raise stores in the frame (6000..6110), the in-frame part of the
    program's error surface;
  * cross-program instruction discriminators materialised in the frame.

Usage:
  handler_anatomy.py PROG            # PROG in {pump,pump_amm,pump_fees,mayhem}
  handler_anatomy.py --all --out maps/
"""
import hashlib
import json
import os
import re
import struct
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sbftool import Prog  # noqa: E402

ROOT = os.environ.get('PUMPFUN_EVIDENCE')
PROGS = ('pump', 'pump_amm', 'pump_fees', 'mayhem')
HANDLER_MAPS = {'pump': 'maps/handlers.json', 'pump_amm': 'maps/amm_handlers_full.json',
                'pump_fees': 'maps/fees_handlers.json'}
ERR_LO, ERR_HI = 6000, 6110
B58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


# ---------------------------------------------------------------- ELF
def reloc_syms(p):
    """call-site pc -> dynsym name for every unapplied R_BPF_64_32 call relocation."""
    rel = p.sec.get('.rel.dyn') or p.sec.get('.rela.dyn')
    ds, dstr = p.sec.get('.dynsym'), p.sec.get('.dynstr')
    if not rel or not ds or not dstr:
        return {}
    ent = 24 if '.rela.dyn' in p.sec else 16
    names = []
    off, size, base = ds[4], ds[5], dstr[4]
    for k in range(size // 24):
        stn = struct.unpack_from('<I', p.b, off + k * 24)[0]
        names.append(p.b[base + stn:p.b.index(b'\0', base + stn)].decode('latin1'))
    out = {}
    for k in range(rel[5] // ent):
        roff, info = struct.unpack_from('<QQ', p.b, rel[4] + k * ent)
        if info & 0xffffffff != 10:
            continue
        symi = info >> 32
        if symi < len(names) and names[symi]:
            out[roff // 8] = names[symi]
    return out


def function_starts(p, relsyms):
    """Function starts = resolved call targets + ELF entry, never a relocated call site."""
    starts = {p.base}
    for pc, ins in p.ins.items():
        if ins.op != 0x85 or pc in relsyms:
            continue
        tgt = pc + 1 + ins.imm
        if tgt in p.ins:
            starts.add(tgt)
    entry = struct.unpack_from('<Q', p.b, 0x18)[0] // 8
    if entry in p.ins:
        starts.add(entry)
    return sorted(starts)


def naive_starts(p):
    """sbftool-style starts (every relative call target, relocation slots included)."""
    starts = {p.base}
    for pc, ins in p.ins.items():
        if ins.op == 0x85 and pc + 1 + ins.imm in p.ins:
            starts.add(pc + 1 + ins.imm)
    return sorted(starts)


def frame_of(p, starts, func_of, pc):
    """(start, end, insns) of the frame holding pc."""
    s = func_of.get(pc)
    if s is None:
        s = max([x for x in starts if x <= pc] or [starts[0]])
    nxt = [x for x in starts if x > s]
    end = nxt[0] if nxt else max(p.order) + 1
    return s, end, [p.ins[x] for x in range(s, end) if x in p.ins]


def seg_reader(p):
    segs = []
    for name, s in p.secs:
        if s[2] & 0x2 and s[5]:
            segs.append((s[3], s[3] + s[5], s[4]))

    def read(va, n):
        for lo, hi, off in segs:
            if lo <= va < hi:
                k = min(n, hi - va)
                return p.b[off + (va - lo):off + (va - lo) + k]
        return b''
    return read


# ---------------------------------------------------------------- constants
def disc_table(repo):
    """disc hex -> [(program, kind, name)] from the repo's instruction maps."""
    tab = defaultdict(list)
    for prog, rel in (('pump', 'maps/handlers.json'), ('pump_amm', 'maps/amm_handlers_full.json'),
                      ('pump_fees', 'maps/fees_handlers.json')):
        path = os.path.join(repo, rel)
        if not os.path.exists(path):
            continue
        for name, rec in json.load(open(path)).items():
            if isinstance(rec, dict):
                disc = rec.get('discriminator') or rec.get('disc')
                if disc:
                    tab[disc.lower()].append((prog, 'instruction', name))
    path = os.path.join(repo, 'docs/mayhem_map.md')
    if os.path.exists(path):
        for line in open(path):
            m = re.match(r'\|\s*\d+\s*\|\s*`([a-z0-9_]+)`\s*\|(.*)', line)
            if not m:
                continue
            for c in [x.strip().strip('`') for x in m.group(2).split('|')]:
                if re.fullmatch(r'[0-9a-f]{16}', c):
                    tab[c].append(('mayhem', 'instruction', m.group(1)))
                    break
    return tab


def expected_disc(name):
    return hashlib.sha256(('global:' + name).encode()).digest()[:8].hex()


classify = [(re.compile(r'^Instruction: [A-Z][A-Za-z0-9]*$'), 'identity'),
            (re.compile(r'^[a-z][a-z0-9_]{2,40}$'), 'identifier'),
            (re.compile(r'^[A-Z][A-Za-z0-9]{2,40}$'), 'camel')]


def kind_of(text):
    for rx, k in classify:
        if rx.match(text):
            return k
    return 'message'


def pascal(s):
    return ''.join(w.capitalize() for w in s.split('_'))


# ---------------------------------------------------------------- frame analysis
def frame_facts(p, body, read, relsyms, discs):
    syscalls, strings, raises, disc_hits, imms = [], [], [], [], []
    for i, ins in enumerate(body):
        if ins.op == 0x85 and ins.pc in relsyms:
            syscalls.append({'pc': hex(ins.pc), 'symbol': relsyms[ins.pc]})
        if ins.op == 0x18:
            va = ins.imm & 0xffffffffffffffff
            imms.append(hex(va))
            key = va.to_bytes(8, 'little').hex()
            if key in discs:
                for dprog, kind, dname in discs[key]:
                    disc_hits.append({'pc': hex(ins.pc), 'disc': key, 'program': dprog,
                                      'kind': kind, 'name': dname})
            nxt = body[i + 1] if i + 1 < len(body) else None
            if nxt is not None and nxt.op == 0xb7 and 0 < nxt.imm <= 96:
                raw = read(va, nxt.imm)
                if raw and all(32 <= c < 127 for c in raw):
                    txt = raw.decode('latin1')
                    strings.append({'pc': hex(ins.pc), 'len': nxt.imm, 'text': txt,
                                    'kind': kind_of(txt), 'va': hex(va)})
        if ins.op in (0x62, 0x6a, 0x72, 0x7a) and ins.dst == 10:
            if ERR_LO <= (ins.imm & 0xffffffff) <= ERR_HI:
                raises.append({'pc': hex(ins.pc), 'code': ins.imm & 0xffffffff})
    return syscalls, strings, raises, disc_hits


def raise_sites(p):
    """custom-range (6000..6110) immediate stores to the frame."""
    out = []
    for pc, ins in p.ins.items():
        if ins.op in (0x62, 0x6a, 0x72, 0x7a) and ins.dst == 10:
            if ERR_LO <= (ins.imm & 0xffffffff) <= ERR_HI:
                out.append((pc, ins.imm & 0xffffffff))
    return sorted(out)


def raise_attribution(p, func_of, relsyms, handler_frames):
    """raise stores split by frame ownership: handler frame / direct callee / deeper."""
    rev = defaultdict(set)
    for pc, ins in p.ins.items():
        if ins.op == 0x85 and pc not in relsyms and pc + 1 + ins.imm in p.ins:
            rev[func_of.get(pc + 1 + ins.imm)].add(func_of.get(pc))
    sites = raise_sites(p)
    own = [pc for pc, _c in sites if func_of.get(pc) in handler_frames]
    d1 = [pc for pc, _c in sites if func_of.get(pc) not in handler_frames
          and rev.get(func_of.get(pc), set()) & handler_frames]
    deep = [pc for pc, _c in sites if pc not in own and pc not in d1]
    return {'total': len(sites), 'handler_frame': len(own), 'direct_callee': len(d1),
            'deeper': len(deep),
            'frames_holding_raises': len({func_of.get(pc) for pc, _c in sites}),
            'codes': sorted({c for _pc, c in sites})}


def load_handlers(prog, repo):
    if prog == 'mayhem':
        out = {}
        path = os.path.join(repo, 'docs/mayhem_map.md')
        if not os.path.exists(path):
            return out
        for line in open(path):
            m = re.match(r'\|\s*\d+\s*\|\s*`([a-z0-9_]+)`\s*\|(.*)', line)
            if not m:
                continue
            cols = [c.strip() for c in m.group(2).split('|')]
            if len(cols) >= 6 and cols[5].startswith('0x'):
                out[m.group(1)] = int(cols[5], 16)
        return out
    path = os.path.join(repo, HANDLER_MAPS.get(prog, ''))
    if not path or not os.path.exists(path):
        return {}
    out = {}
    for name, rec in json.load(open(path)).items():
        if isinstance(rec, str):
            out[name] = int(rec, 16)
        elif isinstance(rec, dict):
            v = rec.get('handler_pc') or rec.get('handler')
            if v:
                out[name] = int(v, 16)
    return out


def sha256(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def build(prog, repo='.', with_prog=False):
    root = ROOT or os.path.join(repo, 'evidence', 'original')
    so = os.path.join(root, prog, 'deployed.so')
    p = Prog(so)
    relsyms = reloc_syms(p)
    starts = function_starts(p, relsyms)
    naive = naive_starts(p)
    func_of = {}
    for a, b in zip(starts, starts[1:] + [max(p.order) + 1]):
        for pc in range(a, b):
            if pc in p.ins:
                func_of[pc] = a
    read = seg_reader(p)
    discs = disc_table(repo)
    handlers = load_handlers(prog, repo)

    rec = {'program': prog, 'binary': os.path.basename(so), 'sha256': sha256(so),
           'frames': len(starts), 'frames_naive': len(naive),
           'spurious_starts': len(set(naive) - set(starts)),
           'syscall_census': dict(Counter(relsyms.values())),
           'handlers': {}}
    own_attr = Counter()
    identity_ok = identity_bad = identity_missing = 0
    for name, hpc in sorted(handlers.items()):
        s, end, body = frame_of(p, starts, func_of, hpc)
        syscalls, strings, raises, dhits = frame_facts(p, body, read, relsyms, discs)
        for sc in syscalls:
            own_attr[sc['symbol']] += 1
        ident = [x['text'] for x in strings if x['kind'] == 'identity']
        want = 'Instruction: ' + pascal(name)
        if ident:
            if want in ident:
                identity_ok += 1
            else:
                identity_bad += 1
        else:
            identity_missing += 1
        callees, seen = [], set()
        for ins in body:
            if ins.op != 0x85 or ins.pc in relsyms:
                continue
            tgt = ins.pc + 1 + ins.imm
            if tgt not in p.ins:
                continue
            cs, cend, cbody = frame_of(p, starts, func_of, tgt)
            if cs in seen:
                continue
            seen.add(cs)
            csys, cstr, craises, cdh = frame_facts(p, cbody, read, relsyms, discs)
            callees.append({'callsite': hex(ins.pc), 'callee': hex(cs), 'insns': len(cbody),
                            'syscalls': sorted({x['symbol'] for x in csys}),
                            'strings': [x['text'] for x in cstr
                                        if x['kind'] in ('identity', 'identifier')][:6],
                            'raise_stores': len(craises),
                            'disc_hits': [f"{x['program']}/{x['name']}" for x in cdh]})
        rec['handlers'][name] = {
            'handler_pc': hex(hpc), 'body': hex(s), 'body_end': hex(end), 'insns': len(body),
            'identity_string_expected': want,
            'identity_string_found': ident,
            'identity_ok': bool(ident) and want in ident,
            'expected_disc': expected_disc(name),
            'own_syscalls': syscalls,
            'own_strings': strings,
            'own_raise_stores': raises,
            'own_disc_hits': dhits,
            'own_immediates': imms_count(body),
            'callees': callees,
        }
    rec['identity'] = {'ok': identity_ok, 'mismatch': identity_bad, 'missing': identity_missing}
    rec['syscall_own_frame'] = dict(own_attr)
    rec['syscall_shared'] = {k: v - own_attr.get(k, 0) for k, v in rec['syscall_census'].items()
                             if v - own_attr.get(k, 0) > 0}
    handler_frames = {rec['handlers'][n]['body'] and int(rec['handlers'][n]['body'], 16)
                      for n in rec['handlers']}
    rec['raise_attribution'] = raise_attribution(p, func_of, relsyms, handler_frames)
    rec['callee_raise_stores'] = sum(len(h['own_raise_stores']) for h in rec['handlers'].values())
    # shared behavioural core: which helper frames the handlers have in common
    share = defaultdict(list)
    for name, h in rec['handlers'].items():
        for c in h['callees']:
            share[c['callee']].append(name)
    helpers = []
    for callee, names in sorted(share.items(), key=lambda kv: -len(kv[1])):
        c = next(x for n in (rec['handlers'][names[0]],) for x in n['callees'] if x['callee'] == callee)
        helpers.append({'callee': callee, 'insns': c['insns'], 'syscalls': c['syscalls'],
                        'raise_stores': c['raise_stores'], 'strings': c['strings'],
                        'handlers': len(names), 'sample': sorted(names)[:4]})
    rec['shared_helpers'] = helpers[:20]
    # single-site syscalls: the program's funnel points
    funnels = []
    for sym, n in rec['syscall_census'].items():
        if n != 1:
            continue
        site = [k for k in relsyms if relsyms[k] == sym][0]
        owner = func_of.get(site)
        funnels.append({'symbol': sym, 'site': hex(site), 'frame': hex(owner),
                        'frame_insns': len(frame_of(p, starts, func_of, site)[2]),
                        'handlers': len(share.get(hex(owner), []))})
    rec['funnels'] = sorted(funnels, key=lambda x: x['symbol'])
    return (rec, p) if with_prog else rec


def imms_count(body):
    return sum(1 for ins in body if ins.op == 0x18)


def md(rec):
    L = []
    h = rec['handlers']
    tot_ins = sum(x['insns'] for x in h.values())
    L.append(f"## {rec['program']}")
    L.append('')
    L.append(f"- binary `{rec['binary']}`, sha256 `{rec['sha256']}`")
    L.append(f"- handler bodies recovered: **{len(h)}**, "
             f"{tot_ins} instructions, median {sorted(x['insns'] for x in h.values())[len(h)//2]} "
             f"insns/body (min {min(x['insns'] for x in h.values())}, "
             f"max {max(x['insns'] for x in h.values())})")
    L.append(f"- frames: {rec['frames']} relocation-aware vs {rec['frames_naive']} naive "
             f"({rec['spurious_starts']} call sites that a naive start scan turns into "
             f"bogus function entries)")
    L.append(f"- identity strings: {rec['identity']['ok']}/{len(h)} recovered and matching "
             f"`Instruction: <PascalCase(name)>`"
             + (f", {rec['identity']['mismatch']} mismatched" if rec['identity']['mismatch'] else '')
             + (f", {rec['identity']['missing']} absent" if rec['identity']['missing'] else ''))
    L.append('')
    L.append('| syscall | sites | in a handler frame | in a shared helper |')
    L.append('|---|---:|---:|---:|')
    for sym, n in sorted(rec['syscall_census'].items(), key=lambda kv: -kv[1]):
        L.append(f"| `{sym}` | {n} | {rec['syscall_own_frame'].get(sym, 0)} | "
                 f"{rec['syscall_shared'].get(sym, 0)} |")
    L.append('')
    ra = rec['raise_attribution']
    L.append(f"- custom-error raise stores: {ra['total']} in {ra['frames_holding_raises']} frames "
             f"({ra['handler_frame']} in a handler frame, {ra['direct_callee']} in a direct callee "
             f"frame, {ra['deeper']} deeper), {len(ra['codes'])} distinct codes")
    L.append('')
    return '\n'.join(L)


def table(rec):
    L = ['| handler | body | insns | own syscalls | callee frames (insns: syscalls, raises) | strings in frame |',
         '|---|---|---:|---|---|---|']
    for name, h in rec['handlers'].items():
        sc = ', '.join(f"`{x['symbol']}`@{x['pc']}" for x in h['own_syscalls']) or '-'
        cal = '; '.join(f"{c['callee']} ({c['insns']}: "
                        + (','.join(c['syscalls']) or '-')
                        + (f", {c['raise_stores']}r" if c['raise_stores'] else '') + ')'
                        for c in h['callees'][:5]) or '-'
        if len(h['callees']) > 5:
            cal += f' +{len(h["callees"]) - 5}'
        st = ', '.join(f"`{x['text']}`" for x in h['own_strings'] if x['kind'] != 'identity')[:130] or '-'
        L.append(f"| `{name}` | {h['body']}..{h['body_end']} | {h['insns']} | {sc} | {cal} | {st} |")
    L.append('')
    return '\n'.join(L)


def verify(rec, p, repo='.'):
    """Cross-checks against the previously published error-site catalog and the ELF."""
    lines = []
    path = os.path.join(repo, f"maps/{rec['program']}_error_sites_full.json")
    if os.path.exists(path):
        pub = json.load(open(path))
        n_sites = len(pub['sites'])
        codes = sorted({s['code'] for s in pub['sites']})
        ra = rec['raise_attribution']
        ok = (n_sites == ra['total'] and codes == ra['codes']
              and pub['functions'] == rec['frames']
              and pub['sha256'] == rec['sha256'])
        lines.append(f"{'PASS' if ok else 'FAIL'} {rec['program']}: raise stores "
                     f"{ra['total']}/{n_sites}, codes {len(ra['codes'])}/{len(codes)}, "
                     f"frames {rec['frames']}/{pub['functions']}, sha256 match "
                     f"{pub['sha256'] == rec['sha256']}")
    n = len(rec['handlers'])
    idok = rec['identity']['ok'] == n and rec['identity']['mismatch'] == 0
    lines.append(f"{'PASS' if idok else 'FAIL'} {rec['program']}: identity strings "
                 f"{rec['identity']['ok']}/{n}")
    ok = True
    for h in rec['handlers'].values():
        a, b = int(h['body'], 16), int(h['body_end'], 16)
        have = sum(1 for pc in range(a, b) if pc in p.ins)
        if b <= a or have != h['insns']:
            ok = False
    starts = [int(h['body'], 16) for h in rec['handlers'].values()]
    ok = ok and len(starts) == len(set(starts))
    lines.append(f"{'PASS' if ok else 'FAIL'} {rec['program']}: body extents non-empty, "
                 f"instruction counts exact, one body per handler")
    census = sum(rec['syscall_census'].values())
    lines.append(f"INFO {rec['program']}: {census} relocated call sites over "
                 f"{len(rec['syscall_census'])} distinct syscall symbols")
    return lines


def main():
    args = sys.argv[1:]
    outdir = None
    if '--out' in args:
        i = args.index('--out')
        outdir = args[i + 1]
        del args[i:i + 2]
    do_verify = '--verify' in args
    if do_verify:
        args.remove('--verify')
    progs = PROGS if (not args or args[0] == '--all') else [args[0]]
    for prog in progs:
        rec, p = build(prog, with_prog=True)
        if outdir:
            os.makedirs(outdir, exist_ok=True)
            with open(os.path.join(outdir, f'{prog}_handler_anatomy.json'), 'w') as fh:
                json.dump(rec, fh, indent=1, sort_keys=True)
        if do_verify:
            print('\n'.join(verify(rec, p)))
            continue
        print(md(rec))
        print(table(rec))


if __name__ == '__main__':
    main()
