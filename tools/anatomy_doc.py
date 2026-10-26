#!/usr/bin/env python3
"""anatomy_doc - writes docs/handler_anatomy_all4.md from maps/<prog>_handler_anatomy.json.

Run after `handler_anatomy.py --all --out maps/`:
    python3 tools/anatomy_doc.py > docs/handler_anatomy_all4.md
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import handler_anatomy as A  # noqa: E402

PROGS = A.PROGS
TITLES = {'pump': 'pump (`6EF8…F6P`)', 'pump_amm': 'pump_amm / PumpSwap (`pAMM…XEA`)',
          'pump_fees': 'pump_fees (`pfee…ojVZ`)', 'mayhem': 'mayhem (`MAyh…MD4e`)'}


def load(prog):
    return json.load(open(f'maps/{prog}_handler_anatomy.json'))


def row(name, h, callee_cap=3, string_cap=3):
    own = ', '.join(f"`{x['symbol']}`@{x['pc']}" for x in h['own_syscalls']) or '-'
    cal = '; '.join(f"{c['callee']} ({c['insns']}i"
                    + (f", {c['raise_stores']}r" if c['raise_stores'] else '')
                    + (f", {','.join(c['syscalls'])}" if c['syscalls'] else '') + ')'
                    for c in h['callees'][:callee_cap])
    if len(h['callees']) > callee_cap:
        cal += f' +{len(h["callees"]) - callee_cap}'
    strs = ', '.join(f"`{x['text']}`" for x in h['own_strings'] if x['kind'] != 'identity')
    if string_cap and strs.count('`') // 2 > string_cap:
        strs = ', '.join(f"`{x['text']}`" for x in
                         [y for y in h['own_strings'] if y['kind'] != 'identity'][:string_cap]) + ' …'
    return (f"| `{name}` | {h['body']} | {h['insns']} | {own} | {cal or '-'} | "
            f"{strs or '-'} |")


def table(d, callee_cap=3, string_cap=3):
    L = ['| handler | body | insns | own syscalls | direct callees (insns, raises, syscalls) | frame strings |',
         '|---|---|---:|---|---|---|']
    for name, h in d['handlers'].items():
        L.append(row(name, h, callee_cap, string_cap))
    return '\n'.join(L)


def census_row(prog, d):
    sizes = sorted(h['insns'] for h in d['handlers'].values())
    ra = d['raise_attribution']
    return (f"| {TITLES[prog]} | {len(d['handlers'])} | {sum(sizes)} | {sizes[len(sizes)//2]} | "
            f"{sizes[0]}–{sizes[-1]} | {d['frames']} / {d['frames_naive']} | "
            f"{d['identity']['ok']}/{len(d['handlers'])} | {ra['total']} | {len(ra['codes'])} |")


def wrapper_rows(recs):
    L = ['| syscall | pump | pump_amm | pump_fees | mayhem |', '|---|---|---|---|---|']
    syms = []
    for prog in PROGS:
        for f in recs[prog]['funnels']:
            if f['symbol'] not in syms:
                syms.append(f['symbol'])
    for sym in sorted(syms):
        cells = []
        for prog in PROGS:
            f = [x for x in recs[prog]['funnels'] if x['symbol'] == sym]
            cells.append(f"{f[0]['frame']} ({f[0]['frame_insns']}i)" if f else '—')
        L.append(f"| `{sym}` | " + ' | '.join(cells) + ' |')
    return '\n'.join(L)


def helper_rows(d, n=8):
    L = ['| helper frame | insns | handlers calling it | syscalls | raise stores | strings |',
         '|---|---:|---:|---|---:|---|']
    for h in d['shared_helpers'][:n]:
        L.append(f"| {h['callee']} | {h['insns']} | {h['handlers']} | "
                 f"{', '.join('`' + s + '`' for s in h['syscalls']) or '-'} | "
                 f"{h['raise_stores']} | {', '.join(h['strings'][:4]) or '-'} |")
    return '\n'.join(L)


def main():
    recs = {prog: load(prog) for prog in PROGS}
    total_h = sum(len(recs[p]['handlers']) for p in PROGS)
    total_i = sum(sum(h['insns'] for h in recs[p]['handlers'].values()) for p in PROGS)
    out = []
    out.append('# Per-handler anatomy of the four deployed programs\n')
    out.append(
        'Body-accurate anatomy of every instruction handler the dispatcher exposes in '
        f'`pump`, `pump_amm`, `pump_fees` and `mayhem`: **{total_h} handler bodies, '
        f'{total_i} instructions**. Every figure here is read from the deployed bytes with '
        '`tools/handler_anatomy.py`; the raw per-handler records are in '
        '`maps/<prog>_handler_anatomy.json`.\n')
    out.append('## Method\n')
    out.append(
        '1. **Frame boundaries are relocation-aware.** A `call` whose 32-bit immediate is an '
        'unapplied `R_BPF_64_32` relocation is a loader-patched call slot (every `sol_*` '
        'syscall). Treating such a slot as a call target invents a function start in the '
        'middle of the caller and truncates its body. `handler_anatomy.py` builds function '
        'starts from resolved call targets only, plus the ELF entry point. Measured effect: '
        + ', '.join(f"{p} {recs[p]['frames']} real frames vs {recs[p]['frames_naive']} naive "
                    f"({recs[p]['spurious_starts']} bogus entries)" for p in PROGS) + '.\n')
    out.append(
        '2. **Every handler body is identified by itself.** Anchor logs '
        '`Instruction: <PascalCase(name)>` from the handler frame as a `(ptr,len)` pair '
        '(`lddw ptr` + `mov len`). That string is read back from `.rodata` and compared with '
        'the dispatcher-map name, so a body is never attributed on address guesswork: '
        + ', '.join(f"{p} {recs[p]['identity']['ok']}/{len(recs[p]['handlers'])}" for p in PROGS)
        + '. The same scan collects the frame\'s other string constants (Anchor account names, '
        'seed prefixes, panic messages).\n')
    out.append(
        '3. **Frame-local syscalls, callee syscalls kept apart.** A handler\'s own runtime '
        'calls are listed with their call site; a helper\'s calls stay under the helper. '
        'Nothing is re-attributed across a call edge.\n')
    out.append(
        '4. **Custom-error raises are attributed by frame ownership**: in a handler body, in '
        'a direct callee body, or deeper. The re-derived raise-store totals reproduce the '
        'error-site catalog exactly (pump 366, pump_amm 233, pump_fees 68, mayhem 29).\n')
    out.append('## 1. Census\n')
    out.append('| program | handlers | instructions | median insns | range | frames (aware / naive) | '
               'identity match | raise stores | codes |')
    out.append('|---|---:|---:|---:|---|---:|---:|---:|---:|')
    for prog in PROGS:
        out.append(census_row(prog, recs[prog]))
    out.append('')
    out.append('## 2. Runtime surface: one wrapper per syscall\n')
    out.append(
        'Each program funnels its runtime interaction through a handful of tiny wrapper '
        'frames; every one of these syscalls has exactly **one** call site in its program. '
        'An instruction handler therefore reaches the runtime only through these wrappers.\n')
    out.append(wrapper_rows(recs))
    out.append('')
    out.append(
        'The wrappers are the same compiled code: comparing instruction shape '
        '(opcode, register bytes, offset — the loader-patched call immediates excluded), '
        '`sol_invoke_signed_rust` (121 instructions), `sol_get_return_data` (135), '
        '`sol_create_program_address` (56), `sol_try_find_program_address` (37), '
        '`sol_sha256` (20), `sol_get_clock_sysvar` (29), `sol_get_rent_sysvar` (24), '
        '`sol_memcmp_` (8), `sol_memmove_` (4), `sol_log_data` (2), `sol_log_pubkey` (2), '
        '`custom_panic` (2) are identical in `pump`, `pump_amm` and `pump_fees`. '
        '`mayhem` carries only the 2/4/8-instruction wrappers identically and differs on '
        'clock (26 vs 29), rent (21 vs 24) and invoke (125 vs 121, 116 differing slots), '
        'and has no `sol_sha256`, `sol_create_program_address`, '
        '`sol_try_find_program_address`, `sol_get_return_data` or `sol_set_return_data` '
        'site — it instead carries a `sol_panic_` wrapper (57 instructions).\n')
    for prog in PROGS:
        out.append(f'### {TITLES[prog]} — shared helper frames\n')
        out.append(helper_rows(recs[prog]))
        out.append('')
    out.append('## 3. pump_fees, handler by handler\n')
    out.append(table(recs['pump_fees'], callee_cap=4, string_cap=3))
    out.append('')
    for prog in ('pump', 'pump_amm', 'mayhem'):
        out.append(f'## 4. {TITLES[prog]}, handler by handler\n')
        out.append(table(recs[prog], callee_cap=3, string_cap=2))
        out.append('')
    out.append('## 5. Reproducing\n')
    out.append('```\n'
                'PUMPFUN_EVIDENCE=evidence/original python3 tools/handler_anatomy.py --all --out maps/\n'
                'python3 tools/report_anatomy.py          # census / wrapper / helper summary\n'
                'python3 tools/anatomy_doc.py > docs/handler_anatomy_all4.md\n'
                '```\n')
    print('\n'.join(out))


if __name__ == '__main__':
    main()
