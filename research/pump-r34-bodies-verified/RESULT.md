# pump-r34-bodies — VERIFIED on our canonical s7clean profile

Independent verification of DeepSeek #2's source-only patch `ds2-pump-r34` @ `85fb47a`
(packet `research/pump-r34-bodies/`) against **our** canonical Pump Round34 byte-race
build profile (`pumpround34/s7`, the s7clean recipe: macOS-host rustc shim +
text-layout wrapper + ordered.ld, platform-tools v1.44, target `sbf-solana-solana`).

## The patch (4 edits / 4 windows)

| Window    | File:line         | Change                                                                 |
|-----------|-------------------|------------------------------------------------------------------------|
| 0x14eab8  | lib.rs:629        | `core::hint::black_box()` on the `u64::try_from` of raw_quote legacy (restores closure 6025 that folding removed) |
| 0x87ca0   | trade_v3.rs:1140  | same `black_box` on post_fee_quote                                     |
| 0x176d8   | buy_v2.rs:959     | partial-fill branch: `quote = trunc(rtr*vq/(vt-rtr)+1)`                 |
| 0x178e0   | buy_v2.rs:983     | non-partial side: `trunc(computed*vq/(vt-computed)+1)`                  |

Applied as `patch -p1` (dry-run + apply both exit 0). Our s7 base source is
**byte-identical** to the contributor's base (`lib.rs` 866dd020…, `trade_v3.rs`
b35f286f…, `buy_v2.rs` 07ffa07a… match ds2's `*.bak`), so the diff ports exactly —
no wholesale file copy. Only the 4 one-line edits were applied.

## Two baselines

### Contributor baseline (DeepSeek #2 recipe — plain v1.44 rustc, `sbpf-solana-solana`, no shim/text-layout/ordered.ld)
| | matched | raw (exact) | total |
|-|---------|-------------|-------|
| base7 (unpatched) | 787 | 129 | 1035 |
| v3 (patched)      | 791 | 129 | 1035 |
| delta             | **+4** | 0 | — |

### Our canonical profile (s7clean recipe — macOS shim + text-layout + ordered.ld, v1.44, `sbf-solana-solana`)
| | matched | raw (exact) | total |
|-|---------|-------------|-------|
| s7clean (unpatched, README number) | 782 | 137 | 1035 |
| bverify (clean re-build of s7, determinism check) | 782 | 137 | 1035 |
| s7p (patched) | 786 | 137 | 1035 |
| delta | **+4** | **0** | — |

`bverify` reproduces s7clean bit-for-bit (candidate.so SHA
`ad47e6a819225508b0f825f960ee79dba254425a730d618795caaa149425d4e1`, identical to
s7clean), confirming the baseline is deterministic at 782/137.

## cmp2 (s7clean → s7p)

```
matched 782 -> 786  +[0x176d8, 0x178e0, 0x87ca0, 0x14eab8]  -[]
raw     137 -> 137  +[]  -[]
```

The +4 matched windows are **exactly** the 4 windows claimed by the patch.
`lost[] = []` — no previously-matched window regressed. Raw (exact) set unchanged.

## Verdict

**COMMITTABLE GAIN: +4 matched on our profile, with zero raw loss and zero lost windows.**

The patch reproduces its claimed +4 on our canonical s7clean profile (782 → 786),
mirroring the +4 the contributor measured on their own base (787 → 791). The absolute
baselines differ only because of the build recipe (the source trees are identical);
the gain and the zero-regression property hold on both profiles.

## Artifacts
- `patch-s7-base.diff` — the exact 4-edit patch applied to our s7 source
- `measure/s7clean-m.json` / `-summary.json` — our unpatched baseline (782/137)
- `measure/bverify-m.json` / `-summary.json` — clean re-build determinism check (782/137)
- `measure/s7p-m.json` / `-summary.json` — our patched build (786/137)
- `SHA256SUMS` — integrity for patch + measure JSONs + candidate.so hashes
