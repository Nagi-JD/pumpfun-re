# pumpfun-re — independent reverse-engineering of the pump.fun Solana programs

Reverse-engineering research for the four deployed pump.fun programs
(`pump`, `pump_amm`/PumpSwap, `pump_fees`, `mayhem`). Everything here is derived
from **public on-chain bytecode** — the deployed programs are public; their Rust
source is not. This repo collects an independent sBPF analyzer, a full structural
map of all four programs, per-handler behavioral specs, differential test
harnesses + a coverage-guided fuzzer that verify reconstructions against the
deployed binaries, and byte-identity research that builds on the public
reconstruction in [lalalune/pumpfun-source] (MIT).

> **Honest status.** Two tracks.
> **Behavioral:** reconstructions verified against the deployed binaries by
> executed differential tests on the paths actually exercised (with measured
> coverage, not assumed).
> **Byte-identity:** we start from lalalune's latest published checkpoints and
> push their function-level match counts further, measured with *their* window
> metric (normalized function windows + raw byte-exact bodies). **No core program
> is byte-identical as a whole ELF yet** — matched function windows are not
> whole-file equality, and normalized matches do not prove identical bytes.

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

## Current verified state — behavioral

- **pump**: core trade loop (create / buy / sell / v3 / SPL+Token-2022 quote) verified
  behaviorally against the deployed binary; real reconstruction bugs found and fixed
  via the harness (e.g. the missing `admin_cto` 6095 guard; see `recovered-fixes/`).
- **pump_amm (PumpSwap)**: full flow verified; differential fuzzer 1,262 runs, 0 real
  divergences.
- **pump_fees**: **31/31 handlers** match the deployed binary on executed paths, with
  handler bodies reached for all 31 (`harness/feesharness`, oracle = exact rebuild of
  lalalune's Fees checkpoint; `update_fee_shares_v2` and `crank_donation_fee_pda` on
  in-body rejection paths only).
- **mayhem**: `initialize_mayhem_state` reconstructed; `create_v2(is_mayhem_mode=true)`
  end-to-end differential gives byte-identical account state on both sides.

## Current state — byte-identity race (27 Oct 2026)

Function windows matched (their window metric) vs lalalune's latest published
checkpoint for each program:

| Program | lalalune published | Ours | Main levers |
|---|---:|---:|---|
| PumpSwap | 651 / 785 (148 raw) | **681 / 785** (148 raw) | base path-prefix remap reproduces their 643 exactly, then `error!` closures placed on deployed lines (+11 → 654); then a verified d1→d2→f2→g3 chain (+27): +13 error-closures across deposit/amm_hop, +5 `require!`/`Source` line moves, +4 `pool.rs` declaration reorder, +5 out-of-line `checked_sub3`/`checked_add3` constructor bodies → 681, re-measured on the canonical profile at every step with zero raw loss and zero matched loss |
| Fees | 582 / 585 (200 exact) | **582 / 585** (200 exact, byte-identical) | reproduced their newest `fees-extend-integration` checkpoint byte-for-byte — `symbols.so` + stripped `candidate.so` sha256-identical to their `result.json`; parity, not a lead. 3 windows remain: 120816 Sweep (near-miss +3 instrs), 147944 Crank (missing code), 163920 CreateDonation (extra PDA-verify region) |
| Pump | 738 / 1035 (Round36, 145 raw) | **786 / 1035 (137 raw)** | per-site `error!` closures placed on deployed lines (no hardcoded-location macro); `migrate`/`migrate_v2` quote fix, verified by execution; +4 trade-body windows (0x176d8/0x178e0 partial-fill quote, 0x87ca0 post-fee, 0x14eab8 legacy raw-quote) restored via `black_box` anti-folding barriers, re-measured on the canonical s7clean profile with zero raw loss. A host-triple `rustc` shim makes the native Linux build byte-identical to their macOS artifact, so raw matches too (137) |
| Mayhem | 432 / 441 (100 exact) | 429 | lalalune's Round-36 Mayhem reached 432; we hold 429 (parity base), **−3 behind**. The 9 remaining windows are whole-function codegen divergences (whole-ELF class), not reachable by localized source edits |

**Honest standing vs lalalune (27 Oct 2026).** We lead PumpSwap (**+30**) and Pump's
normalized windows (**+48**), and tie Fees (582/200, both 3 unmatched). They lead Pump's
raw-byte-exact count (**145 vs our 137**) and Mayhem (**432 vs our 429**). Regaining Pump
raw is a link-order / whole-ELF problem. A measured block-reorder attempt (reordering a
118-function size-identical run to the deployed internal order) **regressed** raw 137→128:
a function's position is the cumulative sum of all preceding function sizes, so symbol-order
alone cannot place a callee at its deployed offset. This is the same unsolved
whole-function-layout wall as Mayhem's 9 remaining windows — not cracked by anyone (their
raw edge is incidental alignment, not a solution).

Every result has a packet in [`research/`](research/README.md) (patch + build recipe +
measure JSON). Whole-ELF byte-identity of the four core programs: **not achieved
by anyone yet** (lalalune's Donation Relay, a separate program, is whole-ELF exact).

[lalalune/pumpfun-source]: https://github.com/lalalune/pumpfun-source

## Contributing

See `CONTRIBUTING.md` and `docs/COORDINATION.md` (the task board). In short:
verify every claim against the binary (cite addresses), never fabricate a
byte-identity or behavioral-match claim, and keep the honest distinction between
"compiles / dispatches" and "verified behaviorally equivalent on executed paths".

[LiteSVM]: https://github.com/LiteSVM/litesvm
