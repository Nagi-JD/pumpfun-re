# 04 — Creation cluster (`create`, `create_v2`, `set_mayhem_virtual_params`)

Binary: `D:/dev/ext/pumpfun-source/evidence/original/pump/deployed.so`
Recovered source: `D:/dev/ext/pumpfun-source/programs/pump/src/` (`create.rs`, `create_v2.rs`, `trade_types.rs`, `nested_create.rs`, `lib.rs`)
Tool: `py -3.12 D:/dev/pumpfun-re/sbftool.py …`

## Dispatch map (verified from the binary)

| Handler | Anchor disc (8 bytes) | disc lddw @ | wrapper @ | real `execute` @ | log string |
|---|---|---|---|---|---|
| `create` | `181ec828051c0777` | `0x23737` | `0x24c1b` | `0x27164` | `Instruction: Create` (`0x1b7d68`, 0x13) |
| `create_v2` | `d6904cec5f8b31b4` | `0x2373b` | `0x24d15` | indirect (see §2.0) | `Instruction: CreateV2` (`0x1b7d7b`, 0x15) |
| `set_mayhem_virtual_params` | `3da9bcbf99952a61` | `0x2372f` | `0x24ab5` | `0x26ff8` | `Instruction: SetMayhemVirtualParams` (`0x1b7d20`, 0x23) |

Log strings dumped directly from rodata via the ELF program headers (vaddr→file-offset map); each matches its discriminator, so the three handlers in scope are positively identified. `sbftool disc global:<name>` returns the three discriminators above; `sbftool callers 0x26ff8` → single caller `0x24aea` (the set_mayhem wrapper), and `sbftool callers 0x19a7b` → single caller `0x24ac9` (same wrapper), so `0x26ff8`/`0x19a7b` are exclusive to `set_mayhem_virtual_params`.

---

## 1. `create` — handler @ wrapper `0x24c1b`, execute `0x27164`

### 1.1 Purpose
Creates a classic (SPL-Token, Tokenkeg) pump.fun coin: initializes the mint (6 decimals), mints the full `global.token_total_supply` to the bonding-curve ATA, revokes mint authority, writes the initial bonding-curve account, and creates the Metaplex metadata account. SOL-quoted only (no quote-mint / mayhem / holder-reward branches). Recovered `create.rs` is complete and matches the binary.

### 1.2 Accounts validated (from `Create<'info>`, `create.rs`)
- `mint` — `init, mint::decimals=6, mint::authority=mint_authority` (SPL Token).
- `mint_authority` — PDA `["mint-authority"]`.
- `bonding_curve` — `init, space=166, seeds=["bonding-curve", mint]`.
- `associated_bonding_curve` — ATA(mint, bonding_curve).
- `global` — PDA `["global"]`.
- `mpl_token_metadata` — program `metaqbxx…518x1s`.
- `metadata` — PDA `["metadata", mpl_program, mint]` with `seeds::program = mpl_token_metadata`.
- `user` (mut signer), `system_program`, `token_program` (Tokenkeg), `associated_token_program`, `rent`.

### 1.3 require! conditions and ORDER (binary-authoritative)
1. **`creator != Pubkey::default()`** → `CreatorShouldNotBeZero`.
   Verified in binary: `execute` @ `0x27164` zeroes a 32-byte stack scratch (`0x27169-0x2716c`), `memcmp`s the 32-byte `creator` arg against it via `0x366cf` (`r3=0x20`) at `0x27172`, and `jeq r0,0x0,+0x249` (`0x27176`) branches to the error path when `creator` is all-zero. This is the first and only `require!` in `create`, matching `create.rs:21`.

   No other explicit `require!` — Anchor `#[account(init …)]`/seed/PDA constraints are enforced by the generated `try_accounts` (the `callx` + `0x1f0b` next-account calls in the wrapper), not by `execute`.

### 1.4 CPIs (in order)
1. **Metaplex `CreateMetadataAccountV3`** (`invoke_signed`, signer = `["mint-authority", bump]`). Data prefix byte `33` then borsh(name, symbol, uri), seller-fee 0, creators=[mint_authority, verified, share=100], collection/uses none (`data.extend_from_slice(&[0,100,0,0,0,0])`).
2. **`token::mint_to`** `global.token_total_supply` to `associated_bonding_curve`, authority = mint_authority (signed).
3. **`token::set_authority`** `MintTokens → None` on `mint` (revokes mint authority permanently).

### 1.5 Initial bonding-curve state written (`create.rs:41`)
```
curve.virtual_token_reserves          = global.initial_virtual_token_reserves
curve.virtual_quote_reserves          = global.initial_virtual_sol_reserves
curve.real_token_reserves             = global.initial_real_token_reserves
curve.token_total_supply              = global.token_total_supply
curve.creator                         = creator
curve.initial_virtual_quote_reserves  = global.initial_virtual_sol_reserves
```
All other `BondingCurve` fields (offsets per `trade_types.rs`: `complete`, `is_mayhem_mode`, `is_cashback_coin`, `quote_mint`, `creator_fee_bps`, `can_edit_creator_fee`, `is_holder_reward`, `depth=0`, `post_complete_*`) default to zero/false. Then `emit!(CreateEvent)` + `emit_cpi!(CreateEvent)` (event disc `1b72a94ddeeb6376`, `sbftool disc event:CreateEvent` → lddw@`0x2c2cf`). Event has `is_mayhem_mode=false`, `quote_mint=default`, `virtual_quote_reserves=initial_virtual_sol_reserves`, `creator_fee_bps=0`, `depth=0`.

### 1.6 GAP vs recovered `.rs`
None material. `create.rs` is a faithful, complete reconstruction; the binary confirms the single creator-zero guard and the three CPIs in order.

---

## 2. `create_v2` — handler @ wrapper `0x24d15`, execute via indirect dispatch

### 2.0 Disassembly status
The `create_v2` wrapper (`0x24d15`) builds the `Accounts` struct through repeated `0x1f0b` next-account calls and then dispatches the body through a fat-pointer vtable (`0x24d58: callx r2`, target loaded from `[r8+0x7]→[*+0x0]`). The body is therefore **not statically pinned** from a direct call edge within the sbftool budget (the `0x1bd820` operand near the call site resolves to rodata string/type-descriptor pointers, not a code vtable — `scratchpad/vt.py`). `0x11703` reached from the wrapper is the `OptionBool`/bool-byte decoder (reads one byte, accepts 0/1, else formats error id `0x15` from string `0x1b3098`), i.e. `is_cashback_enabled`/`is_holder_reward` deserialization, **not** the business logic. Consequently §2.1–2.5 below are taken from the recovered `create_v2.rs` (which is detailed) and cross-checked against the binary where a direct edge exists; the mayhem/CPI gap in §2.6 is corroborated by the error-enum and account-struct evidence that is present in the binary.

### 2.1 Purpose
Token-2022 creation path with optional alternate quote mint, configurable creator fee, holder-reward routing, and (in the deployed binary) a Mayhem-mode branch. Mint uses Token-2022 with a `metadata_pointer` extension pointing at the mint itself; metadata is written via Token-2022 `token_metadata_initialize` + `token_metadata_update_authority` CPIs (discriminators `210,225,30,162,88,184,77,141` and `215,228,166,228,84,100,86,123` in `create_v2.rs`), not Metaplex.

### 2.2 Accounts validated (`CreateV2<'info>`)
- `mint` — `init, decimals=6, mint::authority=mint_authority, token_program=token_program, extensions::metadata_pointer::metadata_address=mint` (Token-2022 `InterfaceAccount`).
- `mint_authority` — PDA `["mint-authority"]`.
- `bonding_curve` — `init, space=166, seeds=["bonding-curve", mint]`.
- `associated_bonding_curve` — ATA(mint, bonding_curve, token_program).
- `global` — PDA `["global"]`.
- `user` (mut signer), `system_program`, `token_program` = Token-2022, `associated_token_program`.
- `mayhem_program_id` — `address = MAYHEM_ID` (`MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e`).
- `global_params` — PDA `["global-params"]` seeds::program = MAYHEM_ID.
- `sol_vault` — PDA `["sol-vault"]` (mut) seeds::program = MAYHEM_ID.
- `mayhem_state` — PDA `["mayhem-state", mint]` (mut) seeds::program = MAYHEM_ID.
- `mayhem_token_vault` — unchecked (mut).
- plus `remaining_accounts` for the alternate-quote path: `[quote_mint, quote_ata, quote_token_program, (quote_control), (nested curve chain…)]`.

### 2.3 require! conditions and ORDER (from `create_v2.rs`; SOL branch verified-complete)
1. `global.create_v2_enabled` → `CreateV2Disabled`.
2. `!is_cashback_enabled.0` → `CashbackDeprecated` (cashback permanently rejected).
3. If `is_holder_reward.0`: `global.is_holder_reward_enabled` → `HolderRewardDisabled`, then **override** `creator = PDA(["holder-rewards", mint])`.
4. `creator != default` → `CreatorShouldNotBeZero`.
5. Quote selection (only if `remaining_accounts` non-empty):
   a. `len >= 3` → `NotEnoughRemainingAccounts`.
   b. `quote_token_program ∈ {Tokenkeg, Token-2022}` AND `.executable` → `InvalidQuoteTokenProgram`.
   c. If quote mint == default or == native WSOL mint → treated as SOL (no fee config).
   d. Literal reject `quote == 9pan9bMn5HatX4EJdBwg9VgCa7Uz5HL8N1m5D3NdXejP` → `UnsupportedQuoteMint` (checked at `0x1f6a8` per source note, before whitelist/control selection).
   e. If `global.whitelisted_quote_mints.contains(quote)` → reserves = `global.initial_virtual_quote_reserves`, `can_configure_fee=false`.
   f. Else require `len>=4`, validate `quote_control` PDA(`["quote-control"]`, owner==program) → `InvalidQuoteControl`; look up `control_entry`; if absent, walk the nested quote-curve chain (`nested_create::walk`, sets `depth`).
   g. `quote.owner == quote_token_program` → `UnsupportedQuoteMint`.
   h. If Token-2022 quote: `quote_extensions_supported(data)` → `UnsupportedQuoteMint` (allows ext kinds 4/12/16/18/19/25/26 freely; 1 transfer-fee ≥108B; 6 default-account-state enabled; 14 permanent-delegate must be zero-delegate; else reject).
   i. ATA address check → `InvalidAssociatedQuoteBondingCurve`; create the quote ATA for the curve.
6. Fee: if `can_configure_fee && creator_fee_bps.0>0` → require `global.creator_fee_configurable` (`CreatorFeeNotConfigurable`) and `<= global.max_configurable_creator_fee_bps` (`CreatorFeeBpsOutOfRange`); else fee=0.
7. `name.len()<=32` / `symbol.len()<=13` / `uri.len()<=200` → `NameTooLong`/`SymbolTooLong`/`UriTooLong`.

`CreationOptionU64` and `OptionBool` deserialize as “absent ⇒ 0/false” (short-read tolerant), so older clients that omit the trailing args default to no fee / no holder-reward.

### 2.4 CPIs (SOL branch)
Rent top-up `system::transfer` to the mint for Token-2022 size (`234+4+64+16+len(name+symbol+uri)`), then `token_metadata_initialize`, `token_metadata_update_authority(None)`, `mint_to(token_total_supply)`, `set_authority(MintTokens→None)`. Alternate-quote branch additionally does `associated_token::create` for the quote ATA.

### 2.5 Initial bonding-curve state written (`create_v2.rs:95`)
Same six base fields as `create`, plus `quote_mint`, `creator_fee_bps=fee`, `is_holder_reward`, `depth`, and `virtual_quote_reserves = initial_virtual_quote_reserves` (the selected `reserves`, not necessarily `initial_virtual_sol_reserves`). `emit!`/`emit_cpi!(CreateEvent)`.

### 2.6 GAP vs recovered `.rs` (the PARTIAL markers)
- **Mayhem branch is STUBBED in source, LIVE in binary.** `create_v2.rs:39` opens with `require!(!is_mayhem_mode, crate::ReconstructionError::ReconstructionBranchUnsupported)` — a reconstruction placeholder, **not** a real program error. The deployed binary carries dedicated mayhem errors the recovered `create_v2.rs` never references: `CpitializeMayhemFailed` (lib.rs:294), `MayhemModeDisabled` (295), `MayhemModeQuoteMintNotAllowed` (338). Combined with the five mayhem accounts hard-wired into `CreateV2` (`mayhem_program_id = MAYHEM_ID`, `global_params`, `sol_vault`, `mayhem_state=["mayhem-state",mint]`, `mayhem_token_vault`), the deployed `create_v2` with `is_mayhem_mode=true` instead **gates on `global.mayhem_mode_enabled` (→ `MayhemModeDisabled`) and CPIs into the Mayhem program `MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e` to initialize `mayhem_state`/`sol_vault` (→ `CpitializeMayhemFailed` on CPI failure), and restricts the quote mint (→ `MayhemModeQuoteMintNotAllowed`).** None of that logic is reconstructed. Evidence: `grep mayhem lib.rs` error enum; `CreateV2` account struct `create_v2.rs:26-35`; body not statically pinned (§2.0).
- **Token-2022 quote ancestry (`nested_create::walk`, `control_entry`) and whitelist admission** are present in source but their exact binary branch order was not re-verified here because the body is behind the indirect dispatch (§2.0). Flag for a follow-up pass that resolves the `0x24d58` vtable.
- **Holder-reward creator override** (`PDA(["holder-rewards",mint])`) is in source but likewise unverified against the binary branch.

---

## 3. `set_mayhem_virtual_params` — wrapper `0x24ab5`, execute `0x26ff8` — **UNRECOVERED**

### 3.0 Status
**No source counterpart exists.** The instruction is absent from `lib.rs` (no `pub fn set_mayhem_virtual_params`, verified by `grep -n "pub fn" lib.rs`) and there is no `.rs` file for it (`grep -rn "virtual_params\|SetMayhem" src/` → only the `create_v2.rs` mayhem-account comments). It is nonetheless a real, dispatchable instruction: disc `3da9bcbf99952a61`, dispatch `lddw@0x2372f`, log `Instruction: SetMayhemVirtualParams`. Everything below is reconstructed from the binary.

### 3.1 Reconstructed behavior

**Wrapper `0x24ab5` (Anchor glue):**
- `0x24ab9-0x24abc`: `sol_log_("Instruction: SetMayhemVirtualParams")` (ptr `0x1b7d20`, len `0x23`).
- `0x24ac9`: `call 0x19a7b` = combined `try_accounts` + argument decode (`r2` = instruction-data pointer, `r5` = `[*-0xff8]` runtime base). `0x19a7b` is a compact (≈20-insn) next-account/decoder exclusive to this handler — it consumes **few accounts** (it pulls one account from the `[ctx+0x0]`/`[ctx+0x8]` account array and bumps its refcount), consistent with a small admin instruction (authority signer + the mayhem params/state account(s)).
- `0x24acb`: `jeq r8,0x2,+0x5c` → on decode error (variant 2) skip straight to account-drop/cleanup.
- `0x24acc-0x24ae5`: marshals the decoded arguments onto the stack — a `u32` (default-initialized to `-1` at `0x24abd`, i.e. an optional/sentinel field), two `u64`s (`[r10-0x6c0]`, `[r10-0x6c8]`), and copies a 0x6c0-byte accounts blob (`memcpy 0x366c2`). The resulting arg record exposes `accounts_ptr` at `+0x8` and a **bool flag at `+0x23`**.
- `0x24aea`: `call 0x26ff8` (the handler body). On return (`0x24aec: jeq r1,0x2`) it runs the Anchor exit/serialize-back and account-refcount drops (`0x24af3 call 0x19ea2`, then the `-1` refcount decrements `0x24af4-…`).

**Execute `0x26ff8` (119 insns):**
- `0x26ff9`: `r7 = [args+0x23]` — the **bool flag** argument.
- `0x26ffa`: `r8 = [args+0x8]` — accounts context.
- `0x26ffb-0x27005`: reads a **contiguous 6×u64 virtual-parameter block** from the accounts context: `[r8+0x210]`, `[r8+0x218]`, `[r8+0x220]`, `[r8+0x228]`, `[r8+0x230]`, `[r8+0x238]` (and later `[r8+0x240]`, `[r8+0x248]` at `0x27048-0x27049`). These are the mayhem virtual reserve/param values.
- `0x27006-0x2700e`: `call 0x1447e` with `r2 = r8+0x1f0` (an account/sub-struct), `r3 = [r8+0x688]`, `r4 = [r8+0xe8]` — a **validation / bounds helper**. `0x1447e` reads two bool gates (`[r2+0x99]`, `[r2+0x9a]`) and an i64 (`[r2+0x60]`), then enforces lamport/reserve thresholds using constants `0xF4240` (1e6), `0x989680` (1e7) and `0xE8D4A51000` (1e12) — i.e. sanity bounds on the reserve magnitudes. `0x27011: jne r2,0x2,+0x14d` → on non-Ok it jumps to the error/return path (≈`0x2715e`).
- `0x27014`: `call 0x34127` (`Clock::get`-class), `0x27016: jne r1,0,+0x21` on error.
- `0x27018-0x27021`: reads a second account’s data (`[r8+0x58]` → data ptr → fields `+0x0/+0x8/+0x10/+0x18`), folded into the event.
- `0x27037 call 0x35633` (alloc 0x100), `0x27042 call 0x33777` (format/serialize), then builds a **0x60-byte event buffer** (`stdw [r10-0xc8],0x60`) whose first 8 bytes are the event discriminator `757be4b6a1a8dcd6` (`[117,123,228,182,161,168,220,214]`, stored via `lddw -0x2923575e491b848b` at `0x2704f`/`0x270a1`). The buffer is filled with the param block (`+0x30..+0x58`), the second account’s fields (`+0x10..+0x28`), and the bool/helper result (`+0x8`).
- `0x2706b call 0x3409f` and a second identical build at `0x2707f-0x270ae` → the classic **`emit!` + `emit_cpi!`** double-emit (self-CPI with program refcount bump at `[r8+0x190]`/`[r8+0x198]`). The event discriminator `757be4b6a1a8dcd6` does **not** match `CreateEvent` (`1b72a94ddeeb6376`), `SetParamsEvent` (`dfc39ff63e308f83`), or the guessed `event:MayhemVirtualParamsEvent` (`b1e1adfde8fb068c`) / `event:SetMayhemVirtualParamsEvent` (`e3f39a10e96e0e2d`) — so the on-chain event struct name differs from all of those; report the raw discriminator.

**Net reconstructed semantics:** an admin/authority instruction over a small account set (signer + the mayhem `global-params`/`mayhem_state` PDAs) that validates a 6–8 × u64 virtual-parameter block against hard lamport bounds (1e6 / 1e7 / 1e12 via `0x1447e`), reads a bool flag argument (`args+0x23`), and emits a parameter event (disc `757be4b6a1a8dcd6`) both as a log and via self-CPI.

### 3.2 GAP / open items (concrete, with addresses)
- **Persistence site not located.** Within `0x26ff8` every store targets the stack (`[r10-…]`) or the malloc’d event buffer (`[r1+…]`/`[r2+…]`); there is **no `stxdw [r8+off]` write back into the accounts/param block** in the disassembled body. So either (a) the new params are written into the `mut` account during the `0x19a7b` decode / Anchor serialize-back path (wrapper `0x24af3 call 0x19ea2`), or (b) the mutation lives behind the `0x1447e` validation helper. **Needs a follow-up trace of `0x19a7b` (full body) and `0x1447e` (`0x14480-0x144c4+`) to pin exactly which account field receives the new virtual params.** As disassembled, `0x26ff8` is a validate-and-emit routine; the "set" store is not yet proven.
- **Account list / PDA & signer checks not fully enumerated.** `0x19a7b` is small and exclusive to this handler but its full constraint set (which account is the authority signer, whether `mayhem_state`/`global-params` PDA seeds are re-derived, whether `address == MAYHEM_ID` is enforced) was not exhaustively disassembled. The accounts-context offsets used by the body (`[r8+0x58]`, `[r8+0xe8]`, `[r8+0x188/0x190/0x198]` refcounts, `[r8+0x1f0]`, `[r8+0x210..0x248]`, `[r8+0x688]`) give the layout but not the seed/signer assertions. **Follow-up: disassemble `0x19a7b` in full.**
- **Event struct name unknown** — only the raw disc `757be4b6a1a8dcd6` is recovered (no matching `event:` name tried succeeded).
