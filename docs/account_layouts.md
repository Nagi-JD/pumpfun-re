> **[Claude verification note]** The "BondingCurve discriminator correction (17b7 vs 23b7)"
> below is a FALSE ALARM: the reconstruction's `DISCRIMINATOR = &[23, 183, 248, 55, 96, 216,
> 172, 96]` is a DECIMAL byte array = hex `17 b7 f8 37 60 d8 ac 60` = `17b7f83760d8ac60` — the
> CORRECT deployed discriminator. 23 is decimal (0x17), not hex 0x23. The reconstruction is
> already right; no fix needed. The binary FACTS in this doc (deployed disc = 17b7, 23b7 absent)
> are correct; only the "reconstruction uses 23b7" conclusion was a decimal/hex misread.
> Offsets independently confirmed by harness runs: pump buyback array @741, AMM buyback array @643.

# Account byte-layout maps (harness seeding)

Private analysis for the user. Tags: **[B]** = confirmed in the deployed bytecode/rodata;
**[R]** = taken from the read-only reconstruction (`programs/*/src/*.rs`) or the repo specs;
**[partial]** = inferred (reason stated).

Binary set: `evidence/original/{pump,pump_amm,pump_fees,mayhem}/deployed.so`.
`sbftool` pc units = vaddr/8; addresses are vaddr. All addresses/constants below were checked
against the captured ELFs unless tagged otherwise.

## How to read this

- **Serialized (Borsh) offsets** are what the harness must write into account bytes. Anchor
  `#[account]` accounts are Borsh: fields are tightly packed in **declaration order**, after the
  8-byte discriminator. **No alignment padding** in the serialized form.
- **In-memory offsets** are the Rust struct offsets the deployed code actually loads/stores
  after Anchor deserializes the account. Rust reorders/aligns fields, so these generally
  **differ** from the Borsh offsets (e.g. `pump.Global.authority` is serialized `9` but read at
  `+0x1a0`).
- None of these accounts is zero-copy (`AccountLoader`/`#[repr(C)]`); every one is Borsh
  `Account<T>` or a custom Borsh `AccountDeserialize`. A few handlers additionally read raw
  serialized bytes directly (noted per account).
- For harness fixtures: seed the **serialized** table. Use the in-memory offsets only to map
  disassembly. Where a variable-length `Vec` exists, the length is a **u32** (Borsh), not u64.

---

# 1. pump (`6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P`)

## 1.1 `Global`

- Discriminator **`a7e8e8b1c86c727f`** = `sha256("account:Global")[:8]` **[B]** (rodata
  `0x1b64d7`; the pump binary has no custom override).
- Total size **1088 bytes** = 8 disc + 1080 payload **[B]** (init `space=1088` constants at
  `0x77ab`, `0x1488d`, `0x1593c`, ...; the Borsh sum below is 1088).
- Layout: Borsh `Account<Global>` (declaration order in `programs/pump/src/lib.rs`).

| Serialized off | Field | Type | Notes |
|---:|---|---|---|
| 8 | initialized | bool | |
| 9 | authority | Pubkey | in-memory read/write **+0x1a0** (spec 01: `0x26920`) |
| 41 | fee_recipient | Pubkey | |
| 73 | initial_virtual_token_reserves | u64 | in-memory **+0x450** |
| 81 | initial_virtual_sol_reserves | u64 | in-memory **+0x460** |
| 89 | initial_real_token_reserves | u64 | in-memory **+0x458** |
| 97 | token_total_supply | u64 | in-memory **+0x468** |
| 105 | fee_basis_points | u64 | in-memory **+0x470** |
| 113 | withdraw_authority | Pubkey | in-memory **+0x1b0..0x1cf** |
| 145 | enable_migrate | bool | in-memory **+0x4a2** |
| 146 | pool_migration_fee | u64 | in-memory **+0x478** |
| 154 | creator_fee_basis_points | u64 | in-memory **+0x480** |
| 162 | fee_recipients | [Pubkey; 7] | 224 bytes |
| 386 | set_creator_authority | Pubkey | in-memory **+0x2b0..0x2cf** |
| 418 | admin_set_creator_authority | Pubkey | in-memory **+0x2d0..0x2ef** |
| 450 | create_v2_enabled | bool | in-memory **+0x4a3** (spec 01) |
| 451 | whitelist_pda | Pubkey | |
| 483 | reserved_fee_recipient | Pubkey | |
| 515 | mayhem_mode_enabled | bool | in-memory **+0x4a4** |
| 516 | reserved_fee_recipients | [Pubkey; 7] | 224 bytes |
| 740 | is_cashback_enabled | bool | in-memory **+0x4a5** |
| **741** | **buyback_fee_recipients** | **[Pubkey; 8]** | **256 bytes; the pump-side buyback array (matches the given 741)** |
| 997 | buyback_basis_points | u64 | |
| 1005 | initial_virtual_quote_reserves | u64 | |
| 1013 | whitelisted_quote_mints | [Pubkey; 1] | 32 bytes |
| 1045 | creator_fee_configurable | bool | |
| 1046 | max_configurable_creator_fee_bps | u64 | |
| 1054 | holder_reward_claim_authority | Pubkey | |
| 1086 | is_holder_reward_enabled | bool | |
| 1087 | max_curve_depth | u8 | |

Notes: the in-memory u64 run `0x450..0x480` and the pubkey region `0x1b0..0x4xx` are from
`spec/02-config.md` (set_params execute `0x26cf8`); the three bools at `+0x4a2..0x4a5` are from
`spec/01-admin-config.md`. The serialized table is deterministic Borsh; the **741** array
offset is the pump legacy-buy buyback anchor.

## 1.2 `BondingCurve`

- Discriminator **`17b7f83760d8ac60`** = `sha256("account:BondingCurve")[:8]` **[B]** (rodata
  `0x1b64ef` in pump; the same bytes appear in mayhem at `0xacab8` for the Pump-owned account).
- **Correction:** the reconstruction's custom `23b7f83760d8ac60` is **not present in the
  deployed pump or mayhem ELF** (raw search both programs, both byte orders). Use `17b7...` for
  this capture. The custom constant is likely a later/other revision; do not seed `23b7...`.
- Total size **166 bytes** **[B]** (rent/realloc target 166 at `0x77b0`, `0x1677d`, ...; the
  prepare helper reallocs to 166).
- Layout: Borsh `Account<BondingCurve>`; version-gated prefix decoding (below).

| Serialized off | Field | Type |
|---:|---|---|
| 8 | virtual_token_reserves | u64 |
| 16 | virtual_quote_reserves | u64 |
| 24 | real_token_reserves | u64 |
| 32 | real_quote_reserves | u64 |
| 40 | token_total_supply | u64 |
| 48 | complete | bool |
| 49 | creator | Pubkey |
| 81 | is_mayhem_mode | bool |
| 82 | is_cashback_coin | bool |
| 83 | quote_mint | Pubkey |
| 115 | creator_fee_bps | u64 |
| 123 | can_edit_creator_fee | bool |
| 124 | is_holder_reward | bool |
| 125 | creator_fee | u64 |
| 133 | protocol_fees | u64 |
| 141 | depth | u8 |
| 142 | initial_virtual_quote_reserves | u64 |
| 150 | post_complete_base_out | u64 |
| 158 | post_complete_quote_in | u64 |

- Raw serialized reads are used in places: `multi_hop_curve_swap` checks `d[48] != 0`
  (complete) **[B]** (`spec/07-route-migrate.md`), i.e. the **serialized** offset, not the
  in-memory struct. Other handlers use the Borsh `Account<BondingCurve>`.
- Version gates (payload lengths after the disc): 41 (base), 73 (+creator), 74
  (+is_mayhem_mode), 75 (+is_cashback_coin), 107 (+quote_mint), 116 (+creator_fee_bps,
  can_edit_creator_fee), 117 (+is_holder_reward), 133 (+creator_fee, protocol_fees), 158
  (+depth, initial_virtual_quote_reserves, post_complete_*) **[R]** (`trade_types.rs`).
- Consumer notes: Mayhem's external copy is an **82-byte prefix** (disc + 74 payload: through
  `is_mayhem_mode`), see Sec.4.3; the AMM reconstruction's `23b7...`/83-byte view does not match
  this capture (the deployed AMM ELF contains neither discriminator) **[B absence]**.

## 1.3 `UserVolumeAccumulator` (pump)

- Discriminator **`56ff700e66359afa`** = `sha256("account:UserVolumeAccumulator")[:8]` **[B]**
  (rodata `0x1b64af`; the AMM uses the same discriminator).
- Total Borsh size **106 bytes**; init `space=137` (31 bytes slack) **[B]** (`137` constants at
  `0x77ba`, `0x1541d`, ...; size 106 at `0xc2ee`).
- Serialized table **[B/R]** (`spec/11-volacc-idl.md`):

| Off | Field | Type |
|---:|---|---|
| 8 | user | Pubkey |
| 40 | needs_claim | bool |
| 41 | total_unclaimed_tokens | u64 |
| 49 | total_claimed_tokens | u64 |
| 57 | current_sol_volume | u64 |
| 65 | last_update_timestamp | i64 |
| 73 | has_total_claimed_tokens | bool |
| 74 | cashback_earned | u64 |
| 82 | total_cashback_claimed | u64 |
| 90 | stable_cashback_earned | u64 |
| 98 | total_stable_cashback_claimed | u64 |

- In-memory offsets (disassembly; **not** serialized): `cashback_earned` +0x58,
  `total_cashback_claimed` +0x60 (`0xee59/0xee5a`), `total_claimed_tokens` +0x250,
  `last_update_timestamp` +0x260, `has_total_claimed_tokens` +0x289 (`0xf658..0xf659`,
  `spec/11-volacc-idl.md`).
- The AMM's same-named account is only 90 bytes (no stable fields); do not cross-seed.

## 1.4 `GlobalVolumeAccumulator`

- Discriminator **`ca2af62b8ebe1eff`** = `sha256("account:GlobalVolumeAccumulator")[:8]` **[B]**
  (rodata `0x1b64c7`).
- Total **544 bytes** **[B]** (`544` constants at `0x703/0x70b/0x1e5e4`).
- Serialized table:

| Off | Field | Type |
|---:|---|---|
| 8 | start_time | i64 |
| 16 | end_time | i64 |
| 24 | seconds_in_a_day | i64 |
| 32 | mint | Pubkey |
| 64 | total_token_supply | [u64; 30] (240 B) |
| 304 | sol_volumes | [u64; 30] (240 B) |

- In-memory offsets (spec 10): `start_time` +0x00, `end_time` +0x08, `seconds_in_a_day`
  +0x10, `mint` +0x18 (memcmp at `0x1e63b`), `total_token_supply` +0x38, `sol_volumes`
  +0x128. Again: seed the serialized table, not these.

## 1.5 `QuoteControl`

- Discriminator **`38f423eec1d5a2c9`** = `sha256("account:QuoteControl")[:8]` **[B]** (rodata
  `0x1b64b7`).
- Init size **2108 bytes** (`space = 8 + QuoteControl::INIT_SPACE`, max_len 50) **[B]**
  (2108 constants at `0x1be66`, `0x1c0a6`, ...); live size = **108 + 40*n** where `n` is the
  number of listed mints (`space(n)` in `quote_control/state.rs`) **[R]**.
- Layout: Borsh `Account<QuoteControl>`.

| Off | Field | Type | Notes |
|---:|---|---|---|
| 8 | admin | Pubkey | in-memory +0x18 (spec 03) |
| 40 | reserves_admin | Pubkey | in-memory +0x38 (spec 03) |
| 72 | _reserved | [u8; 32] | |
| 104 | mints (Vec len) | u32 | Borsh length, 4 bytes |
| 108 + 40*i | mints[i] | {mint: Pubkey, initial_virtual_quote_reserves: u64} | 40 bytes/entry |

- The account is reallocated as mints are added, up to 256 entries; a fixture with `n` entries
  is `108 + 40*n` bytes (the init account is the 2108-byte max_len form). **[R/B]**

---

# 2. pump_amm (PumpSwap, `pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA`)

## 2.1 `GlobalConfig`

- Discriminator **`95089ccaa0fcb0d9`** (custom, `state.rs`) **[B]** (rodata `0x11c62e`).
- Total **949 bytes**; decoders accept legacy **907 / 940 / 949** **[R]** (the AMM source's
  length switch; 949 constants at `0x3ce9/0x3cf4/0x5d74/0x104d1`, ...).
- Layout: Borsh `Account<GlobalConfig>`; the program stores/reads the in-memory struct.

| Off | Field | Type | Notes |
|---:|---|---|---|
| 8 | admin | Pubkey | `has_one` in admin handlers |
| 40 | lp_fee_basis_points | u64 | update_fee_config store |
| 48 | protocol_fee_basis_points | u64 | |
| 56 | disable_flags | u8 | bit0 create, 1 deposit, 2 withdraw, 3 buy, 4 sell |
| 57 | protocol_fee_recipients | [Pubkey; 8] | 256 B; sorted/unique/non-zero enforced |
| 313 | coin_creator_fee_basis_points | u64 | |
| 321 | admin_set_coin_creator_authority | Pubkey | |
| 353 | whitelist_pda | Pubkey | |
| 385 | reserved_fee_recipient | Pubkey | |
| 417 | mayhem_mode_enabled | bool | |
| 418 | reserved_fee_recipients | [Pubkey; 7] | 224 B |
| 642 | is_cashback_enabled | bool | |
| **643** | **buyback_fee_recipients** | **[Pubkey; 8]** | **256 B; the buy/sell buyback array** |
| **899** | **buyback_basis_points** | **u64** | gates the payout, not the account requirement |
| 907 | boost_authority | Pubkey | |
| 939 | boost_enabled | bool | |
| 940 | creator_fee_configurable | bool | |
| 941 | max_configurable_creator_fee_bps | u64 | (941..949) |

- In-memory evidence for the buyback array **[B]**: the validator at `0xc5cd` compares the
  buyback owner against **8 pubkeys at `r9+0x100, +0x120, ..., +0x1e0`** (stride 0x20,
  256 bytes; sites `0xc5de..0xc620`), with 6053 error stores at `0xc670/0xc6ae/0xc6e2`. The
  serialized start 643 is **[R]** from the declaration order, corroborated by the legacy
  **907 = 899 + 8** boundary (the 907-byte layout ends exactly after buyback_basis_points).
- The 31/38-name IDLs do not list the buyback fields; an IDL-generated account places them
  elsewhere. Seed at 643/899.

## 2.2 `Pool`

- Discriminator **`f19a6d0411b16dbc`** (custom) **[B]** (rodata `0x11c60e`).
- Total **287 bytes**; legacy prefixes accepted: 211, 243, 244, 245, 261, 270, 271, 287
  (`state.rs` decoder; 287 constants at `0xb086/0x13c80/...`) **[R/B for 287]**.
- Layout: Borsh `Account<Pool>`.

| Off | Field | Type |
|---:|---|---|
| 8 | pool_bump | u8 |
| 9 | index | u16 |
| 11 | creator | Pubkey |
| 43 | base_mint | Pubkey |
| 75 | quote_mint | Pubkey |
| 107 | lp_mint | Pubkey |
| 139 | pool_base_token_account | Pubkey |
| 171 | pool_quote_token_account | Pubkey |
| 203 | lp_supply | u64 |
| 211 | coin_creator | Pubkey |
| 243 | is_mayhem_mode | bool |
| 244 | is_cashback_coin | bool |
| 245 | virtual_quote_reserves | i128 (16 B) |
| 261 | creator_fee_bps | u64 |
| 269 | can_edit_creator_fee | bool |
| 270 | is_holder_reward | bool |
| 271 | protocol_fees | u64 |
| 279 | creator_fees | u64 |

- The decoder zero-pads a short account up to 287 and accepts the legacy prefixes above; the
  trade handlers read the in-memory struct (field offsets differ; not needed for seeding).

## 2.3 `UserVolumeAccumulator` (AMM)

- Discriminator **`56ff700e66359afa`** (same name/hash as pump) **[B]** (rodata `0x11c5fe`).
- Borsh size **90 bytes**; init `space=137` **[B]** (137 constants at `0x15ebc`; 90 at `0x1c312`).
- Serialized table:

| Off | Field | Type |
|---:|---|---|
| 8 | user | Pubkey |
| 40 | needs_claim | bool |
| 41 | total_unclaimed_tokens | u64 |
| 49 | total_claimed_tokens | u64 |
| 57 | current_sol_volume | u64 |
| 65 | last_update_timestamp | i64 |
| 73 | has_total_claimed_tokens | bool |
| 74 | cashback_earned | u64 |
| 82 | total_cashback_claimed | u64 |

- No `stable_cashback_*` fields on the AMM. The pump version is 106 bytes; use the per-program
  payload.

## 2.4 `FeeConfig` consumption (AMM side)

The AMM does not own `fee_config`; it reads the **fees program** account
`["fee_config", pump_amm]` owned by `pfeeUx...` (disc `8f3492bbdb7b4c9b`). See Sec.3.1 for the
layout. AMM-side checks **[R]**: `data_len() >= 2512` (`FeeConfigTooShort`, 6083) and legacy
trimming (`<4073` clear stable tiers, `<4097` zero exotic) at `trade.rs::TradeFeeConfig`.

---

# 3. pump_fees (`pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ`)

## 3.1 `FeeConfig`

- Discriminator **`8f3492bbdb7b4c9b`** (custom) **[B]** (rodata `0xc3db7`).
- Size: **2512** at init (`InitializeFeeConfig space=2512` **[B]**, constants at `0x9385`);
  **grows to 4097** (`ExtendFeeConfig` **[B]**, 4097 constants at `0x273f`). Decoder floors:
  `<2512` reject; `<4073` no stable tiers; `<4097` no exotic fees **[R]** (the 2512/4097
  constants are in the fees ELF; 4073 is the source boundary).
- Layout: Borsh `Account<FeeConfig>` with variable `Vec`s.

| Off | Field | Type | Notes |
|---:|---|---|---|
| 8 | bump | u8 | PDA bump (`fee_config` seeds) |
| 9 | admin | Pubkey | `has_one` in update handlers |
| 41 | flat_fees | Fees = 3 x u64 (24 B) | lp, protocol, creator bps |
| 65 | fee_tiers len | u32 | Borsh Vec length |
| 69 + 40*i | fee_tiers[i] | FeeTier = u128 threshold + Fees (16 + 24 = 40 B) | |
| 69 + 40*n | stable_fee_tiers len | u32 | present if len >= 4073 |
| 73 + 40*n + 40*j | stable_fee_tiers[j] | FeeTier (40 B) | |
| 73 + 40*(n+m) | exotic_flat_fees | Fees (24 B) | present if len >= 4097 |

- `Fees` order is `lp_fee_bps, protocol_fee_bps, creator_fee_bps` (each u64) **[R]**.
- The AMM consumes this account; it selects a tier by market-cap and uses the flat/exotic
  fallbacks (see `amm_specs.md` Sec.11/Sec.14).

## 3.2 `SharingConfig`

- Discriminator **`d84a0900388c5d4b`** = `sha256("account:SharingConfig")[:8]` **[B]** (rodata
  `0xc3ddf`; the same bytes appear in the AMM's `creator_reassignment.rs`).
- Init `space=1024` **[B]** (1024 constants at `0xdf0a`, ...). Live size = **80 + 34*n**
  (shareholders) **[R]**.
- Layout: Borsh `Account<SharingConfig>` (fees program).

| Off | Field | Type | Notes |
|---:|---|---|---|
| 8 | bump | u8 | |
| 9 | version | u8 | create sets 2 when active |
| 10 | status | enum (1 B) | 0 Paused, 1 Active |
| 11 | mint | Pubkey | AMM migrate constraint: == pool.base_mint |
| 43 | admin | Pubkey | AMM migrate constraint: == pool.coin_creator |
| 75 | admin_revoked | bool | |
| 76 | shareholders len | u32 | |
| 80 + 34*i | shareholders[i] | {address: Pubkey, share_bps: u16} | 34 B/entry |

## 3.3 Other fees state (discriminators verified **[B]**)

| Account | Discriminator | Size / layout |
|---|---|---|
| `FeeProgramGlobal` | `a2a5f5311d2537f2` | 338 B: bump 8, authority 9, disable_flags 41, social_claim_authority 42, claim_rate_limit 74, _reserved[256] 82..338 |
| `BuybackVault` | `99a64790b3bd89fb` | 208 B: authority 8, total_claimed 40, total_claimed_token1 48, total_claimed_token2 56, last_claimed 64, claim_rate_limit 72, _reserved[128] 80..208 |
| `DonationFeePda` | `f6c56009c11e5d73` | 218 B: bump 8, version 9, config_id 10, base_mint 42, quote_mint 74, creator 106, total_donated 138, last_crank_ts 146, reserved[64] 154..218 |
| `SocialFeePda` | `8b6035112aa9ce96` | variable: bump 8, version 9, user_id **Borsh String** at 10 (u32 len + bytes), then platform, total_claimed, last_claimed, total_stable_claimed, _reserved[120]; do not hardcode post-string offsets |

(All four discriminator bytes were found in the fees ELF at `0xc3d6f`..`0xc3de7`; sizes are
from the source `state.rs` and the init `space` constants where present. The SocialFeePda
String makes its fixed tail offset-dependent - parse it, do not assume 14.)

---

# 4. mayhem (`MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e`)

## 4.1 `GlobalParams`

- Discriminator **`79c1f857c3384c0b`** = `sha256("account:GlobalParams")[:8]` **[B]** (rodata
  `0xaca70`).
- Total **254 bytes** **[B]** (254 constants at `0x6228/0x636a/...`; `initialize_global_params`
  creates `space=254`).
- Layout: Borsh `Account<GlobalParams>`; the handlers read the in-memory struct.

| Serialized off | Field | Type | In-memory off (where known) |
|---:|---|---|---|
| 8 | reset_prefix | [u8; 40] | field_0 @0xe8, field_1 @0xec, field_3 @0x68 (crosswalk) |
| 48 | paused | bool | |
| 49 | admin | Pubkey | |
| 81 | trader | Pubkey | |
| 113 | sol_deployed | i128 | |
| 129 | preserved_middle_a | [u8; 8] | field_9 (min SOL reserves); in-memory not pinned |
| 137 | reset_middle | [u8; 25] | field_6 @0xf4; field_8 @0x98 |
| 162 | version | u32 | |
| 166 | field_10 | u64 | @0xa0 |
| 174 | max_sol_per_sweep | u64 | |
| 182 | reset_stable_prefix | [u8; 24] | |
| 206 | stable_deployed | i128 | |
| 222 | reset_stable_suffix | [u8; 24] | field_15 @0xd0 |
| 246 | max_stable_per_sweep | u64 | |

- In-memory offsets are from the repo's field-role crosswalk (serialized vs memory explicitly
  distinguished there); the serialized table is what the harness seeds.
- Withdrawal clocks **[R/B crosswalk]**: SOL last-timestamp = serialized 138..146 (memory
  0x88), interval = field_8 154..162 (memory 0x98); quote last = 238..246 (memory 0xd8),
  interval = field_15 230..238 (memory 0xd0).

## 4.2 `MayhemState` (`mayhem_state`, `["mayhem-state", mint]`)

- Discriminator **`b1fdbf7dcb16866b`** = `sha256("account:MayhemState")[:8]` **[B]** (rodata
  `0xacaa8`; it is also the literal `[0xb1,0xfd,0xbf,0x7d,0xcb,0x16,0x86,0x6b]` checked by
  mayhem `extend_account`).
- Total **106 bytes** **[B]** (106 constants at `0xd8af/0xd93b/...`); `extend_account` target
  170 (over-allocation) **[B]** (170 constant at `0x1e00`).
- Layout: Borsh `Account<MayhemState>` (state names are neutral where historical semantics
  are unproven).

| Serialized off | Field | Type | In-memory off (where known) |
|---:|---|---|---|
| 8 | field_8 | u64 | |
| 16 | end_timestamp | i64 | **0x1a8** (burn reads; initialize writes now+duration) |
| 24 | mint | Pubkey | **0x160..0x180** (initialize copy) |
| 56 | field_56 | i128 | net quote deployment (trades) |
| 72 | field_72 | i128 | net base-token accounting (trades) |
| 88 | flag_88 | bool | |
| 89 | field_89 | u64 | last-trade timestamp; initialize writes now at **0x1b0** [partial] |
| 97 | status | u8 (0/1/2) | **0x1c0** (initialize zeroes a u16) [B/partial] |
| 98 | burned_amount | u64 | **0x1b8** (burn stores; initialize zeroes) |

- Key warning: the serialized `end_timestamp` is **16** and `burned_amount` is **98**, while
  the deployed code reads/writes memory **0x1a8/0x1b8**. Seed 16/98; do not seed 0x1a8/0x1b8.
- The Borsh decoder accepts only bool 0/1 for `flag_88` and status 0/1/2 (state.rs comments;
  derive/differential receipts) **[R]**.

## 4.3 External Pump `BondingCurve` (mayhem consumer)

- Mayhem reads the Pump-owned bonding curve via a **82-byte** codec (disc + 74 payload) with
  the Pump discriminator **`17b7f83760d8ac60`** **[B]** (the same bytes at mayhem rodata
  `0xacab8`; mayhem's `state.rs` says the codec at `0x6dc00` writes 82 bytes including the
  discriminator). Its fields are the 82-byte prefix of Sec.1.2: virtual_token_reserves 8,
  virtual_sol_reserves 16, real_token_reserves 24, real_sol_reserves 32, token_total_supply
  40, complete 48, creator 49..81, is_mayhem_mode 81. Do not seed a 166-byte pump curve for a
  mayhem fixture if the account is only 82 bytes; seed the full pump curve when the harness
  uses the real Pump account.

---

## Harness checklist (quick)

1. **Discriminators**: pump Global `a7e8e8b1c86c727f`, BondingCurve **`17b7f83760d8ac60`**
   (not `23b7...`), UserVolumeAccumulator `56ff700e66359afa`, GlobalVolumeAccumulator
   `ca2af62b8ebe1eff`, QuoteControl `38f423eec1d5a2c9`; AMM GlobalConfig
   `95089ccaa0fcb0d9`, Pool `f19a6d0411b16dbc`, UserVolumeAccumulator
   `56ff700e66359afa`; fees FeeConfig `8f3492bbdb7b4c9b`, SharingConfig
   `d84a0900388c5d4b`, FeeProgramGlobal `a2a5f5311d2537f2`; mayhem GlobalParams
   `79c1f857c3384c0b`, MayhemState `b1fdbf7dcb16866b`.
2. **Buyback arrays**: pump Global at **741..997** (8 keys, 256 B), basis points 997..1005;
   AMM GlobalConfig at **643..899** (8 keys, 256 B), basis points 899..907. The AMM array is
   validated by the 8-key loop at `0xc5cd` (6053 on mismatch); the 6058/6056 site is the
   remaining-account requirement (see `amm_buyback_gate.md`).
3. **Sizes**: pump Global 1088, BondingCurve 166, UserVolumeAccumulator 137 init/106 used,
   GlobalVolumeAccumulator 544, QuoteControl 2108 init (108+40n live); AMM GlobalConfig 949
   (907/940 legacy), Pool 287, UserVolumeAccumulator 137 init/90 used; fees FeeConfig 2512
   init -> 4097 extended, SharingConfig 1024 init (80+34n), FeeProgramGlobal 338; mayhem
   GlobalParams 254, MayhemState 106 (extend target 170).
4. **Never** confuse serialized offsets with the in-memory offsets cited in the specs; the
   former are tightly packed Borsh (seed these), the latter are the disassembly offsets.
5. No zero-copy accounts in this set; all are Borsh. Raw serialized reads exist (e.g. pump
   BondingCurve `d[48]`, fees `data[8]` bump / `data[..8]` disc), so keep the serialized bytes
   consistent even when a handler uses the deserialized struct.
