# pump `create_v2` Mayhem mode - end-to-end flow

Private analysis for the user. Tags: **[B]** = confirmed in the deployed bytecode/rodata;
**[R]** = from the read-only reconstruction / cluster spec; **[partial]** = inferred (reason
stated). No byte-identity or exhaustive-behavior claim.

Sources: `spec/04-creation.md` (create_v2 / Mayhem gap), `programs/pump/src/create_v2.rs`
(reconstruction - Mayhem branch stubbed), `mayhem_specs.md` / `mayhem_map.md`
(initialize_mayhem_state), and the pump binary. Addresses are `sbftool` pc units.

---

## 1. Context and accounts (deployed `CreateV2`) [R/B]

The deployed `CreateV2` context has 16 accounts. 11 are the normal create path; 5 are the
hard-wired Mayhem accounts:

| # | account | constraint |
|---:|---|---|
| 1 | `mint` | `init`, 6 decimals, authority `mint_authority`, Token-2022, `metadata_pointer` -> mint |
| 2 | `mint_authority` | `["mint-authority"]` PDA |
| 3 | `bonding_curve` | `init`, space 166, `["bonding-curve", mint]` |
| 4 | `associated_bonding_curve` | ATA(mint, authority=bonding_curve) |
| 5 | `global` | `["global"]` (pump) |
| 6 | `user` | mut signer |
| 7 | `system_program` | |
| 8 | `token_program` | Token-2022 (typed `Program<Token2022>`) |
| 9 | `associated_token_program` | |
| 10 | `mayhem_program_id` | **address = `MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e`** |
| 11 | `global_params` | `["global-params"]` under `MAYHEM_ID` |
| 12 | `sol_vault` | `["sol-vault"]` under `MAYHEM_ID`, mut |
| 13 | `mayhem_state` | `["mayhem-state", mint]` under `MAYHEM_ID`, mut |
| 14 | `mayhem_token_vault` | unchecked, mut (ATA of the Mayhem `sol_vault`) |
| 15 | `event_authority` | pump `["__event_authority"]` |
| 16 | `program` | pump self |

The 5 Mayhem hard-wires (`mayhem_program_id`, `global_params`, `sol_vault`,
`mayhem_state`, `mayhem_token_vault`) are the only Mayhem-specific accounts in the outer
context (spec 04 Sec.2.2/Sec.2.6) [B for the account/PDAs; the source reconstruction keeps them
"unused for normal creation"].

## 2. Normal `create_v2` flow (the base the Mayhem branch extends) [R]

The reconstruction (`create_v2.rs`) implements the non-Mayhem flow; the deployed branch is
the same until the Mayhem fork:

1. Gates: `global.create_v2_enabled` (CreateV2Disabled), `!is_cashback_enabled`
   (CashbackDeprecated); holder-reward creator = `["holder-rewards", mint]` if requested
   else the arg creator; creator != default (CreatorShouldNotBeZero).
2. Quote selection: empty remaining -> native/default; else `remaining[0..3]` =
   `[quote_mint, quote_ata, quote_token_program]`; Token-2022 extension whitelist; optional
   `quote_control` (remaining[3]) / nested quote chain; `ata` must be the canonical quote
   ATA of the bonding curve; create it.
3. Fee: configurable only when the quote is allowed; `creator_fee_bps` <= global max.
4. Name/symbol/uri length checks.
5. Token-2022 metadata CPIs (not Metaplex):
   - `token_metadata_initialize` disc bytes `210,225,30,162,88,184,77,141`
     (`0xd2e11ea258b84d8d`), accounts `[mint, mint_authority(signer), mint, mint_authority]`.
   - `token_metadata_update_authority` disc bytes `215,228,166,228,84,100,86,123`
     (`0xd7e4a6e45464567b`), accounts `[mint, mint_authority(signer)]`.
6. `mint_to` `global.token_total_supply` -> `associated_bonding_curve` (mint authority PDA).
7. Revoke mint authority (Token-2022 `SetAuthority(MintTokens, None)`).
8. Write the `BondingCurve` fields and emit `CreateEvent` (log + `emit_cpi!`).

In the reconstruction the Mayhem fork is a **stub**: `create_v2.rs:39`
`require!(!is_mayhem_mode, ReconstructionBranchUnsupported)` - a placeholder, not a real
program error. The deployed binary implements the branch.

## 3. Deployed Mayhem branch - what is established

### 3.1 Gates / errors [R + spec 04]
- `global.mayhem_mode_enabled` must be true; otherwise **MayhemModeDisabled**.
- The quote mint is restricted in Mayhem mode; otherwise **MayhemModeQuoteMintNotAllowed**.
  (The exact accepted quote set is not fully decoded; the source names the error, and the
  normal quote path is general.)
- The Mayhem CPI failure path raises **CpitializeMayhemFailed** (the source's spelling).
- The create gate `CreateV2Disabled`, cashback/holder/fee/name checks above apply first in
  the non-Mayhem order; the deployed Mayhem branch inserts its mode/quote checks at the
  corresponding point. The exact interleaving is [partial].

### 3.2 `initialize_mayhem_state` CPI - data payload is exact [B]

The pump binary contains the CPI data builder:
- `0x23181: lddw r1, 0x2dcc4555485ebd9d` = bytes `9d bd 5e 48 55 45 cc 2d`
  = `sha256("global:initialize_mayhem_state")[:8]` (`9dbd5e485545cc2d`).
- `0x23183: stxdw [r7+0x0], r1` writes **only the 8-byte discriminator**; the data length is
  `8` (`stdw [r10-0x58], 8` at `0x231ac`). **The Mayhem init CPI has no arguments.**
- The helper `0x2316a` (211 insns) serializes an `AccountMeta` array with a **0x22 (34-byte)
  stride** (`0x23194: mul64 r4,0x22`; stores pubkey 32 + is_signer/is_writable at
  `+0x28/+0x29`), then invokes. It is called from `0x116fc` inside the create body
  `0x114b1`; the account keys are copied into the meta array at `0x116e0-0x116f3`
  (keys from stack slots `-0x308`, `-0x300`, `-0x470`, `-0x4a0`, `-0x2f8`, `-0x2d0`, ...).
- This confirms: **disc-only payload, N account metas built by the create_v2 body**, not a
  Borsh args struct.

### 3.3 `initialize_mayhem_state` account list - [partial]

The Mayhem handler (`0x101de` wrapper -> parser `0xd25f` -> handler `0x10527`) takes no
args and initializes the per-coin `mayhem_state` (mint, timestamps, zeroed counters;
persistence via the Anchor account exit `0xdabe` to the `mayhem_state` PDA). The Mayhem
parser references `system_program`, `global_params`/`global-params`, `program`,
`token_program`, `associated_token_program`, `mayhem_state`/`mayhem-state`,
`mayhem_token_vault`, `bonding_curve`/`bonding-curve`, `global`, `pump_program`, and the
`payer` create path; the account **order is not statically pinned** (the name references
are in constraint/error tails). Combining the Mayhem parser with the pump `CreateV2`
accounts, the most likely CPI account order is:

1. `payer` / signer (the pump `user`; create-account payer)
2. `global_params` (`["global-params"]` under `MAYHEM_ID`)
3. `mayhem_state` (`["mayhem-state", mint]`; `init`, space 170)
4. `mint` (the new pump mint)
5. `mayhem_token_vault` (ATA of the Mayhem `sol_vault`; the CreateV2 unchecked mut account)
6. `sol_vault` (`["sol-vault"]` under `MAYHEM_ID`)
7. `bonding_curve` (`["bonding-curve", mint]` under pump; the new curve)
8. pump `global` (`["global"]`)
9. `pump_program` (`6EF8...`)
10. `pump_event_authority` (pump `["__event_authority"]`)
11. `system_program`
12. `token_program` (Token-2022)
13. `associated_token_program`
14. (optional) Mayhem `event_authority`/`program` if the init parser requires them

**Why [partial]:** the CPI meta array is built by the create body (`0x116e0-0x116f3`) and
the Mayhem parser's account-name strings are not in consumption order; the *set* is
corroborated by the pump `CreateV2` context and the Mayhem parser, not by a labelled
successful invocation. The exact count/order is the one item a harness should confirm by
logging the CPI inner instruction.

### 3.4 Second `mint_to` into `mayhem_token_vault` - [partial]

The deployed Mayhem branch mints to the Mayhem vault in addition to the normal
`associated_bonding_curve` mint. Evidence and constraints:
- `mayhem_token_vault` is a **mut** account in `CreateV2` and is passed to the Mayhem init
  (the Mayhem handler's `mayhem_token_vault` field / `sol_vault` ATA) - it must be funded.
- The only mint authority for the new mint is the pump `mint_authority` PDA; the second
  `mint_to` must therefore run **before** the authority revoke, with the same signer seeds.
- The amount is almost certainly `global.token_total_supply` (the only amount the create
  path mints; the Mayhem state has no separate supply input in the init - no args).
- The exact placement relative to the metadata CPIs and the init CPI is [partial]. The most
  consistent order is:
  1. init mint / bonding_curve / associated_bonding_curve ATA
  2. quote mode checks (MayhemModeQuoteMintNotAllowed / MayhemModeDisabled)
  3. metadata initialize + update_authority
  4. `mint_to` #1 -> `associated_bonding_curve`
  5. `initialize_mayhem_state` CPI (disc-only; accounts per Sec.3.3)
  6. `mint_to` #2 -> `mayhem_token_vault` (same amount)
  7. revoke mint authority
  8. write curve + `CreateEvent{is_mayhem_mode:true, ...}`
  A variant (init CPI before mint #1) is possible; the harness should read the inner
  instruction order.

### 3.5 Mayhem handler effect (what the CPI does) [B/R]
`initialize_mayhem_state` (mayhem `0x101de`/`0xd25f`/`0x10527`): no args; reads a duration
byte, multiplies by 3600 with checked overflow, sets `now`/`now+duration*3600` timestamps,
copies the mint key into `mayhem_state.mint`, zeroes the signed counters/`burned_amount`/
status, and writes the state back via the Anchor exit `0xdabe`. See `mayhem_specs.md` Sec.25
for the full memory-offset analysis and the persistence proof. This is why the pump
`CreateV2` only needs the disc as CPI data.

## 4. End-to-end diagram (labels: [B] exact, [R] source/spec, [~] partial)

```
create_v2(is_mayhem_mode=true)
  [R] gate create_v2_enabled, !cashback, holder/creator, fee
  [~] Mayhem gates: global.mayhem_mode_enabled (MayhemModeDisabled);
      quote restriction (MayhemModeQuoteMintNotAllowed)
  [R] init mint (Token-2022, 6 dec, metadata_pointer=mint)
  [R] init bonding_curve (166) + associated_bonding_curve ATA
  [R] quote selection (Mayhem accepted quote set [~])
  [R] token_metadata_initialize (d2e11ea258b84d8d)
  [R] token_metadata_update_authority (d7e4a6e45464567b)
  [R] mint_to #1: token_total_supply -> associated_bonding_curve
  [~] initialize_mayhem_state CPI:
        data  = 8-byte disc 9dbd5e485545cc2d  [B]
        accts = [payer, global_params, mayhem_state, mint, mayhem_token_vault,
                 sol_vault, bonding_curve, pump_global, pump_program,
                 pump_event_authority, system, token, ata, (event/program?)] [~]
        failure -> CpitializeMayhemFailed [R]
  [~] mint_to #2: token_total_supply -> mayhem_token_vault (before revoke)
  [R] revoke mint authority (MintTokens -> None)
  [R] write curve; emit CreateEvent{is_mayhem_mode:true, quote_mint, ...}
```

## 5. Open items / verification plan

1. **CPI account order/count**: log the inner instruction in a successful
   `is_mayhem_mode=true` create and compare to Sec.3.3; the disc-only payload is already [B].
2. **Second mint_to amount and placement**: confirm `token_total_supply` and whether it is
   before/after the init CPI; the Mayhem state has no supply arg, so the amount must come
   from the pump `Global`/curve, not the CPI.
3. **Mayhem quote restriction**: decode which quote mints are accepted in Mayhem mode (error
   `MayhemModeQuoteMintNotAllowed`); the normal path is general.
4. **Mayhem token vault address**: confirm it is the ATA of `sol_vault` (the Mayhem handler's
   `mayhem_token_vault` field) and that the create body creates/validates it (it is
   unchecked in `CreateV2`).
5. **Exact guard order** of the Mayhem mode/quote checks relative to the normal
   create/cashback/holder checks; spec 04 notes the body is vtable-dispatched, so use the
   inner-instruction/log trace rather than static ordering alone.

No byte-identity is claimed. The recovered `create_v2.rs` is a stub for this branch; the
CPI data is binary-confirmed, while the account order/second-mint placement remain
harness-verifiable [partial].
