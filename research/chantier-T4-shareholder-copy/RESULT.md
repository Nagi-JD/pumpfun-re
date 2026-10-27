# chantier-T4: Shareholder Vec clone as a memcpy specialization at 0xcf18

Refs T4 (#18, equalize function sizes). Resolves the root interval left by `chantier-T4-whitelist-resync` (`0xce88`..`0xd068`, delta -336): deployed window `0xcf18` (336 B) is `<alloc::vec::Vec<T> as core::clone::Clone>::clone` (`h981bad13`), the `Copy` specialization of `Vec::clone` monomorphized for a 34 B element.

## What the deployed program does

`0xcf18` is a 336 B `Vec<T>::clone` body that clones the backing buffer with a single `memcpy` rather than an element by element loop. Its two call targets in the deployed `.text` are `memcpy` (`0x1b3610`) and `alloc::raw_vec::handle_error` (`0x1ab198`): it allocates a buffer of `len * 34` and copies it in one shot. It is called from `0x2d920` and `0x32840`.

The 34 B element is `Shareholder { address: Pubkey, share_bps: u16 }`. When a type is `Copy`, `Vec::clone` resolves to the `memcpy` specialization; with `Clone` alone it resolves to the element wise clone loop, a different body and a different size. The deployed `Shareholder` is `Copy`, so the deployed build emits the `memcpy` clone at `0xcf18`.

## Change

- `source.patch`: adds `Copy` to the derive list of `Shareholder` in `programs/pump/src/trade_types.rs`. `Copy` is a compile time marker; it changes neither the runtime behavior nor the borsh serialization of `Shareholder`, and it selects the `memcpy` clone specialization that the deployed program uses. The edit stays on its existing source line, so `error!` line numbers are unchanged.
- `ordered-ld.patch` (on top of the T4 `ordered.ld`): places the `Vec<T>::clone` body `h981bad13` between the `u64` and `bool` `BorshDeserialize::deserialize_reader` monomorphs, its deployed neighbours, so it lands at `0xcf18`.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| whitelist-resync (#25) | 789 | 138 | `c152d81d7010078e97530d24aaa96715b0f35de68f16cc89f798994d882d7724` |
| Copy derive, T4 `ordered.ld` | 790 | 138 | `414d3a9578188be58a89be8fe97294394d5cda2a0071037249d8fd8fb6e98a88` |
| Copy derive + `ordered-ld.patch` (this packet) | **790** | **138** | `3aa5b81f4d295c4f418150ad11d74b8f1c11f48c5196c8963ee2b4db160ced8a` |

Gained matched: `0xcf18`. Lost: none (matched and raw). Both Copy rows measure 790; this packet additionally places the body at `0xcf18`, its deployed slot, so the drift frontier advances.

In this packet's build `h981bad13` sits at `0xcf18` with size 336 B, as deployed. The two prior rows differ only in placement: without `ordered-ld.patch` the body lands at `0x15a070`.

Drift solver: `call_only_raw_fail` 220 to 221, `potential_if_delta0` 358 to 359, nonzero intervals 74 to 75. The `0xce88`..`0xd068` interval closes and the next root surfaces at `0xe9e8`..`0xef40`, delta -1240.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
