#!/usr/bin/env python3
"""pump_quote step 1: rename nested_create.rs -> pump_quote.rs (same lines),
wire the module in create_v2.rs as `pump_quote`, keep behavior identical.
"""
import shutil, re

SRC = '/home/tc147/pumpwork/p0/programs/pump'
DST = '/home/tc147/pumpwork/p1/programs/pump'

shutil.copyfile(f'{SRC}/src/nested_create.rs', f'{DST}/src/pump_quote.rs')

cv = open(f'{DST}/src/create_v2.rs').read()
assert '#[path = "nested_create.rs"]' in cv
cv = cv.replace('#[path = "nested_create.rs"]\nmod nested_create;', '#[path = "pump_quote.rs"]\nmod pump_quote;')
cv = cv.replace('nested_create::', 'pump_quote::')
assert 'nested_create' not in cv
open(f'{DST}/src/create_v2.rs', 'w').write(cv)

import os
os.remove(f'{DST}/src/nested_create.rs')
print('p1: nested_create.rs -> src/pump_quote.rs, create_v2.rs rewired')
