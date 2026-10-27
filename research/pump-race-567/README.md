# Pump byte-identity gap research (2026-10-27)

Work dir: `/home/nagi/pumpresearch/` (copy of `programs/pump` at upstream e57657de; `our-reconstruction` and `feesbuild` untouched).
Oracle: `evidence/original/pump/deployed.so` (sha256 7a19affa...), never a build input.
Metric: lalalune's own matcher `repro/layered-passes/pass-01/after-fixes/pump/{analyze.py,elf_reader.py}` copied verbatim to
`pumpresearch/metric/`, wrapped by `metric/measure.py ORIG CAND SYMBOLS`. "matched" = original windows with a normalized + relocation-pattern
counterpart; "exact" = raw-equal bodies. Builds: `pumpresearch/build.sh LABEL [srcdir] [tools]` = direct-path `cargo rustc` with the
`~/.cache/solana/v1.44` rustc/cargo, `-Zremap-cwd-prefix=`, strip via v1.52 llvm-objcopy, deps fetched `--locked` into `pumpresearch/cargo`.
Extra rustc args go through `$EXTRA`.

## 1. Reproduction

| Artifact | sha256 (stripped) | matched / 1035 | exact | unmatched | call-consistent |
|---|---|---:|---:|---:|---:|
| Published "Pump selected" `repro/pump/remaining-guards-main-fortyeight/main/candidate.so` (measured, not rebuilt) | 71ec4d8a... | **528** | **98** | 507 | 454 |
| Native rebuild of the same source, direct-path v1.44 (`out/base-*`) | c7403760... | 533 | 106 | 502 | 459 |
| Native rebuild via `cargo-build-sbf 3.1.15 --tools-version v1.44` | c7403760... (identical) | 533 | 106 | 502 | 459 |

- The published numbers are confirmed exactly by running their metric on their artifact (528/98/507).
- Their recipe (`scripts/build_partial_candidate.py`: `cargo build-sbf --tools-version v1.44 --sbf-sdk ... -- --locked --offline`) ran on an
  **aarch64-apple-darwin** host (see build-comparison.json). The Linux v1.44 build is not byte-identical to 71ec. It scores +5 windows and +8 exact
  bodies higher. I did not investigate why the host changes the output. For Pump, the wrapper and direct-path builds produce the same bytes, unlike Fees.
- Toolchain sweep on the same source: v1.45 gives 486/82 and v1.46.1 gives 394/80. v1.43 does not build because it has no `sbpf-solana-solana` target. v1.44 is the best.
- Structural fact: the original has 1035 windows and the candidate only 780, so about 255 original functions have no candidate function at all. These are per-site
  copies the source does not produce: closures, non-inlined duplicates and similar.

## 2. Clusters of the unmatched windows (base 502, exp2 497)

| # | Cluster | Windows | Representative deployed <-> candidate | Hypothesized cause | Evidence |
|---|---|---:|---|---|---|
| A | **Anchor error-origin constants**: `error!()` stores the `file!()` length and the `line!()` value as st-imm instructions | 72 original windows (28 candidate bodies) | 0x16bb8 (buy_v2.rs:465) <-> cand 0x77e40 set_params closure (set_params.rs:22); 0x81848 (trade_v3.rs:390) <-> cand 0x23000 buy_v2::add (also legacy_buy/sell_v2/legacy_sell/trade `add` copies) | Source file names, paths and line numbers differ from the original | In same-size diff pairs, 80 diffs are `stdw imm` (0x1b vs 0x11, a path length of 27 vs 17) and 74 are `stw imm` (line 0x1d1=465 vs 22). Diagnostic only, not a byte claim: masking the op 0x62/0x7a immediates moves 533 to 610 (exp2: 538 to 610). Pair table: `out/exp2-origins.json` (`origins.py`) |
| A1 | Sub-cluster of A: **55 per-site `map_err(\|_\| error!(..))` closures** (520 B; calls 0x157380, 0x15de88, 0x19bb30, 0x1ace18 in deployed addressing) | 55 (0 matched) | 0x16bb8, 0x16dc0, 0x16fc8, 0x19cc0, 0x410b0, 0x137db8, ... | The original writes a closure at 55 sites; the candidate has only 7 such closures (0x55008, 0x55210, 0x5b730, 0x77e40, 0x84e48, 0x8e628, 0x8e830) | Coordinator lead confirmed; my scan uses different call addresses. All 55 sites were extracted from the deployed binary with (file, line, error code); see section 4 |
| B | Original file layout differs (feeds A) | (counted in A) | n/a | Deployed paths: `programs/pump/src/{trade_v3,buy,buy_v2,sell,sell_v2,pump_quote,fee_recipient,extend_account,sweep_fees,multi_hop_curve_swap,admin_set_idl_authority,set_reserved_fee_recipients,migrate,migrate_v2,create_v2,lib}.rs`, `creator/{admin_cto,set_creator,collect_creator_fee,distribute_creator_fees,distribute_creator_fee_v2,distribute_fee_to_holders,migrate_bonding_curve_creator,set_metaplex_creator}.rs`, `token_incentives/{claim_token_incentives,init_user_volume_accumulator,volume_accumulator}.rs`, `util/{fee,transfer_fee,constant_product}.rs`, `quote_control/{state,initialize_quote_control,update_quote_control_mints}.rs`. The candidate uses flat `src/<x>.rs` with different names | Path strings in deployed rodata |
| C | Unmatched `pump_recovered` handler and helper bodies | 108 candidate bodies, 561 KB | Largest deployed unmatched windows: 0x22a10 (27400 B), 0xcf750 (24312), 0xd5af0 (23608), 0xb6578 (23440), 0xa4378, 0xe62a8, 0x13f630, 0x5b3b0 | Handler logic and inlining differences; these bodies were not analysed one by one | Category counts from `out/exp2-m.json` |
| D | Anchor `try_accounts` | 50 candidate bodies, 384 KB | n/a | Account-struct field order or constraints | Same |
| E | `__global` dispatch wrappers, try_deserialize, AccountsExit, Event, borsh | 33 / 15 / 10 / 6 / 8 | n/a | Probably downstream of the C/D shapes | Same |

The coordinator also reported transfer_checked at 12 deployed vs 1 candidate and system_program::transfer at 9 vs 1. These would be the same per-site instantiation effect. I did not measure them.

## 3. Attempts (real rebuilds, measured)

| Label | Change | Matched | Exact | Delta vs base | Kept |
|---|---|---:|---:|---:|---|
| base | Upstream source, v1.44 direct | 533 | 106 | n/a | Baseline |
| tc-v1.45 / tc-v1.46.1 | Toolchain | 486 / 394 | 82 / 80 | -47 / -139 | No |
| tc-v1.43 | Toolchain | Build fails (no target) | | | No |
| exp1a | Pad set_params.rs with 246 lines and minimum.rs with 640 lines; remap both to lib.rs | Compile error: anchor `#[program]` cannot find `__client_accounts_get_minimum_distributable_fee` after minimum.rs is padded | | | No |
| exp1 | Pad set_params.rs with 246 leading blank lines (closure line 22 -> 268) plus `--remap-path-prefix=src/set_params.rs=programs/pump/src/lib.rs` | 534 | 106 | **+1**: the closure now matches 0x137db8 (lib.rs:268, code 6025) | Mechanism proof only (hack) |
| **exp2** | `--remap-path-prefix=src/=programs/pump/src/` (original path prefix) | **538** | 106 | **+5**, 0 lost (gains 0x135ac0, 0x69978, 0x69f28, 0xe4348, 0x68918) | **Yes** |

To reproduce exp2: `EXTRA="--remap-path-prefix=src/=programs/pump/src/" /home/nagi/pumpresearch/build.sh exp2`. A cleaner equivalent is to build from a
workspace rooted two levels above the crate, so that `file!()` is `programs/pump/src/...` without a remap.

## 4. Most promising next lever

Cluster A is mechanical and worth up to about 72 windows: the diagnostic mask puts its ceiling at roughly 610 against the current 538. That is more than any other identified cause.

1. **Move the modules to the deployed file paths** listed in cluster B and keep the `programs/pump/src/` prefix from exp2. The exact path length is baked into every error-origin body.
2. **Write the error sites as per-site closures** at the 55 deployed sites, in the files they belong to. Use `.map_err(|_| error!(PumpError::...))` with code 6024 or 6025. This is the form already used at set_params.rs:22, legacy_sell.rs:64-65 and trade.rs:125-126. Do not use an `#[inline(always)]` shared helper, because that removes windows. The deployed (file:line, code) sites are:
   - buy_v2.rs: 465(6025), 469, 498, 500, 881(6025), 927(6025), 959(6025), 983(6025), 995
   - lib.rs: 268(6025), 629(6025), 664, 666, 674, 679, 684, 689, 981(6025), 1007, 1009, 1022, 1027, 1032, 1037
   - trade_v3.rs: 382, 721, 767, 811(6025), 904(6025), 911(6025), 930(6025), 970, 997(6025), 1140(6025), 1155
   - multi_hop_curve_swap.rs: 259, 571, 589(6025), 624, 673(6025), 692, 736, 744
   - sell_v2.rs: 341(6025), 366, 368, 386
   - migrate_v2.rs: 309, 313, 326
   - migrate.rs: 280, 282
   - pump_quote.rs: 212, 222
   - create_v2.rs: 412(6109)
   - Sites with no code given use 6024.
3. **Align line numbers** so each `error!` lands on its deployed line: lay each file out in deployed order and pad with blank lines or comments. exp1 shows this works and can be measured one window at a time. These line numbers also give an ordering skeleton for the original source files.

Caveat from exp1a: leading blank lines in minimum.rs broke Anchor's `#[program]` client-account resolution. Pad after the `#[derive(Accounts)]` structs, or build after each padding change to check it.

## 5. Results: executing the closure/origin lever (2026-10-27, continuation)

Method: `place.py FILE SPEC.json`. It rewrites a helper call (`add/sub/narrow/n`), an `.ok_or(PumpError::Overflow)` or an existing `error!(` into the
per-site closure form (`(a).checked_add(b).ok_or_else(|| error!(PumpError::Overflow))` / `u64::try_from(x).map_err(|_| error!(PumpError::Truncation))`).
It places `error!` on the deployed line by inserting newlines inside the expression. When a site is already too low, it joins earlier statement lines; if that still fails, it SKIPs the site.
It never adds leading blank lines before items. File paths: the global `src/=programs/pump/src/` remap, plus per-file remaps
`trade.rs->trade_v3.rs`, `multi_hop_curve.rs->multi_hop_curve_swap.rs`, `trade_types.rs->pump_quote.rs`. `legacy_buy`/`legacy_sell` were physically moved
into `lib.rs` as inline modules, because remapping several files onto `lib.rs` broke module resolution (263 errors). Every step was a real native v1.44 rebuild and was measured with the lalalune matcher.

| Step | Change | Matched | Exact | Delta | Gained (deployed) | Lost |
|---|---|---:|---:|---:|---|---|
| exp2 | path prefix (start point) | 538 | 106 | n/a | | |
| s1 | buy_v2: 6 sites placed (465, 469, 881, 927, 959, 983) | 542 | 106 | +4 | 0x16dc0 0x16fc8 0x171d0 0x176d8 | 0 |
| s2 | trade.rs as trade_v3.rs: 11 sites | 552 | 106 | +10 | 0x81640 0x84970 0x84b78 0x84d80 0x84f88 0x85190 0x85398 0x855a0 0x857a8 0x87ea8 | 0 |
| s3 | multi_hop_curve.rs as multi_hop_curve_swap.rs: 7 placed, 589 skipped | 558 | 106 | +6 | 0x5fc48 0x60058 0x60260 0x60468 0x60670 0x60878 | 0 |
| s4 | sell_v2 4 sites; migrate 280; migrate_v2 309, 326; trade_types.rs as pump_quote.rs 212 (282, 313, 222 skipped) | 563 | 106 | +5 | 0x4bf50 0x6f6d8 0x6f8e0 0x6fae8 0x6fcf0 | 0 |
| s5a | remap legacy_buy/legacy_sell/set_params onto lib.rs | build failed (module resolution) | | | | |
| **s5** | legacy_buy + legacy_sell inlined into lib.rs; sites 629-689 and 981-1037 (4 skipped) | **567** | 106 | +4 | 0x1549b0 0x154bb8 0x1551d0 0x1774f8 | 0 |

Cumulative: **567 / 1035 (54.8%)**. That is +29 vs exp2 538, +34 vs the native baseline 533, +39 vs Shaw's published 528, and +19 vs his unpublished 548.
No step lost a window. The exact count stays at 106: the gained closures are normalized matches, because callers and call targets still differ.

Why some placed sites did not gain: the closure is not emitted as a separate 520-B window, because LLVM inlined or folded it in that caller context.
Affected sites: buy_v2 465 and 983, multi_hop 259, migrate 280, migrate_v2 309, pump_quote 212, and lib.rs 629/666/674/679/684/689. In the deployed binary those are separate windows, so the
original caller shape differs (different caller functions per site group). Matching them needs caller-structure work, not just more line placement.
Leftover candidate closures with no deployed slot: trade_v3 811/6024 and 811/6026 (the old trade.rs:125/127), lib.rs 982/990/995/1012/1099/1100,
nested_create 19 and 161, set_params 22, minimum 24.

Not done: create_v2:412 (6109; candidate site is in nested_create.rs:161) and lib.rs:268 (set_params). Cluster C/D handler bodies are untouched.

Blocker hit at packaging time: while creating the research branch, WSL started returning filesystem I/O errors
(`git worktree add -b pump-race /home/nagi/pumpresearch/pump-race-wt e57657de` died with SIGBUS / "unable to unlink ... Input/output error",
and every later `wsl` call fails with getpwuid/UtilInitGroups errors). The `pump-race` commit was NOT made; its state is unknown.
A partial `.git/worktrees/pump-race-wt` and/or a `pump-race` branch may exist and should be checked (`git worktree prune`) once WSL is healthy.
The other worktree (`/home/nagi/pumpre/repo` on `fees-race`) was not checked out or modified.
Kept source: `/home/nagi/pumpresearch/w5/programs/pump/src`. Specs: `s_buy.json s_trade.json s_mh.json s_sell.json s_mig.json s_mig2.json s_pq.json s_lb.json s_ls.json`.
Remaps: `s4.remap`. Tools: `place.py`, `build.sh`, `metric/`. Artifacts: `out/s1..s5-*`. To rebuild: `EXTRA="$(cat s4.remap)" ./build.sh s5 /home/nagi/pumpresearch/w5`.
