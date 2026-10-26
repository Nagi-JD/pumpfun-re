# 08 — Creator cluster (`collect_creator_fee`, `distribute_fee_to_holders`, `set_metaplex_creator`, `set_creator`, `admin_cto`, `migrate_bonding_curve_creator`)

Binary: `D:/dev/ext/pumpfun-source/evidence/original/pump/deployed.so`
Recovered source: `D:/dev/ext/pumpfun-source/programs/pump/src/` (`lib.rs` for `collect_creator_fee` + the `CollectCreatorFee` ctx; `holder_distribution.rs`; `set_creator.rs`; `admin_cto.rs`; `creator_migration.rs`)
Tool: `py -3.12 D:/dev/pumpfun-re/sbftool.py …`

> NOTE on source layout: the task referenced a `creator/` sub-directory with per-handler files
> (`collect_creator_fee.rs`, `distribute_fee_to_holders.rs`, `set_metaplex_creator.rs`). That
> directory does **not** exist in this checkout. The handlers live in `lib.rs`
> (`collect_creator_fee`, inline at `lib.rs:114`), `holder_distribution.rs`
> (`distribute_fee_to_holders` → `execute`), `set_creator.rs` (`set_creator`→`set`,
> `set_metaplex_creator`→`sync`), `admin_cto.rs`, and `creator_migration.rs`
> (`migrate_bonding_curve_creator`→`execute`). All verification below is against those files.

## Error-code model (verified)

Anchor custom codes are `6000 + variant_index` of `PumpError` (enum in `lib.rs`, 110 variants, 6000–6109).
Codes referenced in this cluster (computed from the enum, cross-checked against the raw `err()` numbers
hard-coded in `admin_cto.rs`):

| hex | dec | PumpError |
|---|---|---|
| `0x1783` | 6019 | `InvalidCreator` |
| `0x178e` | 6030 | `CreatorShouldNotBeZero` |
| `0x17bd` | 6077 | `CreatorFeeNotConfigurable` |
| `0x17be` | 6078 | `CreatorFeeBpsOutOfRange` |
| `0x17c0` | 6080 | `CreatorFeeNotAllowedForCashbackCoin` |
| `0x17c3` | 6083 | `HolderRewardCreatorImmutable` |
| `0x17c4` | 6084 | `HolderRewardDisabled` |
| `0x17c5` | 6085 | `HolderRewardRecipientsMismatch` |
| `0x17c8` | 6088 | `CtoNotAllowedForMayhemCoin` |
| `0x17c9` | 6089 | `CtoNewCreatorRequired` |
| `0x17ca` | 6090 | `CtoNewCreatorNotAllowed` |
| `0x17cb` | 6091 | `CreatorFeeNotConfigurableForQuote` |
| `0x17cc` | 6092 | `CtoCreatorAccountNotWritable` |
| `0x17cf` | 6095 | `CreatorFeesNotSwept` |
| `0x7d0` | 2000 | anchor `ConstraintMut` |
| `0x7d6` | 2006 | anchor `ConstraintSeeds` |

Two lowering idioms appear in the binary:
- **AnchorError (standard `require!`/`error!`)**: `stw [r10 -0x238], <code>` into the AnchorError
  scratch, followed by file/line fields and a call to the error builder (`0x33766`/`0x33777`). The
  error-code immediate is directly observable. Used by `distribute`, `migrate`, **and the deployed
  `admin_cto`**.
- **Anchor seed/mut/has_one constraints**: materialized inside the generated `try_accounts`, as
  `mov r2, 0x7d6`/`0x7d0` (code passed to the constraint logger), never in `execute`.

## Dispatch map (verified from the binary)

| Handler | Anchor disc (8 bytes) | disc lddw @ | wrapper (log/try_accounts/call) @ | real `execute` @ | log string (vaddr, len) |
|---|---|---|---|---|---|
| `collect_creator_fee` | `1416567bc61cdb84` | `0x2377b` | `0x2586e` | `0x5316` | `Instruction: CollectCreatorFee` (`0x1b7edc`, 0x1e) |
| `distribute_fee_to_holders` | `623691610246ad2b` | `0x23783` | `0x258fa` | `0x68ab` | `Instruction: DistributeFeeToHolders` (`0x1b7efa`, 0x23) |
| `set_metaplex_creator` | `8a60aed93055c5f6` | `0x23787` | `0x259f2` | `0x74f7` | `Instruction: SetMetaplexCreator` (`0x1b7f1d`, 0x1f) |
| `set_creator` | `fe94ff70cf8eaaa5` | `0x2378b` | `0x25a82` | `0x71f8` | `Instruction: SetCreator` (`0x1b7f3c`, 0x17) |
| `admin_cto` | `7d7ed6864de5bc59` | `0x2378f` | `0x25b40` | `0x4542` | `Instruction: AdminCto` (`0x1b7f53`, 0x15) |
| `migrate_bonding_curve_creator` | `577c34bf3426d6e8` | `0x237b3` | `0x26118` | `0x6fc1` | `Instruction: MigrateBondingCurveCreator` (`0x1b807a`, 0x27) |

The address the task supplied for each handler (e.g. `collect_creator_fee@0x2586e`) is the Anchor
`__global` **wrapper** (log instruction name → `try_accounts` → call `execute` → emit/return). Each
wrapper's `execute` target was taken from the single resolved call in its body and confirmed exclusive:
`sbftool callers <execute>` returns exactly one caller = its own wrapper (e.g. `callers 0x5316` →
`0x258a4`; `callers 0x4542` → `0x25bf8`; `callers 0x6fc1` → `0x2614d`). The `Instruction:` strings are
present in rodata (`grep -a` on the `.so`) and their lengths match the `mov r2, <len>` in each wrapper,
positively identifying all six.

---

## 1. `collect_creator_fee` — wrapper `0x2586e`, execute `0x5316`

### 1.1 Purpose
Sweeps the native-SOL creator-fee vault to the creator wallet. Legacy (SOL-only) path; the token/
sharing-config path is `collect_creator_fee_v2`/`distribute_creator_fees`.

### 1.2 Accounts validated (`CollectCreatorFee`, `lib.rs:492`)
- `creator` — `mut`, `UncheckedAccount` (payout destination; bound only through the vault seed).
- `creator_vault` — `mut`, PDA `["creator-vault", creator]`.
- `system_program`.
No `has_one`, no custom-error account constraints. Seeds enforced in `try_accounts` (`0x17878`).

### 1.3 require! conditions + ORDER
`collect_creator_fee` has **no `require!`** — it uses early `Ok(())` returns with `msg!` logs, not
errors. Verified: execute `0x5316` contains **zero** error-code immediates (grep of `e_collect.txt` for
`0x17xx`/`0x7dx` = none). Control flow:
1. `0x5343 ldxb r1,[r8 +0x32]` (read `creator.executable`) → `0x5344 jne r1,0,+0x13`: if executable,
   branch to `Ok` (matches `if ctx.accounts.creator.executable { msg!(…); return Ok(()) }`,
   `lib.rs:115`). The skipped block logs via `0x2ae70`/`0x359c3` (string `0x1b5fa4`, len 0x37).
2. amount = `creator_vault.lamports() − rent_minimum(0)`; `== 0` → `msg!` + `Ok` (no error).

### 1.4 CPIs
One `system_program::transfer` signed by the `creator-vault` PDA (`["creator-vault", creator, bump]`),
amount = swept lamports. (Source `lib.rs:118`.)

### 1.5 State writes
None to any program account. Emits `CollectCreatorFeeEvent{timestamp, creator, creator_fee=amount,
quote_mint=Pubkey::default()}` (`emit!` + `emit_cpi!`).

### 1.6 GAP vs recovered source
**No gap.** execute `0x5316` matches `lib.rs:114-121`: executable guard → amount computation →
single signed native transfer → event; no custom errors. `sbftool func 0x5316` = 61 insns, consistent
with the tiny source body.

---

## 2. `distribute_fee_to_holders` — wrapper `0x258fa`, execute `0x68ab`

### 2.1 Purpose
Holder-reward payout: from the `holder-rewards` PDA, pay a list of `amounts` to a parallel list of
recipient accounts (native SOL) or recipient ATAs (token quote), creating missing ATAs and closing the
native wSOL token account. Authority-gated to `global.holder_reward_claim_authority`.

### 2.2 Accounts validated (`DistributeFeeToHolders`, `holder_distribution.rs`)
- `global` — PDA `["global"]`, `has_one = holder_reward_claim_authority @ NotAuthorized`.
- `holder_reward_claim_authority` — `mut` signer.
- `mint` — `UncheckedAccount` (identifies rewards PDA).
- `holder_rewards` — `mut`, PDA `["holder-rewards", mint]`.
- `holder_rewards_token_account` — optional `InterfaceAccount<TokenAccount>`.
- `quote_mint`, `quote_token_program`, `associated_token_program`, `system_program`.
- `remaining_accounts`: `2 × amounts.len()` (recipient + recipient-ATA pairs).

### 2.3 require! conditions + ORDER
1. **`remaining_accounts.len() == amounts.len()*2`** → `HolderRewardRecipientsMismatch` (6085).
   Verified: execute `0x68ab` opens by loading `amounts.len()` (`0x68ad ldxdw r3,[r8 +0x10]`),
   doubling it (`0x68af lsh64 r1,0x1`), loading the remaining-account count (`0x68b2 ldxdw r4,[r2 +0x18]`),
   and `0x68b4 jeq r4,r1,+0x3e`: equal → skip the error block. Error emitted at
   `0x68e6 stw [r10 -0x1a8], 0x17c5` (= 6085). Matches `holder_distribution.rs` `require!(…==…*2, …)`.
   (NOTE: the error slot here is `-0x1a8`, not the `admin_cto` slot `-0x238`; same AnchorError idiom,
   different frame offset.)
2. Token-branch owner/mint/token-program checks on the optional source
   (`ConstraintTokenOwner`/`ConstraintTokenMint`/`ConstraintTokenTokenProgram`), `Overflow` on
   `checked_add`, `HolderRewardsRentFloor`, `HolderRewardTokenAccountMissing` — see §2.6.

### 2.4 CPIs (per source, structurally confirmed)
- native quote: `close_account` of the wSOL source to `holder_rewards`; then per recipient a
  `system_instruction::transfer` from `holder_rewards` (PDA-signed) for non-zero amounts.
- token quote: per recipient, idempotent ATA create (raw ATA-program `invoke_signed` with `data:[0]`)
  when `pair[1]` empty, then `transfer_checked` from the source ATA (PDA-signed).
execute `0x68ab` is 906 insns with the branch/loop structure and the signed-CPI setup consistent with
this (the native/token split and the length guard are confirmed at the head).

### 2.5 State writes
No in-place byte writes to program accounts; lamport/token movements only. Emits
`DistributeFeeToHoldersEvent{timestamp, mint, quote_mint, recipients, total}`.

### 2.6 GAP vs recovered source
**Primary guard + shape match; secondary guards not individually located as immediates.** The headline
`HolderRewardRecipientsMismatch` guard and the length-check arithmetic match the source exactly. The
remaining require-codes expected from the source — `ConstraintTokenOwner` (2017 `0x7e1`),
`ConstraintTokenMint` (2015 `0x7df`), `ConstraintTokenTokenProgram` (2019 `0x7e3`), `Overflow`
(6024 `0x1788`), `HolderRewardsRentFloor` (6086 `0x17c6`), `HolderRewardTokenAccountMissing`
(6087 `0x17c7`) — were **not** found as literal immediates in `e_distribute.txt`. Most plausibly they
are lowered through anchor's generic `require_keys_eq!`/`ok_or` error builders that embed the code
out of the immediate stream, or sit deeper in the 906-insn body than was traced. **Not confirmed as a
divergence** — flagged as the one un-exhausted part of this handler (would need full instruction trace
of `0x68ab`).

---

## 3. `set_metaplex_creator` — wrapper `0x259f2`, execute `0x74f7`

### 3.1 Purpose
One-shot sync of the bonding-curve `creator` field from the Metaplex metadata's first creator, but only
while the curve's creator is still unset. Permissionless (no signer/has_one).

### 3.2 Accounts validated (`SetMetaplexCreator`, `set_creator.rs`)
- `mint` — `InterfaceAccount<Mint>`.
- `metadata` — PDA `["metadata", METAPLEX, mint]`, `seeds::program = METAPLEX`
  (`metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s`); custom `CreatorMetadata` deser that requires
  metadata key byte `== 4`.
- `bonding_curve` — `mut`, PDA `["bonding-curve", mint]`, custom `SetterCurve` deser.

### 3.3 require! conditions + ORDER
No `PumpError` errors. Guard is an early `Ok` return:
1. **`bonding_curve.creator == Pubkey::default()`** gate. Verified: execute `0x74f7` loads the curve
   struct (`0x74f9 ldxdw r9,[r7 +0x8]`), zeroes a 32-byte scratch (`0x74fa-0x74fd`), `memcmp`s the
   curve creator at struct `+0x1e8` against zero via `0x366cf` (`r3=0x20`, `0x7504`), and
   `0x7507 jne r0,0,+0x9`: non-zero (creator already set) → branch out to `Ok`. Matches
   `set_creator.rs` `sync()`: `if a.bonding_curve.creator != default { return Ok(()) }`.
2. then `0x7508 ldxdw r1,[r9 +0x48]` vs `i64::MIN` sentinel (`0x7509 lddw … -0x8000000000000000`)
   = the `Option<Vec<MetadataCreator>>` None discriminant; `Some` → set creator from `creators[0]`.

### 3.4 CPIs
None. (emit helpers `0xb45`/`0x526` from the wrapper are `emit!`/`emit_cpi!`, not external CPIs.)

### 3.5 State writes
`bonding_curve.creator = metadata.creators[0].address` (via `SetterCurve::try_serialize`, writing
offset 49..81). Emits `SetMetaplexCreatorEvent{timestamp, mint, bonding_curve, metadata, creator}`.

### 3.6 GAP vs recovered source
**No gap.** execute `0x74f7` = 26 insns, matching the small `sync()` body: default-creator gate →
Option-None sentinel check → conditional write + event. No error path.

---

## 4. `set_creator` — wrapper `0x25a82`, execute `0x71f8`

### 4.1 Purpose
Authority-gated one-shot creator initialization. Like §3 but signed by `global.set_creator_authority`,
and falls back to the caller-supplied `creator` argument when the Metaplex metadata carries no creators.

### 4.2 Accounts validated (`SetCreator`, `set_creator.rs`)
- `set_creator_authority` — signer.
- `global` — PDA `["global"]`, `has_one = set_creator_authority @ NotAuthorized` (6000).
- `mint` — `InterfaceAccount<Mint>`.
- `metadata` — PDA `["metadata", METAPLEX, mint]`, `seeds::program = METAPLEX`, `CreatorMetadata`
  (key byte `== 4`).
- `bonding_curve` — `mut`, PDA `["bonding-curve", mint]`, `SetterCurve`.

### 4.3 require! conditions + ORDER
Same early-`Ok` gate as §3 (no `PumpError`). Verified: execute `0x71f8` loads the curve (`0x71fb`),
memcmps creator at `+0x1e8` vs zero (`0x7206`), `0x7209 jne r0,0,+0x34`: already-set → `Ok`. It also
pre-loads the metadata first-creator (`[r6 +0x178]`, `0x720a-0x7213`) and the argument creator
(`[r6 +0x1e0]`, `0x7214-0x721d`), then branches on the `Option` None sentinel (`0x721e ldxdw r1,[r6 +0x48]`
vs `i64::MIN`, `0x7221`): `Some` → use `creators[0]`; `None` → copy the argument (`0x7223-0x722a`
move the 32-byte arg). Matches `set()` exactly. `has_one` (NotAuthorized) is enforced in `try_accounts`
(`0x1917f`), not execute.

### 4.4 CPIs
None.

### 4.5 State writes
`bonding_curve.creator = creators[0].address` (metadata present) **or** `= creator` arg (metadata
empty), offset 49..81. Emits `SetMetaplexCreatorEvent` (metadata branch) or `SetCreatorEvent`
(argument branch) — two distinct event shapes, matching source.

### 4.6 GAP vs recovered source
**No gap.** execute `0x71f8` = 71 insns, matching `set()`: default gate → Option split (metadata vs
argument) → conditional write + corresponding event.

---

## 5. `admin_cto` — wrapper `0x25b40`, execute `0x4542`  ⚠ DIVERGENCE

### 5.1 Purpose
Admin community-takeover: reassigns a coin's creator (to a new creator, or to the holder-rewards PDA),
optionally reconfigures the creator fee, sweeps the old creator vault (native or token, incl. the
pump-amm coin-creator vault), resets the pump-fees sharing-config, and updates the pump-amm pool's
coin-creator. Gated to `global.admin_set_creator_authority`.

### 5.2 Accounts validated (`AdminCto`, `admin_cto.rs`, ~30 accounts)
`try_accounts` @ `0x16caf` is **2855 insns** — it validates the full account set. Confirmed error codes
there are anchor `ConstraintSeeds` (`0x7d6`, 2006) and `ConstraintMut` (`0x7d0`, 2000), appearing
~26× combined (one per PDA `seeds`/`mut` constraint: `global`, `bonding_curve`,
`current_creator_quote_token_account`, `creator_vault(+ata)`, `holder_creator_vault(+ata)`,
`amm_global_config`, `pool_authority`, `pool`, `pump_amm_event_authority`,
`coin_creator_vault_authority(+ata)`, `sharing_config`, `pump_fees_event_authority`,
`event_authority`). The source's `has_one = admin_set_creator_authority @ NotAuthorized`,
`current_creator.key()==bonding_curve.creator @ InvalidCreator`, and
`quote_mint @ MintDoesNotMatchBondingCurve` constraints are account-level; their custom codes
(`0x1770`/`0x1783`/`0x1774`) were **not** observed as immediates in `try_accounts` (grep = none),
so those three are either folded or lowered via anchor's generic constraint path. Program-id accounts
(`pump_amm`=`pAMM…fXEA`, `pump_fees`) are `Program`-typed address checks.

### 5.3 require! conditions + ORDER — binary vs source **DO NOT MATCH**
The deployed `admin_cto` uses the **standard AnchorError idiom** (`stw [r10 -0x238], <code>`), whereas
the recovered `admin_cto.rs` models every guard with a custom `fn err(n)->Error` = `ProgramError::Custom(n)`.
That is itself a structural difference (reconstruction artifact), but more importantly the **guard set and
order differ**.

**Binary guard-emit order** (addresses from `sbftool func 0x4542`, each `stw [r10 -0x238], <code>`):

| # | addr | code | PumpError |
|---|---|---|---|
| 1 | `0x4654` | `0x17c3` | `HolderRewardCreatorImmutable` (6083) |
| 2 | `0x468c` | `0x17ca` | `CtoNewCreatorNotAllowed` (6090) |
| 3 | `0x471d` | `0x17c9` | `CtoNewCreatorRequired` (6089) |
| 4 | `0x4752` | `0x17c4` | `HolderRewardDisabled` (6084) |
| 5 | `0x4780` | `0x17cb` | `CreatorFeeNotConfigurableForQuote` (6091) |
| 6 | `0x479e` | `0x1783` | `InvalidCreator` (6019) |
| 7 | `0x47b8` | `0x178e` | `CreatorShouldNotBeZero` (6030) |
| 8 | `0x4800` | `0x17c0` | `CreatorFeeNotAllowedForCashbackCoin` (6080) |
| 9 | `0x481f` | `0x17be` | `CreatorFeeBpsOutOfRange` (6078) |
| 10 | `0x4839` | `0x17bd` | `CreatorFeeNotConfigurable` (6077) |
| 11 | `0x48c4` | `0x17cf` | `CreatorFeesNotSwept` (6095) |

**Source guard order** (`admin_cto.rs::execute`, `err(n)` calls): `6088`(mayhem) → `6083` → `6084` →
`6090` → `6089` → `6030` → `6019` → `6091` → `6077` → `6078` → later `6092`(×2) + anchor `2006`.

**Concrete gaps (binary is authoritative):**
- **`CtoNotAllowedForMayhemCoin` (6088) is ABSENT from the binary.** Source's very first guard
  (`if flag(81) { return err(6088) }`) does not appear anywhere in `admin_cto`'s wrapper, `try_accounts`,
  or `execute` (grep for `0x17c8` across all three = 0). The error string is in the global error table
  (rodata), but no reachable guard in this handler raises it.
- **`CtoCreatorAccountNotWritable` (6092) is ABSENT** from the binary `admin_cto` code (grep `0x17cc`
  = 0), despite the source raising it twice in the wallet-payout block.
- **`CreatorFeeNotAllowedForCashbackCoin` (6080) is PRESENT in the binary** (guard #8, `0x4800`) but is
  **not** raised anywhere in the recovered `admin_cto.rs` (source gates cashback only via `flag(82)` in
  the emitted event, never as an error).
- **`CreatorFeesNotSwept` (6095) is PRESENT in the binary** (guard #11, `0x48c4`) but the recovered
  `admin_cto.rs` never raises it (6095 appears only in `creator_migration.rs`).
- **Ordering differs** even for the shared guards: binary has `6090`/`6089` before `6084`
  (source: `6084` before `6090`/`6089`); binary has `6091` before `6019`/`6030` (source: after);
  binary has `6078` before `6077` (source: `6077` before `6078`); binary has `6019` before `6030`
  (source: `6030` before `6019`).

Conclusion: the recovered `admin_cto.rs` is **not a faithful match** of the deployed `admin_cto`. The
set/order divergence plus the `err()`-vs-`require!` lowering indicate the two are different program
revisions (the deployed version drops the mayhem/writable guards and adds cashback-fee + fees-swept
guards). *Caveat:* the order above is the address order of the AnchorError-emit blocks; for the shared
guards this normally mirrors the source check order (each `require!` emits inline), but it was not
cross-verified against the condition-read order for every guard. The **set-level** differences
(6088/6092 absent, 6080/6095 present) are unconditional — they hold regardless of ordering.

### 5.4 CPIs (per source; present but not each individually decoded)
`execute 0x4542` has 47 call sites (`sbftool func`). Source performs up to four `invoke_signed` CPIs:
(a) pump-amm "collect coin-creator fee" (disc `[1,33,78,185,33,67,44,92]`), (b) pump-amm "set
coin-creator" when a wallet payout happens (`[160,57,89,42,181,139,43,66]`), (c) pump-fees reset
sharing-config (`[60,100,144,156,64,138,182,37]`), (d) pump-amm update-pool coin-creator
(`[45,61,165,151,104,0,49,189]`), plus `system_program::transfer` sweeps and `create_idempotent` ATA
creates. These CPIs live in the tail of the 886-insn `execute` (after the guard block ending `0x48c4`);
they were **not** decoded instruction-by-instruction here. The source's `6092`/`2006` guards sit inside
that same wallet-payout / holder-vault block — their absence as immediates (§5.3) is therefore either a
genuine removal or logic that the trace did not reach; **flagged, not fully resolved.**

### 5.5 State writes (per source)
Bonding-curve in-place byte writes: `creator` ← target at offset `49..81`; `d[123]=0`; `d[124]=holder`;
`fee` ← `d[115..123]` when a fee is supplied; realloc of the curve to 166 bytes with a rent top-up.
Emits `AdminCtoEvent{…}`. These writes were not re-verified at the byte level against the binary tail.

---

## 6. `migrate_bonding_curve_creator` — wrapper `0x26118`, execute `0x6fc1`

### 6.1 Purpose
Migrates a (non-holder-reward) coin's creator to its pump-fees sharing-config PDA, provided all creator
fees have already been swept. Permissionless (no signer; constraints bind the sharing-config to the
curve's current creator).

### 6.2 Accounts validated (`MigrateBondingCurveCreator`, `creator_migration.rs`)
- `mint` — `InterfaceAccount<Mint>`.
- `bonding_curve` — `mut`, PDA `["bonding-curve", mint]`, custom `MigratingCurve` deser.
- `sharing_config` — PDA `["sharing-config", mint]`, `seeds::program = FEES`,
  `has_one = mint @ MintDoesNotMatchBondingCurve`,
  `constraint = bonding_curve.creator == sharing_config.admin @ BondingCurveAndSharingConfigCreatorMismatch`.
- `event_authority` PDA `["__event_authority"]`, `program`.

### 6.3 require! conditions + ORDER — **MATCHES source**
Verified in execute `0x6fc1`:
1. **`!bonding_curve.holder`** → `HolderRewardCreatorImmutable` (6083). `0x6fc3 ldxb r1,[r7 +0x1ed]`
   (the `holder` byte) → `0x6fc4 jne r1,0,+0x1b`: holder set → error. Code emitted at
   `0x7011 stw [r10 -0xd8], 0x17c3` (= 6083).
2. **`bonding_curve.creator_fee == 0`** → `CreatorFeesNotSwept` (6095). `0x6fc5 ldxdw r1,[r7 +0x1c0]`
   (the `creator_fee` u64) → `0x6fc6 jeq r1,0,+0x73`: zero → continue; non-zero → error at
   `0x702d stw [r10 -0xd8], 0x17cf` (= 6095).

Condition-read order (holder first `0x6fc3`, fee second `0x6fc5`) **and** error-emit order match the
source `require!(!holder, …); require!(creator_fee==0, …)` exactly. Uses the standard AnchorError idiom
(error slot `-0xd8`).

### 6.4 CPIs
None (only `emit!`/`emit_cpi!` via wrapper helpers `0xb45`/`0x526`).

### 6.5 State writes
`bonding_curve.creator = sharing_config.key()` (via `MigratingCurve::try_serialize`, offset 49..81).
Emits `MigrateBondingCurveCreatorEvent{timestamp, mint, bonding_curve, sharing_config, old_creator,
new_creator=sharing_config.key()}`.

### 6.6 GAP vs recovered source
**No gap.** execute `0x6fc1` = 286 insns; both guards present in the correct order with the correct
codes, followed by the single creator write and the event. The `has_one`/`constraint` account checks are
in `try_accounts` (`0x18e92`).

---

## Summary of gaps

| Handler | Verdict |
|---|---|
| `collect_creator_fee` | **Match** — no custom errors; executable guard + single signed native transfer + event. |
| `distribute_fee_to_holders` | **Match (primary)** — `HolderRewardRecipientsMismatch` + len check + native/token branch confirmed; 6 secondary constraint/overflow/rent codes not located as immediates (likely generic-builder lowering), not a confirmed divergence. |
| `set_metaplex_creator` | **Match** — default-creator gate → Option-None check → write + event. |
| `set_creator` | **Match** — default gate → metadata-vs-argument split → write + two event shapes. |
| `admin_cto` | **DIVERGENCE** — binary guard set/order ≠ source: **6088 (mayhem) and 6092 (not-writable) ABSENT** from the deployed handler; **6080 (cashback-fee) and 6095 (fees-not-swept) PRESENT** but not in source; several shared guards reordered; binary uses `require!`/AnchorError, source uses a `ProgramError::Custom` `err()` helper. CPI tail (4 `invoke_signed`) and byte-level curve writes not exhaustively decoded. |
| `migrate_bonding_curve_creator` | **Match** — both guards (6083 then 6095) in correct read+emit order; single creator write to sharing-config + event. |
