#!/usr/bin/env python3
"""Show ELF sections of a Solana .so and where given strings live (section + offset)."""
import struct
import sys


def sections(path):
    b = open(path, 'rb').read()
    shoff, = struct.unpack_from('<Q', b, 0x28)
    es, n, si = struct.unpack_from('<HHH', b, 0x3a)
    secs = []
    strtab = None
    raw = [struct.unpack_from('<IIQQQQIIQQ', b, shoff + i * es) for i in range(n)]
    if si < n:
        strtab = raw[si][4]
    for s in raw:
        name = b[strtab + s[0]:b.index(b'\0', strtab + s[0])].decode() if strtab else '?'
        secs.append((name, s))
    return b, secs


def main():
    path = sys.argv[1]
    b, secs = sections(path)
    print(f'# sections of {path}')
    for name, s in secs:
        print(f'  {name:24s} addr={s[3]:#010x} off={s[4]:#010x} size={s[5]:#010x} ({s[5]})')
    print()
    needle = sys.argv[2].encode() if len(sys.argv) > 2 else b'programs/'
    hits = []
    i = 0
    while True:
        j = b.find(needle, i)
        if j < 0:
            break
        k = b.find(b'\0', j)
        hits.append((j, b[j:k][:120].decode('latin1')))
        i = j + 1
    print(f'# {len(hits)} occurrence(s) of {needle!r}')
    for off, s in hits:
        where = '?'
        for name, sec in secs:
            if sec[4] <= off < sec[4] + sec[5] and sec[5]:
                where = f'{name}+{off - sec[4]:#x} (va {sec[3] + (off - sec[4]):#x})'
                break
        print(f'  fileoff={off:#08x} {where:40s} {s}')


if __name__ == '__main__':
    main()
