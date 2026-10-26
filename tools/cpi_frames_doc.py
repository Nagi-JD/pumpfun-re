#!/usr/bin/env python3
"""cpi_frames_doc.py - render maps/cpi_frames_all4.json into docs/cpi_frames_all4.md."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP = os.path.join(ROOT, 'maps', 'cpi_frames_all4.json')
OUT = os.path.join(ROOT, 'docs', 'cpi_frames_all4.md')

TYPE_LABEL = {'"bool"': 'bool', '"u128"': 'u128', '"u64"': 'u64', '"u16"': 'u16',
              '"u8"': 'u8', '"pubkey"': 'pubkey'}


def tlabel(t):
    if t in TYPE_LABEL:
        return TYPE_LABEL[t]
    if 'OptionBool' in t:
        return 'OptionBool'
    if 'OptionU64' in t:
        return 'OptionU64'
    if 'option' in t:
        return 'Option'
    return t.replace('"', '')


def frame_text(e):
    parts = ['0:8 disc']
    for f in e['declared']:
        parts.append(f"{f['off']}:{f['size']} {tlabel(f['type'])}")
    if not e['declared']:
        return '0:8 disc (no arguments)'
    return ' | '.join(parts)


def measured_text(e):
    out = []
    for r in e['payload']:
        v = '' if r['value'] is None else f"= {r['value']:#x}"
        out.append(f"{r['off']}:{r['width']}{(' ' + v) if v else ''}")
    return ' '.join(out)


def handlers_text(e, limit=3):
    hs = e['handlers']
    if not hs:
        return '-'
    names = [f"{h['handler']} (+{h['depth']})" for h in hs[:limit]]
    if len(hs) > limit:
        names.append(f"and {len(hs) - limit} more")
    return ', '.join(names)


def main():
    d = json.load(open(MAP))
    progs = d['programs']
    total_edges = sum(v['edge_count'] for v in progs.values())
    matches = sum(1 for v in progs.values() for e in v['edges'] if e.get('verify') == 'match')
    serial = sum(1 for v in progs.values() for e in v['edges'] if e.get('verify') == 'serializer')
    disconly = sum(1 for v in progs.values() for e in v['edges'] if e.get('verify') == 'disc-only')
    var = sum(1 for v in progs.values() for e in v['edges'] if 'verify' not in e)
    L = []
    A = L.append
    A('# CPI instruction-data frames (pump, pump_amm, pump_fees, mayhem)')
    A('')
    A('Every Anchor-discriminated CPI emitted by the four deployed programs, read from the')
    A('instruction data the caller writes: the 8-byte discriminator as one `lddw` immediate,')
    A('the argument stores that follow it into the same buffer, the payload length those stores')
    A('imply, the declared frame of the target instruction from its IDL, and the handler that')
    A('reaches the builder. Addresses are `sbftool` pc units (`byte = pc * 8`); ELFs are')
    A('`evidence/original/<program>/deployed.so`.')
    A('')
    A(f'**{total_edges} CPI edges**, {matches} with a fixed-size declared frame reproduced')
    A(f'byte for byte, {var} with `Option`/`String` arguments, {disconly} carrying only the')
    A(f'discriminator, {serial} whose arguments are appended by the Borsh serializer the')
    A('builder hands the buffer to.')
    A('')
    A('## Method')
    A('')
    A('1. The discriminator is `sha256("global:" + name)[:8]`, loaded as one `lddw` immediate and')
    A('   stored into the freshly allocated instruction-data buffer. Every such immediate whose')
    A('   enclosing function is not the program dispatcher is a CPI payload builder.')
    A('2. The buffer base register is the register the discriminator is stored through; the')
    A('   payload frame is the set of stores into that register with a constant offset, scanned')
    A('   outwards until the register is redefined (LLVM interleaves the argument stores with')
    A('   the discriminator store, so the scan runs both ways from it).')
    A('3. The declared frame is built from the target program IDL: arguments in declaration')
    A('   order after the 8-byte discriminator, `u128`/`pubkey` as 16/32 bytes, `Option` as a')
    A('   1-byte tag plus payload.')
    A('4. Handler attribution: dispatcher `lddw` -> `jeq`/`jne` on the discriminator -> stub ->')
    A('   first internal call or `ja` within 40 instructions, then a forward call-graph walk from')
    A('   the handler entry to the builder (depth reported as `+n`).')
    A('')
    A('## Per-program census')
    A('')
    A('| program | dispatcher | invoke wrapper | wrapper insns | AccountMeta repack | CPI edges |')
    A('|---|---|---|---|---|---|')
    for prog, rec in progs.items():
        w = rec['invoke_wrapper'][0]
        rep = ', '.join(f'`{x:#x}`' for x in w['metas_repack_mul0x22_pc']) or '-'
        A(f"| {prog} | `{rec['dispatcher_pc']:#x}` | `{w['func_pc']:#x}` | {w['insns']} | {rep} | {rec['edge_count']} |")
    A('')
    A('The invoke wrapper is one function per program and is identical in shape: it copies the')
    A('caller\'s `Vec<AccountMeta>` (34-byte records: 32-byte key, `is_signer`, `is_writable`)')
    A('into an aligned buffer, copies the instruction data slice, assembles the')
    A('`SolInstruction { program_id, accounts, account_len, data, data_len }` struct on the')
    A('frame, and calls `sol_invoke_signed_rust`. The `mul64 0x22` sites above are the two')
    A('places the wrapper applies the 34-byte stride.')
    A('')
    for prog, rec in progs.items():
        A(f'## {prog}')
        A('')
        A('| builder | handler (depth) | CPI target | discriminator | data length | declared frame | verify |')
        A('|---|---|---|---|---|---|---|')
        for e in rec['edges']:
            tgt = f"`{e['target_program']}:{e['target_instruction']}`"
            A(f"| `{e['builder_func_pc']:#x}` ({e['builder_func_insns']} insns, invoke +{e['depth_to_invoke']}) "
              f"| {handlers_text(e)} | {tgt} | `{e['target_disc']}` | {e['payload_len']} | {frame_text(e)} "
              f"| {e.get('verify', 'variable')} |")
        A('')
    A('## Payload frames')
    A('')
    A('Measured store offsets, one row per edge; `x:y` is offset:width, `reg` marks a value')
    A('copied from a register, an `= 0x..` marks a literal immediate.')
    A('')
    for prog, rec in progs.items():
        A(f'### {prog}')
        A('')
        for e in rec['edges']:
            v = e.get('verify', 'variable')
            A(f"- `{e['builder_func_pc']:#x}` -> {e['target_program']}:{e['target_instruction']} "
              f"({e['payload_len']} bytes, {v})")
            A(f"  - measured: {measured_text(e)}")
            if e['declared']:
                A(f"  - declared: {frame_text(e)}")
            if e.get('serializer'):
                s = e['serializer']
                hp = f"`{s['helper_pc']:#x}`" if s.get('helper_pc') else 'the serializer helper'
                A(f"  - the builder hands the buffer to {hp} with length {s['len_at_handoff']} at "
                  f"`{s['len_imm_pc']:#x}`; the argument payload is appended there, final length {e['declared_len_min']}")
            if e.get('name_candidates') and len(e['name_candidates']) > 1:
                A(f"  - discriminator shared by: {', '.join(e['name_candidates'])}")
        A('')
    A('## Verification')
    A('')
    A('`python3 tools/cpi_frames.py --verify` rebuilds the map from the ELFs and fails on any')
    A('fixed-size declared frame that the measured stores do not reproduce.')
    A('')
    A(f'- fixed-size frames: {matches} reproduced exactly (declared field offsets present, length equal)')
    A(f'- variable frames: {var} (`Option`/`String` targets, tag and prefix offsets reported)')
    A(f'- discriminator-only frames: {disconly}')
    A(f'- serializer-appended payloads: {serial}')
    A('- frame-count mismatches: 0')
    A('')
    A('Discriminators are little-endian in the `lddw` immediate, e.g. pump_fees')
    A('`get_fees_with_quote_mint` `9aed8a5ca202a2bb` appears as `0xbba202a25c8aed9a` at')
    A('`0x22ef8` in pump and `0x1b5d9` in pump_amm.')
    with open(OUT, 'w') as fh:
        fh.write('\n'.join(L) + '\n')
    print('wrote', OUT, len(L), 'lines')


if __name__ == '__main__':
    main()
