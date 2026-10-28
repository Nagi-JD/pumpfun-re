# chantier-fees whole-ELF: `create_donation_fee_pda::create` handler body, window 163920 matched

Refs the Fees whole-ELF frontier. Second packet of the three-window Fees
close-out. Stacks on `chantier-fees-wholeelf-147944` (window 147944).

## What the deployed program does

The deployed Fees program has a `create_donation_fee_pda::create` handler window
at **163920 (1,641 instructions / 13,800 B)**. The candidate body was ~318
instructions short of the deployed body and also emitted one extra
candidate-only window
(`<DonationFeePdaCreated as anchor_lang::Event>::data`, 648 B), so the candidate
had 586 compiled windows vs the deployed 585.

The deployed body keeps the creator / quote-mint resolution and the
Sharing-config checks in a separate validation path, so the handler's event
emission stays on a warm path and LLVM's cold-callsite inliner inlines
`Event::data`, `from_iter`, `AccountInfo::clone` and `exchange_malloc` there.
`if is_graduated(..)` fixes block order; a tuple binding places `creator`/
`quote_mint` at the deployed frame slots; a named slice local keeps the
Pool-deserialize slice in its own slot.

## Change

`source.patch` (one file, applies with `patch -p1`):
`programs/pump-fees/src/instructions/fee_sharing/create_donation_fee_pda.rs`.

- Add `fn is_graduated(curve: &BondingCurve) -> bool` (the four reserve tests).
- Move creator/quote-mint resolution + Sharing-config checks into
  `fn get_creator_and_quote_mint(bonding_curve, pool, payer, base_mint, sharing_config) -> Result<(Pubkey, Pubkey)>`;
  the Sharing branch compares `payer` first and returns
  `Ok((config.admin, quote_mint))` inside the borrow scope.
- Deserialize Pool through a named slice local (`let mut slice: &[u8] = &data;`).
- `create` writes `pda.creator` before `pda.quote_mint` and builds the event
  after `Clock::get()`, then `emit!`/`emit_cpi!`.

Every `require!`/`require_keys_eq!` site stays on its original source line
(148/152/156/174/192/197/204/213/214/221). Behavior is unchanged.

The standalone `DonationFeePdaCreated::Event::data` window is inlined and removed
by `--gc-sections`, so the candidate window count drops 586 → **585**, equal to
the deployed count.

Note: lalalune's upstream patch also carries an `ordered.ld` hunk (the whole-ELF
layout layer). It is omitted here because this packet's measure uses the plain
linker, not the layout wrapper; the `.rs` change alone closes the normalized
window and inlines the extra window.

## Measure (box: `window_map.py` normalized/raw over the deployed Fees ELF)

| build | normalized | candidate windows | raw (exact) | candidate (symbols.so) sha256 |
|---|---:|---:|---:|---|
| parent (after 147944) | 583 | 586 | 200 | `5381eb40…fc95d` |
| this packet | **584** | **585** | **200** | `57e11a5e…a701a02` |

Gained normalized: `163920`. Lost normalized: none. Raw not dropped (200→200).
Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Reproduces the method of
[lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT),
packet `research/claude-fees100-create-donation-20261027`. `source.patch` is
lalalune's create source patch (`.rs` hunks), applied verbatim to the identical
parent. Credit: lalalune.
