# Mayhem (`MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e`) - instruction map and handler specs

Status: 25/25 program instructions mapped. The earlier "16 instructions, 8 unmapped"
premise in `DEEPSEEK_PROMPT.md` is stale; see **Corrections** below.

Binary analysed (read-only): `D:\dev\ext\pumpfun-source\evidence\original\mayhem\deployed.so`
(777,408 bytes; repo-recorded SHA-256 `a87fa9f866272514e6acb852b668c4a08aeb173d56c883039991d114d1199bdb`).
`.text` = file offset/vaddr `0x120`, size `0xac8b8` (706,744 bytes). All addresses below are
**virtual byte addresses**; `sbftool` disassembly "pc" units are `byte_addr / 8`.

Decoder: `D:\dev\pumpfun-re\sbftool.py` (repo states it is 0-diff vs `llvm-objdump` on these
files). Marker strings were read directly from `.rodata` (vaddr == file offset in this ELF).

---

## Method (reproducible)

1. Anchor instruction discriminator = `sha256("global:" + snake_case(method))[:8]`.
2. Anchor logs `Instruction: <PascalCase(method)>` (verified: e.g. at `0x101e1` the wrapper
   loads `0xae10b`, length `0x22`; the string is `Instruction: InitializeMayhemState`).
   Converting the logged PascalCase name to snake_case reproduces the hash for every entry.
3. The dispatcher is at **`0xfb06`** (207 instructions, ends `0xfbfb`). It reads the 8-byte
   discriminator from `[r4]` and performs a signed binary search. Each matched case is either
   - `lddw r6, DISC; jeq r0,r6,+off` -> handler stub = `pc+1+off`, or
   - `lddw r6, DISC; jne r0,r6,+off` -> handler stub = fall-through.
   The stub contains `add64 r4,8; add64 r5,-8; call H`; `H` is the handler.
   The first four equality tests (`0xfb07..0xfb15`) are the four 8-byte words of the program id,
   not discriminators.
4. Handler byte address = `H * 8` (because `sbftool` pc = vaddr/8).

All 25 names were confirmed by **both** the `Instruction: ...` rodata string and the
`sha256("global:"+snake)` equality against a dispatcher `lddw` immediate.

---

## Complete map (25/25)

Discriminators are shown in digest order (`sha256(...)[:8].hex()`), the same convention as
`evidence/dispatch-map.json`. `cmp` is the equality comparison form; `jne` cases are why the
old `jeq`-only matcher reported them "unmapped".

| # | method (snake) | log string / struct | discriminator | lddw | cmp | stub | handler (pc) | handler (bytes) | args |
|---:|---|---|---|---|---|---|---|---|---|
| 1 | `buy_pump_swap` | BuyPumpSwap | `de939d076c089151` | 0xfb70 | jeq | 0xfbd0 | 0x1041f | 0x820f8 | `reference:u128, tolerance_bps:u16, retained_reserve_bps:u16` |
| 2 | `sell_pump_swap` | SellPumpSwap | `10c691f0ee6589cb` | 0xfb66 | jeq | 0xfbe4 | 0x103b7 | 0x81db8 | same 20-byte args |
| 3 | `buy_v2` | BuyV2 | `b817ee6167c5d33d` | 0xfb8a | jeq | 0xfbe0 | 0x1034f | 0x81a78 | same 20-byte args |
| 4 | `sell_v2` | SellV2 | `5df6823ce7e940b2` | 0xfb80 | jeq | 0xfbf4 | 0x102e7 | 0x81738 | same 20-byte args |
| 5 | `buy` | Buy | `66063d1201daebea` | 0xfb9a | **jne** | 0xfb9d | 0x1027f | 0x813f8 | same 20-byte args |
| 6 | `sell` | Sell | `33e685a4017f83ad` | 0xfb7d | jeq | 0xfbdc | 0x10217 | 0x810b8 | same 20-byte args |
| 7 | `burn_tokens` | BurnTokens | `4c0f33fee5d77942` | 0xfb90 | **jne** | 0xfb93 | 0xffe1 | 0x7ff08 | none |
| 8 | `sweep_fees` | SweepFees | `afe1624776422294` | 0xfb4c | **jne** | 0xfb4f | 0xfc96 | 0x7e4b0 | none (+16 remaining accounts) |
| 9 | `sweep_fees_admin` | SweepFeesAdmin | `4c93c5e16f9c75e7` | 0xfb97 | jeq | 0xfbc4 | 0xfcd3 | 0x7e698 | none (+16 remaining accounts) |
| 10 | `withdraw_quote_admin` | WithdrawQuoteAdmin | `cc712a30723af859` | 0xfb73 | jeq | 0xfbe8 | 0xfde2 | 0x7ef10 | `amount:u64` |
| 11 | `withdraw_admin` | WithdrawAdmin | `1e1b87bc899eda6b` | 0xfb3c | **jne** | 0xfb3f | 0xfd90 | 0x7ec80 | `amount:u64` |
| 12 | `extend_account` | ExtendAccount | `ea66c2cb96483ee5` | 0xfb27 | **jne** | 0xfb2a | 0x1001c | 0x800e0 | none |
| 13 | `initialize_fee_recipient` | InitializeFeeRecipient | `da578ec8cec516c8` | 0xfb83 | **jne** | 0xfb86 | 0xfc41 | 0x7e208 | `index:u8` |
| 14 | `initialize_global_params` | InitializeGlobalParams | `0d127fea3b28ccda` | 0xfb69 | **jne** | 0xfb6c | 0xfbfc | 0x7dfe0 | none |
| 15 | `update_global_params` | UpdateGlobalParams | `9224de6c59e2f97e` | 0xfba4 | **jne** | 0xfba7 | 0x1004b | 0x80258 | 16 `Option<...>` fields |
| 16 | `update_admin` | UpdateAdmin | `a1b028d53cb8b3e4` | 0xfb24 | jeq | 0xfbbc | 0xfe93 | 0x7f498 | `new_admin:Pubkey` |
| 17 | `update_trader` | UpdateTrader | `c9cf63406556af60` | 0xfb76 | **jne** | 0xfb79 | 0xfe35 | 0x7f1a8 | `new_trader:Pubkey` |
| 18 | `update_max_sol_per_sweep` | UpdateMaxSolPerSweep | `22ada705c885e192` | 0xfb49 | jeq | 0xfbec | 0xfd10 | 0x7e880 | `value:u64` |
| 19 | `update_max_stable_per_sweep` | UpdateMaxStablePerSweep | `804b4c8b7dc46f67` | 0xfb39 | jeq | 0xfbc0 | 0xfd50 | 0x7ea80 | `value:u64` |
| 20 | `reset_sol_deployed` | ResetSolDeployed | `b0ad9da2f0bcc439` | 0xfb5c | **jne** | 0xfb5f | 0xff2d | 0x7f968 | none |
| 21 | `reset_stable_deployed` | ResetStableDeployed | `bf2530b70f5489cb` | 0xfb63 | jeq | 0xfbcc | 0xff59 | 0x7fac8 | none |
| 22 | `reset_state` | ResetState | `9176742a28db948b` | 0xfb46 | jeq | 0xfbd4 | 0xfef1 | 0x7f788 | none |
| 23 | `stop_trading` | StopTrading | `7fb06a3bf27a726f` | 0xfba1 | jeq | 0xfbc8 | 0xffb3 | 0x7fd98 | none |
| 24 | `resume_trading` | ResumeTrading | `922ed456459f1e41` | 0xfb8d | jeq | 0xfbf8 | 0xff85 | 0x7fc28 | none |
| 25 | `initialize_mayhem_state` | InitializeMayhemState | `9dbd5e485545cc2d` | 0xfb59 | jeq | 0xfbf0 | 0x101de | 0x80ef0 | none |

Cross-check: `evidence/dispatch-map.json` lists the same 25 names/discriminators; its
`constant_address`/`target` fields are the same addresses expressed as `pc*8`. I reproduced the
table above independently from the dispatcher, not by reading that file.

### The 26th dispatcher equality case is not an instruction

One `jeq` case has no instruction name: discriminator `e445a52e51cb9a1d`, `lddw@0xfb56`,
`jeq@0xfb58`, stub `0xfbd8`, target **`0x10487`** (bytes `0x82338`). It is called with
`mov64 r1,r2; mov64 r2,r3` and does not do the `r4+=8 / r5-=8` instruction-data adjustment.

`0x10487` verifies a caller key against a 32-byte constant (`0x1048b..0x1049a`) and builds the
literal strings `event_au`+`thority` (`0x104e2..0x104e7` = `event_authority`). This is Anchor's
self-CPI event dispatch, i.e. the `emit_cpi!` receive path, not a program instruction.
Deriving `__event_authority` and checking the caller program id is exactly the `emit_cpi!`
protocol. Do not count it in the instruction set.

### Corrections to the brief

1. **Mayhem has 25 instructions, not 16.** The old matcher counted only `jeq`-form dispatch
   entries (16). Ten entries use `jne` + fall-through, which the matcher skipped.
2. **The "name-guess failures" were false negatives, not bad names.** The names the old
   matcher missed - `buy`, `burn_tokens`, `sweep_fees`, `withdraw_admin`, `extend_account`,
   `initialize_global_params`, `update_global_params`, `update_trader`, `reset_sol_deployed`,
   `initialize_fee_recipient` - are exactly `snake_case(<logged name>)` and hash to real
   dispatcher immediates; they are listed with `cmp=jne` above.
3. **`set_mayhem_virtual_params` is not a Mayhem instruction.** There is no
   `sha256("global:set_mayhem_virtual_params")` lddw (`612a9599bfbca93d` as an integer, bytes
   `3da9bcbf99952a61`) anywhere in this ELF and no `Instruction: SetMayhemVirtualParams`
   string. It belongs to `pump` (`REVERSE_ENGINEERING.md` maps it to pump handler `0x24ab5`).
4. The binary's `Instruction: X` strings are the **method** names PascalCased (Anchor logs the
   program method, not the `#[derive(Accounts)]` struct name). This is why e.g. `buy` and
   `buy_v2` log `Buy`/`BuyV2` even though the reconstruction calls the structs `LegacyBuy`/`BuyV2`.

---

## Per-handler specs

Conventions:
- "Memory offset" means offset in the **in-memory** deserialized account/struct (Rust layout),
  not the Borsh byte offset. Serialized offsets are given separately where they are known.
- `GlobalParams` is the 254-byte `["global-params"]` PDA. Known serialized offsets (repo-verified
  crosswalk): admin 49, trader 81, `sol_deployed` i128 113, `paused` 48, version 162,
  `max_sol_per_sweep` 174, `stable_deployed` i128 206, `max_stable_per_sweep` 246.
- `MayhemState` is the 106-byte account; repo-recorded serialized roles: end_timestamp 16,
  mint 24, field_56 (i128 net quote) 56, field_72 (i128 base-token net) 72, flag_88 88,
  field_89 (last-trade timestamp) 89, status 97, burned_amount 98.
- Anchor custom code = 6000 + enum discriminant.

Evidence tags:
- **[B]** = I verified the address/discriminator/instruction sequence directly in this ELF.
- **[R]** = behaviour from the read-only reconstruction in `programs/mayhem/` plus its
  published differential receipts (9,595 comparisons against this exact captured ELF at the
  Mayhem24 checkpoint). I did not independently re-run those fixtures.

### 1. `buy` (legacy) - handler `0x1027f` **[B]**
- Accounts **[R]**: 23 outer; CPI to Pump uses 18. Key: `trader` (signer, must equal
  GlobalParams.trader via `has_one`), `global_params`, `mayhem_state`
  (`["mayhem-state", mint]`), `mint`, `mayhem_token_vault` (ATA of `sol_vault`), `sol_vault`
  (`["sol-vault"]`), `bonding_curve` (`["bonding-curve", mint]` under Pump id), Pump
  fee/creator/volume/fee-config/event accounts, `bonding_curve_v2`
  (`["bonding-curve-v2", mint]` under Mayhem), `buyback_recipient`.
- Args **[B, spot]**: wrapper at `0x10288..0x102a6` requires data len >= 16 and unpacks
  `reference` (u128 at +0), `tolerance_bps` (u16 at +0x10), `retained_reserve_bps` (u16 at +0x12).
- Checks **[R]**: not paused (6000); optional trade interval (6003/6015 family); deadline
  `now < state.end_timestamp` (6004); on first trade, real SOL reserves >= configured
  minimum, then set status=1; price `vs*1e15/vt` must be within
  `reference +/- reference*tolerance_bps/10000` (6012); output capped by configured cap,
  retained real SOL, and real token reserves.
- CPI **[R]**: `invoke_signed` Pump `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P`,
  disc `66063d1201daebea`, args `(input u64, max_sol u64, 0u8)`, 18 accounts, signed by
  `["sol-vault", bump]`.
- Writes/event **[R]**: reload vault + curve; `GlobalParams.sol_deployed += spent`;
  `MayhemState.field_56 += spent`; `field_72 -= received tokens`; strict
  `overall_limit > low_u64(counter)` (6006) and `coin_limit > low_u64(field_56)` (6007);
  emits the 303-byte `SellEvent` with `side=0` both as log data and `emit_cpi!`.
- Errors **[R]**: 6000 TradingPaused, 6002 MathOverflow, 6004 MayhemModeEnded,
  6006 OverallRiskExceeded, 6007 CoinRiskExceeded, 6008 PumpCpiFailed, 6012 PumpCpiSlippage,
  6015 TradeRateLimit.

### 2. `sell` (legacy) - handler `0x10217` **[B]**
- Accounts **[R]**: 21 outer; 16-account Pump CPI. Same trader/GlobalParams/MayhemState/curve
  shape as `buy`, minus the volume-accumulator accounts.
- Args **[R/B]**: same 20-byte `(reference, tolerance_bps, retained_reserve_bps)`.
- Checks **[R]**: same pause/interval/deadline/reserve/status/price-band gates; output capped
  by cap + retained real SOL; input computed from `vs-output`.
- CPI **[R]**: Pump `33e685a4017f83ad` (sell), 16 accounts, signer `sol-vault` PDA.
- Writes/event **[R]**: `sol_deployed -= received`; `field_56 -= received`;
  `field_72 += tokens`; `side=1` event; no post-CPI risk check on sell.
- Errors **[R]**: 6003 SolReservesTooLow, 6004, 6012, 6015, 6002.

### 3. `buy_v2` - handler `0x1034f` **[B]**
- Accounts **[R]**: 32 outer; 27-account Pump CPI. Adds base/quote ATAs, quote token program,
  ATA program, fee-recipient ATA, creator ATAs, sharing config, user volume ATA,
  buyback ATA.
- Args: same 20 bytes **[R]**.
- Checks **[R]**: quote classification `native = quote_mint == WSOL`; `native_accounting`
  also treats `Pubkey::default()` as native. Native vs stable selects reserve floor
  (GlobalParams 129 vs 222), cap (16 vs 182), overall limit (32 vs 190), coin limit (40 vs 198).
  Same pause/interval/deadline/status/price-band gates.
- CPI **[R]**: Pump `66063d1201daebea`, 27 accounts, `sol-vault` PDA signer. Native path
  additionally funds WSOL (System transfer) + `sync_native` (token tag 17).
- Writes/event **[R]**: `sol_deployed` or `stable_deployed` += spent; `field_56 += spent`;
  `field_72 -= tokens`; strict post-CPI risk checks (6006/6007); 303-byte event with
  native-only fields zeroed for token quotes.
- Errors: 6000, 6002, 6004, 6006, 6007, 6008, 6012, 6015.

### 4. `sell_v2` - handler `0x102e7` **[B]**
- Accounts **[R]**: 31 outer; 26-account Pump CPI (same quote-aware set as `buy_v2` minus the
  buy-only global volume accumulator).
- Args/checks **[R]**: same quote-selected cap/floor/limits; sell input from `vs-output`;
  `minimum = output.saturating_sub(1)`.
- CPI **[R]**: Pump `33e685a4017f83ad`, 26 accounts; native path closes the WSOL quote ATA
  back to the sol vault (token tag 9, signed by `sol-vault`).
- Writes/event **[R]**: `sol_deployed`/`stable_deployed` -= received; `field_56 -= received`;
  `field_72 += tokens`; side=1 event.
- Errors: 6003, 6004, 6008, 6012, 6015, 6002.

### 5. `buy_pump_swap` - handler `0x1041f` **[B]**
- Accounts **[R]**: 31 outer; 25-account PumpSwap CPI. Quote token program is constrained to
  legacy Tokenkeg (`TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA`, constant at `0xad168`);
  base program is Token-2022. Reads `Pool` (zero-padded to 287 bytes, disc
  `f19a6d0411b16dbc`) and `GlobalConfig` (strict 418-byte prefix, disc `95089ccaa0fcb0d9`).
- Args **[R]**: same 20 bytes.
- Budget **[R]**: `effective_quote = pool_quote_token_account.amount + pool.virtual_quote_reserves`
  (checked i128->u64); output = `vs*tokens/(vt+tokens)` capped by cap/retained/effective quote;
  input = `output*vt/(vs+output)`; zero divisor -> 6011 `PumpSwapCpiMathOverflow`.
- CPI **[R]**: PumpSwap `pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA` (constant `0xae2e2`),
  buy disc `66063d1201daebea`, 25 accounts, `sol-vault` PDA signer; native path funds WSOL,
  syncs, and closes it back.
- Writes/event **[R]**: signed-i128 global/state accounting; strict post-CPI risk limits;
  event reports actual pool balances.
- Errors: 6000, 6002, 6004, 6006, 6007, 6010 PumpSwapCpiFailed, 6011, 6012, 6015.

### 6. `sell_pump_swap` - handler `0x103b7` **[B]**
- Accounts **[R]**: 29 outer; 23-account PumpSwap CPI; same fixed Tokenkeg quote constraint.
- Args/checks **[R]**: same 20 bytes; same effective-quote budget; `minimum=output-1`.
- CPI **[R]**: PumpSwap `33e685a4017f83ad`, 23 accounts; native close path as above.
- Writes/event **[R]**: signed-i128 subtract/add; side=1 event.
- Errors: 6003, 6004, 6010, 6011, 6012, 6015, 6002.

### 7. `burn_tokens` - handler `0xffe1` **[B]**
- Accounts **[R/B-strings]**: 12: `mayhem_state` (`["mayhem-state", mint]`), `mint`,
  `mayhem_token_vault` (ATA of `sol_vault`), `sol_vault` (`["sol-vault"]`),
  `bonding_curve` (`["bonding-curve", mint]` under Pump), `global`, `pump_program`
  (`address = PUMP_ID`), `pump_event_authority`, `system_program`, `token_program`,
  `event_authority` (`["__event_authority"]`), `program`. No outer signer is required.
- Args: none (wrapper `0x7ff08` has no instruction-data decoder).
- Checks **[R]**: `state.end_timestamp <= now` else 6005; `state.status != Ended` else 6004.
- CPI **[R]**: SPL Token-2022 `Burn` (tag 8) of the whole vault balance, authority
  `sol_vault` signed by `["sol-vault", bump]`.
- Writes/event **[R]**: `burned_amount = amount`; emits BurnEvent (88-byte payload,
  disc `21592f75527ceefa` = `sha256("event:BurnEvent")[:8]`) as log + `emit_cpi!`;
  sets `status = Ended`.
- Errors: 6004, 6005.

### 8. `sweep_fees` - handler `0xfc96` **[B]**
- Accounts **[R]**: 9 outer + exactly 16 remaining accounts (8 `FeeRecipient`/token-account
  pairs): `trader` (signer, `has_one` GlobalParams.trader), `global_params`, `quote_mint`,
  `trader_quote_ata`, `system_program`, `token_program` (address = Tokenkeg),
  `associated_token_program`, `event_authority`, `program`.
- Args: none.
- Behaviour **[R]**: per pair, token transfer signed by `["fee-recipient", index, bump]`;
  native WSOL additionally moves excess lamports over rent; total capped by
  `max_sol_per_sweep` (native) or `max_stable_per_sweep`; increments the recipient's
  native/stable cumulative counter and (trader path only) timestamp; sequential
  decode/serialize means duplicate pairs see earlier writes.
- Event **[R]**: `SweepEvent` disc `da8286fd656d9598` (observed immediate; `lddw` hits
  0x247d/0x24cc/0x2867/0x28b6 **[B]**).
- Errors: 6016 AccountTypeNotSupported (wrong pair count/type), 6014/6015 for rates.

### 9. `sweep_fees_admin` - handler `0xfcd3` **[B]**
- Same as `sweep_fees` but `admin` signer with `has_one` GlobalParams.admin and **no cap**
  (`u64::MAX`); timestamps are not updated. Errors/event same.

### 10. `withdraw_admin` - handler `0xfd90` **[B]**
- Accounts **[R]**: `admin` (signer, `has_one`), `global_params`, `sol_vault`
  (`["sol-vault"]`), `system_program`.
- Args: `amount:u64`.
- Behaviour **[R]**: optional rate gate reads last SOL timestamp (serialized 138..146) and
  interval (154..162) as signed i64; if both nonzero require `now >= last+interval`
  (6014); writes `now` first; System transfer `sol_vault -> admin` signed by the sol-vault PDA.
  Signed-add overflow panics as in the original.
- Errors: 6014.

### 11. `withdraw_quote_admin` - handler `0xfde2` **[B]**
- Accounts **[R]**: `admin` (signer, `has_one`), `global_params`, `sol_vault`, `quote_mint`,
  `vault_quote_ata`, `admin_quote_ata` (init_if_needed), `token_program`,
  `associated_token_program`, `system_program`.
- Args: `amount:u64`.
- Behaviour **[R]**: quote rate gate reads last timestamp (serialized 238..246) and interval
  (230..238); writes `now`; legacy SPL-Token `transfer` with vault PDA authority. A
  Token-2022-only fixture fails `MissingAccount` and rolls back (the transfer instruction
  targets Tokenkeg).
- Errors: 6014, token-program errors.

### 12. `extend_account` - handler `0x1001c` **[B]**
- Accounts **[R]**: `account` (program-owned, mut), `user` (signer; pays rent shortfall),
  `system_program`, `event_authority`, `program`.
- Args: none.
- Behaviour **[R]**: recognised discriminators -> target sizes: GlobalParams 318,
  FeeRecipient 74, MayhemState 170; equal/larger returns without funding; smaller funds
  rent delta via System transfer, `resize`s (zero-filled), then emits `ExtendAccountEvent`
  (disc `6161d7905d92167c`; `lddw@0x793f` **[B]**) as log + CPI.
- Errors: 6016 AccountTypeNotSupported.

### 13. `initialize_fee_recipient` - handler `0xfc41` **[B]**
- Accounts **[R]**: 8: `admin` (signer/payer; need not equal GlobalParams.admin),
  `wsol_mint` (address = native mint), `fee_recipient` (`["fee-recipient", index]`),
  `fee_recipient_ata` (WSOL ATA of the PDA), `global_params` (PDA, writable),
  `system_program`, `token_program` (address = Tokenkeg), `associated_token_program`.
- Args: `index:u8`.
- Behaviour **[R]**: `index < 8` else 6017 (after init CPIs, rolled back); sets
  `bump`, `index`, zeroes the trailing 32 bytes; creates the 42-byte PDA + native ATA.
- Errors: 6017.

### 14. `initialize_global_params` - handler `0xfbfc` **[B]**
- Accounts **[R]**: 3: `admin` (signer/payer), `global_params`
  (`init`, space 254, `["global-params"]`), `system_program`.
- Args: none.
- Behaviour **[R]**: creates the PDA and sets `admin = signer`; all other fields zero.
- Errors: System/Anchor init errors only.

### 15. `update_global_params` - handler `0x1004b` **[B]**
- Accounts **[R]**: 5: `admin` (signer, `has_one`), `global_params` (mut PDA),
  `system_program`, `event_authority`, `program`.
- Args **[R]**: 16 Borsh `Option`s in recovered order:
  `Option<u32>, Option<u32>, Option<u64>x4, Option<u8>, Option<u64>x2` (fields 0..10),
  then `Option<u64>x5` (fields 11..15) writing serialized offsets
  8,12,16,24,32,40,137,146,154,129,166,182,190,198,222,230.
- Behaviour **[R]**: applies present options, `version += 1` (u32, 6002 on overflow, full
  rollback), emits `GlobalParamsUpdateEvent` (disc `63a75c9898e32629`; `lddw@0x1a02/0x1a5f`
  **[B]**) as log + `emit_cpi!`. Performs a self-CPI, so an unusable `program` account
  rejects/rolls back (the other Admin paths do not touch it).
- Errors: 6002, plus CPI/Anchor errors.

### 16. `update_admin` - handler `0xfe93` **[B]**
- Accounts: 5 (`Admin`: admin signer + `has_one`, global_params, system_program,
  event_authority, program).
- Args: `new_admin: Pubkey` (wrapper requires data len > 31; unaligned 32-byte copy at
  `0xfeae..0xfeea` **[B]**).
- Effects: `GlobalParams.admin = new_admin` (serialized 49). No event.
- Errors: `has_one` 2001/AccountNotSigner 3010/Anchor.

### 17. `update_trader` - handler `0xfe35` **[B]**
- Same 5-account context; arg `new_trader: Pubkey`; writes serialized offset 81. No event.

### 18. `update_max_sol_per_sweep` - handler `0xfd10` **[B]**
- Same 5-account context; arg `value:u64`; writes serialized offset 174.

### 19. `update_max_stable_per_sweep` - handler `0xfd50` **[B]**
- Same 5-account context; arg `value:u64`; writes serialized offset 246.

### 20. `reset_sol_deployed` - handler `0xff2d` **[B]**
- Same 5-account context; no args; zeroes the 16-byte `sol_deployed` (serialized 113..129).

### 21. `reset_stable_deployed` - handler `0xff59` **[B]**
- Same 5-account context; no args; zeroes the 16-byte `stable_deployed` (serialized 206..222).

### 22. `reset_state` - handler `0xfef1` **[B]**
- Same 5-account context; no args. **[R]** clears `reset_prefix[0..40]`, `paused=false`,
  `sol_deployed=0`, `reset_middle[0..25]`, `reset_stable_prefix[0..24]`,
  `stable_deployed=0`, `reset_stable_suffix[0..24]`; preserves admin, trader, version,
  max_sol/max_stable.

### 23. `stop_trading` - handler `0xffb3` **[B]**
- Same 5-account context; no args. **[R]** requires `paused == false` else 6000; sets
  `paused = true`.

### 24. `resume_trading` - handler `0xff85` **[B]**
- Same 5-account context; no args. **[R]** requires `paused == true` else 6000 (the original
  also uses 6000/TradingPaused when already active); sets `paused = false`.

### 25. `initialize_mayhem_state` - wrapper `0x101de`, parser `0xd25f`, handler `0x10527` **[B, partial]**

This is the only handler with **no accepted reconstruction** in the repo; the following is my
static reading, with uncertainty called out.

- Call graph **[B]**: `0x101de` logs `Instruction: InitializeMayhemState` (string at `0xae10b`,
  len `0x22`), calls the generated accounts parser `0xd25f` (byte `0x693b8`), then the
  business handler **`0x10527`** (byte `0x82938`), then the account-exit/serializer
  `0xdabe` (byte `0x6d5f0`).
- Args: **none**. The wrapper (`0x101de..0x10216`) never touches `r4/r5` (instruction data);
  it only moves accounts (`r2/r3`), builds a `Context { program_id, &accounts }` at
  `r10-0x2f8`, and calls parser -> handler -> exit.
- Accounts: **provisional**. The parser's rodata references (read at `0xadaf4+16`,
  `0xadb89+16`, `0xadb96+16`, `0xadbc9+16`, `0xadc0e+16`) contain the name strings
  `system_program`, `global_params`/`global-params`, `program`, `token_program`,
  `associated_token_program`, `mayhem_state`/`mayhem-state`, `mayhem_token_vault`,
  `bonding_curve`/`bonding-curve`, `global`, `pump_program`, and a `payer` create-account
  path (`payer` string built at `0xd2b6`). A plausible schema is:
  `payer/admin (signer)`, `mayhem_state` (`init`, `["mayhem-state", mint]`),
  `mint`, `mayhem_token_vault` (ATA of `sol_vault`), `sol_vault` (`["sol-vault"]`),
  `bonding_curve` (`["bonding-curve", mint]`, `seeds::program = PUMP_ID`), pump `global`,
  `pump_program` (`address = PUMP_ID`), `system_program`, `token_program`,
  `associated_token_program`, `event_authority` (`["__event_authority"]`), `program`.
  The source reconstruction calls the account count/order **unresolved**; treat this list as
  a hypothesis, not a confirmed schema (the shared parser helpers also pull in
  `admin_quote_ata`/`wsol_mint`/`fee_recipient` strings, which belong to other contexts).
- Behaviour **[B]**, memory offsets in the in-memory accounts struct (not Borsh offsets):
  1. `r9 = byte [T+0x2c4]` (`0x1054f`) - a duration/limit byte (likely read from the pump
     global config inlined in the context; semantics not proven).
  2. `r9 *= 3600` (`0x10557`) with checked signed overflow; overflow path at `0x10583`.
  3. `Clock::get` via `0x13dfa`; timestamp available at `[r10-0x10]` (`0x10555`).
  4. `[T+0x1a0] = now` (`0x10556`).
  5. `[T+0x1a8] = now + r9*3600` (`0x10562`) - this is the state `end_timestamp` memory slot
     (burn reads `[ctx+0x1a8]` and requires `<= now`).
  6. `[T+0x160..0x180] = 32-byte mint key` copied from an `AccountInfo.key` at `[T+0x58]`
     (`0x10547..0x1056a`).
  7. zeroes `[T+0x180]`, `[T+0x188]`, `[T+0x190]`, `[T+0x198]`, `[T+0x1b8]` (u64 each),
     u16 at `[T+0x1c0]`; sets `[T+0x1b0] = now` (`0x1056c..0x10571`).
  8. borrow counters are released and the wrapper returns (success path `r0=2`).
  Interpretation (medium confidence): initializes `mint`, a start/end timestamp pair
  (`0x1a0`/`0x1a8`, end = now + hours*3600), zeroes the signed net counters
  (`field_56`/`field_72` memory slots), `burned_amount` (`0x1b8`), and status (`0x1c0`).
  Burn's independently recovered reads of `end_timestamp` at memory `0x1a8` and
  `burned_amount` at `0x1b8` corroborate the mapping.
- CPIs: parser-side System `create_account` for the `mayhem-state` PDA (the `payer` string
  and init path); whether the token vault is `init_if_needed` (ATA CPI) is **not** confirmed.
  No CPI appears in `0x10527` itself.
- Errors: overflow path (likely `MathOverflow`, 6002) plus Anchor parser errors
  (seeds/ownership/`AccountNotEnoughKeys`), not independently enumerated.
- Confidence: **static-only, no successful original invocation**. The repo marks this lane
  "stopped/unrecovered"; do not treat the account list or field semantics as proven.

---

## Verification notes / caveats

- **[B]** claims above were produced by decoding the captured ELF with `sbftool.py` and reading
  `.rodata` directly. Handler addresses are the first direct `call` in each dispatch stub;
  discriminators are `sha256("global:"+snake)[:8]` compared against the dispatcher `lddw`.
- **[R]** behavioural claims come from `programs/mayhem/src/*` plus
  `repro/mayhem/twentyfour/*` receipts (9,595 functional comparisons, 0 mismatches at that
  checkpoint) and `audit/mayhem/RECOVERY.md`. I did not re-execute them; they are reference
  evidence for the user, not my own differential run.
- No byte-identity claim is made for Mayhem. The repo records
  `full_byte_equality: false` (candidate 668,640 bytes vs original 777,408; 362,490 differing
  common bytes, 108,768 excess).
- Known repo-documented divergences still apply: 61 diagnostic rows, three second-burn
  source-location differences, `initialize_mayhem_state` absent, and five unnamed
  `GlobalParams` roles.
