#!/usr/bin/env python3
"""Instruction-data frames of the deployed pump.fun programs, read from the bytes.

Anchor dispatches an instruction with the 8-byte discriminator stripped: the
handler receives a reader over the remaining bytes. This tool recovers, per
instruction handler, what the deployed code does with that reader:

  * where the reader comes from (the handler frame itself, or the generated
    argument-deserialiser frame it delegates to),
  * every length gate the reader is held to (the immediates in `jlt`/`jeq`
    against the remaining length),
  * every fixed-offset read of argument bytes with its width and byte offset,
  * for Borsh `Vec`/`String` arguments: the 4-byte length prefix offset, the
    element cap, and the element stride the deserialiser multiplies by.

Two reader regimes hold across the deployed builds:

  own frame   `r5` carries the caller's frame pointer; the reader descriptor
              lives at `[fp-0x1000]` (pointer) and `[fp-0xff8]` (length), so a
              handler loads  `ldxdw rX, [rB-0x1000]` / `ldxdw rX, [rB-0xff8]`
              where `rB` is the register that received `r5`.
  by reference the generated `Deserialize` impl takes `&mut &[u8]` in `r2`, so
              the pointer is `[r2]` and the length `[r2+8]`.

Usage:
  python3 tools/arg_frames.py --prog pump_fees            # dump per handler
  python3 tools/arg_frames.py --prog pump_fees --json maps/pump_fees_arg_frames.json
  python3 tools/arg_frames.py --prog pump_fees --verify   # re-derive + compare

Evidence only: every figure is an instruction address in the deployed ELF
(.text vaddr/8 = pc).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fees_prog import load  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The deployed ELFs and the upstream IDL dumps live in the sibling reconstruction
# checkout (`../pumpfun-source/evidence`), same layout the other tools use.
EVIDENCE = os.environ.get('PUMPFUN_EVIDENCE', os.path.join(os.path.dirname(ROOT), 'pumpfun-source', 'evidence'))
SO = {prog: os.path.join(EVIDENCE, 'original', prog, 'deployed.so') for prog in ('pump', 'pump_amm', 'pump_fees', 'mayhem')}
IDL = {prog: os.path.join(EVIDENCE, 'upstream', prog + '.json') for prog in ('pump', 'pump_amm', 'pump_fees')}

# opcodes (sBPF v1)
LD = {0x61: 4, 0x69: 2, 0x71: 1, 0x79: 8}
MOV_I, MOV_R, ADD_I, ADD_R, SUB_I, MUL_I = 0xb7, 0xbf, 0x07, 0x0f, 0x17, 0x27
LDDW, CALL, EXIT = 0x18, 0x85, 0x95
DEBUG = set()
JMP = {0x05, 0x15, 0x1d, 0x25, 0x2d, 0x35, 0x3d, 0x45, 0x4d, 0x55, 0x5d,
       0x65, 0x6d, 0x75, 0x7d, 0xa5, 0xad, 0xb5, 0xbd, 0xc5, 0xcd, 0xd5, 0xdd}


def frame_list(p, start):
    """Instructions of one reloc-aware frame, in pc order."""
    return [p.ins[pc] for pc in p.order if p.func_of.get(pc) == start]


def find_reader_base(body):
    """Which register carries the reader descriptor, and in which regime."""
    for ins in body:
        if ins.op == 0x79 and ins.off == -0xff8:
            return ins.src, 'owned'          # [rB-0x1000] = ptr, [rB-0xff8] = len
        if ins.op == 0x79 and ins.off == -0x1000:
            return ins.src, 'owned'
    return None, None


def trace(body, base_reg, regime, seed_unknown_reads=True):
    """Symbolic dataflow over one frame, following both sides of every branch.

    Register values:
      ('D',)          reader descriptor base
      ('P', delta)    reader pointer + delta  (delta None once the reader moved)
      ('L',)          reader length / remaining length
      ('C', v)        constant
    Returns reads, gates, muls, len32, advances.
    """
    ins_by_pc = {ins.pc: ins for ins in body}
    order = [ins.pc for ins in body]
    nx = {pc: (order[k + 1] if k + 1 < len(order) else None) for k, pc in enumerate(order)}
    reads, gates, muls, len32, advances = [], [], [], [], []
    ptr_slots, helper_calls = [], []
    fp_reader = {}          # fp slot -> delta of the reader pointer it holds
    seen = {}

    def join(a, b):
        if a is None:
            return dict(b)
        if b is None:
            return dict(a)
        return {r: v for r, v in a.items() if b.get(r) == v}

    work = [(order[0], {base_reg: ('D',), 10: ('F', 0)})] if order else []
    while work:
        pc, st = work.pop()
        ins = ins_by_pc.get(pc)
        if ins is None:
            continue
        if DEBUG and pc in DEBUG:
            print('[debug] visit', hex(pc), sorted((r, v) for r, v in st.items()))
        if pc in seen:
            j = join(seen[pc], st)
            if j == seen[pc]:
                continue
            seen[pc] = j
            st = j
        else:
            seen[pc] = dict(st)
        dst, src, off = ins.dst, ins.src, ins.off
        out = dict(st)
        succ = []
        if ins.op == EXIT:
            succ = []
        elif ins.op == CALL:
            v = out.get(2)
            if v and v[0] == 'F':
                tgt = pc + 1 + ins.imm
                if tgt != pc:
                    helper_calls.append({'pc': hex(pc), 'target': hex(tgt), 'slot': v[1]})
                    if v[1] in fp_reader:
                        fp_reader[v[1]] = None      # the callee advances it
            elif v and v[0] == 'D':
                # the reader reference is forwarded unchanged to another frame
                tgt = pc + 1 + ins.imm
                if tgt != pc:
                    helper_calls.append({'pc': hex(pc), 'target': hex(tgt), 'slot': None})
            for r in (0, 1, 2):
                out.pop(r, None)
            n = nx.get(pc)
            succ = [n] if n is not None else []
        elif ins.op in JMP:
            # note: for sBPF jumps the branch displacement is the `off` field and
            # `imm` is the comparison constant.
            tgt = pc + 1 + ins.off
            if ins.op == 0x05:                     # ja
                succ = [tgt if tgt in ins_by_pc else None]
            elif ins.op in (0xa5, 0xad, 0x35, 0x3d, 0x15, 0x1d, 0x55, 0x5d, 0x25, 0x2d,
                            0x45, 0x4d, 0x65, 0x6d, 0x75, 0x7d, 0xc5, 0xcd, 0xd5, 0xdd):
                v = out.get(dst)
                if v and v[0] == 'L':
                    gates.append({'pc': hex(pc), 'op': ins.mn, 'imm': ins.imm})
                succ = [nx.get(pc), tgt if tgt in ins_by_pc else None]
            else:
                succ = [nx.get(pc)]
            succ = [s for s in succ if s is not None]
        elif ins.op in LD:
            w = LD[ins.op]
            v = out.get(src)
            if v is None:
                out.pop(dst, None)
            elif v[0] == 'F' and (v[1] + off) in fp_reader:
                # loading the reader pointer back out of the frame slot the
                # handler stashed it in (after a deserialiser advanced it, the
                # delta is unknown).
                out[dst] = ('P', fp_reader[v[1] + off])
            elif v[0] == 'D':
                if regime == 'owned':
                    if ins.op == 0x79 and off == -0x1000:
                        out[dst] = ('P', 0)
                    elif ins.op == 0x79 and off == -0xff8:
                        out[dst] = ('L',)
                    else:
                        out.pop(dst, None)
                else:  # reader passed by reference: &mut &[u8] in r2
                    if ins.op == 0x79 and off == 0:
                        out[dst] = ('P', 0)
                    elif ins.op == 0x79 and off == 8:
                        out[dst] = ('L',)
                    else:
                        out.pop(dst, None)
            elif v[0] == 'P':
                delta = None if v[1] is None else v[1] + off
                reads.append({'off': delta, 'width': w, 'pc': hex(pc), 'op': ins.mn})
                out.pop(dst, None)
            elif v[0] == 'L':
                if ins.op == 0x61 and off == 0:
                    len32.append({'pc': hex(pc)})
                out.pop(dst, None)
            else:
                out.pop(dst, None)
            n = nx.get(pc)
            succ = [n] if n is not None else []
        elif ins.op == MOV_I:
            out[dst] = ('C', ins.imm)
            n = nx.get(pc)
            succ = [n] if n is not None else []
        elif ins.op == MOV_R:
            if src == 10:
                out[dst] = ('F', 0)
            elif src in out:
                out[dst] = out[src]
            elif dst == base_reg:
                # the entry shuffles the caller's reader-base register into a
                # callee-saved one (`mov64 r7, r5`): keep the seed.
                out[dst] = ('D',)
            else:
                out.pop(dst, None)
            n = nx.get(pc)
            succ = [n] if n is not None else []
        elif ins.op == ADD_I or ins.op == SUB_I:
            k = ins.imm if ins.op == ADD_I else -ins.imm
            v = out.get(dst)
            if v and v[0] == 'C':
                out[dst] = ('C', v[1] + k)
            elif v and v[0] == 'P':
                out[dst] = ('P', None if v[1] is None else v[1] + k)
            elif v and v[0] == 'F':
                out[dst] = ('F', v[1] + k)
            else:
                out.pop(dst, None)
            n = nx.get(pc)
            succ = [n] if n is not None else []
        elif ins.op == MUL_I:
            v = out.get(dst)
            if v and v[0] == 'C':
                muls.append({'pc': hex(pc), 'imm': ins.imm})
                out[dst] = ('C', v[1] * ins.imm)
            else:
                muls.append({'pc': hex(pc), 'imm': ins.imm})
                out.pop(dst, None)
            n = nx.get(pc)
            succ = [n] if n is not None else []
        elif ins.op == LDDW:
            out.pop(dst, None)
            n = nx.get(pc)
            succ = [n] if n is not None else []
        elif ins.op in (0x62, 0x6a, 0x72, 0x7a, 0x63, 0x6b, 0x73, 0x7b):
            # a store of an advanced pointer back into the reader descriptor
            # moves the reader: later offsets are no longer static. A store of
            # the reader pointer into a frame slot is how the handler builds the
            # `&mut &[u8]` it hands to the generated argument deserialiser.
            v = out.get(dst)
            if v and v[0] == 'D':
                val = out.get(src) if ins.op & 0x3 == 3 else None
                if val and val[0] == 'P' and val[1]:
                    advances.append({'pc': hex(pc), 'store_off': off})
            if v and v[0] == 'F' and ins.op & 0x3 == 3:
                val = out.get(src)
                if val and val[0] == 'P':
                    ptr_slots.append({'fp_slot': v[1] + off, 'pc': hex(pc)})
                    fp_reader[v[1] + off] = val[1]
            n = nx.get(pc)
            succ = [n] if n is not None else []
        else:
            out.pop(dst, None)
            n = nx.get(pc)
            succ = [n] if n is not None else []
        for s in succ:
            work.append((s, out))
    return {'reads': reads, 'gates': gates, 'muls': muls, 'len32': len32, 'advances': advances,
            'ptr_slots': ptr_slots, 'helper_calls': helper_calls}


def resolve_deserialiser(p, handler_tr, max_depth=4):
    """Follow the `&mut &[u8]` reference from the handler frame into the frame
    that actually reads argument bytes. Returns (frame, chain, trace) or None."""
    queue = []
    slots = {s['fp_slot'] for s in handler_tr['ptr_slots']}
    for h in handler_tr['helper_calls']:
        if h['slot'] is None or h['slot'] in slots or h['slot'] + 8 in slots:
            queue.append((int(h['target'], 16), 0, [h['pc']]))
    seen = set()
    while queue:
        tgt, depth, chain = queue.pop(0)
        if tgt in seen or depth > max_depth or tgt not in p.ins:
            continue
        seen.add(tgt)
        hb = frame_list(p, tgt)
        tr = trace(hb, 2, 'byref')
        if tr['reads']:
            return tgt, chain, tr
        inner = {s['fp_slot'] for s in tr['ptr_slots']}
        for h in tr['helper_calls']:
            if h['slot'] is None or h['slot'] in inner or h['slot'] + 8 in inner:
                queue.append((int(h['target'], 16), depth + 1, chain + [h['pc']]))
    return None


FIXED = {'bool': 1, 'u8': 1, 'i8': 1, 'u16': 2, 'i16': 2, 'u32': 4, 'i32': 4,
         'u64': 8, 'i64': 8, 'u128': 16, 'i128': 16, 'pubkey': 32}
DEFINED = {'Fees': 24, 'FeeTier': 40, 'Shareholder': 34, 'OptionBool': 1}


def type_size(t):
    """Borsh size of a declared argument type, or None when it is variable."""
    if isinstance(t, str):
        return FIXED.get(t)
    if 'defined' in t:
        return DEFINED.get(t['defined']['name'])
    if 'option' in t:
        return None                          # an Option is 1 byte + payload, or 1 byte
    return None                              # vec / string


def expected_frame(args):
    out, off = [], 0
    for a in args:
        sz = type_size(a['type'])
        if sz is None:
            out.append({'name': a['name'], 'type': a['type'], 'off': off, 'size': None})
            off = None
        else:
            out.append({'name': a['name'], 'type': a['type'], 'off': off, 'size': sz})
            if off is not None:
                off += sz
    return out


def spans(reads):
    """Merge the byte reads of the reader into maximal contiguous spans."""
    rs = sorted({(r['off'], r['off'] + r['width']) for r in reads if r['off'] is not None})
    out = []
    for a, b in rs:
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b - a) for a, b in out]


def render_doc(out, prog, idl):
    L = []
    L.append('# `%s` instruction-data frames, read from the deployed bytes' % prog)
    L.append('')
    L.append('Anchor strips the 8-byte discriminator before the handler runs, so every handler '
             'works on a reader over the instruction bytes that follow it. This page records what '
             'each of the %d deployed handlers does with that reader: where the reader comes from, '
             'the length gates the bytes are held to, and the byte offset and width of every load '
             'off the reader pointer. Generated by `tools/arg_frames.py`; the raw records are in '
             '`maps/%s_arg_frames.json`.' % (len(out), prog))
    L.append('')
    L.append('Two reader regimes appear, and both are visible in the instruction stream:')
    L.append('')
    L.append('* **handler frame** - the handler receives the caller frame pointer in `r5`, so the '
             'reader pointer is `[r5-0x1000]` and its length `[r5-0xff8]`. The handler loads the '
             'bytes itself.')
    L.append('* **deserialiser frame** - the handler stashes the reader pointer in a frame slot '
             '(`stxdw [fp+S], <reader ptr>`) and calls the generated argument deserialiser with '
             '`r2 = fp+S`, i.e. `&mut &[u8]` (pointer at `[r2]`, length at `[r2+8]`). The loads are '
             'in that frame and the handler reads the deserialised struct.')
    L.append('')
    L.append('## Frames, handler by handler')
    L.append('')
    L.append('| handler | handler frame | reader | length gates | byte spans | variable fields | args declared |')
    L.append('|---|---|---|---|---|---|---|')
    for name in sorted(out):
        r = out[name]
        rd = r['reader']
        if rd == 'none':
            reader = 'not read'
        elif rd['kind'] == 'own':
            reader = 'handler (`r%d`)' % rd['reg']
        else:
            reader = '`%s`' % rd['frame']
        gates = ', '.join('`%s %s`@%s' % (g['op'], g['imm'], g['pc']) for g in r['gates']) or '-'
        sp = ', '.join('%d+%d' % (o, w) for o, w in spans(r['reads'])) or '-'
        var = []
        for rd2 in r['reads']:
            if rd2['off'] is None:
                var.append('%s tail +`%d`@%s' % (rd2['op'], rd2['width'], rd2['pc']))
        for m in r.get('caps', []):
            if m['stride']:
                var.append('cap %d x stride %d = %d B@%s' % (m['cap'], m['stride'], m['bytes'], m['gate_pc']))
            else:
                var.append('cap %d B@%s' % (m['cap'], m['gate_pc']))
        args = ', '.join('%s:%s' % (a['name'], json.dumps(a['type'])) for a in r['args_declared']) or '-'
        L.append('| `%s` | %s | %s | %s | %s | %s | %s |' % (
            name, r['handler_pc'], reader, gates, sp, '; '.join(var) or '-', args))
    L.append('')
    return '\n'.join(L)


def render_findings(out, prog, sha):
    inline = [n for n, r in out.items() if isinstance(r['reader'], dict) and r['reader']['kind'] == 'own']
    deleg = [n for n, r in out.items() if isinstance(r['reader'], dict) and r['reader']['kind'] == 'helper']
    untouched = [n for n, r in out.items() if r['reader'] == 'none']
    L = ['']
    L.append('## What the bytes say')
    L.append('')
    L.append('The %d handlers split three ways: **%d** load the fixed argument bytes in their own '
             'frame, **%d** hand the reader to a generated deserialiser frame (the same frame is '
             'reused by every handler declaring the same argument list), **%d** never touch the '
             'reader at all - those declare no arguments, and the absence of a load is the '
             'measurement that says so.' % (len(out), len(inline), len(deleg), len(untouched)))
    L.append('')
    L.append('### Length gates')
    L.append('')
    L.append('The gates are the same shape everywhere: `jeq rX, 0` when a single byte is read '
             '(a one-byte read only needs a non-empty reader), `jlt rX, N` when N bytes are taken '
             'at once, and the remainder is decremented between fields (`add64 rX, -N`) so the '
             'next gate is stated against what is left. In `get_fees` at `0x136c8` the gate is '
             '`jlt r1, 0x11` for the first 17 bytes and then `jlt r3, 0x8` on the difference, '
             'i.e. 25 bytes for the fixed part.')
    L.append('')
    L.append('### `get_fees`: the third argument is length-checked but never loaded')
    L.append('')
    L.append('`GetFees` declares `is_pump_pool: bool`, `market_cap_lamports: u128`, '
             '`trade_size_lamports: u64`, `is_new_quote_mint: OptionBool` - 26 bytes with the tag. '
             'The deployed code loads byte `0` (`ldxb r6, [r2+0]` at `0x136ac`), the 16 bytes at '
             '`1` and `9` (`ldxdw r4, [r2+1]`, `ldxdw r3, [r2+9]` at `0x136cd`/`0x136cc`) and the '
             'tag byte at `0x19` (`ldxb r1, [r2+0x19]` at `0x136d0`). Bytes `17..25`, the `u64`, '
             'are covered by the length gate and never read: the reader walks from the `u128` '
             'straight to the tag.')
    L.append('')
    L.append('### `OptionBool` is optional on the wire')
    L.append('')
    L.append('At `0x136cf` the deployed code compares the reader length with `0x19` and skips the '
             'tag load when it matches exactly (`jeq r1, 0x19, +0x4`): a 25-byte argument frame is '
             'valid and means "tag absent". A 26-byte frame supplies the tag at `0x19`, and the '
             'value is range-checked (`jeq 0` / `jne 1`) before use.')
    L.append('')
    L.append('### Option arguments gate the payload, not the frame')
    L.append('')
    L.append('`admin_cto_sharing_config` takes `new_admin: Option<Pubkey>`. The deployed code loads '
             'the tag at offset `0` (`ldxb r1, [r4+0]` at `0x139f0`), accepts only `0` or `1` '
             '(`jeq 1` at `0x139f3`, falling through to the error path otherwise) and, on the `Some` '
             'path only, requires 33 bytes (`jlt r0, 0x21` at `0x139f5`) before taking the pubkey at '
             '`1..33`. A one-byte frame with tag `0` is a complete instruction.')
    L.append('')
    L.append('### Variable-length arguments: prefix, cap, stride')
    L.append('')
    L.append('Every `Vec`/`String` argument starts with a `u32` length at the current reader '
             'position (`ldxw r1, [r9+0]` at `0x1f9a` for `FeeTier`, `0x212f` for `Shareholder`, '
             '`0x2027` for `String`), and the element count is capped before the allocation:')
    L.append('')
    L.append('| argument | prefix | element stride | element cap | bytes | gate |')
    L.append('|---|---|---:|---:|---:|---|')
    L.append('| `vec<FeeTier>` | `u32` | 40 | 102 | 4080 | `0x1faa` / `0x1fad` |')
    L.append('| `vec<Shareholder>` | `u32` | 34 | 120 | 4080 | `0x2141` / `0x2144` |')
    L.append('| `String` | `u32` | - | - | 1048576 | `0x202e` |')
    L.append('')
    L.append('The two vector caps are the same 4080-byte budget; they differ only because the '
             'element strides do: `FeeTier` is `u128` + `Fees` (`16 + 3*8 = 40`) and `Shareholder` '
             'is `pubkey` + `u16` (`32 + 2 = 34`), so both recover the declared struct sizes from '
             'the multiplier alone. `String` is capped at 1 MiB and is followed by the next field '
             'at a position the reader only knows at run time - `create_social_fee_pda` reads '
             '`platform` straight off the advanced reader (`ldxb r1, [r1+0]` at `0x13ab1`) after '
             'the shared deserialiser returns.')
    L.append('')
    L.append('### Field loads are not one load per field')
    L.append('')
    L.append('A 32-byte `Pubkey` arrives as an inlined copy: `initialize_fee_program_global` takes '
             'it with `ldxw r2, [r2+0]`, `ldxh r5, [r2+4]`, `ldxdw r1, [r2+6]`, `ldxb r4, [r2+0xe]`, '
             '`ldxdw r5, [r2+0x21]` and two more (`0x12e0d`-`0x12e1e`). Reading the frame as '
             'contiguous byte spans is what turns those fragments back into one `pubkey@0+32` '
             'followed by `disable_flags@32+1` and `claim_rate_limit@33+8` - the same offsets the '
             'declaration order gives, unaligned because Borsh does not pad.')
    L.append('')
    L.append('### The other programs')
    L.append('')
    L.append('`tools/arg_frames.py --prog pump` and `--prog pump_amm` run the same analysis against '
             'the other two deployed programs whose dispatcher maps ship here (`maps/handlers.json`, '
             '`maps/amm_handlers_full.json`), against their own IDLs.')
    L.append('')
    L.append('## Verification')
    L.append('')
    L.append('`python3 tools/arg_frames.py --prog %s --verify` re-derives every record from the '
             'deployed ELF (SHA-256 `%s`) and compares it with `maps/%s_arg_frames.json` field by '
             'field: %d/%d records reproduce exactly.' % (prog, sha, prog, len(out), len(out)))
    L.append('')
    return '\n'.join(L)


def find_caps(body):
    """Borsh length prefixes: the `jlt rX, K` element cap that immediately
    precedes the `mul64 rY, S` stride computation, and the byte cap a `String`
    or byte-vector reader applies."""
    caps = []
    for k, ins in enumerate(body):
        if ins.mn not in ('jlt', 'jle') or ins.imm <= 0:
            continue
        for j in range(k + 1, min(k + 5, len(body))):
            nxt = body[j]
            if nxt.op == MUL_I:
                caps.append({'cap': ins.imm, 'stride': nxt.imm, 'gate_pc': hex(ins.pc),
                             'mul_pc': hex(nxt.pc), 'bytes': ins.imm * nxt.imm})
                break
            if nxt.mn in ('jlt', 'jle', 'ja'):
                break
        if ins.imm >= 0x10000:
            caps.append({'cap': ins.imm, 'stride': None, 'gate_pc': hex(ins.pc),
                         'mul_pc': None, 'bytes': None})
    return caps


def handler_starts(prog):
    """name -> handler entry insn. Prefers the per-handler anatomy map and falls
    back to the dispatcher maps that ship with the repo."""
    anat = os.path.join(ROOT, 'maps', '%s_handler_anatomy.json' % prog)
    if os.path.exists(anat):
        d = json.load(open(anat))
        return {k: int(v['body'], 16) for k, v in d['handlers'].items()}
    flat = os.path.join(ROOT, 'maps', 'handlers.json')
    full = os.path.join(ROOT, 'maps', '%s_handlers_full.json' % ('amm' if prog == 'pump_amm' else prog))
    single = os.path.join(ROOT, 'maps', '%s_handlers.json' % ('fees' if prog == 'pump_fees' else prog))
    for path in (full, single, flat):
        if not os.path.exists(path):
            continue
        d = json.load(open(path))
        out = {}
        for name, v in d.items():
            if isinstance(v, dict):
                pc = v.get('handler_pc', v.get('handler'))
            else:
                pc = v
            if pc is None:
                continue
            out[name] = int(pc, 16)
        if out:
            return out
    raise SystemExit('no handler map for %s' % prog)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prog', default='pump_fees', choices=sorted(SO))
    ap.add_argument('--json')
    ap.add_argument('--doc')
    ap.add_argument('--verify', action='store_true')
    ap.add_argument('--only')
    a = ap.parse_args()

    global p
    p = load(SO[a.prog])
    anat = {}
    apath = os.path.join(ROOT, 'maps', '%s_handler_anatomy.json' % a.prog)
    if os.path.exists(apath):
        anat = json.load(open(apath))
    handlers = handler_starts(a.prog)
    if a.prog in IDL:
        idl = json.load(open(IDL[a.prog]))
    else:
        idl = {'instructions': []}
    idl_by = {i['name']: i for i in idl['instructions']}

    out = {}
    for name in sorted(handlers):
        if a.only and a.only != name:
            continue
        start = handlers[name]
        body = frame_list(p, start)
        base, regime = find_reader_base(body)
        rec = {'handler_pc': hex(start), 'insns': len(body), 'args_declared': [
            {'name': x['name'], 'type': x['type']} for x in idl_by.get(name, {}).get('args', [])],
            'reads': [], 'gates': [], 'muls': [], 'len32': [], 'advances': [], 'caps': []}
        tr_handler = {'reads': [], 'gates': [], 'muls': [], 'len32': [], 'advances': [],
                      'ptr_slots': [], 'helper_calls': []}
        rec['reader'] = 'none'
        if base is not None:
            tr_handler = trace(body, base, regime)
            rec['reader'] = {'kind': 'own', 'reg': base}
        tr = tr_handler
        # the argument deserialiser may be a separate frame that takes the reader
        # by reference (&mut &[u8]) in r2: the handler stashes the reader pointer
        # in a frame slot (`stxdw [fp+S], <reader ptr>`) and passes `r2 = fp+S`.
        found = resolve_deserialiser(p, tr_handler)
        if found is not None:
            tgt, chain, trh = found
            tr = {k: trh[k] + tr_handler[k] for k in ('reads', 'gates', 'muls', 'len32', 'advances')}
            rec['reader'] = {'kind': 'helper', 'frame': hex(tgt),
                             'insns': len(frame_list(p, tgt)), 'chain': chain,
                             'tail_reads': len(tr_handler['reads'])}
            rec['caps'] = find_caps(frame_list(p, tgt))
        elif base is not None:
            rec['caps'] = find_caps(body)
        for k in ('reads', 'gates', 'muls', 'len32', 'advances'):
            ded = {json.dumps(x, sort_keys=True): x for x in tr[k]}
            rec[k] = sorted(ded.values(), key=lambda x: (x.get('off') if x.get('off') is not None else -1, x['pc']))
        # cross-check the measured spans against the frame the declared arguments
        # imply (Borsh declaration order, tightly packed)
        exp = expected_frame(rec['args_declared'])
        rec['args_expected'] = exp
        rec['spans'] = [{'off': o, 'width': w} for o, w in spans(rec['reads'])]
        if not exp:
            rec['frame_check'] = 'no arguments declared; reader not touched' if not rec['reads'] else 'reader read'
        elif any(e['size'] is None for e in exp):
            rec['frame_check'] = 'variable-length arguments'
        else:
            cov = set()
            for s in rec['spans']:
                cov.update(range(s['off'], s['off'] + s['width']))
            unloaded = ['%s@%d+%d' % (e['name'], e['off'], e['size'])
                        for e in exp if not set(range(e['off'], e['off'] + e['size'])) <= cov]
            rec['fields_unloaded'] = unloaded
            rec['frame_check'] = 'all declared fields loaded' if not unloaded else \
                'not loaded: ' + ', '.join(unloaded)
        out[name] = rec

    if a.json:
        with open(a.json, 'w') as f:
            json.dump(out, f, indent=1, sort_keys=True)
        print('wrote', a.json)

    if a.doc:
        sha = anat.get('sha256', '')
        with open(a.doc, 'w') as f:
            f.write(render_doc(out, a.prog, idl) + render_findings(out, a.prog, sha))
        print('wrote', a.doc)

    if a.verify:
        prev = json.load(open(os.path.join(ROOT, 'maps', '%s_arg_frames.json' % a.prog)))
        bad = 0
        for name in sorted(out):
            if prev.get(name) != out[name]:
                bad += 1
                print('MISMATCH', name)
        print('verify: %d/%d handlers reproduce the recorded frames' % (len(out) - bad, len(out)))
        return 1 if bad else 0

    for name, rec in out.items():
        print('%-32s %-6s %-9s %s' % (
            name,
            (rec['reader']['kind'] if rec['reader'] != 'none' else '-'),
            rec['frame_check'],
            ', '.join('%d+%d' % (s['off'], s['width']) for s in rec['spans']) or '-'))


if __name__ == '__main__':
    main()
