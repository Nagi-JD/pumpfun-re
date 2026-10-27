## Round34 (2026-10-27): our Round23 closure stack moved onto lalalune's newest Pump checkpoint

Base: `repro/pump/main-contract-round34-20261027/` at upstream main 4df2641ad.
Metric: their matcher (`metric/measure.py` = their analyze.py, verbatim; the only change is that the `--dump` JSON also records each candidate window's raw hash, so the raw set can be compared per window. The summary numbers are unaffected).
Reference: `evidence/original/pump/deployed.so`. The deployed binary is never a build input.

### Baseline: their shipped number vs our native rebuild

| Artifact | matched / 1035 | exact (raw) | sha256 (stripped) |
|---|---:|---:|---|
| Their shipped `candidate.so`, measured | 733 | 137 | 908bd16e... |
| Native Linux v1.44, plain cargo (`out/base`) | 733 | 127 | 8530f2ce... |
| **Native Linux v1.44, host-spoofing rustc shim (`out/spoof2`)** | **733** | **137** | **908bd16e...** (byte-identical, unstripped a919935c... identical too) |

Their build ran on macOS arm64 (native v1.44 compiler with official Linux v1.44 SBF target libraries). Cargo derives `-C metadata`, and therefore every mangled symbol hash and their `ordered.ld` selectors, from `rustc -vV` (host line) and from the host cfg (cpufeatures pulls in libc only on aarch64-apple). `shim/rustc` reports `host: aarch64-apple-darwin` and the aarch64-apple-darwin cfg to cargo's two probe calls. Every real compilation runs the unmodified Linux v1.44 rustc. With it, all crate hashes, both ELF hashes and their linker order reproduce exactly. The registry path does not affect the output: an equal-length CARGO_HOME gave the same hash as a short one.

Build (`b34.sh`): direct v1.44 `cargo build` of the workspace from the workspace root, `-Zremap-cwd-prefix=`, their `pump_text_layout_rustc.py` + `pump_physical_source_wrapper.py` wrappers with Linux `rust-lld` and their `ordered.ld`, `--jobs 2`.

### What Round34 had already adopted from our Round23 packets

Nothing. None of the 49 windows our Round23 stack gained (712 → 761) is matched in Round34, and Round34 matches 21 windows our Round23 stack did not (their own work since Round23). Details:
- Closure line placement: no. No deployed closure origin line holds an `error!` in Round34 (`sites.py`: 0/55).
- migrate / migrate_v2 post-complete quote: no. `migrate.rs` still transfers `real_quote_reserves - fee`; `post_complete_quote_in` is not read by either migrate handler.
- Legacy buy/sell bodies in lib.rs: no. Round34 keeps them in `buy.rs`/`sell.rs`. It did add `legacy_native_payments.rs` (rent-floor check) and changed the cashback account lookup in legacy sell.

### Steps (each a real rebuild and measure; matched AND raw sets compared to the previous step)

| Step | Change | matched | raw | Gained | Lost |
|---|---|---:|---:|---|---|
| spoof2 | Round34 unmodified | 733 | 137 | | |
| s1 | sell_v2.rs: 4 closures (341, 366, 368, 386) | 737 | 137 | 0x6f6d8 0x6f8e0 0x6fae8 0x6fcf0 | none |
| s2 | trade_v3.rs: 11 closure sites | 747 | 137 | 0x81640 0x84970 0x84b78 0x84d80 0x84f88 0x85190 0x85398 0x855a0 0x857a8 0x87ea8 | none |
| s3 | multi_hop_curve_swap.rs: 8 closures | 755 | 137 | 0x57c38 0x5fc48 0x5fe50 0x60058 0x60260 0x60468 0x60670 0x60878 | none |
| s4 | buy_v2.rs: 465, 469 (fn item), 498, 500, 881, 927, 995 | 762 | 137 | 0x16bb8 0x16dc0 0x16fc8 0x171d0 0x17ae8 0xac2b8 0xac4c0 | none |
| s5 | migrate.rs 280/282 + migrate_v2.rs 309/313/326, including the post-complete quote fix | 767 | 137 | 0x410b0 0x412b8 0x4bb40 0x4bd48 0x4bf50 | none |
| s6 | create_v2.rs:412 `quote_chain_accounts_required` fn item, used by nested_create | 768 | 137 | 0x19cc0 | none |
| s7 | lib.rs: legacy buy/sell `execute` bodies as inline modules (629–689, 981–1037), PumpError enum compacted so `final_real_sol_reserves_truncation` sits on 268 (set_params) | **782** | **137** | 0x137db8 0x14ecc0 0x14eec8 0x14f0d0 0x14f2d8 0x1549b0 0x154bb8 0x154dc0 0x154fc8 0x1551d0 0x1553d8 0x1555e0 0x1774f8 0x177700 | none |
| s7clean | s7 rebuilt from an empty target dir | 782 | 137 | | identical hashes (ad47e6a8... / 813d2796...) |

**Final: 782 / 1035 (75.6%), +49 over their 733, raw 137 = 137, 0 windows lost at any step.** All 49 windows the Round23 stack had gained are regained on Round34. No other step was needed or kept.

How the changes were moved: for every file we took our final Round23 version (`pumpround23/w_F`) and ported Round34's own Round23→Round34 edits onto it with `port.py`. Each Round34 hunk is located whitespace-insensitively after the previous one, and its new text is squeezed into the same number of lines, so our deployed-line placement does not move (a `//` comment is never joined). Legacy buy/sell hunks that Round34 made inside `execute` were applied to the lib.rs modules where those bodies now live; the rest went to buy.rs/sell.rs. Every hunk was applied exactly once. s1 (sell_v2) used a 3-way merge plus `retarget.py`, which re-pads each closure to its deployed line. `sites.py` reports 51/55 closure origins placed: buy_v2 959/983 and pump_quote 212/222 are still absent, as on Round23.

Behavior: compared with Round34, the per-variant `PumpError::*` counts and the counts of `require*!`, `checked_*`, `narrow` and `try_from` change by exactly the same amounts as our reviewed Round23 stack changed Round23 (`vc.py`: identical deltas). No check is removed or added beyond the helper→closure rewrites, which keep the same variant and order. The only semantic change is the execution-verified migrate fix (migrated quote = real_quote_reserves + post_complete_quote_in − fee, see `research/pump-migrate-verification/`). There is no macro and no file/line literal; all origins come from `error!` (`file!()`/`line!()`) at the real line.

Not run: their captured-loader differential suites and `verify.py`.

Files: `round34-race.patch` (diff vs Round34 `source/programs/pump`), `source/` (final programs/pump tree), `measure/*.json` (spoof2 = base, s1–s7, s7clean, plus their shipped artifact as `shipped-m.json`), tools (`b34.sh`, `shim/rustc`, `step.sh`, `stepport.sh`, `port.py`, `retarget.py`, `resolve.py`, `sites.py`, `cmp2.py`, `vc.py`), `SHA256SUMS`.
