# Pump program — differential-harness code-coverage baseline

**Target:** deployed pump sBPF v1 program
`/mnt/d/dev/ext/pumpfun-source/evidence/original/pump/deployed.so`
**Static size (denominator):** 215,873 instructions, 1,169 recovered functions
(from `sbftool.py stats`; `.text` = 1,792,208 bytes).
**Harness measured:** the existing LiteSVM differential harness (`~/diffharness`,
~15 instruction scenarios), re-run unmodified-in-behaviour against the deployed `.so`.
**Work dir:** `~/sbfcov` (no edits were made to `~/diffharness` or `~/pump-clone`).

---

## Method — REAL EXECUTED-INSTRUCTION TRACE (not a static estimate)

Live per-instruction program-counter traces were obtained from the actual LiteSVM
run. This is **executed coverage**, measured mechanically from the VM, not a static
over-approximation.

How the trace was captured:

1. The LiteSVM stack uses `solana-sbpf` 0.10.0 via `solana-program-runtime` 2.2.4 /
   `solana-bpf-loader-program` 2.2.4. The interpreter already supports tracing:
   when `Config.enable_instruction_tracing` is true, `interpreter.rs` calls
   `context_object.trace(self.reg)` for every executed instruction, where
   `reg[11]` is the program counter. The `InvokeContext` ContextObject stores
   these into `trace_log`, flushed to `InvokeContext.traces: Vec<Vec<[u64;12]>>`
   on each instruction-frame pop, and exposes them via the **public**
   `InvokeContext::get_traces()`.

2. Two things block this through stock LiteSVM 0.6.1:
   - LiteSVM builds its loader env with
     `create_program_runtime_environment_v1(.., debugging_features = false)`
     (lib.rs ~482), so tracing is **off** at program-load time; and
   - LiteSVM constructs the `InvokeContext` inline inside `process_transaction`
     and drops it after the tx — `TransactionMetadata` has **no** traces field,
     the `accounts` field holding the loader env is **private**, so neither the
     flag nor the traces are reachable from an external crate.

3. Resolution (contained, in `~/sbfcov` only): LiteSVM 0.6.1 source was **vendored**
   into `~/sbfcov/vendored/litesvm` and patched in two spots:
   - `debugging_features` → `true` (enables `enable_instruction_tracing`);
   - the inline `InvokeContext` was scoped so that, right after `process_message`,
     `ic.get_traces()` is copied into a thread-local `LAST_TRACES`, drained by a
     new `pub fn take_last_traces()`.
   Enabling tracing does **not** change execution semantics — `trace()` only
   records register snapshots; the only trace-length cap in the runtime
   (`MaxInstructionTraceLengthExceeded`) bounds CPI depth and is enforced
   regardless of the flag.

4. The harness scenarios from `diffharness/src/main.rs` were copied verbatim into
   `~/sbfcov/src/main.rs` (same accounts, same instruction data, same deps:
   spl-token, associated-token, token-metadata, token-2022, pump_fees, pump_amm,
   mayhem). After each `send_transaction`, `take_last_traces()` is read.

5. **Per-program attribution (unambiguous).** Each trace frame is one program
   invocation whose first entry's `reg[11]` equals that program's entry PC
   (`(e_entry - text_vaddr)/8`). Pump's entry index is **175522**, unique among
   all loaded programs (spl-token 225, ATA 2677, metadata 45051, token-2022 39404,
   pump_fees 82549, pump_amm 121825, mayhem 66939). Only frames whose first PC ==
   175522 are counted as pump; CPI frames into other programs are excluded. This
   also captures pump's Anchor `__event_authority` self-CPI frames (they re-enter
   at the same pump entry PC), which is why most handlers show 2 frames.

6. Trace PCs are text-relative; `sbftool` PC-space is offset by `base = text_vaddr/8 = 36`,
   so `sbftool_pc = trace_pc + 36`. Sanity: **0** of the executed PCs fell outside
   pump's valid instruction-start set, and the mapped entry PC 175558 is a valid
   instruction — confirming correct attribution and mapping.

Pipeline: `~/sbfcov` (vendored+patched litesvm, traced harness) → per-handler
`*.trace` files in `~/sbfcov/traces/` → `cov_report.py` (reuses `sbftool.Prog`
for the static denominator, function set, and branch sites).

---

## Results

### Overall instruction coverage (executed / total)

> All 15 scenarios return ok:true (verified by running the stock
> diffharness binary read-only), so these traces reflect fully-executed
> successful happy-path runs. Coverage counts a pump instruction PC once even if
> a loop executes it many times, so per-handler compute-unit totals (e.g. buy =
> 118,545 CU, incl. CPIs) are far larger than the distinct-instruction counts here.

| Metric | Value |
|---|---|
| **Distinct instructions executed** | **50,131 / 215,873 = 23.22%** |
| Functions touched | 433 / 1,169 = 37.04% |
| Distinct executed edges (all types) | 51,680 |

### Per-handler instruction coverage (executed / 215,873 total)

| Handler | Executed insns | % of total |
|---|---:|---:|
| initialize | 3,576 | 1.66% |
| set_params | 5,088 | 2.36% |
| create | 10,161 | 4.71% |
| buy | 10,986 | 5.09% |
| sell | 8,703 | 4.03% |
| buy_v3 | 9,577 | 4.44% |
| sell_v3 | 9,082 | 4.21% |
| buy_v3_spl (non-SOL quote) | 9,901 | 4.59% |
| buy_v3_t22 (Token-2022 quote) | 10,155 | 4.70% |
| sell_v3_t22 | 9,941 | 4.61% |
| bexact_v3_t22 (buy_exact_quote_in_v3) | 10,559 | 4.89% |
| beq_v2_t22 (buy_exact_quote_in_v2) | 12,128 | 5.62% |
| create_v2 (Mayhem flow) | 13,289 | 6.16% |
| migrate | 14,114 | 6.54% |
| migrate_v2 | 5,483 | 2.54% |

(Per-handler numbers overlap heavily — all paths share the Anchor
entry/dispatch/(de)serialization prologue — so they do **not** sum to the 23.22%
union.)

### Branch / edge coverage (conditional jumps)

| Metric | Value |
|---|---|
| Static conditional branches | 14,831 |
| Conditional branches reached (executed) | 4,123 / 14,831 = 27.80% |
| Branch **directions** covered, over executed branches | 4,236 / 8,246 = 51.37% |
| Branch **directions** covered, over all static branches | 4,236 / 29,662 = 14.28% |
| Executed branches with **both** directions taken | 113 |
| Executed branches with only **one** direction | 4,010 |

**Reading:** The harness is strong line/handler coverage for the happy path but
weak path coverage: of the branches it reaches, only ~1.03 of 2 directions are
exercised on average, and only 113 branches ever go both ways. This is the
signature of single-shot, success-only scenarios — error paths, slippage/limit
failures, alternate quote/fee branches, and the not-taken side of guards are
largely unmeasured.

---

## Blocker

No hard blocker for executed coverage: live PC traces **were** obtained.
The only obstacle — stock LiteSVM 0.6.1 hard-codes `debugging_features=false`,
keeps the loader env private, and exposes no trace accessor — was overcome by
vendoring + 2-spot patching LiteSVM inside `~/sbfcov` (upstream and
`~/diffharness` untouched). Option (b), running `solana-sbpf` standalone, was
**not** needed and would have been infeasible anyway (pump requires a full
syscall + CPI + account/invoke-context environment that only the runtime
provides). The static-reachability fallback (option c) was **not** needed.

---

## What is needed for true per-edge coverage

The instruction and branch-direction numbers above already ARE per-edge data
(every consecutive-PC transition within a pump frame is recorded, so each
conditional branch's taken vs not-taken side is known). To make it a complete
per-edge coverage tool:

1. **More inputs, not more instrumentation.** The capture is complete; the gap is
   the corpus. Both-direction branch coverage needs negative/adversarial scenarios
   (failing slippage, zero/dust amounts, wrong owners, uninitialised accounts,
   paused/completed curves, every quote×fee×token-program combination, and the
   un-run handlers: withdraw, collect/claim fees, admin setters, close/extend,
   set_creator, the v2/exact variants not in the harness). Feeding those through
   the same `take_last_traces()` path and unioning raises both metrics directly.
2. **Attribute functions precisely.** `sbftool` derives function starts from CALL
   targets; the ELF entrypoint (175558) is reached by the VM, not a call, so it is
   not a recovered start. For exact per-function reporting, seed `sbftool.starts`
   with the ELF `entry_pc` and any `callx` (indirect, 144 sites) targets resolved
   from the trace itself (the trace reveals real indirect-call edges a static tool
   cannot).
3. **Edge denominator from a full CFG.** For a true "edges covered / edges total"
   ratio, build the static CFG (fall-through + jump targets + resolved `callx`
   from traces) in `sbftool`; today the branch denominator uses the 14,831
   conditional-jump sites, which is the meaningful branch-coverage denominator but
   not the full basic-block edge count.
4. (Optional) The interpreter path is used here; LiteSVM does not JIT, so traces
   are exact. If a JIT path were ever used, `enable_instruction_tracing` also works
   in the JIT backend (jit.rs), but numbers should be taken from the interpreter to
   avoid any backend divergence.

---

## Reproduce

```
cd ~/sbfcov && ~/.cargo/bin/cargo build
./target/debug/covharness /mnt/d/dev/ext/pumpfun-source/evidence/original/pump/deployed.so
# writes ~/sbfcov/traces/*.trace + _summary.txt
python3 -I <scratchpad>/cov_report.py     # prints the tables above
```
