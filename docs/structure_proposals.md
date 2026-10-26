> **[Claude verification note — byte-identity tier is speculative]** The structure proposals
> here are HYPOTHESES for closing per-function byte gaps (the Shaw byte-identity end-goal; still
> 0/4 for everyone). They are NOT verified. Caveat on Entry 2 (now resolved): the cited 197/196
> is the pass-index WINDOW count, not one function. It is a 7-insn log prologue at pc 0x1d701
> (byte 0xeb808) + a separate 190-insn body at pc 0x1d709 (byte 0xeb848): 7+190 = 197. The
> recovered side is 7 at 0x13c36 (0x9e1b0) + 189 at 0x13c3e (0x9e1f0): 7+189 = 196. There is no
> ~338-insn body for this handler; a 338 count merges the 190-insn body with the following
> functions (0x1d7cc stub + 0x1d7d4 109-insn body + ...). The ONLY valid test of any proposal is to apply it,
> rebuild with the pinned recipe, and measure whether that function's compiled bytes move toward
> the original (compare.py). Until that build experiment runs, treat every entry as unproven.

# Byte-structure proposal - `pump_amm::update_buyback_config` wrapper

Goal: move the recovered build's compiled bytes toward the deployed bytes for **one** function
that the repo's pass-index marks **not normalized-identical**, with a specific source-structure
change and a measurement plan for Claude (who owns the toolchain).

No build was performed here. Everything below is read-only disassembly + reasoning. Addresses
are virtual byte addresses; `sbftool` "pc" units are `addr/8`.

---

## 1. Function selected

From `repro/pump_amm/formatter-restoration-v144/inventory/after/all-window-dispositions.tsv`
(the pass-index) and `residual-ledger.json.gz`:

| side | window | bytes | pass-index category | pass-index status |
|---|---|---:|---|---|
| deployed (`evidence/original/pump_amm/deployed.so`) | `[0xed660, 0xedcc8)` | 1640 | ambiguous/unattributed | **no normalized match** |
| recovered (`repro/pump_amm/formatter-restoration-main-v144/main/candidate.so`) | `[0x9db50, 0x9e1b0)` | 1632 | source organization/ownership | **no normalized match** |

Attribution (which the pass-index left "ambiguous/unattributed"):

- Dispatcher `amm_handlers.json` maps `update_buyback_config` -> handler pc `0x1dacc`
  = byte `0xed660`, exactly the original window start.
- Isolated prologues are byte-identical in shape and both load the string
  `Instruction: UpdateBuybackConfig` (33/32-byte log; original at `.rodata 0x11bed0`,
  candidate at `0x10cf50`; both `lddw r1, ...; mov r2, 0x20; call <sol_log_>` at
  original `0x1dad1..0x1dad4` / candidate `0x13b6f..0x13b72`).
- Candidate symbol: `_ZN18pump_amm_recovered9__private8__global21update_buyback_config17h6c99136a14975014E`.

Why this one: the original counterpart is unambiguous (dispatch + log string), the two
windows are near the same size, and the normalized diff reduces to **one** instruction - so
the source-structure lever can be isolated instead of guessed.

---

## 2. Observed difference (verified)

Decode both windows with `sbftool.py` (repo: decoder 0-diff vs `llvm-objdump`), then normalize:

- call immediates -> `CALL`;
- rodata `lddw` immediates -> the referenced string / `CONST`;
- branch displacements kept (they shift by 1 when an instruction is added/removed).

Results:

- original: **199 instructions**, `0xed660..0xedcc8` (1640 bytes)
- candidate: **198 instructions**, `0x9db50..0x9e1b0` (1632 bytes)
- normalized similarity ratio `0.942065...`; 270 common-extent raw differing bytes, 8 excess
  bytes; first raw difference at `+0x2c`, last at `+0x65a` (all other raw differences are
  call/rodata/branch immediates that follow from layout).

The **only** instruction-sequence delta is at normalized index 144:

```
original  [144] pc 0x1db62 (byte 0xedb10): mov64 r1, 0x14
          [145] pc 0x1db63 (byte 0xedb18): mov64 r2, r6
          [146] pc 0x1db64 (byte 0xedb20): call <error ctor>
candidate [144] pc 0x13c00 (byte 0x9e000): mov64 r1, r6
          [145] pc 0x13c01 (byte 0x9e008): call <error ctor>
```

Everything else (prologue, account-name/exit calls, branch structure) normalizes. The call
targets differ:

| | original | candidate |
|---|---|---|
| call target | pc `0x109f` (byte `0x84f8`), 79 insns `0x109f..0x10f3`, includes cold/panic blocks at `0x10c3+` | pc `0x1105` (byte `0x8828`), 36-insn symbol `_ZN3std2io5error5Error3new...` (288 bytes, `0x8828..0x8948`) |
| where `0x14` is materialized | **caller** (`0x1db62`), callee receives it in `r1` | **callee** (`0x1124`: `mov64 r1, 0x14`), caller only passes `r1=r6` |

So the delta is not arithmetic/guard code in `update_buyback_config`; it is **which error
constructor is called and whether the `0x14` immediate is an argument or a baked-in
constant**. `0x14` = 20; it is most plausibly the `ErrorKind`/`Custom` discriminant for the
io/borsh error the generated account-exit path is constructing. (I did not fully prove the
semantic identity of the constant; treat it as an uninterpreted immediate.)

---

## 3. Root-cause hypothesis

**H1 (primary): a monomorphization/function-specialization difference, not a handler-body
difference.** The original calls a generic error constructor with the discriminant as an
argument; the candidate calls a leaner, specialized/concrete constructor that has the
discriminant constant-folded into its body. The candidate call target is a different function
(36 insns / 288 bytes vs 79 insns with cold blocks), and it contains
`mov64 r1, 0x14` internally at `0x1124`. The wrapper merely loses the hoisted `mov r1,0x14`
because its callee no longer takes that argument.

This is consistent with:

- the pass-index flagging this window "no normalized match" while another AMM admin wrapper,
  `update_fee_config` (`[0xe2230,0xe2b28)` 2296 / `[0x9d258,0x9db50)` 2296), is
  "normalized correspondence only" - i.e. similar generated-wrapper shape, different
  error-path codegen;
- everything else in this window normalizing.

**H2 (alternative): the two builds instantiate different concrete error types** (e.g.
`std::io::Error::new` vs `borsh::io::Error::new` / a different `borsh`/`anchor-lang`
revision), which selects a different generic instantiation and therefore a different callee
and call ABI. This is a dependency/source-type provenance difference, still visible as the
same one-instruction caller delta.

**H3: LLVM pass configuration.** Function specialisation (IPSCCP/`FunctionSpecialization`)
can clone a generic callee and bake a constant argument in. If the deployed build had it
enabled and the recovery build did not (or vice versa), this exact delta appears with no
source change. This must be ruled out before attributing the delta to source.

These are ranked hypotheses; the experiments below discriminate them.

---

## 4. Proposed source-structure change (in priority order)

### S1 - de-specialise the error constructor at the call site (inline/structure lever)

If the delta is H1/H3, prevent the constant from being sunk into the callee. Introduce an
`#[inline(never)]` shim that keeps the discriminant a runtime value, and route the
account-exit/serialization error through it:

```rust
// shape only; place next to the AccountSerialize/exit helper that produces this error path
#[inline(never)]
fn io_error_with_kind<E>(kind: std::io::ErrorKind, e: E) -> std::io::Error
where
    E: Into<Box<dyn std::error::Error + Send + Sync>>,
{
    // black_box stops IPSCCP/FunctionSpecialization from cloning this fn per constant kind
    std::io::Error::new(std::hint::black_box(kind), e)
}
```

Call it where the generated wrapper currently reaches the io-error constructor, passing the
same kind the original appears to pass (`0x14`). Expected effect: the caller regains
`mov r1, 0x14` before the call (199 instructions) and the callee loses its internal
`mov r1, 0x14`, i.e. the normalized delta goes to zero. If the error is produced inside the
Anchor/borsh derive rather than user code, wrap the account type's
`AccountSerialize::try_serialize`/`AccountDeserialize` mapping in the same shim
(`#[inline(never)]`, kind through `black_box`) so the wrapper cannot inline/specialise it.

Reasoning: the entire delta is "constant argument hoisted to caller vs. sunk into callee".
Forcing a non-inlined, non-constant-propagated call is the minimal structural change that
reproduces the original call shape without touching business logic.

### S2 - align the concrete error type/instantiation

If S1 does not change the call target, the original likely used a different concrete error
type/instantiation. Align the `AccountSerialize`/`AccountDeserialize` error mapping in the
affected account (and the `borsh`/`anchor-lang` versions in `Cargo.lock`) so the same generic
`Error::new` monomorphization is selected. This is a source/dependency provenance change, not
a pump_amm handler change; keep it isolated so whole-file effects are attributable.

### S3 - compiler-provenance control (run in parallel, no source edit)

Rebuild the **unchanged** source with LLVM function specialisation disabled (if the pinned
toolchain exposes the flag, e.g. via `RUSTFLAGS="-C llvm-args=-enable-function-specialization=false"`,
otherwise the equivalent pass-pipeline control for that LLVM revision). If the caller
regains `mov r1, 0x14` and the callee un-specialises, H3 is confirmed and the remaining gap
is compiler/toolchain provenance, not source structure - record it as such and stop editing
pump_amm for this delta.

### Explicitly not proposed

- **Item order**: the prologue, log call, account-name calls, exit call, and branch skeleton
  already match in order; reordering items will not remove the constant-placement delta and
  risks perturbing many other normalized windows.
- **Merging/splitting the handler body**: the body is not where the delta is. The only
  observed delta is the call-site/callee shape of the generated account-exit error path.
- Any padding/byte patching: this is a source hypothesis, not a byte-identity claim.

---

## 5. Measurement plan for Claude (build + verify)

1. Baseline (no change): rebuild, re-run
   `repro/pump_amm/formatter-restoration-v144/inventory/after/all-window-dispositions.tsv`
   generation; confirm current `update_buyback_config` rows are
   `0x9db50..0x9e1b0` = 198 insns / 1632 bytes and "no normalized match".
2. Apply **S1** only. Rebuild. Decode the candidate window and compare with
   `[0xed660,0xedcc8)` using the same normalization:
   - expect 199 instructions;
   - expect the normalized delta at index 144 to be gone;
   - expect the call target to be the generic error constructor (caller passes `r1=0x14`,
     `r2=<ptr>`), not the 36-insn specialized clone.
3. If S1 is neutral, run **S3** on unchanged source and compare the same two points. If S3
   flips it, mark the gap compiler-provenance; do not apply S2 as a source "fix".
4. If S3 is neutral and S1 fails, apply **S2** (error type/dependency alignment) and re-measure.
5. Regression gates for any accepted change:
   - whole-file raw differing bytes must not increase (baseline per pass-12:
     `pump_amm` 670,791 common-extent differing bytes; candidate 1,196,544 bytes);
   - re-run the full AMM differential harness (`scripts/pump_amm_*_differential.py`, 17,462
     comparisons + 35,418 saved signature checks at the current checkpoint);
   - re-run the pass-index and verify no previously `normalized correspondence only` window
     regresses to `no normalized match`;
   - check the shim does not perturb other error-path call sites (it is a global codegen lever).

### Success criterion

This proposal **cannot** claim byte-identity (relocation-patched call/rodata immediates will
still differ). It is successful if:

- `update_buyback_config` moves from **"no normalized match"** to
  **"normalized correspondence only"** (i.e. the one-instruction delta disappears under the
  repo's normalization), **and**
- the raw differing-byte count for the 1640-byte window drops from 270 to only the
  relocation-immediate bytes that normalization ignores, **and**
- no other window regresses and the differential suite still passes.

If those hold, repeat the same constant-placement audit on the other `__global::*` wrappers
that still have "no normalized match" (e.g. `disable`, `update_admin`, `create_pool`,
`set_boost_authority`, `claim_cashback`, `transfer_creator_fees_to_pump*`) - the same
error-path monomorphization pattern may explain several of the 196 remaining
candidate-side "no normalized match" rows.

---

## 6. Evidence index (for the user / Claude)

- Pass-index: `repro/pump_amm/formatter-restoration-v144/inventory/after/all-window-dispositions.tsv`
  rows `original 0xed660 0xedcc8 1640 ambiguous/unattributed no normalized match` and
  `candidate 0x9db50 0x9e1b0 1632 source organization/ownership no normalized match ...update_buyback_config...`.
- Ledger: `.../inventory/after/residual-ledger.json.gz` (same windows; normalization =
  relocation/call immediates only).
- Dispatcher attribution: `D:\dev\pumpfun-re\amm_handlers.json`
  (`update_buyback_config -> 0x1dacc` pc = `0xed660` byte).
- Exact prologue/log strings: deployed `.rodata 0x11bed0`, recovered `0x10cf50`
  (both `Instruction: UpdateBuybackConfig`).
- Delta instructions: original `0x1db62` (`mov r1,0x14`) / `0x1db63` (`mov r2,r6`);
  recovered `0x13c00` (`mov r1,r6`); recovered callee `0x1105` with internal
  `0x1124` (`mov r1,0x14`).
- Raw metric: 1640 vs 1632 bytes, common extent 1632, 270 raw differing common bytes,
  8 excess bytes (first diff +0x2c, last +0x65a).
- Decoder/reproduction: `python sbftool.py dis <so> <pc>`; normalization script logic is
  described in Sec.2 (replace call immediates; classify rodata `lddw`; keep branch offsets).

---

# Entry 2 - `pump_amm::toggle_mayhem_mode` wrapper (same constant-class delta)

The pass-index marks this wrapper "no normalized match" on both sides:

| side | window | bytes | status |
|---|---|---:|---|
| deployed | `[0xeb808, 0xebe60)` | 1624 | no normalized match |
| recovered | `[0x9e1b0, 0x9e800)` | 1616 | no normalized match |

Handler identity: `update`-style admin wrapper; deployed pc `0x1d701` (byte `0xeb808`,
`amm_handlers.json`); recovered symbol
`_ZN18pump_amm_recovered9__private8__global18toggle_mayhem_mode...`; both log
`Instruction: ToggleMayhemMode`.

## Function boundary (resolved, sbftool)

| part | deployed (first..last insn pc; bytes) | recovered (first..last insn pc; bytes) |
|---|---|---|
| log prologue / dispatch stub | `0x1d701`..`0x1d708` (7 insns), `0xeb808..0xeb848` | `0x13c36`..`0x13c3d` (7 insns), `0x9e1b0..0x9e1f0` |
| handler body | `0x1d709`..`0x1d7cb` (190 insns), `0xeb848..0xebe60` | `0x13c3e`..`0x13cff` (189 insns), `0x9e1f0..0x9e800` |
| pass-index window (stub+body) | `0xeb808..0xebe60`, **197 insns** | `0x9e1b0..0x9e800`, **196 insns** |

Ranges are first..last instruction starts; a 16-byte `lddw` occupies a second pc slot that
is not a separate instruction (e.g. `0x1d707` in the deployed prologue, `0x13c3c` in the
recovered prologue). The prologue is 7/7; the delta is entirely in the body (`0x1d725` / `0x13c5a`). The body
is 190 vs 189, NOT 338. `sbftool.func_body(0x1d709)` returns 190 insns ending at `0x1d7cb`;
the next function is a new 7-insn prologue at `0x1d7cc` and a 109-insn body at `0x1d7d4`
(bytes `0xebe60` and `0xebea0`). A 338-insn "body" is those adjacent functions merged,
not this handler.

## Observed delta (normalized)

- deployed **197** window instructions (**7** prologue + **190** body), recovered **196**
  (**7** + **189**); body-only delta is 190 vs 189 (one instruction).
- Normalized similarity `0.95165`; after ignoring rodata/call immediates and the
  branch displacements that shift by the added/removed instruction, the **only**
  instruction-sequence delta is again at the error-path setup:

```
original  [33] pc 0x1d725 (byte 0xeb928): mov64 r1, 0x14
          [34] pc 0x1d726 (byte 0xeb930): mov64 r2, r6
          [35] pc 0x1d727 (byte 0xeb938): call 0x109f
recovered [33] pc 0x13c5a (byte 0x9e2d0): mov64 r1, r6
          [34] pc 0x13c5b (byte 0x9e2d8): call 0x1105
```

The recovered callee `0x1105` materializes `r1 = 0x14` internally, exactly like
`update_buyback_config` (`structure_proposals` Entry 1). All other deltas are rodata
pointers (`0x11ea3e` vs `0x10e345`, `0x122298` vs `0x112cf0`, `0x1b...`/`0x10...`) and
branch offsets shifted by one instruction - i.e. layout, not logic.

## Proposal

This is a **second instance of the same class** as Entry 1: a constant (0x14 = 20) that the
original passes as an argument to the shared error constructor, while the recovered build
specializes the callee and bakes the constant in. Apply the same source-structure lever:

1. **S1 (primary)**: route the account-exit/serialization error mapping through an
   `#[inline(never)]` helper whose `kind` is kept opaque (`black_box`), so the constant is
   materialized at the call site (`mov r1, 0x14; mov r2, r6`) and the specialized clone is
   not selected. Expect 197 window instructions (7 prologue + 190 body; body-only 190/190)
   and the caller-side pair restored.
2. **S3 (parallel, no source edit)**: rebuild unchanged source with LLVM function
   specialization disabled; if the caller regains `mov r1, 0x14`, record the wall as
   compiler provenance rather than source structure.
3. Do **not** touch item order or split the handler body: the prologue/log/try_accounts/exit
   skeleton already normalizes; only the error-path constant placement differs.

## Measurement

Re-run the pass-index for this window; success = `toggle_mayhem_mode` moves from
"no normalized match" to "normalized correspondence only" (window 197/197; body 190/190), with the raw
common-extent differing bytes reduced to relocation-only. Re-run the AMM differential
suite (the behavior is unchanged: same 6043 `MayhemModeInDesiredState` guard, same store
to `mayhem_mode_enabled` at serialized 417). Because this is the same class as Entry 1,
fixing both with one shared helper is preferable; check the other 8-byte-delta wrappers
(`toggle_cashback_enabled`, `update_max_*`, `reset_*`, `set_boost_authority` if its delta
reduces to the same pattern) for the same error-path clone before editing each one.

## Evidence index

- `repro/pump_amm/formatter-restoration-v144/inventory/after/all-window-dispositions.tsv`
  rows `original 0xeb808 0xebe60 1624 ... no normalized match` and
  `candidate 0x9e1b0 0x9e800 1616 ... no normalized match ... toggle_mayhem_mode`.
- `residual-ledger.json.gz` same windows; normalization = relocation/call immediates only.
- Dispatcher: `toggle_mayhem_mode` handler pc `0x1d701` (byte `0xeb808`).
- Delta: original `0x1d725` (`mov r1,0x14`) / `0x1d726` (`mov r2,r6`) / call `0x109f`;
  recovered `0x13c5a` (`mov r1,r6`) / call `0x1105`; callee `0x1105` has `mov r1,0x14` at
  `0x1124`.
- Raw metric: 1624 vs 1616 bytes, 8 excess bytes (one instruction).
