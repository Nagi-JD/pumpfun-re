# The whole-ELF / raw-byte frontier — root-cause analysis

> **Status (27 Oct 2026).** Per-site window reconstruction is at its ceiling on all four
> core programs. The remaining gap to byte-for-byte identity is the **whole-ELF / raw**
> problem. This note records what that gap *is*, the exact root cause we traced, and every
> cheap lever that was **measured and ruled out** — so nobody re-burns effort on a dead path.

## The two metrics

- **Normalized match** — a function has the same *form* (instructions, with addresses and
  relocations masked). We lead here: Pump 786, PumpSwap 681.
- **Raw byte-exact** — a function is *byte-identical*, addresses included. Capped at Pump 137,
  PumpSwap 148, Fees 200. This is where the wall is.

A raw-fail window whose only byte differences are the imm32 of a relative `call` is
"position-drifted": its callee sits at a different **relative offset** than in the deployed
binary. A function's position is the **cumulative sum of the sizes of every function before
it**, so you cannot place one callee at its deployed offset by reordering — the whole prefix
must match. This is the structural core of the wall.

## Measured potential (drift solver)

For each matched pair we know the deployed order and each function's size. Define
`Δ_interval = size_candidate − size_deployed` per interval between matched functions, and
`Δ_call = Σ Δ_interval` between a call's caller and callee. A window is raw-able **iff all its
`Δ_call = 0`.**

On pump s7clean: **238** raw-fail windows have call-only differences → raw potential
**137 → 375** *if* their drift were zeroed. But the drift is gated by functions we do not
control per-site (see root cause), so the 238 is not cheaply reachable.

## Root cause (pump)

The first `Δ ≠ 0` (the drift root) is **`anchor_lang::error::Error::with_values`**:

| symbol | size | call-sites |
|---|---:|---|
| `with_values17h5fec0328…` @ 0x11b0 | 1336 B | 14 (handlers/legacy/init) |
| `with_values17h95410eb0…` @ 0x1c40 | 1336 B | 22 (set_params/buy_v2/sell_v2/trade) |
| `with_values17h970a193a…` @ 0x2178 | 1336 B | 4 (cluster 0x15e748) |

The deployed binary has **one** `with_values` (0x11b0, same 1336 B body). Our build emits
**three** distinct monomorphizations (+2672 B), which shifts everything after them and breaks
the raw offsets of all cross-root calls. The per-site `error!` closures we place to win
*normalized* windows are a likely source of the extra instantiations — so on pump,
**normalized and raw are partially in tension**: the form that matches the window costs the
layout.

## Levers measured and ruled out

| Lever | Result |
|---|---|
| Reorder a 118-function size-identical run to deployed internal order (`ordered.ld`) | raw **137 → 128** (regressed); position is the cumulative size sum, order alone cannot place a callee |
| `-C passes=mergefunc` (LLVM MergeFunctions) | no change (782/137); the three `with_values` bodies are **not** bitwise-identical, so they do not merge |
| `codegen-units=1` | already the s7clean config |
| `-Z share-generics=on` | catastrophic (matched 428 / raw 105); blows up the whole layout, does not cleanly collapse the copies |

Also ruled out as source-editable on **Fees**: the 3 hard windows are not per-site —
`sweep_buyback` (120816) is a register-allocation / OK-vs-err arm coin-flip under equal
pressure (8 measured source reformulations, closest left +3 insns); `crank_donation` (147944)
and `create_donation` (163920) diverge in **Anchor-generated wrapper codegen** (constant
stores that are opaque internal discriminators, not attributable to any `#[derive(Accounts)]`
field).

## What byte-for-byte would take

Byte-for-byte identity **is reachable** — the Fees checkpoint is an existence proof (its
`symbols.so` is sha256-identical to the upstream qualified artifact, wrappers and monomorphs
included) *because its source reconstruction is complete*. Closing pump's raw gap is therefore
not a flag or a reorder but **completing the source-structure reconstruction**, drift-source by
drift-source, each measured:

1. **`with_values` root** — restructure the error sites to emit **one** instantiation (as
   deployed) without losing the 786 normalized matches.
2. **Anchor wrappers** — reconstruct the exact `#[derive(Accounts)]` structs so Anchor
   regenerates the exact wrapper bodies.
3. **Data / reloc layout** — reproduce the exact order of strings, constants, and error tables
   (the `lddw` targets).

This is a multi-session reconstruction project, it risks the normalized lead (it touches the
very code that produces it), and nothing guarantees 100% (some wrapper codegen may not be
inferable from the binary). It is the only path left; there is no cheap one. **Do not
re-attempt order-only reorder or build-flag collapses for raw — all measured dead.**
