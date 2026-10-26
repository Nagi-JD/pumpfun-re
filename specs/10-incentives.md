# 10 — Token Incentives & Cashback handlers (reverse-engineered)

Target binary: `D:/dev/ext/pumpfun-source/evidence/original/pump/deployed.so`
Tool: `py -3.12 D:/dev/pumpfun-re/sbftool.py …`
Recovered reference source (faithful PumpSwap port): `programs/pump/src/incentives.rs`,
`programs/pump/src/cashback.rs`, `programs/pump/src/volume_sync.rs`.

COMPLETION.md marks `admin_update_token_incentives` and `claim_token_incentives`
UNRECOVERED. Both are PRESENT in the deployed dispatch; this file reconstructs
them from the binary. `claim_cashback` / `claim_cashback_v2` are recovered —
done here as a GAP check against `cashback.rs`.

## Dispatch summary (all four VERIFIED against the binary)

`sbftool disc deployed.so global:<name>`:

| Handler | Anchor discriminator (8-byte) | Dispatch stub | `sol_log_` ix string (verified bytes in .rodata) |
|---|---|---|---|
| admin_update_token_incentives | `d10b7357d5177ccc` | `0x25c54` | `"Instruction: AdminUpdateTokenIncentives"` @0x1b7f68 (len 0x27) |
| claim_token_incentives | `1004471ccc01281b` | `0x25d0e` | `"Instruction: ClaimTokenIncentives"` @0x1b7f8f (len 0x21) |
| claim_cashback | `253a237ebe35e4c5` | `0x25d99` | `"Instruction: ClaimCashback"` @0x1b7fb0 (len 0x1a) |
| claim_cashback_v2 | `7af3cc415e741d37` | `0x25e2a` | `"Instruction: ClaimCashbackV2"` @0x1b7fca (len 0x1c) |

Every stub follows the same shape (`dis 0x25c54 …`): save args → `lddw r1,<ixstr>; mov r2,<len>; call sol_log_`
→ `call <try_accounts>` → run/inline the handler body → serialize accounts back
→ exit. The try_accounts targets are the generated `__global::*` functions:
admin→`0x1e276` (`call -0x7a06` @25c7b), claim_token→`0x1e986` (`call -0x739e` @25d23),
claim_cashback→`0x1f1a0` (`call -0x6c0e` @25dad), claim_cashback_v2→`0x1f375` (`call -0x6acb` @25e3f).

Event discriminators (`sbftool disc event:*`): `AdminUpdateTokenIncentivesEvent`
`93fa6c78f71d43de` (emit helper 0xe8d5, built at 0xe937/0xe98b); `ClaimTokenIncentivesEvent`
`4facf631cd5bcee8` (emit helper 0xebd8, lddw of −0x1731a432ce0953b1 = LE `4f ac f6 31 cd 5b ce e8`
@0xec28/0xec7d); `ClaimCashbackEvent` `e2d6f62107f293e5` (emit helper 0x1f662, lddw @0x1f677);
`SyncUserVolumeAccumulatorEvent` `c57aa77c74515bff` (emit @0xf6af/0xf6fb).

## Shared account structs (VERIFIED)

`GlobalVolumeAccumulator` — in-memory/struct offsets confirmed by `admin()` reading
`gva.mint` at **struct +0x18** (`0x1e63b: ldxdw r6,[r9+0x18]`, then 32-byte memcmp `call 0x366cf`):

| field | struct off | account-data off (+8 disc) |
|---|---|---|
| start_time: i64 | 0x00 | 0x08 |
| end_time: i64 | 0x08 | 0x10 |
| seconds_in_a_day: i64 | 0x10 | 0x18 |
| mint: Pubkey | **0x18** | 0x20 |
| total_token_supply: [u64;30] | 0x38 | 0x40 |
| sol_volumes: [u64;30] | 0x128 | 0x130 |

Matches `volume_sync.rs::GlobalVolumeAccumulator` exactly.

`UserVolumeAccumulator` (space=137, `lib.rs:472`) — in-memory offsets observed in the
cashback bodies: `cashback_earned` @ **+0x58**, `total_cashback_claimed` @ **+0x60**
(`0xee59: stxdw [r8+0x60],r9` ; `0xee5a: ldxdw r1,[r8+0x58]`). Declared field order
(`lib.rs:465`): user, needs_claim, total_unclaimed_tokens, total_claimed_tokens,
current_sol_volume, last_update_timestamp, has_total_claimed_tokens, cashback_earned,
total_cashback_claimed, stable_cashback_earned, total_stable_cashback_claimed.

---

## admin_update_token_incentives @ 0x25c54 (UNRECOVERED — reconstructed)

**1. Purpose.** Authority-gated configuration of the global PumpSwap-style volume-reward
schedule: sets the mint, the day length, the active [start_time,end_time) window, and
per-day token-supply / resets per-day sol-volume buckets. Signature (`lib.rs:96`):
`admin(ctx, start_time:i64, end_time:i64, seconds_in_a_day:i64, day_number:u64, pump_token_supply_per_day:u64)`.

**2. Accounts validated (VERIFIED, in order).** The generated try_accounts `0x1e276`
deserializes and name-tags each account; the account-name strings it loads are the
proof (`strres`):

`authority`(0x1b7369) signer+mut · `global`(0x1b7326) PDA seeds `["global"]`, `has_one=authority`
→ `NotAuthorized` · `global_volume_accumulator`(0x1b7037) mut, PDA `["global_volume_accumulator"]`
· `mint`(0x1b5f48) · `global_incentive_token_account`(0x1b791f) **init_if_needed** ATA
(mint=`mint`, authority=`global_volume_accumulator`) · `associated_token_program`(0x1b74c1)
· `system_program`(0x1b735b) · `token_program`(0x1b759e) · `event_authority`(0x1b732c)
· `program`(0x1b7354). Helper `0x1e637` performs the ATA validation: it reads
`gva.mint` (+0x18) and memcmps it against the all-zero Pubkey @0x1b5ba8 (32 bytes of
`\0`, i.e. the “uninitialized/empty mint” sentinel), using `"global_incentive_token_account"`
as the error context. This exactly matches the `AdminUpdateTokenIncentives<'info>`
struct in `incentives.rs:7-19`.

**3. Error / require! conditions + ORDER (VERIFIED present).** All eight schedule
error variants exist in the `PumpError` Display table (function `0x2bd95`); `xref` of
each string to its table slot:

`StartTimeInThePast`@0x1b849f · `EndTimeInThePast`@0x1b65f0 · `EndTimeBeforeStartTime`@0x1b84b1
· `TimeRangeTooLarge`@0x1b84c7 · `EndTimeBeforeCurrentDay`@0x1b84d8 · `SupplyUpdateForFinishedRange`@0x1b84ef
· `DayIndexAfterEndIndex`@0x1b850b · `DayInActiveRange`@0x1b6650 · (`InvalidIncentiveMint`@0x1b8520, used by claim).
Their presence and naming confirm the require! set and ordering of `incentives.rs:26-50`.

**4. CPIs.** On the init_if_needed path the ATA-program `create`/`idempotent` CPI runs
through `0x1e276`/`0x1e637` (associated_token_program + system_program + token_program
are in the context precisely for this). No value transfer; admin only mutates the
accumulator and emits.

**5. State writes.** `admin()` logic runs after try_accounts (inlined into the
`0x25c54` body) via an indirect `callx` (`0x25c8e`), then calls the event emit helper
`0xe8d5` (`0x25cc2: call 0xe8d5`) and the serialize/cleanup `0x1e8cf` (`0x25ccb`).
It writes `GlobalVolumeAccumulator`: `mint` (+0x18), `seconds_in_a_day` (+0x10),
`start_time` (+0x00), `end_time` (+0x08), and the two `[u64;30]` arrays
`total_token_supply` (+0x38) and `sol_volumes` (+0x128).

**Reconstructed behavior.**
- Account layout: as §2; `global_volume_accumulator` is the single mutated state PDA.
- Schedule math (from binary error set + recovered port `incentives.rs:20-55`):
  `g.mint = mint.key(); g.seconds_in_a_day = seconds_in_a_day`. If `start_time!=0 &&
  end_time!=0`: when `start_time != g.start_time` require `start_time > now`
  (`StartTimeInThePast`) and zero both arrays and set `g.start_time`; require
  `end_time > now` (`EndTimeInThePast`), `end_time > start_time`
  (`EndTimeBeforeStartTime`), `end_time-start_time < seconds_in_a_day*30`
  (`TimeRangeTooLarge`); set `g.end_time`; if `now > g.start_time` compute
  `current=(now-start)/day`, `end=(end-start)/day`, require `end>current`
  (`EndTimeBeforeCurrentDay`) and zero `sol_volumes[current+1..=end]`.
  If `pump_token_supply_per_day>0`: require `now <= g.end_time`
  (`SupplyUpdateForFinishedRange`); if `day_number<30` require
  `day_number<=end` (`DayIndexAfterEndIndex`) and `day_number>=current`
  (`DayInActiveRange`) then set `total_token_supply[day_number]=supply`; else
  (day_number>=30) set `total_token_supply[current..=end]=supply` for the whole active range.
- Transfers: none (config only; the only CPI is the idempotent ATA create).
- Emits `AdminUpdateTokenIncentivesEvent{start_time,end_time,day_number,
  token_supply_per_day,mint,seconds_in_a_day,timestamp}` (disc `93fa6c78f71d43de`,
  helper `0xe8d5`) via both `emit!` and `emit_cpi!`.

Conclusion: the deployed handler matches `incentives.rs::admin` — account set, struct
layout, the full 8-condition schedule guard set, and the event are all confirmed in the binary.

---

## claim_token_incentives @ 0x25d0e (UNRECOVERED — reconstructed)

**1. Purpose.** Settles a user's accrued volume reward: rolls the user volume
accumulator forward against the global schedule, then transfers the owed incentive
tokens from the program's `global_incentive_token_account` to the user's ATA.
`lib.rs:97` → `incentives::claim(ctx)`.

**2. Accounts validated (VERIFIED).** try_accounts `0x1e986`. From `incentives.rs:58-78`
and the account-name strings in that function: `user`(AccountInfo, PDA-seed + event name)
· `user_ata` **init_if_needed** ATA(mint=`mint`, authority=`user`) · `global_volume_accumulator`
PDA `["global_volume_accumulator"]`, `has_one=mint` → `InvalidIncentiveMint`
(@0x1b8520, present in binary) · `global_incentive_token_account` mut, ATA(mint,
authority=global_volume_accumulator) · `user_volume_accumulator` mut, PDA
`["user_volume_accumulator", user]` · `mint` · `token_program` · `system_program`
· `associated_token_program` · `event_authority` · `program` · `payer` signer+mut.

**3. Error / require! + ORDER (VERIFIED).** Zero-reward early exit logs **"No tokens to
claim"** (@0x1b7025, referenced at insn **0xe41d** — `xref2`) then returns Ok, matching
`incentives.rs:112`. Reward math uses the shared volume-accumulator updater (truncation
guarded → `Truncation`, overflow → `"Unexpected overflow"` panic string @ the
`token_incentives/volume_accumulator.rs` path; both strings present in .rodata). Order:
roll-forward update → compute `amount` → `amount==0`? return → transfer → post-state.

**4. CPIs.** `token_interface::transfer_checked` on `token_program`, signed by the
`global_volume_accumulator` PDA (`seeds = ["global_volume_accumulator", bump]`), moving
`amount` (`mint.decimals`) from `global_incentive_token_account` → `user_ata`
(`incentives.rs:113-114`). Plus the idempotent `user_ata` ATA-create CPI on the
init_if_needed path.

**5. State writes (`user_volume_accumulator`).** Per the roll-forward + settlement
(`incentives.rs:82-115`): `user`, and on settlement `total_unclaimed_tokens=0`,
`total_claimed_tokens += amount`, `has_total_claimed_tokens=true`,
`needs_claim = current_sol_volume>0`, `last_update_timestamp=timestamp`; the stale-day
reset path may set `total_claimed_tokens=0`, `has_total_claimed_tokens=false`.

**Reconstructed behavior.**
- Account layout: as §2; reads `global_volume_accumulator` (read-only schedule),
  mutates `user_volume_accumulator`, pays out of `global_incentive_token_account`.
- Amount math: `u.user = user.key()`. If `now < g.start_time && u.last_update < g.start_time`
  → reset claimed. Roll forward (shared updater, original @0x6d408): with
  `today=(now-start)/day`, `previous_day=(last-start)/day`, `end_day=(end-start)/day`,
  if `previous_day < today && previous_day <= end_day && g.sol_volumes[previous_day]>0
  && u.current_sol_volume>0` then
  `reward = u.current_sol_volume * g.total_token_supply[previous_day] / g.sol_volumes[previous_day]`
  (u128 mul/div, `u64::try_from` → `Truncation`), `total_unclaimed_tokens += reward`
  (overflow-checked), `current_sol_volume=0`, update `last_update`/`needs_claim`.
  If `now <= g.end_time`, touch today's bucket and refresh `last_update`/`needs_claim`.
- Payout: `amount = u.total_unclaimed_tokens`; if 0 → `msg!("No tokens to claim")`,
  Ok. Else `transfer_checked(amount)` from the incentive vault to `user_ata` signed by
  the gva PDA; then `total_unclaimed_tokens=0; total_claimed_tokens += amount;
  has_total_claimed_tokens=true; needs_claim = current_sol_volume>0; last_update=now`.
- Emits `ClaimTokenIncentivesEvent{user,mint,amount,timestamp,total_claimed_tokens,
  current_sol_volume}` (disc `4facf631cd5bcee8`, helper `0xebd8`, emit! + emit_cpi!).

Conclusion: matches `incentives.rs::claim`; the `has_one=mint`/`InvalidIncentiveMint`
guard, the "No tokens to claim" zero-exit, the PDA-signed `transfer_checked`, and the
event are all confirmed in the binary.

---

## claim_cashback @ 0x25d99 (recovered — GAP check vs cashback.rs)

**1. Purpose.** Native-SOL cashback: skim the lamports held by the user's volume
accumulator above its rent-exemption and move them to the user. `lib.rs:76` →
`cashback::claim`.

**2. Accounts (VERIFIED, try_accounts `0x1f1a0`).** `user` UncheckedAccount mut ·
`user_volume_accumulator` mut, PDA `["user_volume_accumulator", user]` ·
`system_program` · (`event_authority`,`program` from `#[event_cpi]`). Matches
`cashback.rs:6-11`.

**3. Error / order (VERIFIED, body `0xedd3`).** `amount = lamports.saturating_sub(
Rent::minimum_balance(data_len))` (`0xed d9 call 0x34586` lamports, `0x3453e` rent,
`0xeddf sub64`). `amount==0 → return` (`0xee00 jne r1,0,+0x13`). Overflow on the
accumulator uses the `token_incentives/*` source-path panic string @0x1b7064.

**4. CPIs.** None — direct lamport move via `sub_lamports`/`add_lamports`
(`0xee37 call 0x2ae70` and `0xee58 call 0x163f`, offset arg @0x1b5efc = `0x18`).

**5. State writes.** `user_volume_accumulator.total_cashback_claimed` (+0x60) `+= amount`
(`0xee59: stxdw [r8+0x60], r9`); event reads `cashback_earned` (+0x58).
Emits `ClaimCashbackEvent{user,amount,timestamp,total_claimed,total_cashback_earned}`
(disc `e2d6f62107f293e5`, emit helper `0x1f662`).

**GAP vs cashback.rs.** Logic matches `cashback.rs:32-37` (lamport skim, checked add
to `total_cashback_claimed`, sub/add lamports, event). **One divergence:** the deployed
handler logs **`"No cashback to claim"`** (@0x1b7050, referenced at insn **0xe601** —
`xref2`) on the `amount==0` path before returning, whereas the recovered source does a
silent `return Ok(())`. Add the `msg!("No cashback to claim")` to match byte-for-byte
behavior. (Behaviorally benign — a log line only.)

---

## claim_cashback_v2 @ 0x25e2a (recovered — GAP check vs cashback.rs)

**1. Purpose.** Cashback for either native SOL or an SPL/Token-2022 quote mint:
native path mirrors v1 (lamport skim); token path transfers the full balance of the
accumulator's associated quote token account to the user's quote ATA. `lib.rs:77` →
`cashback::claim_v2`.

**2. Accounts (VERIFIED, try_accounts `0x1f375`).** `user` mut · `user_volume_accumulator`
mut, PDA `["user_volume_accumulator", user]` · `quote_mint` Unchecked · `quote_token_program`
Unchecked · `associated_token_program` · `associated_user_volume_accumulator` Unchecked
mut, PDA `[uva, quote_token_program, quote_mint]` `seeds::program=associated_token_program`
· `associated_quote_user` Unchecked mut · `system_program` · (event_authority,program).
Matches `cashback.rs:14-28`.

**3. Error / order (VERIFIED, body `0xf1af`).** `native = quote_mint.key() == WSOL
native mint`. Non-native: `require quote_mint.owner == quote_token_program`
(`AccountTypeNotSupported`). `amount` = native: lamport skim (same as v1,
`0xf1cc call 0x34586` + rent `0x3453e` + `sub64`); token: decoded token-account
`amount` of `associated_user_volume_accumulator` (0 if data empty). `amount==0` →
`msg!("No cashback to claim")` (@0x1b7050, referenced at insn **0xe9b9**) then return.
Token branch also: decode `quote_mint` as `Mint`, require
`associated_quote_user.owner == quote_token_program`, decode it as `TokenAccount`,
require `recipient.owner == user.key()` (`InvalidCashbackRecipient`).

**4. CPIs.** Native: `sub_lamports`/`add_lamports` (`0xf2af call 0x2ae70`, offset @0x1b5f1c).
Token: `token_interface::transfer_checked` (`0xf312 call 0x30c5e`) on `quote_token_program`,
signed by the `user_volume_accumulator` PDA (`seeds=["user_volume_accumulator",user,bump]`),
from `associated_user_volume_accumulator` → `associated_quote_user`, `amount`,
`mint.decimals`.

**5. State writes.** Native: `total_cashback_claimed` (+0x60) `+= amount`. Token:
`total_stable_cashback_claimed += amount`. Emits `ClaimCashbackEvent` twice (emit! +
emit_cpi!, helper `0x1f662` at `0xf215`/`0xf22a`).

**GAP vs cashback.rs.** Logic matches `cashback.rs:38-54` — native/token split, the
WSOL check, the owner/recipient requires, the PDA-signed `transfer_checked`, and the
two accumulator fields. Same `"No cashback to claim"` note as v1: the deployed binary
logs it on the zero-amount return (insn 0xe9b9); the recovered source returns silently.

---

## Verification method notes
- Discriminators/strings read directly from ELF section bytes (strres.py / sbftool disc).
- Account sets proven from the name strings the generated `__global` try_accounts
  functions load (not inferred from source).
- Error/require! sets proven present by xref of each `PumpError` variant string into the
  Display table `0x2bd95`; `msg!` strings proven live by `lddw` xref (xref2.py, lddw=2 slots).
- CPIs/state writes read from the handler bodies (sbftool func/dis), offsets from the
  observed `stxdw`/`ldxdw` instructions.
