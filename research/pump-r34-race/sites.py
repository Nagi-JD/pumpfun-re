#!/usr/bin/env python3
"""sites.py SRCDIR : for each deployed closure origin, report whether line L of the file holds an
error!(PumpError::Variant) (closure body or named fn item). Also lists other error!(Overflow/Truncation)
lines in those files so misplacement offsets are visible."""
import sys, re
S = """16bb8 buy_v2.rs 465 Truncation
16dc0 buy_v2.rs 469 Overflow
16fc8 buy_v2.rs 881 Truncation
171d0 buy_v2.rs 927 Truncation
176d8 buy_v2.rs 959 Truncation
178e0 buy_v2.rs 983 Truncation
17ae8 buy_v2.rs 995 Overflow
19cc0 create_v2.rs 412 QuoteChainAccountsRequired
410b0 migrate.rs 280 Overflow
412b8 migrate.rs 282 Overflow
4bb40 migrate_v2.rs 309 Overflow
4bd48 migrate_v2.rs 313 Overflow
4bf50 migrate_v2.rs 326 Overflow
57c38 multi_hop_curve_swap.rs 259 Overflow
5fc48 multi_hop_curve_swap.rs 571 Overflow
5fe50 multi_hop_curve_swap.rs 589 Truncation
60058 multi_hop_curve_swap.rs 624 Overflow
60260 multi_hop_curve_swap.rs 673 Truncation
60468 multi_hop_curve_swap.rs 692 Overflow
60670 multi_hop_curve_swap.rs 736 Overflow
60878 multi_hop_curve_swap.rs 744 Overflow
63530 pump_quote.rs 212 Overflow
63738 pump_quote.rs 222 Overflow
6f6d8 sell_v2.rs 341 Truncation
6f8e0 sell_v2.rs 366 Overflow
6fae8 sell_v2.rs 368 Overflow
6fcf0 sell_v2.rs 386 Overflow
81640 trade_v3.rs 382 Overflow
84970 trade_v3.rs 721 Overflow
84b78 trade_v3.rs 767 Overflow
84d80 trade_v3.rs 811 Truncation
84f88 trade_v3.rs 904 Truncation
85190 trade_v3.rs 911 Truncation
85398 trade_v3.rs 930 Truncation
855a0 trade_v3.rs 970 Overflow
857a8 trade_v3.rs 997 Truncation
87ca0 trade_v3.rs 1140 Truncation
87ea8 trade_v3.rs 1155 Overflow
ac2b8 buy_v2.rs 498 Overflow
ac4c0 buy_v2.rs 500 Overflow
137db8 lib.rs 268 Truncation
14eab8 lib.rs 629 Truncation
14ecc0 lib.rs 674 Overflow
14eec8 lib.rs 679 Overflow
14f0d0 lib.rs 684 Overflow
14f2d8 lib.rs 689 Overflow
1549b0 lib.rs 981 Truncation
154bb8 lib.rs 1007 Overflow
154dc0 lib.rs 1009 Overflow
154fc8 lib.rs 1022 Overflow
1551d0 lib.rs 1027 Overflow
1553d8 lib.rs 1032 Overflow
1555e0 lib.rs 1037 Overflow
1774f8 lib.rs 664 Overflow
177700 lib.rs 666 Overflow"""
D = sys.argv[1].rstrip('/') + '/programs/pump/src/'
cache = {}
ok = 0
for row in S.splitlines():
    w, f, l, v = row.split(); l = int(l)
    if f not in cache:
        try: cache[f] = open(D + f).read().split('\n')
        except FileNotFoundError: cache[f] = []
    L = cache[f]
    hit = l <= len(L) and ('error!(PumpError::' + v) in L[l - 1]
    if not hit and l <= len(L) and ('error!(crate::PumpError::' + v) in L[l - 1]: hit = True
    ok += hit
    near = [i + 1 for i, x in enumerate(L) if ('PumpError::' + v) in x and 'error!' in x and abs(i + 1 - l) <= 40]
    print('%-7s %-24s %5d %-12s %s %s' % (w, f, l, v[:12], 'OK ' if hit else '-- ', '' if hit else near))
print('placed', ok, '/ 55')
