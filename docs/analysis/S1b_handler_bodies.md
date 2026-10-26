# S1b — real handler bodies: the `func_insns` artifact, and the fix

Status: measured on the four deployed binaries (no build, no toolchain needed).
Programs (SHA-256 of `deployed.so`, unchanged from `docs/MAP_ALL4.md`):

- `pump` `7a19affaa2c6187e04a5fe0ea298cee81fa5eb8c24cfcc30d85f615e89f7b02d`
- `pump_amm` `6a7ad34596d83b4c435b32f458a56e718e9f82eb4ad38e4316616d15d24d8ff7`
- `pump_fees` `4f2955d0f6b40cc9ff7daa18ccad7d19119ba1249759f4e7e3bb691beee6b35e`
- `mayhem` `a87fa9f866272514e6acb852b668c4a08aeb173d56c883039991d114d1199bdb`

## The defect (what `maps/dispositions.json` actually measured)

Every handler in `maps/dispositions.json` reported a body of 3–7 instructions,
`relative_callees: 0`, `syscalls: {}`, `has_cpi: false`,
`calls_transfer_fee_helper: false` — for all 139 handlers of the four programs,
including `buy_v2`, `create_v2`, `create_pool`, `get_fees`.

Those numbers are an artifact, not a property of the programs.

Cause, in one chain of three facts:

1. `tools/sbftool.py` recovered "functions" as the linear span between *call
   targets* (`_funcs`: `starts = {base} ∪ {pc+1+imm for each call}`).
2. In the deployed `.so` every syscall call site keeps its **unapplied**
   `R_BPF_64_32` relocation and carries `imm = -1` on disk (the loader patches it
   at load time). So `pc + 1 + imm == pc`: each syscall site declared **itself** a
   function start.
3. The dispatch thunk of every Anchor handler begins with a `sol_log_` call on
   its `file!()/line!()` pair at thunk+8. The fake start therefore cut the body
   off after exactly the prologue → 5–7 instructions, zero callees, zero
   syscalls, no CPI.

Cited example (`pump`, `create_v2`, handler `0x24d15`):

```
24d15: mov64 r8, r5            ; prologue
24d16: stxdw [r10 -0x358], r4
24d17: stxdw [r10 -0x350], r3
24d18: stxdw [r10 -0x348], r2
24d19: mov64 r6, r1
24d1a: lddw r1, 0x1b7d7b      ; &file!() string
24d1c: mov64 r2, 0x15         ; len
24d1d: call -0x1              ; R_BPF_64_32 -> sol_log_   <-- fake function start here
```

`sbftool.py func pump.so 0x24d15` printed `(7 insns)` before the fix and
`(389 insns)` after it, with the same `.text`.

## The fix

`tools/sbftool.py`:
- new `Prog._relocs()`: parses `.rel.dyn` (`.rel.dyn` type `10` =
  `R_BPF_64_32` → call site, type `8` = `R_BPF_64_RELATIVE` → `lddw` of an
  internal va). Mapping is `va = 8 * insn_index` (`.text` vaddr `0x120`,
  `base = taddr/8`).
- `Prog._funcs()` skips call sites that carry a type-10 relocation, so syscalls
  never create a function start. Resolved call sites are also printed by
  `dis` (`call -0x1 -> syscall sol_log_`).
- Effect, measured by `tools/func_starts_probe.py` (`old -> new` starts, and how
  many spans grow back):

  | program | syscall sites | fake sites that were also real targets | starts old → new | spans restored |
  |---|---:|---:|---|---:|
  | pump | 270 | 6 | 1169 → 905 | 235 |
  | pump_amm | 174 | 5 | 831 → 662 | 147 |
  | pump_fees | 155 | 6 | 637 → 488 | 124 |
  | mayhem | 134 | 5 | 502 → 373 | 81 |

`tools/handler_bodies.py` (new): does not rely on linear spans at all.
- entries = internal call targets (both directions) + ELF `entrypoint` /
  `custom_panic` symbol values;
- body = recursive descent from the entry: fallthrough, jump targets, `ja`
  follows only its target, `exit` ends a branch, `lddw` advances two slots,
  calls stay opaque; a fallthrough that would land on *another* known entry ends
  the path (`strict_bounds`);
- per handler: body insns, direct callees, back edges, direct and **transitive**
  syscalls (call-graph closure, depth ≤ 6), CPI presence
  (`sol_invoke_signed_rust`), and reachability of a watched pc set with the
  shortest call chain.

Commands:

```
python3 tools/sbftool.py stats       evidence/original/pump/deployed.so
python3 tools/sbftool.py func        evidence/original/pump/deployed.so 0x24d15
python3 tools/handler_bodies.py body evidence/original/pump/deployed.so 0x24d15 --calls
python3 tools/handler_bodies.py handlers evidence/original/pump/deployed.so \
        maps/pump_handlers_full.json maps/pump_bodies.json 0x12a1c,0x343ae
python3 tools/compare_dispositions.py maps/dispositions.json maps/pump_bodies.json
```

## Before / after (all 139 handlers, mechanically regenerated)

| program | handlers | insns old (min/med/max) | insns new (min/med/max) | has_cpi old | has_cpi new | syscall sites old | syscall sites new |
|---|---:|---|---|---:|---:|---:|---:|
| pump | 53 | 6 / 7 / 7 | 61 / 174 / 389 | 0 | 44 | 0 | 631 |
| pump_amm | 30 | 6 / 7 / 7 | 78 / 171 / 377 | 0 | 26 | 0 | 320 |
| pump_fees | 31 | 3 / 7 / 7 | 12 / 169 / 249 | 0 | 25 | 0 | 333 |
| mayhem | 25 | 5 / 7 / 7 | 43 / 68 / 399 | 0 | 16 | 0 | 247 |

Worst understatements (`old -> new`):

- pump: `create_v2` 7→389, `set_params` 7→355, `admin_cto` 7→264, `create` 7→246,
  `distribute_fee_to_holders` 7→241
- pump_amm: `create_pool` 7→377, `create_config` 7→285, `update_fee_config` 7→282,
  `disable` 7→241, `buy` 7→227
- pump_fees: `claim_social_fee_pda_v2` 7→249, `claim_social_fee_pda` 7→248,
  `update_buyback_authority` 7→212, `initialize_fee_program_global` 7→197
- mayhem: `update_global_params` 7→399, `buy`/`buy_v2`/`sell`/`sell_v2` 7→102

New artifacts: `maps/pump_bodies.json`, `maps/pump_amm_bodies.json`,
`maps/pump_fees_bodies.json`, `maps/mayhem_bodies.json`
(per handler: `body_pc`, `body_insns`, `direct_callees`, `callgraph_nodes`,
`syscalls`, `syscalls_transitive`, `has_cpi`, `watch_reach`).

## Validation

1. **Two independent methods agree.** Linear span after the `_funcs` fix and
   CFG recursive descent both give 389 insns for `pump::create_v2 @0x24d15`;
   `pump` totals: 905 vs 907 entries (the 2 extra are the `entrypoint` /
   `custom_panic` symbol values, which are not call targets).
2. **Non-CPI instructions stay non-CPI.** In `pump_fees`, `get_fees @0x136a0`
   and `get_fees_with_quote_mint @0x13763` report no CPI while every state
   mutator does — the expected shape for view functions, so the CPI column is
   not simply "always true".
3. **Bound sensitivity is immaterial.** Body sizes with `strict_bounds` on vs
   off are identical for 13 of the 14 B1 cases; only
   `multi_hop_curve_swap` differs (183 strict vs 327 loose), i.e. over-approximation
   by leaking into the next function's linear code is measurable only there.
4. **CPI wrapper is a single site per program.** `sol_invoke_signed_rust`
   resolves to exactly one call site in each of the four binaries
   (`pump` `0x3440d` inside function `0x343ae`); all handlers' CPI reachability
   is traced through that function, never through a per-handler syscall.

## Consequences for prior citations

- Any statement sourced from `dispositions.json`'s `func_insns`,
  `relative_callees`, `syscalls`, `has_cpi` or `calls_transfer_fee_helper` is
  void, including the corresponding `docs/analysis/B*_notes.md` excerpts. The
  `handler_pc` / `stub_pc` / discriminator columns are unaffected: they come
  from the dispatcher and re-verify.
- `sbftool.py field` / `afield` operate on `func_body()`, i.e. on the same
  truncated spans, so every `field`/`afield` answer produced before this fix
  inspected only the handler prologue. Re-run them against the fixed tool.
- Behavioural facts that do survive: dispatcher discriminators, handler entry
  pcs, callee structure (now complete), and the syscall inventory per program.

Scope: RE / behavioural structure only — no vulnerability analysis, no exploit.
