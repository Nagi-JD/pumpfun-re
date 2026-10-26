# Byte-identity experiment #01 — pump_amm::toggle_mayhem_mode (S1 shim)

Verdict: **NO CHANGE toward target; marginally worse for whole-binary identity.** S1-class
source edits cannot close this delta. Experiment run in a copy; verified artifacts untouched
(baseline copy rebuilt the verified amm_recovered.so byte-for-byte).

## The one-instruction delta
- Deployed body @0x1d709 = 190 insns; recovered body = 189. The single structural diff:
  - Deployed @0x1d723: `mov r1,r6; call <X>; mov r1,0x14; mov r2,r6; call 0x109f` — constant
    `0x14` materialized AT THE CALL SITE, passed to a generic 2-arg builder.
  - Recovered: `mov r1,r6; call <Y>; mov r1,r6; call 0x1147` — callee `0x1147` BAKES `0x14`
    internally (1-arg). Rest = call-target addresses + two off-by-one branch ripples.

## Why S1 cannot close it (the real finding)
- `0x14` is NOT the error code (MayhemModeInDesiredState = 0x2b). It is a shared Anchor-internal
  constant; helper `0x1147` has **13 callers** and bakes `0x14` for all of them.
- The measured "body" is the Anchor `__global` TRAMPOLINE (account deserialize/Drop/serialize),
  not the user handler. The `require_neq!` the S1 shim edits lives in a DIFFERENT user function
  outside the measured window — so S1 is structurally incapable of moving the byte (measured: no
  change; +1 function from the shim → slightly worse).
- The delta is a WHOLE-PROGRAM function-specialization: the deployed compiler cloned a generic
  2-arg builder into a 1-arg clone (`0x1147`) baking the constant, shared across 13 sites. That
  is a global codegen/MIR-inlining/cloning decision, NOT reachable from a local source edit.

## Takeaway for the byte-identity goal
This class of byte gap is driven by the COMPILER's global monomorphization/cloning decisions,
not by local source structure. Local per-function structure proposals (T11 class) cannot force
it. Closing it would require matching the compiler's global specialization behavior (codegen
flags / cloning thresholds / exact toolchain) — which is exactly the lost-provenance wall behind
the 0/4 status. Measured, not asserted.
