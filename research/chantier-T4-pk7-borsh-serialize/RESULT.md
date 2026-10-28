# chantier-T4: out-of-line `[Pubkey;7]` BorshSerialize at 0xea68

Refs T4 (#18, equalize function sizes). Resolves the root interval left by `chantier-T4-shareholder-copy` (`0xe9e8`..`0xef40`, delta -1240): deployed window `0xea68` (1240 B) is the `Vec<u8>` monomorph of `[Pubkey; 7] as borsh::ser::BorshSerialize>::serialize`, called twice from `__global::set_reserved_fee_recipients` (`0x6fef8`) while emitting `ReservedFeeRecipientsEvent` (`emit!` at `0x719c8`, `emit_cpi!` at `0x71c90`).

## What the deployed program does

`0xea68` is a 1240 B body that serializes seven `Pubkey` values into a growable byte buffer. It makes seven calls into `RawVec::reserve` (`0xded0`) and inlines the 32 B pubkey copies. The surrounding matched windows are `PubkeyError::fmt` at `0xe9e8` (128 B) and a smaller `[T; N]` BorshSerialize at `0xef40` (136 B).

In the baseline layout the event field stayed typed as `[Pubkey; 7]`, so the `Vec<u8>` monomorph was inlined into the handler and never appeared as its own `.text` window. The generic `[T; N]` monomorphs that did emit were the `write_all` forms (360 B / 408 B), not the 1240 B reserve-unrolled form the deployed program keeps out of line.

## Change

- `source.patch`: introduces `Pk7([Pubkey; 7])` with a `#[inline(never)]` `BorshSerialize` and a matching `BorshDeserialize`, appends it after the existing `cold_path` marker (no shift of `error!` line numbers), and switches `ReservedFeeRecipientsEvent.reserved_fee_recipients` plus its construction site in `set_reserved_fee_recipients` to `Pk7`. Wire format stays seven consecutive pubkeys; runtime checks and error codes are unchanged.
- `ordered-ld.patch` (on top of the T4 `ordered.ld` from #26): places `Pk7::serialize` (`hbecec53556d1b43a`) immediately after `PubkeyError::fmt`, its deployed neighbour, so it lands at `0xea68`.

## Measure (native)

| build | matched | raw (exact) | candidate sha256 |
|---|---:|---:|---|
| shareholder-copy (#26) | 790 | 138 | `3aa5b81f4d295c4f418150ad11d74b8f1c11f48c5196c8963ee2b4db160ced8a` |
| Pk7, T4 `ordered.ld` (no placement) | 791 | 138 | `c83101d92de99e26e43a4e423d2c3e58b41e524f87d6e53f3453c89c25935310` |
| Pk7 + `ordered-ld.patch` (this packet) | **791** | **139** | `43912acb109f6e915329cfe830bb23e0bcc6d27e6d08ebd95829b5d0f7c8898b` |

Gained matched and raw: `0xea68`. Lost: none. In this packet's build `hbecec53556d1b43a` sits at `0xea68` with size 1240 B and the same raw sha as deployed.

Drift solver: `call_only_raw_fail` 221, `potential_if_delta0` 359 to 360. The `0xe9e8`..`0xef40` interval closes and the next root surfaces at `0xefc8`..`0xf6c0`, delta -1424 (unmatched deployed window `0xf130`, 1424 B).

Details: `measure.json`. Recipe: `build-recipe.md`.

## Attribution

Builds on [lalalune/pumpfun-source](https://github.com/lalalune/pumpfun-source) (MIT), packet `research/pump-r34-bodies-verified`.
