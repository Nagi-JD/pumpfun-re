#!/usr/bin/env python3
"""Verify the report's spliced tables match the generated tables byte for byte."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, 'docs', 'fees_locations_and_memmove.md')
TABLES = os.path.join(ROOT, 'maps', 'fees_location_tables.md')

doc_rows = [l for l in open(DOC).read().splitlines() if l.startswith('|')]
gen_rows = [l for l in open(TABLES).read().splitlines() if l.startswith('|')]
print(f'doc table rows={len(doc_rows)} generated={len(gen_rows)}')
missing = [r for r in gen_rows if r not in doc_rows]
extra = [r for r in doc_rows if r not in gen_rows]
print('missing from doc:', len(missing))
for m in missing:
    print('  -', m)
print('extra in doc:', len(extra))
for m in extra:
    print('  +', m)
paths = re.findall(r'^programs/pump-fees/src/\S+\.rs$', open(DOC).read(), re.M)
print('tree paths in doc:', len(paths), 'distinct:', len(set(paths)))
