#!/usr/bin/env python3
"""Splice the generated Location tables into docs/fees_locations_and_memmove.md.

Keeps the report reproducible: the tables are regenerated from the binary by
gen_fees_report.py, never typed by hand.
"""
import re
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

DOC = os.path.join(ROOT, 'docs', 'fees_locations_and_memmove.md')
TABLES = os.path.join(ROOT, 'maps', 'fees_location_tables.md')


def blocks(path):
    """Return {section-title: text} for the '## ' sections of the tables file."""
    out, cur, buf = {}, None, []
    for line in open(path).read().splitlines():
        if line.startswith('## '):
            if cur:
                out[cur] = '\n'.join(buf).strip('\n')
            cur, buf = line[3:].strip(), []
        else:
            buf.append(line)
    if cur:
        out[cur] = '\n'.join(buf).strip('\n')
    return out


def main():
    b = blocks(TABLES)
    doc = open(DOC).read()
    tree = [l[2:].strip('`') for l in b['paths with no Location record'].splitlines() if l.startswith('- ')]
    base = 'programs/pump-fees/src/'
    have = [base + m for m in re.findall(r'^\| `([^`]+\.rs)`', b['per-file table'], re.M)]
    allp = sorted(set(have) | set(tree))
    doc = doc.replace('<!-- TABLE_TREE -->', '\n'.join(allp))
    doc = doc.replace('<!-- TABLE_PER_FILE -->', b['per-file table'])
    doc = doc.replace('<!-- TABLE_FUNCS -->', b['function table (program files only)'])
    open(DOC, 'w').write(doc)
    print(f'spliced: {len(allp)} paths, '
          f'{b["per-file table"].count(chr(10)) - 1} file rows, '
          f'{b["function table (program files only)"].count(chr(10)) - 1} function rows')
    assert '<!--' not in doc, 'placeholder left in doc'


if __name__ == '__main__':
    main()
