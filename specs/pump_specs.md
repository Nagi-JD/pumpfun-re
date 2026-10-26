# pump (`6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P`) - per-instruction specs

Private analysis for the user. Consolidated from the 11 cluster specs in `spec/` plus the
deployed binary. Tags: **[B]** = confirmed in the deployed bytecode; **[R]** = from the
recovered source / cluster spec; **[partial]** = inferred (reason stated). No byte-identity
claim.

Binary: `evidence/original/pump/deployed.so` (`.text` 215,873 insns). Handler addresses are
`sbftool` pc units (instruction indices), matching `handlers.json` and the cluster specs.
The 53-name IDL map is `handlers.json`; **`add_quote_control_mint` is a further deployed
handler documented in `spec/03` (~0x265d5) but absent from that 53-name IDL** - listed as #17
(so the deployed set is 54). #23 is a cross-reference to #12 (`set_mayhem_virtual_params`),
not a second instruction.

Cluster spec sources: `01-admin-config.md`, `02-config.md`, `03-quote-control.md`,
`04-creation.md`, `05-buy.md`, `06-sell.md`, `07-route-migrate.md`, `08-creator.md`,
`09-fees-sweep.md`, `10-incentives.md`, `11-volacc-idl.md`.

Pump error codes: the cluster specs are the reliable source. Only a few codes are
binary-verified there (e.g. 6000 NotAuthorized, 6003 TooLittleSolReceived, 6005
MintDoesNotMatchBondingCurve, 6022 AccountTypeNotSupported); the reconstructed `PumpError`
enum is a different revision, so numeric codes below are omitted unless the cluster spec
gives one. Use the error **name** as the handle.

---

# Cluster 01 - admin / config

## 1. `initialize` @ 0x2421b
1. **Purpose**: one-time creation of the `Global` PDA; `initialized=true`, `authority=user`.
2. **Accounts [R]**: `global` (`init`, payer=user, space 1088, `["global"]`), `user` (mut
   signer), `system_program`.
3. **Args**: none. **Errors**: `init` blocks re-creation; Anchor seed/signer/PDA checks.
4. **CPIs**: System `create_account` via `init`.
5. **State writes [B]**: `initialized=1` (`0x24248`), `authority=user` (in-memory `+0x1a0`);
   all other fields zero.
6. **GAP**: none (spec 01).

## 2. `update_global_authority` @ 0x24261
1. **Purpose**: transfer `Global.authority` and emit an event.
2. **Accounts [R]**: `global` (mut, `["global"]`, `has_one=authority`), `authority` signer,
   `new_authority` unchecked, + event pair.
3. **Args**: `new_authority: Pubkey` (zero/self accepted).
4. **Errors**: `has_one` -> NotAuthorized (6000); Anchor checks.
5. **CPIs**: event self-CPI only.
6. **State writes [B]**: `global.authority` (`+0x1a0`, `0x26920-0x26923`);
   `UpdateGlobalAuthorityEvent`.
7. **GAP**: none (spec 01).

## 3. `toggle_create_v2` @ 0x2430e
1. **Purpose**: flip `create_v2_enabled`; must differ from current.
2. **Accounts [R]**: `AdminGlobal` (`global` mut PDA `has_one=authority`; `authority` mut
   signer; event pair).
3. **Args**: `enabled: bool` (borsh 0/1, checked `<2`).
4. **Errors**: `has_one` -> 6000; `require_neq!` on equal value -> 6000 (same code as auth
   failure - caller-visible ambiguity).
5. **CPIs**: none. **State writes [B]**: `create_v2_enabled` (`+0x4a3`, `0x26aba`).
6. **GAP**: none (spec 01).

## 4. `toggle_cashback_enabled` @ 0x243d8
Same as #3 for `is_cashback_enabled` (`+0x4a5`, `0x26b0e`); bool ABI check `0x243e6`;
`require_neq` -> 6000. [B]/[R] (spec 01).

## 5. `update_holder_reward_config` @ 0x244a2
1. **Purpose**: set `is_holder_reward_enabled` and `holder_reward_claim_authority`.
2. **Accounts [R]**: `AdminGlobal` + event pair.
3. **Args**: `bool` (checked `<2`) then `Pubkey` (order confirmed by `0x244af-0x244b1`).
4. **Errors**: `has_one`/PDA; no value bounds. **CPIs**: none. **No event**.
5. **State writes**: `is_holder_reward_enabled` and `holder_reward_claim_authority`
   (in-memory offsets not isolated; spec 02).
6. **GAP**: no behavioral gap; per-field store offsets not pinned (spec 02).

## 6. `set_max_curve_depth` @ 0x24566
`AdminGlobal`; arg `max_curve_depth: u8` (raw 0..255, no bounds); no event; writes the
u8. No value guard (spec 01).

## 7. `toggle_mayhem_mode` @ 0x245dc
`AdminGlobal`; arg `enabled: bool` (`jlt <2`); `require_neq` -> 6000; writes
`mayhem_mode_enabled` (`+0x4a4`, `0x26b62`); no event (spec 01).

## 8. `update_creator_fee_config` @ 0x246a6
`AdminGlobal`; args `creator_fee_configurable: bool`, `max_configurable_creator_fee_bps:
u64`; no bps bound; writes the two fields; `UpdateCreatorFeeConfigEvent` (log + CPI)
(spec 02).

## 9. `set_params` @ 0x2494e (execute 0x26cf8)
1. **Purpose**: admin reconfiguration of launch/migration/creator-fee parameters and the 8
   protocol fee recipients.
2. **Accounts [R]**: `SetParams` (`global` mut `["global"]` `has_one=authority`,
   `authority` mut signer, event pair) + **8 remaining recipient accounts**.
3. **Args [B]**: `initial_virtual_token_reserves`, `initial_virtual_sol_reserves`,
   `initial_real_token_reserves`, `token_total_supply`, `fee_basis_points`,
   `withdraw_authority`, `enable_migrate`, `pool_migration_fee`,
   `creator_fee_basis_points`, `set_creator_authority`, `admin_set_creator_authority`.
4. **Errors/order [B]**: remaining>=8 (NotEnoughRemainingAccounts), non-zero recipients,
   rent-exempt, strictly sorted/unique recipients, initial_real<total,
   initial_virtual>initial_real, fee_bps<=1000, withdraw_authority!=default, u128
   final_real_sol_reserves (Truncation), pool_migration_fee<final, creator_fee_bps<=1000.
   Recipient subroutine `0x7caa`.
5. **CPIs**: event self-CPI only.
6. **State writes [B]**: `initial_virtual_token_reserves +0x450`, `initial_virtual_sol +0x460`,
   `initial_real_token +0x458`, `token_total_supply +0x468`, `fee_basis_points +0x470`,
   `withdraw_authority +0x1b0..`, `enable_migrate +0x4a2`, `pool_migration_fee +0x478`,
   `creator_fee_basis_points +0x480`, `set_creator_authority +0x2b0`, 
   `admin_set_creator_authority +0x2d0`, plus the fee recipient copies (not isolated).
7. **GAP**: matches source; recipient-copy offsets not isolated (spec 02).

## 10. `set_reserved_fee_recipients` @ 0x24b5d
`AdminReadonly` (`global` mut `has_one=authority`, `authority` non-mut signer, event pair) +
8 remaining recipients. Arg `whitelist_pda: Pubkey`. Checks remaining>=8, non-zero,
**`!executable`**, rent-exempt, **no sort/unique** (asymmetry vs set_params). Writes
`whitelist_pda`, `reserved_fee_recipient=rem[0]`, `reserved_fee_recipients=rem[1..8]`
(offsets not isolated); `ReservedFeeRecipientsEvent`. [B]/[R] (spec 02).

## 11. `set_virtual_quote_reserves` @ 0x248d8
`AdminGlobal`; arg `u64`; no require beyond `has_one`; no event; writes
`initial_virtual_quote_reserves` (offset not isolated; spec 02).

## 12. `set_mayhem_virtual_params` @ 0x24ab5 (execute 0x26ff8)
1. **Purpose**: write the Mayhem virtual-param block to the Mayhem program (unrecovered
   source).
2. **Accounts [R/partial]**: the wrapper `0x24ab5` calls a compact account/arg decoder
   (`0x19a7b`) and `0x26ff8`; the accounts-context offsets `[r8+0x58]`, `[r8+0xe8]`,
   `[r8+0x1f0]`, `[r8+0x210..0x248]`, `[r8+0x688]` give the layout but not the seed/signer
   assertions (spec 04).
3. **Args [B/partial]**: a u32 optional/sentinel (`-1` default), two u64s, and a 0x6c0-byte
   account blob; the arg record exposes `accounts_ptr +0x8` and a bool at `+0x23`.
4. **Errors [R]**: lamport/reserve bounds `1e6/1e7/1e12`; the event disc is `757be4b6a1a8dcd6`.
5. **CPIs [R]**: a Mayhem CPI/write-back; persistence not fully traced.
6. **State writes**: Mayhem virtual-param block (8 u64 values read at `0x26ffb..0x27049`).
7. **GAP**: **unrecovered**; do not implement from this alone (spec 04 Sec.3).

---

# Cluster 02/03 - quote control (two whitelists)

## 13. `add_quote_mint` @ 0x24774 (legacy)
`AdminGlobal`; migrates a mint into the **single-slot** `Global.whitelisted_quote_mints[1]`.
Checks default, SPL native mint only, duplicate, and a free slot; writes the first default
slot (array at `global+0x3a0` in-memory); no CPIs. [B]/[R] (spec 03).

## 14. `remove_quote_mint` @ 0x24826 (legacy)
`AdminGlobal`; checks default then locates/zeroes the matching slot; no other validation.
[B]/[R] (spec 03).

## 15. `initialize_quote_control` @ 0x264a2
`quote_control` (`init`, payer=user, `8+INIT_SPACE`, `["quote-control"]`), `user` signer,
`system_program`. Permissionless; zeroes admin/reserves_admin/_reserved, empty Vec; System
`create_account`; no event (spec 03).

## 16. `set_quote_control_admin` @ 0x264e3
`global` `has_one=authority` only, `authority` signer, `quote_control` mut; arg `new_admin`
(unvalidated). Writes `quote_control.admin` (`+0x18`); event (spec 03).

## 17. `add_quote_control_mint` @ ~0x265d5 (not in the 53-name IDL map)
`UpdateQuoteControlMints` (shared `try_accounts` `0x1c9db` with remove): authority signer
(`global.authority || quote_control.admin`), global, quote_control mut, system_program,
event pair. Adds a mint with default/native/duplicate/len<256 validation (spec 03).

## 18. `remove_quote_control_mint` @ 0x26667
Same shared context; arg = mint; checks default + presence; removes the Vec entry (no shrink);
event (spec 03).

## 19. `set_quote_control_reserves_admin` @ 0x26728
Authority = `global.authority || admin`; writes `reserves_admin` (`+0x38`); arg unvalidated;
event (spec 03).

## 20. `set_quote_control_mint_reserves` @ 0x267e9
Authority = `global.authority || admin || reserves_admin`; arg `quote_mint + u64` (data len
checked); updates the matched `QuoteControlMint.initial_virtual_quote_reserves`; old value in
event (spec 03).

---

# Cluster 04 - creation

## 21. `create` @ 0x24c1b
Creates a classic SOL-quoted pump coin: init mint (6 decimals), mint total supply to the
bonding-curve ATA, revoke mint authority, write the initial `BondingCurve`, create the
Metaplex metadata; SOL-only (no quote/mayhem/holder branch). `CreateEvent`. [R] (spec 04).

## 22. `create_v2` @ 0x24d15
Token-2022 creation with optional alternate quote, configurable creator fee, holder-reward
routing, and the Mayhem branch. Mint uses Token-2022 with `metadata_pointer`; metadata via
`token_metadata_initialize`/`update_authority` CPIs (not Metaplex). `CreateV2` hard-wires
`mayhem_program_id`, Mayhem `global_params`, `sol_vault`, `mayhem_state`
(`["mayhem-state", mint]`), `mayhem_token_vault`; the Mayhem branch gates
`global.mayhem_mode_enabled` and CPIs into Mayhem (`initialize_mayhem_state`). The wrapper is
vtable-dispatched; the Mayhem CPI data builder is at `0x2316a` (disc-only payload, called
from `0x116fc` inside `0x114b1`), but the full body/order is not fully labelled. The Mayhem
flow is detailed in `create_v2_mayhem.md`. [R]/[partial] (spec 04 + binary CPI builder).

## 23. `set_mayhem_virtual_params` @ 0x24ab5
See #12 (unrecovered).

---

# Cluster 05 - buys

## 24. `buy` (legacy) @ 0x2549c (core 0x2dcfe)
SOL-only fixed-token buy; 23 accounts, 18-account Pump CPI; 2 remaining accounts
(`[0]`=bonding-curve-v2 PDA, `[1]`=buyback recipient in Global 741..997). Ordered gates:
rent/realloc 166 -> fee-recipient membership (NotAuthorized) -> remaining>=2
(BuybackFeeRecipientMissing) -> !complete -> amount>0 (BuyZeroAmount) -> amount<=real
(NotEnoughTokensToBuy) -> fee CPI -> rem[0]/rem[1] checks -> slippage TooMuchSolRequired.
Emit `BuyEvent` (TradeEvent, `[+0x198]=0`). [B]/[R] (spec 05).

## 25. `buy_exact_sol_in` @ 0x25579 (core 0x2dcfe)
Same accounts; exact branch: limit>0 -> input>0 (BuyNotEnoughSolToCoverFees) -> !complete ->
raw_quote>0 -> computed<=real||partial -> rem checks -> slippage
(BuySlippageBelowMinTokensOut). `ix_name="buy_exact_sol_in"`. [B]/[R] (spec 05).

## 26. `buy_v2` @ 0x24ea2
SOL native or arbitrary quote; 32-account context; non-native ATA checks/creation, fee
recipient, !complete, amount>0/<=real, fee CPI, buyback membership, slippage. GAP:
transfer-fee gross-up missing in the reconstruction for fee-bearing Token-2022 quotes.
[B]/[R] (spec 05).

## 27. `buy_exact_quote_in_v2` @ 0x24f6b
Same BuyV2 accounts; exact branch (raw_quote/estimate, computed<=real||partial, slippage);
same transfer-fee gap. [B]/[R] (spec 05).

## 28. `buy_v3` @ 0x250d9 (logic 0x28f74)
SellV3 event_cpi layout; `prepare` -> `check_quote` (binary general, not USDC-only) ->
!complete -> !cashback -> amount>0 -> native buyback membership -> local fee_config read
(len>=2512, tiers) -> slippage. `partial_fill` is parsed then discarded. Self event CPI;
no fee-program CPI. Transfer-fee gross-up unmodelled. [B]/[R] (spec 05).

## 29. `buy_exact_quote_in_v3` @ 0x25185 (logic 0x2913f)
SellV3 accounts; order: prepare -> check_quote -> !cashback -> !complete -> min_tokens_out>0
-> spendable>0 -> native buyback -> fee_config -> affordability -> NotEnoughTokensToBuy
unless partial/mayhem -> slippage. `partial_fill` is load-bearing; crossing emits
`PostCompleteBuyEvent`. Transfer-fee/nested-route gaps. [B]/[R] (spec 05).

---

# Cluster 06 - sells

## 30. `sell` (legacy) @ 0x25656 (worker 0x2a511)
SOL-only; rent -> fee recipient (NotAuthorized) -> complete -> amount>0 (SellZeroAmount) ->
NotEnoughTokensToSell -> fee CPI -> gross min `TooLittleSolReceived` (6003, `0x2a682`) ->
base transfer -> remaining checks. Lamport payout; no Token-2022 fee. [B]/[R] (spec 06).

## 31. `sell_v2` @ 0x25034 (worker 0x288a1)
Native + arbitrary quote; non-native quote ATA checks/creation; same gate chain; gross min
`TooLittleSolReceived` (`0x28bd7`). **No** Token-2022 fee netting/harvest; the user can
receive less than the minimum while the tx succeeds (present in binary and source). [B]/[R]
(spec 06).

## 32. `sell_v3` @ 0x25231 (worker 0x29515)
WSOL/USDC-only per source `check_quote`; prepare -> check_quote -> !cashback -> complete ->
amount>0 -> NotEnoughTokensToSell -> native buyback -> local fee_config/tiers -> gross min
(`0x29622`) -> base transfer -> payout. No fee-program CPI. [B]/[R] (spec 06).

---

# Cluster 07 - route / migration

## 33. `multi_hop_curve_swap` @ 0x252b8 (execute 0xacfb)
Curve-hop router. Args `amount_in: u64`, `hop_fees: Vec<u8>`; remaining_accounts 5 per hop
(base_mint, quote_mint, bonding_curve PDA, base ATA, quote ATA); `amount_in!=0`,
`len>=5`, `len%5==0`, `hop_fees.len==count`, flags<4; per-hop body `0xb70e` does
prepare/fee/reserve/transfer/event; terminal `current_mint == destination.mint`. `hop_fees`
bit0 = protocol leg, bit1 = creator leg; buyback = pf*buyback_bps/10000. **No depth cap in
this function** (the cap lives in the outer router). `TradeEvent +0x198` =
`quote_before_adapter - quote_after_adapter` (non-zero for lossy quotes; reconstruction
hardcodes 0). Detailed in `multihop_specs.md`. [B]/[R] (spec 07).

## 34. `migrate` @ 0x256fb (execute 0x7f6e)
Native-SOL completed curve -> pump-AMM pool: create pool/ATAs, seed liquidity, AMM create
(disc `233,146,209,142,207,104,64,188`), non-mayhem AMM buyback/boost
(`140,233,33,94,132,90,194,143`), close temp accounts, burn/close LP, sweep residue, zero
curve reserves, `CompletePumpAmmMigrationEvent`. Gates: complete (`d[48]`), idempotent
already-migrated early Ok, overflow guards, non-mayhem remaining>=2. [B]/[R] (spec 07).

## 35. `migrate_v2` @ 0x25749 (execute 0x9311)
Generalized (native + SPL/Token-2022 quote) migration; per-side token programs, Token-2022
fee harvest (`26,4`) and `QuoteMintNotWritable` (110), `quote_account_size` sizing. Same
complete/idempotent/overflow/non-mayhem gates. [B]/[R] (spec 07).

## 36. `extend_account` @ 0x257cf (execute 0x771b)
Grows an owned account to the type's size: discriminators -> 166 (BondingCurve), 1088
(Global/DistributionCurve), 137 (UserVolumeAccumulator), 600 (202,42,246,43,142,190,30,255),
else AccountTypeNotSupported; current>=size early Ok; rent delta from user; realloc;
`ExtendAccountEvent`. [B]/[R] (spec 07).

---

# Cluster 08 - creator

## 37. `collect_creator_fee` @ 0x2586e (execute 0x5316)
Native-SOL creator vault -> creator wallet. Accounts creator (mut unchecked), creator_vault
(`["creator-vault", creator]`), system_program. No require; executable creator -> early Ok,
amount = vault lamports - rent; zero -> early Ok. One system transfer signed by the vault
PDA; `CollectCreatorFeeEvent`; no state writes. [B]/[R] (spec 08).

## 38. `distribute_fee_to_holders` @ 0x258fa (execute 0x68ab)
Holder-reward payout from `["holder-rewards", mint]` to recipient/ATA pairs; authority
`global.holder_reward_claim_authority`. First guard: remaining == amounts.len()*2
(`HolderRewardRecipientsMismatch`, 6085, `0x68e6`). Native: close wSOL source then
PDA-signed system transfers; token: idempotent ATA create + transfer_checked. Secondary
constraint/rent codes not located as immediates (flagged, not a divergence).
`DistributeFeeToHoldersEvent`. [B/R] (spec 08).

## 39. `set_metaplex_creator` @ 0x259f2 (execute 0x74f7)
Permissionless one-shot sync: if curve creator is default, set it from Metaplex
`creators[0]`; no errors, early Ok. Writes curve creator (49..81); `SetMetaplexCreatorEvent`.
[B]/[R] (spec 08).

## 40. `set_creator` @ 0x25a82 (execute 0x71f8)
`global.set_creator_authority` signer + `has_one`; same default-creator gate; metadata
creators[0] else the argument creator; two event shapes. Writes curve creator (49..81).
[B]/[R] (spec 08).

## 41. `admin_cto` @ 0x25b40 (execute 0x4542) - **DIVERGENCE**
Admin takeover: reassign creator, optional fee, sweep old vault, reset sharing config,
update AMM pool coin-creator. ~30 accounts. **Binary guard set/order differs from the
reconstruction**: 6088 (mayhem) and 6092 (not-writable) are absent from the deployed
handler; 6080 (cashback fee) and 6095 (fees-not-swept) are present but absent in source;
several shared guards reordered. CPIs (per source): AMM collect coin-creator fee
(`1,33,78,185,33,67,44,92`), AMM set coin-creator (`160,57,89,42,181,139,43,66`), fees reset
sharing config (`60,100,144,156,64,138,182,37`), AMM update pool coin-creator
(`45,61,165,151,104,0,49,189`), plus system/ATA. State: curve creator (49..81), d[123]=0,
d[124]=holder, fee (115..123) when supplied. Binary is authoritative; see spec 08 Sec.5.
[B]/[R] (spec 08).

## 42. `migrate_bonding_curve_creator` @ 0x26118 (execute 0x6fc1)
Migrates a non-holder-reward creator to the fees sharing-config PDA. Guards: !holder ->
6083; creator_fee==0 -> 6095 (both in correct order); writes creator = sharing_config
(49..81); event. Permissionless; sharing config constrained to the curve creator. [B]/[R]
(spec 08).

---

# Cluster 09 - fees / sweep

## 43. `sweep_protocol_fee` @ 0x25376 (execute 0xe502, creator=false)
Sweep accrued protocol fees (`data[133]`) from a curve to a recipient. Accounts: payer
signer, global `["global"]`, base/quote mints, token/ATA/system programs, bonding_curve
mut (`["bonding-curve", base_mint]`; `data[83]` quote/default -> native), associated quote
curve ATA, recipient mut unchecked, associated recipient ATA. Rent top-up/realloc 166;
recipient must be in the global fee-recipient set (reserved set if `data[81]!=0`, else
`fee_recipient`/classic search) -> NotAuthorized; amount = `pf`; zero -> early Ok; native
lamport move or token `transfer_checked` (PDA signed); zero `data[133..141]`;
`SweepBondingCurveFeeEvent{bucket=0}`. [B]/[R] (spec 09).

## 44. `sweep_creator_fee` @ 0x25409 (execute 0xe502, creator=true)
Same body; amount = `data[125]`; recipient must be the `["creator-vault", curve.creator]`
PDA (ConstraintSeeds); zero `data[125..133]`; event bucket=1. [B]/[R] (spec 09).

## 45. `get_minimum_distributable_fee` @ 0x261a8 (execute 0x64a6)
Read-only query. Accounts mint, bonding_curve (`["bonding-curve", mint]`), sharing_config
(`["sharing-config", mint]` under fees, has_one mint), creator_vault
(`["creator-vault", sharing_config]`). Shareholders' required minimum computed locally
(no fee-program CPI - the `get_return_data` hypothesis is refuted); `MinimumDistributableFeeEvent`.
[B]/[R] (spec 09).

## 46. `distribute_creator_fees` @ 0x26225 (execute 0x6508)
Native distribution of creator-vault lamports to sharing-config shareholders.
`bonding_curve.creator == sharing_config` (BondingCurveAndSharingConfigCreatorMismatch),
status Active (SharingConfigNotActive), remaining>=shareholders
(NotEnoughRemainingAccounts), `native_eligible` (address/non-executable/share_bps>0/
rent-floor), per-share `available*share_bps/10000` (div-by-10000 confirmed), PDA-signed system
transfer; event. [B]/[R] (spec 09).

## 47. `distribute_creator_fees_v2` @ 0x262dd (execute 0x17f00)
Generalized native/token distribution; extra arg `initialize_ata: bool` (r6);
quote_mint/native check (MintDoesNotMatchBondingCurve); native lamports or token ATA
balance; token mode needs a second remaining-account array of recipient ATAs;
`ShareholdersAndRemainingAccountsMismatch`, `UnableToDistributeCreatorFeesToUninitializedAccount`;
optional ATA create + transfer_checked; event. [B]/[R] (spec 09).

---

# Cluster 10 - incentives / cashback

## 48. `admin_update_token_incentives` @ 0x25c54
Authority-gated volume-reward schedule. Accounts authority signer, global `["global"]`
`has_one`, global_volume_accumulator `["global_volume_accumulator"]` mut, mint,
global_incentive_token_account init_if_needed ATA, ATA/system/token programs, event pair.
Args start_time/end_time/seconds_in_a_day (i64), day_number (u64), supply/day (u64). Writes
gva mint/seconds/start/end and the two [u64;30] arrays; eight schedule guards
(StartTimeInThePast, EndTimeInThePast, EndTimeBeforeStartTime, TimeRangeTooLarge,
EndTimeBeforeCurrentDay, SupplyUpdateForFinishedRange, DayIndexAfterEndIndex,
DayInActiveRange); `AdminUpdateTokenIncentivesEvent`. [B]/[R] (spec 10).

## 49. `claim_token_incentives` @ 0x25d0e
Accounts user (unchecked), user_ata init_if_needed, gva `has_one=mint`
(InvalidIncentiveMint), global incentive ATA, user_volume_accumulator, mint, token/system/
ATA programs, event pair, payer signer. Rolls the accumulator forward, pays
`total_unclaimed_tokens` from the incentive vault via a gva-PDA-signed transfer_checked;
zero -> `msg!("No tokens to claim")`; updates claimed/unclaimed/needs_claim/timestamp;
event. [B]/[R] (spec 10).

## 50. `claim_cashback` @ 0x25d99
Native cashback: user unchecked, user_volume_accumulator PDA, system, event pair. Skims
lamports above rent to the user; amount==0 logs `"No cashback to claim"` (divergence from
the silent source return); `total_cashback_claimed += amount`; `ClaimCashbackEvent`.
[B]/[R] (spec 10).

## 51. `claim_cashback_v2` @ 0x25e2a
Native or token cashback; adds quote_mint/quote program/ATA program/accumulator ATA/user
ATA. Native lamport skim; token transfer_checked from the accumulator ATA (PDA signed);
zero logs `"No cashback to claim"`; updates total_cashback_claimed or
total_stable_cashback_claimed; event. [B]/[R] (spec 10).

---

# Cluster 11 - volume accumulator / IDL

## 52. `init_user_volume_accumulator` @ 0x25ebc
Accounts payer signer, user unchecked, user_volume_accumulator init_if_needed 137
(`["user_volume_accumulator", user]`), system, event pair. No args; sets user (account
+8..40) from the user key; `InitUserVolumeAccumulatorEvent`. [B]/[R] (spec 11).

## 53. `close_user_volume_accumulator` @ 0x25f6d
Accounts user signer mut, user_volume_accumulator PDA close=user, event pair. Read-only body
(event fields); Anchor close refunds lamports; `CloseUserVolumeAccumulatorEvent`. [B]/[R]
(spec 11).

## 54. `sync_user_volume_accumulator` @ 0x25ff1
Accounts user unchecked, global_volume_accumulator PDA, user_volume_accumulator PDA mut,
event pair. If `last_update < start && now < start`: `total_claimed_tokens=0`,
`has_total_claimed_tokens=false`; event only if the prior value was >0. No timestamp
write. [B]/[R] (spec 11).

## 55. `admin_set_idl_authority` @ 0x260a3
Accounts authority signer, global `["global"]` `has_one`, idl_account mut
(`address=IdlAccount::address`), system_program, program_signer (empty-seed PDA), event
pair. Arg `idl_authority: Pubkey`. System-owned IDL -> seeded system transfer and return
(no event); program-owned -> realloc 10240, disc check `[24,70,98,191,58,144,123,158]`,
rewrite header authority, `AdminSetIdlAuthorityEvent`; else AccountTypeNotSupported.
[B]/[R] (spec 11).

---

## Notes

- The 53-name `handlers.json` map plus the deployed `add_quote_control_mint` (#17) are the
  complete pump set covered here. The 11 cluster specs are the authoritative binary-verified
  sources; this file consolidates them and flags the known divergences (`admin_cto`,
  `claim_cashback*` log line, `create_v2` Mayhem stub, `sell_v2` gross-min, v3 quote/
  transfer-fee gaps, `multi_hop` adapter delta).
- `create_v2_mayhem.md` and `multihop_specs.md` carry the deep dives for #22 and #33.
- No whole-byte identity is claimed. `admin_cto` is a different revision from the recovered
  source (spec 08 Sec.5); `set_mayhem_virtual_params` stays unrecovered.
