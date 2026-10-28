# pump_quote module split: +3 windows (2026-10-28)

Stacked on the Round34 checkpoint source (`repro/pump/main-contract-round34-20261027/source`).
Same toolchain and metric: platform-tools v1.44 direct `cargo rustc` (no
cargo-build-sbf), measured with the lalalune window metric against
`evidence/original/pump/deployed.so`. Builds on lalalune/pumpfun-source (MIT).

## Before / after

| build | matched / 1035 | raw | unique_pairs |
|---|---:|---:|---:|
| p0/p1 (Round34 rebuild baseline) | 738 | 129 | 522 |
| **p6 (this packet)** | **741** | **129** | **525** |

gained deployed windows (3), lost none, raw set unchanged (129 -> 129):
`0x62170` (constant_product fn), `0x63530` (arm, line 212), `0x63738` (arm, line 222).

Baseline note: the Round34 checkpoint publishes 733 matched; our rebuild of the
same source measures 738 in this environment. The packet's before/after is taken
on our own rebuild (738 -> 741), same environment on both sides.

## What pump_quote is

The deployed program carries a real module `programs/pump/src/pump_quote.rs`
(~415 lines, 31 error closures: Overflow/DivisionByZero + the quote errors
6100-6105). The Round34 candidate folds this logic into `nested_create.rs`
(188 lines). The closures therefore bake the wrong path (`nested_create.rs`, 34
chars vs `pump_quote.rs`, 31) and the wrong lines - and no candidate window can
match a deployed arm whose (path-len, line, code) triple is baked into its body.

Exact deployed closure map (from the binary, `tools/29-exact-closures.py`):
61:6024, 62:6105, 90:6100, 104:6024, 106:6026, 117:6024, 119:6024, 121:6026,
122:6024, 131:6026, 134:6024, 137:6024, 139:6026, 199:6024, 201:6026, 212:6024,
222:6024, 241:6104, 279:6103, 280:6103, 307:6103, 334:6024, 365:6103, 366:6103,
371:6103, 372:6103, 378:6103, 406:6103, 407:6102, 410:6103, 415:6103.

## The change (`pump-quote-split.patch`)

1. **Module split**: `nested_create.rs` -> `src/pump_quote.rs` (the deployed
   module name/path), `create_v2.rs` re-wired (`#[path = "pump_quote.rs"] mod
   pump_quote;`). Behavior unchanged.
2. **Per-site Overflow closures**: the candidate used one shared `fn overflow()`
   item (a single closure at line 19 used 13 times); the deployed has one
   closure per site (11 in pump_quote.rs + 3 in create_v2.rs = 14 = our 13 uses
   + the `require!` site). Each use is now its own `|| error!(PumpError::Overflow)`.
3. **Line layout**: fns reordered and every error!/require placed with
   whitespace-only padding/compaction. Exact placement where a deployed window
   can match: constant_product -> 131/134/137/139, price -> 199/201/212/222/241.
4. **price reconstructed to the deployed fingerprint**: the deployed window
   0x62aa0 carries exactly O@199 D@201 O@212 O@222 6104@241 (5 closures); the
   candidate had 7 (a duplicate `checked_sub(real)` - value-identical, and a
   `require!(real != 0)` the deployed does not raise). Both duplicate checks were
   removed: the duplicate sub is already covered at 199 (same expression), and
   the `real != 0` guard is not in the deployed closure set. Behavior note: with
   `real == 0` the deployed divides and traps; the previous candidate raised
   DivisionByZero. This moves behavior toward the deployed.
5. **fn-item arms**: the closures at 212/222 are standalone functions in the
   deployed (their arms are the 520-byte windows 0x63530/0x63738). They are now
   `#[inline(never)] fn` items whose `error!` sits on lines 212/222 - the same
   fn-item method as the pump-r23 packets. Inline closures get inlined into the
   caller and produce no arm window (measured: 739, no gain); the fn-items do
   (measured: 741).

No macro hardcodes a file or line; placement is real code position. The deployed
`.so` is not a build input.

## Evidence

- `pump-quote-split.patch` - p1 source -> p6 source.
- `measure-p1.json`, `measure-p6.json` - metric outputs (matched/raw sets).
- `transform-rename.py`, `transform-place.py` - the two transforms with asserts.
- `SHA256SUMS`.

## Remaining in pump_quote.rs (for follow-up)

The deployed cluster also carries 61:6024, 62:6105, 90:6100 (walk's depth /
eligibility checks, split out as helpers in the deployed), convert's 104/106/
117/119/121/122, and the validation families at 279-415. Their windows need the
deployed's helper decomposition (walk's checks live partly in create_v2.rs in the
deployed). The full closure map above is the work list.
