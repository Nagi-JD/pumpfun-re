# CPI instruction-data frames (pump, pump_amm, pump_fees, mayhem)

Every Anchor-discriminated CPI emitted by the four deployed programs, read from the
instruction data the caller writes: the 8-byte discriminator as one `lddw` immediate,
the argument stores that follow it into the same buffer, the payload length those stores
imply, the declared frame of the target instruction from its IDL, and the handler that
reaches the builder. Addresses are `sbftool` pc units (`byte = pc * 8`); ELFs are
`evidence/original/<program>/deployed.so`.

**23 CPI edges**, 15 with a fixed-size declared frame reproduced
byte for byte, 6 with `Option`/`String` arguments, 1 carrying only the
discriminator, 1 whose arguments are appended by the Borsh serializer the
builder hands the buffer to.

## Method

1. The discriminator is `sha256("global:" + name)[:8]`, loaded as one `lddw` immediate and
   stored into the freshly allocated instruction-data buffer. Every such immediate whose
   enclosing function is not the program dispatcher is a CPI payload builder.
2. The buffer base register is the register the discriminator is stored through; the
   payload frame is the set of stores into that register with a constant offset, scanned
   outwards until the register is redefined (LLVM interleaves the argument stores with
   the discriminator store, so the scan runs both ways from it).
3. The declared frame is built from the target program IDL: arguments in declaration
   order after the 8-byte discriminator, `u128`/`pubkey` as 16/32 bytes, `Option` as a
   1-byte tag plus payload.
4. Handler attribution: dispatcher `lddw` -> `jeq`/`jne` on the discriminator -> stub ->
   first internal call or `ja` within 40 instructions, then a forward call-graph walk from
   the handler entry to the builder (depth reported as `+n`).

## Per-program census

| program | dispatcher | invoke wrapper | wrapper insns | AccountMeta repack | CPI edges |
|---|---|---|---|---|---|
| pump | `0x236eb` | `0x343ae` | 121 | `0x343c0`, `0x3441a` | 8 |
| pump_amm | `0x1b793` | `0x2104c` | 121 | `0x2105e`, `0x210b8` | 2 |
| pump_fees | `0x1240e` | `0x164a3` | 121 | `0x164b5`, `0x1650f` | 7 |
| mayhem | `0xfb06` | `0x136a3` | 125 | `0x136b1` | 6 |

The invoke wrapper is one function per program and is identical in shape: it copies the
caller's `Vec<AccountMeta>` (34-byte records: 32-byte key, `is_signer`, `is_writable`)
into an aligned buffer, copies the instruction data slice, assembles the
`SolInstruction { program_id, accounts, account_len, data, data_len }` struct on the
frame, and calls `sol_invoke_signed_rust`. The `mul64 0x22` sites above are the two
places the wrapper applies the 34-byte stride.

## pump

| builder | handler (depth) | CPI target | discriminator | data length | declared frame | verify |
|---|---|---|---|---|---|---|
| `0x2141c` (496 insns, invoke +2) | admin_cto (+2) | `pump_amm:admin_cto_pool` | `2d3da597680031bd` | 50 | 0:8 disc | 8:32 pubkey | 40:1 bool | 41:1 Option | variable |
| `0x21617` (501 insns, invoke +2) | admin_cto (+2) | `pump_amm:collect_coin_creator_fee` | `a039592ab58b2b42` | 8 | 0:8 disc (no arguments) | match |
| `0x21817` (677 insns, invoke +2) | migrate (+3), migrate_v2 (+3) | `pump_amm:create_pool` | `e992d18ecf6840bc` | 70 | 0:8 disc | 8:2 u16 | 10:8 u64 | 18:8 u64 | 26:32 pubkey | 58:1 bool | 59:1 OptionBool | 60:1 OptionU64 | 61:1 OptionBool | 62:1 OptionBool | variable |
| `0x21ac7` (597 insns, invoke +2) | migrate (+3), migrate_v2 (+3) | `pump_amm:init_boost` | `8ce9215e845ac28f` | 8 | 0:8 disc (no arguments) | match |
| `0x21d27` (565 insns, invoke +2) | admin_cto (+2) | `pump_amm:transfer_creator_fees_to_pump_v2` | `01214eb921432c5c` | 8 | 0:8 disc (no arguments) | match |
| `0x22ce3` (494 insns, invoke +2) | admin_cto (+2) | `pump_fees:admin_cto_sharing_config` | `3c64909c408ab625` | 41 | 0:8 disc | 8:1 Option | variable |
| `0x22edc` (389 insns, invoke +2) | buy (+3), buy_exact_quote_in_v2 (+3), buy_exact_sol_in (+3), and 3 more | `pump_fees:get_fees_with_quote_mint` | `9aed8a5ca202a2bb` | 57 | 0:8 disc | 8:1 bool | 9:16 u128 | 25:32 pubkey | match |
| `0x2316a` (533 insns, invoke +2) | create_v2 (+3) | `mayhem:initialize_mayhem_state` | `9dbd5e485545cc2d` | 8 | 0:8 disc (no arguments) | disc-only |

## pump_amm

| builder | handler (depth) | CPI target | discriminator | data length | declared frame | verify |
|---|---|---|---|---|---|---|
| `0x1af26` (356 insns, invoke +2) | multi_hop_swap (+3) | `pump:multi_hop_curve_swap` | `e19a7516d756f667` | 16 | 0:8 disc | 8:8 u64 | 16:4 bytes | variable |
| `0x1b5bd` (389 insns, invoke +2) | buy (+3), buy_exact_quote_in (+3), sell (+3) | `pump_fees:get_fees_with_quote_mint` | `9aed8a5ca202a2bb` | 57 | 0:8 disc | 8:1 bool | 9:16 u128 | 25:32 pubkey | match |

## pump_fees

| builder | handler (depth) | CPI target | discriminator | data length | declared frame | verify |
|---|---|---|---|---|---|---|
| `0x109b8` (485 insns, invoke +2) | update_fee_shares (+3) | `pump:distribute_creator_fees` | `a572670079cef751` | 8 | 0:8 disc (no arguments) | match |
| `0x10ba8` (566 insns, invoke +2) | update_fee_shares_v2 (+3) | `pump:distribute_creator_fees_v2` | `ffcb134ff444089f` | 9 | 0:8 disc | 8:1 bool | match |
| `0x10de9` (453 insns, invoke +2) | create_fee_sharing_config (+2) | `pump_amm:extend_account` | `ea66c2cb96483ee5` | 8 | 0:8 disc (no arguments) | match |
| `0x10fb9` (453 insns, invoke +2) | create_fee_sharing_config (+2) | `pump:migrate_bonding_curve_creator` | `577c34bf3426d6e8` | 8 | 0:8 disc (no arguments) | match |
| `0x11abc` (437 insns, invoke +2) | create_fee_sharing_config (+2) | `pump_amm:migrate_pool_coin_creator` | `d0089f044aaf103a` | 8 | 0:8 disc (no arguments) | match |
| `0x11c7c` (533 insns, invoke +2) | update_fee_shares (+3) | `pump_amm:transfer_creator_fees_to_pump` | `8b348655e4e56cf1` | 8 | 0:8 disc (no arguments) | match |
| `0x11e9c` (565 insns, invoke +2) | update_fee_shares_v2 (+3) | `pump_amm:transfer_creator_fees_to_pump_v2` | `01214eb921432c5c` | 8 | 0:8 disc (no arguments) | match |

## mayhem

| builder | handler (depth) | CPI target | discriminator | data length | declared frame | verify |
|---|---|---|---|---|---|---|
| `0xdcfc` (558 insns, invoke +1) | buy (+2) | `pump_amm:buy` | `66063d1201daebea` | 25 | 0:8 disc | 8:8 u64 | 16:8 u64 | 24:1 OptionBool | variable |
| `0xdf38` (521 insns, invoke +1) | sell (+2) | `pump_amm:sell` | `33e685a4017f83ad` | 24 | 0:8 disc | 8:8 u64 | 16:8 u64 | match |
| `0xeb3b` (670 insns, invoke +1) | buy_pump_swap (+2) | `pump_amm:buy` | `66063d1201daebea` | 25 | 0:8 disc | 8:8 u64 | 16:8 u64 | 24:1 OptionBool | variable |
| `0xede7` (633 insns, invoke +1) | sell_pump_swap (+2) | `pump_amm:sell` | `33e685a4017f83ad` | 24 | 0:8 disc | 8:8 u64 | 16:8 u64 | match |
| `0x1098d` (734 insns, invoke +1) | buy_v2 (+2) | `pump_amm:buy_v2` | `b817ee6167c5d33d` | 8 | 0:8 disc | 8:8 u64 | 16:8 u64 | serializer |
| `0x10c6e` (706 insns, invoke +1) | sell_v2 (+2) | `pump_amm:sell_v2` | `5df6823ce7e940b2` | 24 | 0:8 disc | 8:8 u64 | 16:8 u64 | match |

## Payload frames

Measured store offsets, one row per edge; `x:y` is offset:width, `reg` marks a value
copied from a register, an `= 0x..` marks a literal immediate.

### pump

- `0x2141c` -> pump_amm:admin_cto_pool (50 bytes, variable)
  - measured: 0:8 8:8 16:8 24:8 32:8 40:1 41:1 = 0x0 42:8
  - declared: 0:8 disc | 8:32 pubkey | 40:1 bool | 41:1 Option
- `0x21617` -> pump_amm:collect_coin_creator_fee (8 bytes, match)
  - measured: 0:8
- `0x21817` -> pump_amm:create_pool (70 bytes, variable)
  - measured: 0:8 8:2 10:8 18:8 26:8 34:8 42:8 50:8 58:1 59:1 60:8 68:1 69:1
  - declared: 0:8 disc | 8:2 u16 | 10:8 u64 | 18:8 u64 | 26:32 pubkey | 58:1 bool | 59:1 OptionBool | 60:1 OptionU64 | 61:1 OptionBool | 62:1 OptionBool
- `0x21ac7` -> pump_amm:init_boost (8 bytes, match)
  - measured: 0:8
- `0x21d27` -> pump_amm:transfer_creator_fees_to_pump_v2 (8 bytes, match)
  - measured: 0:8
- `0x22ce3` -> pump_fees:admin_cto_sharing_config (41 bytes, variable)
  - measured: 0:8 8:1 = 0x0 9:8 17:8 25:8 33:8
  - declared: 0:8 disc | 8:1 Option
- `0x22edc` -> pump_fees:get_fees_with_quote_mint (57 bytes, match)
  - measured: 0:8 8:1 9:8 17:8 25:8 33:8 41:8 49:8
  - declared: 0:8 disc | 8:1 bool | 9:16 u128 | 25:32 pubkey
- `0x2316a` -> mayhem:initialize_mayhem_state (8 bytes, disc-only)
  - measured: 0:8

### pump_amm

- `0x1af26` -> pump:multi_hop_curve_swap (16 bytes, variable)
  - measured: 0:8 8:8
  - declared: 0:8 disc | 8:8 u64 | 16:4 bytes
- `0x1b5bd` -> pump_fees:get_fees_with_quote_mint (57 bytes, match)
  - measured: 0:8 8:1 9:8 17:8 25:8 33:8 41:8 49:8
  - declared: 0:8 disc | 8:1 bool | 9:16 u128 | 25:32 pubkey

### pump_fees

- `0x109b8` -> pump:distribute_creator_fees (8 bytes, match)
  - measured: 0:8
- `0x10ba8` -> pump:distribute_creator_fees_v2 (9 bytes, match)
  - measured: 0:8 8:1
  - declared: 0:8 disc | 8:1 bool
- `0x10de9` -> pump_amm:extend_account (8 bytes, match)
  - measured: 0:8
  - discriminator shared by: mayhem:extend_account, pump:extend_account, pump_amm:extend_account
- `0x10fb9` -> pump:migrate_bonding_curve_creator (8 bytes, match)
  - measured: 0:8
- `0x11abc` -> pump_amm:migrate_pool_coin_creator (8 bytes, match)
  - measured: 0:8
- `0x11c7c` -> pump_amm:transfer_creator_fees_to_pump (8 bytes, match)
  - measured: 0:8
- `0x11e9c` -> pump_amm:transfer_creator_fees_to_pump_v2 (8 bytes, match)
  - measured: 0:8

### mayhem

- `0xdcfc` -> pump_amm:buy (25 bytes, variable)
  - measured: 0:8 8:8 16:8 24:1
  - declared: 0:8 disc | 8:8 u64 | 16:8 u64 | 24:1 OptionBool
  - discriminator shared by: mayhem:buy, pump:buy, pump_amm:buy
- `0xdf38` -> pump_amm:sell (24 bytes, match)
  - measured: 0:8 8:8 16:8
  - declared: 0:8 disc | 8:8 u64 | 16:8 u64
  - discriminator shared by: mayhem:sell, pump:sell, pump_amm:sell
- `0xeb3b` -> pump_amm:buy (25 bytes, variable)
  - measured: 0:8 8:8 16:8 24:1
  - declared: 0:8 disc | 8:8 u64 | 16:8 u64 | 24:1 OptionBool
  - discriminator shared by: mayhem:buy, pump:buy, pump_amm:buy
- `0xede7` -> pump_amm:sell (24 bytes, match)
  - measured: 0:8 8:8 16:8
  - declared: 0:8 disc | 8:8 u64 | 16:8 u64
  - discriminator shared by: mayhem:sell, pump:sell, pump_amm:sell
- `0x1098d` -> pump_amm:buy_v2 (8 bytes, serializer)
  - measured: 0:8
  - declared: 0:8 disc | 8:8 u64 | 16:8 u64
  - the builder hands the buffer to `0x11f60` with length 8 at `0x1099b`; the argument payload is appended there, final length 24
  - discriminator shared by: mayhem:buy_v2, pump:buy_v2, pump_amm:buy_v2
- `0x10c6e` -> pump_amm:sell_v2 (24 bytes, match)
  - measured: 0:8 8:8 16:8
  - declared: 0:8 disc | 8:8 u64 | 16:8 u64
  - discriminator shared by: mayhem:sell_v2, pump:sell_v2, pump_amm:sell_v2

## Verification

`python3 tools/cpi_frames.py --verify` rebuilds the map from the ELFs and fails on any
fixed-size declared frame that the measured stores do not reproduce.

- fixed-size frames: 15 reproduced exactly (declared field offsets present, length equal)
- variable frames: 6 (`Option`/`String` targets, tag and prefix offsets reported)
- discriminator-only frames: 1
- serializer-appended payloads: 1
- frame-count mismatches: 0

Discriminators are little-endian in the `lddw` immediate, e.g. pump_fees
`get_fees_with_quote_mint` `9aed8a5ca202a2bb` appears as `0xbba202a25c8aed9a` at
`0x22ef8` in pump and `0x1b5d9` in pump_amm.
