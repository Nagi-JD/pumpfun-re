# Mayhem (`MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e`) - handler specs (batch 2)

Private analysis for the user. Format matches `specs/01-admin-config.md` (Purpose / Accounts /
Args / Errors / CPIs / State writes / GAP). Tags: **[B]** = confirmed directly in the deployed
bytecode or `.rodata`; **[R]** = taken from the read-only reconstruction in
`programs/mayhem/src/` + `repro/mayhem/twentyfour/` receipts (9,595 comparisons against this
capture); **[partial]** = inferred, reason stated. No byte-identity is claimed.

Binary: `evidence/original/mayhem/deployed.so` (SHA-256
`a87fa9f866272514e6acb852b668c4a08aeb173d56c883039991d114d1199bdb`; `.text` `0x120`,
`0xac8b8` bytes). Decoder: `sbftool.py` (`pc` = vaddr/8; addresses are vaddr).
The full 25/25 map, dispatcher method and the `Instruction: X` identification are in
`mayhem_map.md`; this file focuses on the specs and closes the `initialize_mayhem_state` gap.

Program-id constants verified in `.rodata` **[B]**: Pump `0xae2ac`, PumpSwap `0xae2e2`,
Tokenkeg `0xad168`/`0xae302`, Token2022 `0xae322`.
Event discriminators verified as `lddw` immediates **[B]**: SellEvent `31487b2d6e40b085`
@`0xb6f7`; BurnEvent `sha256("event:BurnEvent")[:8]` = `21592f75527ceefa` @`0x1c73/0x1ceb`;
GlobalParamsUpdateEvent `63a75c9898e32629` @`0x1a02/0x1a5f`; ExtendAccountEvent
`6161d7905d92167c` @`0x793f`; SweepEvent `da8286fd656d9598` @`0x247d/0x24cc/0x2867/0x28b6`.

---

## 25. `initialize_mayhem_state` - wrapper `0x101de`, parser `0xd25f`, handler `0x10527`
**(the previously unresolved handler)**

- **Identity [B]**: disc `9dbd5e485545cc2d`; `lddw@0xfb59`; `jeq@0xfb5b`; stub `0xfbf0`;
  wrapper byte `0x80ef0`. Wrapper logs `Instruction: InitializeMayhemState` (string
  `0xae10b`, len `0x22`).
- **Call graph [B]**: `0x101de` -> accounts parser **`0xd25f`** (byte `0x693b8`) -> business
  handler **`0x10527`** (byte `0x82938`) -> account-exit/serializer **`0xdabe`**
  (byte `0x6d5f0`).
- **Args [B]**: **none**. The wrapper `0x101de..0x10216` never touches `r4/r5` (the
  instruction-data pointer/length); it only stores `r2/r3` (accounts), builds
  `Context { program_id, &accounts }` at `r10-0x2f8`, then calls parser -> handler -> exit.
- **Accounts [partial]**. The parser references the account-name/seed strings
  `system_program`, `global_params`/`global-params`, `program`, `token_program`,
  `associated_token_program`, `mayhem_state`/`mayhem-state`, `mayhem_token_vault`,
  `bonding_curve`/`bonding-curve`, `global`, `pump_program`, `pump_event_authority`
  (`.rodata` pointers `0xadaf4`, `0xadb89`, `0xadb96`, `0xadbc9`, `0xadc0e` and the merged
  string pool they point into) and builds a `payer` string for a create-account path
  (`0xd2b6`). The Pump `create_v2` Mayhem branch hard-wires and passes the Mayhem accounts
  `global_params` (`["global-params"]`), `sol_vault` (`["sol-vault"]`),
  `mayhem_state` (`["mayhem-state", mint]`), `mayhem_token_vault` (unchecked) and
  `mayhem_program_id` (`MAyh...`) (`specs/04-creation.md` Sec.2.6). Combining these, the
  **most likely** account list (order not statically pinned) is:
  1. `payer` / initializing signer (create-account payer)
  2. `global_params` (`["global-params"]`, Mayhem PDA)
  3. `mayhem_state` (`init`, `["mayhem-state", mint]`, space 170 - the `ExtendAccount`
     target for the MayhemState discriminator)
  4. `mint`
  5. `mayhem_token_vault` (ATA of `sol_vault`)
  6. `sol_vault` (`["sol-vault"]`)
  7. `bonding_curve` (`["bonding-curve", mint]`, `seeds::program = PUMP`)
  8. pump `global` (read-only config; the source of the duration byte, see below)
  9. `pump_program` (`address = PUMP_ID`)
  10. `pump_event_authority`
  11. `system_program`
  12. `token_program`
  13. `associated_token_program`
  14. `event_authority` (`["__event_authority"]`)
  15. `program`
  **Why [partial]:** Anchor's generated `try_accounts` attaches account-name strings only on
  error/constraint paths, and the parser 0xd25f's name references are all near its tail
  (`0xd3ed..0xd4bd`), so the consumption order cannot be recovered from the strings alone; the
  hand-written source for this handler does not exist. The *set* is corroborated by the Pump
  CPI oracle, not the order/count. Treat 15 as an upper bound and verify with a successful
  original invocation before implementing.
- **Handler body [B]**, memory offsets in the in-memory accounts struct (not Borsh offsets;
  `r7 = [Context+8]` = `&accounts`):
  1. `r9 = byte [T+0x2c4]` (`0x1054f`) - a duration/limit byte (most likely read from the pump
     `global` config inlined in the context; semantics not proven).
  2. `r9 *= 3600` (`0x10557`) with a checked signed-overflow branch; overflow path `0x10583`.
  3. `Clock::get` via `0x13dfa` (`0x10552`); the timestamp is at `[r10-0x10]` (`0x10555`).
  4. `[T+0x1a0] = now` (`0x10556`).
  5. `[T+0x1a8] = now + r9*3600` (`0x10562`) - the state `end_timestamp` memory slot; burn
     reads `[ctx+0x1a8]` and requires `<= now`.
  6. `[T+0x160..0x180] = 32-byte key` copied from an `AccountInfo.key` at `[T+0x58]`
     (`0x10547..0x1056a`); this is the `MayhemState.mint` memory slot.
  7. zeroes `[T+0x180]`, `[T+0x188]`, `[T+0x190]`, `[T+0x198]`, `[T+0x1b8]` (u64 each),
     u16 at `[T+0x1c0]`; sets `[T+0x1b0] = now` (`0x1056c..0x10571`).
  8. releases two RefCell borrow counters (`0x10572..0x10579`) and returns (success `r0=2`).
  Interpretation (medium confidence): sets `mint`, a start/end timestamp pair
  (`0x1a0`/`0x1a8`, end = now + hours*3600), zeroes the signed net counters
  (`field_56`/`field_72` memory slots), `burned_amount` (`0x1b8`) and status (`0x1c0`).
  Burn's independently recovered reads of `end_timestamp` at memory `0x1a8` and
  `burned_amount` at `0x1b8` corroborate the mapping.
- **Persistence [B]**: the wrapper calls the Anchor accounts-exit routine `0xdabe` after the
  handler. `0xdabe` performs the program-id/borrow checks and serializes the mutated
  `MayhemState` back to the **`mayhem_state`** PDA (`["mayhem-state", mint]`). The handler
  itself performs no `sol_invoke_signed_rust`; the only CPI in this instruction is the
  parser-side System `create_account` for the state PDA (the `payer` string at `0xd2b6`);
  whether the token vault is `init_if_needed` (ATA CPI) is not confirmed. The repo's
  `ExtendAccount` target 170 bytes and the 106-byte serializer are consistent with the
  `mayhem_state` write-back.
- **Errors [partial]**: the overflow branch at `0x10583` (likely `MathOverflow`, 6002) plus
  Anchor parser errors (seeds/owner/`AccountNotEnoughKeys`). Not independently enumerated.
- **CPI**: System `create_account` (state PDA). No token/Pump CPI in `0x10527`.
- **GAP**: account order/count and the duration source are **[partial]**; the handler effects
  and the write-back account are **[B]** at the instruction level, but there is **no accepted
  differential replay** (the repo marks this lane stopped/unrecovered). Do not implement from
  this spec without a successful original invocation.

---

## Specs for the other 24 handlers

These are unchanged from the merged map (re-verified here) and are retained in the same
order. Each item names the evidence class.

### 1. `buy` (legacy) @ 0x1027f (byte 0x813f8)
1. **Purpose**: trader-signed buy through the Pump bonding curve with Mayhem risk limits and
   a signed-i128 accounting update.
2. **Accounts [R]**: 23 outer; 18-account Pump CPI. trader (signer, `has_one` GlobalParams
   trader), global_params, mayhem_state (`["mayhem-state", mint]`), mint,
   mayhem_token_vault (ATA of sol_vault), sol_vault (`["sol-vault"]`), system/token programs,
   pump global, bonding_curve (`["bonding-curve", mint]` under Pump), Pump fee recipient /
   creator vault / event authority / program, global/user volume accumulators, fee config /
   program, bonding_curve_v2 (`["bonding-curve-v2", mint]` under Mayhem), buyback recipient.
3. **Args [B]**: `reference: u128`, `tolerance_bps: u16`, `retained_reserve_bps: u16`
   (wrapper `0x10288..0x102a6` requires len >= 16 and unpacks +0/+0x10/+0x12).
4. **Errors [R]**: 6000 TradingPaused, 6002 MathOverflow, 6004 MayhemModeEnded,
   6006 OverallRiskExceeded, 6007 CoinRiskExceeded, 6008 PumpCpiFailed, 6012 PumpCpiSlippage,
   6015 TradeRateLimit.
5. **CPIs [R]**: Pump `6EF8...` buy disc `66063d1201daebea`, 18 accounts, signer
   `["sol-vault", bump]`.
6. **State writes [R]**: GlobalParams.sol_deployed += spent; MayhemState.field_56 += spent;
   field_72 -= tokens; strict low-u64 risk checks; `SellEvent{side=0}` log + `emit_cpi!`
   (303 bytes).
7. **GAP**: [R] body; map/args/CPI id [B].

### 2. `sell` (legacy) @ 0x10217 (byte 0x810b8)
Same 20-byte args; 21 outer, 16-account Pump CPI (`33e685a4017f83ad`); output capped by cap +
retained real SOL; sol_deployed -= received, field_56 -=, field_72 +=; side=1 event; errors
6003/6004/6012/6015/6002. [R] body, [B] map/args.

### 3. `buy_v2` @ 0x1034f (byte 0x81a78)
Quote-aware (`WSOL`/default = native vs stable); 32 outer / 27-account Pump CPI
(`66063d1201daebea`); native path funds WSOL + `sync_native`; quote-selected cap/floor/limits
(GlobalParams 16/129/32/40 native vs 182/222/190/198 stable); updates
sol_deployed/stable_deployed, field_56, field_72; strict post-CPI risk checks; 303-byte event
with native-only fields zeroed for token quotes. [R] body, [B] map.

### 4. `sell_v2` @ 0x102e7 (byte 0x81738)
31 outer / 26-account Pump CPI (`33e685a4017f83ad`); native path closes WSOL to the sol vault
(tag 9); same quote-selected caps/limits; sol_deployed/stable_deployed -= received,
field_56 -=, field_72 +=; side=1 event; errors 6003/6004/6008/6012/6015/6002. [R]/[B] map.

### 5. `buy_pump_swap` @ 0x1041f (byte 0x820f8)
31 outer / 25-account PumpSwap CPI; quote token program constrained to Tokenkeg
(`0xad168`); base program Token-2022 (`0xae322`); Pool zero-padded to 287 and GlobalConfig
strict 418-byte prefix; `effective_quote = pool_quote + virtual_quote`; zero divisor -> 6011;
native path funds/syncs/closes WSOL; updates signed-i128 counters; strict post-CPI limits;
event reports actual pool balances. [R] body, [B] map/CPI ids.

### 6. `sell_pump_swap` @ 0x103b7 (byte 0x81db8)
29 outer / 23-account PumpSwap CPI (`33e685a4017f83ad`); same fixed Tokenkeg quote
constraint; `minimum = output-1`; signed-i128 subtract/add; side=1 event. [R]/[B] map.

### 7. `burn_tokens` @ 0xffe1 (byte 0x7ff08)
12 accounts (mayhem_state, mint, vault, sol_vault, bonding_curve, global, pump_program,
pump_event_authority, system/token programs, event_authority, program); no args; requires
`end_timestamp <= now` (6005) then `status != Ended` (6004); SPL Token-2022 Burn (tag 8) of
the whole vault signed by sol_vault; sets burned_amount, emits BurnEvent (disc
`21592f75527ceefa`), sets status=Ended. [B] map/event, [R] body.

### 8. `sweep_fees` @ 0xfc96 (byte 0x7e4b0)
9 outer + exactly 16 remaining (8 FeeRecipient/token-account pairs); trader signer (`has_one`);
per pair token transfer signed by `["fee-recipient", index, bump]`; native WSOL also moves
lamports over rent; capped by max_sol/max_stable_per_sweep; per-recipient cumulative counter +
timestamp; SweepEvent `da8286fd656d9598`. [B] map/event, [R] body.

### 9. `sweep_fees_admin` @ 0xfcd3 (byte 0x7e698)
Same as sweep_fees with admin (`has_one` admin), uncapped, timestamps preserved. [B]/[R].

### 10. `withdraw_quote_admin` @ 0xfde2 (byte 0x7ef10)
admin/global_params/sol_vault/quote_mint/vault ATA/admin ATA/token+ATA/system; arg
`amount:u64`; quote rate clock at serialized 238..246 (last) and 230..238 (interval), signed
i64, now >= last+interval (6014); writes now then legacy Tokenkeg transfer with vault PDA.
[B] map, [R] body.

### 11. `withdraw_admin` @ 0xfd90 (byte 0x7ec80)
4 accounts (admin/global_params/sol_vault/system); arg `amount:u64`; SOL rate clock at
serialized 138..146 and interval 154..162; System transfer sol_vault -> admin signed by
sol_vault; signed-overflow panics; 6014. [B] map, [R] body.

### 12. `extend_account` @ 0x1001c (byte 0x800e0)
account (owner=mayhem), user signer, system_program, event_authority, program; no args;
target 318 GlobalParams / 74 FeeRecipient / 170 MayhemState; rent top-up + realloc;
ExtendAccountEvent `6161d7905d92167c` (log + CPI); 6016 unknown type. [B] map/event, [R] body.

### 13. `initialize_fee_recipient` @ 0xfc41 (byte 0x7e208)
8 accounts (admin, wsol_mint address=WSOL, fee_recipient `["fee-recipient", index]`,
fee_recipient ATA, global_params, system, token_program=Tokenkeg,
associated_token_program); arg `index:u8`; index < 8 else 6017 (after CPIs, rolled back);
writes bump/index, zeroes 32 opaque bytes; creates the 42-byte PDA + WSOL ATA. [B] map,
[R] body.

### 14. `initialize_global_params` @ 0xfbfc (byte 0x7dfe0)
3 accounts (admin signer/payer, global_params `init` space 254 `["global-params"]`,
system_program); no args; creates the PDA and sets admin = signer, rest zero. [B] map,
[R] body.

### 15. `update_global_params` @ 0x1004b (byte 0x80258)
5 accounts (Admin); 16 Borsh `Option`s writing serialized offsets
8,12,16,24,32,40,137,146,154,129,166,182,190,198,222,230; applies present options,
version += 1 (6002 on overflow, full rollback), GlobalParamsUpdateEvent
`63a75c9898e32629` (log + CPI); self-CPI so an unusable `program` account rejects.
[B] map/event, [R] body.

### 16. `update_admin` @ 0xfe93 (byte 0x7f498)
Admin (5 accounts); arg `new_admin: Pubkey` (wrapper requires len > 31; unaligned 32-byte
copy at `0xfeae..0xfeea` [B]); writes serialized 49; no event. [B] map/args, [R] body.

### 17. `update_trader` @ 0xfe35 (byte 0x7f1a8)
Admin; arg `new_trader: Pubkey`; writes serialized 81; no event. [B] map, [R] body.

### 18. `update_max_sol_per_sweep` @ 0xfd10 (byte 0x7e880)
Admin; arg `value:u64`; writes serialized 174. [B] map, [R] body.

### 19. `update_max_stable_per_sweep` @ 0xfd50 (byte 0x7ea80)
Admin; arg `value:u64`; writes serialized 246. [B] map, [R] body.

### 20. `reset_sol_deployed` @ 0xff2d (byte 0x7f968)
Admin; no args; zeroes the 16-byte sol_deployed (113..129). [B]/[R].

### 21. `reset_stable_deployed` @ 0xff59 (byte 0x7fac8)
Admin; no args; zeroes the 16-byte stable_deployed (206..222). [B]/[R].

### 22. `reset_state` @ 0xfef1 (byte 0x7f788)
Admin; no args; clears reset_prefix[0..40], paused=false, sol_deployed=0,
reset_middle[0..25], reset_stable_prefix[0..24], stable_deployed=0, reset_stable_suffix[0..24];
preserves admin/trader/version/max limits. [B]/[R].

### 23. `stop_trading` @ 0xffb3 (byte 0x7fd98)
Admin; no args; requires paused==false (6000) then sets paused=true. [B]/[R].

### 24. `resume_trading` @ 0xff85 (byte 0x7fc28)
Admin; no args; requires paused==true (6000; the original also returns 6000/TradingPaused when
already active) then sets paused=false. [B]/[R].

---

## Remaining [partial] items / gaps

- `initialize_mayhem_state`: **account order/count and the duration source** are not pinned
  (no source, no successful replay). The set is corroborated by the Pump `create_v2` Mayhem
  CPI and the parser's name strings; the write-back account (`mayhem_state`) and the handler
  effects are [B] at the instruction level.
- The five unnamed GlobalParams roles, the 61 diagnostic rows and the three second-burn
  source-location differences documented by the repo still apply.
- No whole-byte equality: repo records candidate 668,640 vs original 777,408 bytes,
  362,490 differing common bytes, 108,768 excess.
