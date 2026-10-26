# B1 — util/transfer_fee.rs: which quote legs actually reach the fee helper

Status: **measured** on `pump` `7a19affa…f7b02d` with `tools/handler_bodies.py` +
`tools/b1_transfer_fee.py` (no build, no toolchain). Supersedes the earlier
version of this note, whose conclusions came from `maps/dispositions.json`
`func_insns: 7 / relative_callees: 0 / has_cpi: false` — an artifact of the
truncated function spans fixed in `S1b_handler_bodies.md`.

## The helper

`@0x12a1c`, 73 insns, 5 callees (`0x129c5<-0x12a20`, `0x2ae70<-0x12a2a`,
`0x2bbd1<-0x12a3c`, `0x359c3<-0x12a47`, `0x33766<-0x12a66`), no syscall of its
own. Shape (cited): it calls `0x129c5` to extract a tagged value from the
account/struct at `r2` (`ldxdw r1,[r2+0]`, `[r2+8]`, `[r2+0x10]`, `[r2+0x18]`;
`0x129c5` returns tag 2 or 0), then compares (`0x12a22: jne r1, 0x2`, `0x12a24:
jlt r7, r1`) and takes a formatted-panic branch (`0x12a28: lddw r2, 0x1b5efc` →
`0x2ae70`) when the amount is below the extracted value. Identification of this
pc as the Token-2022 transfer-fee helper is inherited from `docs/MAP_ALL4.md`
("Transfer-fee helper (cited): `0x12a1c`"); what this note adds is the measured
reachability set, not the identification.

Direct callers, 14 sites in 7 functions (all cited):

| function | call sites |
|---|---|
| `0xb676` (2287 insns) | `0xb993`, `0xba0a`, `0xbb3e`, `0xbb49` |
| `0x10780` (422 insns) | `0x1090b`, `0x10914` |
| `0x27737` (1896 insns) | `0x27ced` |
| `0x27ec6` (2464 insns) | `0x281bb`, `0x286c6` |
| `0x288a1` (1714 insns) | `0x28bbd`, `0x28e62` |
| `0x2913f` (952 insns) | `0x291f8` |
| `0x29515` (734 insns) | `0x29601`, `0x296f4` |

## Measured matrix (transitive call-graph reachability from the handler entry)

`REACHED` = the helper is inside the handler's internal call closure (depth ≤ 6);
the chain is the BFS chain, each edge a real `call` in the parent's body.
It is a structural property, not a proof that a given input executes that path.

| handler | handler_pc | body insns | helper @0x12a1c | depth | chain |
|---|---|---:|---|---:|---|
| `buy_v2` | `0x24ea2` | 196 | REACHED | 2 | `0x24ea2` → `0x27737` → `0x12a1c` |
| `buy_exact_quote_in_v2` | `0x24f6b` | 196 | REACHED | 2 | `0x24f6b` → `0x27ec6` → `0x12a1c` |
| `buy_v3` | `0x250d9` | 168 | REACHED | 3 | `0x250d9` → `0x28f74` → `0x10780` → `0x12a1c` |
| `buy_exact_quote_in_v3` | `0x25185` | 168 | REACHED | 2 | `0x25185` → `0x2913f` → `0x12a1c` |
| `sell_v2` | `0x25034` | 162 | REACHED | 2 | `0x25034` → `0x288a1` → `0x12a1c` |
| `sell_v3` | `0x25231` | 133 | REACHED | 2 | `0x25231` → `0x29515` → `0x12a1c` |
| `multi_hop_curve_swap` | `0x252b8` | 183 | REACHED | 3 | `0x252b8` → `0xacfb` → `0xb676` → `0x12a1c` |
| `migrate_v2` | `0x25749` | 133 | not reached | — | — |
| `migrate` | `0x256fb` | 77 | not reached | — | — |
| `create` | `0x24c1b` | 246 | not reached | — | — |
| `create_v2` | `0x24d15` | 389 | not reached | — | — |
| `buy` (SOL) | `0x2549c` | 216 | not reached | — | — |
| `buy_exact_sol_in` | `0x25579` | 216 | not reached | — | — |
| `sell` (SOL) | `0x25656` | 162 | not reached | — | — |

Edge check by hand (`sbftool.py dis`): `0x24eec: call 0x27737` inside `buy_v2`'s
body, and `0x27ced: call 0x12a1c` inside `0x27737`.

Reproduce:

```
python3 tools/b1_transfer_fee.py evidence/original/pump/deployed.so \
        maps/pump_handlers_full.json 0x12a1c 0x343ae
```

(`0x343ae` = the single `sol_invoke_signed_rust` wrapper of `pump`, entered at
its one CPI site `0x3440d`; every handler's CPI is reached through it.)

## What this means for the reconstruction

1. **The transfer-fee path is the quote leg, exactly as B1 assumed for buys** —
   `buy_v2`, `buy_exact_quote_in_v2`, `buy_v3`, `buy_exact_quote_in_v3` all reach
   `0x12a1c`, while the native-SOL legs (`buy`, `buy_exact_sol_in`) do not.
2. **Correction — the sell side needs the same path.** The earlier note listed
   `sell_v2` as a control "should NOT use transfer-fee helper"; measured, both
   `sell_v2` (`0x25034` → `0x288a1` → `0x12a1c`) and `sell_v3`
   (`0x25231` → `0x29515` → `0x12a1c`) reach it, while native `sell`
   (`0x25656`) does not. `util/transfer_fee.rs` therefore has to be wired into
   **six** trade handlers, not four, plus the router (below).
3. **Correction — `migrate_v2` does not reach the helper.** Its closure has no
   edge to `0x12a1c` (it does CPI, depth 3, but to a different target). If the
   harvest really applies a transfer fee, it does so through another site; that
   is an open question for the Rust port, not a supported claim.
4. **`multi_hop_curve_swap` reaches it via the adapter** (`0x252b8` → `0xacfb` →
   `0xb676` → `0x12a1c`), consistent with the B4 note's "adapter delta" pointer
   to this helper. `0xb676` is also the widest caller (four sites), so it is the
   natural place to look for the per-hop accumulation.
5. CPI is universal in the trade handlers and always goes through one wrapper
   function per program (`pump`: `0x343ae`), so a reconstructed client has a
   single CPI accounting point to match — useful for a later differential harness.

## Still open (unchanged, toolchain-blocked)

The fee arithmetic itself sits one level deeper: `0x129c5` (80 insns) extracts
the config; the multiply/divide and ceiling rounding are not yet located with
cited addresses. Wiring `transfer_fee.rs` into the six handlers and running the
LiteSVM differential vs `deployed.so` still needs Rust + `cargo-build-sbf`,
which is blocked on disk headroom (see `docs/COORDINATION.md`).

Scope: RE / behavioural structure only — no vulnerability analysis, no exploit.
