# DeepSeek — task set 5 (2026-10-26). While Cédric finishes the pump_fees sharing lot.

Your lane: **reverse-engineering / analysis from the deployed binaries**. Claude's lane:
build + differential harness + fuzz, and re-verify your deliverables against the binary
before anything is trusted. Hand each deliverable back to the user as a `.md`/`.json`.

## Ground rules (every task)
- Binary-grounded: cite the instruction ADDRESS for every structural claim.
- Tag each claim **[B]** = confirmed in the deployed disassembly, **[R]** = repo reconstruction
  (reference only), **[partial]** = inconclusive (say why).
- NEVER fabricate a discriminator, offset, address, or a byte-identity/behavioral claim.
- Tooling: `python tools/sbftool.py func <prog.so> <addr>` (disasm), `callers`, `disc`.
  Binaries: `evidence/original/{pump,pump_amm,pump_fees,mayhem}/deployed.so`.

## Already covered — do NOT redo (merged into the repo)
Account surface + arg-frames (all 4 programs), CPI graph (23 edges, discs verified),
error raise-sites, handler anatomy, PDA/seed catalog, source-reference maps, panic-Location
source-tree recovery, discriminators, gate catalogs, event layouts. See `maps/` + `docs/`.
pump_fees behavioral verification is DONE for our 19 handlers (19/19 byte-identical on executed
paths, see VERIFICATION.md); Cédric owns the 12 sharing/social/donation handlers.

---

## TIER A — Mayhem reconstruction (HIGHEST VALUE — the one real missing-code gap)

The recovered `mayhem` binary is INCOMPLETE: ~461 fns / 71,875 insns vs deployed 502 / 83,947
(~41 fns / ~12k insns short), and the single most important handler —
**`initialize_mayhem_state` (disc `9dbd5e485545cc2d`)** — is ABSENT entirely. This is the CPI
target of pump `create_v2` in mayhem mode, so nothing downstream can be verified until it exists.

**A1. `initialize_mayhem_state` full body.** Reverse the deployed handler end-to-end: account
order (10 accounts per the create_v2 CPI), arg frame, the `mayhem_state` account it initializes
(discriminator, field→offset layout, total size), every field write with its source, and the
exact CPI/`invoke_signed` calls it makes (signer seeds). Output `mayhem_init_state.md`.

**A2. The ~41 missing function bodies.** Diff the deployed mayhem function set against the
recovered one (addresses), list every function present in deployed but missing/incomplete in the
reconstruction, and reverse each body (signature + instruction-grounded pseudo-Rust). Prioritise
anything on the `buy` / `sell` / `buy_v2` / `sell_v2` / `initialize_global_params` reach set.
Output `mayhem_missing_fns.md`, one entry per function with its deployed address.

**A3. `GlobalParams` + `mayhem_state` account layouts.** Field→byte-offset tables as the program
READS them (note borsh vs zero-copy), 8-byte discriminators, total sizes, with the load/store
sites cited. Output `mayhem_account_layouts.md`.

---

## TIER B — pump create_v2 mayhem branch (pairs with Tier A)

**B1. `create_v2` is_mayhem_mode = true, full flow.** `docs/create_v2_mayhem.md` has a spec but
the CPI ordering / second `mint_to` were soft. Reverse the deployed pump `create_v2` mayhem
branch end-to-end: the exact `mint_to` into the mayhem token vault, the ordering of every CPI,
and the `initialize_mayhem_state` CPI payload + account order (must match Tier A1 exactly).
Update `create_v2_mayhem.md`, upgrading every [partial]/[R] to [B] where the bytes confirm it.

---

## TIER C — pump_fees structural non-correspondence (feeds the byte calibrator)

The tightened binary-divergence report (`docs/bindiff_pump_fees.md`) leaves **37 genuinely-
unmatched + 59 gated-for-review** functions in MISSING/EXTRA — recovered functions with no clean
deployed twin. Our 19 handlers are behaviorally byte-identical, so these are suspected
function-boundary / inlining artifacts, NOT missing behavior — but that is unproven.

**C1. Classify the 37 genuinely-unmatched fns.** For each (recovered address from
`bindiff_pump_fees.md`), decide with evidence: (a) genuine missing/extra logic, (b) a
function the recovered build SPLIT or MERGED vs deployed (give the deployed counterpart
address + the split/merge boundary), or (c) a shared runtime/serde helper reached only by
`callx`. Output `fees_noncorrespondence.md`. This tells us whether `fees_recovered.so` is truly
source-complete or just structured differently — the question that gates byte-to-byte calibration.

---

Pull the next open task when you finish one. Ping the user with each `.md`; Claude re-verifies
against the binary before merge. No public PRs to third-party repos.
