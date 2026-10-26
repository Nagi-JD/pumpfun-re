# pumpfun-re — independent reverse-engineering of the pump.fun Solana programs

Reverse-engineering research for the four deployed pump.fun programs
(`pump`, `pump_amm`/PumpSwap, `pump_fees`, `mayhem`). Everything here is derived
from **public on-chain bytecode** — the deployed programs are public; their Rust
source is not. This repo collects an independent sBPF analyzer, a full structural
map of all four programs, per-handler behavioral specs, buildable behavioral
reconstructions, and a differential test harness + coverage-guided fuzzer that
verify reconstructions against the deployed binaries.

> **Honest status.** This is a **behavioral** reverse-engineering effort, not a
> byte-identical rebuild. Whole-file byte-identity of the deployed programs is an
> open problem (the original source structure is lost and cannot be uniquely
> recovered from a stripped binary). What this repo proves is *behavioral*
> equivalence on the paths actually exercised — and it measures that coverage
> rather than assuming it.

## What's here

| Path | What it is |
|------|-----------|
| `tools/sbftool.py` | sBPF disassembler + analyzer. Decoder verified **0-diff vs llvm-objdump** across every instruction of all four programs. Function recovery, discriminator→handler lookup, caller search, interprocedural field-writer data-flow. Pure Python, no external deps. |
| `tools/*.py` | structural-map builders (`map_amm.py`, `map_rest.py`, `re_map.py`, `re_full.py`), on-chain scanners (`scan_trailing.py`, `hunt_multihop.py` — need a `SOLANA_RPC` env var). |
| `docs/REVERSE_ENGINEERING.md` | full structural map: every instruction → discriminator → handler, syscalls, source-file strings, per program. |
| `docs/MAP_ALL4.md` | one-page summary map of all 4 programs. |
| `docs/MASTER_GAPS.md` | ranked gap list for a full behavioral build. |
| `docs/VERIFICATION.md` | differential-harness results (what is proven byte-identical in *behavior* vs matched-rejection vs not yet verified). |
| `maps/*.json` | instruction→handler address tables (`handlers.json` = pump, `amm_handlers.json` = PumpSwap). |
| `specs/*.md` | 11 binary-verified per-handler behavioral specs for the pump program. |
| `recovered-fixes/*.rs` | reconstruction fixes found via the differential harness/fuzzer (e.g. the Token-2022 transfer-fee direction, buyback-check ordering, creator-fee/volume writes). |
| `harness/` | differential test harnesses (Rust + LiteSVM): `diffharness` (pump), `ammharness` (PumpSwap), `feesharness` (fees). Run deployed vs recovered on identical state, diff ok/err/logs/account-state/CU. |
| `fuzzer/` | coverage-instrumented differential fuzzer + `COVERAGE.md` (measured instruction/branch coverage of the deployed pump program under the harness). |

## Using `sbftool`

```bash
# disassemble a function
python tools/sbftool.py func <program.so> 0x2549c
# locate an instruction's handler by Anchor discriminator
python tools/sbftool.py disc <program.so> global:buy global:sell
# program stats (insns, functions, syscalls)
python tools/sbftool.py stats <program.so>
```

The deployed `.so` files are **not committed** (they are public on-chain — pull
them with `solana program dump <PROGRAM_ID> out.so --url mainnet-beta`).

## Running the differential harness

The harnesses are Rust + [LiteSVM]. Each loads the **deployed** `.so` and a
**recovered** build at the same program id, runs the same instructions on
identical seeded state, and compares results byte-for-byte. See each
`harness/*/src/main.rs` for the exact flow and `docs/VERIFICATION.md` for results.

## Current verified state (summary)

- **pump**: core trade loop (create / buy / sell / v3 / SPL+Token-2022 quote) verified
  behaviorally against the deployed binary; several real reconstruction bugs found
  and fixed via the harness/fuzzer (see `recovered-fixes/`).
- **pump_amm (PumpSwap)**: `create_pool` / `deposit` / `withdraw` byte-identical in
  behavior (incl. the constant-product sqrt-k LP math); `buy`/`sell` reach an
  identical terminal state at a shared external fee-program gate.
- **pump_fees**: structural map complete (31/31); differential verification in progress.
- **mayhem**: partial map; pending.

Byte-identity of the deployed binaries: **not achieved and not the goal of this
repo** — this is behavioral RE with measured coverage.

## Contributing

See `CONTRIBUTING.md` and `docs/COORDINATION.md` (the task board). In short:
verify every claim against the binary (cite addresses), never fabricate a
byte-identity or behavioral-match claim, and keep the honest distinction between
"compiles / dispatches" and "verified behaviorally equivalent on executed paths".

[LiteSVM]: https://github.com/LiteSVM/litesvm
