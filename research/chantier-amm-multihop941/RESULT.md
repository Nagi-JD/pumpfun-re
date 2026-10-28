# AMM multi_hop 941 — measured close on our 701/167 master (2026-10-28)

> **Nature.** BUILD + MEASURE on OUR harness (WSL, native `cargo rustc`
> platform-tools v1.44 + `r34_r2.remap`, no `cargo-build-sbf`). Measured with
> `ammresearch/tools/measure.py` vs `evidence/original/pump_amm/deployed.so`,
> diffed with `chantier-matched/lost.py`. Source/link reconstruction only; the
> deployed `.so` is never a build input; no file/line macro is hardcoded.
>
> **Credit.** Closing insight: PR #87 (`cerapmen7`, `research/amm-multihop-941/`).
> Source oracle lalalune/pumpfun-source (MIT).

## Result (measured)

| build | matched / 785 | raw | Δ | lost |
|---|---:|---:|---:|---|
| btree baseline (clean, dedicated target dir) | 701 | 148 | — | — |
| **+ reline941 (this patch)** | **702** | 148 | **+1** | GAIN `0xb92c8`; LOST none → **CLEAN** |
| btree baseline under PR #88 layout layer | 701 | 167 | — | — |
| **+ reline941 under PR #88 layout layer** | **702** | **167** | +1 | GAIN `0xb92c8`; LOST none → **CLEAN** |

```
matched base 701 new 702 delta 1 ; raw 148 -> 148
GAIN matched: ['0xb92c8'] ; LOST matched: [] ; LOST raw: [] -> CLEAN
```

## The window

`0xb92c8` (idx 0x17259–0x17299, ~520 B) is the outlined cold `Overflow` (Anchor
6023) error arm at `instructions/swap/multi_hop_swap.rs:941` — a byte-twin (up to
relocations) of the already-matched 636 arm at `0x44cc8`, differing only in the
baked line constant (`0x3ad`=941 vs `0x27c`=636). The signature includes that line
constant, so matching it needs an `error!(PumpAmmError::Overflow)` on source line
941 that LLVM outlines like the existing five arms (579/586/636/671/718). The arm
is caller-independent — any Overflow site relined to 941 produces it.

## The change (`source.patch`, `reline941.py`)

Rewrite the `output` computation's
`total_quote.checked_sub(quote_transfer_fee).ok_or(PumpAmmError::Overflow)?`
to `...ok_or_else(|| error!(PumpAmmError::Overflow))?` and blank-line-pad the
closure so `error!` lands on source line 941. Behavior-preserving (same check,
same `Overflow`; `error!` only attaches the `Location` — the d1/g3 technique).
Lines 1–718 stay byte-identical, so the 579/586/636/671/718 arms are untouched;
block-2 stays `super::checked_add3`, so the g3 windows `0x3a398` and `0xb3460`
are preserved (confirmed: `lost[]==[]`).

Our built `.so` emits exactly one arm with the 941 constant (disasm):
`stw [r10-0x78],0x1787` (6023), `stw [r10-0xf8],0x3ad` (941),
`stdw [r10-0x100],0x39` (len 57) — byte-identical in form to deployed
idx 0x17259–0x17299, differing only in masked relocation addresses.

## Note on PR #87's form

PR #87's published patch (block-2 inline chain → `expected_destination`) is clean
on u2 (657→658) but does **not** stack on our 701 tree: our block-2 was already
extracted to `super::checked_add3` by the g3 PR, so adopting PR #87's form removes
`checked_add3`'s sole caller and regresses `0x3a398` + `0xb3460` (net 701→700).
Full integration analysis + measurements in
`research/chantier-amm-mh941-integrate/`. This packet is the g3-compatible close.

## Reproduce

```sh
bash ~/build_btree_clean.sh                     # 701/148
patch -p1 -d <btree> < source.patch             # reline the output Overflow to 941
bash mb.sh reline941                            # 702/148, lost[]==[]
bash build_amm_layout.sh                        # 702/167 under PR #88 layout, lost[]==[]
```

*No `.so`, no secrets. Local packet — not pushed.*
