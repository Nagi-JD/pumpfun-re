#!/usr/bin/env python3
"""report_anatomy - the summary blocks of docs/handler_anatomy_all4.md, reproducible.

  * per-program census (handlers, body sizes, frame counts, identity check);
  * the single-site syscall wrappers of each program (site, frame, frame size);
  * cross-program instruction-shape comparison of those wrappers;
  * the shared helper frames ranked by how many handlers call them.

Reads maps/<prog>_handler_anatomy.json (produced by handler_anatomy.py) and the
deployed binaries for the instruction-shape comparison.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import handler_anatomy as A  # noqa: E402

WRAPPERS = ('sol_invoke_signed_rust', 'sol_log_data', 'sol_set_return_data',
            'sol_get_return_data', 'sol_create_program_address',
            'sol_try_find_program_address', 'sol_sha256', 'sol_get_clock_sysvar',
            'sol_get_rent_sysvar', 'sol_memcmp_', 'sol_memmove_', 'sol_memset_',
            'sol_memcpy_', 'sol_log_pubkey', 'sol_panic_', 'custom_panic', 'abort')


def insn_words(p, frame, n):
    out = []
    for pc in range(frame, frame + n):
        ins = p.ins.get(pc)
        if ins is None:
            out.append(None)
            continue
        # immediate of a relocated call slot is patched by the loader: compare shape only
        out.append((ins.op, ins.dst, ins.src, 0 if ins.op == 0x85 else ins.off))
    return out


def main():
    root = A.ROOT or os.path.join('evidence', 'original')
    recs = {prog: json.load(open(f'maps/{prog}_handler_anatomy.json')) for prog in A.PROGS}
    for prog in A.PROGS:
        d = recs[prog]
        sizes = sorted(h['insns'] for h in d['handlers'].values())
        print(f'## {prog}: {len(d["handlers"])} handlers, {sum(sizes)} instructions, '
              f'median {sizes[len(sizes) // 2]}, min {sizes[0]}, max {sizes[-1]}')
        print(f'   frames {d["frames"]} (naive {d["frames_naive"]}), '
              f'identity {d["identity"]}')
        ra = d['raise_attribution']
        print(f'   raises {ra["total"]} in {ra["frames_holding_raises"]} frames '
              f'(handler {ra["handler_frame"]}, direct callee {ra["direct_callee"]}, '
              f'deeper {ra["deeper"]}), {len(ra["codes"])} codes')
        print('   single-site wrappers:')
        for f in d['funnels']:
            print(f'     {f["symbol"]:30s} site {f["site"]:>9s}  frame {f["frame"]:>8s}  '
                  f'{f["frame_insns"]:>4d} insns')
        print('   top shared helpers (handlers calling the frame directly):')
        for h in d['shared_helpers'][:8]:
            print(f'     {h["callee"]:>9s} {h["insns"]:>5d} insns  handlers={h["handlers"]:>3d}  '
                  f'syscalls={",".join(h["syscalls"]) or "-"}  raises={h["raise_stores"]}  '
                  f'strings={",".join(h["strings"][:4]) or "-"}')
        print()

    progs = {prog: A.Prog(os.path.join(root, prog, 'deployed.so')) for prog in A.PROGS}
    print('## cross-program instruction-shape comparison (pump as reference)')
    for sym in WRAPPERS:
        ref = [x for x in recs['pump']['funnels'] if x['symbol'] == sym]
        if not ref:
            continue
        ref = ref[0]
        rw = insn_words(progs['pump'], int(ref['frame'], 16), ref['frame_insns'])
        out = []
        for prog in ('pump_amm', 'pump_fees', 'mayhem'):
            f = [x for x in recs[prog]['funnels'] if x['symbol'] == sym]
            if not f:
                out.append(f'{prog}: absent')
                continue
            f = f[0]
            w = insn_words(progs[prog], int(f['frame'], 16), f['frame_insns'])
            same = len(rw) == len(w) and all(a == b for a, b in zip(rw, w))
            out.append(f'{prog}: ' + ('identical shape' if same
                                      else f'{len(w)} insns, '
                                           f'{sum(1 for a, b in zip(rw, w) if a != b)} differ'))
        print(f'  {sym:30s} pump {len(rw):>3d} insns | ' + ' | '.join(out))


if __name__ == '__main__':
    main()
