#!/usr/bin/env python3
"""Print the 20 embedded program paths (Location-bearing + Location-free), sorted."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLES = os.path.join(ROOT, 'maps', 'fees_location_tables.md')
BASE = 'programs/pump-fees/src/'
txt = open(TABLES).read()
have = [BASE + m for m in re.findall(r'^\| `([^`]+\.rs)`', txt, re.M)]
tree = [l[2:].strip('`') for l in txt.split('## paths with no Location record')[1].splitlines()
        if l.startswith('- ')]
for p in sorted(set(have) | set(tree)):
    print(p)
