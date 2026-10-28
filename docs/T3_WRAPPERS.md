# T3 — Reconstruct pump's Anchor wrappers to byte-exact

> **Goal.** Close the pump Anchor-generated wrapper windows (`try_accounts` / `exit` /
> dispatch / `try_deserialize`) that are still raw-fail or unmatched, by reconstructing the
> `#[derive(Accounts)]` structs — never by editing the ELF. These are the biggest raw gaters
> on pump. lalalune proved the class is reconstructable by finishing Fees at whole-ELF
> (585/585). **Method: [`WRAPPER_RECONSTRUCTION.md`](WRAPPER_RECONSTRUCTION.md). Read it first.**
>
> **Base:** pump profile **s7p = 802 / 161** (after the merged chain #22–#32). Target to pass:
> lalalune Round-37 **823 / 203**. **Tool:** `tools/drift_solver.py`.

## Prerequisite — the vendored Anchor macro (do this first)

pump currently pulls `anchor-attribute-program 0.31.2` from **crates.io**. The recipe requires
the **vendored** macro with `#[used]` (stock crates.io does not reproduce wrapper bytes). We
already have the right version from the Fees work: `anchor-attribute-program 0.31.2` with
`#[used]` at `/work/next637/vendor/used-public`.

1. Override the transitive dep in the pump workspace `Cargo.toml`:
   `[patch.crates-io] anchor-attribute-program = { path = "…/used-public" }` (keep 0.31.2 so it
   resolves). Add `--gc-sections` to the link step.
2. Rebuild with the s7p recipe (macOS-host rustc shim + `ordered.ld` + platform-tools v1.44,
   `--locked --offline`, `-Zremap-cwd-prefix=`).
3. **Measure** — confirm the base still reproduces (or moves toward deployed on wrappers) with
   `lost[] = []`. If it regresses, stop and report; do not proceed on a broken base.
   *(A measured "wire vendored macro" experiment is in flight — coordinate: if its packet
   `research/chantier-anchor-vendored/` lands, build on it.)*

## Targets (confirm current set with the solver)

Run `python3 tools/drift_solver.py <deployed.so> <candidate-symbols.so>` on the current 802/161
build and take the wrapper windows from the ranked spoiler list. The known wrapper families
(addresses/sizes shift after each merge — **trust the solver, not these**):

| Family | Window(s) | Kind |
|---|---|---|
| `Create::try_accounts` | ~6672 B + ~6464 B | parser |
| `Initialize::try_accounts` (global_init) | ~5896 B | parser |
| `LegacyBuy::try_accounts` | ~8128 B | parser |
| `Global::try_deserialize` / `IdlAccount::try_deserialize` | ~728 B | deserialize/discriminator |
| each struct's generated `exit` + dispatch wrapper | — | writeback/dispatch |

## Per-wrapper recipe (one sub-claim per instruction)

For each target wrapper:

1. **Disassemble** the deployed window (`tools/sbftool.py func <deployed.so> <addr>`) and the
   candidate's matching window. Diff the two bodies.
2. **Attribute every mismatch** to exactly one of:
   - **field ORDER** — the generated parser loads accounts in declaration order (seen as
     `[r7+872]`, `[r7+88]`, … offsets). Reorder the struct fields until the load sequence matches.
   - **field TYPE** — `Program<'info,T>` (re-emits the unconditional program-ID check + canonical
     parser), `Account` vs `InterfaceAccount` vs `UncheckedAccount` vs **owned `AccountInfo`**
     (owned `AccountInfo` shifts the generated `exit` struct offsets — the Fees `event_authority`
     trick). Pick the type that reproduces the deployed layout/validation.
   - **constraint** — `seeds`/`bump`, `has_one`, `token::mint`/`token::authority`, explicit owner,
     `associated_token::` **with the real ATA + mint constants**, `init`/`close`/`mut`. Each
     constraint is a block in `try_accounts`; match them one-for-one to the deployed branches.
   - **macro version** — covered by the vendored 0.31.2 `#[used]` macro (prerequisite).
3. **Change exactly that construct** in the `#[derive(Accounts)]` struct. Do not hand-edit the ELF.
4. **`try_deserialize` / discriminator**: match the declared discriminator and the standard
   `#[account]`/`#[event]` path; ensure the event serialization is **inlined** so no extra
   candidate-only `<T as Event>::data` window is emitted (`--gc-sections` drops it when uncalled).
5. **Residual handler-body divergence** (after the wrapper matches): if a body still diverges by
   register allocation, apply the **noalias fix** — pass `&UncheckedAccount` (not `&AccountInfo`)
   into helpers, or `let x: &AccountInfo = x.as_ref();` to drop the noalias scope.
6. **Rebuild + MEASURE** (`drift_solver.py` + the window metric): matched (vs 802), raw (vs 161),
   `lost[]` on BOTH sets. Verify first with `llc` on the IR when iterating is cheaper than a build.

## Discipline (hard)

- **Reconstruct the struct, never the ELF.** No assembly, no byte patching, no padding bytes.
- **Faithful to deployed only** — no check added/removed, no behavior change. Constraints must
  match the deployed validation one-for-one.
- **Measure every attempt.** Keep only if raw↑ (or matched↑) with `lost[] = []` on both sets and
  normalized not below 802. Revert exactly otherwise.
- **One sub-claim = one instruction = one PR = one packet** `research/chantier-T3-<instr>/`
  (source.patch + ordered-ld.patch if layout changed + measure JSON + RESULT.md citing
  before/after + the deployed window addresses). No `.so`, no secrets. PR-only.

## Deliverable per sub-claim

The reconstructed `#[derive(Accounts)]` struct diff, the measured matched/raw before→after, the
`lost[]` proof (empty), and the deployed window address(es) it matched. Stack sub-claims in order
like #22–#32 (linear, each on the previous) so the cumulative is always measurable.
