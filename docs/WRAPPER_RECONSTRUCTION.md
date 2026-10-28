# Fees whole-ELF (585/585) method — extracted from lalalune/pumpfun-source

Source: upstream `lalalune/pumpfun-source` `main` @ `07fd164` (28 Oct 2026). MIT,
public research. Credit: lalalune (fees100 Claude lanes + Codex Crank research).
Read-only study; nothing built or committed.

Upstream files read (all via `git show origin/main:<path>`):
- `README.md` (Fees row: 585/585, raw 585, **Whole ELF equal: Yes**)
- `docs/BYTE-IDENTITY-PROGRESS.md`
- `research/claude-fees100-crank-donation-20261027/README.md` + `source.patch`  (the last function → 585/585)
- `research/claude-fees100-whole-elf-endstate-20261027/README.md`  (the beyond-source layout proof)
- `research/claude-fees100-create-donation-20261027/README.md`  (handler-codegen recipe)
Local checkpoint corroboration (older 579–582 frontier, same lanes):
- `pumpre/repo/research/fees-crank-event-ownership/README.md`  (the exit/dispatch WRAPPER recovery — 952 B / 840 B)
- `pumpre/repo/research/fees-crank-safe-context-source/README.md`
- `pumpre/repo/research/fees-wrapper-codegen-controls/README.md`  (codegen-unit controls rejected)

---

## (a) What the Crank divergence was, and the exact change that closed it

Crank is **four** separate compiled windows, and they diverged for **two different
reasons**. Our "whole-ELF, not source-editable" verdict conflated them; both are
in fact source-reconstructable.

### A1. The Anchor-generated WRAPPERs (`exit` + dispatch) — the 952 B / 840 B pair
These are the windows we saw as deployed 952 B vs our candidate 840 B.
- `CrankDonationFeePda::exit` @ 424,824 = **952 B** (Anchor-generated account-writeback/exit)
- `__global::crank_donation_fee_pda` dispatch wrapper @ 656,832 = **840 B**

Divergence: the generated `exit` loaded two account fields at the **wrong struct
offsets** — 624 and 680 — where the original used **664 and 720**. Pure codegen
layout drift, no business logic.

Exact source change that closed it (`fees-crank-event-ownership`): declare
`event_authority` in the `#[derive(Accounts)] CrankDonationFeePda` struct as an
**owned `AccountInfo`** instead of the borrowed/leaner form. That one field-type
change shifts the struct layout so Anchor's generated `exit` loads fields at
664/720 — byte-matching the original. The owner bytes and the three field labels
(`donation_fee_pda`, `donation_fee_pda_ata`, `quote_mint`) then also match. After
this the dispatch wrapper matched as a complete normalized body too.

Note: `fees-wrapper-codegen-controls` separately proved the divergence is **NOT**
fixed by root `-Ccodegen-units` substitution (1/2/4/8/16 all fail) — it is the
Accounts-struct field type, not a compiler flag.

### A2. The business HANDLER body @ 147,944 = 15,976 B — the last function (→585/585)
This is `#[program] crank_donation_fee_pda`'s own logic (1,950 instructions). It
was the single remaining unmatched window on the 584-function parent. Its
residual was **register allocation** around the SyncNative `AccountMeta`/`pack()`/
`AccountInfo`-clone region, and it was closed by a **source form, not a flag**:

- Root cause: if the inlined helper takes `rent: &AccountInfo`, that parameter is
  `noalias readonly`. LLVM attaches scoped-noalias metadata → GVN reuses the
  `rent.key` pointer loaded for the `AccountMeta` (before `pack`) inside the
  account-info clone (after `pack`). Wrong spill/reload shape.
- The original instead **reloads `rent.key` after `pack`** (`ldxdw r3,[r6+0]`),
  i.e. its `rent` AccountInfo was *not* behind a noalias parameter.
- Fix: pass the Anchor wrapper **`&UncheckedAccount`** into the helper and load the
  `AccountInfo` from it (carries no noalias scope). Equivalent one-liner:
  `let rent: &AccountInfo<'info> = rent.as_ref();`. Proven first with `llc` on the
  candidate IR, then by a real build.
- Helper is a **plain `fn` with no attributes**:
  `fn sync_native_excess<'info>(donation: &AccountInfo<'info>, ata: &mut Account<'info, TokenAccount>, rent: &UncheckedAccount<'info>) -> Result<Option<u64>>`
  — reads rent, `minimum_balance(218)`, saturating excess, moves lamports, invokes
  SyncNative with three metas via `TokenInstruction::SyncNative.pack()`, reloads
  the token account, returns `Ok(None)` + the second `msg!("Nothing to donate")`.
- Handler split into native arm (`match sync_native_excess(...)? { Some(a)=>a, None=>return Ok(()) }`)
  and non-native arm (keeps its own `msg!` — the original's second log site).

Takeaway: the wrapper (A1) is an **Accounts-struct layout** problem; the handler
(A2) is an **LLVM-aliasing-via-wrapper-type** regalloc problem. Both are source.

---

## (b) Generic Accounts-struct reconstruction recipe
"Given a deployed Anchor wrapper window (`try_accounts` / `exit` / dispatch /
`try_deserialize`) that diverges, regenerate it byte-exact."

The generated wrapper is a pure function of (Anchor macro version) × (the
`#[derive(Accounts)]` struct) × (field types) × (field ORDER) × (constraints).
Reconstruct these, do not hand-edit the ELF:

1. **Pin the macro.** Anchor Lang/SPL **0.32.1**, and **vendor the proc-macro
   crate** (`anchor-attribute-program`, with `#[used]`) at the exact path the
   build expects. Different Anchor patch levels emit different wrapper bytes — the
   vendored macro is what makes codegen reproducible. This is a hard prerequisite.
2. **Field ORDER = load order.** The generated parser loads account wrappers in
   declaration order (seen as `[r7+872]`, `[r7+88]`, `[r7+272]` …). Reorder struct
   fields until the generated load sequence matches the disassembly.
3. **Field TYPE controls both layout and validation codegen.** Pick per field:
   - `Program<'info, T>` / standard **Program account syntax** → re-emits the
     unconditional program-ID check + canonical parser layout (this is literally
     how Mayhem recovered all six trade parsers + Burn: "restoring the
     unconditional program-ID check in an authenticated Anchor source copy permits
     standard Program account syntax and reproduces the original generated parser").
   - `Account<'info, T>` vs `InterfaceAccount` vs `UncheckedAccount` vs owned
     `AccountInfo` → each yields a different struct offset layout and a different
     generated `exit`. (A1: owned `AccountInfo` for `event_authority` shifted
     exit offsets 624/680 → 664/720.)
4. **Constraints = validation body.** `seeds`/`bump`, `has_one`, `token::mint`,
   `token::authority`/explicit owner constraint, `associated_token::` with the
   **native ATA constants**, `init`/`close`, `mut`. The Fees sharing parsers
   (484816/16112, 502096/16880) were recovered specifically "through the native
   ATA constants and explicit quote-mint owner constraint." Each constraint is a
   block in `try_accounts`; match them one-for-one to the original's branches.
5. **`try_deserialize` / `IdlAccount` / discriminator.** Use the declared
   discriminator and the standard `#[account]`/`#[event]` paths; event
   serialization must be **inlined** (declare so the extra
   `<T as Event>::data` helper is NOT emitted — otherwise you get an extra
   candidate-only window and `--gc-sections` is what removes it when uncalled).
6. **Workflow:** diff the generated wrapper against the disassembly; attribute each
   mismatch to one of {order, type, constraint, macro version}; change exactly that
   construct; rebuild with the pinned toolchain; re-diff. `codegen-units` and other
   compiler flags are NOT valid knobs here (proven by wrapper-codegen-controls).
7. **Handler bodies (not wrappers)** are controlled by source *form*, measured
   from IR: helper boundaries drive **inlining** (LLVM cold-callsite inliner,
   block-freq <2%, threshold 45); `if`-chains drive **block order** (SBF
   `analyzeBranch` can't analyze cond branches → block order follows IR order);
   tuple bindings + named slice locals drive **frame-slot** assignment (SROA /
   StackColoring → fixed offsets like -96/-128/-784); the **wrapper type passed
   into a helper** drives aliasing/regalloc (the A2 noalias fix).

---

## (c) Mapping to OUR pump T3 targets
Our T3 targets are the pump (not fees) Anchor wrappers we had filed "whole-ELF,
not source-editable." The Fees result refutes that class — all are reconstructable:

- **`LegacyBuy::try_accounts`, `Create::try_accounts`, `Initialize::try_accounts`**
  → direct analog of Fees' `CrankDonationFeePda::try_accounts` (408,640) and the
  Mayhem trade parsers. Reconstruct each `#[derive(Accounts)]` struct per recipe
  (b): fix field ORDER against the load sequence, pick field TYPES (Program syntax
  where a program-ID check exists; owned `AccountInfo` where exit offsets are off),
  encode every constraint (`seeds`/`bump`/`has_one`/`token::`/`associated_token::`
  with the real mint/ATA constants). Rebuild with vendored Anchor 0.32.1.
- **`IdlAccount` / `Global::try_deserialize`** → analog of the discriminator/`exit`
  recovery (424,824) and event-inlining. Match the declared discriminator and the
  `#[account]` deserialize path; ensure no extra `try_serialize`/`data` helper is
  emitted (inline it) so window count matches.
- **Any pump handler body that then still diverges** → use recipe (b.7): check for
  the `&AccountInfo` noalias trap (swap to `&UncheckedAccount` / `.as_ref()`),
  helper-boundary inlining, `if`-chain block order, and tuple/slice frame slots.
- **First action before any of this:** stand up the pinned build (Linux
  platform-tools v1.44, the exact `rustc` hash, vendored Anchor 0.32.1 macro with
  `#[used]`, `cargo rustc --release --locked --offline --target sbpf-solana-solana`,
  `-Zremap-cwd-prefix=` + `--remap-path-prefix`), because the wrapper bytes only
  reproduce under that toolchain.

---

## (d) Did their Fees approach need anything beyond source? YES.
Source reconstruction gets you byte-equal **function bodies**; **whole-ELF
identity needs a layout layer** (proven in `claude-fees100-whole-elf-endstate`):

1. **Custom linker script `layout/ordered.ld`** applied through a **linker
   wrapper** around `rust-lld`. It fixes the order/slot of every function window
   so the `.text` layout matches the original.
2. **`tools/relayout.py`** — regenerates `ordered.ld` after ANY source change
   (binds input sections by name, content identity, call/pointer-graph color;
   each matched function keeps its window slot; a newly matched body moves into its
   original window; vanished sections dropped). Every source edit requires a
   re-bind.
3. **Vendored `anchor-attribute-program` with `#[used]`** (part of `source/`, not
   stock crates.io) — makes wrapper codegen + a referenced symbol survive.
4. **Pinned toolchain, exactly:** Anza platform-tools **v1.44**
   (`sbpf-solana-solana`), a specific `rustc` SHA, Anchor Lang/SPL **0.32.1**,
   strip with pinned **`llvm-objcopy --strip-all`** (v1.52; v1.48 libs elsewhere),
   `CARGO_NET_OFFLINE=true`, `--locked --offline`, authenticated vendored dep cache,
   `RUSTFLAGS=-Zremap-cwd-prefix=` + explicit `--remap-path-prefix` for the math
   subcrate.
5. **Source line-number preservation.** The `source.patch` pads with **blank lines**
   so every statement keeps its original source line (e.g. require! sites on
   148/152/156/…). Line numbers feed `.rodata` Source/Location records and affect
   codegen, so they are load-bearing, not cosmetic.
6. **`--gc-sections`** removes any extra candidate-only helper (e.g. the un-inlined
   `Event::data`) once nothing calls it — so the compiled-window count equals the
   original's 585.

What they did **NOT** use (explicitly, in every packet): no assembly, no captured
instruction fragments, no padding bytes, no post-link binary rewriting, no
output-byte patching. Everything is ordinary safe Rust + the layout recipe +
pinned toolchain. The final stripped ELF (873,256 B meaningful; remaining 75,688 B
of the capture are zero loader allocation) is byte-identical; two independent
builds reproduced the same hash (`5b6ceda5…`).

---

## One-line bottom line
The Anchor `#[derive(Accounts)]` wrapper IS source-editable: its bytes are a
deterministic function of macro-version × field-order × field-type × constraints.
Reconstruct the struct (not the ELF), pin Anchor 0.32.1 (vendored macro), and wrap
`rust-lld` with `ordered.ld`/`relayout.py` for whole-ELF identity. The two tricks
that unlock it: (1) owned `AccountInfo` fields to move generated `exit`/parser
offsets; (2) `&UncheckedAccount` (not `&AccountInfo`) into helpers to kill the
noalias regalloc divergence in handler bodies.
