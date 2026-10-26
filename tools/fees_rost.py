#!/usr/bin/env python3
"""Print .rodata strings at given VAs (lengths from the caller or NUL scan)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fees_prog import load  # noqa: E402

p = load(sys.argv[1])
for a in sys.argv[2:]:
    va = int(a, 0)
    chunk = p.b[va:va + 120]
    end = chunk.find(b'\0')
    print(f'{va:#x}: {chunk[:end if end >= 0 else 120]!r}')
