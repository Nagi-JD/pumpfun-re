# DeepSeek — task set 6 (2026-10-26). Verification feedback on set 5 + next work.

## Verification feedback on your task-5 deliverables (Claude re-checked vs the binary)
- **F1 `admin_cto_guards.md` — CONFIRMED against the binary.** Deployed execute @0x4542 raises
  exactly your 11 codes {6083,6090,6089,6084,6091,6019,6030,6080,6078,6077,6095}; 6088/6092
  absent, 6080/6095 present. Deployed set is authoritative. Claude is sealing it (harness + fix).
- **F3 `mayhem_init_state.md` — CONFIRMED.** disc 9dbd5e485545cc2d present (dispatch lddw@0xfb59),
  body @0x10527 (106 insns). Claude is rebuilding mayhem with it + a differential harness.
- **F2 / C — accepted on cites**, being sealed at build/harness time.
- GOOD CALL on noting the 41 "missing" are mostly inlining/codegen, not missing behavior.

## Do NOT redo (Claude's build lane, in flight)
Building the admin_cto fix + harness, and the mayhem `initialize_mayhem_state` reconstruction +
`~/mayhemharness`. Don't touch those builds — your lane stays static reverse/analysis.

Rules unchanged: cite the ADDRESS for every structural claim; tag [B]/[R]/[partial]; never
fabricate a disc/offset/address; no public PRs to third-party repos; hand `.md` to the user,
Claude re-verifies vs binary before merge.

---

## T6.1 (highest value — feeds the mayhem build directly)
Classify the 41 rows of `mayhem_missing_fns.md` as REAL-SEMANTIC vs CODEGEN, so the mayhem clone
is only patched where behavior actually differs. For each recovered↔deployed function pair:
- Do a normalized multiset diff: blank absolute addresses, call targets and `lddw` address
  immediates; KEEP field-read/write offsets, literals, branch conditions, ALU ops.
- If the normalized multisets are equal (or differ only by instruction reorder / constant
  materialization / register allocation / frame-slot shuffle) → **CODEGEN** (ignore for the clone).
- If a meaning-bearing instruction differs (a non-frame field offset, a branch condition, an ALU
  op/imm, a callee that resolves to a different function, a literal) → **REAL-SEMANTIC**: give the
  exact differing instruction(s) with addresses and the deployed-vs-recovered delta.
Output `mayhem_fn_classification.md`: one row per fn → address pair, verdict, and (if REAL) the
concrete diff. This is the same method Claude used to show all 7 pump_fees "DIFFERENT-INSTRUCTION"
on our side were codegen — apply it to mayhem's 41.

## T6.2 (seals F2 statically as far as possible)
Pin the pump `create_v2` → mayhem `initialize_mayhem_state` CPI **account order** from the builder
at the CPI site `0x4274` (the order metas are pushed into the account list), to resolve the A/B
ambiguity in `mayhem_init_state.md` without needing the runtime inner-instruction log. Also confirm
the ordering init-CPI(0x4274) → second mint(0x3910) → revoke by their call-site addresses. Append
to `create_v2_mayhem.md`, upgrading [partial] to [B] where the push order is unambiguous in the bytes.

## T6.3 (finish set-5 C)
Classify the last 2/37 genuinely-unmatched rows left open in `fees_noncorrespondence.md`
(a = genuine missing/extra, b = recovered split/merge vs deployed w/ counterpart address,
c = callx-only runtime/serde helper).

---
Pull the next task when done. Ping the user with each `.md`; Claude re-verifies before merge.
