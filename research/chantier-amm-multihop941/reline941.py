#!/usr/bin/env python3
"""Reline the `output` checked_sub Overflow site in multi_hop_swap.rs to the
outlined error!() form with error! landing on source line 941, byte-identical in
form to the already-matched 636 arm. Lines <=718 are left untouched.

Usage: edit941.py <path-to-multi_hop_swap.rs> [TARGET_LINE]
"""
import sys

path = sys.argv[1]
target = int(sys.argv[2]) if len(sys.argv) > 2 else 941
lines = open(path).read().split("\n")

# Locate the exact output block (anchored, no ambiguity).
old = [
    "    let output = if sell {",
    "        total_quote",
    "            .checked_sub(quote_transfer_fee)",
    "            .ok_or(PumpAmmError::Overflow)?",
    "    } else {",
    "        base_amount",
    "    };",
]
# find start index
start = None
for i in range(len(lines) - len(old) + 1):
    if lines[i:i+len(old)] == old:
        start = i
        break
if start is None:
    print("BLOCK NOT FOUND — aborting", file=sys.stderr)
    sys.exit(2)

# 1-based line number of the ".ok_or_else(|| " line = start+4 (the 4th old line)
# We want `error!(...)` on 1-based line == target.
# New block:
#   let output = if sell {
#       total_quote
#           .checked_sub(quote_transfer_fee)
#           .ok_or_else(||<space>
#   <blank lines>
#   error!(PumpAmmError::Overflow))?
#       } else { ... }
okorelse_lineno = start + 4  # 1-based line of ".ok_or_else(|| "
# number of blank lines between okorelse line and the error! line
n_blank = target - okorelse_lineno - 1
if n_blank < 0:
    print(f"target {target} too small (okorelse at {okorelse_lineno})", file=sys.stderr)
    sys.exit(3)

new = (
    [
        "    let output = if sell {",
        "        total_quote",
        "            .checked_sub(quote_transfer_fee)",
        "            .ok_or_else(|| ",
    ]
    + [""] * n_blank
    + [
        "error!(PumpAmmError::Overflow))?",
        "    } else {",
        "        base_amount",
        "    };",
    ]
)
lines = lines[:start] + new + lines[start+len(old):]
open(path, "w").write("\n".join(lines))

# verify: report 1-based line that now holds the error!
for i, l in enumerate(lines, 1):
    if l.strip() == "error!(PumpAmmError::Overflow))?" and i >= target:
        print(f"error! now at line {i} (target {target})")
        break
print(f"okorelse at {okorelse_lineno}, n_blank {n_blank}, new total lines {len(lines)}")
