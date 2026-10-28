# chantier-fees whole-ELF: `crank_donation_fee_pda` handler body, window 147944 matched

Refs the Fees whole-ELF frontier. First packet of the three-window Fees close-out
(147944 → 163920 → 120816). Parent: the verified Fees byte-race baseline
`extend-qualified` (582 normalized / 200 raw, unmatched `[120816, 147944, 163920]`,
symbols sha256 `ca9e6a93…`).

## What the deployed program does

The deployed Fees program has one remaining large handler window at **147944
(1,950 instructions / 15,976 B)**: the `#[program]` handler
`crank_donation_fee_pda`. The candidate reproduced every window except this one.
The residual was pure **register allocation** around the SyncNative
`AccountMeta` / `TokenInstruction::SyncNative.pack()` / `AccountInfo`-clone region.

Root cause (measured by lalalune on the candidate IR with `llc`): when the
inlined SyncNative helper takes `rent: &AccountInfo`, that parameter is
`noalias readonly`. LLVM attaches scoped-noalias metadata, so GVN reuses the
`rent.key` pointer loaded for the `AccountMeta` (before `pack`) inside the
account-info clone (after `pack`). The deployed program instead **reloads
`rent.key` after `pack`** (`ldxdw r3,[r6+0]`) — i.e. its `rent` `AccountInfo`
was not behind a noalias parameter.

## Change

`source.patch` (two files, applies with `patch -p1`):

- `programs/pump-fees/src/donation.rs`: factor the native-SyncNative region into a
  plain helper
  `fn sync_native_excess<'info>(donation: &AccountInfo, ata: &mut Account<TokenAccount>, rent: &UncheckedAccount) -> Result<Option<u64>>`.
  Passing the Anchor wrapper **`&UncheckedAccount`** (from which the `AccountInfo`
  is loaded) carries no noalias scope and yields exactly the deployed reload
  shape. The `DonationFeePdaCranked` `Event::data` becomes the standard
  one-line `AnchorSerialize` form (blank lines keep all following source line
  numbers). 
- `programs/pump-fees/src/lib.rs`: the handler calls the helper in a native arm
  (`match … { Some(amount)=>amount, None=>return Ok(()) }`) and keeps its own
  `msg!("Nothing to donate")` on the non-native arm.

Behavior is unchanged: same checks, CPIs, events and errors. The helper's reload
is equivalent to `try_borrow_data` + `try_deserialize` + `set_inner`, and the
Borsh event serialization is equivalent to the per-field encoding.

## Measure (box: `window_map.py` normalized/raw over the deployed Fees ELF)

| build | normalized | raw (exact) | candidate (symbols.so) sha256 |
|---|---:|---:|---|
| parent (extend-qualified baseline) | 582 | 200 | `ca9e6a93…afb335` |
| this packet | **583** | **200** | `5381eb40…fc95d` |

Gained normalized: `147944`. Lost normalized: none. Raw not dropped (200→200).
Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Reproduces the method of
[lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT),
packet `research/claude-fees100-crank-donation-20261027` (the `&UncheckedAccount`
noalias fix). `source.patch` is lalalune's crank source patch, applied verbatim
to the identical `extend-qualified` parent. Credit: lalalune.
