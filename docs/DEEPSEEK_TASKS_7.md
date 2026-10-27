# DeepSeek — task set 7 (2026-10-27). Hard problems.

Your static analysis has been consistently strong (F3 mayhem init, create_v2 CPI ordering, the
mayhem 41-row classification, the Fees unmatched triage + idiom correction). This set is the
hardest open work in the project. Read-only analysis as usual; Claude tests every proposal with
the real build/verifier before anything is trusted.

Context you need:
- Base = lalalune/pumpfun-source (MIT) at `~/pumpre/repo` main `e57657de`. Their own status:
  Fees 577/585 windows (143 exact), Mayhem 426/441 (70 exact), PumpSwap 488/785 (62%, 555/785 in
  an unpublished local checkpoint), Pump 528/1035 (51%). Donation Relay is whole-ELF exact.
- Claude reproduced their Fees build bit-for-bit (`/home/nagi/pumpre/feesbuild/`, `tools/try.sh`
  ~22 s per build+measure). Do NOT edit that tree — another agent runs the Fees race there.
- Rules: cite addresses; tag [B]/[R]/[partial]; never fabricate; no PRs to third-party repos.

---

## T7.1 — Build provenance forensics (the "unresolved recipe" Shaw lists for the 4 core programs)
Shaw's NEXT-STEPS lists the build recipe of the 4 core programs as UNRESOLVED (platform-tools
version, Cargo.lock, RUSTFLAGS/profile). The binaries leak a lot of it. For EACH of pump,
pump_amm, pump_fees, mayhem `deployed.so`, extract every provenance fingerprint:
- rustc / LLVM version and commit hash strings, platform-tools markers, `.comment` section.
- Every embedded dependency path (`.cargo/registry/src/index.crates.io-…/<crate>-<x.y.z>/…`,
  panic Locations) → the exact crate VERSION list. This is a partial Cargo.lock reconstruction.
- anchor-lang / anchor-spl / solana-program / spl-token(-2022) versions from paths and code shape.
- Build-path prefixes (`/home/runner/work/…`, remapped paths), which reveal CI layout + remap flags.
- Profile hints: overflow-checks (presence of overflow panics), panic strategy, opt-level / LTO /
  codegen-units signatures you can argue from the code (cross-crate inlining, symbol shape).
Then COMPARE with what Shaw's checkpoints use for each program and list every mismatch.
Deliverable `provenance_forensics.md`: per program, a table fingerprint → evidence address →
inferred value → Shaw's current value → match/mismatch. A single recipe mismatch can explain
hundreds of unmatched windows on Pump/PumpSwap, so this is potentially the biggest lever we have.

## T7.2 — PumpSwap root-cause clustering (largest unexplained gap)
PumpSwap has ~230–297 unmatched windows. In Fees, all 7 bad call edges turned out to be one
problem: the dispatchers calling the 7 unmatched handlers. Look for the same kind of structure in
PumpSwap. Classify the unmatched windows (Shaw's inventory for the PumpSwap checkpoint is in the
repo) by root cause: one shared helper whose shape differs and contaminates every caller, a
monomorphization/generic-instantiation difference, a dependency version (link to T7.1), a single
source-file layout issue, codegen-only, or genuinely missing logic. Rank the clusters by
"windows unlocked if fixed". Deliverable `amm_unmatched_clusters.md` with the top 5 clusters, each
with representative deployed↔candidate address pairs and the hypothesized single fix.

## T7.3 — Mayhem: the last 15 windows
Mayhem is at 426/441. Same method you used on Fees: pair the 15 unmatched windows exactly
(dispatcher edges + leftover-window analysis), classify (codegen-shape vs real delta vs bad
pairing), and propose one concrete source change per window, ranked by likelihood.
Deliverable `mayhem_unmatched_proposals.md`.

Order: T7.1 first (it can unblock everything), then T7.2, then T7.3. Ping the user after each.
