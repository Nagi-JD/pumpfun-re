# DeepSeek — task set 5 (2026-10-26). While Shuai-Qing finishes the pump_fees sharing lot.

**This set = the OPEN/HIGH findings of `fidelity_audit.md` (F1, F2, F3) first, then two
follow-ons.** Do F1/F2/F3 in that priority. They are the only confirmed real divergences /
missing code left after the catalog PRs merged.

Your lane: reverse-engineering from the deployed binaries. Claude re-verifies each `.md` against
the binary before merge. Rules: cite the instruction ADDRESS for every structural claim; tag
**[B]** (confirmed in deployed disasm) / **[R]** (repo reconstruction, reference only) /
**[partial]** (say why); never fabricate a disc/offset/address. Tooling:
`python tools/sbftool.py func <prog.so> <addr>` + `callers`/`disc`. Binaries:
`evidence/original/{pump,pump_amm,pump_fees,mayhem}/deployed.so`.

## Already covered — do NOT redo (merged)
Account surface + arg-frames + CPI graph (discs verified) + error raise-sites + handler anatomy +
PDA/seeds + source-ref maps + panic-Location recovery + discriminators + gate/event catalogs, for
all 4 programs (`maps/`, `docs/`). pump_fees is behaviorally verified for OUR 19 handlers
(19/19 byte-identical on executed paths, VERIFICATION.md); Shuai-Qing owns the 12 sharing handlers.

---

## F3 (do first) — Mayhem `initialize_mayhem_state` is ABSENT. [fidelity_audit F3, HIGH, OPEN]
Deployed has it (wrapper `0x101de`, parser `0xd25f`, body `0x10527`, disc `9dbd5e485545cc2d`);
the recovered mayhem build does not. It is the CPI target of pump `create_v2` Mayhem mode, so it
blocks F2. Reverse end-to-end: account order (the 10 accounts), arg frame, the `mayhem_state`
account it initializes (disc, field→offset layout, total size, borsh vs zero-copy), every field
write with its source, and every CPI/`invoke_signed` (signer seeds). Then reverse the ~41 other
functions present in deployed but missing/incomplete in the recovered mayhem build (recovered
~461 fns vs deployed 502), prioritising the buy/sell/buy_v2/sell_v2/initialize_global_params reach
set. Output `mayhem_init_state.md` (F3 body + account layout) and `mayhem_missing_fns.md`
(one entry per missing fn with its deployed address).

## F2 (second) — pump `create_v2` Mayhem branch CPI is wrong + second mint missing. [F2, HIGH, PARTIAL]
Wrapper `0x24d15`, execute body `0x3cf8..0x4492`. The binary's Mayhem CPI data is 8 bytes;
recovered-fixes adds args; there is no second `mint_to` into `mayhem_token_vault`; account
list/order is inferred. Reverse the deployed branch end-to-end: exact CPI ordering, the second
mint, and the `initialize_mayhem_state` payload + account order — which MUST match F3 exactly.
Update `create_v2_mayhem.md`, upgrading [partial]/[R] to [B] where the bytes confirm it.

## F1 (third) — pump `admin_cto` guard set/order is a different revision. [F1, HIGH, OPEN]
Wrapper `0x25b40`, execute `0x4542`. Deployed guard set/order differs from the recovered source:
deployed has NO 6088/6092, has EXTRA 6080/6095, and the order is different. Reverse the deployed
`admin_cto` execute path and produce the EXACT ordered guard list (error code -> account/flag
checked -> raise-site address) as the binary runs it. State per code whether it is a recovered
reconstruction error or a deployed-revision difference. Output `admin_cto_guards.md`. Claude will
then diff it and, if it's a recovered bug, write the fix + a differential `admin_cto` harness case.

---

## Follow-on C — pump_fees structural non-correspondence (feeds the byte calibrator)
`docs/bindiff_pump_fees.md` leaves 37 genuinely-unmatched + 59 gated functions in MISSING/EXTRA.
Our 19 handlers are behaviorally byte-identical, so these are SUSPECTED function-boundary /
inlining artifacts, not missing behavior — unproven. For each genuinely-unmatched recovered
address, decide with evidence: (a) genuine missing/extra logic, (b) a recovered split/merge vs
deployed (give the deployed counterpart + boundary), or (c) a callx-only runtime/serde helper.
Output `fees_noncorrespondence.md`. Answers whether `fees_recovered.so` is truly source-complete.

---
Pull the next task when you finish one. Ping the user with each `.md`; Claude re-verifies before
merge. No public PRs to third-party repos.
