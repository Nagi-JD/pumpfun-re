# chantier-T4: out-of-line `[Pubkey;8]` BorshSerialize at 0xf130 for SetParamsEvent

Refs T4 (#18, equalize function sizes). Resolves the root interval left by `chantier-T4-pk7-borsh-serialize` (`0xefc8`..`0xf6c0`, delta -1424): deployed window `0xf130` (1424 B) is the `Vec<u8>` monomorph of `<[Pubkey; 8] as borsh::ser::BorshSerialize>::serialize`, called once (`0x164080`) from `<SetParamsEvent as anchor_lang::Event>::data` at `0x163ea8` (1040 B).

## What the deployed program does

`0xf130` serializes eight `Pubkey` values into a growable byte buffer: eight calls into `RawVec::reserve` (`0xded0`) with the 32 B copies inlined. It sits between the 360 B `[T; N]` serializer at `0xefc8` and the 408 B one at `0xf6c0`.

Its only caller, `SetParamsEvent::data` at `0x163ea8`, allocates the 256 B event buffer, writes the discriminator and the first 0x69 bytes of fixed fields as straight stores (no reserve), calls `0xf130` for `fee_recipients`, then writes `timestamp`, `set_creator_authority` and `admin_set_creator_authority` with three reserves. It follows `PostCompleteBuyEvent::data` (`0x163bf0`) in `.text`.

In the baseline layout `fee_recipients` stayed typed as `[Pubkey; 8]`, so the serializer was inlined into `SetParamsEvent::data`, which grew to 3496 B with 21 reserve calls and matched no deployed window.

## Change

- `source.patch`: introduces `Pk8([Pubkey; 8])` with a `#[inline(never)]` `BorshSerialize` and a matching `BorshDeserialize`, appended at the end of `lib.rs` after `Pk7` (no shift of `error!` line numbers), and switches `SetParamsEvent.fee_recipients` plus its construction site in `set_params::execute` to `Pk8`, both on their existing lines. Wire format stays eight consecutive pubkeys; runtime checks and error codes are unchanged.
- `ordered-ld.patch` (on top of the T4 `ordered.ld` from #27): places `Pk8::serialize` (`h4d76d758b2eba544`) right after the 360 B `[T; N]` serializer so it lands at `0xf130`, and moves `SetParamsEvent::data` (`h5db509fee3433e88`) right after `PostCompleteBuyEvent::data`, its deployed neighbour.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| pk7-borsh-serialize (#27) | 791 | 139 | `43912acb109f6e915329cfe830bb23e0bcc6d27e6d08ebd95829b5d0f7c8898b` |
| Pk8, #27 `ordered.ld` (no placement) | 793 | 139 | `c7c6319b817b3193bb61f8da2fc269aefa13e96f5482bbc83eadfa6188acb3c0` |
| Pk8, `Pk8::serialize` placed only | 793 | 140 | `f476cc046519a65a0570de62f8d6834b80acfe2c7fe7929d0064df8b8fe53ba4` |
| Pk8 + `ordered-ld.patch` (this packet) | **793** | **140** | `1d77749f01ea68e705f2fc7cf339ff1a2fc57a43de98ac544091fc76d4afe6af` |

Gained matched: `0xf130`, `0x163ea8`. Gained raw: `0xf130`. Lost: none. In this packet's build `h4d76d758b2eba544` sits at `0xf130` with size 1424 B and the same raw sha as deployed; `SetParamsEvent::data` is 1040 B and directly follows `PostCompleteBuyEvent::data`.

Drift solver: `call_only_raw_fail` 221 to 222, `potential_if_delta0` 360 to 362, `intervals_nonzero` 90 to 88 (88 with the full placement, 90 with the serializer placed alone). The `0xefc8`..`0xf6c0` and `0x163bf0`..`0x1642b8` intervals close.

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
