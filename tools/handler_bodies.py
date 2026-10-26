#!/usr/bin/env python3
"""handler_bodies.py - real per-handler body recovery for sBPF (v1) Solana programs.

Why this exists
---------------
sbftool.py recovers "functions" as the linear span between call targets. On the
*deployed* binaries every syscall call site carries an unapplied `R_BPF_64_32`
relocation (imm = -1 on disk, patched by the loader), so `pc + 1 + imm == pc`:
each syscall call site becomes a bogus function start and truncates the
enclosing function to its prologue. Result (before this tool): every pump
handler reported `func_insns: 5..7`, `relative_callees: 0`, `syscalls: {}`,
`has_cpi: false` even for `buy_v2`/`create_v2`.

This tool instead:
  1. parses `.rel.dyn` and resolves every call site to its syscall symbol
     (R_BPF_64_32) and every lddw to its target (R_BPF_64_RELATIVE);
  2. builds function entries only from *internal* call targets (callees both
     forward and backward) plus the ELF entrypoint/custom_panic symbols;
  3. recovers each function body by recursive descent (fallthrough + jump
     targets, `ja` follows only its target, `exit` ends a branch), calls stay
     opaque and are attributed separately;
  4. reports per handler: body insns, direct callees, syscall histogram with
     cited call sites, transitive reachability (depth-limited) of a watched
     helper/CPI wrapper, and the shortest call chain.

Scope: RE / behavioural structure only - no vulnerability analysis.

Usage:
  handler_bodies.py stats   PROG.so
  handler_bodies.py body    PROG.so PC [--calls]
  handler_bodies.py reach   PROG.so ROOT_PC TARGET_PC
  handler_bodies.py handlers PROG.so MAPS_JSON OUT_JSON
  handler_bodies.py relocs  PROG.so
"""
import json
import os
import struct
import sys
from collections import Counter, deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sbftool import Prog  # noqa: E402

R_BPF_64_RELATIVE = 8
R_BPF_64_32 = 10      # call site -> dynsym index (syscall / internal symbol)


class RelProg(Prog):
    """Prog with the call graph built from *internal* call targets.

    sbftool.Prog now resolves .rel.dyn itself (call_sym / data_ptr); this subclass
    adds CFG-based body recovery and a transitive call graph on top of it."""

    def __init__(self, path):
        super().__init__(path)


    # ---- call graph -----------------------------------------------------
    def call_entries(self):
        """Internal call targets only: syscall sites never create an entry."""
        st = {self.base}
        for pc, ins in self.ins.items():
            if ins.op == 0x85:
                if pc in self.call_sym:      # syscall call site -> not a function
                    continue
                tgt = pc + 1 + ins.imm
                if tgt in self.ins and tgt != pc:
                    st.add(tgt)
        for name, val in getattr(self, 'dynsym', []):
            if val and name in ('entrypoint', 'custom_panic'):
                if val // 8 in self.ins:
                    st.add(val // 8)
        return sorted(st)

    def body(self, entry, limit_entry_cross=None):
        """Recursive descent from `entry`. Calls are opaque (not traversed).

        limit_entry_cross: when True (default set by load()), a fallthrough that
        would land exactly on another known function entry ends that path instead
        of leaking into the next function's linear code.

        Returns (insns list in pc order, call sites list, back edges count)."""
        if entry not in self.ins:
            return [], [], 0
        if limit_entry_cross is None:
            limit_entry_cross = getattr(self, 'strict_bounds', True)
        seen = {}
        work = deque([entry])
        calls = []
        backedges = 0
        hi = self.base + len(self.order)
        while work:
            pc = work.popleft()
            while True:
                if pc in seen or pc not in self.ins or pc >= hi:
                    break
                if pc != entry and limit_entry_cross and pc in self.entries_set:
                    break                            # crossed into another function
                seen[pc] = True
                ins = self.ins[pc]
                op = ins.op
                if op == 0x95:                       # exit
                    break
                if op == 0x85:                       # call: opaque
                    if pc not in self.call_sym:
                        tgt = pc + 1 + ins.imm
                        if tgt in self.ins and tgt != pc:
                            calls.append(pc)
                    nxt = pc + 1
                    if nxt in seen:
                        backedges += 1
                    pc = nxt
                    continue
                if op == 0x05:                       # ja: target only
                    tgt = pc + 1 + ins.off
                    if tgt <= pc:
                        backedges += 1
                    if tgt in self.ins and tgt not in seen:
                        work.append(tgt)
                    break
                if op in (0x15, 0x1d, 0x25, 0x2d, 0x35, 0x3d, 0x45, 0x4d, 0x55, 0x5d,
                          0x65, 0x6d, 0x75, 0x7d, 0xa5, 0xad, 0xb5, 0xbd, 0xc5, 0xcd,
                          0xd5, 0xdd):
                    tgt = pc + 1 + ins.off
                    if tgt <= pc:
                        backedges += 1
                    if tgt in self.ins and tgt not in seen:
                        work.append(tgt)
                    pc += 1
                    continue
                pc += 2 if ins.wide else 1          # lddw occupies two slots
        return [self.ins[p] for p in sorted(seen)], calls, backedges

    def callees(self, entry):
        """Direct internal callees of a function body (cached)."""
        if entry in self._callee_cache:
            return self._callee_cache[entry]
        _, calls, _ = self.body(entry)
        out = []
        for pc in calls:
            tgt = pc + 1 + self.ins[pc].imm
            if tgt in self.ins:
                out.append((pc, tgt))
        self._callee_cache[entry] = out
        return out

    def syscalls(self, entry):
        """Direct syscalls in a body: name -> [call site pcs]."""
        body, _, _ = self.body(entry)
        h = {}
        for ins in body:
            if ins.op == 0x85:
                nm = self.call_sym.get(ins.pc)
                if nm:
                    h.setdefault(nm, []).append(ins.pc)
        return h

    def reach(self, root, targets, max_depth=6, max_nodes=4000):
        """BFS over the internal call graph from root. Returns
        {target: (depth, chain[list of pcs])} and the visited node set."""
        if isinstance(targets, int):
            targets = {targets}
        targets = set(targets)
        start = root if root in self.entries_set else self.func_start_internal(root)
        seen = {start: (0, [start])}
        q = deque([start])
        found = {}
        nodes = 0
        while q:
            cur = q.popleft()
            depth, chain = seen[cur]
            if cur in targets:
                found.setdefault(cur, (depth, chain))
            if depth >= max_depth or nodes >= max_nodes:
                continue
            nodes += 1
            for _, tgt in self.callees(cur):
                if tgt not in seen:
                    seen[tgt] = (depth + 1, chain + [tgt])
                    q.append(tgt)
                if tgt in targets and tgt not in found:
                    found[tgt] = (depth + 1, chain + [tgt])
        return found, set(seen)

    entries_set = set()
    _callee_cache = {}

    def func_start_internal(self, pc):
        s = [x for x in self.entries if x <= pc]
        return s[-1] if s else self.base

    def transitive_syscalls(self, entry, max_depth=6):
        """Union of direct syscalls over the internal call closure of `entry`.
        Returns {syscall: [node_pc where it appears, ...]}."""
        found, visited = self.reach(entry, set(), max_depth=max_depth)
        out = {}
        for node in sorted(visited):
            for nm, sites in self.syscalls(node).items():
                out.setdefault(nm, [])
                for s in sites:
                    if s not in out[nm]:
                        out[nm].append(s)
        return out


def load(path):
    p = RelProg(path)
    p.entries = p.call_entries()
    p.entries_set = set(p.entries)
    return p


def fmt_sites(pcs, n=6):
    s = ' '.join(hex(x) for x in pcs[:n])
    return s + (' ...' if len(pcs) > n else '')


def cmd_stats(p):
    print('text=%#x insns=%d linear_starts=%d real_entries=%d syscall_sites=%d data_lddw=%d' % (
        p.tsize, len(p.order), len(p.starts), len(p.entries), len(p.call_sym), len(p.data_ptr)))
    hist = Counter()
    for pc, nm in p.call_sym.items():
        hist[nm] += 1
    for nm, c in hist.most_common():
        print('  %-28s %d' % (nm, c))


def cmd_relocs(p):
    for pc in sorted(p.call_sym):
        ins = p.ins.get(pc)
        print('%8x (va %#x) %-28s %r' % (pc, pc * 8, p.call_sym[pc], ins))


def cmd_body(p, pc, show_calls=False):
    start = pc if pc in p.entries_set else p.func_start_internal(pc)
    body, calls, back = p.body(start)
    sysc = p.syscalls(start)
    print('; body @ %#x  insns=%d  calls=%d  backedges=%d  entry=%s' % (
        start, len(body), len(calls), back, start in p.entries_set))
    print('; syscalls: ' + (', '.join('%s×%d@%s' % (k, len(v), fmt_sites(v))
                                      for k, v in sorted(sysc.items())) or 'none'))
    cl = p.callees(start)
    print('; callees: ' + (', '.join('%#x<-%#x' % (t, c) for c, t in cl[:40]) or 'none'))
    if show_calls:
        for ins in body:
            if ins.op == 0x85:
                nm = p.call_sym.get(ins.pc)
                tgt = ins.pc + 1 + ins.imm
                print('%8x: call %s' % (ins.pc, nm if nm else '%#x' % tgt))


def cmd_reach(p, root, target):
    found, visited = p.reach(root, target)
    print('root=%#x target=%#x reachable=%s graph_nodes=%d' % (
        root, target, bool(found), len(visited)))
    for t, (d, chain) in found.items():
        print('  chain depth %d: %s' % (d, ' -> '.join('%#x' % x for x in chain)))


def cmd_handlers(p, maps_json, out_json, watch=()):
    """Per-handler body metrics. `watch` = pcs whose transitive reachability is
    reported per handler (e.g. the Token-2022 transfer-fee helper, the CPI wrapper)."""
    with open(maps_json) as f:
        handlers = json.load(f)
    rows = []
    for name, meta in sorted(handlers.items()):
        hp = int(meta['handler_pc'], 16) if isinstance(meta.get('handler_pc'), str) else meta['handler_pc']
        start = hp if hp in p.entries_set else p.func_start_internal(hp)
        body, calls, back = p.body(start)
        sysc = p.syscalls(start)
        cl = p.callees(start)
        tsys = p.transitive_syscalls(start)
        wfound, visited = p.reach(start, set(watch))
        rows.append({
            'name': name,
            'handler_pc': hex(hp),
            'body_pc': hex(start),
            'body_insns': len(body),
            'direct_callees': len(cl),
            'callgraph_nodes': len(visited),
            'backedges': back,
            'syscalls': {k: [hex(x) for x in v] for k, v in sorted(sysc.items())},
            'syscall_sites_total': sum(len(v) for v in sysc.values()),
            'syscalls_transitive': {k: [hex(x) for x in v] for k, v in sorted(tsys.items())},
            'has_cpi': 'sol_invoke_signed_rust' in tsys,
            'has_log': 'sol_log_' in tsys or 'sol_log_data' in tsys,
            'watch_reach': {hex(t): {'depth': d, 'chain': [hex(x) for x in chain]}
                            for t, (d, chain) in sorted(wfound.items())},
        })
    with open(out_json, 'w') as f:
        json.dump({'source_elf': os.path.basename(os.path.dirname(out_json)),
                   'handler_map': os.path.basename(maps_json),
                   'watch_pcs': [hex(w) for w in watch],
                   'handlers': rows,
                   'note': 'body metrics = recursive-descent CFG from handler entry (handler_bodies.py); '
                           'calls opaque; syscalls_transitive = union over internal call closure (depth<=6)'},
                  f, indent=1)
    wt = ' '.join('%-10s' % ('@' + hex(w)[2:]) for w in watch)
    print('%-34s %8s %6s %6s %5s %5s %4s %s' % (
        'handler', 'body_pc', 'insns', 'clls', 'nodes', 'cpi', 'sysc', wt))
    for r in rows:
        wr = ' '.join('%-10s' % ('R' if hex(w) in r['watch_reach'] else '.') for w in watch)
        print('%-34s %8s %6d %6d %5d %5s %4d %s' % (
            r['name'], r['body_pc'], r['body_insns'], r['direct_callees'],
            r['callgraph_nodes'], 'yes' if r['has_cpi'] else '-',
            r['syscall_sites_total'], wr))


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    cmd, path = sys.argv[1], sys.argv[2]
    p = load(path)
    if cmd == 'stats':
        cmd_stats(p)
    elif cmd == 'relocs':
        cmd_relocs(p)
    elif cmd == 'body':
        pc = int(sys.argv[3], 0)
        if pc > len(p.order) * 8:
            pc //= 8
        cmd_body(p, pc, '--calls' in sys.argv)
    elif cmd == 'reach':
        cmd_reach(p, int(sys.argv[3], 0), int(sys.argv[4], 0))
    elif cmd == 'handlers':
        watch = tuple(int(x, 0) for x in sys.argv[5].split(',')) if len(sys.argv) > 5 else ()
        cmd_handlers(p, sys.argv[3], sys.argv[4], watch)
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
