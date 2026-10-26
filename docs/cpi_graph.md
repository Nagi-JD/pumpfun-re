# Inter-program CPI graph (deployed programs)

Private analysis for the user. Tags: **[B]** = call edge/disc/account set confirmed in the
deployed bytecode; **[R]** = from the reconstruction / cluster specs; **[partial]** = inferred
(reason stated). No exhaustive all-input claim.

Program ids: pump `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P`, PumpSwap
`pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA`, fees
`pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ`, mayhem
`MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e`, Tokenkeg
`TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA`, Token-2022
`TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb`, ATA
`ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL`, Metaplex
`metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s`, system
`11111111111111111111111111111111`, relay `RLAYHr9TRFcKB2ubYQhspcnXiaGpaVzNQvHytt47RZu`.

Disc values below are the 8-byte instruction discriminators (byte order as in the hex tables);
for SPL Token the "disc" is the **1-byte instruction tag** (`transfer_checked`=12,
`mint_to`=7, `burn`=8, `close_account`=9, `sync_native`=17, ATA create idempotent=1, ATA
create=0), not an Anchor hash.

---

## 1. pump -> fees `get_fees_with_quote_mint` (trade fee query)

| caller (handler) | edge |
|---|---|
| `buy` `0x2549c`, `buy_exact_sol_in` `0x25579`, `buy_v2` `0x24ea2`, `buy_exact_quote_in_v2` `0x24f6b`, `buy_v3` `0x250d9`, `buy_exact_quote_in_v3` `0x25185`, `sell` `0x25656`, `sell_v2` `0x25034`, `sell_v3` `0x25231` [R/B spec 05/06] | `invoke` fees `get_fees_with_quote_mint` **`9aed8a5ca202a2bb`** |

- Data [R]: `is_pump_pool: bool` (1) + `market_cap_lamports: u128` (16) + `quote_mint: Pubkey`
  (32); the pump trade data prefix is `154,237,138,92,162,2,162,187,1` + cap + quote_mint.
- Accounts [R]: `[fee_config (fees-owned, ["fee_config", pump]), pump program id]`.
- Return: `get_return_data` -> `Fees {lp_fee_bps, protocol_fee_bps, creator_fee_bps}` (24 B).
- Signer: none (the fee_config PDA is passed read-only; the pump id account is the
  `program` account of the caller).
- Note: the AMM's legacy buy/sell use the **same** instruction (`9aed...`), with the AMM id
  as the config namespace (see Sec.5).

## 2. pump -> mayhem `initialize_mayhem_state` (create_v2 Mayhem mode)

| caller | edge |
|---|---|
| `create_v2` `0x24d15` (is_mayhem_mode=true) [R/B] | `invoke`/`invoke_signed` mayhem `initialize_mayhem_state` **`9dbd5e485545cc2d`** |

- Data [B]: exactly the 8-byte disc, no args (pump builder `0x23181`, data len 8; account-meta
  serializer `0x2316a`, caller `0x116fc`).
- Accounts [partial]: `[payer/signer, global_params, mayhem_state, mint, mayhem_token_vault,
  sol_vault, bonding_curve, pump_global, pump_program, pump_event_authority, system_program,
  token_program, associated_token_program, (mayhem event?)]` - order inferred from the mayhem
  parser + `CreateV2` hard-wires; see `create_v2_mayhem.md` Sec.3.3.
- Signer: the pump `user` (outer signer) for the Mayhem payer; the Mayhem PDA seeds are
  `["global-params"]`, `["sol-vault"]`, `["mayhem-state", mint]`.
- Failure -> pump `CpitializeMayhemFailed` (name from source; the pump error code is
  revision-ambiguous).
- The second `mint_to` into `mayhem_token_vault` is a Token-2022 CPI, not this edge [partial].

## 3. pump -> pump_amm (migration)

| caller | edge | disc |
|---|---|---|
| `migrate` `0x256fb` / `migrate_v2` `0x25749` [B spec 07] | AMM `create_pool` | **`e992d18ecf6840bc`** (`233,146,209,142,207,104,64,188`) |
| same, non-mayhem | AMM `init_boost` (the "buyback/boost" call) | **`8ce9215e845ac28f`** (`140,233,33,94,132,90,194,143`) |
| `migrate`/`migrate_v2` | Token-2022 / Token transfers, ATA creates, close, mint/burn, sync_native | 1-byte SPL tags |

- `create_pool` accounts [R]: the 18-account AMM create set (pool, global_config, creator,
  base/quote mints, lp_mint, user/pool ATAs, system/token_2022/base/quote/ATA programs).
- `init_boost` accounts [R]: pool, global_config, creator, base/quote mints, pool base/quote
  ATAs, boost_vault_authority, boost_vault, quote_token_program, system, ATA program.
- Signer: the **pool_authority** PDA (`["pool-authority", mint]` under pump/AMM) for the
  curve-signed seeding; the AMM create is invoked with the pump-derived signer.
- `migrate_v2` additionally harvests Token-2022 withheld fees (`op 26,4`) and checks the quote
  mint writable (`QuoteMintNotWritable` 110) [B spec 07].

## 4. pump -> pump_fees (sharing / admin)

| caller | edge | disc |
|---|---|---|
| `create_v2`/`admin_cto`/creator paths [R] | fees `create_fee_sharing_config` / admin reset | see fees rows |
| `admin_cto` `0x25b40` [R spec 08] | fees `admin_cto_sharing_config` (reset) | **`3c64909c408ab625`** (`60,100,144,156,64,138,182,37`) |
| `migrate_bonding_curve_creator` | - | no CPI |

- The pump `create_fee_sharing_config` path is actually called **from the fees program**
  (`create_fee_sharing_config` invokes pump), not pump -> fees. The pump -> fees edge in the
  creator cluster is the AMM/fees admin reset from `admin_cto` (fees program id) [R spec 08].
- Signer: the sharing-config/Pump authority as required by the fees context; the pump
  `admin_cto` passes the caller authority.

## 5. pump_amm -> fees `get_fees_with_quote_mint` / local config

| caller | edge |
|---|---|
| AMM legacy `buy` `0x1cec9`, `sell` `0x1d099` [R] | `invoke` fees `get_fees_with_quote_mint` **`9aed8a5ca202a2bb`**, accounts `[fee_config, pump_amm]`, data `is_pump_pool` (canonical flag) + cap + quote mint; return `TradeFees` |
| AMM `buy_v2`/`sell_v2`/`buy_exact_quote_in_v2`/`multi_hop_swap` [R] | **no fee CPI**; reads the fees-owned `fee_config` account locally (`fee_config.len() >= 2512`) |

- The AMM's legacy trade CPI is the only AMM -> fees value CPI; the V2/multi-hop paths read the
  same account in-process.
- Signer: none for the query.

## 6. pump_amm -> pump `multi_hop_curve_swap`

| caller | edge | disc |
|---|---|---|
| `multi_hop_swap` `0x1d2ec` (Pump-owned hop group) [B/R] | `invoke_signed` pump `multi_hop_curve_swap` | **`e19a7516d756f667`** (`225,154,117,22,215,86,246,103`) |

- Data [B]: `amount_in: u64` + `flags.len(): u32` + `flags[]` (2-bit per hop: bit0 protocol,
  bit1 creator).
- Accounts [B/R]: `[pump_global, pump_fee_config, global_config (signer), user, authority,
  source, destination, buyback_fee_recipient, token_program, token_2022_program, system,
  pump_event_authority, pump_program]` + the 5 accounts per curve hop.
- Signers: AMM `global_config` PDA (`["global_config", bump]`) and the source-owner seeds when
  selling from a pool.
- Return: `get_return_data` must be the pump program with 16 bytes (`amount_out`, `buyback`);
  `MultiHopCurveRunMismatch` otherwise.

## 7. pump_amm -> token / ATA (all trade/liquidity handlers)

| caller | edge |
|---|---|
| `buy`/`sell`/`buy_v2`/`sell_v2`/`buy_exact_quote_in_v2`/`create_pool`/`deposit`/`withdraw`/`collect_coin_creator_fee`/`sweep_*`/`transfer_creator_*`/`boost_burn` [R] | `token_interface::transfer_checked` (tag 12), `mint_to` (7), `burn` (8), `close_account` (9), `sync_native` (17) on Tokenkeg/Token-2022; ATA create/idempotent (tag 0/1) on the ATA program |

- Signers: the pool PDA (`["pool", index, creator, base, quote, bump]`) for pool-vault legs;
  the user for user legs; the coin-creator-vault PDA (`["creator_vault", coin_creator]`) for
  creator sweeps; the boost-vault PDA (`["boost_vault", pool]`) for boost flows.
- `create_pool` mints LP on Token-2022 with the pool PDA signer; `deposit`/`withdraw` use
  Token-2022 mint/burn; `buy_pump_swap`/`sell_pump_swap` use the PumpSwap CPI instead (below).

## 8. pump_amm -> pump_amm (self) and PumpSwap

- `multi_hop_swap` re-parses `AmmHop` groups; no self-CPI.
- `buy_pump_swap`/`sell_pump_swap` (AMM handlers) `invoke_signed` **PumpSwap** (`pAMM...`) buy
  `66063d1201daebea` / sell `33e685a4017f83ad`, signed by the `sol-vault` PDA
  (`["sol-vault", bump]`), 25/23 accounts (per `amm_specs.md`).
- `create_pool`/`deposit`/`withdraw` do not self-CPI.

## 9. pump_fees -> pump / pump_amm

| caller | edge | disc |
|---|---|---|
| `create_fee_sharing_config` `0x13810` [R] | Pump `extend_account` | **`ea66c2cb96483ee5`** |
| same | Pump `migrate_bonding_curve_creator` | **`577c34bf3426d6e8`** |
| same, graduated | AMM `extend_account` | **`ea66c2cb96483ee5`** |
| same, graduated | AMM `migrate_pool_coin_creator` | **`d0089f044aaf103a`** |
| `update_fee_shares` `0x138d4` [R] | AMM `transfer_creator_fees_to_pump` | **`8b348655e4e56cf1`** |
| same | Pump `distribute_creator_fees` | **`a572670079cef751`** |
| `update_fee_shares_v2` `0x1395a` [R] | AMM `transfer_creator_fees_to_pump_v2` | **`01214eb921432c5c`** |
| same | Pump `distribute_creator_fees_v2` | **`ffcb134ff444089f`** |

- Signers: the fees program's sharing-config/admin authority as required; the pump/AMM CPIs
  are ordinary `invoke` from the fees program (the target PDAs are passed in the fees
  instruction's account list). `create_fee_sharing_config` passes the pump/AMM event
  authorities and programs.
- `admin_cto_sharing_config` itself does not CPI (it is the fees-side reset).

## 10. pump_fees -> relay / Token (donation, social, buyback, withdraw)

| caller | edge |
|---|---|
| `crank_donation_fee_pda` `0x140b8` [R] | `invoke_signed` relay `RLAYHr...` disc **`78d939f187688bb8`**, 13 accounts (epoch/debouncer/ATA/quote/quote-ATA/donation/payer/mint-whitelist/ATA/token/system/relay-event/relay-program), signer = donation-fee PDA (`["donation-fee-pda", base, config]`); native WSOL also Tokenkeg `sync_native` (17) |
| `claim_social_fee_pda` `0x13b5d` / `_v2` `0x13c64` [R] | system lamport move (native) or Token `transfer_checked` (tag 12) signed by `["social-fee-pda", user_id, platform]`; v2 ATA creates |
| `sweep_buyback` `0x13e01` [R] | Token `transfer_checked` from `["buyback-vault", index]` ATA; lamport move |
| `withdraw` `0x14121` [R] | Token `transfer_checked` signed by `["referral-vault", user]` or system transfer |
| `create_social_fee_pda` / `initialize_buyback` / `initialize_fee_config` / `initialize_fee_program_global` [R] | System `create_account`/ATA create (Anchor init) |

## 11. mayhem -> pump / PumpSwap / Token

| caller | edge | disc |
|---|---|---|
| `buy` `0x1027f` (18-account) / `buy_v2` `0x1034f` (27) [R] | Pump buy | **`66063d1201daebea`** |
| `sell` `0x10217` (16) / `sell_v2` `0x102e7` (26) [R] | Pump sell | **`33e685a4017f83ad`** |
| `buy_pump_swap` `0x1041f` (25) [R] | PumpSwap buy | **`66063d1201daebea`** |
| `sell_pump_swap` `0x103b7` (23) [R] | PumpSwap sell | **`33e685a4017f83ad`** |
| all trade paths [R] | Token/Token-2022 transfers, ATA create | SPL tags 12/0/1/17/9 |
| `burn_tokens` `0xffe1` [R] | Token-2022 burn | tag 8 |
| `sweep_fees`/`sweep_fees_admin` `0xfc96`/`0xfcd3` [R] | Token transfer from `["fee-recipient", index]` ATAs | tag 12 |
| `withdraw_admin` `0xfd90` / `withdraw_quote_admin` `0xfde2` [R] | system transfer from `["sol-vault"]` / Token transfer from vault ATA | system / tag 12 |
| `initialize_mayhem_state` `0x101de` [R] | System `create_account` for `["mayhem-state", mint]` | system |
| all handlers with `#[event_cpi]` [R] | self-CPI event | tag **`e445a52e51cb9a1d`** |

- The Pump/PumpSwap trade CPIs are signed by the Mayhem `sol-vault` PDA
  (`["sol-vault", bump]`); the outer trader is the configured trader signer. The account lists
  are in `mayhem_specs.md` (18/16/27/26/25/23).
- `initialize_mayhem_state`'s CPI account order is [partial] (see `create_v2_mayhem.md`).

## 12. Self-CPI event tag

All four programs use the Anchor `emit_cpi!` receive tag **`e445a52e51cb9a1d`**:
- mayhem dispatcher pseudo-entry `0x10487` (event authority check + event dispatch);
- AMM `emit_event` (tag + event.data, invoked to the AMM event authority);
- pump and fees handlers with `#[event_cpi]` (the event authority/program accounts in their
  contexts).
This tag is **not** an instruction/event/account discriminator; it is the receive-side marker.

---

## Notes

- The `spec/08` CPI labels for `admin_cto` are misleading: the four discs it lists are
  `01214eb921432c5c` (AMM `transfer_creator_fees_to_pump_v2`), `a039592ab58b2b42` (AMM
  `collect_coin_creator_fee`), `3c64909c408ab625` (fees `admin_cto_sharing_config`), and
  `2d3da597680031bd` (AMM `admin_cto_pool`), not "collect/set/update" as labelled. Use the
  names above.
- The pump trade -> fees query is `get_fees_with_quote_mint` (`9aed...`), not `get_fees`
  (`e725...`). The AMM legacy trade uses the same `9aed...` edge.
- `migrate`/`migrate_v2` are the only pump -> AMM edges; the AMM -> pump edge is the
  `multi_hop_swap` curve batch. No pump -> AMM trade CPI is part of a normal pump buy/sell.
- Return-data users: pump/AMM trade fee queries (24-byte `Fees`/`TradeFees`) and the AMM
  multi-hop curve batch (16-byte `(amount_out, buyback)`).
