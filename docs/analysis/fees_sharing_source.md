# pump_fees claim / sharing / social / donation subsystem - reconstructed source

Target: `evidence/original/pump_fees/deployed.so` (pump_fees `pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ`).
Scope: exactly the 12 claim/sharing/social/donation handlers listed in QUEUE.md P0, their
internal helpers, and the three account layouts they read or write.
Behavioural baseline: `specs-fees/fees_specs.md` (not repeated here).

Tags: **[B]** confirmed in the deployed disassembly, address cited ·
**[R]** taken from the repo reference (specs / recovered source / `docs/account_layouts.md`) ·
**[partial]** inconclusive, reason given.

Instruction addresses are insn indices (`byte = insn * 8`), produced with the
relocation-aware loader `tools/fees_prog.py` (`.rel.dyn` applied: type 10 renames `call`
sites, type 8 resolves `lddw` rodata pointers). Every call target below is
`pc + 1 + imm` computed from the deployed bytes.

Tooling added this tick (all local, `tools/`): `fees_walk.py` (annotated body walk),
`fees_ladder.py` (symbolic r1..r3 at every call), `fees_anchors.py` (AnchorError
file:line:code tuples per function), `fees_errnames.py` (FeeError message table by
interpreting the resolver), `fees_codes.py` (code immediates), `fees_sysscan.py`
(syscall/helper call-site census), `fees_b58.py`, `fees_hex.py`.

---

## 1. Deployed entry table

| handler | disc | entry insn | .text byte | insns | Anchor log | try_accounts | body (impl) | account serialiser |
|---|---|---:|---:|---:|---|---|---|---|
| create_fee_sharing_config | c34e564c6f34fbd5 | 0x13810 | 0x9c080 | 168 | `Instruction: CreateFeeSharingConfig` @0x13814 | 0xd95d (1321) | 0x56c7 (1510) | 0xe2a5 (365) |
| revoke_fee_sharing_authority | 12e99e27b9cf3a68 | 0x138ba | 0x9c5d0 | 12 | `Instruction: RevokeFeeSharingAuthority` @0x138bb | in body | 0x14217 (58) | in body |
| transfer_fee_sharing_authority | ca0a4bc8a422d260 | 0x138c7 | 0x9c638 | 12 | `Instruction: TransferFeeSharingAuthority` @0x138c8 | in body | 0x14258 (58) | in body |
| update_fee_shares | bd0d8863bba4ed23 | 0x138d4 | 0x9c6a0 | 129 | `Instruction: UpdateFeeShares` @0x138d9 | 0xecba (1927) | 0x5e6f (696) | 0x989 (132) |
| update_fee_shares_v2 | 6ffb31064e4e6a12 | 0x1395a | 0x9cad0 | 134 | `Instruction: UpdateFeeSharesV2` @0x1395f | 0xf52a (2034) | 0x673a (974) | 0x989 (132) |
| admin_cto_sharing_config | 3c64909c408ab625 | 0x139e4 | 0x9cf20 | 171 | `Instruction: AdminCtoSharingConfig` @0x139e9 | 0xba35 (733) | 0x3e64 (586) | 0x989 (132) |
| set_social_claim_authority | 9336b89a88edb999 | 0x12eca | 0x97650 | 188 | `Instruction: SetSocialClaimAuthority` @0x12ecf | 0xa5d2 (548) | 0x341d (382) | 0xa0f (124) |
| create_social_fee_pda | 90e03bd34ef8cadc | 0x13a95 | 0x9d4a8 | 194 | `Instruction: CreateSocialFeePda` @0x13a9a | 0xe4d2 (860) | 0x5cd3 (389) | 0xa8d (170) |
| claim_social_fee_pda | e115fb85a11ec7e2 | 0x13b5d | 0x9dae8 | 248 | `Instruction: ClaimSocialFeePda` @0x13b62 | 0xbe2e (748) | 0x40d1 (551) | 0xa8d (170) |
| claim_social_fee_pda_v2 | 114df0863abc3595 | 0x13c64 | 0x9e320 | 249 | `Instruction: ClaimSocialFeePdaV2` @0x13c69 | 0xc131 (1199) | 0x4308 (1303) | 0xa8d (170) |
| create_donation_fee_pda | f48b10580eff7a1a | 0x14044 | 0xa0220 | 113 | `Instruction: CreateDonationFeePda` @0x14048 | 0xcfe6 (1094) | 0x500a (1641) | 0xb3b (147) |
| crank_donation_fee_pda | dc0abda7a9111945 | 0x140b8 | 0xa05c0 | 104 | `Instruction: CrankDonationFeePda` @0x140bc | 0xc788 (1312) | 0x483d (1950) | 0xcf6f (112) |

All twelve discs are the `lddw` immediate in the dispatcher at insn `0x12420..0x124c2` and
match `sha256("global:" + name)[:8]` **[B]**.

`update_fee_shares`, `update_fee_shares_v2`, `admin_cto_sharing_config` also carry the
account-name string `sharing_config` in the frame (`lddw` len-14 pair at 0x1394d, 0x139d7,
0x13a89) **[B]**; `create_social_fee_pda` / `claim_social_fee_pda(_v2)` carry
`social_fee_pda` (0x13aff, 0x13c2f) **[B]**; `create_donation_fee_pda` carries
`donation_fee_pda` (0x1408b) **[B]**; `set_social_claim_authority` carries
`fee_program_global` (0x12f2d) **[B]**.

---

## 2. Shared helpers

### 2.1 Corrected helper table

| helper | insn | byte | insns | role |
|---|---|---:|---:|---|
| `deserialize_fee_shares` | 0x212b | 0x10958 | 147 | argument deserialiser called by both `update_fee_shares*` |
| `sol_memcpy_` thunk | 0x184d9 | 0xc26c8 | 4 | `call sol_memcpy_` at 0x184da; 372 call sites in the program [B] |
| **`sol_memcmp_` thunk** | **0x184e6** | **0xc2730** | **8** | `stw [fp-4], 0` at 0x184e6, `call sol_memcmp_` at 0x184e9, result returned sign-extended (lsh/arsh 0x20 at 0x184eb/0x184ec); **274 call sites** [B] |
| **`sol_memmove_` thunk** | **0x184dd** | **0xc26e8** | **4** | `call sol_memmove_` at 0x184de, returns dst; **exactly one caller: 0x171f** inside the bump-allocator / `Vec` grow path 0x1636 (636 insns) [B] |
| `Vec::extend_from_slice` writer | 0x15991 | 0xacc88 | 35 | `(r1 = &mut Vec {ptr@0, cap@8, len@0x10}, r2 = src, r3 = n)`; clamps `n` to `cap - len`, `sol_memcpy_` at 0x159a5, `len += taken` at 0x159ad [B] |
| `Vec<Shareholder>` serialiser | 0x1e6d | 0xf368 | 32 | writes a `u32` length (`jgt 0xffffffff` guard at 0x1e74, `stxw`+4-byte copy at 0x1e75/0x1e7a), then per element 32-byte address (`memcpy 0x20` at 0x1e82) + `u16` at element+0x20 (`ldxh`/`stxh` at 0x1e84/0x1e85) with **stride 0x22 = 34** (`mul64 r7, 0x22` at 0x1e7c, `add64 r8, 0x22` at 0x1e8c) [B] |
| FeeError message resolver | 0x8dca | 0x46e50 | 149 | binary search on the `u32` at `[r1+0]` (code passed **by reference**) into 36 `(ptr,len)` leaves, then `callx r4` (formatter). Recovered table in §2.2 [B] |
| `err!(FeeError)` constructor | 0x8d8b | 0x46c58 | 59 | `(r1 = out, r2 = discriminant 0..35)`; builds the `AnchorError` for one enum variant directly (no Location) [B] |
| AnchorError message writer | 0x8932 | 0x44990 | 917 | formats a `fmt::Arguments` record (`r2` = the `.rodata` record) into `(ptr,len)` message text; the `core::fmt` instantiation used by every `require!` message [B: args at 0x5eb7, 0x5ee2, 0x724e/0x7272, 0x7274] |
| AnchorError box (0xa0) | 0x15a4e | 0xad270 | 17 | `alloc(0xa0)`, `sol_memcpy_` 0xa0 bytes, returns `(tag 0, ptr)` [B] |
| AnchorError + origin (0x80) | 0x15a5f | 0xad2f8 | 20 | `alloc(0x80)`, stores tag `2` at +0, copies a 0x30-byte origin triple to +0x20..+0x38, `stb [r0+0x38], 2`, returns `(tag 1, ptr)` [B] |
| AnchorError ctor by code | 0x1601e | 0xb00f0 | 70 | `(r1 = out, r2 = code)`; the ctor used by the `try_accounts` constraint paths [B] |
| error-name formatter | 0x2b1 | 0x1588 | 77 | appends the account/instruction name to the error message [B] |
| account-name/authority gate | 0x724e | 0x39270 | 140 | `fee_sharing/mod.rs` helper: admin compare, `admin_revoked`, `status`; see §4.4 [B] |
| remaining-accounts / creator-fee flush | 0x7113 | 0x38898 | 295 | `fee_sharing/mod.rs` helper: 6013 @mod.rs:60, Location 74, 6033 @mod.rs:83 [B] |
| shareholder set validator | 0x6479 | 0x323c8 | 669 | `update_fee_shares.rs` 6010@258, 6011@259, 6017@269, 6014@291, 6012@292; the only route from the two bodies to the allocator 0x1636 [B] |
| bump allocator / `Vec` grow | 0x1636 | 0xb1b0 | 636 | heap cursor `0x300000000`..`0x300008000`; contains the single `sol_memmove_` call at 0x171f [B, chain in `docs/fees_locations_and_memmove.md` §5] |
| CPI assembly + invoke | 0x72e5 | 0x39728 | 117 | repacks 6 x 0x30-byte account metas, calls the invoke wrapper 0x109b8 (485) at 0x7353 [B] |
| drop-in-place loop | 0x1424 | 0xa120 | 26 | walks a `RefCell` chain decrementing borrow counters [B] |
| `ProgramError` drop | 0x1ec6 | 0xf630 | 178 | drop / conversion for the enum error values, 7 sites in 0x5e6f (0x60f6..0x610f) [B] |
| `SharingConfig` packer | 0x989 | 0x4c48 | 132 | writes the account image, disc `lddw` 0xc3ddf at 0x9a8; ladder in §3.1 |
| `SocialFeePda` packer | 0xa8d | 0x5468 | 170 | disc `lddw` 0xc3de7 at 0xaac; ladder in §3.2 |
| `DonationFeePda` packer | 0xb3b | 0x59d8 | 147 | disc `lddw` 0xc3d6f at 0xb5a; ladder in §3.3 |
| `FeeConfig` packer | 0xbd0 | 0x5e80 | 122 | surrounding subsystem, cited for completeness; disc `lddw` at 0xbef |
| event-authority check | 0x17148 | 0xb8a40 | 41 | shared `event_authority` / `program` guard used by 6 of the 12 |
| small out-param writer | 0x1621c | 0xb10e0 | 2 | two-instruction trampoline |

### 2.1.1 Correction to the previous tick's memmove reading

The previous revision of this file listed insn `0x184e6` as the `sol_memmove_` thunk and the
v2 site `0x67f0` as its call. Both are wrong on the deployed bytes:

* `0x184e6` is the **`sol_memcmp_`** thunk. Its 8 instructions are `stw [fp-4], 0`,
  `mov64 r4, fp`, `add64 r4, -4`, `call sol_memcmp_` (relocated, at 0x184e9), then
  `ldxw r0, [fp-4]`, `lsh64 r0, 0x20`, `arsh64 r0, 0x20`, `exit` **[B]**. It has 274 call
  sites, which is also why it looks like a "shared" thunk in the call census.
* The `sol_memmove_` thunk is `0x184dd` (4 insns, syscall at 0x184de) and it has **one**
  caller, `0x171f`, inside the allocator `0x1636` **[B: `fees_sysscan.py --callers-of 0x184dd`]**.
  The reachability chain (`0x5e6f` -> `0x6479` @0x60e6/@0x612e -> `0x1636` @0x658c and
  `0x673a` -> `0x6e50` @0x6ad5/@0x6b12 -> `0x1636` @0x6f63) is the one already measured in
  `docs/fees_locations_and_memmove.md` §5.
* `0x67f0` inside `0x673a` is `call sol_memcmp_` with `r3 = 0x20`: a 32-byte key comparison
  (`add64 r2, -0x40` at 0x67ee, unequal branch at 0x67fc materialises the two rodata
  constants 0x100000000f0a098 / 0x553beb1adc39c4da). It is not a copy.

Consequence for the two bodies: `update_fee_shares` **does** reach `sol_memmove_`, but only
indirectly, through the shareholder-set validator `0x6479` and the allocator `0x1636`; the
in-place gap-closing shift documented in `docs/fees_locations_and_memmove.md` §5
(`dst = [fp-0x68]`, `src = dst + 0x10`, `len = (a - b - 1) * 16`) therefore belongs to that
allocator/grow path, not to a direct call in either body **[B]**.

### 2.2 Recovered FeeError message table (codes 6000..6039)

Resolver: insn `0x8dca` (byte `0x46e50`). Shape measured: `ldxw r2, [r3+0]` at 0x8dce (the
code is passed by reference in `r1`), a signed binary search on that `u32`, each leaf
`lddw r2, <rodata VA>` + `mov64 r3, <len>`, then `callx r4` at 0x8e81. Recovered by
interpreting that ladder (`tools/fees_errnames.py`), code = 6000 + discriminant:

| code | message text (rodata, len) | code | message text (rodata, len) |
|---:|---|---:|---|
| 6000 | `Only Pump and PumpSwap programs can call this instruction` @0xc457a (57) | 6020 | `Remaining account key doesn't match shareholder address` @0xc4810 (55) |
| 6001 | `Invalid admin` @0xc45b3 (13) | 6021 | `Feature is currently deactivated` @0xc37e0 (32) |
| 6002 | `No fee tiers provided` @0xc45c0 (21) | 6022 | `User ID exceeds maximum length` @0xc4847 (30) |
| 6003 | `format` @0xc45d5 (6) **[B] (closed in P1-f)** | 6023 | `Instruction is deprecated` @0xc4865 (25) |
| 6004 | `The offset should be <= fee_config.fee_tiers.len()` @0xc45db (50) | 6024 | `Reward split can only be updated once` @0xc487e (37) |
| 6005 | `Fee tiers must be sorted by market cap threshold (ascending)` @0xc460d (60) | 6025 | `Math overflow` @0xc48a3 (13) |
| 6006 | `Fee total must not exceed 10_000bps` @0xc4649 (35) | 6026 | `Invalid buybackindex` @0xc48b0 (20) |
| 6007 | `Invalid Sharing Config` @0xc466c (22) | 6027 | `Claim rate limit exceeded` @0xc4040 (25) |
| 6008 | `Invalid Pool` @0xc4682 (12) | 6028 | `Account is not a valid FeeConfig for this instruction` @0xc48c4 (53) |
| 6009 | `Sharing config authority has been revoked - sharing config can only be updated once` @0xc468e (83) | 6029 | `Account type not supported` @0xc48f9 (26) |
| 6010 | `No shareholders provided` @0xc46e1 (24) | 6030 | `Mint does not match quote mint` @0xc4913 (30) |
| 6011 | `format` @0xc45d5 (6) **[B] (closed in P1-f)** | 6031 | `Unsupported quote mint` @0xc4931 (22) |
| 6012 | `Duplicate shareholder address` @0xc46f9 (29) | 6032 | `Invalid remaining accounts` @0xc4947 (26) |
| 6013 | `Not enough remaining accounts` @0xc4716 (29) | 6033 | `Pool creator_fees must be swept before the shares change` @0xc4961 (56) |
| 6014 | `Invalid share total - must equal 10_000 basis points` @0xc4733 (52) | 6034 | `quote_mint is not the bonding curve's quote mint` @0xc4999 (48) |
| 6015 | `Share calculation overflow` @0xc4767 (26) | 6035 | `Token withdrawals need quote_mint, vault_ata, user_ata and token_program` @0xc49c9 (72) |
| 6016 | `The given account is not authorized to execute this instruction.` @0xc4781 (64) | 6036 | `Nothing to withdraw` @0xc4a11 (19) |
| 6017 | `Shareholder cannot have zero share` @0xc47c1 (34) | 6037..6039 | same leaf @0xc4a11 (19) |
| 6018 | `Fee sharing config is not active` @0xc3720 (32) | | |
| 6019 | `AMM accounts are required for graduated coins` @0xc47e3 (45) | | |

Cross-check against the name column of `specs-fees/fees_specs.md` §Error table: every code
that file names agrees with the text above (6001 InvalidAdmin, 6002 NoFeeTiers,
6004 OffsetNotContinuous, 6005 FeeTiersNotSorted, 6006 InvalidFeeTotal, 6007 InvalidSharingConfig,
6008 InvalidPool, 6010 NoShareholders, 6012 DuplicateShareholder, 6013 NotEnoughRemainingAccounts,
6014 InvalidShareTotal, 6016 NotAuthorized, 6017 ZeroShareNotAllowed, 6018 SharingConfigNotActive,
6020 ShareholderAccountMismatch, 6022 UserIdTooLong, 6023 DeprecatedInstruction,
6024 FeeSharesAlreadyUpdated, 6026 InvalidBuybackIndex, 6028 InvalidFeeConfigAccount,
6029 AccountTypeNotSupported, 6030 InvalidMint, 6031 UnsupportedQuoteMint,
6033 PoolCreatorFeesNotSwept, 6034 InvalidQuoteMint, 6036 NothingToWithdraw) **[B]**.
Two leaves hold the pooled string `format` (0xc45d5) for 6003 and 6011: the enum variants
there are `TooManyFeeTiers` / `TooManyShareholders` per the source table **[R]**, so the
resolver's 6-byte entry is read as a string-pool artifact rather than a message **[B] (closed in P1-f)**.
The nine codes `specs-fees` could not isolate from immediates now carry text:
6000, 6009, 6015, 6019, 6021, 6025, 6027, 6032, 6035 **[B]**.

### 2.3 Per-body AnchorError origins (file:line + code)

Measured with `tools/fees_anchors.py`: every `lddw` that resolves to a
`programs/pump-fees/...` path, the `stdw` length that accompanies it, the `stw` line and the
code immediate in the same tuple. These are the real `Location` values Anchor embeds in the
error, i.e. the original source lines of each raise site:

| function | file | line | code |
|---|---|---:|---|
| 0x14217 (revoke body) | `lib.rs` | 183 | 6023 |
| 0x14258 (transfer body) | `lib.rs` | 188 | 6023 |
| 0x5e6f (update_fee_shares) | `instructions/fee_sharing/update_fee_shares.rs` | 129 | 6031 |
| 0x5e6f | same | 130 | 6024 |
| 0x673a (update_fee_shares_v2) | `instructions/fee_sharing/update_fee_shares_v2.rs` | 137 | 6024 |
| 0x673a | same | 152 | 6034 |
| 0x724e (mod.rs authority gate) | `instructions/fee_sharing/mod.rs` | 97 | 6016 |
| 0x724e | same | 99 | 6018 |
| 0x7113 (mod.rs remaining/flush) | `instructions/fee_sharing/mod.rs` | 60 | 6013 |
| 0x7113 | same | 74 | - |
| 0x7113 | same | 83 | 6033 |
| 0x6479 (shareholder validator) | `update_fee_shares.rs` | 258 | 6010 |
| 0x6479 | same | 259 | 6011 |
| 0x6479 | same | 269 | 6017 |
| 0x6479 | same | 291 | 6014 |
| 0x6479 | same | 292 | 6012 |
| 0x56c7 (create_fee_sharing_config) | `create_fee_sharing_config.rs` | 273 | 6008 |
| 0x56c7 | same | 280 | 6008 |
| 0x56c7 | same | 297 | 6008 |
| 0x56c7 | same | 302 | 6016 |
| 0x56c7 | same | 307 | 6016 |
| 0x3e64 (admin_cto_sharing_config) | `admin_cto_sharing_config.rs` | 86 | 6001 |
| 0x5cd3 (create_social_fee_pda) | `create_social_fee_pda.rs` | 67 | 6022 |
| 0x500a (create_donation_fee_pda) | `create_donation_fee_pda.rs` | 148 | 6008 |
| 0x500a | same | 152 | 6008 |
| 0x500a | same | 156 | 6008 |
| 0x500a | same | 174 | 6008 |
| 0x500a | same | 192 | 6007 |
| 0x500a | same | 197 | 6007 |
| 0x500a | same | 204 | 6007 |
| 0x500a | same | 213 | 6016 |
| 0x500a | same | 214 | 6018 |
| 0x500a | same | 221 | 6016 |

Two new file-level anchors come out of this table: `instructions/fee_sharing/mod.rs` carries
raise sites at lines **60, 74, 83, 97, 99** (the file had **no** panic `Location` record, which
is why `docs/fees_locations_and_memmove.md` §3 lists it as "no panic site"), and
`create_donation_fee_pda.rs` carries sites at 148..221 although it likewise has no
`Location` record. So "absent from the panic table" must not be read as "the file has no
source line of interest" **[B]**.

For the four bodies with no path-anchored raise (0x341d, 0x40d1, 0x4308, 0x483d) the raises go
through `err!(FeeError::X)`, i.e. the `0x8d8b` constructor with a **bare discriminant**:

* 0x40d1 @0x40f1 -> disc `0x15` = 6021 (the "ClaimSocialFeePda is currently disabled" gate) **[B]**
* 0x4308 @0x4328 -> disc `0x15` = 6021 **[B]**
* 0x483d @0x48c1 -> disc `0x15` = 6021, @0x4bf3 -> disc `0xf` = 6015 **[B]**

---

## 3. Account layouts

Method: each layout is now closed from its **packer**, which walks the in-memory copy in
Borsh declaration order and hands one field at a time to the `extend_from_slice` writer
0x15991. The write sequence therefore *is* the field table, and the field sizes have to tile
the account size exactly. All three packers open with the same measured guard:
`sol_memcmp_(crate::ID = 0xc4ead, program_id, 32)` at 0x98e / 0xa92 / 0xb5d, `mov64 r9, 2`
(Ok tag) at 0x98f / 0xa93 / 0xb5e, and an early exit at 0x992 / 0xa96 / 0xb5b when the
comparison is non-zero **[B]**. `0xc4ead` base58-decodes to
`pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ` (`tools/fees_b58.py`), the program's own id.

### 3.1 `SharingConfig` - packer 0x989 (byte 0x4c48, 132 insns)

Discriminator **`d84a0900388c5d4b`** = `sha256("account:SharingConfig")[:8]` **[B]**: rodata
0xc3ddf, `lddw r2` at 0x9a8, written into the output buffer at 0x9ab with `r3 = 8`.

Field ladder, in serialisation order (each row is one `call 0x15991` with the frame slot it
fills, the source expression and the length) **[B]**:

| # | serialised field | size | source in memory | writer call |
|---:|---|---:|---|---|
| 0 | discriminator | 8 | rodata 0xc3ddf | 0x9ab (`lddw` at 0x9a8) |
| 1 | `bump: u8` | 1 | `struct + 0x5a` | 0x9c4 |
| 2 | `version: u8` | 1 | `struct + 0x5b` | 0x9cb |
| 3 | `status: u8` | 1 | `struct + 0x58` (byte copied through `fp-1`, `ldxb` at 0x9cd) | 0x9d4 |
| 4 | `mint: [u8; 32]` | 32 | `struct + 0x18` | 0x9db |
| 5 | `admin: [u8; 32]` | 32 | `struct + 0x38` | 0x9e2 |
| 6 | `admin_revoked: u8` | 1 | `struct + 0x59` (`ldxb` at 0x9e4) | 0x9eb |
| 7 | `shareholders: Vec<Shareholder>` | 4 + 34·n | slice `(ptr = struct+0x8, len = struct+0x10)` | 0x9f1 -> `0x1e6d` |

* Serialised size = 8 + 1 + 1 + 1 + 32 + 32 + 1 + (4 + 34·n) = **80 + 34·n** **[B: the field
  sizes tile the ladder exactly and the element stride is 34 in 0x1e6d]**. The `space = 1024`
  init value is **[R]**.
* `Shareholder` element layout **[B]**: `address: [u8; 32]` at element+0x00 (32-byte
  `sol_memcpy_` at 0x1e82), `share_bps: u16` at element+0x20 (`ldxh`/`stxh` 0x1e84/0x1e85),
  stride 0x22 (34).
* Name mapping of rows 1..6 to the declared identifiers is **[R]**; the *order* and the
  *memory offsets* are **[B]**. Note that the in-memory order differs from the serialised
  order (Rust field reordering): `status` lives at 0x58, `admin_revoked` at 0x59, and the two
  remaining `u8` at 0x5a / 0x5b. That assignment is cross-checked independently by the
  authority gate 0x724e, which reads `[sharing_config+0x59]` as the revoked flag (0x7263),
  `[sharing_config+0x58]` as the status (0x726d) and compares 32 bytes at `+0x38` as the admin
  (0x725f) - so `admin` at 0x38 and the two named `u8` are pinned twice **[B]**; which of
  0x5a / 0x5b is `bump` and which is `version` was settled by the store map of §16.10:
  `0x5864` stores the program-derived `sharing-config` bump at 0x5a and `0x5865` stores the
  constant 2 at 0x5b, so 0x5a is `bump` and 0x5b is `version` **[B pairing, R names]**. The
  in-memory copy is 0x5c =
  92 bytes: `[0x00,0x08)` head, the shareholder fat pointer at 0x08 / 0x10, `mint`
  0x18..0x38, `admin` 0x38..0x58, the four `u8` 0x58..0x5c **[B]**.
* The two 8-byte writers the previous revision pinned "at 0x990 (struct + 0x48)" and
  "0x99a (struct + 0x50)" do not exist in this packer: 0x990 is `lsh64 r0, 0x20`, 0x99a is a
  `call`, and the body contains no store to struct+0x48 / struct+0x50 at all. Those two
  readings are withdrawn (they match the `pump_amm` mis-probe noted in QUEUE.md).
* Load site: 0x250d (60 insns) is the loader used by `update_fee_shares`; it gates on
  `data.len() >= 0x73` (`jlt r0, 0x73` at 0x2511), increments the borrow counter at 0x251a,
  and compares a 32-byte key slice taken from the account image (`ldxdw [r1+0x59]` at 0x2525,
  `[r1+0x53]`, `[r1+0x57]`, `[r1+0x61]`, `[r1+0x62]`, `[r1+0x6a]`, `[r1+0x72]` at
  0x252a..0x2532) against a zeroed 32-byte frame buffer (`sol_memcmp_` at 0x253f), returning a
  one-byte tag at `[out+8]`. The zero-key comparison is the uninitialised-account sentinel
  **[B] (closed in P1-a)**.

### 3.2 `SocialFeePda` - packer 0xa8d (byte 0x5468, 170 insns)

Discriminator **`8b6035112aa9ce96`** = `sha256("account:SocialFeePda")[:8]` **[B]**: rodata
0xc3de7, `lddw r2` at 0xaac, written at 0xaaf with `r3 = 8`.

Field ladder **[B]**:

| # | serialised field | size | source in memory | writer call |
|---:|---|---:|---|---|
| 0 | discriminator | 8 | rodata 0xc3de7 | 0xaaf |
| 1 | `bump: u8` | 1 | `struct + 0xa8` | 0xacc |
| 2 | `version: u8` | 1 | `struct + 0xa9` | 0xad3 |
| 3 | `user_id` Borsh `String` length | 4 | `r3` = the string length (staged at 0xae2) | 0xae4 |
| 4 | `user_id` bytes | n | `ldxdw r2, [fp-0x50]` at 0xaea (the staged string pointer) | 0xaeb |
| 5 | `platform: u8` | 1 | `struct + 0xaa` | 0xaf2 |
| 6 | `total_claimed: u64` | 8 | `struct + 0x18` (`ldxdw` at 0xaf4) | 0xafb |
| 7 | `total_claimed_stable: u64` | 8 | `struct + 0x20` (`ldxdw` at 0xafd) | 0xb04 |
| 8 | `last_claimed_at: u64` | 8 | `struct + 0x28` (`ldxdw` at 0xb06) | 0xb0d |
| 9 | `_reserved` | **0x78 = 120** | `struct + 0x30` (`add64 r7, 0x30` at 0xb13) | 0xb18 |

* Serialised size = 8 + 1 + 1 + 4 + n + 1 + 8 + 8 + 8 + 120 = **159 + n** where n =
  `user_id.len()` **[B: the immediates tile]**; the in-memory copy tiles the same way
  (`0x30 + 0x78 = 0xa8`, the three `u8`s ending at `0xab`), and the 120-byte `_reserved`
  matches `docs/account_layouts.md` §3.3 **[R]**. Variable size, Borsh `Account<SocialFeePda>`.
* Field names rows 1..8 are **[R]** (`docs/account_layouts.md` §3.3); order and offsets **[B]**.
* The in-memory `user_id` occupies `[0x08, 0x18)` and its byte length is written from a
  register, not from a struct offset; the exact field type is **[partial]**, only the
  serialisation order is measured.

### 3.3 `DonationFeePda` - packer 0xb3b (byte 0x59d8, 147 insns)

Discriminator **`f6c56009c11e5d73`** = `sha256("account:DonationFeePda")[:8]` **[B]**: rodata
0xc3d6f, `lddw r2` at 0xb5a, written at 0xb5d with `r3 = 8`.

Field ladder **[B]**:

| # | serialised field | size | source in memory | writer call |
|---:|---|---:|---|---|
| 0 | discriminator | 8 | rodata 0xc3d6f | 0xb5d |
| 1 | `bump: u8` | 1 | `struct + 0xd8` | 0xb76 |
| 2 | `version: u8` | 1 | `struct + 0xd9` | 0xb7d |
| 3 | `config_id: [u8; 32]` | 32 | `struct + 0x48` | 0xb84 |
| 4 | `base_mint: [u8; 32]` | 32 | `struct + 0x68` | 0xb8b |
| 5 | `quote_mint: [u8; 32]` | 32 | `struct + 0x88` | 0xb92 |
| 6 | `creator: [u8; 32]` | 32 | `struct + 0xa8` | 0xb99 |
| 7 | `total_donated: u64` | 8 | `struct + 0xc8` | 0xba2 |
| 8 | `last_crank_ts: u64` | 8 | `struct + 0xd0` (`ldxdw [r7+0xd0]` at 0xba4) | 0xbab |
| 9 | `_reserved[64]` | **0x40 = 64** | `struct + 0x8` (`add64 r7, 0x8` at 0xbad) | 0xbb2 |

* Serialised size = 8 + 1 + 1 + 128 + 8 + 8 + 64 = **218** **[B: tiles exactly, and matches
  `docs/account_layouts.md` §3.3 [R]]**. The in-memory copy tiles the same way and is also
  0xda = 218 bytes: `[0x00,0x08)` head, `_reserved` 0x08..0x48, the four 32-byte keys
  0x48..0xc8, the two `u64` at 0xc8 / 0xd0, the two `u8` at 0xd8 / 0xd9 **[B]**.
* Field names rows 1..8 are **[R]**; order, offsets and sizes **[B]**.
* Write path for the crank instruction: the 112-insn writer 0xcf6f (strings
  `donation_fee_pda`, `donation_fee_pda_ata`, `quote_mint`) called from 0x140fb **[B]**.

---

## 4. Handler modules

Each module below gives the reconstructed dispatch wrapper **[B, every address cited]** and the
state of the body reconstruction. The wrapper shape is measured, not assumed: log string,
argument cursor parked in the frame, argument deserialiser, `try_accounts` over the accounts
slice, a `sol_memcpy_` of the returned accounts struct, the body call, then the account packer
and the `Result` return write (`stxdw [r1+0x8]`/`stxdw [r1+0x0]` at the two exit stores).

```rust
// shared shape, deployed addresses per handler in the table above
pub fn dispatch(
    program_id: &Pubkey,      // r2 at entry (r1 = entry input pointer)
    accounts: &[AccountInfo], // r3 = ptr, r4 = len  [B: stored to fp-0xc28 / fp-0xc20 at 0x138f1/0x138f2]
    data: &[u8],              // [r5-0x1000] = ptr, [r5-0xff8] = len
) -> ProgramResult {
    msg!("Instruction: <Name>");                    // sol_log_ site
    let mut cursor = data;                          // ptr/len parked in the frame
    let args = <Args>::deserialize(&mut cursor)?;   // arg deserialiser site
    let ctx = <Ctx>::try_accounts(program_id, accounts, &mut cursor)?; // try_accounts site
    ctx = memcpy(ctx);                              // 0x184d9 thunk site
    <body>(&ctx, args)?;                            // body site
    <Account>::exit(&ctx)?;                         // packer site
    Ok(())
}
```

### 4.1 `create_fee_sharing_config` - 0x13810 (byte 0x9c080, 168 insns) **[B wrapper]**

```rust
pub fn create_fee_sharing_config(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    data: &[u8],
) -> ProgramResult {
    msg!("Instruction: CreateFeeSharingConfig");          // 0x13814
    let mut cursor = data;                                 // 0x1381d..0x13826
    let ctx = CreateFeeSharingConfigAccounts::try_accounts(program_id, accounts, &mut cursor)?;
                                                           // 0xd95d (1321 insns)
    let ctx = memcpy_frame(ctx);                           // 0x184d9 thunk, call 0x13833
    create_fee_sharing_config_impl(&ctx)?;                 // 0x56c7 (1510 insns), call 0x13847
    SharingConfig::exit(&ctx)?;                            // 0xe2a5 (365 insns), call 0x13850
    Ok(())
}
```

- accounts referenced in the try_accounts frame **[B]**: `global`, `event_authority`, `program`, `payer`.
- body status: **[B] for the gates, the initialisation image, the event and the four external CPIs
  (§16.13, item D2-g closed)**. The raise map is measured (§2.3): `create_fee_sharing_config.rs`
  lines 273/280/297 = 6008 InvalidPool, 302/307 = 6016 NotAuthorized, and every one of those five
  sites now has an instruction address (§16.4), plus five `err!` sites at 6019 and 6008 (§16.5).
  The phase map is closed in **§16** (item D2-a): 21 phases, 65 call sites, 26 distinct callees.
  The extent is corrected there too: the body is **1548 slots, `0x56c7`..`0x5cd2**, not the 1510
  of the pinned slice, because the slice stops at `0x5cac` while the body continues for 38 more
  slots and ends at `0x5cd2 ja -0x18d`. The three `InvalidPool` gates of lines 273/280/297 are
  closed in **§16.8** (item D2-b): `pool.base_mint == mint`, `pool.creator ==
  find_program_address([b"pool-authority", mint])` under the pump program, and `pool.key() ==
  create_program_address([b"pool", index, creator, base_mint, quote_mint, bump])` under the pump
  AMM program, with the `pool` image placed at `ctx+0x4c0` (0xfc bytes). The two 6016 gates of
  lines 302/307 are closed in **§16.9** (item D2-c): both read `payer.key()` against
  `global[0x158]` or `bonding_curve[0x00..0x20]` (307, box at `0x5776`) and against
  `pool[0xc0]` (302, box at `0x5ab9`). The field-by-field store map onto the 3.1 ladder is closed
  in **§16.10** (item D2-d): the eleven stores at `0x5862..0x589e` fill `bump` (`ctx+0x5a`, the
  program-derived bump of the `sharing-config` PDA, read from `arg+0x24`), `version` (`0x5b`, the
  constant 2), `status` (`0x58`, the constant 1), `mint` (`0x18..0x38`), `admin` (`0x38..0x58`),
  `admin_revoked` (`0x59`, the constant 0) and a one-element shareholder vector whose single holder
  is `admin` with `share_bps` 10000, and the arm then issues one serialisation through the 3.1 packer
  `0x989` at `0x58a6`. The event is closed in **§16.11** (item D2-e): the body builds one
  `CreateFeeSharingConfigEvent` image at `fp-0x470`, whose eight borsh fields are `timestamp`
  (clock sysvar `unix_timestamp`, read through the `Clock::get` wrapper `0x1621e` at `0x5b2d`),
  `mint`, `bonding_curve`, `pool: Option<Pubkey>`, `sharing_config`, `admin`, `initial_shareholders`
  and `status`, serialised twice by the same monomorphised serialiser `0xe41c` (its only two callers
  in the program are `0x5bd9` and `0x5bee`) with the discriminator
  `sha256("event:CreateFeeSharingConfigEvent")[0..8]` and published once through `sol_log_data`
  (`0x161a7` at `0x5be1`) and once through a self instruction to `pfeeUxB6...` signed with the
  `__event_authority` seeds (`0x16eb0` at `0x5c1e`, `sol_invoke_signed_rust` via `0x161ae` at
  `0x5c3d`). The reconstructed body is closed in **§16.12** (item D2-f): the body has no loop (both SCCs are
  abort paths), `0x5cd1` is a join edge into the single shared tail so the event is emitted exactly once per
  instruction, the 8 bytes prefixed by `0x21dc` are `sha256("anchor:event")[0..8]`, and the body issues five
  CPI sites, the four external ones through the monomorphised helpers `0x10de9` (twice), `0x10fb9` and
  `0x11abc`. The four external CPIs are named in **§16.13** (item D2-g closed): `pump::extend_account` at
  `0x59cc` and `pump::migrate_bonding_curve_creator` at `0x5b22`, then `pump_amm::extend_account` at
  `0x5ca1` and `pump_amm::migrate_pool_coin_creator` at `0x5cce`, each with an exact preimage of its
  8 byte leading constant (`sha256("global:extend_account")`, `sha256("global:migrate_bonding_curve_creator")`,
  `sha256("global:migrate_pool_coin_creator")`), a measured meta count (5, 5, 5, 4) and a measured
  signer/writable vector. No open item remains on this body.

### 4.2 `revoke_fee_sharing_authority` - 0x138ba (byte 0x9c5d0, 12 insns) **[B]**

```rust
pub fn revoke_fee_sharing_authority(
    _program_id: &Pubkey,
    _accounts: &[AccountInfo],
    _data: &[u8],
) -> ProgramResult {
    msg!("Instruction: RevokeFeeSharingAuthority");        // 0x138bb, rodata 0xc523a, len 0x26
    deprecated_instruction()                               // 0x14217, call 0x138c1
}
```

Measured wrapper **[B]**: 12 instructions, `mov64 r6, r1` at 0x138ba (out pointer),
`lddw r1, 0xc523a` + `mov64 r2, 0x26` + `sol_log_` at 0x138bb..0x138be, `r1 = fp-0x10` at
0x138bf/0x138c0, `call 0x14217` at 0x138c1, then the two exit stores `stxdw [r6+8]`,
`stxdw [r6+0]` at 0x138c4/0x138c5 and `exit` at 0x138c6. **No `try_accounts` call and no
account access at all.**

Body 0x14217 (byte 0xa10b8, 58 insns) - the whole of it, measured:

```rust
// programs/pump-fees/src/lib.rs:183 (Location tuple built at 0x14246..0x1424d)
fn deprecated_instruction() -> Result<(), anchor_lang::error::Error> {
    let msg = format!("{}", FeeError::DeprecatedInstruction);   // 0x8932 @0x1421c, 0x8dca @0x1422e
                                                                // panic path 0x178c8 @0x14239
    Err(Box::new(AnchorError {                                  // allocation 0x15a4e @0x14252
        error_code_number: 6023,                                // stw [fp-0x78], 0x1787 @0x14249
        file: "programs/pump-fees/src/lib.rs",                  // 0xc4f0d, len 29 @0x14246/0x1424c
        line: 183,                                              // stw [fp-0xf8], 0xb7 @0x1424b
        ..                                                      // origin struct zeroed at 0x1424d
    }))
}
```

Instruction-level evidence **[B]**: `mov64 r6, r1` 0x14217; `r1 = fp-0x70`, `lddw r2,
0xc3e74` (fmt record), `call 0x8932` 0x14218..0x1421c; three zero/one stores to fp-0x48 /
fp-0x50 / fp-0x58 at 0x1421d..0x1421f; the `lddw 0xc87f8` + `stdw [fp-0x10], 0x20` pair
(0x14220..0x14222) that supplies the 32-byte `&str` the Display writes; `call 0x8dca` at
0x1422e; `jeq r0, 0` / `call 0x178c8` (panic_fmt, message `a Display implementation returned
an error unexpectedly` at 0xc387d, len 0x37) at 0x1422f..0x14239; the origin triple copy at
0x1423a..0x14245; the code/line/file stores at 0x14246..0x1424d; `call 0x15a4e` (0xa0-byte
box) at 0x14252; return write 0x14253..0x14257.

Behaviour: **the handler is a deprecated stub that consumes no accounts and unconditionally
returns `FeeError::DeprecatedInstruction` (6023) from `lib.rs:183`** **[B]**. This matches
`specs-fees/fees_specs.md` §30 **[R]** and the 6023 immediates it recorded at 0x14249/0x1428a.

### 4.3 `transfer_fee_sharing_authority` - 0x138c7 (byte 0x9c638, 12 insns) **[B]**

Identical twelve-instruction thunk: log `Instruction: TransferFeeSharingAuthority` at
0x138c8..0x138cb (rodata 0xc5260, len 0x28), `call 0x14258` at 0x138ce, exit stores
0x138d1/0x138d2, `exit` 0x138d3. No accounts.

Body 0x14258 (byte 0xa12c0, 58 insns): the same shape as 0x14217 with the code/line pair at
0x14287..0x1428d -> `error_code_number = 6023` (`stw [fp-0x78], 0x1787` at 0x1428a) and
`line = 188` (`stw [fp-0xf8], 0xbc`), file `programs/pump-fees/src/lib.rs` (0xc4f0d, len 29)
**[B]**. Behaviour: deprecated stub, `lib.rs:188`, code 6023 **[B]**.

### 4.4 `update_fee_shares` - 0x138d4 (byte 0x9c6a0, 129 insns) **[B wrapper]**

```rust
pub fn update_fee_shares(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    data: &[u8],
) -> ProgramResult {
    msg!("Instruction: UpdateFeeShares");                  // 0x138d9
    let mut cursor = data;                                 // 0x138dd..0x138e4
    let shares = deserialize_fee_shares(&mut cursor)?;     // 0x212b (147 insns), call 0x138e5
    let ctx = UpdateFeeSharesAccounts::try_accounts(program_id, accounts, &mut cursor)?;
                                                           // 0xecba (1927 insns), call 0x138fc
    let ctx = memcpy_frame(ctx);                           // 0x184d9 thunk, call 0x13909 (0x5e8 bytes)
    update_fee_shares_impl(&ctx, shares)?;                 // 0x5e6f (696 insns), call 0x13925
    SharingConfig::exit(&ctx)?;                            // 0x989 (132 insns), call 0x1392f
    Ok(())
}
```

Measured wrapper details **[B]**: the argument deserialiser result is tested against
`i64::MIN` (`lddw 0x8000000000000000` at 0x138e8 and 0x13900); the accounts struct is copied
with length `0x5e8` (1512 bytes) at 0x13908; the body returns its `Result` in fp-0xc40 and the
wrapper branches on tag `2` (= Ok) at 0x13927; the packer is called with
`(out = fp-0xc50, ctx = fp-0xc18, crate::ID = 0xc4ead, program_id = [fp-0xc80])` at
0x13928..0x1392f and the account name `sharing_config` (0xc4c1c, len 0xe) is formatted at
0x1394d..0x13950.

Body 0x5e6f (byte 0x2f378, 696 insns, `update_fee_shares.rs`). Measured skeleton, in
execution order **[B]**:

| # | insn | what the bytes do |
|---:|---|---|
| 1 | 0x5e70..0x5e8d | borrow the first context account (`ldxdw r4, [r2+8]`, borrow counter inc/dec at 0x5e7a / 0x5ea2 / 0x5ea6 / 0x5ea9) and read the AccountInfo flags `[r6+0x28]`/`[r6+0x29]`/`[r6+0x2a]` (is_signer / is_writable / executable) |
| 2 | 0x5e9a | `call 0x250d(fp-0x40, fp-0x278)` - load + zero-key-check the `SharingConfig` image (§3.1) |
| 3 | 0x5eb7, 0x5ec9, 0x5ee2, 0x5ef4 | message + code-name formatting for the two `require!` sites below (fmt records 0xc3e84 and 0xc3e6c; `0x8932` + `0x8dca`), panic path 0x5eff (`0x178c8`) |
| 4 | 0x5f18 | 0xa0-byte AnchorError box (`0x15a4e`) for the raise at 0x5f0c/0x5f0f |
| 5 | 0x5f21 | `call 0x724e(fp-0x288, ctx+0x5d0)` - the `fee_sharing/mod.rs` authority/state gate (§4.4.1) |
| 6 | 0x5f3c | `call 0x7113(fp-0x40)` - the `fee_sharing/mod.rs` helper: its argument block is built at 0x5f24..0x5f3b with `r4 = ctx+0x290`, `r5 = fp`, the quote key parked at `fp-0x1000` and the rodata constant **0xc3740 (WSOL)** at `fp-0xff8` (0x5f34..0x5f36); measured raises 6013 @mod.rs:60 and 6033 @mod.rs:83 |
| 7 | 0x5f5a | second 0xa0-byte error box, for the raise at 0x5f4e/0x5f51 |
| 8 | 0x60ce | `call 0x73f3(fp-0x298, ctx+0x288, fp-0x1d8)` (327 insns) |
| 9 | 0x60d5 | `call 0x63a6(fp-0x278, ?, fp-0x1d8)` (202 insns) - calls the `SharingConfig` packer 0x989 |
| 10 | 0x60e6, 0x612e | `call 0x6479` twice - the shareholder-set validator (6010/6011/6017/6014/6012, §2.3); the only route to the allocator 0x1636 and therefore to `sol_memmove_` |
| 11 | 0x60eb | `call 0x1424(fp-0x148)` - drop the `RefCell` chain |
| 12 | 0x60f6..0x610f | seven `call 0x1ec6` drop sites (ProgramError/AnchorError values) |
| 13 | 0x6125 | `call 0x72e5(fp-0x2a8)` - CPI assembly + invoke |

Raise sites measured **[B]**: 6031 `Unsupported quote mint` from `update_fee_shares.rs:129`
(code immediate at 0x5f0f, path tuple at 0x5f0c) and 6024 `Reward split can only be updated
once` from `update_fee_shares.rs:130` (code at 0x5f51, tuple at 0x5f4e).

Reconstructed body (the parts the bytes support; the two `require!` messages are the
measured order, the shareholder rewrite is delegated to 0x6479):

```rust
pub fn update_fee_shares(ctx: Context<UpdateFeeShares>, shares: Vec<FeeShare>) -> Result<()> {
    let sharing_config = &ctx.accounts.sharing_config;                 // 0x5e70..0x5e9a
    let config = SharingConfig::load(sharing_config)?;                 // 0x250d

    require!(
        quote_mint_is_wsol(&ctx.accounts),                             // measured key compare
        FeeError::UnsupportedQuoteMint                                 // 6031, line 129
    );
    require!(
        !config.shares_updated_once(),                                 // measured: `status`/`admin_revoked`
        FeeError::FeeSharesAlreadyUpdated                              // 6024, line 130
    );

    check_authority_and_state(&ctx, &config)?;                         // 0x724e, mod.rs:97/99
    flush_creator_fees_if_needed(&ctx)?;                               // 0x7113, mod.rs:60/83
    let updated = build_shareholder_set(&ctx, &shares)?;               // 0x6479 (+0x1636 grow)
    let config = apply_shares(config, updated)?;                       // 0x73f3 / 0x63a6
    write_sharing_config(&config)?;                                    // 0x989 via 0x63a6
    Ok(())
}
```

Status: **[partial]**. The call sequence, the helper identities, both `file:line` raise
sites, the account writer and the allocator/memmove path are measured (§2.1, §2.3);
the exact predicates of the two `require!`s and the arithmetic inside 0x6479 (669 insns,
five more raise sites) are not yet walked instruction by instruction, so the reconstructed
line above names the *measured* helpers and codes but not every operand.

#### 4.4.1 The `fee_sharing/mod.rs` authority gate 0x724e (byte 0x39270, 140 insns) **[B]**

Called by both `update_fee_shares` bodies (0x5f21 in 0x5e6f, 0x5cd3-region equivalent in
0x673a). Measured sequence:

```rust
fn check_authority_and_state(ctx: &impl Accounts, config: &SharingConfig) -> Result<()> {
    let signer = ctx.accounts[0].to_account_info();                    // 0x7250..0x7251
    // 32-byte key copy -> fp-0x118 (0x7252..0x7259), compare against config.admin (+0x38)
    if sol_memcmp_(signer.key, &config.admin, 32) != 0 {               // 0x725f
        return Err(NotAuthorized);                                     // 6016, mod.rs:97 (0x1780 @0x72ba)
    }
    if config.admin_revoked != 0 {                                     // ldxb [r7+0x59] @0x7263
        return Err(FeeError::SharingConfigAuthorityRevoked);           // disc 9 -> 6009 (0x8d8b @0x7268)
    }
    if config.status == 0 {                                            // ldxb [r7+0x58] @0x726d
        return Err(FeeError::SharingConfigNotActive);                  // 6018, mod.rs:99 (0x1782 @0x72d8)
    }
    Ok(())
}
```

Notes **[B]**: the two error tuples carry the file `programs/pump-fees/src/instructions/
fee_sharing/mod.rs` (0xc44bd, len 54) with line 97 at 0x72bc and line 99 at 0x72da, and file
length 0x36 only occurs for that path, so the length is itself a second witness for the file
name. The `admin` offset 0x38 and the two `u8` offsets 0x58 (status) / 0x59 (admin_revoked)
are the same in-memory offsets the packer ladder of §3.1 writes, which cross-checks the
layout independently of the serialised order. The 6009 raise goes through `err!(...)`
(0x8d8b) rather than a Location tuple, which is why `specs-fees` did not list it.

### 4.5 `update_fee_shares_v2` - 0x1395a (byte 0x9cad0, 134 insns) **[B wrapper]**

Same shape as 4.4 with `Instruction: UpdateFeeSharesV2` at 0x1395f, argument deserialiser
0x212b at 0x1396b, `try_accounts` 0xf52a (2034) at 0x13981, `memcpy` thunk at 0x1398f, body
0x673a (974) at 0x139ad, packer 0x989 at 0x139b6 and 0x139df.

Body 0x673a (byte 0x339d0, 974 insns, `update_fee_shares_v2.rs`), measured skeleton:

| # | insn | what the bytes do |
|---:|---|---|
| 1 | 0x67ee..0x67f3 | `sol_memcmp_` of 32 bytes (`add64 r2, -0x40` @0x67ee, `r3 = 0x20` @0x67ef) - a key comparison, **not** a memmove; unequal branch at 0x67fc materialises the rodata constants 0x100000000f0a098 / 0x553beb1adc39c4da |
| 2 | 0x6784 | raise tuple: `update_fee_shares_v2.rs:137` = 6024 `Reward split can only be updated once` |
| 3 | 0x686d | raise tuple: `update_fee_shares_v2.rs:152` = 6034 `quote_mint is not the bonding curve's quote mint` |
| 4 | 0x6ad5, 0x6b12 | `call 0x6e50` (671 insns) - the v2 shareholder path; 0x6e50 calls the allocator 0x1636 at 0x6f63, i.e. the `sol_memmove_` route |
| 5 | - | the other direct callees measured: 0x8932 (917), 0x8dca (149), 0x178c8 (26), 0x724e (140), 0x15a4e (17), 0x1652f (8), 0x17eb1 (1), 0x184e6 (8, memcmp), 0x7113 (295), 0x15a91 (65), 0x753b (386), 0x1ec6 (178), 0x250d (60), 0x6134 (597), 0x735a (153), 0x6e50 (671), 0x6b1e (786), 0x989 (132), 0x1424 (26), 0x176d7 (17) |

Status: **[partial]**, same reason as 4.4: helpers, raise lines and the quote-mint/shares-once
gates are measured; the arithmetic in 0x6e50 / 0x6b1e (the v2 shareholder and stable-leg
paths) is not yet walked. The previous revision's claim that the body calls `sol_memmove_` at
0x67f0 is withdrawn (§2.1.1).

### 4.6 `admin_cto_sharing_config` - 0x139e4 (byte 0x9cf20, 171 insns) **[B wrapper]**

`Instruction: AdminCtoSharingConfig` at 0x139e9; `try_accounts` 0xba35 (733, strings
`pool_authority`, `authority`, `global`, `mint`) at 0x13a21; helper 0x17148 (41) at 0x13a2a;
0x175c5 (68, formatting) at 0x13a40; 0x1275 (31) at 0x13a43; AnchorError ctor 0x1601e at
0x13a52; `memcpy` thunk at 0x13a5f; body 0x3e64 (586) at 0x13a77; packer 0x989 at 0x13a81.
Body status: **[B]** (reconstructed body closed in §15.5); measured: Location tuple `admin_cto_sharing_config.rs:86` =
6001 `Invalid admin` (tuple at 0x3f58), the string `a Display implementation returned an
error unexpectedly`, and the `__event_authority` rodata pointer 0xc3ec2.

Updated by §15.4: the gate order is measured (the argument is one `Option<Pubkey>`, tag byte
at record +0x00, 32-byte key at +0x01..0x20, matching the 41-byte CPI frame of
`docs/cpi_frames_all4.md:56`), the body holds exactly one raise (`Some(new_admin)` with the key
equal to 32 zero bytes: `sol_memcmp_` 0x184e6 at 0x3ebd, `jeq` to the 0x3f2a record, code word
0x1771 = 6001, line word 0x56 = 86, exit at 0x3f7b), and it rewrites five `SharingConfig` fields
before the wrapper hands the same value base (`accounts+0x98`, read again at 0x13a7b) to packer
0x989: `status` +0x58 (0x00 on `None`, 0x01 on `Some`), `admin` +0x38..0x57 (four zero words or
the argument key), `admin_revoked` +0x59 (0x01 or 0x00), the `shareholders` vector at
+0x00/+0x08/+0x10 (empty, or one 0x22-byte element `{key, 0x2710}` allocated at 0x3ee5), and
`version` +0x5b = 0x02 at 0x3ef8 for both branches. `bump` +0x5a and `mint` +0x18..0x37 are not
written. The reset then logs and CPIs `ResetFeeSharingConfigEvent` (serialiser 0xbd36, discriminator
cbcc97e27837d6f3 at 0xbd4f) with the signer seed `ctx.bumps.__event_authority` taken from ctx+0x22.
Updated by §15.5: the body is reconstructed line by line (the three pre-write snapshots of the
prologue, the `match` on the `Option` tag with its single `6001` raise, the five rewritten fields,
`version` = 2, and the `ResetFeeSharingConfigEvent` whose `new_admin` field is decided on a second
read of the tag), so no `[partial]` is left on this body. The three source-level names the bytes
cannot carry are listed once in §15.5 and none of them moves an offset.

### 4.7 `set_social_claim_authority` - 0x12eca (byte 0x97650, 188 insns) **[B wrapper]**

`Instruction: SetSocialClaimAuthority` at 0x12ecf; `fee_program_global` name string at
0x12f2d; `try_accounts` 0xa5d2 (548, strings `authority`, `fee_program_global`,
`fee_program_global`, `event_authority`) at 0x12ef9; `memcpy` thunk at 0x12f03; body 0x341d
(382) at 0x12f1b; writer 0xa0f (124) at 0x12f26; name formatter 0x2b1 at 0x12f30;
event-authority check 0x17148 at 0x12f53; AnchorError ctor 0x1601e at 0x12f61.

Body status: **[B]** (reconstructed body closed in §15.3); measured inside 0x341d: `__event_authority`
pointer 0xc3ec2, a callee set of one-hop account-flag reads, and **no** path-anchored raise tuple and
**no** code immediate, i.e. this body raises nothing of its own (§2.3). 0xa0f references the 8-byte
constant at 0xc3d97 (the `FeeProgramGlobal` discriminator region) and is the field writer for
the claim authority.

Updated by §15.1 and §15.2: the full call and branch sequence of `0x341d` is measured (seven
direct calls, `0x1621e` `Clock::get`, `0x175af` allocator, `0x15a5f` twice, `0x161a7`
`sol_log_data`, `0x16eb0` builder, `0x161ae` `invoke_signed`), and the writer `0xa0f` is
measured as a seven-append serialisation that fixes the `FeeProgramGlobal` account data at
`0x152` bytes with the new claim authority at `data[0x2a..0x49]`. Closed by §15.3: the
reconstructed Rust body, every line cited, plus the base-register naming correction (`r6` is the
accounts struct, whose first field is the `Account<FeeProgramGlobal>`).

### 4.8 `create_social_fee_pda` - 0x13a95 (byte 0x9d4a8, 194 insns) **[B]**

Wrapper, re-measured end to end this tick. `Instruction: CreateSocialFeePda` at 0x13a9a
(rodata 0xc52e4, len 0x1f); the instruction-data slice is parked at `[r5-0x1000]` / `[r5-0xff8]`
(0x13a9e..0x13aa1); the argument deserialiser is 0x1d11 (69 insns) at 0x13aa6, called with the
cursor `{ptr @fp-0x518, len @fp-0x510}`; an error is signalled with the sentinel
`i64::MIN` (0x13aa9/0x13aab). At 0x13aad the wrapper tests the **remaining** data length and, if
it is zero, takes the 0x13b23 path that calls 0x17148 (41) and then raises Anchor error
`0x66 = 102` (`InstructionDidNotDeserialize`) through 0x1601e at 0x13b34. If bytes remain, the
first remaining byte (`ldxb` at 0x13ab1) is carried to the body in `r4` (0x13aed): that byte is
the `platform: u8` argument. The accounts struct is produced by `try_accounts` 0xe4d2 (860) at
0x13ac3, memcpy'd by the `sol_memcpy_` thunk 0x184d9 at 0x13ad1, and the body is entered at
0x13aee with `(r1 = out, r2 = &entry-struct, r3 = &user_id String, r4 = platform)`.

Measured entry-struct layout (built at 0x13ad3..0x13ae2, object base `fp-0x298`): **[B]**

| off | content | writer |
|---:|---|---|
| 0x00 | `program_id` | 0x13ae1 |
| 0x08 | pointer to the accounts struct (`fp-0x518`) | 0x13ade |
| 0x10 | accounts slice ptr | 0x13adc (from `r3` at entry) |
| 0x18 | accounts slice len | 0x13ada (from `r4` at entry) |
| 0x20 | `bumps.social_fee_pda` | 0x13ad6 (copied from `fp-0x52a`) |
| 0x21 | `bumps.__event_authority` | 0x13ad8 (copied from `fp-0x529`) |

The `+0x10` / `+0x18` pair is the two entry registers `r3` / `r4` spilled by the wrapper
(0x13adc / 0x13ada); §6.1 reads the same two slots as a reader key/len pair, so their declared
name is **[partial]** while the stores themselves are **[B]**. The rest of the block agrees with
§6.1 (`+0x00` program id, `+0x08` accounts-struct pointer, `+0x20` the bumps block).

The two bump bytes are initialised to `0xff` (`sth [fp-0x52a], 0xffff` at 0x13ab3) and filled by
`try_accounts`, which is what pins them as the `Bumps` struct rather than account data **[B]**.
The accounts struct itself is the 0x280-byte object at `fp-0x518`: field 0 is the
`SocialFeePda` image (0x00..0xab, the same offsets the packer 0xa8d reads, §3.2) and the
remaining account fields sit at 0xb0 / 0xb8 / 0xe8 / 0x118 / 0x140 / 0x278 / 0x279 / 0x27c
(measured: 0xb0 and 0x118 hold `&AccountInfo` whose `key` at +0x00 is dereferenced at 0x5d13 /
0x5d1d; 0xb8..0xe2 is an `AccountInfo` with `lamports` Rc at +0xc0 and flags at +0xe0/+0xe1/+0xe2,
read at 0x5d38 / 0x5d9a..0x5da2) **[B]**.

`try_accounts` also copies the 0x98-byte tail of the account image into the struct
(`memcpy(r6+0x18, fp-0x120, 0x98)` at 0x0e807, where `r6` is the struct base) **[B]**: that is
`total_claimed @0x18`, `total_claimed_stable @0x20`, `last_claimed_at @0x28`, `_reserved
0x30..0xa8`, `bump @0xa8`, `version @0xa9`, `platform @0xaa`, i.e. exactly the 0x98 bytes the
body re-zeroes and rewrites.

#### 4.8.1 Body 0x5cd3 (byte 0x2e698, 389 insns) - measured sequence **[B]**

| # | insn | what the bytes do |
|---:|---|---|
| 1 | 0x5cd4 | `r7 = [r2+0x8]` - the accounts struct |
| 2 | 0x5cd5..0x5cd7 | `if [r7+0x279] & 1 != 0` -> log `CreateSocialFeePda is currently disabled` (0xc440a, len 0x28) at 0x5ce3 and `err!(21)` = **6021** `FeatureDeactivated` (0x8d8b, immediate `0x15` at 0x5ce6) |
| 3 | 0x5cd8..0x5cdf | `if [r7+0xa9] != 0` -> log `social_fee_pda already exists` (0xc43ed, len 0x1d) and return `Ok(())` (`mov64 r2, 2` at 0x5cde, exit stores 0x5cea/0x5ceb) |
| 4 | 0x5ced..0x5cef | `r1 = [r3+0x10]` = `user_id.len()`; `>= 0x15` jumps to the 6022 raise |
| 5 | 0x5cf0..0x5cf3 | save `r2` at `fp-0x1d0`; `bump = [r2+0x20]` -> `[r7+0xa8]`; `[r7+0xa9] = 1` |
| 6 | 0x5cf4..0x5cff | `0x17665` (90) clones the `String` into `fp-0x188`, copied to `[r7+0x00]`, `[r7+0x08]`, `[r7+0x10]` |
| 7 | 0x5d01 | `[r7+0xaa] = platform` (r8 = r4) |
| 8 | 0x5d02..0x5d06 | `sol_memset_(r7+0x18, 0, 0x90)` (0x184e1) - `total_claimed`, `total_claimed_stable`, `last_claimed_at` and the 120-byte reserve |
| 9 | 0x5d07..0x5d0b | `0x1621e` = `Clock::get()` into `fp-0xd0`; tag != 0 -> 0x5d80, where 0x15a5f (20) wraps the `ProgramError` and the body returns the error |
| 10 | 0x5d0c..0x5d12 | `r1 = [fp-0xa8]` = `unix_timestamp`; the 3 words of the `String` are re-staged to `fp-0x188..fp-0x178` |
| 11 | 0x5d13..0x5d25 | the 32-byte keys of the two `&AccountInfo` at `[r7+0xb0]` and `[r7+0x118]` are copied to `fp-0x168..fp-0x150` and `fp-0x148..fp-0x130` |
| 12 | 0x5d26..0x5d29 | `platform` -> `fp-0x128`; `unix_timestamp` -> `fp-0x170` (in-memory event order: `user_id @0x00`, `timestamp @0x18`, key1 `@0x20`, key2 `@0x40`, `platform @0x60`) |
| 13 | 0x5d2a..0x5d37 | `0xec2c` (132) = `try_to_vec` of the event (`called Result::unwrap() on an Err value` at 0xc44f3, panic path 0x178c8); then `sol_log_data(&[bytes])` via the 0x161a7 thunk, slice descriptor `fp-0x68` |
| 14 | 0x5d3f..0x5d40 | `r1 = [fp-0x1d0]` (the entry struct); borrow-overflow check on the `lamports` Rc at `[r7+0xc0]` (increment 0x5d3e, `abort` at 0x5d41 when it wraps) |
| 15 | 0x5d8e..0x5d97 | the same guard for the `data` Rc at `[r7+0xc8]` |
| 16 | 0x5d98..0x5d99 | `[fp-0x1d0] = [ctx+0x21]` - the `__event_authority` bump |
| 17 | 0x5d9a..0x5da8 | `executable`/`is_writable`/`is_signer` (`+0xe2..+0xe0`), `rent_epoch` (`+0xd8`), `owner` (`+0xd0`) staged, then a **second** `0xec2c` (`out = fp-0xe8`) over the same event block |
| 18 | 0x5dae..0x5dd1 | the bump allocator `0x300000000` / `0x300008000` allocates `len + 8` bytes; the 8-byte head constant `0x1d9acb512ea545e4` is written at 0x5dd0 |
| 19 | 0x5dd2..0x5ddf | the serialised event bytes are appended after that head |
| 20 | 0x5df8..0x5e00 | the 32-byte key staged from `[r8]` (= a `&AccountInfo` key) is copied to `+0x00` of a 0x22-byte `AccountMeta` and `sth [r1+0x20], 1` writes `is_signer = 1, is_writable = 0` |
| 21 | 0x5e08..0x5e0b | `0x16eb0` (118) builds the instruction with `program_id = 0xc4ead` |
| 22 | 0x5e0c..0x5e28 | the account list of the self-instruction: `__event_authority` (0xc3ec2, len 0x11) and `program` (len 1 slice at `fp-0x1000`), with signer seeds `[[b"__event_authority", bump]]` (`stdw [fp-0x30], 2` / `stdw [fp-0x20], 0x11` / `stxdw [fp-0x18], &fp-1` at 0x5e1d..0x5e27) |
| 23 | 0x5e33 | `0x161ae` (108) = the `invoke_signed` path (its callee 0x164a3 holds the `sol_invoke_signed_rust` syscall at 0x16502) |
| 24 | 0x5e34..0x5e47 | success sentinel `0x800000000000001a` (`lddw -0x7fffffffffffffe6`) -> drop the two borrows and return `Ok(())` |
| 25 | 0x5e4a..0x5e62 | otherwise `0x15a5f` (20) wraps the `ProgramError` into the `AnchorError` value and the body returns it |
| 26 | 0x5d42..0x5d7f | the 6022 raise: file 0xc43a5 = `programs/pump-fees/src/instructions/fee_sharing/create_social_fee_pda.rs` (len 0x48 = 72), line `0x43 = 67` (0x5d75), code `0x1786 = 6022` (0x5d73), boxed by 0x15a4e (17) at 0x5d7c |
| 27 | 0x5e63..0x5e6e | allocation-failure path: 0x175af (3) -> `panic_fmt` 0x17888 (9) |

`0x1d9acb512ea545e4` is the little-endian word of `e445a52e51cb9a1d`, the Anchor `emit_cpi!`
receive tag (`docs/cpi_graph.md` sec. "all handlers with `#[event_cpi]`") **[B: constant read at
0x5dd0, tag identity cross-checked against `docs/discriminators.md`]**.

#### 4.8.2 Reconstructed body

```rust
// programs/pump-fees/src/instructions/fee_sharing/create_social_fee_pda.rs
pub fn create_social_fee_pda(
    ctx: Context<CreateSocialFeePda>,
    user_id: String,
    platform: u8,
) -> Result<()> {
    // [B] 0x5cd5..0x5ce7
    require!(!feature_disabled(CREATE_SOCIAL_FEE_PDA), FeeError::FeatureDeactivated); // 6021
    // [B] 0x5cd8..0x5cdf
    if ctx.accounts.social_fee_pda.version != 0 {                    // [R] name, [B] offset 0xa9
        msg!("social_fee_pda already exists");
        return Ok(());
    }
    // [B] 0x5ced..0x5d7c
    require!(user_id.len() <= 20, FeeError::UserIdTooLong);          // 6022, line 67

    let pda = &mut ctx.accounts.social_fee_pda;                      // [B] r7 = accounts_struct+0
    pda.bump = ctx.bumps.social_fee_pda;                             // [B] [0xa8] <- [entry+0x20]
    pda.version = 1;                                                 // [B] [0xa9] = 1
    pda.user_id = user_id.clone();                                   // [B] 0x17665, [0x00..0x18]
    pda.platform = platform;                                         // [B] [0xaa]
    pda.total_claimed = 0;                                           // [B] memset 0x18..0xa8
    pda.total_claimed_stable = 0;
    pda.last_claimed_at = 0;
    pda._reserved = [0u8; 120];

    let now = Clock::get()?.unix_timestamp;                          // [B] 0x1621e, field fp-0xa8
    let event = SocialFeePdaCreated {                                // [R] field list: event_layouts.md
        timestamp: now,                                              // [B] fp-0x170
        user_id,                                                     // [B] fp-0x188..0x170
        platform,                                                    // [B] fp-0x128
        social_fee_pda: <key of the AccountInfo at accounts_struct+0xb0>,  // [B] key read 0x5d13
        created_by:     <key of the AccountInfo at accounts_struct+0x118>, // [B] key read 0x5d1d
    };
    emit!(event);                                                    // [B] 0xec2c + sol_log_data 0x5d37
    emit_cpi!(event);                                                // [B] tag 0x5dd0 + invoke_signed 0x5e33
    Ok(())
}
```

Notes for re-verification:
* The `user_id` `String` occupies `[0x00, 0x18)` of the in-memory image (pointer at +0x00,
  capacity at +0x08, length at +0x10): the body writes all three words at 0x5cfa..0x5cff and the
  packer 0xa8d reads the length from a register staged at 0x0aea. This agrees with §6.8 item 2,
  which reaches the same `[0x00, 0x18)` span from the two claim bodies; §3.2's
  "`user_id` occupies `[0x08, 0x18)`" row leaves the pointer word at +0x00 unassigned.
* The two 32-byte keys of the event are read from two `&AccountInfo` fields of the accounts
  struct (`+0xb0`, `+0x118`); which of them is `social_fee_pda` and which is `created_by` is
  **[B]** as of section 10.3 (the `+0xb0` slot is the account the `Account<T>` deserialiser
  consumes, the `+0x118` slot is the first fetched account), the addresses were already **[B]**.
* `[r7+0x279]` is a `u32` field of the accounts struct written by `try_accounts` at 0x0e843
  (`stxw [r6+0x279]`), and the body only tests its low bit; the value is the
  `FeeProgramGlobal` `disable_flags` word, which §6.1 pins **[B]** at `+0x271` in the two claim
  structs by the `disable_flags & 2` gate (0x40d3/0x430a); here the offset differs because the
  struct layout differs, and the bit test plus the raise are **[B]**.

---

### 4.9 `claim_social_fee_pda` - 0x13b5d (byte 0x9dae8, 248 insns) **[B wrapper]**

`Instruction: ClaimSocialFeePda` at 0x13b62; `social_fee_pda` name at 0x13c2f; 0x1d11 at
0x13b6e; `try_accounts` 0xbe2e (748, strings `social_fee_pda`, `recipient`,
`fee_program_global`, `social_claim_authority`) at 0x13b88; `memcpy` thunk at 0x13b96; body
0x40d1 (551) at 0x13bb0; second `memcpy` thunk at 0x13bbe; event-authority check at 0x13be2;
AnchorError ctor at 0x13bf1; 0xc685 (257) at 0x13c1c; 0x1621c (2) at 0x13c20; packer 0xa8d at
0x13c28; name formatter at 0x13c32; 0x175af (3) at 0x13c58; 0x178c8 (26) at 0x13c63.

Body status: **[B]**, with 6.3 and section 14 as the current reading (return type, exit census, block
map); this first pass measured inside 0x40d1: the messages `ClaimSocialFeePda is
currently disabled`, `Claim rate limit exceeded`, `No fees available to claim`, `Recipient
account is executable, so it cannot receive lamports`, the `unwrap()` message at 0x13c5c,
and `err!(FeeError::...)` disc `0x15` = 6021 at 0x40f1.

### 4.10 `claim_social_fee_pda_v2` - 0x13c64 (byte 0x9e320, 249 insns) **[B wrapper]**

`Instruction: ClaimSocialFeePdaV2` at 0x13c69; `try_accounts` 0xc131 (1199, strings
`social_fee_pda`, `quote_mint`, `associated_recipient`, `recipient`) at 0x13c90; `memcpy`
thunk at 0x13c9e; body 0x4308 (1303) at 0x13cba; second `memcpy` thunk at 0x13cc7; 0x1621c at
0x13ce7; 0xc607 (66, strings `social_fee_pda`, `quote_mint`) at 0x13ced; event-authority check
at 0x13cf3; AnchorError ctor at 0x13d02; 0xc685 at 0x13d2d; 0x1621c at 0x13d32; 0xc607 at
0x13d38; 0x175af at 0x13d5e; 0x178c8 at 0x13d69.

Body status: **[partial]**; measured inside 0x4308 the same four gate messages as 4.9 plus the
`quote_mint` account surface, i.e. the v2 body repeats the claim twice (SOL leg and stable
leg) with the same gate order, and `err!` disc `0x15` = 6021 at 0x4328.

### 4.11 `create_donation_fee_pda` - 0x14044 (byte 0xa0220, 113 insns) **[B]**

Wrapper: `Instruction: CreateDonationFeePda` at 0x14048 (0xc42xx family); account name string
`donation_fee_pda` at 0x1408b; `try_accounts` 0xcfe6 (1094) at 0x14058; `memcpy` thunk 0x184d9 at
0x14065; body 0x500a (1641) at 0x14079; packer 0xb3b (147) at 0x14084. The instruction takes no
arguments (no argument deserialiser call site in the wrapper, matching specs-fees §27).

#### 4.11.1 Body 0x500a (byte 0x28050, 1641 insns) - measured phases **[B]**

The accounts struct is `r7`. The `DonationFeePda` image is inline at `r7+0x278` (0xda bytes):
`config_id @0x2c0`, `base_mint @0x2e0`, `quote_mint @0x300`, `creator @0x320`,
`total_donated @0x340`, `last_crank_ts @0x348`, `bump @0x350`, `version @0x351`, i.e. the packer
0xb3b's source offsets shifted by 0x278 **[B: every store site cited below]**.

| # | insn | what the bytes do |
|---:|---|---|
| 1 | 0x500c..0x5021 | gate: `[r7+0x271] != 0` -> log `CreateDonationFeePda is currently disabled` (0xc42d7) and `err!(21)` = **6021** (0x8d8b at 0x501e) |
| 2 | 0x500f..0x5016 | `if [r7+0x351] != 0` -> log `donation_fee_pda already exists` (0xc42b8) and return `Ok(())` |
| 3 | 0x5024..0x5032 | account flags read through 0x368 / 0x58 / 0x110 and the flag bytes at 0xf0/0xe0/0xe8/0xd8 (signer, writable, executable of the accounts that follow) |
| 4 | 0x5033..0x503d | `RefCell` borrow guard, `abort` at 0x503d on overflow |
| 5 | 0x503e..0x5047 | `sol_memcmp_` of an `AccountInfo.owner` (pointer from `[r7+0x360]`, key at +0x18) against 0xc4f3c = `pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA` (the AMM program id); mismatch -> 0x529b -> **6008** `InvalidPool`, `create_donation_fee_pda.rs:148` (code `0x1778` at 0x52cd). So the pool owner check is the first pool gate. |
| 6 | 0x504b..0x5057 | `try_borrow_data` 0x16577 (15) and the slice length/shape test |
| 7 | 0x505f..0x5066 | `0x118f6` (82) = `Account<Pool>` deserialiser: length `>= 8`, discriminator word `0xbc6db111046d9af1` = little-endian `f19a6d0411b16dbc` (= `sha256("account:Pool")[:8]`), otherwise **3001** `AccountDiscriminatorMismatch` through 0x1601e (`mov64 r2, 0xbb9` at 0x11922); error branch -> 0x5260 |
| 8 | 0x5080..0x5092 | `0x1652f` (8) = `AccountInfo::data_len`; `jlt r0, 0x73` rejects a bonding curve shorter than 115 bytes -> 0x56c2 (`0x176d7` panic path) |
| 9 | 0x509b..0x50a8 | the curve's quote mint is read out of the serialised bytes: `ldxdw [r0+0x59]`, `ldxb [r0+0x61]`, `ldxw [r0+0x53]`, `ldxh [r0+0x57]`, `ldxdw [r0+0x62]`, `ldxb [r0+0x72]`, `ldxdw [r0+0x6a]`, i.e. the 32 bytes at serialised offset **0x53..0x73 = 83..115** (specs-fees §27) |
| 10 | 0x50d3..0x5118 | three key comparisons (`sol_memcmp_` at 0x50d3, 0x5101, 0x5115) that choose the curve path, the "quote mint absent -> WSOL" default and the pool path; the WSOL constant 0xc3740 (`So11111111111111111111111111111111111111112`) is materialised here |
| 11 | 0x511d..0x5164 | raise **6007** `InvalidSharingConfig` at `create_donation_fee_pda.rs:192` (tuple 0x520b, box 0x15a4e at 0x5217) and the `&AccountInfo` teardown 0x15a91 (65) at 0x5161 |
| 12 | 0x5167..0x519e | `sol_memcmp_` of the sharing-config `owner` against 0xc4ead (`pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ`, the program's own id) at 0x516a -> **6007** at `:197` (tuple 0x5250) |
| 13 | 0x51b8..0x51e9 | the successful write phase: `[r7+0x350] = [entry+0x21]` (bump), `[r7+0x351] = 1`, `config_id` 32 bytes at 0x2c0, `base_mint` at 0x2e0, `quote_mint` at 0x300, `creator` at 0x320, `total_donated = 0` (0x1e9), `last_crank_ts = 0` (0x1ea), reserve zeroed at `r6+0x00..0x40` (0x51e1..0x51e8) |
| 14 | 0x51ed..0x51fa | `Clock::get()` 0x1621e; tag != 0 -> 0x52f6 path, `0x15a5f` at 0x51fa wraps the error |
| 15 | 0x5243..0x525f | `0x16549` (11) = `data_is_empty`; then Anchor error **6007** at `:204` (tuple 0x5587) and `0x12f8` (68) as the error constructor variant |
| 16 | 0x527d..0x52b1 | `sol_memcmp_` against 0xc4ead and **6008** `InvalidPool` at `:156` (tuple 0x5539) |
| 17 | 0x5338..0x5388 | the event struct is written (`sth`/`stxdw` chain 0x534e..0x5381, in-memory field order key1 @0x18, key2 @0x38, ...) and logged with `sol_log_data` (0x161a7) at 0x5388 |
| 18 | 0x5412..0x5435 | the `emit_cpi!` buffer: tag `0x1d9acb512ea545e4` at 0x5412, a 0x22-byte `AccountMeta` with `is_signer = 1` at 0x543c/0x5441 |
| 19 | 0x544a..0x5475 | `0x16eb0` (118) builds the self-instruction with `program_id = 0xc4ead`, then `__event_authority` (0xc3ec2) and `invoke_signed` 0x161ae at 0x5475 |
| 20 | 0x548c..0x5505 | the pool branch: `0x16f53` (37) = `try_find_program_address` with the seed literal `pool-authority` (0xc4301) and `sol_memcmp_` at 0x552a -> **6008** at `:174` (tuple 0x5642) |
| 21 | 0x55af..0x55de | `0x16f7a` (56) = `create_program_address` with the seed `pool` (0xc3e0c) -> `0x8d8b` `err!` at 0x55d6 and **6007** at `:192`/`:204` family |
| 22 | 0x55e0..0x5668 | sharing-config validation: key compares against the pool base mint, `admin == payer` -> **6016** `NotAuthorized` at `:213` (tuple 0x55fc) and `config.status` -> **6018** `SharingConfigNotActive` at `:214` (tuple 0x56b1) |
| 23 | 0x5669..0x56c1 | final `err!` site (0x8d8b at 0x566f) for the non-pool creator mismatch and the panic path 0x56c2 (`0x176d7`) |

Raise table for the body, in source-line order (all **[B]**, tuple address -> file:line:code):
`:148` (0x52ca) 6008 `InvalidPool`, `:152` (0x54bb) 6008, `:156` (0x5539) 6008, `:174` (0x5642)
6008, `:192` (0x520b) 6007 `InvalidSharingConfig`, `:197` (0x5250) 6007, `:204` (0x5587) 6007,
`:213` (0x55fc) 6016 `NotAuthorized`, `:214` (0x56b1) 6018 `SharingConfigNotActive`, `:221`
(0x513e) 6016, and the unconditional `err!(21)` = 6021 `FeatureDeactivated` at 0x501e.

#### 4.11.2 Reconstructed body

```rust
// programs/pump-fees/src/instructions/fee_sharing/create_donation_fee_pda.rs
pub fn create_donation_fee_pda(ctx: Context<CreateDonationFeePda>) -> Result<()> {
    require!(!feature_disabled(CREATE_DONATION_FEE_PDA), FeeError::FeatureDeactivated); // 6021, 0x501e
    if ctx.accounts.donation_fee_pda.version != 0 {                                     // [B] 0xa9-of-image
        msg!("donation_fee_pda already exists");
        return Ok(());
    }
    if ctx.accounts.pool.owner != &PUMP_AMM_ID {                                        // [B] 0x5044
        return err!(FeeError::InvalidPool);                     // 6008, :148
    }
    let pool = Account::<Pool>::try_from(&ctx.accounts.pool)?;                           // [B] 0x118f6
    let curve_data = ctx.accounts.bonding_curve.try_borrow_data()?;                      // [B] 0x16577
    if curve_data.len() < 115 { /* 0x16d7 panic path 0x56c2 */ }                         // [B] 0x5081
    let quote_from_curve = Pubkey::new_from_array(curve_data[83..115]);                  // [B] 0x509b..0x50a8
    /* three further key comparisons at 0x50d3 / 0x5101 / 0x5115 select the branch */
    ...
    let d = &mut ctx.accounts.donation_fee_pda;                                          // [B] r7+0x278
    d.bump = ctx.bumps.donation_fee_pda;                                                 // [B] 0x51b8
    d.version = 1;                                                                       // [B] 0x51ba
    d.config_id = ctx.accounts.config_id.key();                                          // [B] 0x51c1..0x51c4
    d.base_mint = ctx.accounts.base_mint.key();                                          // [B] 0x51cb..0x51ce
    d.quote_mint = quote_mint;                     // curve bytes 83..115 or WSOL 0xc3740, [B] 0x509b / 0x51d6
    d.creator = creator;                                                                 // [B] 0x51d0..0x51d4
    d.total_donated = 0;                                                                 // [B] 0x51e9
    d.last_crank_ts = 0;                                                                 // [B] 0x51ea
    d._reserved = [0u8; 64];                                                             // [B] 0x51e1..0x51e8
    let now = Clock::get()?.unix_timestamp;                                              // [B] 0x51ed
    let event = DonationFeePdaCreated { timestamp: now, created_by, donation_fee_pda,
        config_id, base_mint, quote_mint, creator };                                     // [R] event_layouts.md
    emit!(event);         // [B] sol_log_data at 0x5388
    emit_cpi!(event);     // [B] tag 0x5412, invoke_signed 0x5475
    // sharing-config validation branch: [B] 0x548c..0x56c1, raises `:192/:197/:204` 6007,
    // `:213` 6016, `:214` 6018, `:221` 6016
    Ok(())
}
```

Status: **[partial]** on the branch *arithmetic* only, and that residue is narrowed in section
10.2 (the three `sol_memcmp_` sites carry their operands, the WSOL default is four inline
immediates, and the two sharing-config equalities carry their line and code). Measured and
citable: the phase order
above, every raise tuple with its file:line:code, the account-image offsets, the `Pool` and
`SharingConfig` deserialisers, the WSOL default, the two seed literals (`pool-authority`,
`pool`), the event log and the event CPI. Walked in section 10.2: the exact predicates of the
three key comparisons at 0x50d3/0x5101/0x5115 and of the sharing-config compares at
0x55e0..0x5668, with the accounts-struct slot each one reads and the raise line and code each
failure produces. The one point left open there is the declared Rust shape of the accounts slot
at `+0xb8`.

---

### 4.12 `crank_donation_fee_pda` - 0x140b8 (byte 0xa05c0, 104 insns) **[B]**

Wrapper: `Instruction: CrankDonationFeePda` at 0x140bc; `try_accounts` 0xc788 (1312) at 0x140cc;
`memcpy` thunk at 0x140d6; body 0x483d (1950) at 0x140f2; writer 0xcf6f (112) at 0x140fb
(strings `donation_fee_pda`, `donation_fee_pda_ata`, `quote_mint`). No arguments.

#### 4.12.1 Body 0x483d (byte 0x241e8, 1950 insns) - measured phases **[B]**

The accounts struct is `r8` at entry and `r7` after the first spill block. The
`DonationFeePda` image sits at `r6` (`r6 = [r8+0x360]`); the body writes `total_donated` at
`[r6+0xc8]` (0x4b67) and `last_crank_ts` at `[r6+0xd0]` (0x4c2d), i.e. the packer 0xb3b source
offsets of §3.3 **[B]**.

| # | insn | what the bytes do |
|---:|---|---|
| 1 | 0x483f..0x4841 | gate: `[r8+0x261] != 0` -> log `CrankDonationFeePda is currently disabled` (0xc4238) and `err!(21)` = **6021** (0x8d8b at 0x48c1) |
| 2 | 0x4843..0x4859 | 13 account-field borrows staged (0x48/0x50/0x58/0x60, 0x68/0x70/0x78/0x80, 0xa8/0xb0/0xb8/0xc0) - the CPI account list |
| 3 | 0x4868..0x486e | `sol_memcmp_` of the `quote_mint` key against 0xc3740 = WSOL; equal -> native branch 0x4b7b, unequal -> token branch 0x4bd2 |
| 4 | 0x4870..0x4871 | `if [r8+0x318] == 0` -> 0x4bd2 |
| 5 | 0x4879..0x48b8 | builds the log/anchor inputs for the branch that follows (`0x175c5` (68) formatter at 0x4890, `donation-fee-pda` literal 0xc41d8, `0x15a5f`/`0x8d8b` error paths, `abort` at 0x4b85 for the borrow guards) |
| 6 | 0x4b57..0x4b5d | `0x8718` (528 insns) - the largest helper in this body (its callees include 0x161ae); called once, before the amount accounting, with the 13-account list; returns a tag that must be `2` (`jeq r8, 2` at 0x4b5c) |
| 7 | 0x4b5f..0x4b67 | amount accounting: `r3 = [r6+0xc8]` (old `total_donated`), compare, `stxdw [r6+0xc8], r1` - `total_donated += amount` |
| 8 | 0x4b6a..0x4b77 | `Clock::get()` 0x1621e, `0x15a5f` error wrap |
| 9 | 0x4b9f..0x4bbe | `Rent::get()` 0x1623b (24), `Rent::minimum_balance` 0x16254 (47), `AccountInfo::lamports` 0x16520 (13), and the comparison that derives the surplus to move out of the PDA |
| 10 | 0x4bd2..0x4bf6 | `Nothing to donate` (0xc40e6) + return `Ok(())` path, and the `err!(0xf)` = **6015** site (0x8d8b at 0x4bf3) |
| 11 | 0x4e43..0x4e88 | the Tokenkeg `sync_native` instruction: a 0x40-byte instruction built at 0x4e57..0x4e83 (`sth ..., 0x100` metas) with data pointer 0xc4268 (the 32-byte buffer whose first byte is `0x11` = 17), then `0x153af` (224) at 0x4e88 = the PDA-signed invoke path |
| 12 | 0x4f1d..0x4f70 | `0x161a9` (5) = the plain `invoke` path (empty signer slice at `fp-0x1000`), then `try_borrow_data` 0x16577 and `0x14d4a` (110) = the SPL token-account reader; `jeq r3, 2` at 0x4f6a accepts the unpack |
| 13 | 0x4fd2..0x4fe5 | `sol_memcpy_` twice; the event fields land at `[r7+0x2d8]` / `[r7+0x2e0]` |
| 14 | 0x4fe7..0x4ff1 | `stxw [r7+0x360]` and the 5 stores at 0x364/0x36c/0x374/0x37c/0x384 - the `DonationFeePdaCranked` event record |
| 15 | 0x4c1d..0x4c2d | native-leg second half: `lamports` 0x16520, `0x15a5f` wrap, `stxdw [r6+0xd0], r5` - `last_crank_ts = now` |
| 16 | 0x4cc6 | `sol_log_data` (0x161a7) of the event built at 0x4c52..0x4cc5 |
| 17 | 0x4d51..0x4d8b | the `emit_cpi!` buffer: tag `0x1d9acb512ea545e4` at 0x4d51, a 0x22-byte `AccountMeta` with `is_signer = 1` at 0x4d7f, `0x16eb0` (118) at 0x4d8b |
| 18 | 0x4da0..0x4db3 | `__event_authority` (0xc3ec2) + `invoke_signed` 0x161ae at 0x4db3 |
| 19 | 0x4dde..0x4e09 | the second `Nothing to donate` path (0x4dde, 0x4e09) and the `lamports`/`try_borrow_data` pair that feeds it |

Raise/exit table: **6021** at 0x48c1 (`CrankDonationFeePda is currently disabled`), **6015** at
0x4bf3 (`err!` disc `0xf`), plus the two `Nothing to donate` early-`Ok(())` sites at 0x4bd2 and
0x4dde **[B]**. `discriminators`/error-name mapping of 6015 is from the recovered table §2.2
**[R]**.

#### 4.12.2 Reconstructed body

Between 0x4b57 and 0x4b7b the block layout is not the execution order: `0x8718` at 0x4b57 is
reached from the token branch, while the clock/rent block at 0x4b6a..0x4bbe belongs to the
native branch. The table above records the program counter of each measured step; the code
below records the dependency order the bytes imply.

```rust
// programs/pump-fees/src/instructions/fee_sharing/crank_donation_fee_pda.rs
pub fn crank_donation_fee_pda(ctx: Context<CrankDonationFeePda>) -> Result<()> {
    require!(!feature_disabled(CRANK_DONATION_FEE_PDA), FeeError::FeatureDeactivated); // 6021, 0x48c1
    let d = &mut ctx.accounts.donation_fee_pda;                                        // [B] [r8+0x360]
    let now = Clock::get()?.unix_timestamp;                                            // [B] 0x4b6a
    let rent = Rent::get()?;                                                           // [B] 0x4b9f
    let min = rent.minimum_balance(SIZE);                                              // [B] 0x16254
    if ctx.accounts.quote_mint.key() == &WSOL_MINT {                                   // [B] 0x4868
        // native leg
        let excess = ctx.accounts.donation_fee_pda.lamports() - min;                   // [B] 0x4bb5
        if excess > 0 {
            system_transfer(pda -> ata, excess)?;                                      // [B] transfer ix built 0x4c52.., invoke 0x161a9/0x153af
        }
        sync_native(ata)?;                    // [B] tag 17 buffer 0xc4268, invoke 0x153af at 0x4e88
    }
    let amount = read_ata_amount(&ctx.accounts.donation_fee_pda_ata)?;                 // [B] 0x16577 + 0x14d4a
    if amount == 0 { msg!("Nothing to donate"); return Ok(()); }                       // [B] 0x4bd2 / 0x4dde
    // [B] 0x4b57 0x8718 (528) builds and sends the relay instruction
    d.total_donated += amount;                                                         // [B] [r6+0xc8] 0x4b67
    d.last_crank_ts = now;                                                             // [B] [r6+0xd0] 0x4c2d
    let event = DonationFeePdaCranked { timestamp: now, signer, donation_fee_pda, config_id,
        base_mint, quote_mint, creator, amount };                                      // [R] event_layouts.md
    emit!(event);        // [B] sol_log_data 0x4cc6
    emit_cpi!(event);    // [B] tag 0x4d51, invoke_signed 0x4db3
    Ok(())
}
```

Status: **[partial]** on the relay payload, and that item is closed in section 10.1 (the
payload ladder, the relay program id, the 13-meta list with its literal flag words and the four
signer seeds are all measured). Measured: the gate, the WSOL branch, the rent/lamports
surplus computation, the `sync_native` data buffer (`0x11` = tag 17) and its PDA-signed invoke,
the SPL token amount read, both early-`Ok(())` exits, the state writes and the event log + event
CPI. Walked in section 10.1: the internal structure of `0x8718` (528 insns, the relay instruction
builder, the 13-account meta list and the invoke), so the relay payload is binary-grounded
rather than **[R]**.

---

### 4.13 Sublane C helper catalogue (new this tick)

Addresses are insn indices; every role below was measured from the callee's own bytes (syscall
names via `.rel.dyn`, rodata strings, argument shape at the call site).

| helper | insns | role as measured | evidence |
|---|---:|---|---|
| 0x8d8b | 59 | `err!(FeeError discriminant)` constructor, used by the three bodies for 6021 (both) and 6015 (crank) | `stxdw`/resolver 0x8dca + 0xa0-box 0x15a4e reachable; sites 0x5ce7, 0x501e, 0x48c1, 0x4bf3 |
| 0x8dca | 149 | FeeError message resolver (binary search over the 36 leaves) | §2.2 |
| 0x8932 | 917 | AnchorError message formatter (`core::fmt`) | sites 0x5d46, 0x511d, 0x52a3 |
| 0x12f8 | 68 | Location-tuple error constructor (`file`,`line`,`code`) into the 0xa0 `AnchorError` | sites 0x524f, 0x5538, 0x5586, 0x55b0, 0x5641 |
| 0x15a4e / 0x15a5f | 17 / 20 | `AnchorError` box (0xa0) / box + origin (0x80); 0x15a5f is the `ProgramError` wrap used for `?` propagation from `Clock::get` / `Rent::get` / `invoke_signed` | sites 0x5d7c, 0x5d8a, 0x5e4e, 0x51fa, 0x523d, 0x4b77, 0x4c28 |
| 0x1601e | 70 | `AnchorError` ctor by numeric code, used by the `try_accounts`/deserialiser paths (102, 3001) | 0x13b34, 0x11922, 0x0d875 |
| 0x161a7 | 2 | `sol_log_data` thunk | 0x5d37, 0x5388, 0x4cc6 |
| 0x161a9 | 5 | plain `invoke` (empty signer-slice at `fp-0x1000`) | 0x4f1d |
| 0x161ae | 108 | `invoke_signed` path; callee 0x164a3 holds the `sol_invoke_signed_rust` syscall at 0x16502 | 0x5e33, 0x5475, 0x4db3 |
| 0x1621e | 29 | `Clock::get()` (out `{tag, Clock}`), field order slot/epoch_start/epoch/leader_schedule_epoch/unix_timestamp | 0x5d09, 0x51ed, 0x4b6a |
| 0x1623b | 24 | `Rent::get()` | 0x4b9f |
| 0x16254 | 47 | `Rent::minimum_balance(len)`: `(len + 0x80)` bounds-checked at 0x16256/0x16258, u128 arithmetic through 0x18628/0x184ee/0x18676/0x184c1/0x18654 | 0x4bb1 |
| 0x16520 | 13 | `AccountInfo::lamports()` (borrow counter check, value at `[Rc+0x18]`) | 0x4bb5, 0x4c1d, 0x4e09 |
| 0x1652f | 8 | `AccountInfo::data_len()` | 0x5080 |
| 0x16549 | 11 | `AccountInfo::data_is_empty()` | 0x5243 |
| 0x16568 | 13 | `try_borrow_data` variant returning the slice descriptor | 0x4dcf, 0x4e16 |
| 0x16577 | 15 | `try_borrow_data` with the borrow counter increment | 0x504b, 0x4f57 |
| 0x16eb0 | 118 | instruction builder: takes a program id and a serialised data buffer, used for both self-instructions (event CPI) | 0x5e0b, 0x544d, 0x4d8b |
| 0x16f53 | 37 | `try_find_program_address` (`sol_try_find_program_address` at 0x16f61) plus the `PubkeyError` panic path 0x17888 | 0x551c |
| 0x16f7a | 56 | `create_program_address` (`sol_create_program_address` at 0x16f8f) with the seed-length guards at 0x16f7a/0x16f82 | 0x55d0 |
| 0x17665 | 90 | `Vec<u8>`/`String` clone (allocator + `sol_memcpy_`, `BorrowError` panic strings on the shared path) | 0x5cf9 |
| 0xec2c | 132 | `try_to_vec` of one value: `called Result::unwrap() on an Err value` (0xc44f3), `0x1af8` slice-range panics, `sol_memcpy_` 0x184d9; writes `{tag, ptr, len}` to the out slot | 0x5d2a, 0x5da8 |
| 0x118f6 | 82 | `Account<Pool>` deserialiser: `len >= 8`, discriminator word `0xbc6db111046d9af1` (= LE `f19a6d0411b16dbc`), error **3001** `AccountDiscriminatorMismatch` | 0x505f |
| 0xd848 | 83 | `Account<SharingConfig>` deserialiser, same shape with discriminator word `0x4b5d8c3800094ad8` (= LE `d84a0900388c5d4b`) | 0x54a1 |
| 0x153af | 224 | the PDA-signed invoke path used for `sync_native` (first constant argument 0xc4268 = the 32-byte `[0x11, 0...]` buffer) | 0x4e88 |
| 0x14d4a | 110 | SPL token-account reader called right after `try_borrow_data` of the ATA; its result tag is tested at 0x4f6a | 0x4f66 |
| 0x8718 | 528 | relay instruction builder and sender used once in the crank body before the state accounting | 0x4b57 |
| 0x175c5 | 68 | `fmt` formatting helper (`a formatting trait implementation returned an error`) | 0x4890 |
| 0x176d7 | 17 | `panic_fmt` trampoline used by the small accessors' borrow-failure path | 0x56c4, 0x508f, 0x5386 |
| 0x178c8 / 0x17888 | 26 / 9 | `panic` / `panic_fmt` | 0x5d63, 0x52bd, 0x5e6e |

Cross-checks worth recording:

* 8-byte discriminator immediates must be read **little-endian** in this build: `lddw r3,
  -0x43924eeefb92650f` is `0xbc6db111046d9af1` as an unsigned word, and its byte reverse is
  `f19a6d0411b16dbc` = `sha256("account:Pool")[:8]`. The same rule turns the crank/create event
  head `0x1d9acb512ea545e4` into `e445a52e51cb9a1d`, the Anchor `emit_cpi!` tag. Any future
  sentence in this file that quotes a discriminator as a `lddw` immediate should state which
  byte order it is in.
* `0xc4f3c` = `pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA` (pump_amm), `0xc4ecd` =
  `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P` (pump), `0xc4ead` =
  `pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ` (pump_fees, self), `0xc3740` =
  `So11111111111111111111111111111111111111112` (WSOL), `0xc4268` = 32 bytes `11 00 ...`
  (Tokenkeg tag 17 = `SyncNative`), `0xc3ec2` = `__event_authority`, `0xc4301` = `pool-authority`,
  `0xc3e0c` = `pool`, `0xc41d8` = `donation-fee-pda` (all decoded with `tools/SC_consts.py`).
* Tools added this tick (local, `tools/`): `SC_scan.py` (who references a rodata VA / a field
  offset; call census of one function), `SC_filter.py` (compacted structural skeleton of a body,
  with the `RefCell` borrow/drop boilerplate elided), `SC_consts.py` (32-byte rodata decode to
  base58 plus discriminator naming). Scratch walks used for this section:
  `scratch/walk_5cd3.txt`, `scratch/walk_500a.txt`, `scratch/walk_483d.txt`,
  `scratch/st_500a.txt`, `scratch/st_483d.txt`.

Sublane C open items (do not re-open the A/B handlers). All three are closed in section 10:
1. Walk `0x8718` (528) so the crank relay payload of specs-fees §28 is binary-grounded rather
   than **[R]**. **Closed in 10.1.**
2. Attribute the three key comparisons at 0x50d3 / 0x5101 / 0x5115 and the sharing-config
   compares at 0x55e0..0x5668 to concrete account fields. **Closed in 10.2.**
3. Resolve which accounts-struct field feeds each of the two 32-byte keys of the
   `SocialFeePdaCreated` event (`+0xb0`, `+0x118`). **Closed in 10.3.**
## 5. Open items (next tick)

1. Walk 0x6479 (669 insns) and 0x6e50 (671 insns) instruction by instruction: they hold the
   shareholder-set arithmetic, five of the six measured raise lines (258/259/269/291/292) and
   the only path to the allocator/memmove. That is the remaining blocker on 4.4 and 4.5.
2. Walk 0x73f3 (327) and 0x63a6 (202) to close the "apply + write" phase of both update bodies.
3. Walk 0x56c7 (1510), 0x500a (1641), 0x483d (1950), 0x4308 (1303) with the raise map of §2.3
   as the branch skeleton; the Location lines give the expected order.
4. Resolve the two pooled-string leaves (6003 / 6011) so the error table has no `format` row,
   and confirm the 6021/6015 disc mapping in 0x483d.
5. Close the `0x73`-byte gate of the `SharingConfig` loader 0x250d and the purpose of the
   zero-key comparison (0x253f).

Nothing in this file is a PR: it is a local handoff for binary re-verification.

---

## 6. SUBLANE B: `claim_social_fee_pda` / `claim_social_fee_pda_v2`

Scope of this section: the two claim handlers only (SUBLANE B of the P0 split). Bodies
`0x40d1` and `0x4308` are walked instruction by instruction; every helper they call is
listed with its deployed address and the evidence for its role. Tags as in the header
**[B] / [R] / [partial]**.

Tooling added for this walk (local, `tools/`): `fees_struct_view.py` (structure-only listing:
calls, rodata loads, struct accesses, constant stores, branches, with the frame-slot
plumbing dropped). Bodies were also dumped in full with `fees_walk.py`:
`0x40d1` = 551 decoded insns over `[0x40d1, 0x4308)`, `0x4308` = 1303 decoded insns over
`[0x4308, 0x483d)` (the next function start is the crank body `0x483d`) **[B]**.

### 6.1 Accounts-struct (ctx) offsets measured on the two claim bodies

The body receives `r2 = &Context` and dereferences `[r2+8]` to the in-memory copy of the
accounts struct (`ldxdw r7, [r2+8]` at `0x40d2` / `0x4309`; the wrapper copies that struct
with `memcpy` at `0x13b96` (616 bytes = `0x268`) and `0x13c9e` (664 bytes = `0x298`)
respectively) **[B]**. `Context` itself is the 8-word block the wrapper builds at `fp-0x40`:
`+0x00` program id, `+0x08` accounts-struct pointer, `+0x10`/`+0x18` reader key/len,
`+0x20` the `bumps` block (v1: one byte, `stxb [fp-0x20]` at `0x13b9c`; v2: two bytes,
`stxh [fp-0x20]` at `0x13ca4`), `+0x28..+0x38` the deserialised args **[B]**.

| ctx offset | width | measured use (insn) | claim | v2 | identity |
|---|---:|---|---|---|---|
| `+0x00..+0x18` | 0x18 | `user_id: String` (ptr/cap/len) written at `0x5cf6..0x5cff` in `create_social_fee_pda` | read `0x4308`-leg via `+0x8/+0x10` at `0x46ba/0x46bb` | yes | `social_fee_pda.user_id` **[B]** |
| `+0x18` | 8 | `+= amount` at `0x41b8` (claim), `0x459f` (v2 SOL leg) | yes | yes | `total_claimed` **[B]** |
| `+0x20` | 8 | read as the rate-limit base `0x40fd` / `0x4334`; written with `now` `0x41ba` / `0x45a1`, `0x4710` | yes | yes | `last_claimed_at` **[B]** |
| `+0x28` | 8 | `+= amount` at `0x470e` (v2 stable leg); read into the event `0x41e4` | yes | yes | `total_claimed_stable` **[B]** |
| `+0x30..+0xa8` | 0x78 | never touched by either claim body | - | - | `_reserved` **[R: §3.2]** |
| `+0xa8` / `+0xa9` / `+0xaa` | 1 each | `bump` (`0x46b9`), `version` (`0x5cf3` in create), `platform` (`0x41c2`, `0x45a9`, `0x46bf`) | yes | yes | `bump` / `version` / `platform` **[B]** |
| `+0xb0` | 8 (ptr) | `&AccountInfo(social_fee_pda)`; `lamports()` at `0x412c` / `0x4429`; lamport debit `0x4192..0x419d` | yes | yes | `social_fee_pda` account **[B]** |
| `+0xb8` | 0x30 inline | 48-byte `AccountInfo` copied into the CPI meta block at `0x4200`/`0x423e` | yes | - | `event_authority` **[B]** |
| `+0x118` | 8 (ptr) | executable flag `[+0x2a]` read at `0x4169` / `0x433f`; lamport credit `0x419e..0x41aa` | yes | yes | `recipient` **[B]** |
| `+0x120` | 8 (ptr) | `[+0x58]` -> 32-byte key compared with WSOL at `0x435a..0x4361`; `[+0x30]` byte read at `0x46f9` and passed as the `TransferChecked` decimals at `0x4700` (8.1) | - | yes | `quote_mint` **[B for the WSOL compare and for the decimals use]**, name **[R]** |
| `+0x128` | 8 (ptr) | borrowed for the ATA helper arg block `0x4369` / `0x46da` | - | yes | `associated_social_fee_pda` (IDL order) **[R]**, offset **[B]** |
| `+0x130` | 8 (ptr) | ATA helper arg block `0x4670` / `0x46e4`; event meta `0x46d6` | - | yes | `associated_recipient` **[R]**, offset **[B]** |
| `+0x138` | 8 (ptr) | ATA helper arg block `0x4393` / `0x46d6` | - | yes | `quote_token_program`, and `+0x140` `associated_token_program` **[B: §8.5]** |
| `+0x268` / `+0x290` | 8 | `claim_rate_limit` compared against `last + limit` at `0x40fb..0x4107` / `0x4332..0x433e` | yes | yes | `fee_program_global.claim_rate_limit` **[B]** |
| `+0x271` / `+0x299` | 1 | `disable_flags & 2` gate at `0x40d3/0x40d4` and `0x430a/0x430b` | yes | yes | `fee_program_global.disable_flags` **[B]** |
| `+0x278` | 8 (ptr) | 32-byte key copied into the event block at `0x41d5..0x41de` | yes | - | `social_claim_authority: Signer`, the event's third key **[B: §8.5]** |

The `fee_program_global` pod image sits inline in both structs; the v2 struct is 0x30 bytes
longer (664 vs 616) and every `fee_program_global` offset shifts by `+0x28`
(`0x271 -> 0x299`, `0x268 -> 0x290`, `0x278 -> 0x2a0`). That shift is 40 bytes = five 8-byte
account slots, i.e. exactly the five accounts v2 adds ahead of `fee_program_global`
(`quote_mint`, `associated_social_fee_pda`, `associated_recipient`, `quote_token_program`,
`associated_token_program`), which is independent evidence for the v2 declaration order
**[B for the shift]**, **[R for the five names]**; the remaining 8 bytes of struct growth are the
`system_program` slot v2 appends behind `social_claim_authority`, closed in 6.12 **[B]**.

### 6.2 `claim_social_fee_pda` wrapper - `0x13b5d` (byte `0x9dae8`, 248 insns) **[B]**

```rust
// programs/pump-fees/src/instructions/fee_sharing/claim_social_fee_pda.rs (handler)
pub fn claim_social_fee_pda(
    program_id: &Pubkey,                 // r2
    accounts: &[AccountInfo],            // r3 = ptr, r4 = len
    data: &[u8],                         // [parent_fp-0x1000] / [parent_fp-0xff8]
) -> ProgramResult {
    msg!("Instruction: ClaimSocialFeePda");                       // 0xc5303, len 0x1e, @0x13b62
    let mut cursor = data;                                        // reader @fp-0x618 (0x13b66..0x13b69)
    let args = ClaimSocialFeePdaArgs::deserialize(&mut cursor)?;  // 0x1d11 (69) @0x13b6e
    let bump_seed = -1i8;                                         // stb [fp-0x629], 0xff @0x13b78
    let ctx = ClaimSocialFeePdaAccountStruct::try_accounts(       // 0xbe2e (748) @0x13b88
        program_id, accounts, &mut cursor, &[bump_seed],
    )?;
    let ctx = memcpy_frame(ctx);                                  // 0x184d9, 0x268 bytes @0x13b96
    let res = claim_social_fee_pda_body(&ctx, &args, &bump);      // 0x40d1 (551) @0x13bb0
    match res {
        r if tag(r) == i64::MIN       => { /* Ok(None): no account write */ }        // 0x13bb4/0x13bb7
        r if tag(r) == i64::MIN + 1   => return Err(program_error(r)),               // 0x13bf8
        _ => {
            SocialFeePda::try_serialize(&ctx.accounts.social_fee_pda, ...)?;         // 0xa8d @0x13c28
            check_account_name("social_fee_pda")?;                                   // 0x2b1, 0xc4c41 len 0xe @0x13c32
        }
    }
    Ok(())
}
```

Measured wrapper details **[B]**: entry `mov64 r6, r5` at `0x13b5d` and the four spills
`0x13b5e..0x13b61`; the args deserialiser `0x1d11` returns its `Result` at `fp-0x398` and the
tag is compared with `i64::MIN` at `0x13b71`; `try_accounts` `0xbe2e` is called with
`(r1 = fp-0x398, r2 = program_id, r3 = &accounts, r5 = parent fp)` and its output struct is
copied with `memcpy(fp-0x600, fp-0x380, 0x268)` at `0x13b96`; the body is called with
`(r1 = fp-0x398, r2 = fp-0x40 /* &Context */, r3 = fp-0x18 /* &args */)` at `0x13bb0`; the
account writer is the `SocialFeePda` packer `0xa8d` at `0x13c28` with
`(out = fp-0x640, accounts = fp-0x618, crate::ID = 0xc4ead, program_id = r8)` and its failure
path formats the account name `social_fee_pda` (`0xc4c41`, len `0xe`) through `0x2b1` at
`0x13c32`; `0xc685` (257) is called at `0x13c1c` and `0x1621c` (2, `sol_set_return_data`)
at `0x13c20`.

### 6.3 `claim_social_fee_pda` body - `0x40d1` (byte `0x20688`) **[B]**

Block table, in execution order. `ctx` below is the accounts struct (`r7`).

| # | insns | measured operation |
|---:|---|---|
| 1 | `0x40d1`..`0x40d5` | `r7 = ctx`; `if ctx[0x271] & 2 != 0` -> disabled gate |
| 2 | `0x40ea`..`0x40f3` | `msg!("ClaimSocialFeePda is currently disabled")` (`0xc40b1`, `0x27`) then `err!` disc `0x15` = 6021 through the `0x8d8b` constructor |
| 3 | `0x40d6`..`0x40e9` | `Clock::get()` (`0x1621e`, `sol_get_clock_sysvar`) into `fp-0x238`; a syscall failure goes through `0x15a5f` (20) and returns the error result |
| 4 | `0x40fa`..`0x4107` | `now = clock.unix_timestamp`; `limit = ctx[0x268]`; `last = ctx[0x20]`; `next = last + limit` with an overflow guard; `if last != 0 && now < next` -> rate limit |
| 5 | `0x4151` | `msg!("Claim rate limit exceeded")` (`0xc4040`, `0x19`), then `Ok(None)` tag `i64::MIN` |
| 6 | `0x4108`..`0x412d` | 48-byte `AccountInfo` copy of `ctx[0xb0]` to `fp-0x238` + `Rc` clone of its lamports/data cells, `lamports()` via `0x16520` (13) -> `pda_lamports` |
| 7 | `0x413e`..`0x414d` | `Rent::get()` (`0x1623b`, 24) and the rent-exempt comparison block at `0x4141..0x4147` |
| 8 | `0x4155`..`0x4166` | `Rent::minimum_balance(179)` (`0x16254`, 47 insns, `mov64 r2, 0xb3` at `0x415d`) -> `rent_min`; `amount = pda_lamports - rent_min` with a borrow guard |
| 9 | `0x4167`/`0x4169` | `if pda_lamports <= rent_min` -> `msg!("No fees available to claim")` (`0xc4059`, `0x1a`) at `0x4298`, `Ok(None)` at `0x42a0` |
| 10 | `0x4169`..`0x416b` | `if ctx[0x118].executable != 0` -> `msg!("Recipient account is executable, so it cannot receive lamports")` (`0xc4073`, `0x3e`) at `0x429c` |
| 11 | `0x416c`..`0x419d` | lamport move out: `**[ctx[0xb0]].lamports -= amount` (`ldxdw`/`sub`/`stxdw` at `0x4192..0x419d`) |
| 12 | `0x419e`..`0x41aa` | lamport move in: `**[ctx[0x118]].lamports += amount` (overflow-guarded add at `0x41a0..0x41a9`) |
| 13 | `0x41ab`..`0x41b8` | `ctx[0x18] = ctx[0x18] + amount` with `checked_add` semantics (`jlt` guard `0x41b0`, `stxdw [r7+0x18]` at `0x41b8`) |
| 14 | `0x41b9`/`0x41ba` | `ctx[0x20] = now` |
| 15 | `0x41c0`..`0x41de` | three 32-byte keys staged for the event: `ctx[0xb0]` key, `ctx[0x118]` key, `ctx[0x278]` key |
| 16 | `0x41df`..`0x41ef` | event payload staged at `fp-0x1b8..-0x168`: `ctx[0x18]`, `ctx[0x28]`, `ctx[0xaa]`, the pre-move lamport values and four zeroed words |
| 17 | `0x41f0`..`0x41fb` | borsh serialise of the event (`0xc64d`, 48, which carries the `Result::unwrap()` panic text) into `fp-0xd0`, then `sol_log_data` (`0x161a7`) of one slice at `0x41fb` |
| 18 | `0x41fc`..`0x4204` | `ctx + 0xb8` (inline `event_authority` `AccountInfo`) copied to `fp-0x160`; `bump = Ctx.bumps.event_authority` read back from `[fp-0x318]+0x20` |
| 19 | `0x4205`..`0x421e` | second borsh pass `0x21dc` (139) over the event buffer |
| 20 | `0x421f`..`0x422e` | `alloc(0x22)` (`0x19e3`, 30) for one `AccountMeta`: 32-byte key + `is_signer = 1` at `+0x20`; `Vec` header `{ptr, len = 1, cap = 1}` at `fp-0x68` |
| 21 | `0x422f`..`0x4238` | `Instruction::new_with_borsh` (`0x16eb0`, 118; strings `Some`/`None`/`BufferTooSmall`/`Utf8Error`) -> instruction buffer at `fp-0xd0` |
| 22 | `0x4239`..`0x424c` | 48-byte account-meta block copied at `fp-0x68`; event-authority PDA seeds built: `"__event_authority"` (`0xc3ec2`, len `0x11`) + one bump byte, 2 seed entries |
| 23 | `0x424d`..`0x4257` | invoke with seeds: data slice at `[fp-0x1000]`, 1 account, `0x161ae` (108, the `sol_invoke_signed_c` wrapper) at `0x4257` |
| 24 | `0x4258`..`0x425c` | return check against the build's Ok tag `0x800000000000001a` (`lddw r1, -0x7fffffffffffffe6`); otherwise `0x42c3` -> `0x15a5f` -> error result |
| 25 | `0x426e`..`0x4272` | success value block: `memcpy(out, fp-0x238, 0xd8)` to the caller's return slot |
| 26 | `0x425d`..`0x4307` | `Rc` borrow-counter drops for every cloned cell, then `exit` at `0x40f9` |

Reconstructed body **[B for the operation order and every address; field predicates [partial]
where marked]**:

```rust
pub fn claim_social_fee_pda_body(
    ctx: &Context<ClaimSocialFeePda>,       // r2 -> [r2+8] = &accounts struct
    _args: &ClaimSocialFeePdaArgs,          // r3: user_id/platform are re-read from the account
    bumps: &Bumps,                          // Ctx+0x20 = bumps.event_authority
) -> Result<Option<u64>> {
    // 1. feature gate
    if ctx.accounts.fee_program_global.disable_flags & 2 != 0 {          // 0x40d3, 0x40d4
        msg!("ClaimSocialFeePda is currently disabled");                 // 0x40ea
        return Err(err!(FeeError::FeatureDeactivated));                 // 6021, disc 0x15, 0x40f0
    }

    // 2. rate limit
    let now = Clock::get()?.unix_timestamp;                              // 0x40d9
    let limit = ctx.accounts.fee_program_global.claim_rate_limit;        // ctx+0x268
    let pda = &mut ctx.accounts.social_fee_pda;
    if limit != 0 {                                                     // 0x40fc
        let next = pda.last_claimed_at.checked_add(limit).unwrap_or(u64::MAX); // 0x40fe..0x4104
        if pda.last_claimed_at != 0 && now < next {                      // 0x4106, 0x4107
            msg!("Claim rate limit exceeded");                           // 0x4151
            return Ok(None);                                             // tag i64::MIN, 0x42a0
        }
    }

    // 3. rent headroom
    let pda_lamports = ctx.accounts.social_fee_pda.lamports();           // 0x16520 @0x412c
    let rent_min = Rent::get()?.minimum_balance(SOCIAL_FEE_PDA_SPACE);   // 179 = 0xb3, 0x415d
    let amount = pda_lamports.saturating_sub(rent_min);                  // 0x415f..0x4166
    if pda_lamports <= rent_min {                                       // 0x4167
        msg!("No fees available to claim");                              // 0x4298
        return Ok(None);
    }
    if ctx.accounts.recipient.executable {                              // ctx+0x118 +0x2a, 0x4169
        msg!("Recipient account is executable, so it cannot receive lamports"); // 0x429c
        return Ok(None);
    }

    // 4. lamport move
    **ctx.accounts.social_fee_pda.try_borrow_mut_lamports()? -= amount;   // 0x4192..0x419d
    **ctx.accounts.recipient.try_borrow_mut_lamports()? += amount;        // 0x419e..0x41aa

    // 5. accounting
    pda.total_claimed = pda.total_claimed.checked_add(amount)            // ctx+0x18, 0x41ab..0x41b8
        .ok_or(FeeError::ShareCalculationOverflow)?;                     // [partial: 6015 is not raised here in v1]
    pda.last_claimed_at = now;                                          // ctx+0x20, 0x41ba

    // 6. event: log + self-CPI through the event authority
    let ev = SocialFeePdaClaimed {                                      // [partial: field names]
        social_fee_pda: ctx.accounts.social_fee_pda.key(),               // key #1, 0x41c0
        recipient: ctx.accounts.recipient.key(),                         // key #2, 0x41cb
        /* key #3 = ctx[0x278], identity [partial] */                    // 0x41d5
        total_claimed: pda.total_claimed,                                // ctx+0x18, 0x41df
        total_claimed_stable: pda.total_claimed_stable,                  // ctx+0x28, 0x41e4
        lamports_before: pda_lamports,                                   // 0x41e8/0x41ea
        platform: pda.platform,                                          // ctx+0xaa, 0x41e5
    };
    sol_log_data(&[&ev]);                                               // 0x161a7 @0x41fb
    let ix = Instruction::new_with_borsh::<_, _>(                        // 0x16eb0 @0x4238
        crate::ID,
        &ev,
        vec![AccountMeta { pubkey: event_authority_key, is_signer: true, is_writable: false }],
    );                                                                  // meta alloc 0x19e3 @0x4221
    invoke_signed(                                                      // 0x161ae @0x4257
        &ix,
        &[ctx.accounts.event_authority.clone(), ctx.accounts.program.clone()],
        &[&[b"__event_authority", &[bumps.event_authority]]],            // 0xc3ec2 + bump, 0x4245..0x424c
    )?;
    Ok(Some(amount))
}
```

Two points are deliberately marked uncertain:
* the success-path return: `0x426e` copies `0xd8` bytes from `fp-0x238` into the return slot,
  which does not fit a `Result<Option<u64>>`. The measured tags are `0x8000000000000000`
  (`i64::MIN`, the "no value" return used by the three early exits), `0x8000000000000001`
  (the error return) and `0x800000000000001a` (the Ok tag the `0x16568` / `0x16577`
  constructors emit) **[B]**. The declared return type of the body is therefore **[partial]**.
* which account key is staged third for the event (`ctx+0x278`) **[partial]**; the other two
  are pinned by the lamport transfer that precedes them.

### 6.4 `claim_social_fee_pda_v2` wrapper - `0x13c64` (byte `0x9e320`, 249 insns) **[B]**

Same wrapper shape as 6.2 with the v2 names and one extra step in the exit chain:

| insn | what it is |
|---|---|
| `0x13c69` | `msg!("Instruction: ClaimSocialFeePdaV2")` (`0xc3800`, `0x20`) |
| `0x13c8a` | args deserialiser out at `fp-0x3c8` |
| `0x13c90` | `try_accounts` `0xc131` (1199) |
| `0x13c9e` | `memcpy` `0x184d9` of `0x298` (664) bytes = the accounts struct |
| `0x13cba` | body `0x4308` with `(r1 = fp-0x3c8, r2 = fp-0x40, r3 = fp-0x18)` |
| `0x13cc7` | `memcpy` of `0xc0` bytes (the instruction buffer) |
| `0x13ce7`, `0x13d32` | `0x1621c` (2, `sol_set_return_data`) twice |
| `0x13cf3` | `0x17148` (41) event-authority / program check |
| `0x13d02` | `0x1601e` (70) the AnchorError ctor used by the constraint paths |
| `0x13d38` | `0xc607` (66) - the v2 account-exit chain, see 6.6 |

### 6.5 `claim_social_fee_pda_v2` body - `0x4308` (byte `0x21840`) **[B]**

Block table; `ctx` = accounts struct (`r7`).

| # | insns | measured operation |
|---:|---|---|
| 1 | `0x4309`..`0x430c` | `if ctx[0x299] & 2 != 0` -> disabled (same message `0xc40b1`, same `err!` disc `0x15` = 6021 at `0x4328`) |
| 2 | `0x4310`..`0x433e` | `Clock::get()` (`0x1621e` @`0x4310`); `limit = ctx[0x290]`; `last = ctx[0x20]`; `if last != 0 && now < last + limit` -> rate limit (`0x4346` message, `Ok(None)` at `0x434a`) |
| 3 | `0x433f`..`0x4345` | `ctx[0x118].executable` -> recipient-executable message (`0xc4073`) |
| 4 | `0x434d`..`0x4361` | `quote_mint` key (`ctx[0x120] -> [+0x58] -> key`) compared with WSOL (`0xc3740`) by `sol_memcmp_` `0x184e6` @`0x435d`; **equal -> native leg at `0x4406`, different -> token leg at `0x4362`** |
| 5 | `0x4406`..`0x444e` | native leg: `lamports()` `0x16520` @`0x4429` on `ctx[0xb0]`, `Rent::get()` `0x1623b` @`0x443d`, rent-exempt compare, `minimum_balance(0xb3)` `0x16254` @`0x4549` |
| 6 | `0x4549`..`0x4556` | `if pda_lamports > rent_min` else `msg!("No fees available to claim")` (`0xc4059`) at `0x4685`, and the executable re-check at `0x4554` |
| 7 | `0x4557`..`0x4593` | lamport move out/in (`0x457d..0x4593`), mirroring the v1 body |
| 8 | `0x4594`..`0x45a1` | `ctx[0x18] = ctx[0x18] + amount` (`0x459f`), `ctx[0x20] = now` (`0x45a1`) |
| 9 | `0x45a6`..`0x463e` | SOL-leg event: keys from `ctx[0xb0]`, `ctx[0x118]`, `ctx[0x2a0]`; borsh `0xc64d` @`0x45da`; `sol_log_data` `0x161a7` @`0x45e2`; `Instruction::new_with_borsh` `0x16eb0` @`0x461f`; invoke `0x161ae` @`0x463e`; return check against `0x800000000000001a` (`lddw` at `0x463f`) with the failure path at `0x47de` |
| 10 | `0x4362`..`0x43e0` | token leg part 1: borrow `ctx[0xb0]`, `ctx[0x128]`, `ctx[0x120]`; call `0x76be` (739) @`0x43d7` |
| 11 | `0x43e0`..`0x4460` | drop chains after the first ATA check; error at `0x44f`-region if the helper's tag is not 2 |
| 12 | `0x4475`..`0x44e8` | token leg part 2: same borrow set for `ctx[0x138]`/`ctx[0x120]`; call `0x76be` @`0x44d9` (second ATA) |
| 13 | `0x44fc`..`0x4512` | `0x16577` (15, `Result` constructor) @`0x44ff` and `0x14ecc` (129, SPL-token state unpack: `jeq len,0x163` / `jlt len,0xa5` at `0x14ed0`/`0x14ed1`) @`0x450f`; tag must be 2 |
| 14 | `0x4666`..`0x46b3` | token leg amount/limit path: `0x16577` @`0x466d`, `0x14ecc` @`0x467c`, `0x143e` (13) @`0x4682`, `msg!("No fees available to claim")` at `0x4685`, and the drop blocks that return the error result (`0x4690`, `0x46a0`, `0x46ab`) |
| 15 | `0x46b6`..`0x46d5` | stable-leg context: `bump = ctx[0xa8]`, `user_id` from `ctx[0x8]/[0x10]`, `slice.to_vec()` `0x1933` (33) @`0x46be`; seeds array built for `["social-fee-pda", user_id, &[platform], &[bump]]` (`0xc40d8` ptr + `0xe` len at `0x46ce`/`0x46d5`, platform `0x46bf`, bump `0x46d1`) |
| 16 | `0x46d6`..`0x46ef` | five `AccountInfo` copies for the invoke (`ctx[0x138]`, `ctx[0x128]`, `ctx[0x120]+0x58`, `ctx[0x130]`, `ctx[0xb0]`) and the `0xc0`-byte instruction buffer copy |
| 17 | `0x46f8`..`0x4703` | the PDA-signed token CPI: `0x14dba` (272) @`0x4700`, arguments `(out = fp-0x488, data = fp-0x2b0, len = r8, byte = ctx[0x120][0x30])`; the helper itself calls the invoke wrapper `0x161ae` at `0x14e0e` |
| 18 | `0x4704`..`0x4710` | `ctx[0x28] = ctx[0x28] + amount` (`0x470e`) and `ctx[0x20] = now` (`0x4710`) |
| 19 | `0x4711`..`0x47d6` | stable-leg event: keys from `ctx[0xb0]`, `ctx[0x118]`, `ctx[0x2a0]` and the quote mint key `ctx[0x120]+0x58`; borsh `0xc64d` @`0x4757`; `sol_log_data` @`0x475f`; `Instruction::new_with_borsh` @`0x479c`; invoke `0x161ae` @`0x47bb` |
| 20 | `0x47d7`..`0x483c` | error/drop tails and `exit` |

Reconstructed body:

```rust
pub fn claim_social_fee_pda_v2_body(
    ctx: &Context<ClaimSocialFeePdaV2>,
    _args: &ClaimSocialFeePdaV2Args,
    bumps: &Bumps,
) -> Result<Option<u64>> {
    if ctx.accounts.fee_program_global.disable_flags & 2 != 0 {          // ctx+0x299, 0x430a
        msg!("ClaimSocialFeePda is currently disabled");
        return Err(err!(FeeError::FeatureDeactivated));                 // 6021, 0x4328
    }
    let now = Clock::get()?.unix_timestamp;                              // 0x4310
    let limit = ctx.accounts.fee_program_global.claim_rate_limit;        // ctx+0x290
    let pda = &mut ctx.accounts.social_fee_pda;
    if limit != 0 && pda.last_claimed_at != 0
        && now < pda.last_claimed_at.saturating_add(limit) {             // 0x4334..0x433e
        msg!("Claim rate limit exceeded");                               // 0x4346
        return Ok(None);
    }
    if ctx.accounts.recipient.executable {                              // ctx+0x118, 0x433f
        msg!("Recipient account is executable, so it cannot receive lamports");
        return Ok(None);
    }

    // --- WSOL leg: identical to claim_social_fee_pda -------------------
    if ctx.accounts.quote_mint.key() == WSOL_MINT {                      // 0x434d..0x4361
        let pda_lamports = ctx.accounts.social_fee_pda.lamports();       // 0x16520 @0x4429
        let rent_min = Rent::get()?.minimum_balance(SOCIAL_FEE_PDA_SPACE); // 0x16254 @0x4549
        if pda_lamports <= rent_min {                                    // 0x4554
            msg!("No fees available to claim");                          // 0x4685
            return Ok(None);
        }
        let amount = pda_lamports - rent_min;
        **ctx.accounts.social_fee_pda.try_borrow_mut_lamports()? -= amount; // 0x457d..0x4587
        **ctx.accounts.recipient.try_borrow_mut_lamports()? += amount;      // 0x4588..0x4593
        pda.total_claimed = pda.total_claimed.checked_add(amount)?;       // ctx+0x18, 0x459f
        pda.last_claimed_at = now;                                       // ctx+0x20, 0x45a1
        emit_log_and_cpi(SocialFeePdaClaimed { .. });                    // log 0x45e2, cpi 0x463e
        return Ok(Some(amount));
    }

    // --- stable leg: two ATAs + PDA-signed token transfer --------------
    let social_ata   = &ctx.accounts.associated_social_fee_pda;          // ctx+0x128
    let recipient_ata = &ctx.accounts.associated_recipient;              // ctx+0x130
    check_ata(&ctx.accounts.quote_mint, &ctx.accounts.social_fee_pda,
              social_ata, /* ctx[0x138], ctx[0x120] */)?;                // 0x76be @0x43d7
    check_ata(&ctx.accounts.quote_mint, &ctx.accounts.recipient,
              recipient_ata, /* ctx[0x138], ctx[0x120] */)?;             // 0x76be @0x44d9
    let amount = token_account_amount(social_ata)?;                      // 0x14ecc @0x450f
    if amount == 0 {                                                     // 0x4666..0x4685
        msg!("No fees available to claim");
        return Ok(None);
    }
    let bump = ctx.accounts.social_fee_pda.bump;                         // ctx+0xa8, 0x46b9
    let seeds: &[&[u8]] = &[b"social-fee-pda",                       // 0xc40d8 len 0xe, 0x46ce/0x46d5
                            pda.user_id.as_bytes(),                  // ctx+0x8/+0x10, 0x46ba/0x46bb
                            &[pda.platform],                         // ctx+0xaa, 0x46bf
                            &[bump]];                                // 0x46d1
    spl_token_transfer_checked_signed(                                   // 0x14dba @0x4700
        /* 5 accounts: ctx[0x138], ctx[0x128], ctx[0x120]+0x58, ctx[0x130], ctx[0xb0] */
        amount, ctx.accounts.quote_mint.decimals,                        // ctx[0x120][0x30], 0x46f9
        seeds,
    )?;
    pda.total_claimed_stable = pda.total_claimed_stable.checked_add(amount)?; // ctx+0x28, 0x470e
    pda.last_claimed_at = now;                                           // ctx+0x20, 0x4710
    emit_log_and_cpi(SocialFeePdaClaimed { /* + quote_mint, lifetime_stable */ }); // log 0x475f, cpi 0x47bb
    Ok(Some(amount))
}
```

Measured caveat on the shape of this body: the compiler laid the two legs out in a
non-source order (the `quote_mint == WSOL` test at `0x4361` jumps *forward* to the lamport leg
at `0x4406`, and the token leg occupies `0x4362..0x4405` plus `0x4666..0x46b3`), so the branch
structure above is the one the bytes implement, not the order the blocks appear in `.text`
**[B]**.

### 6.6 Helpers reached from the two claim bodies

| helper | insn | byte | insns | measured role |
|---|---|---:|---:|---|
| `0x1d11` | `0x1d11` | `0xe888` | 69 | args deserialiser of `{user_id: String, platform: u8}` (both wrappers); strings `a Display implementation returned an error unexpectedly` |
| `0xbe2e` / `0xc131` | - | - | 748 / 1199 | `try_accounts` of the two accounts structs; name strings `social_fee_pda`, `recipient`, `fee_program_global`, `social_claim_authority` (v1) and `social_fee_pda`, `quote_mint`, `associated_recipient`, `quote_token_program`, `associated_token_program` (v2) **[B]** |
| `0x1621e` | - | `0xb2d60` | 29 | `Clock::get()` (`sol_get_clock_sysvar`) |
| `0x1623b` | - | `0xb2e40` | 24 | `Rent::get()` (`sol_get_rent_sysvar`) |
| `0x16254` | - | `0xb2f10` | 47 | `Rent::minimum_balance` (called with `r2 = 0xb3` = 179 = SocialFeePda space) |
| `0x16520` | - | `0xb2900` | 13 | `AccountInfo::lamports()` - reads `[+8]` lamports cell, borrow count at `[+0x10]`, returns the `u64` at `[[+0x18]]` |
| `0x16568` / `0x16577` | - | `0xb2b40` / `0xb2bb8` | 13 / 15 | `Result` constructors; both write the Ok tag `0x800000000000001a` (`-0x7fffffffffffffe6`) and a 2-word payload |
| `0x184d9` | - | `0xc26c8` | 4 | `sol_memcpy_` thunk, returns `dst` (r1) |
| `0x184e6` | - | `0xc2730` | 8 | `sol_memcmp_` thunk, sign-extended result; used for the WSOL compare (`r3 = 0x20`) |
| `0x161a7` | - | `0xb0d38` | 2 | `sol_log_data` |
| `0x161ae` | - | `0xb0dc0` | 108 | `sol_invoke_signed_c` wrapper (account-meta repack + single syscall); 2 call sites in each body |
| `0x16eb0` | - | `0xb8b80` | 118 | `Instruction::new_with_borsh` / borsh writer; strings `Some`, `None`, `BufferTooSmall`, `Utf8Error` |
| `0x21dc` | - | `0x10ee0` | 139 | second borsh/serialiser pass over the event buffer (call sites `0x421c`, `0x4603`, `0x4780`) |
| `0x19e3` | - | `0xcf18` | 30 | bump allocator `alloc(size, align)`; used for the single `AccountMeta` (0x22 bytes) |
| `0xc64d` | - | `0x63268` | 48 | borsh `to_writer` + `unwrap` (carries the `called \`Result::unwrap()\` on an \`Err\` value` panic text); call sites `0x41f3`, `0x4208`, `0x45da`, `0x45ef`, `0x4757`, `0x476c` |
| `0x8d8b` | - | `0x46c58` | 59 | `err!(FeeError)` constructor, called with the bare discriminant `0x15` (6021) at `0x40f1` and `0x4328` |
| `0x15a5f` | - | `0xad2f8` | 20 | program-error to return-value conversion (8 call sites per body) |
| `0x1ec6` | - | `0xf630` | 178 | account/instruction data copy + `ProgramError` conversion; carries the `ProgramError` name block |
| `0x17665` | - | `0xbb328` | 90 | `RefCell` borrow guard (`BorrowError` / `already borrowed` strings) for the later entries of the blob; the entry reached at `0x41bf` runs `0x17665..0x1767b` only and is an exact size `user_id` clone (section 14.5) **[B]** |
| `0x17148` | - | `0xb8a40` | 41 | event-authority / program guard (v2 wrapper `0x13cf3`) |
| `0xa8d` | - | `0x5468` | 170 | `SocialFeePda` packer (disc `8b6035112aa9ce96`, §3.2); v1 exit path |
| `0xc607` | - | `0x63038` | 66 | v2 account-exit chain: `0xa8d` at `0xc60f`, then a 32-byte `sol_memcmp_` `0x184e6` @`0xc617`, an owner check `0x15a40` @`0xc61d` and a key compare `0x16589` @`0xc622` on `ctx[0x120][+0x58]` (the `quote_mint` mint-type re-validation), then the account-name formatter `0x2b1` with `social_fee_pda` (`0xc4c41`) / `quote_mint` / `associated_social_fee_pda` (`0xc4c65`) |
| `0x76be` | - | `0x3b5f0` | 739 | `fee_sharing/mod.rs` helper reached twice per v2 body (`0x43d7`, `0x44d9`): raises 6029 `Account type not supported` at `mod.rs:299` and 6030 `Mint does not match quote mint` at `mod.rs:306`, with two further tuples at lines 273 and 278 without an immediate; internally validates with `sol_memcmp_` (`0x76e4/0x76f8/0x7700`), `0x15527` (62), `0x15a91` (65), `0x15ea0` (305), `0x16068` (242), `0x178c8` (26), `0x12f8` (68) and ends with `0x13c3` (97) twice, i.e. an ATA/mint/authority validation pair. Role name **[B]** after 6.10, where the four `require!` predicates of this helper are walked: associated-token address equality at `mod.rs:273` (code 2006), initialised-account gate at `mod.rs:278` (code 3012), token-program owner at `mod.rs:299` (code 6029), token account mint field at `mod.rs:306` (code 6030); the `0x7830` create leg is walked in 6.11 and issues an SPL associated-token-account `CreateIdempotent` CPI (data byte `0x01`, six metas, plain `invoke`) |
| `0x14dba` | - | `0xa6dd0` | 272 | PDA-signed token transfer: 5 `AccountInfo` copies (`0x14de6..0x14e02`), invoke wrapper `0x161ae` @`0x14e0e`, `0x151ad` (184) and `0x15a5f` result conversions. Reached once per v2 body @`0x4700` |
| `0x14ecc` | - | `0xa7660` | 129 | SPL-token state unpack: length dispatch `jeq r9, 0x163` / `jlt r9, 0xa5` at `0x14ed0`/`0x14ed1` (165-byte token account and the 0x163 form), then `0x152c4` (149) and a 0xa5-byte zeroed output image at `0x14f36..0x14f4e`. Call sites `0x450f`, `0x467c` |
| `0x1933` | - | `0xc998` | 33 | `slice.to_vec()`: bump allocator + `sol_memcpy_`, writes `{ptr@+0, len@+8, cap@+0x10}`; used to copy `user_id` for the PDA seeds @`0x46be` |
| `0x143e` | - | `0xa1f0` | 13 | 13-insn tag/drop helper on the token-leg result (call site `0x4682`) |
| `0x1621c` | - | `0xb10e0` | 2 | `sol_set_return_data` trampoline (v2 wrapper `0x13ce7`, `0x13d32`; v1 wrapper `0x13c20`) |

### 6.7 Gates and error sites measured in sublane B

| gate | condition site | message / code | return |
|---|---|---|---|
| feature deactivated | `0x40d3` (v1), `0x430a` (v2): `disable_flags & 2` | `msg!("ClaimSocialFeePda is currently disabled")` + `err!` disc `0x15` = **6021** `Feature is currently deactivated` (`0x40f1`, `0x4328`) | `Err` |
| claim rate limit | `0x40fb..0x4107` (v1), `0x4332..0x433e` (v2) | `msg!("Claim rate limit exceeded")` (`0xc4040` len `0x19`) | `Ok(None)` |
| recipient executable | `0x4169` (v1), `0x433f` (v2) | `msg!("Recipient account is executable, so it cannot receive lamports")` (`0xc4073` len `0x3e`) | `Ok(None)` |
| nothing to claim | `0x4167` (v1), `0x4554`/`0x4685` (v2) | `msg!("No fees available to claim")` (`0xc4059` len `0x1a`) | `Ok(None)` |
| ATA type / mint mismatch (v2) | `0x76be` @`0x43d7`, `0x44d9` | **6029** `Account type not supported` (`mod.rs:299`), **6030** `Mint does not match quote mint` (`mod.rs:306`) | `Err` |
| token transfer / unpack failure (v2) | `0x4701..0x4703`, `0x450f..0x4512` | propagation through `0x15a5f` / `0x1ec6` | `Err` |

The claim path never raises 6027: that code is the buyback rate limit, not this one, and the
claim's rate-limit branch is a plain `msg!` + early `Ok(None)` **[B]** (matches
`specs-fees/fees_specs.md` §25 **[R]**).

### 6.8 Measured corrections to earlier sections of this file

1. **`SocialFeePda` in-memory field order.** §3.2 lists the *serialisation* order as
   `total_claimed` (0x18), `total_claimed_stable` (0x20), `last_claimed_at` (0x28). The two
   claim bodies prove the **in-memory** triple is different: the rate limit reads
   `[ctx+0x20]` as the previous claim time (`0x40fd`, `0x4334`), the SOL leg writes `now` to
   `[ctx+0x20]` (`0x41ba`, `0x45a1`), and the stable leg accumulates into `[ctx+0x28]`
   (`0x470e`). So in memory `0x18 = total_claimed`, `0x20 = last_claimed_at`,
   `0x28 = total_claimed_stable`; the serialised order (0x18, 0x20, 0x28 in the packer
   ladder) is unchanged, and the names attached to rows 6/7/8 of §3.2 need swapping **[B]**.
2. **`user_id` in memory.** §3.2 leaves the in-memory `user_id` at `[0x08, 0x18)` as
   `[partial]`. `create_social_fee_pda` writes the three `String` words at `r7+0x0`,
   `r7+0x8`, `r7+0x10` (`0x5cfa..0x5cff`), and the v2 claim seeds read `ctx[0x8]` (len, also
   `ctx[0x10]`) at `0x46ba/0x46bb`, so the `String` occupies `[0x00, 0x18)` and the four `u8`
   live at `0xa8/0xa9/0xaa` + one pad byte **[B]**.
3. **§4.9 / §4.10 are superseded by 6.3 / 6.5.** The previous text gave "gate messages and a
   raise site" for the two claim bodies; both bodies are now walked block by block with the
   helper table of 6.6.
4. **The v1 body does not raise 6015.** The `err!` constructor is only reached once
   (`0x40f1`, disc 0x15), so `ShareCalculationOverflow` is not on this path; the overflow
   guards are silent (`mov64 r4, -0x1` style saturating results) **[B]**.

### 6.9 Open items for sublane B

Status after the section 8 walk (tick t_b66911d0): items 3 and 4 are closed on the deployed bytes,
item 2 is measured down to the byte layout of the returned record, item 1 is narrowed to a
single-writer chain and stays **[partial]** on the name only.
Closure map for the fine chunk queue:
item 2 is closed for the v1 body in section 14.1 to 14.7, item 1 in 8.5, item 3 in 8.2, item 4 in 8.1.
Item 3 is also closed at the predicate level in 6.10 (tick t_d333790d), which walks the comparison
chain into the two sites that carry no code immediate and resolves the code names from the deployed
resolver at `0x16068`.
The fine chunk queue that followed is closed as well: (B2-a) in 6.10, (B2-b) in 8.1, (B2-c) in 8.5,
(B2-d) in 6.11 and (B2-e) in 6.12, which is the closing walk of sublane B2 and leaves no open
**[partial]** item on `claim_social_fee_pda_v2`.

1. `ctx+0x278` (v1) / `ctx+0x2a0` (v2): pin the identity of the third pubkey in the event by
   walking the two `try_accounts` (`0xbe2e`, `0xc131`) store order.
2. The success-path return block (`memcpy(out, fp-0x238, 0xd8)` at `0x426e`): determine the
   declared return type of both bodies from the wrapper's use of the slot.
3. Inside `0x76be` (739 insns): the exact `require!` predicates of `mod.rs:273` and
   `mod.rs:278` (no code immediate) and its two `0x13c3` calls. Closed in 6.10.
4. `0x14dba` (272): name the SPL-token instruction it invokes (transfer vs
   transfer_checked) from its 8-byte discriminator immediate.

Nothing in this section is a PR: it is a local handoff for binary re-verification.

### 6.10 Item 3 closed: the two `require!` predicates inside `0x76be` (mod.rs:273, mod.rs:278)

8.2 pinned the four raise sites of this helper with their codes, `file:line:col` and the record each one
prints. What it left open is the branch chain that reaches the two sites which carry no program code of
their own, `mod.rs:273` and `mod.rs:278`. This walk closes that: every gate below is a cited comparison,
and every block named here has exactly one predecessor (census over the 739-insn range
`0x76be..0x79b5`, recomputed with `scratch/B2/preds.py` over an `sbftool dis` dump of that range).

**(a) The call ABI, measured at both call sites.** The v2 body calls this helper twice, `0x43d7` and
`0x44d9`, and stages the same six-word argument frame at the caller's `fp-0x1000`:

| slot | call 1, `0x43d7` (`associated_social_fee_pda`) | call 2, `0x44d9` (`associated_recipient`) |
|---|---|---|
| `r1` out | `fp-0x448` (`0x43cf`/`0x43d0`) | `fp-0x458` (`0x44d1`/`0x44d2`) |
| `r2` the ATA `AccountInfo` | `ctx+0x128` (`0x4369`, stored `0x4378`) | `ctx+0x130` (`0x4401`) |
| `r3` address of the wallet key pointer | `[ctx+0xb0]+0x00` (`0x436a`, stored `0x4387`) | `[ctx+0x118]+0x00` (`0x4402`, stored `0x448e`) |
| `r4` the 32 quote-mint key bytes | `[[ctx+0x120]+0x58]+0x00` (`0x4388`..`0x4392`) | same staging (`0x448f`..`0x4499`) |
| `r5` | `r10` (`0x43d5`), the frame the callee reads at `[r9-0x1000]`..`[r9-0xfd8]` | same |
| `[fp-0x1000]` | address of the quote_token_program key copy at `fp-0x2f8` (`0x4393`..`0x439c`, stored `0x43c4`..`0x43c6`) | same |
| `[fp-0xff0]` | `ctx+0x138` (`0x43bf`/`0x43c0`) | same |
| `[fp-0xfe8]` | `0` (`0x43ce` `stdw`) | `1` (`0x44d0` `stdw`) |
| `[fp-0xfe0]` / `[fp-0xfd8]` | `&ctx+0x2a0` / `&ctx+0x2a8` (`0x43c7`..`0x43cd`) | same |

One word differs between the two calls, the bool at the caller's `fp-0xfe8`, and it is what separates
the reachability of the two predicates below. **[B]**

**(b) `mod.rs:273` is the ATA address equality, code 2006.** The chain:

1. `0x76d5` `call 0x15527` (62 insns) derives 32 bytes into `fp-0x230`. The seed array it builds at
   `0x1554c`..`0x15557` holds three `0x20`-byte entries: slot `fp-0x90` (seed 0) points at the `r2`
   copy, slot `fp-0x80` (seed 1) at the `r4` copy, slot `fp-0x70` (seed 2) at the `r3` copy
   (`0x15554`/`0x15551`/`0x1554e` against the three copies made at `0x15534`/`0x1553c`/`0x15544`).
   The callee's `r2` is the wallet key copy, `r4` is `[caller fp-0x1000]` (quote_token_program key) and
   `r3` is the incoming `r4` (quote-mint key), so the seed order is wallet, token program, mint. The
   program id it derives under is the four `lddw` immediates at `0x15528`/`0x1552b`/`0x1552e`/`0x15531`
   stored at `fp-0xb0`, the 32 bytes `8c97258f4e2489f1bb3d1029148e0d830b5a1399daff1084048e7bd8dbe9f859`
   = `ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL` **[B: `tools/fees_b58.py --hex`]**. The call is
   therefore `get_associated_token_address_with_program_id(wallet, quote_mint, quote_token_program)`.
2. `0x76d6`..`0x76df` overwrite `fp-0x1f0` with the ATA's own key (loaded through the pointer at
   `[r2+0x00]`), then `0x76e0`..`0x76e4` run `sol_memcmp_(fp-0x1f0, fp-0x230, 0x20)` through the thunk
   `0x184e6`. **[B]**
3. `0x76e7` `jne r0, 0x0, +0x86` -> `0x776e` is the only predecessor of `0x776e`, the block that builds
   the `0xc3e64` record and calls `0x16068` (`0x776e`..`0x7784`); `0x7785` `jeq r0, 0x0, +0xa` ->
   `0x7790` is the only predecessor of the raise block, which stores `0x7d6` at `0x779f` and line
   `0x111` = 273 at `0x77a1` (8.2). **[B]**

So the predicate is the equality of the ATA account key with the derived associated token address, in
`require_keys_eq!` form: the wallet is `social_fee_pda` on the `0x43d7` call and `recipient` on the
`0x44d9` call, the mint and the token program are the same on both. Any substitution of the ATA account
reaches this site. **[B for the comparison, the seeds and the program id]**

**(c) `mod.rs:278` is the initialized-account gate, code 3012.** The chain:

1. `0x76f3` `ldxdw r6, [r6+0x18]` loads the owner pointer of the account in `r2` and `0x76f8` compares
   it with `0xc36a0`, which is 32 zero bytes (dumped), through `0x184e6`. `0x76fc`
   `jeq r0, 0x0, +0x53` -> `0x7750`, the only predecessor of that block. **[B]**
2. `0x76ee`/`0x76ef` had copied the caller's bool into `fp-0x308` (`ldxdw r1, [r9-0xfe8]`), and
   `0x7753`/`0x7754` test it: `jne r1, 0x0, +0xdb` -> `0x7830`, the only predecessor of that block.
3. With the bool clear, `0x7755`..`0x776c` build the `0xc3e24` record, call `0x16068`, and `0x776c`
   `jeq r0, 0x0, +0xea` -> `0x7857`, the only predecessor of the raise block, which stores `0xbc4` at
   `0x7866` and line `0x116` = 278 at `0x7868` (8.2). **[B]**

The predicate therefore reads "the account is initialized, or the caller asked for the missing-account
leg". For this handler the raise is reachable from the first call only, because `0x43ce` stages the bool
as `0` and `0x44d0` stages it as `1`: an empty `associated_social_fee_pda` fails with 3012 at
`mod.rs:278`, while the same condition on `associated_recipient` enters `0x7830`, runs the six-account
CPI at `0x798a` and loops back to the owner compare at `0x76fc`. **[B for the chain and the two
constants]**

**(d) The two neighbour predicates, with the compared operands cited.** 8.2 located both sites; the
values they compare were not named there.

* `mod.rs:299`, code 6029: `0x76fd`..`0x7700` run `sol_memcmp_([r2+0x18], [helper fp-0x2e8], 0x20)` and
  `0x7703` `jeq r0, 0x0, +0xc3` -> `0x77c7`, the accept leg. Helper `fp-0x2e8` holds the caller's
  `[fp-0x1000]`, the quote_token_program key: `0x76cc` overwrites `r4` with `[r9-0x1000]` before the
  store at `0x76d4`, while the incoming `r4` was preserved in `r5` at `0x76bf` and stored at `fp-0x2e0`
  by `0x76d2`. Reading both slots as the incoming `r4` would make this compare the account owner with
  the mint key, which the next row rules out. So 6029 is the owner-equals-token-program check on the
  token account. **[B]**
* `mod.rs:306`, code 6030: the token account data is unpacked at `0x77da` (`0x14ecc`, 129 insns) into
  `fp-0x1f0`, `0x77e4` copies its `+0x10`..`+0x88` tail to `fp-0xa8` and `0x77f0`/`0x77f1` add the two
  mint words, so the assembled image starts at `fp-0xb8`; `0x77f2` runs `sol_memcmp_(fp-0xb8,
  [fp-0x2e0], 0x20)` and `0x77fa` `jeq r0, 0x0, +0x1b6` -> `0x79b1` is the accept leg. `[fp-0x2e0]` is
  the incoming `r4`, the 32 quote-mint bytes from `[[ctx+0x120]+0x58]+0x00`, so 6030 is the token
  account's mint field against the quote mint. **[B]**

**(e) Both names move from [R] to [B]: the codes are resolved by the binary's own table.** `0x16068` is
the builtin `ErrorCode` resolver: `0x16068` `ldxw r1, [r1+0x0]`, a binary search on the code value, one
leaf per code of the form `lddw r1, <(ptr,len) pair>`, and the common tail `0x1619b`..`0x161a6` hands
the pair to `0x156a0`.

| code | search path | leaf | pair | text |
|---:|---|---|---|---|
| `0x7d6` = 2006 | `0x16069` (not `>0x7ed`) -> `0x1606a` (not `>0x7da`) -> `0x1606b` (`>0x7d0`) -> `0x16088` (`>0x7d5`) -> `0x160a0` (not `>0x7d7`) -> `0x160a1` `jeq r1, 0x7d6` | `0x16151` | `0xc9300` = `(0xc616d, 0x1f)` | `A seeds constraint was violated` = `ConstraintSeeds` **[B: `tools/fees_hex.py 0xc616d 31`]** |
| `0xbc4` = 3012 | `0x16069` (`>0x7ed`) -> `0x16072` (`>0xbb9`) -> `0x1607a` (`>0xbc3`) -> `0x16094` (not `>0xbc8`) -> `0x16095` (not `>0xbc5`) -> `0x16096` `jeq r1, 0xbc4` | `0x16160` | `0xc9650` = `(0xc6ae7, 0x3b)` | `The program expected this account to be already initialized` = `AccountNotInitialized` **[B: `tools/fees_hex.py 0xc6ae7 59`]** |

**(f) What stays [partial] in this helper.** Nothing after 6.11. The Rust spelling of the bool
parameter and of the two call sites is the one shape 6.11 measures on the bytes: one helper taking the
wallet or recipient `AccountInfo`, the candidate ATA `AccountInfo`, the quote mint key, the quote token
program key and a create-if-missing bool, with the `0x7830` leg issuing an associated-token-account
`CreateIdempotent` CPI when that bool is set (6.11).

Status of the three B2 items after this walk: (B2-a) closed here, (B2-b) closed in 8.1, (B2-c) closed in
8.5. The `0x7830` leg named in (f) as **[partial]** is closed in 6.11, which leaves no open item inside
`0x76be`.

### 6.11 Item (B2-d) closed: the `0x7830` leg issues ATA `CreateIdempotent`

6.10(f) left one name open inside `0x76be`, the instruction that the `0x7830` block hands to the
six-account invoke at `0x798a`. This walk measures it end to end: the program id, the data byte, the six
account metas with their flags, the signer slice the invoke passes, and the status branch that feeds the
result back into the validation loop. Range `0x76be..0x79b5` (739 insns, `scratch/B2/region_76be_739.txt`),
branch census over that range with `scratch/B2/preds.py`, builder dumped from
`scratch/B2/create_ix_0x15569.txt`.

**(a) Entry: the leg runs from the `associated_recipient` call only.** `0x7830` is the only target of
`0x7754 jne r1, 0x0, +0xdb`, and `r1` is `[helper fp-0x308]`, filled at `0x76ee`/`0x76ef` from the caller
word `[caller fp-0xfe8]`. 6.10(a) measured that word as `0` at `0x43ce` (call `0x43d7`,
`associated_social_fee_pda`) and `1` at `0x44d0` (call `0x44d9`, `associated_recipient`). An empty
`associated_social_fee_pda` therefore still fails at `mod.rs:278` with 3012 and never enters `0x7830`.
**[B]**

**(b) The instruction is built by one function behind a pair of five-instruction thunks, and the thunk is
what selects the data byte.**

| thunk | frame words staged | call | data byte |
|---|---|---|---|
| `0x15609`..`0x1560d` | `[fp-0x1000] = r5` (`0x15609`), `[fp-0xff8] = 0` (`0x1560a`), `r5 = r10` (`0x1560b`) | `0x1560c` -> `0x15569` | `0x00` |
| `0x1560e`..`0x15612` | `[fp-0x1000] = r5` (`0x1560e`), `[fp-0xff8] = 1` (`0x1560f`), `r5 = r10` (`0x15610`) | `0x15611` -> `0x15569` | `0x01` |

The helper calls the second one: `0x784b call 0x1560e`. **[B]**

**(c) The data is exactly one byte, value `0x01`.** `0x15569` reads the thunk flag back out of the thunk
frame: `0x15581 stxdw [r10-0x108], r5` saves the frame pointer the thunk passed in `r5`, `0x155b7`
`0x155b8` load `[that frame -0xff8]` into `[helper fp-0x108]`. The write is `0x155ec`/`0x155ed`
(`r1 = 1`, `r2 = 1`) into the bump allocator `0x142d0`, then `0x155f3` `ldxdw r1, [r10-0x108]` and
`0x155f4 stxb [r0+0x0], r1`. The pointer lands at `[out+0x20]` (`0x15602`) and the length pair at
`[out+0x18]`/`[out+0x28]` is set to `1` (`0x15604`, `0x15605`). The out struct is `fp-0xb8`
(`0x7844`/`0x7845`). The invoke path reads those same words back: `0x164db ldxdw r9, [ix+0x20]` (data
pointer) and `0x164dc ldxdw r6, [ix+0x28]` (data length), then copies `r6` bytes at `0x164e7`..`0x164eb`.
So this CPI carries a single data byte, `0x01`; the `0x15609` twin carries `0x00`. **[B]**

**(d) Program id.** The four `lddw` at `0x155f5`, `0x155f9`, `0x155fc`, `0x155ff`, stored at `[out+0x30]`
to `[out+0x48]` (`0x155f8`, `0x155fb`, `0x155fe`, `0x15601`), are the same 32 bytes as the address
derivation at `0x15527` (`0x15528`/`0x1552b`/`0x1552e`/`0x15531`): memory order
`8c97258f4e2489f1`, `048e7bd8dbe9f859`, `0b5a1399daff1084`, `bb3d1029148e0d83` =
`ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL` **[B: `python3 tools/fees_b58.py --hex
8c97258f4e2489f1bb3d1029148e0d830b5a1399daff1084048e7bd8dbe9f859`]**. The invoke path carries it from
`[ix+0x30]` (`0x164e6 add64 r7, 0x30`).

**(e) The ATA in meta 1 is derived inside the builder.** `0x155a6 call 0x16f53` is a 14-insn
`find_program_address` shim: bump start `0xff` at `0x16f59`, 32-byte out at `fp-0x38`, seeds pointer,
seed count, program id and out passed in `r1..r4` (`0x16f5a`..`0x16f60`). The three seeds are the
(ptr,len) pairs staged at `0x15595`/`0x1559c` (`fp-0x70`, len `0x20`), `0x15598`/`0x1559d` (`fp-0x80`),
`0x1559b`/`0x1559e` (`fp-0x90`), pointing at three 32-byte copies: `fp-0x20` from `r7` = argument 4
(`0x1558b`..`0x15592`), `fp-0x40` from `r6` = `[[thunk frame -0x1000]]` (`0x15582`..`0x1558a`, the quote
token program key), `fp-0x60` from `r8` = argument 3 (`0x15579`..`0x15580`, the wallet key). The program
id it derives under is the ATA constant at `fp-0xb0` (`0x1556d`..`0x15578`). The result is copied at
`0x155a7`..`0x155ae` to `fp-0xf8..fp-0xe0` and then into meta 1 at `0x155bb`..`0x155c1`. So the seed
order is wallet, quote token program, quote mint under the ATA program id, which is the canonical
associated token address derivation. **[B]**

**(f) The six metas, with the field order and the stride measured on the invoke side.** One `0xcc`
allocation at `0x155af`/`0x155b0`/`0x155b1` (`r1 = 0xcc`, `r2 = 1` -> `0x142d0`) is six entries of
`0x22` bytes. The stride is confirmed twice on the consumer: `0x161ba mul64 r1, 0x22` for the metas and
`0x161bf mul64 r1, 0x30` for the account infos, and the flags are read as `is_signer` at `+0x20` and
`is_writable` at `+0x21` (`0x164c9 ldxb r7, [r9+0x20]`, `0x164ca ldxb r8, [r9+0x21]`).

| meta | offset in the block | pubkey, measured source | flag store | signer / writable | role |
|---:|---:|---|---|---|---|
| 0 | `0x00` | argument 2 of `0x1560e` = helper `fp-0x210`, filled at `0x7833`..`0x783a` from `[[ctx+0x2a0]+0x0]` (`0x7830`, `0x7831`); that ctx slot is `social_claim_authority` (8.5) | `0x155cc sth [r9+0x20], 0x101` | 1 / 1 | payer |
| 1 | `0x22` | the derived associated token address, (e) | `0x155cb sth [r9+0x42], 0x100` | 0 / 1 | the associated token account to create |
| 2 | `0x44` | argument 3 = helper `fp-0x1f0`, filled at `0x783c`..`0x7843` from `[helper fp-0x2f8]`, which is the wallet key pointer stored at `0x76e9` from helper `r3` (`0x76c3`) | `0x155d5 sth [r9+0x64], 0x0` | 0 / 0 | the ATA owner: `social_fee_pda` on `0x43d7`, `recipient` on `0x44d9` |
| 3 | `0x66` | argument 4 = helper `fp-0x2e0` = the incoming `r4`, the 32 quote mint bytes (6.10(d)) | first bytes of the zero run, `0x155de stdw [r9+0x86], 0x0` | 0 / 0 | quote mint |
| 4 | `0x88` | 32 zero bytes, `0x155de`..`0x155e2` = `11111111111111111111111111111111` **[B: `tools/fees_b58.py --hex` over 64 zero digits]** | rest of the same zero run | 0 / 0 | system program |
| 5 | `0xaa` | `r6` = `[[thunk frame -0x1000]]` = the helper `r5`, which `0x7832 mov64 r5, r2` set to `[helper fp-0x2e8]` = the quote token program key pointer stored at `0x76d4` from `[caller fp-0x1000]` | `0x155eb sth [r9+0xca], 0x0` | 0 / 0 | quote token program |

The zero run `0x155de`..`0x155e2` is one contiguous 36-byte write (`stdw` at `0x155de`, `0x155df`,
`0x155e0`, `0x155e1` and `stw` at `0x155e2`) covering meta 3's two flag bytes, all 32 bytes of meta 4's
pubkey and meta 4's two flag bytes. Every flag pair is a 16-bit store of `0x101`, `0x100` or `0x0`, so
the low byte is `is_signer` and the high byte is `is_writable`. **[B]**

**(g) The six `AccountInfo` images are paired positionally with those metas.** `0x7983`..`0x798a` stage
`r1 = fp-0xd0` (status out), `r2 = fp-0xb8` (the instruction image), `r3 = fp-0x1f0` (the account-info
array) and `r4 = 6` (`0x7989`). The array is six `0x30`-byte images at `fp-0x1f0`, `fp-0x1c0`,
`fp-0x190`, `fp-0x160`, `fp-0x130`, `fp-0x100`, assembled by the copy sequences `0x7873`..`0x7982`. The
wrapper pairs them by position with the metas and asserts the pairing: `0x161cf ldxdw r2, [r7+0x30]`
then `0x161d2 call 0x184e6` compares the meta pubkey with the key of the info at that slot, advancing
`0x161cb add64 r6, 0x22` and `0x161d4 add64 r7, 0x30` together. So the roles in (f) are the roles of the
six accounts in the CPI. **[B]**

**(h) The invoke is a plain `invoke`, with no PDA signature.** `0x161a9` stages `stdw [fp-0x1000], 0x8`
and `stdw [fp-0xff8], 0x0` before entering `0x161ae`, which forwards both into the syscall frame
(`0x1620b`..`0x1620e`), and `0x164a3` loads them into `r4` (`0x16500`) and `r5` (`0x16501`) immediately
before `0x16502 call ;; SYS sol_invoke_signed_rust`. `r5` is the signer-seed count and it is `0`, so the
create is not signed by a program derived address. That is why the payer in meta 0 has to be the real
signer `social_claim_authority`. **[B]**

**(i) Status branch back into the validation loop.** `0x798b` loads `0x800000000000001a` and `0x798d`
reads the status word at `fp-0xd0`; that constant is the Ok tag the syscall path writes on success
(`0x16504`/`0x16506 stxdw [r2+0x0], r1`). Equal takes `0x7990`..`0x7994`: `r1 = fp-0x1f0`, `0x7992
call 0x13c3` drops the account-info array, and `0x7994 ja -0x298` returns to `0x76fd`, the
`mod.rs:299` owner compare of 6.10(d). Not equal takes `0x79a0`..`0x79af`, which formats the status
through `0x15a5f` and returns through the common exit at `0x77c3`. A failed create therefore aborts the
helper and a successful one continues into the same validation chain, which is what lets the second call
create the account and still be checked for owner and mint right after. **[B]**

**(j) Names.** Data `0x01` with this six-account list is the associated-token-account `CreateIdempotent`
instruction: the program id is the ATA program, the payer is meta 0, the account to create is the derived
address, then the wallet, the mint, the system program and the token program, all read only. That is the
`create_associated_token_account_idempotent(payer, wallet, mint, token_program)` constructor of the SPL
associated-token-account crate. The helper wraps it as "create the account when the caller asked for it
and it does not exist yet", and because the variant is the idempotent one, a concurrent create by another
transaction cannot make this leg fail with `AccountAlreadyInUse`. **[R for the upstream constructor
name, B for the measured facts in (a) to (i)]**

**Status of sublane B2 after this walk:** (B2-a) closed in 6.10, (B2-b) closed in 8.1, (B2-c) closed in
8.5, (B2-d) closed here, (B2-e) closed in 6.12. `0x76be` and its helper set carry no open **[partial]**
item, and the `claim_social_fee_pda_v2` handler stands measured from wrapper `0x13c64` through body
`0x4308`, token helper `0x76be` and SPL-token helper `0x14dba`.

### 6.12 Item (B2-e) closed: the residual 8 bytes are the `system_program` slot at `ctx+0x2a8`

6.1 fixed the `+0x28` shift of `fee_program_global` as five 8-byte account slots and left the last 8
bytes of struct growth **[partial]**. This walk names them. Evidence: both `try_accounts` bodies dumped
whole for this tick, `scratch/B2/ta_v1_be2e.txt` (748 insns from `0xbe2e`) and
`scratch/B2/ta_v2_c131.txt` (1199 insns from `0xc131`), plus the two wrappers and the two bodies.

**(a) The two totals, re-measured.** v1 wrapper `0x13b93`/`0x13b94` stage `r2 = fp-0x380` and
`r3 = 0x268`, then `0x13b96 call 0x184d9`. v2 wrapper `0x13c9b`/`0x13c9c` stage `r2 = fp-0x3b0` and
`r3 = 0x298`, then `0x13c9e call 0x184d9`. 616 against 664, growth `0x30` = six 8-byte slots **[B]**.

**(b) The pod moves by exactly `+0x28`.** v1 `0xc0fa`..`0xc0ff` copies `0x138` bytes from `fp-0x1f8`
to `r6+0x138`. v2 `0xc5cb`..`0xc5d0` copies the same `0x138` bytes from `fp-0x2a0` to `r6+0x160`. The
destination moved by `0x160 - 0x138 = 0x28`, so the five token accounts sit ahead of
`fee_program_global` **[B]**.

**(c) The tail behind the pod grows by one word.** v1 writes one byte at `r6+0x270` (`0xc10b`, source
`fp-0x620`) and one word at `r6+0x278` (`0xc10d`, source `fp-0x650`, which `0xbef2` filled with the
result of the `social_claim_authority` step at `0xbeb9`, the slot 8.5 names). v2 writes one byte at
`r6+0x298` (`0xc5da`), one word at `r6+0x2a0` (`0xc5de`, source `fp-0x840`, filled at `0xc236` from the
`0x21c6` fetch, the `Signer` path of 8.5(b)) and one word at `r6+0x2a8` (`0xc5dc`). The first two v2
writes are v1's tail shifted by `0x28` (`0x270 + 0x28 = 0x298`, `0x278 + 0x28 = 0x2a0`), and the third
has no v1 counterpart. `0x28` ahead of the pod plus `0x8` behind it is exactly the `0x30` growth **[B]**.

**(d) That extra word is `system_program`.** Its only writer is `0xc5dc` `stxdw [r6+0x2a8]`, which
loads `[fp-0x850]`, and that slot is filled at `0xc23f` from the fetch at `0xc23a call 0x235b`. The
fetch is a `Program` monomorph: `0x236b`..`0x236e` zero 32 bytes at `fp-0x40`, `0x2374 call 0x184e6`
compares the account key with that zero run, and `0x2378 ldxb r1, [r8+0x2a]` requires the executable
byte. Its one failure exit is `0xc27f`..`0xc284`, which formats `0xc4a3a` len `0xe`, the 14 bytes of
`system_program` **[B: `tools/fees_hex.py 0xc4a3a 14`]**. The v2 body takes the address of that slot at
`0x43cb` (`add64 r1, 0x2a8`) and hands it to helper `0x76be` at `0x43cd` (`stxdw [fp-0xfd8], r1`),
beside `&ctx+0x2a0` staged at `0x43c7`..`0x43c9` **[B]**.

**(e) Why v1 carries no such slot.** v1 declares six accounts and none of them is a system program
(8.5(c)), and its native leg moves lamports by direct arithmetic (`0x4192`..`0x41aa`) with no CPI, so
the slot has no reader there. v2 declares twelve accounts, six of them new: `quote_mint`,
`associated_social_fee_pda`, `associated_recipient`, `quote_token_program` and
`associated_token_program` ahead of `fee_program_global`, and `system_program` behind
`social_claim_authority`. Six new 8-byte slots against `0x30` growth closes the accounting with nothing
left over **[B for the offsets, the writes and the count]**, **[R for the IDL names]**.

**(f) The two superseded 6.1 rows, restated in place.** The `+0x138` pair is `quote_token_program` and
`associated_token_program`, and `+0x278` (v1) and `+0x2a0` (v2) are `social_claim_authority`, both from
8.5. The 6.1 table and its closing paragraph now carry those tags.

**Status of sublane B2 after this walk: retired.** (B2-a) closed in 6.10, (B2-b) closed in 8.1,
(B2-c) closed in 8.5, (B2-d) closed in 6.11, (B2-e) closed here. `claim_social_fee_pda_v2` is measured
from wrapper `0x13c64` through body `0x4308`, token helper `0x76be`, SPL-token helper `0x14dba` and
`try_accounts` `0xc131`, and no open **[partial]** item remains on this handler.

Severity: Informational
Sévérité : Informational
Severity justification: static naming of one 8-byte accounts-struct slot with no behaviour, reachability or fund effect measured, so no exploitable impact is claimed.

---

## 7. SUBLANE A: `update_fee_shares` / `update_fee_shares_v2`, full bodies + every helper

Scope of this section: the two update handlers only (SUBLANE A of the P0 split). It
supersedes the **[partial]** status of 4.4 and 4.5: both bodies are now walked instruction by
instruction, and every helper they call is reconstructed with its deployed address. Sections
1, 2, 3 and the other handler modules are untouched. Tags as in the header **[B] / [R] /
[partial]**.

Bodies: `0x5e6f` = 696 decoded insns over `[0x5e6f, 0x60ce)`-call sites through the last exit at
`0x6133`, `0x673a` = 974 decoded insns ending at the panic path `0x6b1d`. Helper sizes below
are decoded instruction counts inside the reloc-aware function range.

Tooling added for this walk (local, `tools/`): `fees_body.py` (full annotated dump: absolute
branch targets, call target + callee size, relocated `lddw` VA with the first printable bytes,
so a body can be re-read byte for byte), plus the existing `fees_walk.py`, `fees_ladder.py`,
`fees_anchors.py`, `fees_sysscan.py`.

### 7.1 The context record these two bodies receive, and the two wrappers

Both bodies are called with `r1 = out`, `r2 = &Context`, `r3 = &Vec<Shareholder>`:

* `update_fee_shares`: `r1 = fp-0xc40`, `r2 = fp-0xc18`, `r3 = fp-0x18` at `0x1391f..0x13925`;
  the `Vec` the deserialiser 0x212b produced at `fp-0x618..fp-0x608` is re-staged to
  `fp-0x18`/`fp-0x10`/`fp-0x8` at `0x1391a..0x1391e`, so the body reads `[r3+0x10]` as
  `len` (`0x647a`) and `[r3]` as `ptr`. **[B]**
* `update_fee_shares_v2`: `r1 = fp-0x3a8`-region out, `r2 = fp-0x2d8`-region context, `r3 =
  &Vec`; `mov64 r8, r3` at `0x673a` and `[r8+...]` is never re-derived. **[B]**

Measured fields of that `r2` record for these two handlers:

| offset | width | measured use | tag |
|---|---:|---|---|
| `+0x08` | 8 (ptr) | the accounts struct: `ldxdw r4, [r2+8]` at `0x5e70`, re-read from the frame slot at `0x5eaa` (`r6`), and `ldxdw r7, [r2+8]` at `0x673c`. Every account field offset below is relative to that base. | **[B]** |
| `+0x10` / `+0x18` | 8 / 8 | remaining-account pointer / count: read at `0x5f25`/`0x5f26` and handed to the flush helper 0x7113, which indexes it at a `0x30` stride (`sub64 r1, r2` with `mul64 r2, 0x30` from `len-1` at `0x714f..0x7151`); the same pair is read by 0x63a6 at `0x63a7`/`0x63a8` and walked by 0x6134 with `add64 r8, 0x30` at `0x61b3` | **[B]** |
| `+0x20` | 1 | the bump byte: `ldxb r3, [r1+0x20]` at `0x60e1` (v1) and `0x6ad0` (v2), passed to the apply helper as `r3` | **[B]** |
| `+0x28..+0x38` | 0x18 | not used by these two bodies (the args arrive in `r3`) | - |

The `Context` header shape (`+0x00` program id, `+0x08` accounts pointer) is the one sublane B
measured on the claim bodies in 6.1; the two rows above are the additions this walk measured on
these two wrappers. Note that the two handlers' wrappers do **not** carry the args inside that
record: `update_fee_shares` passes them as a third pointer (`r3 = fp-0x18`, staged at
`0x1391a..0x1391e`), so `+0x28..+0x38` of `r2` is never read here. The claim handlers' layout
in 6.1 must therefore not be assumed identical; only the rows above are reused. **[B]**
The 48-byte `AccountInfo` shape used everywhere below (`key@0`, `lamports@8`, `data@0x10`,
`owner@0x18`, `rent_epoch@0x20`, `is_signer@0x28`, `is_writable@0x29`, `executable@0x2a`) is
the one already recorded in 4.4 and in `docs/account_layouts.md`: the clone blocks read exactly
those offsets (`0x5e89..0x5e8d`, `0x5f7b..0x5f7f`, `0x67a0..0x67a4`, and eleven more).

#### 7.1.1 `update_fee_shares` wrapper - `0x138d4` (byte `0x9c6a0`, 129 insns) **[B]**

```rust
pub fn update_fee_shares(
    program_id: &Pubkey,        // r2  -> fp-0xc80
    accounts: &[AccountInfo],   // r3 = ptr (r8), r4 = len (r9)
    data: &[u8],                // [r5-0x1000] = ptr, [r5-0xff8] = len
) -> ProgramResult {
    msg!("Instruction: UpdateFeeShares");                       // 0x138d9, rodata 0xc5288, len 0x1c
    let mut cursor = data;                                      // 0x138dd..0x138e4
    let args = Vec::<Shareholder>::deserialize(&mut cursor)?;   // 0x212b, call 0x138e5
    // 0x138e6..0x138ea: the deserialiser Result tag is compared with 0x8000000000000000
    let mut ctx = UpdateFeeSharesAccounts::try_accounts(program_id, accounts, &mut cursor)?;
                                                                // 0xecba (1927), call 0x138fc
    let ctx = memcpy_frame(&ctx);                                // 0x184d9, 0x5e8 bytes at 0x13908
    update_fee_shares_impl(&mut ctx, &args)?;                    // 0x5e6f, call 0x13925
    SharingConfig::exit(&ctx)?;                                  // 0x989, call 0x1392f
    // 0x13930..0x13956: tag check, then Ok(()) or the account name "sharing_config"
    // (0xc4c1c, len 0xe) formatted into the error by 0x2b1 at 0x13950
    Ok(())
}
```

Extra measured detail: the account-name formatter is reached with `r5 = 0xe` at `0x1394f` (the
`sharing_config` field of the accounts struct is the one whose write can fail, so its name is
added to the error); the failed-path error ctor is `0x1601e` with code `0x66` = 102
(`0x13943`/`0x13944`). **[B]**

#### 7.1.2 `update_fee_shares_v2` wrapper - `0x1395a` (byte `0x9cad0`, 134 insns) **[B]**

Identical shape: `Instruction: UpdateFeeSharesV2` at `0x1395f`, deserialiser `0x212b` at
`0x1396b`, `try_accounts` `0xf52a` (2034) at `0x13981`, `memcpy` thunk at `0x1398f`, body
`0x673a` at `0x139ad`, packer `0x989` at `0x139b6`, second packer call `0x139df`, name
formatter `0x2b1` at `0x139f3`/`0x13a0e`. **[B]**

### 7.2 `update_fee_shares` body - `0x5e6f` (byte `0x2f378`, 696 insns) **[B]**

#### 7.2.1 Gate and call order, measured

| # | insn | what the bytes do | tag |
|---:|---|---|---|
| 1 | `0x5e70..0x5e95` | borrows the `AccountInfo` at accounts `+0x288` (two `RefCell` increments at `0x5e74..0x5e88`, the `is_signer`/`is_writable`/`executable` bytes read at `0x5e8b..0x5e8d`) and stages a 14-word `AccountInfo` record at `fp-0x278` | **[B]** |
| 2 | `0x5e9a` | `call 0x250d(out = fp-0x40, &record)`: read that account's serialised `quote_mint` and answer "is it the default pubkey" (7.4.2) | **[B]** |
| 3 | `0x5e9e` | the answer is the byte at `fp-0x38` (= `out+8`) | **[B]** |
| 4 | `0x5eaf` | `answer == 0` (the curve carries a non-default quote mint) -> block `0x5ede`: format record `0xc3e6c` through `0x8932`/`0x8dca` (`0x5ee2`/`0x5ef4`), then `0x5f00` builds the `AnchorError` with code `0x178f` = **6031** at `0x5f0f`, file `0xc4432` len `0x44` = 68 at `0x5f0c`/`0x5f12`, line `0x81` = **129** at `0x5f11`, boxed by `0x15a4e` at `0x5f18` | **[B]** |
| 5 | `0x5eb0` | `ldxb r1, [accounts+0x5b]`; `== 1` -> block `0x5eb3`: format record `0xc3e84`, then code `0x1788` = **6024** at `0x5f51`, line `0x82` = **130** at `0x5f53`, boxed at `0x5f5a` | **[B]** |
| 6 | `0x5f1c..0x5f21` | `call 0x724e(out = fp-0x288, config object at `accounts+0x5d0`, accounts)` = the `fee_sharing/mod.rs` authority/state gate, whose raises are `mod.rs:97` (6016), `mod.rs:99` (6018) and `err!` 6009 (4.4.1) | **[B]** |
| 7 | `0x5f24..0x5f3c` | builds the flush argument block: the `(ptr, count)` pair from `ctx+0x10`/`ctx+0x18`, an `AccountInfo` staged from `accounts+0xc0`, and the WSOL key `rodata 0xc3740` (`= So11111111111111111111111111111111111111112`, base58-decoded) at `fp-0x1000`/`fp-0xff8`; `call 0x7113(out = fp-0x40, ptr, count, accounts+0x290, fp)` (7.4.4) | **[B]** |
| 8 | `0x5f63..0x60ce` | clones eleven accounts and pushes eight `AccountInfo` pointers at `fp-0xfd0..fp-0x1000`, then `call 0x73f3(out = fp-0x298, accounts+0x288, fp-0x1d8, fp-0x1a8, fp)` = the AMM `transfer_creator_fees_to_pump` invocation (7.4.5) | **[B]** |
| 9 | `0x60cf` | tag `!= 2` -> return the error | **[B]** |
| 10 | `0x60d5` | `call 0x63a6(out = fp-0x278, ctx, fp-0x1d8)` = validate the payout set against the new shareholder list and re-serialise the config (7.4.7) | **[B]** |
| 11 | `0x60df` | if the returned word at `fp-0x268` is `0` the payout set is empty: straight to the apply helper (`0x60e0 -> 0x60e6`) | **[B]** |
| 12 | `0x60ef..0x6125` | seven `0x1ec6` drops plus the meta assembly, then `call 0x72e5(out = fp-0x2a8, ...)` = pump `distribute_creator_fees` (7.4.6) | **[B]** |
| 13 | `0x6128..0x612e` | second `call 0x6479(out = fp-0x2b8, accounts, ctx+0x20 bump, &args)` on the payout path | **[B]** |
| 14 | `0x6128`/`0x60e1` | both paths call `0x6479` with `r3 = ldxb [ctx+0x20]` and `r4 = the saved &Vec` = the apply + event helper (7.4.10) | **[B]** |

#### 7.2.2 Reconstructed body

```rust
// programs/pump-fees/src/instructions/fee_sharing/update_fee_shares.rs
pub fn update_fee_shares(
    ctx: Context<UpdateFeeShares>,
    shareholders: Vec<Shareholder>,
) -> Result<()> {
    // 0x250d: does the pump bonding curve carry a non-default quote mint?
    // data[0x53..0x73] is the serialised BondingCurve.quote_mint (offset 83, 32 bytes).
    let quote_is_default = curve_quote_is_default(&ctx.accounts.bonding_curve)?;

    require!(
        quote_is_default,                                   // 6031
        FeeError::UnsupportedQuoteMint                      // update_fee_shares.rs:129
    );
    require!(
        ctx.accounts.sharing_config.version != 1,           // accounts + 0x5b
        FeeError::FeeSharesAlreadyUpdated                   // 6024, update_fee_shares.rs:130
    );

    check_authority_and_state(&ctx)?;                       // 0x724e  mod.rs:97 / mod.rs:99
    flush_creator_fees(&ctx, &WSOL, &ctx.remaining_accounts)?;
                                                            // 0x7113  mod.rs:60 / 74 / 83
    let prepared = pump_amm::transfer_creator_fees_to_pump(&ctx)?;
                                                            // 0x73f3 -> 0x11c7c
    let payout = write_sharing_config(&ctx, &prepared)?;    // 0x63a6 -> 0x6134 + 0x989

    if !payout.is_empty() {
        pump::distribute_creator_fees(&ctx, &payout)?;      // 0x72e5 -> 0x109b8
    }

    apply_shareholders_and_emit(&ctx, &shareholders)?;      // 0x6479
    Ok(())
}
```

Notes that the re-verification will want:

* The two `require!`s are adjacent in the source (lines 129 then 130) but the compiler emitted
  the 6024 block first (`0x5ede`) and the 6031 block second (`0x5eb3`): the *measured* transfer
  of control is `answer == 0 -> 6031` and `version == 1 -> 6024`, which is what the body above
  states. **[B]**
* `version` is the same in-memory byte the packer writes as serialised field 2: packer `0x989`
  reads `struct + 0x5a` and `struct + 0x5b` for the two trailing `u8`s (`0x9bf`/`0x9c0` and
  `0x9c7`/`0x9c8`), and §3.1 already pins `status` at `+0x58` and `admin_revoked` at `+0x59`
  through the authority gate. Which of `+0x5a`/`+0x5b` is `bump` and which is `version` is
  **[partial]** in §3.1, but the *check itself* is measured: the byte compared with 1 is
  `+0x5b`. **[B]**
* The legacy path requiring the *default* quote mint matches `specs-fees/fees_specs.md` §7
  ("Legacy path requires the curve quote == default") **[R]**, and is what makes 6031
  `Unsupported quote mint` reachable from this handler. **[B]**
* Ordering of 0x63a6 (write) before the pump CPI and before 0x6479 (which sets
  `admin_revoked = 1` and installs the new `Vec`) is measured, but *why* the config is
  serialised at that point is **[partial]**: the most consistent reading is "the account is
  written once the payout set has been validated, then written again at `exit`"; a realloc is
  not observed in the body. **[partial]**

### 7.3 `update_fee_shares_v2` body - `0x673a` (byte `0x339d0`, 974 insns) **[B]**

#### 7.3.1 Gate and call order, measured

| # | insn | what the bytes do | tag |
|---:|---|---|---|
| 1 | `0x673c..0x673f` | `r7 = [ctx+8]` (accounts struct), `r3 = [r7+0x240]` (the config object), `ldxb r1, [r3+0x5b]`; `== 1` -> block `0x6740`: code `0x1788` = **6024** at `0x6787`, line `0x89` = **137** at `0x6789`, file `0xc4476` len `0x47` = 71 at `0x6784`/`0x678a` | **[B]** |
| 2 | `0x6762..0x6768` | `call 0x724e(out = fp-0x308, config at accounts+0x230)` | **[B]** |
| 3 | `0x676c..0x67e6` | borrows the account at `accounts+0x248`, gates its data at `len >= 0x73` (`jlt r0, 0x73` at `0x67b0`, panic `0x17eb1` at `0x67c0`), then **inlines** the curve-quote read: the 32 bytes at data `0x53..0x73` are copied to `fp-0x88` (`0x67ca..0x67e6`) | **[B]** |
| 4 | `0x67eb..0x6805` | `sol_memcmp_(fp-0x88, zeroed 32 bytes, 0x20)` at `0x67f0`: equal (default quote) -> the four immediates of the WSOL key are stored at `fp-0x2e0..fp-0x2f8` (`0x67fc..0x6805`, the same 32 bytes as `rodata 0xc3740`); different -> the curve value is moved to `fp-0x2e0..0x2f8` (`0x67f4..0x67fb`) | **[B]** |
| 5 | `0x6818..0x6827` | reads the `quote_mint` account key (`[r7+0xd8]` -> `key@0`, 32 bytes at `fp-0x2d8`) and `sol_memcmp_`s it against the expected key (`fp-0x2f8`, `r3 = 0x20`); mismatch -> `0x6848`: code `0x1792` = **6034** at `0x6870`, line `0x98` = **152** at `0x6872` | **[B]** |
| 6 | `0x682b..0x6842` | `call 0x7113(out = fp-0x40, ctx+0x10, ctx+0x18, [r7+0x248]+8, fp)` with the stage pointers `fp-0x1000 = &expected_quote`, `fp-0xff8 = &WSOL`; its raises are `mod.rs:60` (6013), `mod.rs:74`, `mod.rs:83` (6033) | **[B]** |
| 7 | `0x6898..0x6a2b` | clones the payout accounts and pushes eight `AccountInfo` pointers at `fp-0xfc0..fp-0x1000`, then `call 0x753b(out = fp-0x338, ...)` = AMM `transfer_creator_fees_to_pump_v2` (7.4.12) | **[B]** |
| 8 | `0x6a39` | `call 0x250d(out = fp-0x40, &curve record)` again, answered flag at `fp-0x38` | **[B]** |
| 9 | `0x6a4e` | flag `!= 0` (curve quote is the default pubkey, legacy leg) -> `0x6a4f`: `call 0x6134(out = fp-0x2d8, ptr, count)` (7.4.8). flag `== 0` (real quote mint) -> `0x6aed`: `call 0x6b1e(out = fp-0x2d8, ptr, count)` (7.4.9). Both join at `0x6a5d`. | **[B]** |
| 10 | `0x6a6b` | `ldxb r2, [fp-0x2c0]` + `and64 r2, 1`; set -> `0x6afc`: stores the new `Vec` (`ptr@+0`, `cap@+8`, `len@+0x10`) into the config object `[r7+0x240]` and calls the packer `0x989(out = fp-0x348, [r7+0x240], crate::ID, crate::ID)` at `0x6b07`; `Err` -> return | **[B]** |
| 11 | `0x6a6e..0x6ab3` | if the payout word at `fp-0x48` is non-zero: twelve `0x1ec6` drops and the meta array, then `call 0x735a(out = fp-0x358, ...)` = pump `distribute_creator_fees_v2` (7.4.12) | **[B]** |
| 12 | `0x6ad5` / `0x6b12` | both paths end in `call 0x6e50(out, accounts, ldxb [ctx+0x20], &args)` = apply + event (7.4.11) | **[B]** |
| 13 | `0x6b1b` | unreachable-by-branch panic path: `call 0x176d7` with the location record `0xc8a98` (line `0x30` = 48), i.e. the borrow-length assertion | **[B]** |

#### 7.3.2 Reconstructed body

```rust
// programs/pump-fees/src/instructions/fee_sharing/update_fee_shares_v2.rs
pub fn update_fee_shares_v2(
    ctx: Context<UpdateFeeSharesV2>,
    shareholders: Vec<Shareholder>,
) -> Result<()> {
    require!(
        ctx.accounts.sharing_config.version != 1,       // accounts object + 0x5b
        FeeError::FeeSharesAlreadyUpdated               // 6024, update_fee_shares_v2.rs:137
    );

    check_authority_and_state(&ctx)?;                   // 0x724e mod.rs:97 / mod.rs:99

    // inlined curve-quote read, same 0x53..0x73 slice as 0x250d
    let curve_quote: [u8; 32] = ctx.accounts.bonding_curve
        .try_borrow_data()?[0x53..0x73].try_into().unwrap();
    let expected = if curve_quote == [0u8; 32] { WSOL } else { curve_quote };

    require!(
        ctx.accounts.quote_mint.key().to_bytes() == expected,
        FeeError::InvalidQuoteMint                       // 6034, update_fee_shares_v2.rs:152
    );

    flush_creator_fees(&ctx, &expected, &ctx.remaining_accounts)?;   // 0x7113
    let prepared = pump_amm::transfer_creator_fees_to_pump_v2(&ctx)?; // 0x753b -> 0x11e9c

    let quote_is_default = curve_quote_is_default(&ctx.accounts.bonding_curve)?; // 0x250d
    let payout = if quote_is_default {
        check_remaining_accounts_legacy(&ctx, &prepared)?;   // 0x6134, update_fee_shares.rs:186/188
        prepared
    } else {
        check_remaining_accounts_quoted(&ctx, &prepared)?;   // 0x6b1e, _v2.rs:234/237/239
        prepared
    };

    if payout.write_requested {
        ctx.accounts.sharing_config.shareholders = shareholders_copy;
        ctx.accounts.sharing_config.exit()?;                 // 0x989 at 0x6b07
    }

    if !payout.is_empty() {
        pump::distribute_creator_fees_v2(&ctx, &payout)?;    // 0x735a -> 0x10ba8
    }

    apply_shareholders_and_emit(&ctx, &shareholders)?;        // 0x6e50
    Ok(())
}
```

Notes:

* The version gate is the **first** statement of the v2 body (`0x673c`), while in v1 it is the
  second (after the quote probe). That is a real difference between the two sources, not a
  reading artifact: v1 entry `0x5e70` goes to the probe first and v2 entry `0x673c` tests
  `+0x5b` first. **[B]**
* The `expected` key substitution (WSOL when the curve quote is the default pubkey) is
  measured on the bytes (`0x67f0` memcmp against a zeroed 32-byte buffer, then either the four
  WSOL immediates or the curve value are staged at `fp-0x2e0..fp-0x2f8`); WSOL is
  `So11111111111111111111111111111111111111112`, base58-decoded from `rodata 0xc3740`
  (`tools/tmp_x4.py` run: `069b8857feab8184fb687f634618c035dac439dc1aeb3b5598a0f00000000001`). **[B]**
* `matched.rewrite` stands for the `and64 r2, 1` test on `[fp-0x2c0]` at `0x6a6b`, a byte the
  0x6134/0x6b1e results produce. Which result byte it is was **[partial]** in the previous
  revision; section 9.2 closes it: it is the byte at record `+0x18`, written 0 at `0x62a1` and
  `0x6cda` and 1 at `0x6399`, `0x6e3a` and `0x6df2`, and it is set exactly when the matcher had
  to repair the shareholder vector. The store sequence itself (config `+0/+8/+0x10` then packer
  0x989) is measured at `0x6afc..0x6b07`. **[B]**
* The legacy branch reuses the v1 helper `0x6134` (whose raise lines are in
  `update_fee_shares.rs`), which is why the v2 body can surface `update_fee_shares.rs:186/188`
  errors: that cross-file attribution is measured by the anchor scan in 2.3 and is the
  strongest single piece of evidence that `0x6134` is a shared helper and not a v2 duplicate.
  **[B]**

### 7.4 Helpers the two bodies call

Every entry gives the deployed address, the decoded size, the argument registers as measured at
the call site, the raise sites, and a reconstructed signature.

#### 7.4.1 `Vec<Shareholder>` deserialiser - `0x212b` (byte `0x10958`, 147 insns) **[B]**

Called at `0x138e5` (v1 wrapper), `0x1396b` (v2 wrapper) and `0xd930`.

```rust
fn deserialize_shareholders(out: &mut Result<Vec<Shareholder>, ProgramError>,
                            reader: &mut &[u8]) {
    if reader.len() < 4 { *out = Err(InvalidInstructionData); return; }   // 0x212d -> 0x21a7
    let n = u32::from_le_bytes(*reader[..4]);                            // 0x212f
    *reader = &reader[4..];                                              // 0x2130..0x2134
    if n == 0 { *out = Ok(Vec::new()); return; }                         // 0x2136 -> 0x21b8
    let cap = n.min(120);                                                // 0x2141..0x2143
    let mut v = Vec::with_capacity(cap);                                 // heap 0x300000000, n*0x22
    while v.len() < n {
        if reader.len() < 0x20 { *out = Err(InvalidInstructionData); return; }  // 0x2178 -> 0x21af
        let e = Shareholder {
            address: reader[..32],                                       // 0x217e..0x219b
            share_bps: u16::from_le_bytes(reader[32..34]),               // 0x2189/0x2190
        };
        v.push(e);                                                        // grow 0x1bd6 when needed
        *reader = &reader[34..];                                          // 0x216e add64 r6, 0x22
    }
    *out = Ok(v);                                                         // 0x21bc..0x21c2
}
```

Measured facts: `4`-byte length prefix; per-element stride `0x22` = 34 (`mul64 r2, 0x22` at
`0x2144`, `add64 r6, 0x22` at `0x216e`, `add64 r9, 0x20` for the address buffer at `0x64d8` in
the apply helper); a **120-element cap** (`jlt r1, 0x78` then `mov64 r3, 0x78` at
`0x2141..0x2142`, i.e. 120 x 34 = 4080 bytes, the same 4080-byte budget `docs/arg_frames`
records for the `Shareholder` vector); the element write order (32-byte address then `u16` at
element `+0x20`) is byte-identical to the packer ladder in §3.1, so the in-memory `Shareholder`
and the wire `Shareholder` share the 34-byte stride. **[B]**

#### 7.4.2 curve `quote_mint` probe - `0x250d` (byte `0x12868`, 60 insns) **[B]**

```rust
fn curve_quote_is_default(curve: &AccountInfo) -> Result<bool> {
    let data = curve.try_borrow_data()?;                  // 0x250f -> 0x1652f
    if data.len() < 0x73 { return Ok(true); }             // 0x2511, 0x2521 (tag 2, flag 1)
    let quote: [u8; 32] = data[0x53..0x73];               // 0x2525..0x2535
    Ok(quote == [0u8; 32])                                // 0x184e6 at 0x253f
}
```

`data[0x53..0x73]` is the serialised `pump::BondingCurve.quote_mint` (offset **83 = 0x53**, 32
bytes) per `docs/account_layouts.md` §1.2 **[R for the field name, B for the offset and the
comparison]**. The `0x73` gate is bounds-driven: reading 32 bytes at `0x53` needs
`len >= 0x73`. Returns `Ok` (tag 2) with a one-byte flag at `out+8` = `1` when the region is
all-zero, `0` otherwise (`0x2540..0x2545`). Both bodies consume the flag with opposite
polarity (v1 requires it, v2 branches on it), which is why v1 rejects a curve that already
carries a real quote mint.

#### 7.4.3 authority / state gate - `0x724e` (byte `0x39270`, 140 insns)

Unchanged from 4.4.1: admin compare at `0x725f`, `admin_revoked` at `0x7263`, `status` at
`0x726d`, raises 6016 `mod.rs:97`, 6009 (`err!`), 6018 `mod.rs:99`. Called at `0x5f21` (v1) and
`0x6768` (v2). **[B]**

#### 7.4.4 creator-fee flush - `0x7113` (byte `0x38898`, 295 insns) **[B]**

```rust
fn flush_creator_fees(ctx: &Accounts, quote_mint: &Pubkey,
                      remaining: &[AccountInfo]) -> Result<()> {
    if !ctx.accounts.pump_creator_vault.is_some() { return Ok(()); }  // ldxb [r4+0x48] 0x7116
    if remaining.is_empty() { return Err(FeeError::NotEnoughRemainingAccounts); } // 6013 mod.rs:60
    let (pool_authority, _) = derive("pool-authority", quote_mint, pump::ID);  // 0x712d, 0xc4301/0xc4ecd
    let (pool, _)          = derive("pool", quote_mint, pump_amm::ID);         // 0x714e, 0xc3e0c/0xc4f3c
    // 0x716a / 0x7172 sol_memcmp_ 32 against the supplied keys; mismatch -> the formatted
    // error built at 0x717f/0x7191 whose Location is mod.rs:74 (code immediate absent)
    if !pool_creator_fees_swept(&remaining[remaining.len() - 1]) {
        return Err(FeeError::PoolCreatorFeesNotSwept);                // 6033 mod.rs:83, 0x7237
    }
    Ok(())
}
```

Measured: both derivation calls go through `0x16f53` (37 insns, `try_find_program_address`), seed
libraries `pool-authority` (`0xc4301`, len 14) and `pool` (`0xc3e0c`, len 4), program ids
`0xc4ecd` = `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P` (pump) and `0xc4f3c` =
`pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA` (pump_amm), both base58-confirmed; the last
remaining account is indexed as `(len - 1) * 0x30` at `0x714f..0x7153`; the three raises are
`mod.rs:60` (0x71f9, 6013), `mod.rs:74` (0x71a0, no code), `mod.rs:83` (0x7237, 6033). **[B]**

#### 7.4.5 AMM payout CPI, v1 - `0x73f3` (byte `0x39f98`, 327 insns) **[B]**

```rust
fn amm_transfer_creator_fees_to_pump(ctx: &Accounts, remaining: &[AccountInfo],
                                     prepared: &mut Prepared) -> Result<()> {
    // 0x7401..0x7408: four Option slots of the accounts object are tested non-null
    // 0x7413: the curve/quote key is compared with the all-zero pubkey (rodata 0xc36a0)
    // 0x74e8..0x7515: ten 0x30-byte AccountInfo copies + a 0x1b0-byte block copy
    pump_amm::transfer_creator_fees_to_pump(...)   // call 0x11c7c at 0x7534
}
```

CPI edge, from `maps/cpi_frames_all4.json`: target `pump_amm`, instruction
`transfer_creator_fees_to_pump`, disc **`8b348655e4e56cf1`** materialised at `0x11c85`-region
(the map records the builder function `0x11c7c`, 533 insns, `depth_to_invoke` 2), payload
length **8** (the discriminator alone, `payload_spans [[0, 8]]`), one caller
`update_fee_shares` at depth 3. **[B]**

#### 7.4.6 pump payout CPI, v1 - `0x72e5` (byte `0x39728`, 117 insns) **[B]**

Assembles the meta array from seven `0x30`-byte copies (`0x7314..0x7338`), one `0x120`-byte
six-record block copy (`0x733d`) and the three words taken from `[r9]` (`0x732f..0x7333`),
writes the payload length `8` at `fp-0x10` (`0x734e`) and calls `0x109b8` (485 insns) at
`0x7353`.

CPI edge: target `pump`, instruction `distribute_creator_fees`, disc
**`a572670079cef751`**, payload length **8**, single caller `update_fee_shares` at depth 3.
**[B, `maps/cpi_frames_all4.json`]**

#### 7.4.7 config write + payout Vec - `0x63a6` (byte `0x31d30`, 202 insns) **[B]**

```rust
fn write_sharing_config(ctx: &Context, prepared: &Prepared) -> Result<Vec<AccountInfo>> {
    let accounts = ctx.accounts;                                  // [ctx+8]
    let shares = &accounts.sharing_config.shareholders;            // accounts + 8 / + 0x10
    let matched = check_remaining_accounts(&shares, ctx.remaining_ptr, ctx.remaining_len)?;
                                                                   // 0x6134 at 0x63b0
    // 0x63bb..0x63be: the packer runs only when the matcher asks for a rewrite (record +0x18)
    SharingConfig::exit_for(accounts, crate::ID)?;                  // 0x989 at 0x644e
    // 0x63c3..0x641f: heap Vec of the payout AccountInfo (0x30 stride, cap usize::MAX/0x30
    // written as the immediate 0x2aaaaaaaaaaaaaa at 0x63c8)
    Ok(matched)
}
```

Correction, section 9: the two legs are exclusive, not sequential. The packer runs only when the
matcher's `rewrite` byte is set; otherwise the body goes straight to the payout vector, which is
built from **all** remaining accounts (9.3). **[B]**

On the error path the `Result` is rebuilt at `0x643f`/`0x6443` and the drops at
`0x645e..0x6476` unwind. **[B]**

#### 7.4.8 remaining-account / shareholder key matcher - `0x6134` (byte `0x309a0`, 597 insns) **[B]**

Shared by `0x63a6` (v1) and the v2 body's legacy branch (`0x6a56`).

```rust
fn check_remaining_accounts(shares: &[Shareholder], remaining: &[AccountInfo])
    -> Result<Vec<AccountInfo>> {
    let mut out = Vec::with_capacity(remaining.len());   // 0x613a mul 0x30
    let mut addrs = Vec::with_capacity(shares.len());    // 0x6159 mul 0x22
    for (i, sh) in shares.iter().enumerate() {
        if i >= remaining.len() { return Err(FeeError::NotEnoughRemainingAccounts); }
                                                          // 6013 update_fee_shares.rs:186
        if remaining[i].key.as_ref() != sh.address.as_ref() {
            return Err(FeeError::ShareholderAccountMismatch); // 6020 :188
        }
        out.push(remaining[i].clone());
    }
    Ok(out)
}
```

Measured: `mul64 r2, 0x30` at `0x613a` and `mul64 r2, 0x22` at `0x615a` (the two allocations), the
`0x30`-stride walk at `0x61b3`, the 32-byte `sol_memcmp_` at `0x61ab`, the two raise tuples at
`0x62ea` (`update_fee_shares.rs:186`, 6013) and `0x6306` (`:188`, 6020), and the
`Result::unwrap()`-shaped panic helper `0x7e` (158) reached at `0x6329`.

Correction, section 9: the byte read at `0x61b2` is `remaining[i].executable` (element offset
0x2a), not an offset into the account array, and it gates whether the matched element is pushed
at all. The helper also carries a bps repair path and returns a `rewrite` flag at record +0x18.
See 9.1, 9.2 and 9.4; the reconstruction above stops at the match itself. **[B]**

#### 7.4.9 v2 remaining-account matcher - `0x6b1e` (byte `0x358f0`, 786 insns) **[B]**

Same job for the non-default-quote branch. Raises, all in `update_fee_shares_v2.rs`: 6013 at
`:234` (tuple `0x6d58`), 6013 at `:237` (tuple `0x6d01`), 6020 at `:239` (tuple `0x6d74`); the
32-byte key compare is at `0x6ba2`; the Vec growth path uses `0x1bd6`/`0x1ba9`/`0x1b21`; the two
`Location` records it builds are `0xc8b08` (line `0x37` = 55) and `0xc8b20` (line `0x12` = 18).
Shape: the same key-vs-shareholder-address match as 7.4.8 with the v2 account set (the
quote-mint leg adds the vault ATA / token-program accounts), which is why it carries the second
6013 site at `:234`/`:237` instead of the single one in 7.4.8. **[B]**

Correction, section 9: the two helpers share the executable gate after all. 0x6134 reads it at
`0x61b2` as `[r8 + 0x5a]` (base `remaining - 0x30`) and 0x6b1e reads it at `0x6ba8` as
`[r7 + 0x2a]` (base `remaining`), which is the same field. What actually separates them is the
repair leg: 0x6b1e additionally appends the remaining accounts after the matched prefix
(`0x6e16..0x6e2c`). See 9.1 and 9.2. The v2 body still branches between two helpers, and the
v2 one is not a rename of the v1 one. **[B]**

#### 7.4.10 apply shareholders + event, v1 - `0x6479` (byte `0x323c8`, 669 insns) **[B]**

```rust
fn apply_shareholders_and_emit(ctx: &Accounts, bump: u8,
                               shareholders: &[Shareholder]) -> Result<()> {
    require!(!shareholders.is_empty(), FeeError::NoShareholders);
                                                        // 6010 update_fee_shares.rs:258
    require!(shareholders.len() <= 10, FeeError::TooManyShareholders);
                                                        // 6011 :259  (jlt r9, 0xb at 0x649e)
    let mut total: u16 = 0;
    let mut addrs = Vec::with_capacity(shareholders.len());   // len * 0x20, 0x64aa
    for sh in shareholders {
        require!(sh.share_bps != 0, FeeError::ZeroShareNotAllowed);  // 6017 :269
        total = total.checked_add(sh.share_bps).ok_or(FeeError::ShareCalculationOverflow)?;
                                                                // err! 6015 via 0x8d8b @0x6583
        addrs.push(sh.address);
    }
    // 0x658c: allocator 0x1636 grows the working buffer; pairs are memcmp'd (0x659a/0x65b6)
    // and duplicates compacted (0x65bb..0x65c4)
    require!(total == 10_000, FeeError::InvalidShareTotal);       // 6014 :291 (0x2710 at 0x65c6)
    require!(dedup_len == shareholders.len(), FeeError::DuplicateShareholder); // 6012 :292
    let v = Vec::from(dedup);                                    // len * 0x22 at 0x65df
    ctx.accounts.sharing_config.shareholders = v;                 // +0x00/+0x08/+0x10 at 0x6641..0x6644
    ctx.accounts.sharing_config.admin_revoked = true;             // stb [+0x59], 1 at 0x6645
    let now = Clock::get()?.unix_timestamp;                        // 0x1621e at 0x6648
    emit!(UpdateFeeSharesEvent { ... });                          // 0x16eb0 + CPI 0x161ae at 0x6706
    Ok(())
}
```

Measured: `r4 = &Vec` and `len = [r4+0x10]` at `0x647a`; the 10-element ceiling is
`jlt r9, 0xb` at `0x649e` (11 -> the `:259` block); the per-element `u16` at element `+0x20`
(`ldxh [r0+0x20]` at `0x64de`) with the `u16` overflow test at `0x64e1..0x64e5`; the sum test
`jeq r7, 0x2710` at `0x65c6`; the duplicate test `count != len` at `0x65ca`; the copy-back of
the new `Vec` and `stb [r8+0x59], 0x1` at `0x6641..0x6645`; `Clock::get` at `0x6648`
(`sol_get_clock_sysvar` inside `0x1621e`); the event serialiser `0x16eb0` (118) at `0x66e7`;
the event CPI emitter `0x161ae` (108, `invoke_signed` at `0x16214`) at `0x6706` with the
`__event_authority` string `0xc3ec2`, and the program id `0xc4ead` at `0x66e3`/`0x66e7`. **[B]**

The `r3` argument (`ldxb [ctx+0x20]` at the call sites) is the **bump of the event-authority
PDA**: it is stored to `fp-0x2e8` at `0x64a1`, re-read at `0x66f7` and written as the last byte
of a two-seed array whose first seed is `__event_authority` (`0xc3ec2`, len `0x11` at
`0x66f4`/`0x66fb`), with seed count `2` at `0x66f9` and the single signed-seed array count `1`
at `0x66ff`; `invoke_signed` then uses it at `0x6706`. **[B]**

#### 7.4.11 apply shareholders + event, v2 - `0x6e50` (byte `0x37280`, 671 insns) **[B]**

The v2 twin of 7.4.10, same five gates on the v2 file: 6010 `:292` (line immediate `0x124` at
`0x6ee1`, tuple `0x6edc`), 6011 `:293` (`0x125` at `0x6f16`, tuple `0x6f11`), 6017 `:303`
(`0x12f` at `0x6f4b`, tuple `0x6f46`), 6014 `:325` (`0x145` at `0x6fe7`, tuple `0x6fe2`), 6012
`:326` (`0x146` at `0x7047`, tuple `0x7042`); allocator `0x1636` at `0x6f63`; the duplicate
memcmps at `0x6f71`/`0x6f8d`; the `u16` sum test in the same position; `Clock::get` `0x1621e` at
`0x7021`; the event serialiser `0x16eb0` at `0x70c0` and the event CPI `0x161ae` at `0x70df`,
with the identical `__event_authority` + bump seed array built at `0x70c8..0x70d8` from the same
`fp-0x2e8` bump slot (`0x6e78` store, `0x70d0` re-read). Called at `0x6ad5` (payout path) and
`0x6b12` (empty payout path). **[B]**

Section 9.5 closes this to the instruction: 0x6e50 is 0x6479 line for line with five
substitutions (the `file!()` constant, the five `line!()` immediates, the config install through
`accounts + 0x240`, and the two key sources of the event), so the reconstruction above in 7.4.10
covers this helper with those substitutions and nothing else. **[B]**

#### 7.4.12 v2 payout CPIs - `0x753b` (byte `0x3a9d8`, 386) and `0x735a` (byte `0x39ad0`, 153) **[B]**

* `0x753b` = AMM leg: `sol_memcmp_` 32 against the all-zero pubkey `0xc36a0` at `0x755b`, eleven
  `0x30`-byte meta copies (`0x766b..0x76b0`), `call 0x11e9c` (565) at `0x76b7` = pump_amm
  `transfer_creator_fees_to_pump_v2`, disc **`01214eb921432c5c`**, payload length **8**.
* `0x735a` = pump leg: twelve `0x30`-byte meta copies plus one `0x150`-byte seven-record block
  copy (`0x7393..0x73e4`), `call 0x10ba8` (566) at `0x73ec` = pump `distribute_creator_fees_v2`,
  disc **`ffcb134ff444089f`** materialised at `0x10bc0`, payload length **9**: the
  discriminator plus `initialize_ata: bool` at offset 8 (`payload_spans [[0,8],[8,9]]`,
  `declared` in `maps/cpi_frames_all4.json`). That bool is the one visible wire difference
  between the v1 and v2 pump call. **[B]**

### 7.5 Supporting helpers reached from these two bodies (addresses only)

| helper | insn | byte | insns | role | tag |
|---|---|---:|---:|---|---|
| `sol_memcpy_` thunk | 0x184d9 | 0xc26c8 | 4 | every 0x30/0x120/0x1b0 account-meta copy above | **[B]** |
| `sol_memcmp_` thunk | 0x184e6 | 0xc2730 | 8 | all 32-byte key comparisons (0x253f, 0x659a, 0x65b6, 0x6827, 0x716a, 0x7172, ...) | **[B]** |
| `Vec` reserve (0x22 stride) | 0x1c03 | 0xe018 | 43 | growth of the shareholder vector inside 0x6479 (`0x64f4`) | **[B]** |
| `Vec` grow (0x22 stride) | 0x1bd6 | 0xdeb0 | 44 | growth inside the deserialiser (`0x21a2`) and 0x6134/0x6b1e | **[B]** |
| `Vec` grow instantiations | 0x1ba9 / 0x1b21 | 0xdd48 / 0xd908 | 44 / 45 | the 0x30 and mixed-stride variants used by 0x6134 / 0x6b1e | **[B]** |
| `RawVec` grow core | 0x1a5a | 0xd2d0 | 101 | shared by the three above; the only `sol_memcpy_` inside them | **[B]** |
| bump allocator / `Vec` grow | 0x1636 | 0xb1b0 | 636 | heap cursor `0x300000000`; the single `sol_memmove_` site at `0x171f` (§2.1.1) | **[B]** |
| `Clock::get` | 0x1621e | 0xb10f0 | 29 | `sol_get_clock_sysvar` at `0x16226`, then the 122-insn clock copy `0x16733` | **[B]** |
| event data serialiser | 0x16eb0 | 0xb7580 | 118 | Borsh event body (`BufferTooSmall`/`Utf8Error` strings, `None`/`Some`) | **[B]** |
| event CPI emitter | 0x161ae | 0xb0d70 | 108 | `invoke_signed` at `0x16214`; takes `__event_authority` (`0xc3ec2`) | **[B]** |
| `SharingConfig` packer | 0x989 | 0x4c48 | 132 | writes the account image (§3.1); called at `0x1392f`, `0x644e`, `0x6b07` | **[B]** |
| `err!(FeeError)` ctor | 0x8d8b | 0x46c58 | 59 | the code-immediate-free raises (6009, 6015) | **[B]** |
| AnchorError ctor by code | 0x1601e | 0xb00f0 | 70 | the 102 wrapper raise at `0x13944` | **[B]** |
| error message resolver | 0x8dca | 0x46e50 | 149 | every `require!` message text (§2.2) | **[B]** |
| message formatter | 0x8932 | 0x44990 | 917 | formats the `fmt::Arguments` record into the message | **[B]** |
| AnchorError box | 0x15a4e | 0xad270 | 17 | 0xa0-byte box, used at `0x5f18`, `0x5f5a`, `0x6511`, `0x6546`, `0x657b`, `0x6617`, ... | **[B]** |
| panic_fmt | 0x178c8 | 0xbc640 | 26 | the `Display` failure path | **[B]** |
| panic with location | 0x176d7 | 0xbb6b8 | 17 | `0x6b1b` (v2 borrow-length assertion, record `0xc8a98`) | **[B]** |
| drop / drop_in_place | 0x1ec6 / 0x17148 / 0x1424 | 0xf630 / 0xb8a40 / 0xa120 | 178 / 41 / 26 | the `AccountInfo` clone and `RefCell` unwinds | **[B]** |
| borrow-data length | 0x1652f | 0xb2978 | 8 | `data` pointer/len of an `AccountInfo` (`0x250f`, `0x67af`) | **[B]** |

### 7.6 What this section still leaves open

Status after tick t_c576e10d (section 9): items 1, 2 and 5 below are closed there, with the
measuring instruction for each. Items 3 and 4 are unchanged. **[B]**

1. `0x63a6`'s re-serialisation point (before the payout CPI, `0x60d5`) is measured; whether it
   is a space/realloc step or a plain write is **[partial]** (no `realloc` CPI or System
   program call is reached from the body).
2. The conditional config write in v2 (`0x6a6b` `and64 r2, 1`) is measured as a byte test; the
   producing byte inside the 0x6134 / 0x6b1e results is **[partial]**.
3. The 6011 variant name (`TooManyShareholders`) is **[R]** because the message leaf is the
   pooled `format` string (§2.2); the *predicate* (`len <= 10`) is **[B]**.
4. Field *names* inside `SharingConfig` are **[R]** where §3.1 still marks `+0x5a`/`+0x5b`
   **[partial]**; the byte the version gate reads (`+0x5b`) is **[B]**.
5. The per-account `+0x5a` byte read inside 0x6134 (`0x61b2`) still has **[partial]** meaning:
   the two paths it selects are not yet distinguished in the walk.

## 8. SUBLANE B follow-up (tick t_b66911d0): the four 6.9 open items

Status after this walk: item 3 and item 4 are closed on the deployed bytes, item 2 is measured
down to the byte layout of the returned record with its Rust type name left **[partial]**, item 1
is narrowed to a single-writer chain and stays **[partial]** with the one missing measurement
named at the end. Nothing here is a PR or a push: it is a local handoff for binary re-verification.

### 8.1 Item 4 closed: the v2 token leg issues SPL `TransferChecked` (tag 12)

The form of the discriminator in the 6.9 wording ("8-byte discriminator immediate") does not
match the bytes. Measured shape:

| where | bytes | reading |
|---|---|---|
| `0x14dba` (272 insns) | helper reached from `0x3cdd`, `0x4700` (v2 claim body, token leg) and `0x7c18` | token transfer helper: builds instruction, 4 account infos, invoke |
| `0x14dcc -> 0x151ad` (184 insns) | `r1 = fp-0xc0` (out), `r2 = [args+0x18]`, `r3 = [args+0x48]`, `r4 = [args+0x78]`, `r5 = fp` | instruction builder, called with the token program key in `r2` |
| `0x151b6` | `memcmp(r2, 0xc3760, 0x20)` | compared against `TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb` (Token-2022) **[B: `fees_b58.py 0xc3760`]** |
| `0x151c8` | `memcmp(r2, 0xc3640, 0x20)` when the first compare differs | `TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA` (classic SPL Token) **[B]** |
| `0x151ce` | `jne r0, 0` after both compares | neither program id -> error branch |
| `0x151d2` | `stw [r10 -0x50], 0xc` | the spl-token instruction enum tag, 4-byte store of 12 |
| `0x151d1` | `stxdw [r10 -0x48], r2` | amount, `u64` |
| `0x151d0` | `stxb [r10 -0x40], r3` | decimals, `u8` |
| `0x151d7 -> 0x1505d` (336 insns) | `r1 = fp-0x80`, `r2 = fp-0x50` | the spl-token packer, switching on the tag at `[r7+0x0]` (`ldxw r1, [r7+0x0]` at `0x15065`) |
| `0x1509f` | `jeq r1, 0xc, +0x4b` -> `0x150eb` | tag 12 leaf |
| `0x150eb`..`0x150f0` | `ldxdw r1,[r7+0x8]`; `ldxb r2,[r7+0x10]`; `stxb [r0+0x9], r2`; `stxdw [r0+0x1], r1`; `stb [r0+0x0], 0xc`; `mov64 r8, 0xa` | writes `[12][amount u64 LE][decimals u8]`, length 10 |
| `0x150a9` -> `0x15133`..`0x15137` | `stb [r0+0x0], 0x3`; `mov64 r8, 0x9` | control: tag 3 = `Transfer`, length 9 (amount only) |
| `0x150aa`..`0x150ad` | `stb [r0+0x0], 0x4`; length 9 | control: tag 4 = `Approve` |
| `0x15103`..`0x15108` | `stb [r0+0x0], 0xf`; length 0xa | control: tag 15 = `BurnChecked` |
| `0x14df3` / `0x14df8` / `0x14dfd` / `0x14e02` | four `memcpy(dst, src, 0x30)` from `[args+0x48]`, `[args+0x78]`, `[args+0xa8]`, `[args+0xd8]` | four 0x30-byte account infos staged for the CPI |
| `0x14e0d` / `0x14e0e` | `mov64 r4, 0x4`; `call 0x161ae` (108 insns) | invoke with 4 accounts |

So the CPI is `transfer_checked`: the 10-byte data `[0x0c, amount, decimals]` is unambiguous, and
4 account infos (source, mint, destination, authority) is the `transfer_checked` meta set
**[B for the data and the count]**, **[R for the four role names]**.

The decimals argument is read in the v2 claim body itself: `0x46f8` `ldxdw r1, [r7 +0x120]`,
`0x46f9` `ldxb r4, [r1 +0x30]`, then `r2 = fp-0x2b0`, `r3 = r8`, `call 0x14dba` at `0x4700`. That
closes the `+0x120 / [+0x30]` row of 6.1: the byte at `+0x30` of the object behind `ctx+0x120`
is the decimals passed to `TransferChecked`, i.e. the quote mint's decimals byte
**[B for the read and the pass-through]**, **[R for naming it `quote_mint.decimals`]**.

### 8.2 Item 3 closed: the four raise sites inside `0x76be` (739 insns)

The code immediates the earlier pass could not find are stored into the AnchorError origin record
one instruction before the box is built. Layout of that record, measured on all four sites:
`[fp-0x1e8]` = file path pointer, `[fp-0x1e0]` = file path length `0x36` = 54 =
`programs/pump-fees/src/instructions/fee_sharing/mod.rs` (**[B: `fees_hex.py 0xc44bd`]**),
`[fp-0x1d8]` = line, `[fp-0x1a0]` = column `0x2`.

| raise site | code store | code | line store | line | col | error |
|---|---|---|---:|---|---:|---:|---|
| `0x772c` | `stw [fp-0x158], 0x178d` | 6029 | `0x772e` `stw [fp-0x1d8], 0x12b` | 299 | 2 | `Account type not supported` |
| `0x779f` | `stw [fp-0x158], 0x7d6` | 2006 | `0x77a1` `stw [fp-0x1d8], 0x111` | 273 | 2 | `ConstraintSeeds` |
| `0x780c` | `stw [fp-0x158], 0x178e` | 6030 | `0x7809` `stw [fp-0x1d8], 0x132` | 306 | 2 | `Mint does not match quote mint` |
| `0x7866` | `stw [fp-0x158], 0xbc4` | 3012 | `0x7868` `stw [fp-0x1d8], 0x116` | 278 | 2 | `AccountNotInitialized` |

The column is the constant `0x2` stored at `0x772d`, `0x77a0`, `0x7808` and `0x7867`
(`stb [r10 -0x1a0], 0x2`), and the file pointer is reloaded at `0x7729`, `0x779c`, `0x7805` and
`0x7863` **[B]**.

Both records the 6.9 item asked about therefore do carry a code, and it is not an immediate of a
`require!` site but an entry of the packed error record handed to `0x16068` (242 insns):

* `mod.rs:273`: `0x7780`/`0x7781` `r2 = fp-0xb8`, `0x7782` `lddw r1, 0xc3e64`, `0x7784` `call 0x16068`.
  The record's first `u32` is `0x7d6` = 2006, which is exactly the code stored at `0x779f`
  **[B: `fees_hex.py 0xc3e64`]**. The return word is tested at `0x7785` `jeq r0, 0` -> `0x7790`
  (the raise block); a non-zero return falls into `0x7786`, which formats
  `a Display implementation returned an error unexpectedly` (`0xc387d`) through `0x178c8` (26).
* `mod.rs:278`: `0x7769` `lddw r1, 0xc3e24`, `0x776b` `call 0x16068`, first `u32` of the record
  `0xbc4` = 3012 = the code stored at `0x7866` **[B: `fees_hex.py 0xc3e24`]**, return word tested
  at `0x776c` `jeq r0, 0` -> `0x7857` (the raise block, `0x7857`..`0x7873`).
* the two other sites keep their own records: `0xc3e7c` for 6029 at line 299 (resolved through
  the FeeError message resolver `0x8dca` at `0x7718`, panic guard at `0x771b`/`0x771c`) and
  `0x7805`'s record for 6030 at line 306.

`0x13c3` is not a domain helper: it is the `Drop` glue of an accounts struct. Its 97 instructions
are a chain of `Rc` borrow-counter decrements (`[x-1]` / `[x-1/8]` pairs at struct offsets
`+0x8/+0x10`, `+0x38/+0x40`, `+0x68/+0x70`, ...), and both call sites drop the same stack
temporary at `fp-0x1f0`: `0x7992` on the invoke-Ok path (result tag compared with
`-0x7fffffffffffffe6` at `0x798b`) and `0x79af` on the invoke-error path (error built by
`0x15a5f` at `0x79aa`). They bracket the six-account invoke at `0x798a` (`0x161a9`, 5 insns,
`mov64 r4, 0x6` at `0x7989`) **[B]**.

### 8.3 Item 2 measured: the `0xd8` block is one `Result` shared by both bodies

Every successful leg of both bodies ends with the same store:

* v1 `0x426e`..`0x4272`: `memcpy(r1 = r6 /* out */, r2 = fp-0x238, r3 = 0xd8)`.
* v2 `0x4657` (native leg) and `0x47d4` (token leg): `memcpy(r1 = r6, r2 = fp-0x2b0, r3 = 0xd8)`.

The wrappers prove the internal layout of those `0xd8` bytes:

| field | v1 anchor | v2 anchor | reading |
|---|---|---|---|
| word at `+0x00` | `0x13bb4` `lddw r1, -0x7fffffffffffffff`; `0x13bb7` `jeq r7, r1` -> `0x13bf8` | `0x13cbe`/`0x13cc0` -> `0x13d09` | `Result` discriminant; `i64::MIN + 1` is the `Err` arm and lands on the Rc-drop then error-return block |
| Ok payload at `+0x18`, 0xc0 bytes | `0x13bbc` `mov64 r3, 0xc0`, `0x13bbd` `memcpy(fp-0x100, fp-0x380, 0xc0)` | `0x13cc5` `mov64 r3, 0xc0`, `0x13cc7` same memcpy from `fp-0x3b0` | the Ok value; `0x18 + 0xc0 = 0xd8` exactly |
| variant byte | `0x13bd9` `lddw r2, i64::MIN`; `0x13bdc` `stb [heap+0], 0x0` when equal, else `0x13c16` `stb [heap+0], 0x1` | `0x13ce2`/`0x13ce4`, `0x13ce5` `stb [r1+0x0], 0x0` | 2-variant discriminant written at the head of the return buffer |
| buffer | `0x13bc2`..`0x13bd6` 0x100 bytes on the bump cursor `0x300000000`, `[fp-0x398] = 0x100` cap | `0x13ccb`..`0x13cdf`, `[fp-0x3c8] = 0x100` | return-data buffer |
| publish | `0x13bde` / `0x13c17` `[fp-0x388] = 1`; `0x13c1c` `call 0xc685` (borsh append); `0x13c1e` reload `(ptr, len)`; `0x13c20` `call 0x1621c` -> `0x1651e` (2 insns, single relocated call) | `0x13ce6` `r2 = 1`; `0x13ce7` `call 0x1621c`; `0x13ced` `call 0xc607` (66) | `sol_set_return_data` shape: `(ptr, len)` where `len` is the writer length after the borsh append, not a constant |

Consequences for the declaration, stated at the level the bytes support:

* the body's declared return is a single `0xd8`-byte `Result` whose Ok value is a `0xc0`-byte
  record starting at `+0x18`, identical in both handlers **[B]**;
* the Ok value is a two-variant value: the wrapper writes byte `0` when the body's tag is
  `i64::MIN` (the three `msg!` + `Ok(None)` exits at v1 `0x4151`, `0x42a0` and the v2 twins) and
  byte `1` otherwise, then publishes it as return data **[B]**;
* in the byte-`1` case the record is appended by the borsh serialiser `0xc685` (257 insns),
  whose first two reads are `0xc68a` `ldxdw r9, [r7 +0x18]` (the first 8 bytes of the record,
  written as a `u64`) and `0xc699` `ldxdw r9, [r7 +0x10]` compared against `0xffffffff`
  (a `u32` element count) **[B for the reads]**;
* the Rust name and full shape of the record are **[partial]**: no type-name string is emitted
  for it, and the serialiser reaches one of its fields through the `Result` header copy at
  `fp-0x118` rather than through the record itself, so the field-to-offset map of the record is
  not recoverable from this path alone.

### 8.4 Item 1 narrowed: the third event key is a single-writer slot, still unnamed

Measured writers, both handlers:

| slot | only writer | source | body read |
|---|---|---|---|
| `ctx+0x278` (v1) | `0xc10d` `stxdw [r6 +0x278], r3` | `[fp-0x650]`, written once at `0xbef2` `stxdw [r10 -0x650], r3` | `0x41d5` `ldxdw r2, [r7 +0x278]`, 32-byte key staged at `fp-0x1d8`..`fp-0x1c0` |
| `ctx+0x2a0` (v2) | `0xc5de` `stxdw [r6 +0x2a0], r3` | `[fp-0x840]`, written once at `0xc236` `stxdw [r10 -0x840], r3` | `0x45bc` in the native leg, `0x43c8` `add64 r8, 0x2a0` for the token leg |
| `ctx+0x2a8` (v2, neighbour) | `0xc5dc` `stxdw [r6 +0x2a8], r3` | `[fp-0x850]`, written once at `0xc23f` | not read by the claim bodies |

The `r3` feeding `fp-0x650` / `fp-0x840` is the second word of the `Option<&AccountInfo>` returned
by the same monomorphised `next_account_info`, `0x21c6` (22 insns; it advances the accounts
cursor by `0x30` at `0x21d6`..`0x21d8` and raises 3005 through `0x1601e` with code `0xbbd` when
the cursor is empty), called at `0xbeb9` (v1) and `0xc231` (v2) **[B]**. The v2 neighbour
`ctx+0x2a8` comes from the following monomorph `0x235b` (69 insns) at `0xc23a`, which is the
variant that also reads the executable flag byte `[account+0x2a]` at `0x2378` **[B]**.

The account-name strings raised from the block that follows the `0xbeb9` step are
`recipient` (`0xc4c38`, len 9, at `0xbed3`), `fee_program_global` (`0xc4afc`, len 0x12, at
`0xbedc`) and `social_claim_authority` (`0xc4c4f`, len 0x16, at `0xbee5`), plus
`social_fee_pda` (`0xc4c41`, len 0xe, at `0xbe85`) earlier in the same body **[B]**. That trio
does not separate the slot: the three names are the targets of three different constraint errors
raised from the same block, and the rodata run is pooled and shared with the v2 body (it also
contains `quote_mint`, `associated_social_fee_pda`, `associated_recipient`,
`quote_token_program`), so its order cannot be read as v1's declaration order.

What the body does with the slot is fully measured: exactly one read per handler, used only for
the third 32-byte key of the emitted event, and the key order is the same in both handlers
(`ctx+0xb0`, `ctx+0x118`, `ctx+0x278` at v1 `0x41c0`/`0x41cb`/`0x41d5`; `ctx+0xb0`, `ctx+0x118`,
`ctx+0x2a0` at v2 `0x45a7`/`0x45b2`/`0x45bc`), so both instructions emit the same three-key
event **[B]**.

Still open, and the one measurement that would close it: a constraint error that is unique to the
account consumed at `0xbeb9` (the `has_one`/`seeds` pair is shared with the neighbouring fields),
or the declaration order of the v1 accounts struct from a source-side artefact. Until one of
those lands, the slot stays **[partial]** on its name only; its width, feed and use are settled.

**Closed in 8.5 below**: both of those routes landed on the following tick. The per-step failure
exits separate the three names (`0xbee3` is reachable from `0xbebd` alone), the IDL artefact times
out the declaration order, and the name is `social_claim_authority`, so the slot is no longer
**[partial]**.

Nothing in this subsection is a PR: local handoff only.

### 8.5 Item 1 closed: `ctx+0x278` (v1) and `ctx+0x2a0` (v2) are `social_claim_authority: Signer`

Five measurements now name the slot and they agree. None of them depends on the pooled rodata run
that 8.4 could not read.

**(a) the failure exit of that step is unique and it carries the name.** In `0xbe2e` the account
consumed at `0xbeb9` has exactly one failure exit: `0xbebc` `jeq r2, 0x2` falls through to `0xbebd`
`ja +0x25` -> `0xbee3`, and `0xbee3` is the block that formats `0xc4c4f` len `0x16` =
`social_claim_authority` (`0xbee5` `lddw r4`, `0xbee7` `mov64 r5, 0x16`, `0xbee8` `call 0x2b1`). A
branch census over the whole 748-insn body finds one instruction that targets `0xbee3`: `0xbebd`.
The v2 twin has the same shape: `0xc234` `jeq r2, 0x2` -> `0xc235` `ja +0x40` -> `0xc276`, which
formats `0xc4c4f` again at `0xc277`..`0xc27b`, and `0xc276` has no other predecessor **[B]**.

**(b) the monomorph called there is the `Signer` path.** `0x21c6` (22) advances the account cursor
by `0x30` (`0x21d6`..`0x21d8`) and on success calls `0x15970` (13), which performs exactly one
check: `0x15972` `ldxb r3, [r2 +0x28]`, and when that byte is zero it raises code `0xbc2` = 3010
(`0x15976` `mov64 r2, 0xbc2`, `0x15977` `call 0x1601e`). `+0x28` is the `is_signer` byte of the
`AccountInfo` layout this binary uses everywhere (`+0x28` signer, `+0x29` writable, `+0x2a`
executable: see the three byte reads `0xbef8`/`0xbefa`/`0xbefc` on `[r1 +0x2a]`, `[r1 +0x29]`,
`[r1 +0x28]` and their stores at `0xc107`/`0xc105`/`0xc103`, plus the recipient executable read
`0x4169` `ldxb r1, [r1 +0x2a]`). `3010` is
`AccountNotSigner`: the string sits in rodata at `0xc41a8` and the same mapping is used at
`docs/mayhem_map.md:311`. The Ok tag of this monomorph is `2` (`0x159971` `mov64 r1, 0x2`), which is
what `0xbebc` compares against **[B for the check, the byte and the code]**, **[R for the
ErrorCode name]**.

**(c) the declaration order of both handlers, from the IDL artefact this repo already loads.** The
file `evidence/upstream/pump_fees.json` (the `IDL` that `scripts/fees_admin_differential.py` loads)
declares, for `claim_social_fee_pda` (disc `e115fb85a11ec7e2`): `recipient`, `social_fee_pda`,
`fee_program_global`, `social_claim_authority`, `event_authority`, `program`, with
`social_claim_authority` the only `signer` entry; and for `claim_social_fee_pda_v2` (disc
`114df0863abc3595`): `recipient`, `social_fee_pda`, `quote_mint`, `associated_social_fee_pda`,
`associated_recipient`, `quote_token_program`, `associated_token_program`, `fee_program_global`,
`social_claim_authority`, `system_program`, `event_authority`, `program`, again with
`social_claim_authority` as the only signer. That artefact describes this build and not a
neighbouring one: its `SocialFeePdaClaimed` event discriminator `sha256("event:SocialFeePdaClaimed")
[..8]` = `0x3212c141edd2eaec` is present in the deployed `.so` as the immediate stored at `0xc665`
(`0xecead2ed41c11232`, memory bytes `32 12 c1 41 ed d2 ea ec`), and 8.6 lines that same struct's 13
fields up with the deployed serialiser read by read **[R for the names]**, **[B for the
artefact-to-binary tie]**. The tie covers the whole artefact, not one event:
`python3 tools/fees_idl_order.py verify` reports all 53 IDL discriminators (30 instructions, 23
events) located in the deployed image, and each one equals its own
`sha256("global:"|"event:" + name)[..8]` derivation, 0 absent **[B]**. The 8-byte values reach the
image as `lddw` immediates, which SBF encodes as two 4-byte halves, so a contiguous byte search
misses them; the 16-byte event-CPI pair at `0xc3dbf` is the one contiguous rodata case.

**(d) the v1 consumption order equals that declaration order.** Walking `0xbe2e` in body order:
`recipient` is inlined at `0xbe4b`..`0xbe53` (name `0xc4c38` len 9 formatted at `0xbed1`);
`social_fee_pda` at `0xbe7b` (monomorph `0x2342` -> `0xfab`, name `0xc4c41` len `0xe` at `0xbe88`);
`fee_program_global` at `0xbea2` (monomorph `0x22b4` -> `0xf33`, name `0xc4afc` len `0x12` at
`0xbeda`); `social_claim_authority` at `0xbeb9` (monomorph `0x21c6`, name at `0xbee3` as in (a));
`event_authority` inlined at `0xbebe` (its None exit formats `0xc4a24` len `0xf` at `0xbf1b`..
`0xbf26`); `program` at `0xbf05` (helper `0x353`, name `0xc4a33` len 7 at `0xbf0b`..`0xbf10`). Six
fields, six steps, the IDL order **[B]**. What 8.4 read as one pooled string run is in fact six
separate per-field error blocks, one per step: which of them a step can reach is decided by its own
`jeq`/`ja` pair, not by the order the strings sit in rodata.

**(e) the value lands at `ctx+0x278` / `ctx+0x2a0` and nowhere else, and the record confirms the
name.** One writer per body: `0xc10c` `ldxdw r3, [r10 -0x650]` then `0xc10d` `stxdw [r6 +0x278],
r3`, and `0xc5dd`/`0xc5de` for `0x2a0` in v2. The one body read of the slot is what the claim
record puts in its sixth borsh field, which the IDL names `social_claim_authority`: v1 `0x41d5`..
`0x41de` (32-byte copy from `ctx+0x278` into record payload `+0x48`), v2 native leg `0x45bc`..
`0x45c5`, v2 token leg `0x4733`..`0x473c` (both from `ctx+0x2a0`). The event's third key and the
record's `social_claim_authority` field are therefore the same account **[B]**.

The same walk settles the neighbouring slots, all by the identical test (consumption step -> the
failure exit that step alone can reach -> the name formatted there):

| slot | account | consumed at | failure exit and name | type evidence |
|---|---|---|---|---|
| v1 `ctx+0xb8` | `event_authority` | `0xbebe` (inlined) | `0xbf1b`, `0xc4a24` len `0xf` | inline `AccountInfo`, `0x30` bytes at `+0xb8` (`0xc124` store, flags at `0xc103`..`0xc107`) **[B]** |
| v1 `ctx+0x118` | `recipient` | `0xbe4b` (inlined) | `0xbed1`, `0xc4c38` len 9 | key read `0x41cb`, executable `0x4169` **[B]** |
| v1 `ctx+0xf0` | `program` | `0xbf05` (`0x353`) | `0xbf0b`, `0xc4a33` len 7 | **[B]** |
| v2 `ctx+0x120` | `quote_mint` | `0xc1a5` (`0x50`) | `0xc1c2`, `0xc4c65` len `0xa` | closes the 6.1 name **[B]** |
| v2 `ctx+0x128` | `associated_social_fee_pda` | `0xc1d1` (inlined) | `0xc25b`, `0xc4c6f` len `0x19` | **[B]** |
| v2 `ctx+0x130` | `associated_recipient` | `0xc1db` (inlined) | `0xc1e3`, `0xc4c88` len `0x14` | **[B]** |
| v2 `ctx+0x138` | `quote_token_program` | `0xc208` (`0x24`) | `0xc252`, `0xc4c9c` len `0x13` | closes the 6.1 pair **[B]** |
| v2 `ctx+0x140` | `associated_token_program` | `0xc211` (`0x23a0`) | `0xc264`, `0xc4bdc` len `0x18` | closes the 6.1 pair **[B]** |
| v2 `ctx+0x148` | `fee_program_global` | `0xc21a` (`0x22b4`) | `0xc26d`, `0xc4afc` len `0x12` | **[B]** |
| v2 `ctx+0x2a8` | `system_program` | `0xc23a` (`0x235b`) | `0xc27f`, `0xc4a3a` len `0xe` | `0x235b` requires the executable byte (`0x2378` `ldxb r1, [r8 +0x2a]`) **[B for slot and name]**, **[R for the `Program` typing]** |

Two rows of 6.1 change status here: `+0x120` moves from **[R]** to **[B]** on its name, and the
"**[partial]** token program / ATA program pair" at `+0x138`/`+0x140` closes as
`quote_token_program` / `associated_token_program`. One measured detail of the two `0x353` helpers:
their Ok tag is `2` and the *failure* branch is the one taken on `jeq ..., 0x2` (`0xbf08`..`0xbf0a`
in v1, `0xc246`..`0xc248` in v2), which is the opposite of the `0x21c6` convention.

### 8.6 Item 2 closed: the `0xc0` Ok record is the borsh image of `SocialFeePdaClaimed`

`0xc685` (257) is the compiler's `BorshSerialize` for one fixed struct: `r1` is the record base,
`r2` is the output `Vec<u8>` (capacity at `+0x0`, pointer at `+0x8`, length at `+0x10`), and it
returns `0` on success (`0xc786` `mov64 r0, 0x0`) or `0x1400000003` when a `Vec` length does not fit
a `u32` (`0xc697` loads that word, `0xc69a`/`0xc69c` compare a length against `0xffffffff`). Its 13
reads, in order:

| # | insn | read | bytes written | borsh field (IDL order) |
|---:|---|---|---:|---|
| 1 | `0xc68a` | `ldxdw r9, [r7 +0x18]` (stored `0xc694`) | 8 | `timestamp: i64` |
| 2 | `0xc699` | `ldxdw r9, [r7 +0x10]` length (stored as `u32` at `0xc6ad`), source `ldxdw r4, [r7 +0x8]` at `0xc69d` (copied `0xc6bd`) | `4 + len` | `user_id: string` |
| 3 | `0xc6cb` | `ldxb r4, [r7 +0xd0]` (stored `0xc6cc`) | 1 | `platform: u8` |
| 4 | `0xc6cf` | `add64 r9, 0x20`, 32 bytes at `0xc6dd`..`0xc6e4` | 32 | `social_fee_pda: pubkey` |
| 5 | `0xc6e7` | `add64 r9, 0x40`, 32 bytes at `0xc6f2`..`0xc6f9` | 32 | `recipient: pubkey` |
| 6 | `0xc6fa` | `add64 r9, 0x60`, 32 bytes at `0xc70b`..`0xc712` | 32 | `social_claim_authority: pubkey` |
| 7 | `0xc717` | `ldxdw r9, [r7 +0x80]` (stored `0xc722`) | 8 | `amount_claimed: u64` |
| 8 | `0xc726` | `ldxdw r9, [r7 +0x88]` (stored `0xc72f`) | 8 | `claimable_before: u64` |
| 9 | `0xc735` | `ldxdw r9, [r7 +0x90]` (stored `0xc73e`) | 8 | `lifetime_claimed: u64` |
| 10 | `0xc745` | `ldxdw r9, [r7 +0x98]` (stored `0xc750`) | 8 | `recipient_balance_before: u64` |
| 11 | `0xc754` | `ldxdw r9, [r7 +0xa0]` (stored `0xc75d`) | 8 | `recipient_balance_after: u64` |
| 12 | `0xc75f` | `add64 r9, 0xa8`, 32 bytes at `0xc76f`..`0xc776` | 32 | `quote_mint: pubkey` |
| 13 | `0xc77a` | `ldxdw r7, [r7 +0xc8]` (stored `0xc783`) | 8 | `lifetime_stable_claimed: u64` |

Offsets above are relative to the record base the wrapper passes at `0x13c18` (`fp-0x118`), whose
first `0x18` bytes are the three words the body returned at `+0x00`/`+0x08`/`+0x10` (`0x13bbf`..
`0x13bc1`) and whose payload `+0x18`..`+0xd8` is the `0xc0` copy taken at `0x13bb8`. The read order
is the IDL's declaration order for `SocialFeePdaClaimed` field for field, with matching widths, so
the `0xc0` record is that struct and the names below are its IDL names **[R for names]**, **[B for
every offset and width]**.

Where every one of those 13 fields is written in the two bodies:

| borsh field | record | payload | v1 source | v2 source |
|---|---:|---:|---|---|
| `timestamp` | `+0x18` | `+0x00` | `[fp-0x320]`, set at `0x4119` from `[fp-0x210]` = the `unix_timestamp` of the `Clock::get` at `0x40d9` (the same value the rate-limit compare uses at `0x4107`), stored `0x41e6` | `[fp-0x508]`, stored `0x45cd` |
| `user_id` | `+0x08`/`+0x10` | n/a | `ctx+0x08`/`ctx+0x10` cloned by `0x17665` at `0x41bf` (alloc `0x142d0`, `memcpy` `0x184d9`, stores `0x17678`..`0x1767a`) | `0x45a6`, same helper |
| `platform` | `+0xd0` | `+0xb8` | `ctx+0xaa` read `0x41c2`, stored `0x41e5` | read `0x45a9`, stored `0x45cc` |
| `social_fee_pda` | `+0x20` | `+0x08` | `[ctx+0xb0]` key, `0x41c1`..`0x41ca` | `0x45a7`..`0x45b1` |
| `recipient` | `+0x40` | `+0x28` | `[ctx+0x118]` key, `0x41cb`..`0x41d4` | `0x45b2`..`0x45bb` |
| `social_claim_authority` | `+0x60` | `+0x48` | `[ctx+0x278]` key, `0x41d5`..`0x41de` | `0x45bc`..`0x45c5` (native leg), `0x4733`..`0x473c` (token leg) |
| `amount_claimed` | `+0x80` | `+0x68` | `[fp-0x328]` (the claimable amount computed `0x415f`..`0x4167`), stored `0x41ef` | `r9`, stored `0x45d5` |
| `claimable_before` | `+0x88` | `+0x70` | the same `[fp-0x328]`, stored `0x41ed`: the whole claimable balance is claimed, so the two fields carry the same value on this path | the same `r9`, stored `0x45d4` |
| `lifetime_claimed` | `+0x90` | `+0x78` | `ctx+0x18` after `+= amount` (`0x41b8`), read `0x41df`, stored `0x41ec` | `ctx+0x18`, stored `0x45d3` |
| `recipient_balance_before` | `+0x98` | `+0x80` | `lamports(recipient)` through `0x16520` at `0x4178`, kept in `[fp-0x330]` at `0x4179`, stored `0x41eb` | `[fp-0x4f0]`, stored `0x45d1` |
| `recipient_balance_after` | `+0xa0` | `+0x88` | the updated lamports cell re-read at `0x41b5`/`0x41b6`, kept in `[fp-0x348]` at `0x41b7`, stored `0x41e9` | `[fp-0x510]`, stored `0x45d0` |
| `quote_mint` | `+0xa8` | `+0x90` | four zero words at `0x41e0`..`0x41e3` (v1 has no quote mint account) | zeros in the native leg at `0x45c7`..`0x45ca`; the mint key in the token leg, `[ctx+0x120]` -> `[+0x58]`, `0x473d`..`0x4748` |
| `lifetime_stable_claimed` | `+0xb0` | `+0xb0` | `ctx+0x28`, read `0x41e4`, stored `0x41e7` | `ctx+0x28`, stored `0x45ce` |

Memory layout of the `0xd8` block, measured from those store offsets and identical in both bodies:
capacity word `+0x00`, `String` pointer `+0x08`, `String` length `+0x10`, `timestamp` `+0x18`,
`social_fee_pda` `+0x20`, `recipient` `+0x40`, `social_claim_authority` `+0x60`, `amount_claimed`
`+0x80`, `claimable_before` `+0x88`, `lifetime_claimed` `+0x90`, `recipient_balance_before`
`+0x98`, `recipient_balance_after` `+0xa0`, `quote_mint` `+0xa8`, `lifetime_stable_claimed`
`+0xc8`, `platform` `+0xd0`, and `0x18 + 0xc0 = 0xd8` exactly. The memory order is not the borsh
order (`platform` is third in borsh and last in memory), which is why the serialiser offsets and the
store offsets differ: every read of `0xc685` lands on a word the body wrote, and every field the
body wrote is read once by the serialiser.

Word `+0x00` is the one word of the block that `0xc685` never reads, and it is what the wrapper
tests: `0x13bd9` `lddw r2, i64::MIN` with `0x13bdb` `jne r7, r2` selecting the payload branch at
`0x13c16`, and `0x13bb4` `lddw r1, i64::MIN + 1` with `0x13bb7` `jeq r7, r1` selecting the error
return at `0x13bf8`. The early exits write those constants themselves: `0x40f6` `lddw r1,
i64::MIN + 1` for every error fold into `0x40f4` (including the `err!` 6021 disabled exit built at
`0x40f1`), and `0x42a0` `lddw r1, i64::MIN` before the jump to `0x40f8` for the three no-claim
exits (`0xc4040` rate limit at `0x4151`, `0xc4059` "No fees available to claim" at `0x4298`,
`0xc4073` recipient-executable at `0x429c`). On the claim path `[r6+0x0]` carries the `user_id` byte
length written by `0x1767a`, so neither compare can fire there.

The wrapper then publishes borsh(`Option<SocialFeePdaClaimed>`): variant byte `0` alone when the tag
is `i64::MIN` (`0x13bdd` `stb [r1 +0x0], 0x0` with `[fp-0x388] = 1` at `0x13bde`), and variant byte
`1` followed by the 13-field body when it is not (`0x13c16` `stb [r1 +0x0], 0x1`, append through
`0x13c1c` `call 0xc685`, publish at `0x13c20` `call 0x1621c` with `(ptr = [fp-0x390], len =
[fp-0x388])`). One byte for variant 0 and one byte plus payload for variant 1 is exactly borsh's
`Option<T>` encoding **[B]**, so both bodies are declared as returning
`Result<Option<SocialFeePdaClaimed>>` **[R for the Rust spelling]**.

The same record is also the event: `0xc64d` (48) allocates a `0x100` buffer, writes the 8-byte event
discriminator at `0xc667` (`0xecead2ed41c11232`, memory bytes `32 12 c1 41 ed d2 ea ec` =
`sha256("event:SocialFeePdaClaimed")[..8]`), appends the same record through `0xc685` at `0xc66d` and
returns `(cap 0x100, ptr, len)`. The bodies call it twice, `0x41f3` (v1) and `0x45da` / `0x476c`
(v2), and publish the result through `0x161a7` at `0x41fa` / `0x45e2` (the `sol_log_data` shape),
while the self-CPI data is built from the 16-byte pair at `0xc3dbf` (`0xe445a52e51cb9a1d`, the
Anchor event-CPI tag, then `0xf19a6d0411b16dbc`) at `0x4209` / `0x476d`. No event name string is
emitted anywhere, so the names come from the IDL artefact and every offset and width from the
serialiser **[R for names]**, **[B for offsets]**.

Two wordings stay conservative and are labelled at the site: the word `+0x00` serves both as the
enum tag slot and as the `String` capacity word, which is measured behaviour and not a claim about
the declared enum, and the fact that the v2 native leg zeroes `quote_mint` while the token leg fills
it is recorded as measured behaviour without a claim about intent.

### 8.7 Sublane B retired

Sections 6, 8.1 through 8.6 now cover, on the deployed bytes: both wrappers (`0x13b5d`, `0x13c64`),
both bodies (`0x40d1`, `0x4308`) block by block, the accounts struct of each handler down to every
slot the bodies read, and the return record down to every borsh field. The 6.9 items are all closed:
item 4 (token leg `TransferChecked`, tag 12) in 8.1, item 3 (four raise sites in `0x76be` with codes
and `file:line:col`) in 8.2, item 2 (the `0xd8` return, its `0xc0` payload, its 13 borsh fields) in
8.3 and 8.6, item 1 (`ctx+0x278` / `ctx+0x2a0` = `social_claim_authority`) in 8.4 and 8.5. No
**[partial]** is left on a sublane B body, helper, layout or record; the only **[R]** items that
remain are names taken from the IDL artefact, and each is labelled at the site where it is used.

One accounting refinement for the file: the accounts struct the wrapper hands to the body is `0x280`
bytes in v1 and `0x2b0` in v2, not `0x268` / `0x298`. The wrapper writes the first `0x18` bytes word
by word (`0x13b97`..`0x13b9a` move the three words out of `fp-0x618`/`fp-0x610`/`fp-0x608`, then
`0x13ba2`/`0x13ba3` stores the address `fp-0x618` into `Context+0x08`) and memcpy's the remaining
`0x268` (`0x13b96`) / `0x298` (`0x13c9e`) into `fp-0x600` and its v2 twin, which is `ctx+0x18`. So
`0x18 + 0x268 = 0x280` and `0x18 + 0x298 = 0x2b0`, and the largest field the v1 try_accounts writes
is `r6+0x278` (`0xc10d`) while v2's is `r6+0x2a8` (`0xc5dc`), which is what fixes both totals. Every
body read in 6.1 uses the same base, so the 6.1 table is unaffected.

New local tool this tick (untracked, additive): `tools/fees_idl_order.py`, which prints the IDL
declaration order of any instruction (ordered account list with signer/writable flags) or of any
event (ordered borsh field list with widths), recomputes `sha256("global:"|"event:" + name)[..8]`,
and verifies the whole artefact against the deployed image (`verify` mode: 53 of 53 discriminators
located, 0 absent). It is what produced the name side of 8.5 and 8.6.

Nothing in this subsection is a PR: local handoff only.

## 9. SUBLANE A follow-up (tick t_c576e10d): 7.6 items 1, 2 and 5 closed on the bytes

Scope of this section: the two update handlers and the helpers they call, only. It closes the
three helper-level items that 7.6 left open, records two structural corrections that belong next
to 7.1, and leaves 7.6 items 3 and 4 exactly where they were (item 4 is a layout question owned
by section 3.1). Tags as in the header **[B] / [R] / [partial]**. Nothing here is a PR or a push.

Bodies re-walked for this section, all with `python3 tools/fees_body.py <addr>` on
`evidence/original/pump_fees/deployed.so`: `0x6134` (597 insns), `0x6b1e` (786), `0x63a6` (202),
`0x989` (132), `0x6479` (669), `0x6e50` (671), `0x5e6f` (696), `0x673a` (974).

### 9.1 Item 5 closed: the `+0x5a` byte inside 0x6134 is `remaining[i].executable`

The sentence at the end of 7.4.8 ("a per-account byte at `+0x5a`, read at `0x61b2`, selects the
advance path") measured the right instruction against the wrong base. The byte is a field of the
accounted element, at element offset **0x2a**:

* `0x6182..0x618e`: `mov64 r8, r6` then `add64 r8, -0x30` with `r6 = r2` = the remaining-accounts
  pointer, so the walk base is `remaining - 0x30`; `mov64 r1, r7` / `mul64 r1, 0x30` /
  `add64 r8, r1` then gives `r8 = remaining + (i-1) * 0x30` at the top of iteration `i`.
* `0x619d`: `ldxdw r9, [r8 + 0x30]` is the key pointer of `remaining[i]`; `0x619e..0x61a5` copy
  the 32 bytes at `[r9]` to `fp-0x118`, and `0x61ab` compares them with the shareholder address
  (`sol_memcmp_` `0x184e6`, `r3 = 0x20`).
* `0x61b2`: `ldxb r1, [r8 + 0x5a]`, and `0x5a = 0x30 + 0x2a`, so the byte read is
  `remaining[i] + 0x2a`. `0x61b3` then does `add64 r8, 0x30`, which is why the same element is
  read afterwards as `[r8 + 0x28]`, `[r8 + 0x29]` and `[r8 + 0x2a]` (`0x61ea..0x61f1`).
* The same three offsets are written into the cloned `AccountInfo` at `0x6207..0x620c`
  (`stxb [r2 +0x2a]`, `stxb [r2 +0x29]`, `stxb [r2 +0x28]`), and the v1 body reads that same
  triple off an `AccountInfo` at `0x5e8b..0x5e8d` and stores it at `0x5e8e..0x5e90`. So
  element +0x28 = `is_signer`, +0x29 = `is_writable`, +0x2a = `executable`.
* The v2 twin reads the same field with no base correction at `0x6ba8`
  (`ldxb r1, [r7 + 0x2a]` with `r7 = remaining + i * 0x30`), which pins the identity of the
  0x6134 read independently of the base arithmetic above.

Control effect **[B]**: `0x61b6` (`jeq r1, 0x0 -> 0x61b8`) enters the push block only when the
byte is 0 and otherwise jumps back to the loop head `0x618f`; `0x6bac`
(`jeq r1, 0x0 -> 0x6bba`) is the same test in 0x6b1e. The matcher therefore drops any matched
remaining account whose `executable` byte is set, from both of its working vectors (the
shareholder copy and the `AccountInfo` copy), and keeps scanning.

Tags: byte identity and both gate sites **[B]**. Why the source filters executable accounts was
**[partial]** here: the bytes prove the filter and no string or check name survives for it. What the
drop costs and what it keeps valid is measured in 11.3, which supersedes this closing sentence.

### 9.2 Item 2 closed: the flag at record `+0x18`, its writers, its consumers

The conditional write in v2 that 7.3.2 left **[partial]** is driven by a first-class byte of the
record that both matchers return. Measured stores:

| store | value | site |
|---|---:|---|
| 0x6134, non-normalising exit | 0 | `stb [r2 +0x18], 0x0` at `0x62a1` |
| 0x6134, normalising exit | 1 | `stb [r2 +0x18], 0x1` at `0x6399` |
| 0x6134, normalising exit, empty sub-case | 1 | `stb [r1 +0x18], 0x1` at `0x6369` |
| 0x6b1e, non-normalising exit | 0 | `stb [r2 +0x18], 0x0` at `0x6cda` |
| 0x6b1e, normalising exit | 1 | `stb [r2 +0x18], 0x1` at `0x6e3a` |
| 0x6b1e, normalising exit, empty sub-case | 1 | `stb [r1 +0x18], 0x1` at `0x6df2` |

The selector is a single comparison at the loop exit, between the working shareholder vector
length and the length the caller passed in:

* 0x6134 `0x6235..0x6238`: `ldxdw r1, [fp-0x1d0]` (the caller's `shares.len()`, stored at
  `0x6178`) and `ldxdw r2, [fp-0x198]` (the working length, zeroed at `0x6185`, updated at
  `0x61f6`), then `jeq r2, r1 -> 0x6239` when equal and the fallthrough `ja +0x112 -> 0x634b`
  when different.
* 0x6b1e `0x6c6f..0x6c71`: `ldxdw r2, [fp-0x1f0]` (working length, `0x6bd4`) against `r5`
  (`shares.len()`, `0x6b84`), `jeq r2, r5 -> 0x6c72` when equal, `ja +0x160 -> 0x6dd2` when not.

Because an element is only pushed when its `executable` byte is clear (9.1), the two lengths
differ exactly when at least one matched remaining account carried that byte. The "different"
exit is a repair path, and it is the path that sets the flag:

* bps renormalisation **[B]**: `0x6350..0x6364` walks the working vector at a 0x22 stride and
  replaces each `share_bps` with `bps * 0x2710 / total` (`mul64 r5, 0x2710` at `0x635b`,
  `div64 r5, r1` at `0x635c`), clamped to 0x2710 (`jlt r5, 0x2710` at `0x635d`), accumulating a
  u16 total that saturates at 0xffff (`0x6360..0x6363`). `0x636e..0x6376` writes 0 to every
  `share_bps` when the accumulated total is 0. `0x6377..0x638b` computes `0x2710 - total`
  (`0x637d`, `sub64 r3, r7`) and adds it to the last element's `share_bps` with a 0xffff clamp
  (`stxh [r8 +0x20], r3` at `0x638b`), guarded by the overflow panic at `0x6378` /
  `call 0x178af` with the location record `0xc8af0`. The 0x6b1e twin is the same ladder at
  `0x6dd2..0x6e15`.
* 0x6b1e adds one step the v1 helper does not have **[B]**: `0x6e16..0x6e2c` appends the
  remaining accounts that sit after the matched shareholder prefix to a second vector
  (size check at `0x6e1a`, `call 0x1b21` at `0x6e22`, `sol_memcpy_` at `0x6e2a` with the
  destination at `ptr + len * 0x30`), and the record tail then carries that vector's triple.

Consumers, measured:

* `0x63a6` at `0x63b1..0x63be`: after the `Err`-sentinel test at `0x63b4`/`0x63b6` it reads
  `ldxb r4, [fp-0x20]` (record `+0x18`), masks bit 0 with `and64 r4, 0x1` at `0x63bc`, jumps to
  the packer block `0x6443` when the bit is set and to the payout-vector block `0x63bf` when it
  is clear.
* the v2 body at `0x6a6b..0x6a6d`: `ldxb r2, [fp-0x2c0]` (record `+0x18`), `and64 r2, 0x1`,
  `jne r2, 0x0 -> 0x6afc`. At `0x6afc..0x6b07` the record's three leading words are stored into
  the SharingConfig object behind `accounts + 0x240` (`[obj +0x10] = r9`, `[obj +0x8] = r8`,
  `[obj +0x0] = r1`, the same three words loaded at `0x6a57..0x6a59`), and `0x989` is called on
  that object with `crate::ID` (rodata `0xc4ead`) in both id registers.

So the flag reads as "the matcher rewrote the shareholder vector, install it and re-serialise the
account". That settles the polarity question of 7.3.2: the conditional v2 write happens exactly
when the working vector lost an entry, that is when the shares needed the repair.

### 9.3 Item 1 closed: 0x63a6 re-serialises in place, with no realloc

0x63a6 calls the packer `0x989` at `0x644e` with `(out = fp-0x48, account object = r8,
crate::ID, crate::ID)`, both id registers holding rodata `0xc4ead`. The write itself is entirely
in place:

* `0x993`: `ldxdw r8, [r7 + 0x60]` loads the `AccountInfo` pointer the account object carries at
  `+0x60`; `0x995` and `0x99a` borrow its data (`call 0x15a40`, `call 0x16589`) and `0x99e`
  tests the borrow tag against `0x800000000000001a`.
* `0x9a1..0x9a5` build the writer as `(ptr, len)` from the borrowed data
  (`ldxdw r2, [r1 +0x0]`, `ldxdw r1, [r1 +0x8]`), so the capacity of every following write is
  the account's current data length.
* `0x9ab` writes the 8-byte discriminator (`lddw r2, 0xc3ddf` at `0x9a8`, `r3 = 8`), and
  `0x9c4..0x9f1` write the seven measured fields of section 3.1 through `call 0x15991`
  (`write_all` shape), ending with the shareholder vector at `0x9f1` (`0x1e6d`).
* the whole 132-instruction body contains no `sol_invoke_signed_c`, no `sol_alloc_free`, no
  `realloc` and no System-program CPI. The only indirect call is the `callx r2` drop at `0x9fd`.
* a write that does not fit lands at `0xa01`, builds the Anchor error with code `0xbbc` =
  **3004 `AccountDataTooSmall`** (`mov64 r2, 0xbbc` at `0xa03`, `call 0x1601e`) and returns it.

Answer to 7.6 item 1: plain write, no space and no realloc step. The account is written once,
bounded by the data length it already has, and a shareholder list that outgrows the account
yields 3004 instead of a resize. The reason this write sits between the AMM CPI (`0x60ce`) and
the payout CPI (`0x60d5` -> `0x72e5`) is **[partial]**. Measured: it only runs when the matcher
asked for a rewrite (9.2), and the wrapper calls the same packer again at `0x1392f` on exit, so
the early call commits the repaired shares before the payout leg runs.

Corrected reconstruction of 0x63a6, superseding the ordering in 7.4.7:

```rust
fn write_sharing_config<'info>(ctx: &Context, _prepared: &mut Prepared)
    -> Result<Payout<'info>>
{
    let cfg = ctx.accounts.sharing_config;                    // [ctx + 8], 0x63a9
    let matched = check_remaining_accounts(&cfg.shareholders, ctx.remaining_accounts)?;
                                                              // 0x6134 at 0x63b0
    if matched.rewrite {                                      // record +0x18, 0x63bb..0x63be
        cfg.exit()?;                                          // 0x989 at 0x644e, in place
        Ok(Payout { /* record tail words, 9.4 */ })            // 0x6451..0x6456
    } else {
        let payout: Vec<AccountInfo<'info>> =                 // 0x63c1..0x641f
            ctx.remaining_accounts.iter().cloned().collect();  // 0x30 stride, Rc bumps
        Ok(Payout { accounts: payout, /* 9.4 */ })            // 0x6420..0x6425
    }
}
```

### 9.4 The matcher record, as far as it is measured

Record base in the callers: `fp-0x38` in 0x63a6 (`0x63ae`), `fp-0x2d8` in the v2 body (`0x6a53`
and `0x6af1`). Offsets whose role the bytes settle:

| offset | measured use | tag |
|---|---|---|
| `+0x00` | the `Err` sentinel slot: both callers compare it with `0x8000000000000000` (`0x63b4`, `0x6a5a`) and take the error path on equality | **[B]** |
| `+0x00..+0x18` | the repaired shareholder vector, with the same word order the apply helpers install into the account (`cap@+0x00`, `ptr@+0x08`, `len@+0x10`, 9.5). Copied verbatim into the SharingConfig at `0x6afc..0x6aff` (`+0x10` to `+0x10`, `+0x8` to `+0x8`, `+0x0` to `+0x0`), and the packer reads `+0x8` as the element pointer and `+0x10` as the count (section 3.1 row 7) | **[B]** |
| `+0x10` | the count the v1 body tests for emptiness at `0x60df` | **[B]** |
| `+0x18` | the rewrite flag (9.2) | **[B]** |
| `+0x19..+0x38` | one 31 byte move through the unaligned frame mirror `fp-0x118`: 7 padding bytes (`+0x19..+0x1f`) then the extra-accounts vector triple. The mirror is staged at `fp-0x111/-0x109/-0x101` (`0x6393..0x6398`, `0x6e34..0x6e39`) and read back at `fp-0x118/-0x110/-0x108/-0x101` (`0x639a..0x63a1`, `0x6e3b..0x6e42`) | **[B]**, 11.1: the value is not a key, the 7 leading bytes are the first 7 bytes of the last matched element key and are read by nothing |
| `+0x20`, `+0x28`, `+0x30` | cap, pointer and length of the owned `Vec<AccountInfo>` of matched accounts. Empty vector writes `0 / 8 / 0` (`0x6366..0x636c`, `0x6def..0x6df5`); the non-normalising exits write the count and the exactly sized bump buffer (`0x629c..0x62a1`, `0x6cd5..0x6cda`); the normalising exits write the staged local vector triple (`0x6393..0x6398`, `0x6e34..0x6e39`) which the 31 byte move lands at these three offsets (`0x639b..0x63a1`, `0x6e3c..0x6e42`) | **[B]**, 11.2: consumer `0x1424` reads the length at `+0x10`, the pointer at `+0x08`, and walks at a `0x30` stride |

Two structural corrections to keep next to 7.1:

* the v1 body reaches its SharingConfig **inline** in the accounts object it is given:
  `[ctx + 0x08]` is that base, the version gate reads `[base + 0x5b]` at `0x5eb0`, the helper
  0x63a6 reads the shareholders at `[base + 0x8]` / `[base + 0x10]` (`0x63aa`/`0x63ab`), and the
  object carries its own `AccountInfo` pointer at `+0x60` (`0x993`).
* the v2 body reaches the same object **through a pointer** at `accounts + 0x240`
  (`0x673c..0x6740`, `0x6a4f`, `0x6afc`), so the v2 version gate reads
  `[[accounts + 0x240] + 0x5b]`. The helper 0x63a6 and the v2 body write the same in-memory
  layout through different addressing, which is why the two version gates are not at the same
  instruction shape.

### 9.5 The apply/event pair 0x6479 and 0x6e50 walked as a pair

7.4.11 described 0x6e50 by listing its raise sites next to 0x6479's. This tick compared the two
bodies instruction by instruction, which is a stronger result than a second independent walk:
**the two bodies are the same code with five substitutions**.

Method **[B]**: both bodies were dumped with `fees_body.py` (669 insns at `0x6479`, 671 at
`0x6e50`), every line reduced to `opcode + operands` with the call and branch displacements
erased (the resolved call target is kept), then aligned and compared position by position. The
alignment is exact up to the config install, the v1 install block is 5 instructions and the v2
one is 7, and from there the streams line up again with a +2 shift. 664 positions were compared
and 64 differ, in five groups and nowhere else:

| # | group | 0x6479 (v1) | 0x6e50 (v2) | positions |
|---:|---|---|---|---:|
| 1 | `file!()` pointer and length for every `require!` | `0xc4432`, `0x44` | `0xc4476`, `0x47` | 5 x 2 |
| 2 | `line!()` immediates | `0x102`, `0x103`, `0x10d`, `0x123`, `0x124` (258, 259, 269, 291, 292) | `0x124`, `0x125`, `0x12f`, `0x145`, `0x146` (292, 293, 303, 325, 326) | 5 |
| 3 | config install, `0x6641..0x6645` against `0x7018..0x701e` | direct on `r8` | through `ldxdw r1, [r8 + 0x240]` twice | 5 against 7 |
| 4 | first key the event carries | `ldxdw r2, [r8 + 0xc0]` at `0x667b` | `ldxdw r2, [r8 + 0x58]` at `0x7054` | 1 |
| 5 | second key, admin and version read for the event, `0x6685..0x669f` against `0x705e..0x7079` | straight off `r8` (`+0x60`, `+0x38..+0x50`, `+0x5b`) | off `r2 = [r8 + 0x240]` (the config pointee) for the admin and version, and the key through `[[r8+0x240] + 0x60]` | 46 |

Two further positions differ only in their branch displacement (`0x6639`, `0x6733`), a
consequence of the +2 shift. Everything else, including the five raise tuples, the allocator
calls, the `memcmp` pair, the `Clock::get` call, the event serialiser, the `invoke_signed`
emitter and the whole drop epilogue, is token-identical. **[B]**

So the reconstruction of 7.4.10 applies to 0x6e50 with substitutions 1, 3, 4 and 5, and with
these raised lines: `update_fee_shares_v2.rs:292` (6010), `:293` (6011), `:303` (6017),
`:325` (6014), `:326` (6012). Measured against the immediates in group 2 **[B]**.

Three details both bodies share, worth having in the handoff because 7.4.10 and 7.4.11
abbreviated them:

* the config install **[B]**: `0x663b..0x6640` moves the bump-allocator cursor to the compacted
  buffer and `sol_memcpy_`s the shareholder elements into it; `0x6641..0x6644` then writes the
  three-word vector as `[+0x00] = count`, `[+0x08] = buffer`, `[+0x10] = count`; `0x6645` sets
  `admin_revoked` with `stb [+0x59], 0x1`. The v2 twin is `0x7012..0x701e` through the pointer.
  `+0x08` and `+0x10` are exactly the two slots the packer reads back (section 3.1 row 7),
  which pins the in-memory vector word order for `SharingConfig` at
  `cap@+0x00, ptr@+0x08, len@+0x10` **[B]**. This is the same triple the matcher returns at
  record `+0x00..+0x18` (9.4), so the "three leading words of the record" are the cap, the
  pointer and the length of the repaired shareholder vector, in that order.
* the event **[B]**: `0x667a..0x669f` stage five inputs, the key of the account at
  `accounts + 0xc0` (v1) or `accounts + 0x58` (v2), the key of the account at
  `accounts + 0x60` (v1) or `[[accounts + 0x240] + 0x60]` (v2), the 32-byte admin pubkey from
  the config at `+0x38`, the version byte from the config at `+0x5b`, and the argument vector
  triple. `0x66a5` (`call 0xf498`, 136 insns) serialises the event body. The event
  discriminator is the first 8 bytes of rodata `0xc3dbf` = **`e445a52e51cb9a1d`**, materialised
  at `0x66b8..0x66bc`. `0x66cb` (`call 0x21dc`, 139 insns) and `0x66d0` (`call 0x19e3`, 30
  insns) assemble the payload. `0x66e7` (`call 0x16eb0`) serialises it and `0x6706`
  (`call 0x161ae`) emits it through `invoke_signed` with the `__event_authority` seed literal at
  rodata `0xc3ec2` (length `0x11`), the bump from `fp-0x2e8`, seed count 2 (`0x66f9`) and one
  signed seed (`0x66ff`). The v2 twin is `0x7053..0x70df`.
* the payload staging order is `[account@0xc0/0x58 key, account@0x60 key, admin, version,
  shareholders]`. Mapping those five groups onto Rust field names is **[R]** from
  `specs-fees/fees_specs.md`; the staging order and the discriminator are **[B]**.

### 9.6 What this tick left open (all three items 1 to 3 are closed in section 11)

1. The source of the block at record `+0x19` was **[partial]** here, closed in 11.1: it is a 31 byte
   tail move, 7 padding bytes plus the extra-accounts vector triple at `+0x20/+0x28/+0x30`.
2. The role of the three record words at `+0x20`, `+0x28`, `+0x30` was **[partial]** here, closed in
   11.2: cap, pointer and length of an owned `Vec<AccountInfo>`.
3. The reason for the executable-account filter stays **[partial]** by nature of the binary: 11.3
   measures what the drop costs and fixes the constraint against the sibling program's named error,
   but pump_fees carries no name for it. The filter and its two sites are **[B]**.
4. 7.6 items 3 and 4 are unchanged: item 3 is the 6011 name (`[R]`), item 4 belongs to the
   layout section 3.1 and is not re-opened here.

---

## 10. SUBLANE C follow-up (tick t_036b5475): relay payload, 0x500a equalities, event keys

Section 4.13 left three items open for the three C handlers. All three are walked here on the
deployed bytes of `pump_fees`; no A or B handler is touched and nothing in this section is a
PR. Addresses are instruction indices, bytes are `insn * 8`, and every constant below is
quoted from the disassembly of the deployed ELF.

### 10.1 Item 1 closed: the crank relay CPI, walked end to end in 0x8718

`0x8718` (528 insns, byte 0x438c0) is the whole relay call: it serialises the payload, builds
the 13 `AccountMeta` records, assembles the instruction and invokes. Entry registers, measured
at the only call site (`0x4b57`, inside body 0x483d):

| reg | value at 0x4b57 | meaning |
|---|---|---|
| `r1` | `fp-0x538` | out slot for the `Result<(), ProgramError>` pair |
| `r2` | `fp-0x3a0` | the staged account array minus 0x30 (first key read at `+0x30`, see below) |
| `r3` | `fp-0x448` | the instruction-args struct (built at `0x4871..0x48ae`) |
| `r4` | `fp-0x3e0` | the signer-seed array (4 slices) |
| `r5` | `4` | the number of seeds in that array |

The prologue `0x8718..0x871b` saves them (`r9 = r5`, `r8 = r4`, `r7 = r2`, `[fp-0x470] = r1`).

**Payload.** `0x83e7` (171 insns) is the serialiser; it is called once at `0x871f` with the
out descriptor at `fp-0x270` and the args struct in `r2`. Measured ladder, with the site of
each write:

| rel | field | size | source | sites |
|---|---|---:|---|---|
| `+0x00` | disc `78d939f187688bb8` | 8 | `lddw` of `-0x477497780ec62688` (unsigned `0xb88b6887f139d978`) | `0x83f6`, stored `0x83f8` |
| `+0x08` | `amount: u64` | 8 | args `+0x18` | `0x83fe`, stored `0x840c` |
| `+0x10` | `config_id: [u8;32]` | 32 | args `+0x20..+0x40` | `0x840f`, four stores `0x8420..0x8427` |
| `+0x30` | `0u16` | 2 | args `+0x60` | `ldxh` `0x842b`, `stxh` `0x8438` |
| `+0x32` | borsh `String` length | 4 | args `+0x10`, guarded by `> 0xffffffff` | `0x843b`, guard `0x843c..0x843e`, `stxw` `0x8453` |
| `+0x36` | borsh `String` bytes | n | args `+0x08` (pointer), `memcpy` thunk `0x184d9` | `0x843f`, `0x8466` |
| `+0x36+n` | fees program id | 32 | args `+0x40..+0x60` | pointer `0x8469`, four stores `0x8477..0x847e` |

Payload size = **86 + n** bytes, which reproduces the order `specs-fees` sec. 28 declares
(`disc`, `amount`, `config_id`, `0u16`, `"{base_mint},{creator}"`, fees program id) on the
bytes rather than from the spec **[B]**. The `String` itself is produced by the handler: the
`format` trait object at `0x175c5` is called at `0x4890` with the args struct as the output
slot and two placeholders (`stdw` immediates `0x2` at `0x488a` / `0x488b`), both arguments
formatted through the same impl at `0xb83a0`, and the piece table at `.data.rel.ro` `0xc8ad0`
resolves to the rodata run at `0xc40f7` whose first byte is `,`. That is a two-argument,
comma-separated `format!` **[B]**; the two argument identities stay **[R]** as
`base_mint` / `creator` per sec. 28.

**Instruction args struct (caller side, `0x4871..0x48ae`).** Each field lands at the offset the
serialiser reads:

| args off | value | site |
|---|---|---|
| `+0x08` / `+0x10` | `String` pointer and length, written by the `format` call | `0x488c..0x4890` |
| `+0x18` | `amount` from `[accounts + 0x318]`, zero -> the `Nothing to donate` exit at `0x4bd2` | `ldxdw` `0x486f`, `stxdw` `0x4891` |
| `+0x20..+0x40` | `config_id` from `[accounts + 0x48..+0x60]` (32 bytes) | `0x4849..0x484a`, copied `0x4871..0x4878` |
| `+0x40..+0x60` | `pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ` (this program) from four `lddw` | `0x4892..0x489d` |
| `+0x60` | `0u16` | `sth` `0x489e` |

The four `lddw` immediates at `0x4892..0x489d`, read in ascending memory order, decode to the
program id above **[B]** with `tools/fees_b58.py --hex`.

**Account metas.** `0x879b..0x8824`: the bump allocator at `0x300000000` reserves
`0x1ba = 442 = 13 * 34` bytes (`add64 r2, -0x1ba` at `0x87a1`, growth guard `0x300000008` at
`0x87ac`, the `0x175af` allocator panic at `0x892f`). Each record is 34 bytes; the key is a
32-byte copy and the flag pair is written as a **literal** `sth` at record `+0x20`, so the
signer/writable pattern is positional and not copied from the source `AccountInfo`:

| meta index | flag word | site |
|---|---|---|
| 0..4 | `0x0100` = not signer, writable | `0x87b8`, `0x87c1`, `0x87ca`, `0x87d3`, `0x87dc` |
| 5..6 | `0x0101` = signer, writable | `0x87e5`, `0x87ee` |
| 7..12 | `0x0000` = read only, not signer | `0x87f7`, `0x8800`, `0x8809`, `0x8812`, `0x881b`, `0x8824` |

The keys come from the 13 staged `AccountInfo` records: `ldxdw r2, [r7+0x30]` followed by a
0x30 stride up to `[r7+0x240]` (`0x8726`, `0x872f`, `0x8738`, `0x8741`, `0x874a`, `0x8753`,
`0x875c`, `0x8765`, `0x876e`, `0x8777`, `0x8780`, `0x8789`, `0x8792`), and each key pointer is
dereferenced for its 32 bytes. In body 0x483d those 13 records are assembled at
`fp-0x370 + 0x30k` from 13 distinct `&AccountInfo` fields of the accounts struct, reached at
`0x48af`, `0x48d1`, `0x48f3`, `0x4915`, `0x4937`, `0x495a`, `0x497c`, `0x499f`, `0x49c5`,
`0x49e7`, `0x4a0a`, `0x4a2f`, `0x4a5d` and reading the struct offsets `0x2a0`, `0x2b8`,
`0x2c0`, `0x2c8`, `0x298`, `0x2d0`, `0x000`, `0x270`, `0x2b0`, `0x288`, `0x280`, `0x278`,
`0x2a8`. The record-to-meta-index pairing and the per-slot account names stay **[partial]**.

**CPI target.** Four `lddw` at `0x8825..0x8830` materialise a 32-byte key on the frame and are
copied into the syscall struct as the program id. Ascending memory order gives
`063b9bd789fb8efd4b5fc757131b325ae2e386d549a259d9c3a8879a3655e694` =
`RLAYHr9TRFcKB2ubYQhspcnXiaGpaVzNQvHytt47RZu` **[B]**, which is the `address` the IDL declares
for `crank_donation_fee_pda` account `donation_relay_program` **[IDL cross-check]**.

**Instruction struct and invoke.** The struct is built at `fp-0x458`; the syscall wrapper reads
it at `+0x08` (accounts pointer), `+0x10` (accounts length), `+0x20` (data pointer), `+0x28`
(data length) and `+0x30` (program id, 32 bytes) at `0x164ac`, `0x164ba`, `0x164db`,
`0x164dc`, `0x164e5`/`0x164f4..0x164fb`. The matching stores in 0x8718 are `0x8834` (heap
pointer into the struct), `0x8835` / `0x8836` (the two 13 counts), `0x8832` (data pointer
word), `0x8831` (data length word) and `0x8825..0x8830`, with the allocator bump re-armed at
`0x87af`. The account-info array handed to the invoke is the 13
records cloned by `0x8496` (642 insns, one refcount bump per record) at `0x883d`, and the
signer slice is `{ptr = fp-0x2a8, len = 1}` staged at `0x883e..0x8841`. The single group at
`fp-0x2a8` is `{ptr = incoming r4 = fp-0x3e0, len = incoming r5 = 4}` (`0x8837`, `0x8838`).
The invoke chain is `0x8849` -> `0x161ae` (108 insns) -> `0x16214` -> `0x164a3` (121 insns)
-> `sol_invoke_signed_rust` at `0x16502` **[B]**. Success is the tag `2` written to the out
slot (`mov64 r6, 0x2` at `0x884a`, stores `0x892c`/`0x892d`, `exit` `0x892e`) and the caller
tests exactly that tag at `0x4b5c`. A failing invoke is wrapped by `0x15a5f` at `0x8853`.

**Signer seeds.** The four slices sit at `fp-0x3e0` with the 16-byte stride, filled in body
0x483d:

| seed | pointer | length | source | sites |
|---|---|---:|---|---|
| 0 | `0xc41d8` = `donation-fee-pda` | 16 (`0x10`) | rodata literal | `0x48a9`, length `0x48ae` |
| 1 | `fp-0x488` | 32 (`0x20`) | `[accounts + 0x68..+0x80]` | pointer `0x48a6`, length `0x48ad` |
| 2 | `fp-0x4a8` | 32 (`0x20`) | `[accounts + 0x48..+0x60]` | pointer `0x48a5`, length `0x48ac` |
| 3 | `fp-0xe8` | 1 | the byte `[accounts + 0xd8]` | pointer `0x48a2`, byte `0x48a1`/`0x48aa`, length `0x48ab` |

Those three values sit at the image ladder offsets of section 4.11.1 when the image base is
taken at the accounts struct itself: `config_id +0x48`, `base_mint +0x68`, `bump +0xd8`. The
IDL declares the `donation_fee_pda` PDA as `["donation-fee-pda", base_mint, config_id]` plus
the bump, so the measured order `[literal, +0x68, +0x48, +0xd8]` reproduces the declared
vector exactly **[B] with IDL cross-check**, and the PDA is signed with four seeds, one group.

Section 4.12.2's status line is therefore closed: the relay payload, the relay program id, the
13-meta list and the four seeds are all binary-grounded.

### 10.2 Item 2 closed: the quote-mint default and the account-key equalities in 0x500a

Body 0x500a holds three `sol_memcmp_` calls at `0x50d3`, `0x5101` and `0x5115`. Measured
operands and outcomes:

| site | left operand | right operand | on equality |
|---|---|---|---|
| `0x50d3` | the 32 bytes of the curve quote mint at `fp-0x300` (`0x509b..0x50a8`, serialised offsets `0x53..0x72`), or 32 zero bytes when `data_len < 0x73` (`0x5092..0x5096`) | an all-zero 32-byte frame buffer at `fp-0x200` (`0x50ca..0x50cd`) | `0x50df`: the quote mint is replaced by four `lddw` immediates |
| `0x5101` | the 32 bytes at `[accounts + 0xb8..+0xd8]`, copied to `fp-0x60` (`0x50eb..0x50f2`) | `key(AccountInfo at accounts + 0x368)` (`r9 = [fp-0x558]`, `0x50f3..0x50fb`) | `0x5165`: `owner` of that account (`[r9+0x18]`) must equal `0xc4ead` = `pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ`, match -> `0x5242`, mismatch -> the raise that formats `0xc3e00` and resolves the code through `0x8dca` (6007, the `:197` row of 4.11.1) |
| `0x5115` | `key(AccountInfo at accounts + 0x110)` (`r1 = [fp-0x560]`, `0x5106..0x510f`) | the same `fp-0x60` copy | `0x5187`: the two 32-byte values are packed into a 41-byte record at `fp-0x398`; mismatch falls into the 6007 raise formatted at `0x5119..0x511d` |

The four immediates at `0x50df..0x50e8` decode, in ascending memory order, to
`069b8857feab8184fb687f634618c035dac439dc1aeb3b5598a0f00000000001` =
`So11111111111111111111111111111111111111112` **[B]**. This corrects the wording of section
4.11.1 row 10: the WSOL default is materialised as four inline immediates at `0x50df..0x50e8`,
not loaded from the rodata constant `0xc3740`.

The sharing-config block `0x55de..0x5668` is two further equalities plus a byte gate:

| site | left operand | right operand | on mismatch |
|---|---|---|---|
| `0x55de..0x55f1` | `key(AccountInfo at accounts + 0x110)` (`0x55de..0x55e7`) | the 32 bytes staged at `fp-0x2c8` (`0x55ea`), part of the record copied to `fp-0x2b8` by the 0x68-byte `memcpy` at `0xd0b4` in `try_accounts` | line `0xd5 = 213` (`stw` `0x5600`), path length `0x4a` (`0x5601`), code `0x1780 = 6016` (`0x5603`), tuple boxed at `0x5608`, which is the `:213` row of section 4.11.1 (`0x55fc`) |
| `0x5634..0x5637` | `key(AccountInfo at fp-0x580)` (`0x5625..0x562e`) | the derived key staged at `fp-0xe0` (`0x5613..0x5624`) | line `0xae = 174` (`0x5646`), code `0x1778 = 6008` (`0x5649`), which is the `:174` row (`0x5642`) |
| `0x5669..0x566f` | the byte at `fp-0x2a7` | zero | `0x566f` calls the `err!` constructor `0x8d8b` with discriminant `0x9`, i.e. 6009 |

The accounts-struct slots these compares read are filled by `try_accounts` `0xcfe6` (1094
insns) at its epilogue `0xd424..0xd447`: `+0x368` from `fp-0x898` (`0xd424`), `+0x360` from
`fp-0x890` (`0xd426`), `+0x110` from `fp-0x818` (`0xd437`), `+0x118` from `fp-0x8b0`
(`0xd435`), `+0xb8` from `fp-0x880` (`0xd43b`), `+0xb0` from `fp-0x878` (`0xd43d`), and the
65-byte record copied from `fp-0x248` into `+0xc0` (`0xd411..0xd416`). The account names that
`try_accounts` itself prints sit at `0xd0a3` (`base_mint`, len 9), `0xd0ca` (`bonding_curve`,
len 0xd), `0xd0f2` (`sharing_config`, len 0xe) and `0xd0fb` (`config_id`, len 9), which
anchors the fetch order in that region of the deserialiser to the declared account list of
section 27 of `specs-fees`.

Mapped onto the ladder `specs-fees` sec. 27 declares (curve path or pool path -> `creator`,
then `creator == sharing_config key` -> validate with `owner == fees`, `admin == payer`,
`!admin_revoked`, `Active`, else `payer == creator`): the equality at `0x5101` is the
`creator == sharing_config` test (its owner gate at `0x5165` is the `owner fees` leg), the
equality at `0x5115` selects the second branch and the `0x55de` compare carries the `:213`
6007/6016 outcome the spec assigns to that validation. The mechanics are **[B]**; the two
compared struct slots keep **[R]** naming (`creator` from the derivation, the payer leg of the
ladder) because the accounts struct holds them in a pointer-shaped slot at `+0xb8` whose Rust
type is not settled:

* `+0xb8` receives a single word from `fp-0x880` at `0xd43b`, while the body reads the **32
  bytes** at `+0xb8..+0xd8` as a pubkey (`0x50eb..0x50f2`, and the packing at `0x5187..0x5196`
  re-reads the same 32 bytes as four unaligned pieces),
* and the 65-byte record copied to `+0xc0` at `0xd411` starts exactly at `+0xc0`, so the
  boundary between the slot at `+0xb8` and that record is measured but its declared shape is
  not.

That single ambiguity is the only thing this item still leaves open, and it is a naming
question, not a comparison-mechanics one.

### 10.3 Item 3 closed: the two keys of `SocialFeePdaCreated`

Body 0x5cd3 copies two 32-byte keys out of the accounts struct into the event block at
`0x5d13..0x5d25`: the first through the word at `[accounts + 0xb0]` (`0x5d13`, target
`fp-0x168`), the second through `[accounts + 0x118]` (`0x5d1d`, target `fp-0x148`). The fill
evidence for both slots is in `try_accounts` `0xe4d2` (860 insns):

| slot | written from | that slot was filled by | therefore |
|---|---|---|---|
| `+0xb0` | `fp-0x6f8` (`stxdw [r6+0xb0]` at `0xe83c`) | `r9 = [fp-0x360]` at `0xe6b3`, and the same `r9` is passed to the `Account<T>` deserialiser `0x1ec6` at `0xe6b5` (the only deserialisation in this instruction) | the `social_fee_pda` account |
| `+0x118` | `fp-0x428` (`stxdw [r6+0x118]` at `0xe826`) | the account returned by the **first** fetch of `try_accounts`, helper `0x21c6` at `0xe4f7`, stashed at `0xe4fc` | the first declared account, `payer` in the IDL order |

So `SocialFeePdaCreated` carries `social_fee_pda` and `created_by = payer` in that order, which
is the field order the event reconstruction already had; the two slots are now **[B]** and the
name mapping is fixed by the IDL order plus the single-deserialisation argument above. The
remaining event fields are unchanged from 4.8.1: `timestamp` (`[fp-0xa8]` of the `Clock` out
slot), `user_id` (`fp-0x188..fp-0x170`) and `platform` (`fp-0x128`).

### 10.4 Sublane C status after this tick

| handler | wrapper | body | helpers | open |
|---|---|---|---|---|
| `create_social_fee_pda` | **[B]** | **[B]** 389 insns, 27 measured steps (4.8.1) | every callee carries a deployed address (4.13) | none |
| `create_donation_fee_pda` | **[B]** | **[B]** 1641 insns, 23 measured phases (4.11.1), raise table in source-line order | same | the declared shape of the accounts slot at `+0xb8` (10.2), a naming question |
| `crank_donation_fee_pda` | **[B]** | **[B]** 1950 insns (4.12.1), relay CPI walked here | same | the per-index names inside the relay `AccountMeta` list (10.1) |

Tools used for this tick, all local under `tools/` and `scratch/`: `fees_walk.py` for the
annotated walks (`scratch/walk_8718.txt`, `scratch/walk_83e7.txt`, `scratch/walk_164a3.txt`,
`scratch/walk_cfe6.txt`), `SC_scan.py calls` for the callee census, `fees_b58.py --hex` plus
two small decoders (`scratch/c_imm.py`, `scratch/c_imm2.py`) for the inline 32-byte blocks,
`scratch/c_va.py` for a rodata pointer dump and `scratch/c_idl.py` / `scratch/c_idl2.py` for
the declared account order and addresses.

Severity: Informational
Sévérité : Informational
Severity justification: static reconstruction of three deployed handlers, no behaviour change and no impact measured on any deployed program.


---

## 11. SUBLANE A follow-up 2 (tick t_7c9b8dd6): the record tail, its three words, the executable filter

Scope: the two update handlers and the matcher helpers only. This section closes the three items
9.6 left open and touches nothing else. The brief named this section 10; section 10 was taken by the
SUBLANE C follow-up (tick t_036b5475) before this tick ran, so this is 11 and the 9.x lines it
supersedes are patched in place.

Bodies re-dumped for this section with `python3 tools/fees_body.py <addr>` on the deployed ELF:
`0x6134` (597 insns), `0x6b1e` (786), the record consumer inside `0x673a` (`0x6a4e..0x6b1a`),
`0x735a` (153) and `0x1424` (26). Every offset quoted below was re-decoded from the raw instruction
words (opcode, dst, src, signed 16 bit offset) rather than read from the annotated text, because the
first result turns on a one byte difference between two instruction offsets.

### 11.1 Item 1 closed: the block at record `+0x19` is 7 dead bytes plus the extra-accounts vector

9.4 described a 32 byte block written at `+0x19`. The bytes show a 31 byte move, and the moved value
is not a key. The two normalising exits write four words at `+0x19`, `+0x21`, `+0x29` and `+0x30`,
that is at 0, 8, 16 and 23 bytes from the field base:

| # | 0x6134 store | source load | 0x6b1e store | source load |
|---:|---|---|---|---|
| 1 | `stxdw [r2 +0x19]` at `0x639b` | `[fp-0x118]` at `0x639a` | `0x6e3c` | `[fp-0x118]` at `0x6e3b` |
| 2 | `stxdw [r2 +0x21]` at `0x639d` | `[fp-0x110]` at `0x639c` | `0x6e3e` | `[fp-0x110]` at `0x6e3d` |
| 3 | `stxdw [r2 +0x29]` at `0x639f` | `[fp-0x108]` at `0x639e` | `0x6e40` | `[fp-0x108]` at `0x6e3f` |
| 4 | `stxdw [r2 +0x30]` at `0x63a1` | `[fp-0x101]` at `0x63a0` | `0x6e42` | `[fp-0x101]` at `0x6e41` |

Three facts pin this as one move of `record+0x19..+0x38`, 31 bytes, not a 32 byte value: the source
offset of every word is a constant `0x131` above its destination, the spacing is 8, 8, 7 on both
sides, and the last destination word starts 23 bytes in, which is the overlapping tail chunk a byte
move of 0x1f bytes produces (the fourth word rewrites the last byte of the third). **[B]**

The frame mirror at `fp-0x118` is filled as follows. The three words the exit stages at `fp-0x111`,
`fp-0x109` and `fp-0x101` sit at `+7`, `+15` and `+23` inside that mirror, and they are the
(cap, ptr, len) triple of the working `AccountInfo` vector:

* 0x6134 takes them from `[fp-0x148]`, `[fp-0x140]`, `[fp-0x138]` (`0x6393..0x6398`). The same three
  slots are independently measured as cap, pointer and length of the 0x30 stride vector: `0x61f4`
  and `0x61f5` load `[fp-0x138]` and `[fp-0x148]` and compare them before the grow call on
  `fp-0x148` (`0x1ba9`), and `0x6205` computes `[fp-0x140] + n * 0x30` for the element write.
* 0x6b1e takes them from `[fp-0x160]`, `[fp-0x158]`, `[fp-0x150]` (`0x6e34..0x6e39`), and the roles
  are measurable in place: `0x6e19` reads `[fp-0x160]` and subtracts `[fp-0x150]` for the capacity
  check, `0x6e28` adds `[fp-0x158]` and `len * 0x30`, `0x6e2b` and `0x6e2c` add the appended count
  back into `[fp-0x150]`.

Because the mirror carries the triple at `+7/+15/+23`, the triple lands in the record at `+0x20`,
`+0x28` and `+0x30`, which are exactly the three words 9.4 listed as unknown.

The first seven bytes of the mirror are never written on this path. `fp-0x118` is the loop scratch
slot for the matched element's key: 0x6134 copies the 32 bytes at `[r9]` into
`fp-0x118/-0x110/-0x108/-0x100` at `0x619e..0x61a5` and memcmps them at `0x61ab`, and 0x6b1e does the
same at `0x6b96..0x6b9d` with the memcmp at `0x6ba2`. The staging starts at `fp-0x111`, one byte into
that slot, so key bytes 0..7 survive and are moved into the record. They are the record's padding and
no reader consumes them (11.1, consumer below). The overlap the brief flagged is therefore real but
harmless: those 7 bytes are the only part of the key that reaches the record, and nothing reads
`+0x19..+0x1f`.

The record layout is now fully measured. Size 0x38:

| offset | field | evidence |
|---|---|---|
| `+0x00` | cap of the repaired `Vec<Share>`, and the `Result` discriminant | from `[fp-0x130]` (`0x6391`, `0x6e32`); both callers compare it with `0x8000000000000000` (`0x63b4`, `0x6a5a`), and the error path writes that sentinel at `0x6d9d` |
| `+0x08` | pointer of that vector | from `[fp-0x128]` (`0x6390`, `0x6e31`) |
| `+0x10` | length of that vector | from `[fp-0x120]` (`0x638e`, `0x6e2f`); tested for emptiness in the v1 body at `0x60df` |
| `+0x18` | rewrite flag, one byte | 9.2 |
| `+0x19` | 7 bytes of padding | written only by the 31 byte move, filled with key bytes 0..7 (above) |
| `+0x20` | cap of the extra-accounts `Vec<AccountInfo>` | 11.2 |
| `+0x28` | pointer of that vector | 11.2 |
| `+0x30` | length of that vector | 11.2 |

The consumer settles it without any inference. The v2 body copies the same four words from
`record+0x21`, `+0x19`, `+0x29`, `+0x30` into `fp-0x38`, `fp-0x40`, `fp-0x30`, `fp-0x29`
(`0x6a5d..0x6a64`, again a constant `+0x59` shift, destination base `fp-0x40`), and then builds the
triple it actually uses from three loads one byte into those slots:

* `0x6a65`: `ldxdw r2, [fp-0x39]` to `[fp-0x58]`, and `fp-0x39` is `record+0x19+7 = +0x20`
* `0x6a67`: `ldxdw r2, [fp-0x31]` to `[fp-0x50]`, and `fp-0x31` is `record+0x21+7 = +0x28`
* `0x6a69`: `ldxdw r2, [fp-0x29]` to `[fp-0x48]`, and `fp-0x29` is `record+0x29+7 = +0x30`

So the consumer drops the 7 padding bytes and reads exactly the triple the producer staged. The same
one byte shift appears on the producer and the consumer side, which is what a 31 byte field move looks
like from both ends. **[B]**

What the v2 body then does with the triple **[B]**:

* `0x6a6e`: `ldxdw r1, [fp-0x48]`, and the distribution leg is skipped when that word is zero
  (`jeq -> 0x6b0c`), so the length of the vector gates the pump call.
* `0x6ab4` and `0x6ab6`: `fp-0x58` becomes slot 1 of the ten slot argument block at `fp-0xfc0`.
* `0x735a` reads it as a triple at `0x73b2..0x73b7` (`[r7+0x00]`, `[r7+0x08]`, `[r7+0x10]` with
  `r7 = fp-0x58`) and installs it at the head of its request struct (`fp-0x298`, `fp-0x290`,
  `fp-0x288`), next to a seven entry 0x30 stride account array built at `0x73bd..0x73c1` and four
  more accounts at `0x73d6..0x73e4`. The request then goes to `0x10ba8` at `0x73ec`, whose result the
  body tests against 2 at `0x6acf`.
* `0x6b15..0x6b17`: the triple is dropped through `0x1424`.

Answer to 9.6 item 1, on the bytes: the block is neither the account key, nor the config key, nor a
`Pubkey` built from the working vector. It is the tail of the record, flag byte written separately at
`+0x18`, seven bytes of padding, and an owned `Vec<AccountInfo>` whose (cap, ptr, len) sits at
`+0x20`, `+0x28`, `+0x30`. The vector is the matcher's clone list for the matched accounts, sized in
the prologue from the caller's shareholder count (0x6134: `0x6139..0x613a`, `0x6145`, cap at
`0x6156`; 0x6b1e: `0x6b28..0x6b29`, `0x6b4d..0x6b4f`), extended in the repair path by the append at
`0x6e16..0x6e2c` (v2 only). The 7 bytes at `+0x19` carry the first seven bytes of the last matched
element key and are consumed by nobody.

### 11.2 Item 2 closed: `+0x20`, `+0x28`, `+0x30` are cap, pointer and length of that vector

Three independent measurements fix the roles and the element type.

Empty vectors write a known constant body **[B]**. The empty sub-case of the repair path writes the
whole record from scratch, and the right half is `[+0x30] = 0`, `[+0x28] = 8`, `[+0x20] = 0`
(`0x6366..0x636c` in 0x6134, `0x6def..0x6df5` in 0x6b1e). The left half is `[+0x10] = 0`,
`[+0x08] = 2`, `[+0x00] = 0`. The two non-zero words are the dangling pointers Rust uses for a zero
length vector, and they equal the alignment of the element type: 8 for the 0x30 stride vector,
2 for the 0x22 stride share entry (32 byte address plus 2 byte bps). So `+0x28` is the pointer slot
and `+0x20` the capacity slot, in the same (cap, ptr, len) order 9.5 measured for the in-memory
`SharingConfig` vector.

The non-normalising exits write a full vector **[B]**. v1 at `0x629c..0x62a1` stores `+0x28` from
`[fp-0x1a0]`, and `+0x30` and `+0x20` from the same `[fp-0x188]`. `[fp-0x1a0]` is 8 when no accounts
remain (`0x6239`) and the bump-allocator base when they do (`0x623d..0x625d`), and `[fp-0x188]` is
arg3, the remaining-account count (`0x618a`), the same count the clone buffer is sized from
(`0x6139..0x613a` pointer arithmetic, `0x6145` size check). v2 is the same shape: `[fp-0x1c8]` is 8
at `0x6c72..0x6c73` or the heap base at `0x6c95`, and `+0x28`, `+0x30`, `+0x20` are written at
`0x6cd5..0x6cd9` from `[fp-0x1c8]` and `[fp-0x1a8]` (arg3, saved at `0x6b23`). Capacity equals length
equals the account count because the buffer is allocated to exactly that many 0x30 elements.

The consumer fixes the type **[B]**. `0x1424` is the drop the v2 body runs on the extracted triple
(`0x6b15`): it reads the length at `+0x10`, exits when it is zero (`0x1425`), sets the element cursor
to the pointer at `+0x08` plus `0x10` (`0x1426..0x1428`), walks at a `0x30` stride (`0x1429`) and
decrements two reference counts per element (`0x142d..0x143d`). There is no deallocation call, which
matches the bump allocator that produced the buffer. So the three words describe a `Vec<AccountInfo>`
of 0x30 byte cloned accounts, and the length word at `+0x30` is the same word the v2 body tests at
`0x6a6e` before it forwards anything.

### 11.3 Item 3: why the source filters executable remaining accounts

The filter itself and its two sites are 9.1. This tick measured what the filter costs and what it
buys, which is as far as the bytes go.

Measured consequences of the drop **[B]**:

* the pair leaves both working vectors. On the filter path the code jumps to the loop head (v1
  `0x61b7`) or into the end-of-shareholders test (v2 `0x6bad`), so the share entry write
  (`0x61cc..0x61d4`) and the `AccountInfo` clone write (`0x6286..0x6291`, twin `0x6c0d..0x6c11`) are
  both skipped for that element. Nothing is raised and nothing is logged, so this is a skip, not a
  rejection.
* the forwarded list can never carry an executable account. The clone writes the three flag bytes
  read from the same element (`0x61ea..0x61f1` into `0x6207..0x620c`), and the block is only reached
  when that element's executable byte is zero, so the byte stored at clone `+0x2a` is always zero.
* the survivors absorb the dropped one once the repair path runs. The repair ladder 9.2 measured
  (`0x6350..0x638b`, twin `0x6dd2..0x6e15`) rewrites every surviving `share_bps` to
  `bps * 0x2710 / total`, clamps at `0x2710`, and gives `0x2710 - total` to the last entry, so the
  dropped pair's basis points are redistributed over the survivors rather than left unallocated. Off
  that path the surviving entries keep their original values, so the installed vector sums to
  `0x2710` minus the dropped share, and the apply helper `0x6479` is where the share total is
  checked: its 6014 `Invalid share total - must equal 10_000 basis points` is one of the five raises
  the pair walk of 9.5 lists (`0x123` in the v1 body, `0x145` in the twin, line immediates 291 and
  325). **[B]** for the two writes, **[R]** for mapping that raise to the name.

What the source leaves behind, measured **[B]**: pump_fees has no error for an executable recipient.
The `FeeError` table resolved through `0x8dca` carries no such name, and the only remaining-account
error in it is 6013 `Not enough remaining accounts` (`0xc4716`). The filter therefore cannot be an
error path in this program.

What fixes the motive, from the sibling program **[R]**: the pump program's own sharing sweep rejects
an executable recipient outright with
`UnableToDistributeCreatorFeesToExecutableRecipient`, on the same `{address, share_bps}` list shape
and with the same per shareholder order (`specs/09-fees-sweep.md`, sweep error order item 3, and
`native_eligible` in item 5). The list pump_fees forwards is the list that program validates, so
dropping the element here keeps the forwarded list acceptable there.

Verdict for 9.6 item 3: the mechanism is **[B]**, the motive is **[partial]** and is written here
once, as a measured consequence plus one named constant from the sibling program. The filter turns a
hard failure the sibling would raise into a silent drop followed by a basis-point renormalisation
over the survivors. Nothing in the deployed bytes of pump_fees names the reason in a string or a
check name, so no further positive reading is available from this binary.

### 11.4 What this supersedes, and what stays open here

Patched in place so the file keeps one reading per instruction: the two 9.4 record rows for
`+0x19..+0x39` and for `+0x20`, `+0x28`, `+0x30`, the 9.1 closing sentence on the filter, and 9.6
items 1 to 3.

Still open in this part of the walk: 7.6 item 3, the 6011 name (`[R]`), and 7.6 item 4, the layout
naming owned by section 3.1. Neither belongs to this lane.

One observation outside this tick's three items, recorded so a later tick does not have to rediscover
it: in 0x6134 the address cursor is seeded from arg4 at `0x615b` and then re-seeded from `r6` at
`0x61b5`, where `r6` is arg2 (`0x6134`) and is also the base the 0x30 stride walk subtracts from
(`0x6182..0x6183`); the v2 twin seeds the same cursor from `r8`, which holds arg4 (`0x6b26`,
`0x6b6a`), while its 0x30 stride base comes from arg2 through `[fp-0x1d8]` (`0x6b24`). Which register
carries which base does not change anything above: both bodies copy the matched element's key into
`fp-0x118` and both stage the vector triple the same way. It is left to a tick that owns the matcher
input walk.

Severity: Informational
Sévérité : Informational
Severity justification: static reconstruction off the deployed bytes only, no execution against any program; the one behavioural property measured (basis-point renormalisation after an executable-account drop) is reachable only through the authorized caller's own remaining-account list, so no fund, admission or production effect is measured.

---

## 12. SUBLANE C follow-up 2 (tick t_9f896a36): the `+0xb8` slot shape and the relay meta order

The two items section 10.4 left open are both closed here on the deployed bytes of
`pump_fees`. No A or B handler is touched, nothing in this section is a PR, and every address
below is an instruction index (byte = insn * 8).

### 12.1 The builder of the `create_donation_fee_pda` accounts struct, measured whole

`try_accounts` `0xcfe6` (1094 insns) writes the accounts struct through one base register,
`r6 = r1` (`0xcfe7`, the out pointer the wrapper passes at `0x14052..0x14053` as `fp-0x370`).
Every write into that base, in epilogue order:

| struct offset | width | source | sites |
|---|---:|---|---|
| `+0x000..+0x080` | 0x80 | `memcpy` from `fp-0x2d0` | `0xd3fc..0xd400` |
| `+0x080` | 8 | `fp-0x820` | `0xd444..0xd445` |
| `+0x088`, `+0x090` | 8 each | `r9`, `r7` | `0xd443`, `0xd442` |
| `+0x098` | 8 | `fp-0x828` | `0xd440..0xd441` |
| `+0x0a0` | 8 | `fp-0x830` | `0xd43e..0xd43f` |
| `+0x0a8`, `+0x0a9`, `+0x0aa` | 1 each | `fp-0x848`, `fp-0x840`, `fp-0x838` | `0xd41a`..`0xd41e` |
| `+0x0b0` | 8 | `fp-0x878` | `0xd43c..0xd43d` |
| `+0x0b8` | 8 | `fp-0x880` | `0xd43a..0xd43b` |
| `+0x0c0..+0x101` | **0x41 = 65** | `memcpy` from `fp-0x248` | `0xd411..0xd416` |
| `+0x101` | 1 | `fp-0x888` | `0xd41f..0xd420` |
| `+0x102` | 4 | `fp-0x250` | `0xd446` |
| `+0x106` | 2 | `fp-0x24c` | `0xd447` |
| `+0x108` | 8 | `fp-0x850` | `0xd438..0xd439` |
| `+0x110` | 8 | `fp-0x818` | `0xd436..0xd437` |
| `+0x118` | 8 | `fp-0x8b0` | `0xd434..0xd435` |
| `+0x120` | 8 | `fp-0x858` | `0xd432..0xd433` |
| `+0x128` | 8 | `fp-0x868` | `0xd430..0xd431` |
| `+0x130` | 8 | `fp-0x860` | `0xd42e..0xd42f` |
| `+0x138..+0x270` | 0x138 | `memcpy` from `fp-0x418` | `0xd401..0xd406` |
| `+0x270` (1), `+0x271` (4), `+0x274` (4) | overlapping | `fp-0x870`, `fp-0x420`, `fp-0x41d` | `0xd421..0xd422`, `0xd407..0xd408`, `0xd409..0xd40a` |
| `+0x278` | 8 | `fp-0x8a0` | `0xd42c..0xd42d` |
| `+0x280` | 8 | `fp-0x8b8` | `0xd42a..0xd42b` |
| `+0x288` | 8 | `fp-0x8a8` | `0xd428..0xd429` |
| `+0x290..+0x358` | 0xc8 | `memcpy` from `fp-0x168` | `0xd40b..0xd410` |
| `+0x358` | 8 | `r8` | `0xd427` |
| `+0x360` | 8 | `fp-0x890` | `0xd425..0xd426` |
| `+0x368` | 8 | `fp-0x898` | `0xd423..0xd424` |

`r6` is written exactly once in this function (`0xcfe7`) and the only other `mov64 r6` inside
`0xcfe6..0xd448` belongs to the next function (`0xd449`), so all the offsets above land in the same
object. The wrapper then copies that object into the `Context` it hands to body `0x500a`:
`memcpy` at `0x14061..0x14065` (destination `fp-0x6c8`, source `fp-0x358`, size `0x358`), so the
body's `r7 = [ctx+0x8] = fp-0x6e0` reads the same offsets the table lists, and the three words at
`ctx+0x00/+0x08/+0x10` are re-filled from `[fp-0x370]`, `[fp-0x368]`, `[fp-0x360]` at
`0x14059..0x1406a` **[B]**.

### 12.2 Item 1 closed: `+0xb8` is the head of a 73-byte inline account image, and `+0xc0` is its tail

The ambiguity of 10.2 is resolved by arithmetic on the widths, not by naming:

* the body reads the 32 bytes at `+0xb8..+0xd8` in place, with `r6 = r7 + 0xb8` (`0x50c8..0x50c9`)
  and four `ldxdw` from `r6+0x18`, `r6+0x10`, `r6+0x8`, `r6+0x0` (`0x50eb..0x50f2`),
* `try_accounts` fills that region with **one 8-byte store at `+0xb8`** (`0xd43b`) **plus a 65-byte
  block copy at `+0xc0`** (`0xd411..0xd416`); `8 + 65 = 73` and `73 = 0x49`, so the region
  `+0xb8..+0x101` is one value whose length is exactly the sum of the two writes,
* the next write starts at `+0x101` (`0xd420`, a single byte), which is where that value ends. So
  `+0xc0` is not a field boundary and the "65-byte record" reading of 10.2 is superseded: it is the
  tail of the 73-byte value minus its first word.

Both sources are the same fetched wrapper. The fetch out slot is `fp-0x578`, so its words sit at
`+0x08 = fp-0x570`, `+0x10 = fp-0x568`, `+0x18 = fp-0x560`:

* `+0xb8` takes `[fp-0x880]`, and the last writer of `fp-0x880` is `0xd0d3`, which copies
  `r3 = [fp-0x570]` loaded at `0xd0c3` (the previous block's `0xd0ac..0xd0ad` is overwritten),
* `+0xc0` takes the 65 bytes staged at `fp-0x248`, filled at `0xd0d4..0xd0d9` from `fp-0x568`
  with `0x41` bytes, then patched at record `+0x04` (2 bytes) and `+0x08` (4 bytes) from
  `fp-0x522`/`fp-0x526` (`0xd0dc`, `0xd0da`),
* so the value at `+0xb8` is `wrapper+0x08` followed by `wrapper+0x10..+0x51`, i.e. **73 bytes of
  the fetched account wrapper**, and the two patches only move the wrapper's own `+0x52`/`+0x56`
  words into the tail.

The wrapper itself is built by `0xdbb` (121 insns) and is `{+0x00: &AccountInfo, +0x08: word,
+0x10: word, +0x18..+0x51: 0x39-byte payload, +0x51: tag byte, +0x52: word, +0x56: half}`: the
payload copy of `0x39` bytes is at `0xe2c`, the tag store at `0xe31`, the two trailing stores at
`0xe2e` and `0xe30`, and `0x51 - 0x08 = 0x49 = 73` matches the slot width measured above **[B]**.

Both candidate readings named in section 10.2 are therefore refuted on the bytes:

| candidate | refutation |
|---|---|
| `config_id: Pubkey` typed account | the body takes `config_id` from the pointer at `+0x358` (`0x51bb`, key deref at `0x51bc..0x51c0`) and `try_accounts` writes `+0x358` from `r8` at `0xd427` |
| `base_mint: Pubkey` typed account | the body takes `base_mint` from the pointer at `+0x58` (`0x51c5..0x51ca`), which lies inside the 128-byte block copied to `+0x000` at `0xd400` |
| pointer-shaped field | a pointer field needs a second dereference; the body does that for `+0x110` (`0x5106..0x5108`), `+0x358` (`0x51bb..0x51bc`), `+0x360` (`0x503e..0x503f`) and `+0x368` (`0x50f3..0x50f4`), but for `+0xb8` it reads the four words straight out of the struct |

The declared shape is therefore `pub <name>: Account<'info, T>` with `&AccountInfo` at `+0xb0` and
`size_of(T) = 73` inline at `+0xb8`; the first 32 bytes of `T` are the value the two `sol_memcmp_`
calls of 10.2 compare, i.e. the curve-side `creator` the ladder of 10.2 places on the left of both
compares (`key(AccountInfo@+0x368)` at `0x5101`, `key(AccountInfo@+0x110)` at `0x5115`). The fetch
that feeds the slot is the one at `0xd0c2` (`call 0x226f`), whose missing-account message is
`bonding_curve` (rodata `0xc4d7c`, length `0xd`, formatted at `0xd0cd` after the tag byte
`[wrapper+0x51]` is tested at `0xd0c5`) **[B for the shape and the fetch, R for the field name]**.

The same shape appears in the crank struct, which is independent confirmation of the pattern: three
inline 32-byte values live at `+0x48..+0x68`, `+0x68..+0x88` and `+0xa8..+0xc8`, staged as four
word stores each at `0x4843..0x485a` **[B]**.

### 12.3 Item 2 closed: the 13 relay metas paired with the accounts-struct field each one clones

`0x8718` reads its 13 keys from the clone array with a 0x30 stride, and the read order is not the
array order: twelve reads at `[r7+0x30]`, `[r7+0x60]`, ... `[r7+0x240]` (`0x8726`, `0x872f`, `0x8738`,
`0x8741`, `0x874a`, `0x8753`, `0x875c`, `0x8765`, `0x876e`, `0x8777`, `0x8780`, `0x8789`) and the
thirteenth at `[r7+0x00]` (`0x8792`), with `r7 = fp-0x3a0` from the call site (`0x4b50..0x4b51`).
Each 34-byte meta takes the 32-byte key plus a literal flag pair, and the flag stores run in strict
meta order: `sth [r2+0x20]` = `0x0100` for metas 0 to 4 (`0x87b8`, `0x87c1`, `0x87ca`, `0x87d3`,
`0x87dc`), `0x0101` for metas 5 and 6 (`0x87e5`, `0x87ee`), `0x0000` for metas 7 to 12 (`0x87f7`,
`0x8800`, `0x8809`, `0x8812`, `0x881b`, `0x8824`) **[B]**.

So meta index `k` (0-based) clones the record at `fp-0x3a0 + 0x30*(k+1)` for `k = 0..11`, and
meta 12 clones the record at `fp-0x3a0`. The records are assembled at `0x4a80..0x4b4d` with the
layout `{+0x00 key, +0x08 lamports Rc, +0x10 data Rc, +0x18 owner, +0x20 rent_epoch, +0x28 is_signer,
+0x29 is_writable, +0x2a executable}` (0x30 stride: `+0x28`/`+0x29`/`+0x2a` bytes at
`0x4acf..0x4acb` for one record and the same shape for the other twelve), and each record's key
pointer is `[struct+OFF]+0x00` with `OFF` loaded at `0x48af..0x4a5d` **[B]**.

| meta | flag word | record | struct field it clones | name |
|---:|---|---|---|---|
| 0 | `0x0100` writable | `fp-0x370` | `+0x2b8` | `debouncer` **[B]** |
| 1 | `0x0100` writable | `fp-0x340` | `+0x2c0` | `debouncer_ata` **[B]** |
| 2 | `0x0100` writable | `fp-0x310` | `+0x2c8` | offset only **[partial]** |
| 3 | `0x0100` writable | `fp-0x2e0` | `+0x298`, then `+0x58` | `quote_mint` **[B]** |
| 4 | `0x0100` writable | `fp-0x2b0` | `+0x2d0` | offset only **[partial]** |
| 5 | `0x0101` signer + writable | `fp-0x280` | `+0x000` | offset only **[partial]** |
| 6 | `0x0101` signer + writable | `fp-0x250` | `+0x270` | offset only **[partial]** |
| 7 | `0x0000` read only | `fp-0x220` | `+0x2b0` | `epoch_tracker` **[B]** |
| 8 | `0x0000` read only | `fp-0x1f0` | `+0x288` | offset only **[partial]** |
| 9 | `0x0000` read only | `fp-0x1c0` | `+0x280` | offset only **[partial]** |
| 10 | `0x0000` read only | `fp-0x190` | `+0x278` | offset only **[partial]** |
| 11 | `0x0000` read only | `fp-0x160` | `+0x2a8` | `mint_whitelist` **[B]** |
| 12 | `0x0000` read only | `fp-0x3a0` | `+0x2a0` | `donation_relay_event_authority` **[B]** |

Note added by the follow-up tick (section 13.1 to 13.4): the record, offset and flag columns above are
correct, and the name cells are shifted by one record. Each ladder store carries the account that the
pointer arithmetic of its branch points at, so the names of metas 0, 1, 7, 11 and 12 move one slot and
the seven cells left open here are measured in 13.4, which supersedes this table row by row.

Name grounding for the five remaining-account names, all from the matcher inside `try_accounts`
`0xc788` (1312 insns). It decrements the remaining count (`stxdw [r8+0x8]` at `0xc8a9`, `0xc8ca`,
`0xc8e3`, `0xc8fd`, `0xc929`, `0xc930`) and advances the cursor by 0x30 each time
(`stxdw [r8+0x0]` at `0xc8ac`, `0xc8cd`, `0xc8e6`, `0xc900`, `0xc92c`, `0xc932`); each branch
formats its expected name:

| branch | count test | name string | slot written | struct field |
|---|---|---|---|---|
| `0xc8ae..0xc8bc` | `remaining - 2` | `donation_relay_event_authority` `0xc4d51`, len `0x1e` | `fp-0x9d8` | `+0x2a0` (`0xccb5`) |
| `0xc8c7..0xc8dc` | `remaining - 3` | `mint_whitelist` `0xc4d43`, len `0xe` | `fp-0x9e0` | `+0x2a8` (`0xccb3`) |
| `0xc8e0..0xc8f6` | `remaining - 4` | `epoch_tracker` `0xc4d20`, len `0xd` | `fp-0xa08` | `+0x2b0` (`0xccb1`) |
| `0xc8fa..0xc919` | `remaining - 5` | `debouncer` `0xc4d36`, len `0xd` | `fp-0xa10` | `+0x2b8` (`0xccaf`) |
| `0xc90b..0xc922` | `remaining - 6` | `debouncer_ata` `0xc4d2d`, len `0xd` | `fp-0xa18` | `+0x2c0` (`0xccad`) |

`quote_mint` is grounded in the body: `0x485b..0x4865` walks `[r8+0x298]`, then `+0x58`, then
`+0x00`, stages the 32 bytes and compares them with `0xc3740` (WSOL) at `0x4868`, and meta 3 is the
only record whose key comes through that `+0x58` hop **[B]**.

One caveat on the offsets themselves, recorded so a later tick does not inherit an over-claim:
twelve of the thirteen record keys resolve cleanly to `[[struct+OFF]+0x00]` with `OFF` taken from the
clone block that fills the record. The record behind meta 6 is the exception: its key source slot is
`fp-0x760`, while the epilogue fills `+0x270` from `fp-0x548` (`0xcc7b..0xcc7c`), a value staged by
the second fetch (`0xc7c4`, after `call 0x21c6` at `0xc7bf`). Both readings agree that meta 6 clones a
fetched account rather than a derived value, and the signer flag says the same thing; which of the two
slot chains is the live one is the first thing to re-measure when the name of meta 6 is taken up.

Follow-up: section 13.3 measures both chains and they agree. `fp-0x548` holds the account pointer of
the field (written by the `0x21c6` fetch at `0xc7c4`, stored into `+0x270` at `0xccc0`) and `fp-0x760`
holds the key that the bundle builder stashes from the same field at `0x49b2`, so meta 6 is `payer`
and the field needs no further measurement.

Cross-check that does not depend on any name: 10.1 measured exactly one signer group of four seeds,
so at most one of the two signer metas can be a PDA. The two signer metas (5 and 6) therefore have to
be the two accounts that can actually sign this CPI, one by transaction signature and one by the
`donation_fee_pda` seed vector measured at `0x48a2..0x48ae`. That is consistent with the flag table
being a hand-written per-index pattern rather than something copied from the source `AccountInfo`
flags, which is also why the flags are literal `sth` immediates **[B]**.

### 12.4 Sublane C status after this tick

| handler | wrapper | body | helpers | open |
|---|---|---|---|---|
| `create_social_fee_pda` | **[B]** | **[B]** 389 insns | every callee carries a deployed address (4.13) | none |
| `create_donation_fee_pda` | **[B]** | **[B]** 1641 insns (4.11.1) | same | none on shape: 12.2 settles `+0xb8` |
| `crank_donation_fee_pda` | **[B]** | **[B]** 1950 insns | same | the declared names of metas 2, 4, 5, 6, 8, 9, 10 (7 of 13, all offsets and flag words already measured) |

What remains is a naming residue only, with a measured method for it: decode the cursor arithmetic of
the `0xc788` matcher (the decrements `-2/-3/-4/-5/-6/-7` and the advances `+0x60/+0x90/+0xc0/+0xf0/
+0x120/+0x150` at `0xc8a7..0xc933`) and pair each of the seven remaining slots with the account the
iterator yields at that position. No comparison, branch, raise site or CPI shape is open.

Follow-up: section 13 walks that matcher with the count symbolic and names all thirteen metas, which
retires the lane.

Tools used this tick, all local and untracked under `scratch/`: `c_fetch.py` (linear trace of `r1..r5`
at every call with rodata string heads, used for `0xcfe6` and `0xc788`), `c_slots.py` (last writer of
each frame slot inside a function), `c_records.py` (record layout and per-field provenance of the 13
clones), `c_metas.py` (assembly band `0x4a80..0x4b4d` against the borrow blocks `0x48af..0x4a5d`),
`c_cond.py` (condensed call / store view) and the disassembly dumps `walk_8718b.txt`,
`fetch_cfe6.txt`, `fetch_c788.txt`, `cfe6_dis.txt`.

Severity: Informational
Sévérité : Informational
Severity justification: static reconstruction off the deployed bytes only, no execution against any program and no behaviour change; the two readings closed here are a struct-field shape and a CPI meta order, so no fund, admission or production effect is measured.

---

## 13. SUBLANE C follow-up 3 (tick t_09c3f45c): the seven open relay metas and the meta 6 slot caveat

Scope: the relay `AccountMeta` list of `crank_donation_fee_pda` and nothing else. Section 12.4 left
seven names open (`+0x2c8`, `+0x2d0`, `+0x000`, `+0x270`, `+0x288`, `+0x280`, `+0x278`) and section
12.3 left one caveat on the slot chain behind meta 6. Both are closed here on the deployed bytes of
`pump_fees`. Every address below is an instruction index (byte = insn * 8), as in sections 7 to 12.

### 13.1 The ten leading fetches of `try_accounts` `0xc788`, with the check each one makes

The account name attached to a failed fetch is a literal formatted by the error builder at `0x2b1`,
and each of the ten leading fetches has its own name block. Reading the check inside each helper as
well as the name, the ten fetches come out in the declared order of IDL accounts 1 to 10 **[B]**:

| # | fetch site | helper | the check inside the helper | error name, VA and length (format site) | lands in |
|---:|---|---|---|---|---|
| 1 | `0xc78c` | inline clone of `[r8+0x00]`, `Rc` increments at `0xc795` and `0xc7a0`, stores at `0xc79b` and `0xc7a6` | none | `event_authority`, `0xc4a24`, `0xf` (`0xc7f1`) | `fp-0x980` key and the flags at `fp-0x9a8`/`-0x9b0`/`-0x9b8`, then `+0x0e0..+0x110` |
| 2 | `0xc7b6` | `0x2432` | key == `0xc4ead` = `pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ` (memcmp at `0x2447`) | `program`, `0xc4a33`, `7` (`0xc7fd`) | `fp-0x9c0`, then `+0x268` (`0xccc2`) |
| 3 | `0xc7bf` | `0x21c6` -> `0x15970` | tag `2` only when `[account+0x28]` (is_signer) is non zero (`0x15972`, `0x15973`) | `payer`, `0xc4bca`, `5` (`0xc806`) | `fp-0x548`, then `+0x270` (`0xccc0`) |
| 4 | `0xc7c8` | `0x235b` | key == 32 zero bytes, the frame block zeroed at `0x236b..0x236e` and compared at `0x2374`, i.e. the System program id | `system_program`, `0xc4a3a`, `0xe` (`0xc80f`) | `fp-0x540`, then `+0x278` (`0xccbe`) |
| 5 | `0xc7d1` | `0x24c4` | key == `0xc3640` = `TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA` (memcmp at `0x24d9`) | `token_program`, `0xc4bcf`, `0xd` (`0xc818`) | `fp-0x538`, then `+0x280` (`0xccbc`) |
| 6 | `0xc7da` | `0x23a0` | key == `0xc3600` = `ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL` (memcmp at `0x23b5`) | `associated_token_program`, `0xc4bdc`, `0x18` (`0xc821`) | `fp-0x530`, then `+0x288` (`0xccba`) |
| 7 | `0xc7e2..0xc7e7` | inline (`count-1`, `cursor+0x30`, record pointer into `r3` at `0xc7e4`) | none | `rent`, `0xc3ea0`, `4` (`0xc899`) | `fp-0x9c8`, then `+0x290` (`0xccb9`) |
| 8 | `0xc834` | `0x22b4` | full `Account<T>` read | `fee_program_global`, `0xc4afc`, `0x12` (`0xc885`) | `fp-0x9f0`/`fp-0xa00`/`fp-0x9f8`, then `+0x110`/`+0x118`/`+0x120` (`0xccc4`, `0xccc6`, `0xccc8`) |
| 9 | `0xc84b` | `0x232b` | full `Account<T>` read with a `0xc8` byte payload (`0xc858`) | `donation_fee_pda`, `0xc4218`, `0x10` (`0xc88e`) | `fp-0x9d0`/`fp-0x9d8`/`fp-0x9e0`, then the `0xe0` byte block at `+0x000` (`0xcc86`) |
| 10 | `0xc862` | `0x4d3` | `InterfaceAccount` read | `quote_mint`, `0xc4c65`, `0xa` (`0xc8a0`) | `fp-0x9d0`, then `+0x298` (`0xccb7`) |

Two of these confirm the name-to-account pairing outside the string table, because the check inside
the helper names the type: `0x2432` accepts only the pump_fees program id, which is the `program`
account of the IDL, and `0x21c6` accepts only an account whose `is_signer` byte is set, which is the
`payer` field declared `signer: true`. `0x235b` compares against 32 zero bytes, which is the pubkey
`11111111111111111111111111111111` the IDL declares for `system_program`. `+0x298` also matches the
hop 12.3 measured in the body: `0x4937..0x4938` reads `[struct+0x298]+0x58` and memcmps the 32 bytes
with `0xc3740` = `So11111111111111111111111111111111111111112` **[B]**.

### 13.2 The remaining-account ladder, walked with the count symbolic

After `quote_mint` the body reads the iterator count once (`0xc867`, `r1 = [r8+0x08]`, `r2 =
[r8+0x00]`) and then runs a count dispatch over seven accounts. Walking that region with the count
`N` and the cursor `C` symbolic (`scratch/c_ladder.py`, driven off `scratch/c_cfg.py` branch targets)
gives one slot per count branch, and each branch that fires on an exhausted iterator formats the name
of the account it could not take:

| `N` | count test | taken on the test | error block and its name literal |
|---:|---|---|---|
| `0` | `0xc868` `jeq r1, 0x0` | `0xc8c0`, the bare iterator failure built at `0xc8c3` and returned at `0xc8c6` | no per-account name |
| `1` | `0xc872` `jne r4, 0x0` with `r4 = N-1` | fall through to `0xc873` | `0xc87a..0xc882`, name at `0xc87f`: `donation_relay_program`, `0xc4d0a`, `0x16` |
| `2` | `0xc8ad` with `r4 = N-2` | fall through to `0xc8ae` | `0xc8b6..0xc8bf`, name at `0xc8bc`: `donation_relay_event_authority`, `0xc4d51`, `0x1e` |
| `3` | `0xc8ce` with `r4 = N-3` | fall through to `0xc8cf` | `0xc8d7..0xc8df`, name at `0xc8dc`: `mint_whitelist`, `0xc4d43`, `0xe` |
| `4` | `0xc8e7` with `r4 = N-4` | fall through to `0xc8e8` | `0xc8f0..0xc8f9`, name at `0xc8f6`: `epoch_tracker`, `0xc4d20`, `0xd` |
| `5` | `0xc901` with `r4 = N-5` | fall through to `0xc902` | `0xc903..0xc925`, name at `0xc922`: `debouncer`, `0xc4d2d`, `0x9` |
| `6` | `0xc92d` `jeq r4, 0x0` with `r4 = N-6` | `0xc90b` | `0xc90b..0xc91c`, name at `0xc919`: `debouncer_ata`, `0xc4d36`, `0xd` |
| `>= 7` | `0xc92d` not taken | `0xc92e` and then `0xc92f..0xc933` | none, the ladder falls through to the account checks at `0xc934` |

The six literals are packed with no padding, each one starting exactly where the previous one ends:
`0xc4d0a + 0x16 = 0xc4d20` (`epoch_tracker`), `+ 0xd = 0xc4d2d` (`debouncer`), `+ 0x9 = 0xc4d36`
(`debouncer_ata`), `+ 0xd = 0xc4d43` (`mint_whitelist`), `+ 0xe = 0xc4d51`
(`donation_relay_event_authority`). That arithmetic plus the declared lengths fixes all six strings
with no ambiguity, and it also settles the pair 12.3 recorded the other way round: `0xc4d2d` is
`debouncer` (9 bytes) and `0xc4d36` is `debouncer_ata` (13 bytes).

So the ladder requires at least seven remaining accounts and names the account that is missing, in
order, for every short count. Account `k` of the group is therefore the account whose name appears on
the `N = k` branch, and the pointer arithmetic of each branch says where it comes from:

| group slot | pointer | store site | frame slot | struct offset | meta | declared name |
|---|---|---|---|---|---|---|
| `G1` | `C` | `0xc86b` | `fp-0x1b0` | `+0x2d0` (through `0xccd7`) | 4 | `donation_fee_pda_ata` |
| `G2` | `C+0x30` | `0xc8c7` | `fp-0x9d8` | `+0x2a0` (`0xccb5`) | 12 | `donation_relay_program` |
| `G3` | `C+0x60` | `0xc8e0` | `fp-0x9e0` | `+0x2a8` (`0xccb3`) | 11 | `donation_relay_event_authority` |
| `G4` | `C+0x90` | `0xc8fa` | `fp-0xa08` | `+0x2b0` (`0xccb1`) | 7 | `mint_whitelist` |
| `G5` | `C+0xc0` | `0xc926` | `fp-0xa10` | `+0x2b8` (`0xccaf`) | 0 | `epoch_tracker` |
| `G6` | `C+0xf0` | `0xc92e` | `fp-0xa18` | `+0x2c0` (`0xccad`) | 1 | `debouncer` |
| `G7` | `C+0x120` | `0xc933` | `fp-0xa20` | `+0x2c8` (`0xccab`) | 2 | `debouncer_ata` |

`G1` carries no name literal because the branch that would report it is the `N = 0` case, which
returns the iterator failure itself. Its identity is fixed twice over: by the declared order of the
seven remaining accounts, which the six literals of the table above walk from `G2` to `G7`, and by the
helper that consumes it. `0xccd7` (called at `0xc976` with the pointer block built at `0xc95e..0xc971`)
takes `fp-0x1b0`, compares the account owner with `0xc36a0` = `11111111111111111111111111111111`
(`0xccdb..0xcce3`), reads it as a token account otherwise, checks the mint against the value reached
through `[[fp-0x160]+0x58]` (`0xccfc..0xcd11`) and formats `donation_fee_pda_ata` (`0xc4cf6`, `0x14`) on
both failure blocks (`0xccef`, `0xcd1d`). Its two result words land at `fp-0xa30` and `fp-0xa28`
(`0xc977`, `0xc979`), which the epilogue stores at `+0x2d0` (`0xcca9`) and `+0x2d8` (`0xcca7`), and
the body reads `[struct+0x2d0]` as an `AccountInfo` (`0x495a..0x495b` dereferences its `+0x8` `Rc`) so
meta 4 is that account **[B]**.

The ordering inside the group also matches the seven declared remaining accounts one for one: IDL
accounts 11 to 17 are `donation_fee_pda_ata`, `donation_relay_program`, `donation_relay_event_authority`,
`mint_whitelist`, `epoch_tracker`, `debouncer`, `debouncer_ata`, and the ladder takes them in that
exact sequence. The IDL also marks none of those seven `optional`, which matches the ladder requiring
all seven before it falls through at `0xc934`.

### 13.3 The meta 6 caveat of 12.3: one account, two slots, no conflict

12.3 recorded that the record behind meta 6 has its key source at `fp-0x760` while the epilogue fills
`+0x270` from `fp-0x548`. The two slots belong to the same account and to two different stages:

* `fp-0x548` holds the pointer. It is written at `0xc7c4` by the `0x21c6` fetch (IDL account 3,
  `payer`), copied to `fp-0x988` at `0xcc7b..0xcc7c`, and stored into `+0x270` at `0xccbf..0xccc0`.
* `fp-0x760` holds the key of that same pointer. The bundle builder reads `[r8+0x270]` at `0x499f`,
  takes `[r1+0x00]` (the account key) at `0x49b1`, stashes it at `0x49b2`, and the bundle fill copies
  it into `fp-0x250` at `0x4ac9`, which is the record the body reads as meta 6
  (`fp-0x3a0 + 0x30*7`).
* the third reader, `0xcb06` (`ldxdw r3, [fp-0x760]`), runs on the `fee_program_global` constraint
  failure path and reads the second word of the named error that `0xcb05` builds with its out slot at
  `fp-0x768`. That write happens after the bundle fill, so the slot is reused as scratch and the two
  uses do not interact.

So there is a single live chain, pointer at `fp-0x548` and key stash at `fp-0x760`, and the field it
fills is `payer` **[B]**.

### 13.4 The thirteen relay metas, complete

Record index `k` of the bundle is the account read at the `k`-th block of `0x483d..0x4a5d`; the body
reads meta `k` from record `k+1` for `k = 0..11` and meta 12 from record 0 (`0x8718`, twelve reads at
`[r7+0x30]..[r7+0x240]` and one at `[r7+0x00]`, `r7 = fp-0x3a0`). With the ten leading fetches of
13.1, the ladder of 13.2 and the helper of 13.3, all thirteen names are measured:

| meta | struct offset | bundle record | flag word at meta `+0x20` | declared name | grounding |
|---:|---|---|---|---|---|
| 0 | `+0x2b8` | `fp-0x370` (index 1) | `0x0100` writable | `epoch_tracker` | ladder `G5` (`0xc926`), name `0xc4d20` at `0xc8f6` |
| 1 | `+0x2c0` | `fp-0x340` (index 2) | `0x0100` writable | `debouncer` | ladder `G6` (`0xc92e`), name `0xc4d2d` at `0xc922` |
| 2 | `+0x2c8` | `fp-0x310` (index 3) | `0x0100` writable | `debouncer_ata` | ladder `G7` (`0xc933`), name `0xc4d36` at `0xc919` |
| 3 | `+0x298` | `fp-0x2e0` (index 4) | `0x0100` writable | `quote_mint` | fetch 10 (`0x4d3` at `0xc862`), name `0xc4c65` at `0xc8a0` |
| 4 | `+0x2d0` | `fp-0x2b0` (index 5) | `0x0100` writable | `donation_fee_pda_ata` | helper `0xccd7`, names at `0xccef` and `0xcd1d` |
| 5 | `+0x000` | `fp-0x280` (index 6) | `0x0101` signer + writable | `donation_fee_pda` | fetch 9 (`0x232b` at `0xc84b`), name `0xc4218` at `0xc88e`, seeds of 10.1 |
| 6 | `+0x270` | `fp-0x250` (index 7) | `0x0101` signer + writable | `payer` | fetch 3 (`0x21c6` at `0xc7bf`), `is_signer` gate at `0x15972`, 13.3 |
| 7 | `+0x2b0` | `fp-0x220` (index 8) | `0x0000` read only | `mint_whitelist` | ladder `G4` (`0xc8fa`), name `0xc4d43` at `0xc8dc` |
| 8 | `+0x288` | `fp-0x1f0` (index 9) | `0x0000` read only | `associated_token_program` | fetch 6 (`0x23a0` at `0xc7da`), key `0xc3600`, name `0xc4bdc` |
| 9 | `+0x280` | `fp-0x1c0` (index 10) | `0x0000` read only | `token_program` | fetch 5 (`0x24c4` at `0xc7d1`), key `0xc3640`, name `0xc4bcf` |
| 10 | `+0x278` | `fp-0x190` (index 11) | `0x0000` read only | `system_program` | fetch 4 (`0x235b` at `0xc7c8`), key `0x00*32`, name `0xc4a3a` |
| 11 | `+0x2a8` | `fp-0x160` (index 12) | `0x0000` read only | `donation_relay_event_authority` | ladder `G3` (`0xc8e0`), name `0xc4d51` at `0xc8bc` |
| 12 | `+0x2a0` | `fp-0x3a0` (index 0) | `0x0000` read only | `donation_relay_program` | ladder `G2` (`0xc8c7`), name `0xc4d0a` at `0xc87f` |

Two checks that do not depend on any string fix the assignment by shape alone. First, the flag words
partition the thirteen into five writable non-signer, two signer and six read-only, and the declared
IDL flags partition the same set of names the same way (the writable, non-signer members of the
thirteen are exactly `epoch_tracker`, `debouncer`, `debouncer_ata`, `quote_mint`,
`donation_fee_pda_ata`; the signer-capable ones are exactly `donation_fee_pda` through its seed vector
and `payer` through a transaction signature; the remaining six carry no writable flag in the IDL).
Second, the record rotation is forced: metas 5 and 6 are the only signer metas, so record 6 and
record 7 must be the two accounts that can sign, and only `+0x000` and `+0x270` satisfy that. A
rotation by any other amount would put a non-signer account on a signer meta.

In source order the relay CPI therefore hands over

```
AccountMeta::new(epoch_tracker,               false)   // meta 0,  +0x2b8
AccountMeta::new(debouncer,                   false)   // meta 1,  +0x2c0
AccountMeta::new(debouncer_ata,               false)   // meta 2,  +0x2c8
AccountMeta::new(quote_mint,                  false)   // meta 3,  +0x298
AccountMeta::new(donation_fee_pda_ata,        false)   // meta 4,  +0x2d0
AccountMeta::new(donation_fee_pda,            true)    // meta 5,  +0x000, PDA signer
AccountMeta::new(payer,                       true)    // meta 6,  +0x270, transaction signer
AccountMeta::new_readonly(mint_whitelist,     false)   // meta 7,  +0x2b0
AccountMeta::new_readonly(associated_token_program, false)  // meta 8,  +0x288
AccountMeta::new_readonly(token_program,      false)   // meta 9,  +0x280
AccountMeta::new_readonly(system_program,     false)   // meta 10, +0x278
AccountMeta::new_readonly(donation_relay_event_authority, false)  // meta 11, +0x2a8
AccountMeta::new_readonly(donation_relay_program, false)          // meta 12, +0x2a0
```

with the two wrapper fields read through their own hops in the body: `[struct+0x298]+0x58` for
`quote_mint` (`0x4937..0x4938`) and the `0xc8` byte image at `+0x000` for `donation_fee_pda`
(`0x497c..0x497d`). The single signer group of four seeds measured at `0x48a2..0x48ae` in 10.1 signs
meta 5, and the flag words are literal `sth` immediates installed at `0x87b8..0x8824`, so the signer
bits come from the hand written list rather than from the source `AccountInfo` flags.

### 13.5 What this supersedes, and sublane C status

Rows corrected from the 12.3 table, all by one slot for the ladder names and by measurement for the
seven that were listed as offset only:

| meta | 12.3 | this section |
|---:|---|---|
| 0 | `debouncer` | `epoch_tracker` |
| 1 | `debouncer_ata` | `debouncer` |
| 2 | offset only | `debouncer_ata` |
| 4 | offset only | `donation_fee_pda_ata` |
| 5 | offset only | `donation_fee_pda` |
| 6 | offset only | `payer` |
| 7 | `epoch_tracker` | `mint_whitelist` |
| 8 | offset only | `associated_token_program` |
| 9 | offset only | `token_program` |
| 10 | offset only | `system_program` |
| 11 | `mint_whitelist` | `donation_relay_event_authority` |
| 12 | `donation_relay_event_authority` | `donation_relay_program` |

The one-slot shift came from pairing each ladder store with the fetch that follows it; the stores pair
with the pointer arithmetic instead, and 13.2 shows the store of `G_k` carrying the address
`C + 0x30*(k-1)` in both the success path and the short-count path.

| handler | wrapper | body | helpers | open |
|---|---|---|---|---|
| `create_social_fee_pda` | **[B]** | **[B]** 389 insns | every callee carries a deployed address (4.13) | none |
| `create_donation_fee_pda` | **[B]** | **[B]** 1641 insns (4.11.1) | same | none |
| `crank_donation_fee_pda` | **[B]** | **[B]** 1950 insns | same | none: 13 of 13 metas named here |

Sublane C is retired. Every handler in the create/crank PDA lane now has a full reconstructed body,
every helper it calls carries a deployed address, and the two struct-shape questions of section 10.4
plus the meta names of 12.4 are closed on the bytes. Sections 12.2, 12.3, 13.1 and 13.2 are the four
readings a re-verification pass can diff against the ELF directly.

Tools used this tick, all local and untracked under `scratch/`: `c_cfg.py` (a range dump with every
branch target resolved and every `lddw` shown with its rodata string head), `c_iter.py` (iterator
mutations and the register carrying the cursor), `c_ladder.py` (symbolic walk of `0xc867..0xc940`
with the remaining count and the cursor symbolic, so each short count lands on its own error block),
`c_keys.py` (32 byte rodata to base58), plus `tools/sbftool.py` and the existing `fees_*.py` helpers.

Severity: Informational
Sévérité : Informational
Severity justification: static reconstruction off the deployed bytes only, with no execution against any program and no behaviour change; the readings closed here are one CPI account list and one struct field name, so no fund, admission or production effect is measured.

---

## 14. SUBLANE B1 follow-up (tick t_18bb22e2): the v1 return type behind the `0xd8` block at `0x426e`

Scope: `claim_social_fee_pda` (v1) only, wrapper `0x13b5d` and body `0x40d1..0x4306`. This closes the
fine chunk item (B1-a), which is 6.9 item 2 read for the v1 body alone. `claim_social_fee_pda_v2` is
not touched here. Bytes read this tick: the pinned body slice
`scratch/slices/B_v1_body_0x40d1-0x4307.txt` (the body is not re-dumped), plus three targeted dumps
for bytes the slice does not carry: `func 0xc685` (the borsh writer the body calls at `0x41f3` and
`0x4208`), `dis 0x17665 30` (the `user_id` clone reached at `0x41bf`) and `dis 0x13b90 78` (the v1
wrapper return path). Tags as in the header **[B] / [R] / [partial]**.

### 14.1 The return slot is a hidden out pointer, so the declared type is a memory object [B]

`0x40d1` is the body's first instruction and it is `mov64 r6, r1`. `r6` is callee saved in sBPF, it is
never reloaded in the whole body, and the body touches it in exactly two ways: as the destination of
the `0xd8` copy (`0x4270` `mov64 r1, r6`, used by the `0x4272` call to `0x184d9`) and as the base of
every return store (`0x40f4`, `0x40f5`, `0x40f8`, `0x42ad`, `0x42ae`, `0x42b1`, `0x42bd`, `0x42be`,
`0x42c1`, `0x42ca`, `0x42cb`, `0x42ce`). `r0` is working register on the way out (`0x4227` holds an
`AccountMeta` pointer) and no path sets it as a return value. The caller side agrees: the wrapper
stages `r1 = fp-0x398` before `0x13bb0 call 0x40d1` and reads the three words back at `0x13bb1`,
`0x13bb2`, `0x13bb3` from `fp-0x388`, `fp-0x390`, `fp-0x398`.

Three consequences, all **[B]**: the body returns by hidden pointer, so the declared return type is not
a scalar; the returned object is `0xd8` bytes, because that is the only size ever copied to `r6`; and
the body has exactly one `exit`, at `0x40f9`, so every path funnels through one epilogue.

### 14.2 Exit census: four `Err` sites, three empty `Ok` sites, one payload `Ok` site [B]

| shape | tag word written to `[r6+0x00]` | other words | sites |
|---|---|---|---|
| `Err(message)` | `0x8000000000000001` (`0x40f6`, also `0x42af`, `0x42bf`, `0x42cc`) | `[r6+0x08]` message pointer, `[r6+0x10]` message length (`0x40f4`, `0x40f5`) | `0x40f4`, reached by `0x40e9 ja +0xa`, by fall through from `0x40f3`, and by `0x4150 ja -0x5d`; plus the three post CPI folds `0x42ad..0x42b2`, `0x42bd..0x42c2`, `0x42ca..0x42ce`, each after a `0x15a5f` conversion |
| `Ok(None)` | `0x8000000000000000` (`0x42a0`) | none: `0x42a2 ja -0x1ab` lands on `0x40f8`, so only the tag store runs | entered from the three log exits `0x4151` (rate limit, len `0x19`), `0x4298` (len `0x1a`), `0x429c` (len `0x3e`), all through the relocated call at `0x429f` |
| `Ok(record)` | no tag store: the copy carries the record's own first word | the whole `0xd8` image | `0x426e` `mov64 r2, r10`, `0x426f` `add64 r2, -0x238`, `0x4270` `mov64 r1, r6`, `0x4271` `mov64 r3, 0xd8`, `0x4272 call 0x184d9`; then teardown `0x4273..0x4296` and `0x4296 jne r2, 0x0, -0x19e` straight to the `0x40f9` exit |

The three shapes share one 24 byte header region and differ only in what that region holds, which is
what makes a single word test sufficient: `Err` puts (message pointer, message length) in header words
1 and 2, `Ok(record)` puts the record's own clone there, and `Ok(None)` leaves words 1 and 2 at
whatever the frame held before, because the region is scratch earlier in the body (`0x4129`
`stxdw [r10 -0x238], r3` and `0x4127` hold the account trio the `0x16520` lamports read consumes at
`0x412c`). Those stale words never reach program output: the wrapper publishes one byte and nothing
else on that arm (`0x13bdd` `stb [r1 +0x0], 0x0` with the length word set to `1` at `0x13bde`).

### 14.3 The `0xd8` block, mapped from the body's own stores [B]

Base `fp-0x238`, the same address the `0x4272` copy takes as its source. Every store below is inside
the body; the field names are the 8.6 borsh names.

| block offset | width | store site | value source |
|---:|---:|---|---|
| `+0x00` | 8 | `0x1767a` | the `user_id` clone length register (14.5) |
| `+0x08` | 8 | `0x17678` | clone pointer, allocation from `0x142d0` |
| `+0x10` | 8 | `0x17679` | clone length |
| `+0x18` | 8 | `0x41e6` | `timestamp`, from `[fp-0x210]` = the `Clock` value of `0x40d9`, kept in `[fp-0x320]` at `0x4119` |
| `+0x20..0x40` | 32 | `0x41ca`, `0x41c8`, `0x41c6`, `0x41c4` | `social_fee_pda`, from `[ctx+0xb0][+0x00..0x18]` |
| `+0x40..0x60` | 32 | `0x41d2`, `0x41d0`, `0x41ce`, `0x41d4` | `recipient`, from `[ctx+0x118][+0x00..0x18]` |
| `+0x60..0x80` | 32 | `0x41de`, `0x41dc`, `0x41da`, `0x41d8` | `social_claim_authority`, from `[ctx+0x278][+0x00..0x18]` |
| `+0x80` | 8 | `0x41ef` | `amount_claimed`, from `[fp-0x328]` |
| `+0x88` | 8 | `0x41ee` | `claimable_before`, the same `[fp-0x328]` |
| `+0x90` | 8 | `0x41ec` | `lifetime_claimed`, `[r7+0x18]` after the `0x41b8` update |
| `+0x98` | 8 | `0x41eb` | `recipient_balance_before`, `[fp-0x330]` from the `0x4178` lamports read |
| `+0xa0` | 8 | `0x41e9` | `recipient_balance_after`, `[fp-0x348]` from the re-read at `0x41b5` and `0x41b6` |
| `+0xa8..0xc8` | 32 | `0x41e3`, `0x41e0`, `0x41e1`, `0x41e2` | `quote_mint`, four immediate zero words on v1 |
| `+0xc8` | 8 | `0x41e7` | `lifetime_stable_claimed`, `[r7+0x28]` |
| `+0xd0` | 1 | `0x41e5` (`stxb`) | `platform`, the byte `[r7+0xaa]` read at `0x41c2` |
| `+0xd1..0xd8` | 7 | none | padding inside the copied range |

So the block is 24 bytes of header plus a `0xc0` payload, and inside the payload the last named field
is the `platform` byte at `+0xb8`, followed by seven padding bytes (`0xd8 - 0xd1 = 7`). The block is
not zeroed as a whole before the copy, and the seven padding bytes are read by no consumer (14.4), so
their content is leftover frame bytes and carries no information.

### 14.4 What the writer needs from the block [B]

`func 0xc685` (257 insns) reads the record through `r7` at exactly ten direct offsets, plus three
32 byte copies staged through `r9`:

| read | offset | bytes emitted |
|---|---|---|
| `0xc68a` | `+0x18` | 8, `timestamp` |
| `0xc699` | `+0x10` | the `u32` length, guarded against `0xffffffff` at `0xc69a` and `0xc69c` |
| `0xc69d` | `+0x08` | the byte source, consumed by `0xc6bd call 0x184d9` with the `0xc699` length |
| `0xc6cb` (`ldxb`) | `+0xd0` | 1, `platform` |
| `0xc6cf`, `0xc6e7`, `0xc6fa` | `+0x20`, `+0x40`, `+0x60` | 32 each, through `r9 = r7 + offset` (`0xc6d0`, `0xc6e8`, `0xc6fb`) |
| staged `+0xa8` | `+0xa8` | 32, `quote_mint` |
| `0xc717` | `+0x80` | 8 |
| `0xc726` | `+0x88` | 8 |
| `0xc735` | `+0x90` | 8 |
| `0xc745` | `+0x98` | 8 |
| `0xc754` | `+0xa0` | 8 |
| `0xc77a` | `+0xc8` | 8 |

`+0x00` is absent from that list, and so are `+0xd1..+0xd7`. That absence is the whole basis of the
return type reading: the writer consumes exactly the thirteen fields of 8.6 and never touches the word
the wrapper tests.

### 14.5 Word `+0x00` on the claim path: where its value comes from [B]

The body fills the header with one call, `0x41bf call 0x17665` (`r1 = fp-0x238`, `r2 = ctx`). The blob
that starts at `0x17665` carries several adjacent snippets, and the one this call enters runs
`0x17665..0x1767b` and exits at `0x1767b`, so the single line role recorded for `0x17665` in 6.6 (a
`RefCell` borrow guard) does not describe this path. The entered code is an exact size clone:

```
17665: mov64 r7, r1            ; destination
17667: ldxdw r8, [r2 +0x8]     ; source pointer
17668: ldxdw r6, [r2 +0x10]    ; source length
17669: jeq r6, 0x0, +0xa       ; empty source skips the allocation
17671: call 0x142d0            ; allocate r6 bytes
17677: call 0x184d9            ; memcpy(r9, r8, r6)
17678: stxdw [r7 +0x8], r9     ; pointer
17679: stxdw [r7 +0x10], r6    ; length
1767a: stxdw [r7 +0x0], r6     ; the same length register
```

Two measured points follow. First, on the claim path word `+0x00` receives `r6`, the same register as
the length word, so it holds a small non negative `user_id` byte count and it equals neither
`0x8000000000000000` nor `0x8000000000000001`; the wrapper compares at `0x13bb4` with `0x13bb7` and at
`0x13bd9` with `0x13bdb` therefore cannot fire on a claim that reaches `0x426e` [B]. Second, the stores
`0x17679` and `0x1767a` write the same register, so this byte image does not by itself separate a
"length" reading of that word from a "capacity" reading; the serialised length is the one at `+0x10`,
because that is the word the writer guards against `0xffffffff` at `0xc699`. The file records the
provenance and stops there.

### 14.6 The wrapper's reading of the slot, re-measured for this body [B]

`0x13bb1` `ldxdw r4, [r10 -0x388]` (word 2), `0x13bb2` `ldxdw r6, [r10 -0x390]` (word 1), `0x13bb3`
`ldxdw r7, [r10 -0x398]` (word 0). `0x13bb4` `lddw r1, -0x7fffffffffffffff` with `0x13bb7`
`jeq r7, r1` sends the `Err` arm to `0x13bf8`. The payload branch copies `0xc0` bytes from `fp-0x380`
(the slot plus `0x18`) into `fp-0x100` (`0x13bb8..0x13bbd`) and puts word 2, word 1, word 0 at
`fp-0x108`, `fp-0x110`, `fp-0x118` (`0x13bbf..0x13bc1`), so the writer's base `fp-0x118` is the same
24 byte header plus `0xc0` payload the body built. `0x13bd9` `lddw r2, -0x8000000000000000` with
`0x13bdb` `jne r7, r2` selects `0x13c16` when the word is not the empty tag; `0x13bdd` writes variant
byte `0` and length `1` for the empty arm (`0x13bdf ja +0x40` to the publish at `0x13c20`), and
`0x13c16` writes variant byte `1`, appends through `0x13c1c call 0xc685` and publishes at `0x13c20`.

### 14.7 Answer to (B1-a), and the one part the bytes do not settle

* The v1 body's declared return is one enum returned through a hidden out pointer, `0xd8` bytes, with
  the three reachable encodings of 14.2 and the field map of 14.3: an `Err` arm carrying a message
  pointer and length, an empty `Ok` arm carrying nothing, and a payload `Ok` arm carrying the `0xc0`
  record whose borsh name table is 8.6 **[B]**.
* Its Rust spelling is `Result<Option<SocialFeePdaClaimed>>` **[R]**, with the type name from the IDL
  artefact and every offset, width and sentinel from the bytes. No type name string is emitted
  anywhere in the program, so the spelling is the only labelled part of this answer.
* **[partial]**, and deliberately so: the mechanism by which the compiler folded the discriminant into
  header word `+0x00` (a niche of the payload's first word versus an ordinary variant tag) is not
  recoverable from this path. That word is written by a shared clone helper with a small value, and the
  only code that tests it is the wrapper, so both readings produce the same bytes. The reconstruction
  asserts the measured behaviour and does not assert the niche mechanism.

### 14.8 Sublane B1 status after this tick

| handler | wrapper | body | helpers | open item |
|---|---|---|---|---|
| `claim_social_fee_pda` | **[B]** `0x13b5d` | **[B]** `0x40d1..0x4306`, every store and every exit mapped, single `exit` at `0x40f9` | every callee carries a deployed address (6.6), with the one role correction of 14.5 | none named for B1: (B1-a) closes here |

Item (B1-a) is the only item the fine chunk queue pinned for this body, and 6.9 item 2 is now closed
for v1 on the body bytes plus the wrapper bytes, not on 8.3's summary alone. `claim_social_fee_pda_v2`
stays with sublane B2 and is untouched by this section. Nothing here is a PR, a push or a reference
program run: the whole tick reads the deployed image.

Severity: Informational
Sévérité : Informational
Severity justification: static reconstruction off the deployed bytes with no execution and no behaviour change; the readings closed here are one return type and one exit census, so no fund, admission or production effect is measured.

## 15 SUBLANE D1

### 15.1 (D1-a) closed: measured call and branch sequence of body `0x341d`

Scope of this section: the two remaining simpler bodies, `set_social_claim_authority`
(`0x12eca`, body `0x341d`) and `admin_cto_sharing_config` (`0x139e4`, body `0x3e64`).
This tick closes (D1-a) only. Body and wrapper indices are instruction indices, byte offset
is 8x, as everywhere else in this file.

**Entry contract, from the wrapper (measured this tick, re-read of `0x12eca`):**

| step | insns | measured |
|---|---|---|
| 1 | `0x12eca`..`0x12ece` | `r6 = r5` (data end), `r9 = r4` (data len), `r8 = r3` (data ptr), `r7 = r2` (program id), `r1` saved at `fp-0x400` |
| 2 | `0x12ed3` | `ldxdw r1, [r6-0xff8]`, `jlt r1, 0x20` gates the instruction data at 32 bytes |
| 3 | `0x12ed4`..`0x12eec` | the single `Pubkey` argument is assembled into `fp-0x20`..`fp-0x1`; the last byte is stored by `0x12eec stxb [r10-0x1], r1` |
| 4 | `0x12eed`..`0x12ef2` | ix-data descriptor `{ptr @fp-0x3b0, len @fp-0x3a8}` plus a `0xff` bump sentinel at `fp-0x3b1` |
| 5 | `0x12ef9` | `try_accounts` `0xa5d2` with out `fp-0x1e0`, program id `r7`, descriptor `fp-0x3b0`; `[fp-0x1e0]` is read back as `r6` at `0x12efb`, `[fp-0x1d8]` as `r8` at `0x12efa`, and the tag byte `[fp-0x26] == 2` gate is `0x12efc`/`0x12efd` (taken -> `0x12f64`) |
| 6 | `0x12f13` | `fp-0x3a0` is parked at `fp-0x1d8`, so the body sees `[ctx+0x8] = fp-0x3a0` |
| 7 | `0x12f1b` | `call 0x341d` with `r1 = fp-0x3c8` (out), `r2 = fp-0x1e0` (ctx), `r3 = fp-0x20` (the `Pubkey` argument) |
| 8 | `0x12f1d` | `ldxdw r6, [fp-0x3c8]`, `jeq r6, 2`, so tag 2 is the success tag of the body result; anything else skips to `0x12f64` |
| 9 | `0x12f26` | `call 0xa0f` with `r1 = fp-0x3d8` (out), `r2 = fp-0x3a0`, `r3 = 0xc4ead` (`crate::ID`), `r4 = r7` (program id) |
| 10 | `0x12f27`..`0x12f30` | writer tag `[fp-0x3d8] != 2`, then `0x2b1` formats the account name `0xc4afc` len `0x12` = `fee_program_global` into the `AnchorError` |

**Body `0x341d`, measured sequence** (382 instructions, `exit` at `0x35a9`):

| step | insns | measured |
|---|---|---|
| 1 | `0x341d`..`0x3420` | `r7 = r3` (argument ptr), `r8 = r2` (ctx), `r9 = r1` (out), `ldxdw r6, [r8+0x8]` = `fp-0x3a0`, the `Account<FeeProgramGlobal>` value |
| 2 | `0x3421`..`0x3428` | four `stxdw [r6+0x128..0x147]` copy the 32 argument bytes from `[r7+0x0..0x18]`, in reverse address order, into the in-memory `Pubkey` field at `r6+0x128` |
| 3 | `0x3429`..`0x342d` | `call 0x1621e` = `Clock::get()` into `fp-0xd0`; `ldxdw r1, [fp-0xd0]`, `jne r1, 0` -> `0x3444` error path |
| 4 | `0x342e`..`0x3440` | heap bookkeeping: `lddw r1, 0x300000000` (allocator cursor), `lddw r1, 0x300007f00`, `lddw r2, 0x300000007`, `jgt r1, r2` -> `0x3452`; the fall-through path allocates through `0x175af` at `0x3443`, then `0x3444`..`0x3451` unwraps and `ja +0x155` returns through `0x35a7` |
| 5 | `0x3452`..`0x3462` | builds the 0x30-byte event image in a heap block: tag `0xefe34ef847f763c` at `+0x0` (`0x3458`/`0x345a`), the `Clock::get()` `unix_timestamp` read from `fp-0xa8` at `+0x8` (`0x3452`/`0x3457`), the 32 argument bytes at `+0x10..+0x2f` (`0x345b`..`0x3462`) |
| 6 | `0x3463`..`0x3469` | `stxdw [fp-0xd0] = ptr`, `stdw [fp-0xc8] = 0x30`, then `call 0x161a7` = the `sol_log_data` thunk with one slice of 0x30 bytes (`r2 = 1`, `r9 = 1`) |
| 7 | `0x346a`..`0x347e` | two `Rc` bumps: `ldxdw r5, [r6+0x168]` then `stxdw [r5+0], r1` at `0x3471`, and `ldxdw r3, [r6+0x170]` then `stxdw [r3+0], r1` at `0x347b`; the borrow-failure branch lands on `0x3473` which is `call -0x1` (the abort stub) |
| 8 | `0x347f`..`0x3492` | second allocator gate, identical shape to step 4; `0x3492 ja -0x52` returns to `0x3441` |
| 9 | `0x3493` | `ldxb r8, [r8+0x20]`: one byte read from `ctx+0x20` (the ctx base is `fp-0x1e0`) |
| 10 | `0x3494`..`0x349c` | the `AccountInfo` record that starts at `r6+0x160` is read: `ldxb [r6+0x18a]`, `ldxb [r6+0x189]`, `ldxb [r6+0x188]` are the executable, is_writable and is_signer bytes of the 0x30-stride layout fixed in 14.6, and `ldxdw [r6+0x180]`, `ldxdw [r6+0x178]` are its rent_epoch and owner words; the record's lamports and data words are the `+0x168` and `+0x170` reads of step 7 |
| 11 | `0x349d`..`0x34ac` | rebuilds the same 0x30-byte event image in a second heap block `r2`: tag at `0x34a4`, timestamp from `fp-0x108` at `0x34a1`, argument bytes at `0x34a5`..`0x34ac` |
| 12 | `0x34ad`..`0x34c0` | allocator gate for 0x38 bytes: `jslt r4, 0x0` -> `0x35aa` and `jlt r3, 0x300000008` -> `0x35aa` |
| 13 | `0x34c1`..`0x3526` | CPI instruction data: `lddw r4, 0x1d9acb512ea545e4` stored at `+0x0` (`0x34c4`), then the 0x30 event bytes copied one `ldxb`/`stxb` pair at a time (`0x34c7`..`0x3526`) to `+0x8`..`+0x37` |
| 14 | `0x3527`..`0x3550` | one `AccountMeta` is sized and allocated (`0x3529`..`0x3537` gate, heap cursor store at `0x353a`), filled at `0x353b`..`0x3544` (four words from `fp-0x110` plus `sth [r1+0x20], 1`), the `Vec` header is `{ptr @fp-0x60, cap @fp-0x58 = 1, len @fp-0x68 = 1}` (`0x3545`..`0x3547`), then `call 0x16eb0` at `0x3550` builds the self-instruction with `r2 = 0xc4ead` (`crate::ID`) and `r4 = 0x38` |
| 15 | `0x3551`..`0x3577` | account list staged, `__event_authority` key `0xc3ec2` at `fp-0x28` (`0x3565`), the step-9 byte stored at `fp-0x1` (`0x3568`), instruction data pointer at `fp-0x1000` (`0x356e`), then `call 0x161ae` = `invoke_signed` at `0x3577` with `r4 = 1` |
| 16 | `0x3578`..`0x357c` | `lddw r1, -0x7fffffffffffffe6` (ok sentinel), `ldxdw r2, [fp-0x80]`, `jeq r2, r1` skips the error branch, `ja +0x12` -> `0x358f` |
| 17 | `0x357d`..`0x3588`, `0x358f`..`0x35a6` | `Rc` decrements on the same two records (`[r6+0x0]`, `[r6+0x8]`, `[r2+0x0]`, `[r2+0x8]`), `call 0x15a5f` at `0x3593` wraps the `ProgramError` when the sentinel test failed |
| 18 | `0x35a7`..`0x35a9` | `stxdw [r9+0x8], r1`, `stxdw [r9+0x0], r2`, `exit`, the two-word result the wrapper reads at `0x12f1c` |

Direct callee set of the body, with the role each one already carries elsewhere in this file:
`0x1621e` = `Clock::get()` (656, 709), `0x175af` = allocator (2 sites, `0x3443` and `0x35ab`),
`0x15a5f` = `AnchorError` wrap of a `ProgramError` for `?` propagation (967), `0x161a7` =
`sol_log_data` thunk (969), `0x16eb0` = self-instruction builder with `program_id = 0xc4ead`
(668, 803), `0x161ae` = `invoke_signed` (803). Re-measured here: the body has no raise tuple,
no `AnchorError` code immediate, and no path-anchored failure string of its own, which is the
statement 4.7 already carries for the body.

The two event serialisations carry the same 8-byte tag `0xefe34ef847f763c`, followed by a
`unix_timestamp` word and the argument `Pubkey`; one is logged with `sol_log_data` at `0x3469`
(0x30 bytes) and one is embedded behind the `emit_cpi!` tag `0x1d9acb512ea545e4` at `0x34c4`
(0x38 bytes) and invoked at `0x3577`. **[B]**

### 15.2 (D1-a continued) the store made through writer `0xa0f`, and the field it writes

`0xa0f` is 124 instructions and is the write-back for the `Account<FeeProgramGlobal>` value.
Measured, in order:

| step | insns | measured |
|---|---|---|
| 1 | `0xa0f`..`0xa14` | `r7 = r2` (the `FeeProgramGlobal` value base `fp-0x3a0`), `r6 = r1` (out), then `sol_memcmp_` `0x184e6` of the 32 bytes at `0xc4ead` (`crate::ID`) against `r4` (the program id), length 0x20; `jne r0, 0` at `0xa18` -> error |
| 2 | `0xa19`..`0xa1c` | `ldxdw r8, [r7+0]` (the account info pointer), then helper `0x15a40`: `ldxdw r1, [r6+0x18]`, `lddw r2, 0xc36a0`, `r3 = 0x20`, `sol_memcmp_`, so the 32 bytes at `[r8+0x18]` are compared against the 32 zero bytes at `0xc36a0`; `jne r0, 0` -> error. The helper's field name stays **[partial]**: the bytes fix the compare, not the source-level test |
| 3 | `0xa1d`..`0xa26` | `0x16589` borrows the account data into `fp-0x20`; the ok sentinel `-0x7fffffffffffffe6` is compared at `0xa24`/`0xa26` |
| 4 | `0xa27`..`0xa2b` | the borrowed slice is re-framed as a write cursor `{ptr @fp-0x20, cap @fp-0x18, len @fp-0x10 = 0}` |
| 5 | `0xa2c`..`0xa6f` | seven `0x15991` appends (the writer fixed at 64: `r1 = &mut {ptr, cap, len}`, `r2 = src`, `r3 = n`), in this serialisation order |

The append sequence *is* the `FeeProgramGlobal` field table, and it fixes both the account data
size and where the claim authority lands:

| # | src | n | account data offset | note |
|---|---|---|---|---|
| 1 | `0xc3d97` | 8 | `0x00` | `a2a5f5311d2537f2`, which is `sha256("account:FeeProgramGlobal")[:8]` **[B]** |
| 2 | `r7+0x150` | 1 | `0x08` | in-memory 1-byte field at `+0x150` |
| 3 | `r7+0x108` | 0x20 | `0x09` | in-memory `Pubkey` at `+0x108` |
| 4 | `r7+0x151` | 1 | `0x29` | in-memory 1-byte field at `+0x151` |
| 5 | `r7+0x128` | 0x20 | `0x2a` | in-memory `Pubkey` at `+0x128`, the slot step 2 of 15.1 overwrites from the instruction argument |
| 6 | `[r7+0x148]` | 8 | `0x4a` | in-memory u64 at `+0x140`, staged to `fp-0x8` at `0xa61`/`0xa62` |
| 7 | `r7+0x8` | 0x100 | `0x52` | in-memory 256-byte block at `+0x8` |

The seven lengths sum to 8 + 1 + 32 + 1 + 32 + 8 + 256 = 338 = `0x152`, so the
`FeeProgramGlobal` account data is `0x152` bytes. **[B]**

The store this handler is named for is therefore: the instruction `Pubkey` argument, copied
into the value at `ctx+0x128` by `0x3421`..`0x3428`, is serialised by `0xa0f` into
`FeeProgramGlobal` account data bytes `0x2a`..`0x49`. It is the second of the two `Pubkey`
fields in the record, the first being `data[0x09..0x29]` from memory `+0x108`, which this
handler never touches. **[B]**

Not measured this tick, listed so the next tick does not re-derive it: the source-level names of
the `+0x150`/`+0x151`/`+0x148` fields and of the 256-byte block at `+0x8`, the role of the
`0x15a40` compare inside `0xa0f`, and the meaning of the byte read from `ctx+0x20` at `0x3493`.

Status: **[partial]**. (D1-a) is closed on the bytes. (D1-b), the reconstructed body, is open.

Severity: Informational
Sévérité : Informational
Severity justification: Reverse-engineering measurement of one handler body and its write-back path; no behavior, fund or consensus effect is measured.

### 15.3 (D1-b) closed: reconstructed body of `set_social_claim_authority`, every line cited

(D1-b) turns the measured sequence of 15.1 and the write-back of 15.2 into the Rust body. Reading the
wrapper `0x12eca` again this tick refined one name, and it moves no offset of 15.1 or 15.2: the base
register `r6` of the body is the **accounts struct**, not the bare `Account<FeeProgramGlobal>` value.

**Naming correction, measured on the wrapper this tick**

| insns | measured |
|---|---|
| `0x12efe`..`0x12f03` | `sol_memcpy_` `0x184d9` with `r1 = fp-0x390`, `r2 = fp-0x1d0` (which is `ctx+0x10`), `r3 = 0x1aa` |
| `0x12efb`, `0x12f0a` | `r6 = [ctx+0x00]` parked at `[fp-0x3a0]` |
| `0x12efa`, `0x12f09` | `r8 = [ctx+0x08]` parked at `[fp-0x398]` |
| `0x12f13` | `[ctx+0x08] = fp-0x3a0` |
| `0x12f14` | `[ctx+0x00] = r7`, the program id |
| `0x12f16`..`0x12f1b` | `r1 = fp-0x3c8` (out), `r2 = fp-0x1e0` (context), `r3 = fp-0x20` (the `Pubkey` argument), `call 0x341d` |

Those stores plus the `0x1aa`-byte copy rebuild, at `fp-0x3a0`, a byte copy of the `try_accounts` out
struct that stands at `fp-0x1e0`, and `ctx+0x08` then points at the copy. So `r6 = [ctx+0x08]` at
`0x3420` is the accounts struct base and the body works inside that copy. **Correction to 15.1 step 1
and 15.2 step 1, naming only:** the base is the accounts struct. Every field offset keeps its value,
the claim authority slot stays at base `+0x128` and the writer `0xa0f` keeps reading base `+0x08`,
`+0x108`, `+0x128`, `+0x148`, `+0x150`, `+0x151`.

That base `+0x00` is the account info reference of the first field, and the deserialised value starts
at `+0x08`: `0xa19` `ldxdw r8, [r7+0x0]`, `0xa1a` runs `0x15a40` on that pointer (which reads its
`+0x18` owner word against the 32 zero bytes at `0xc36a0`, re-read this tick), and `0xa20` `0x16589`
borrows the data of the same pointer.

**The `FeeProgramGlobal` value, in memory and in account data**

The append order of `0xa0f` (15.2) is the borsh order, so every appended field carries a value offset
(base +), an accounts-struct offset (base +) and an account data offset:

| value off | base off | data off | n | field |
|---:|---:|---|---:|---|
| `+0x148` | `+0x150` | `0x08` | 1 | `bump`, name `[R]` from specs-fees §10 ("writes bump (8)") |
| `+0x100` | `+0x108` | `0x09` | 32 | `authority` |
| `+0x149` | `+0x151` | `0x29` | 1 | `disable_flags` |
| `+0x120` | `+0x128` | `0x2a` | 32 | `social_claim_authority` |
| `+0x140` | `+0x148` | `0x4a` | 8 | `claim_rate_limit` |
| `+0x000` | `+0x008` | `0x52` | 256 | 256-byte trailing block, source name `[partial]` |

The three names come from specs-fees §10, its argument list and its write census, mapped onto the
measured offsets; the `social_claim_authority` row agrees with the `writes 42` line of specs-fees §14
(`0x2a`). Positions are `[B]` from 15.2; the trailing 256-byte block is the one field whose source
name the bytes do not carry.

**Reconstructed body**

```rust
// programs/pump-fees/src/instructions/fee_sharing/set_social_claim_authority.rs
pub fn set_social_claim_authority(
    ctx: Context<SetSocialClaimAuthority>,
    social_claim_authority: Pubkey,
) -> Result<()> {
    // [B] 0x3421..0x3428: four word stores of the argument at base+0x128, the
    //      social_claim_authority slot of the first field
    ctx.accounts.fee_program_global.social_claim_authority = social_claim_authority;

    // [B] 0x3429..0x342d: call 0x1621e Clock::get into fp-0xd0, tag read back at
    //      0x342c, error branch 0x3444 with the 0x15a5f wrap and the return at 0x344f
    let now = Clock::get()?.unix_timestamp;               // [B] fp-0xa8 = Clock at +0x28

    let event = SetSocialClaimAuthorityEvent {            // [R] name: docs/discriminators.md:281
        timestamp: now,                                   // [B] image +0x08, 0x3457
        social_claim_authority,                           // [B] image +0x10..+0x2f, 0x345b..0x3462
    };
    emit!(event);                                         // [B] 0x3452..0x3469, sol_log_data 0x161a7
    emit_cpi!(event);                                     // [B] 0x349d..0x3577
    Ok(())                                                // [B] 0x358d, result stored 0x35a7..0x35a9
}
```

Both event images are built with direct stores: tag `0xefe34ef847f763c` at image `+0x00`, the
`unix_timestamp` word at `+0x08` (`0x3458`, `0x345a`, `0x3457`), the argument key at `+0x10..+0x2f`
(`0x345b`..`0x3462`). The constant reads back as the byte string `3c767f84ef34fe0e`, which is the
`SetSocialClaimAuthorityEvent` row of `docs/discriminators.md:281`, with fields `timestamp,
social_claim_authority` per `docs/event_layouts.md:215` `[B: constant + cross-check]`. This body runs
no borsh serialiser, which is why `0xec2c` (the one 4.8 uses) is absent from the 15.1 callee set.

**The `emit_cpi!` chain, measured**

| # | insns | measured |
|---|---|---|
| 1 | `0x349d`..`0x34ac` | the second 0x30-byte image is built in a fresh heap block `r2`: tag at `0x34a4`, timestamp from `fp-0x108` at `0x34a1`, key at `0x34a5`..`0x34ac` |
| 2 | `0x34ad`..`0x34c0` | allocator gate for 0x38 bytes: `jslt r4, 0x0` -> `0x35aa`, `jlt r3, 0x300000008` -> `0x35aa` |
| 3 | `0x34c1`..`0x3526` | CPI data: `0x1d9acb512ea545e4` at `+0x00` (`0x34c4`/`0x34c6`), the 0x30 image copied byte by byte to `+0x08`..`+0x37` |
| 4 | `0x3527`..`0x3537` | one 0x22-byte `AccountMeta` is allocated (heap cursor minus 0x22) |
| 5 | `0x353b`..`0x3543` | the event authority key, read from `[r6+0x160]`, is copied to `meta+0x00..0x1f` |
| 6 | `0x3544` | `sth [r1+0x20], 1`, so `is_signer = 1` and `is_writable = 0` |
| 7 | `0x3545`..`0x3547` | `Vec<AccountMeta>` header `{ptr fp-0x60, cap fp-0x58 = 1, len fp-0x68 = 1}` |
| 8 | `0x3548`..`0x3550` | `call 0x16eb0` with `program_id = 0xc4ead` and data length `0x38` |
| 9 | `0x3551`..`0x355e` | the account info copy: executable, is_writable, is_signer staged at `0x3551`..`0x3556` into `fp-0x3e`, `fp-0x3f`, `fp-0x40`, then rent_epoch `fp-0x48`, owner `fp-0x50`, data Rc `fp-0x58`, lamports Rc `fp-0x60`, key `fp-0x68` |
| 10 | `0x355f`..`0x356e` | seeds slice `{ptr fp-0x38 = &fp-0x28, len fp-0x30 = 2}`: seed 0 `{0xc3ec2, 0x11}` = `__event_authority` at `fp-0x28`/`fp-0x20`, seed 1 `{&fp-1, 1}` at `fp-0x18`/`fp-0x10` with the bump byte stored by `0x3568`; account infos `{ptr fp-0x1000 = &fp-0x38, len fp-0xff8 = 1}` |
| 11 | `0x3570`..`0x3577` | `call 0x161ae` = `invoke_signed`, seeds at `r5`, signer count `r4 = 1` |
| 12 | `0x3578`..`0x3593` | the ok sentinel `0x800000000000001a` compared at `0x357b`, success path drops the four Rc words at `0x357d`..`0x358c` and returns tag 2 at `0x358d`, failure path wraps through `0x15a5f` at `0x3593` |

**Two names this tick settles**

* `0x3493` `ldxb r8, [r8+0x20]` reads one byte from the **context** struct, not from the accounts
  struct: `ctx+0x00` is the program id and `ctx+0x08` the accounts reference (`0x12f14`, `0x12f13`),
  and `ctx+0x20` is the byte the wrapper copies at `0x12f0c` from `fp-0x3b1` after `try_accounts`
  returns. The body keeps it in `r9` (`0x3534`) and writes it as seed 1 at `0x3568`, so it is the
  `__event_authority` bump of the signer seeds, `ctx.bumps.__event_authority` `[B]`. This closes the
  15.1 `[partial]` line about the meaning of the byte read at `ctx+0x20`.
* the account info at base `+0x160` (key `+0x160`, lamports `+0x168`, data `+0x170`, owner `+0x178`,
  rent_epoch `+0x180`, is_signer `+0x188`, is_writable `+0x189`, executable `+0x18a`) is the second
  field of the accounts struct and the body feeds it to the event CPI: it clones it at
  `0x346a`..`0x347e` (`Rc` bumps, abort stub at `0x3473`) and copies it at `0x3551`..`0x355e`. The
  first field, the `Account<FeeProgramGlobal>`, is `0x160` bytes wide, being the 8-byte info
  reference plus the 0x152-byte value, so the event authority slot opens at `+0x160` `[B]`.

**Gates.** The body raises nothing: no raise tuple and no code immediate (15.1). The signer and
`has_one` gates sit in the accounts struct and its `try_accounts` `0xa5d2`, carried `[R]` from
specs-fees §11 and §14. `0xa5d2` opens by calling the two deserialisers `0x21c6` at `0xa5d9` and
`0x22b4` at `0xa5e2`, and the `fee_program_global` name formatter `0xc4afc` is reached later in the
same entry region at `0xa643`, `0xa678`, `0xa6ea`, `0xa754`, `0xa77a` (linear window from `0xa5d2`,
`[B]`).

**Residual `[partial]`, terminal (bytes cannot settle these).** The source name of the 256-byte
trailing block of `FeeProgramGlobal`; the source name of the accounts struct slot that follows the
event authority at base `+0x190`; the source-level test behind the `0x15a40` zero-owner compare inside
`0xa0f` (15.2). None of the three changes a byte offset or an address used above.

Status: (D1-b) is closed on the bytes and the 4.7 body status flips to `[B]`. Next item in the
sublane: (D1-c), the `admin_cto_sharing_config` body `0x3e64` gate order.

Severity: Informational
Sévérité : Informational
Severity justification: Reverse-engineering reconstruction of one handler body and its event CPI path from cited instruction addresses; no behavior, fund or consensus effect is measured.

---

### 15.4 (D1-c) closed: gate order and rewrites of `admin_cto_sharing_config` body `0x3e64`

(D1-c) closes on the bytes: the gate order of the body, its single raise, and the exact list of
`SharingConfig` fields it rewrites before the wrapper hands the in-memory copy to packer `0x989`.

Bytes read this tick: the pinned slice `scratch/slices/D1_admin_cto_body_0x3e64.txt` (553 printed
insns, `0x3e64`..`0x40ad`) with every branch target resolved, the body tail `0x40a0`..`0x40f8`, the
wrapper window `0x139e4`..`0x13a9f`, the head and Vec loop of serialiser `0xbd36`, the three bump
stores inside `try_accounts` `0xba35`, and rodata at `0xc3ff5`, `0xc3ec2`, `0xc3e78`, `0xc387d`,
`0xc4c1c`. No program was run and no account data was built.

**Entry contract** (measured this tick; no offset already fixed in 4.6 or 15.1 moves)

| reg | measured at body entry |
|---|---|
| `r1` | out slot, kept in `r9` from `0x3e66` and parked at `fp-0x220` at `0x3e9c` |
| `r2` | the context object the wrapper builds at `fp-0xe8` |
| `r3` | the `Option<Pubkey>` argument record at `fp-0x1b9`, `0x13a76` |
| `r6` | `[ctx+0x08]` at `0x3e67`, the accounts struct copy the wrapper points at with `0x13a6f` |

The wrapper deserialises the argument itself: the `Option` tag byte lands at record `+0x00` (`0x13a0d`)
and the 32-byte key at `+0x01..0x20` (`0x13a0a`..`0x13a13`, sourced from the post-discriminator slice
`r4 = [fp-0x1000]` read at `0x139ef`). That record shape is the 41-byte frame declared in
`docs/cpi_frames_all4.md:56` (`0:8 disc | 8:1 Option | 32 key`, measured stores `8:1 = 0x0 9:8 17:8
25:8 33:8`), so this tick adds the consumer side of that frame.

**The three words the body reaches through the accounts struct**

| base off | measured chain | what it is |
|---:|---|---|
| `+0x58` | `0x3f0e` `ldxdw r1,[r6+0x58]`, `0x3f0f` `ldxdw r1,[r1+0x00]`, then four word loads `0x3f10`..`0x3f17` into `fp-0x28..fp-0x10`, which become event field `mint` at `S+0x38` (`0x3fbb`..`0x3fb5`) | pointer to the `mint` account info |
| `+0x98` | `0x3e68`, `0x3e9e`, `0x3ec3`, `0x3ef7`, `0x3f18`, `0x3fa8`; the wrapper reads the same word at `0x13a7b` (`fp-0x100` is copy base `fp-0x198` plus `0x98`) and passes it to packer `0x989` at `0x13a81` as the config argument | pointer to the `SharingConfig` value |
| `+0xa0` | `0x3fe4` `ldxdw r1,[r6+0xa0]`, key into `r9` at `0x3fea`, both `Rc` refcounts bumped at `0x3fe6` and `0x3ff0`, flags and words read at `0x3ff9`..`0x4004` | pointer to the account info the event CPI signs and passes |

The word at `+0x98` is the same config base packer `0x989` walks in 3.1, so the memory offsets used
below are the ones 3.1 already fixes: vec cap `+0x00`, vec ptr `+0x08`, vec len `+0x10`, `mint`
`+0x18..0x37`, `admin` `+0x38..0x57`, `status` `+0x58`, `admin_revoked` `+0x59`, `bump` `+0x5a`,
`version` `+0x5b` **[B]**. One further word sits past the 0x5c-byte value at `+0x60`: `0x3f19`
`ldxdw r2,[r1+0x60]`, `0x3f1a` `ldxdw r2,[r2+0x00]`, then four word loads into `fp-0x58..fp-0x40`
that become event field `sharing_config` at `S+0x58` (`0x3fb3`..`0x3fad`). The packer never reads
past `+0x5b`, so that word is not account data: it points at the `SharingConfig` account's own info
record. The pointer chain is **[B]**; the Rust type behind it stays `[partial]` and moves no offset.
The wrapper names the same account on the packer path: `0x13a89` formats `0xc4c1c` with
`r5 = 0xe`, the string `sharing_config`.

**Gate order, in execution order**

| # | insns | gate | outcome |
|---:|---|---|---|
| G0 | `0x3e9a`..`0x3e9d` | `ldxb r1,[r7+0x00]` then `jne r1,0x0` | tag `0` takes the `None` branch at `0x3e9e`, any other value the `Some` branch at `0x3eac` |
| G1 | `0x3eac`..`0x3ec2` | the `Some` key is copied to `fp-0x58..fp-0x40` (`0x3eac`..`0x3eb3`), 32 zero bytes are written at `fp-0x198..fp-0x180` (`0x3eb4`..`0x3eb7`), `sol_memcmp_` `0x184e6` runs at `0x3ebd` with `r3 = 0x20`, and the result is sign-extended at `0x3ec0` and `0x3ec1` | `jeq r0,0x0` at `0x3ec2` sends the equal case to `0x3f2a`, the single raise of this body |
| G2 | `0x3ef9`..`0x3efd` | `Clock::get` `0x1621e` into `fp-0xc0`, tag read back at `0x3efc` | a non-zero tag wraps through `0x15a5f` at `0x3f08` and returns at `0x3f0b` |
| G3 | `0x4092`..`0x4096` | `invoke_signed` `0x161ae`, result compared with the ok sentinel `0x800000000000001a` at `0x4093` | a mismatch wraps through `0x15a5f` at `0x40ac` |

G1 is `InvalidAdmin`, code `6001`, at `admin_cto_sharing_config.rs:86`, and it is the only error
record the body builds:

| insns | measured |
|---|---|
| `0x3f2a`..`0x3f2e` | `0x8932` with the rodata table `0xc3e78` fills the error object at `fp-0x1b0` |
| `0x3f40`, `0x3f41` | `0x8dca` with `0xc3e78` and `fp-0xc0`; the guard sends the Display failure path to `0x178c8` at `0x3f4b` with `0xc387d` and `r2 = 0x37` (`a Display implementation returned an error unexpectedly`) |
| `0x3f58` | `lddw r1,0xc3ff5`, the string `programs/pump-fees/src/instructions/fee_sharing/admin_cto_sharing_config.rs`, stored at `fp-0x190` |
| `0x3f5b` | `stw [fp-0x100],0x1771`, i.e. code `6001` |
| `0x3f5c`, `0x3f5d`, `0x3f5e` | the words `0x2` at `fp-0x148`, `0x56` (86) at `fp-0x180` and `0x4b` (75) at `fp-0x188` complete the location record |
| `0x3f64`, `0x3f77` | `0x15a4e` then `0x15a91` turn the record into the `(tag, payload)` pair, and `0x3f7b` jumps to the exit at `0x40c0` |

So the semantic gate is `Some(new_admin)` with `new_admin` equal to 32 zero bytes. The `None` branch
(`0x3e9e`..`0x3eaa`) never reaches `0x3f2a`. The constraint gates named in specs-fees section 22
(`6007` mint mismatch, `6016` authority mismatch) are not re-run here: they sit in `try_accounts`
`0xba35` **`[R]`**. A scan of the 553 printed insns for the error constructors `0x8d8b`, `0x1601e`,
`0x8dca`, `0x178c8`, `0x15a4e` and `0x15a91` returns the single cluster `0x3f2a`..`0x3f77` listed
above, so this body raises nothing else.

**The fields rewritten, in execution order**

`None` branch, `0x3e9e`..`0x3eaa`:

| insns | config offset | value |
|---|---|---|
| `0x3e9f` | `status` `+0x58` | `0x00` |
| `0x3ea1`, `0x3ea2`, `0x3ea3`, `0x3ea4` | `admin` `+0x50`, `+0x48`, `+0x40`, `+0x38` | four zero words, the default key |
| `0x3ea6` | `admin_revoked` `+0x59` | `0x01` |
| `0x3ea8`, `0x3ea9`, `0x3eaa` | vec len `+0x10`, vec ptr `+0x08`, vec cap `+0x00` | `0`, `0x2`, `0` (`0x2` is the align-2 dangling pointer of an empty `Vec<Shareholder>`) |

`Some` branch, `0x3ec3`..`0x3ef5`:

| insns | config offset | value |
|---|---|---|
| `0x3ec4` | `status` `+0x58` | `0x01` |
| `0x3ec7`, `0x3ec9`, `0x3ecb`, `0x3ecd` | `admin` `+0x50`, `+0x48`, `+0x40`, `+0x38` | the argument key, read from `r9 = r7+1` at `+0x18`, `+0x10`, `+0x08`, `+0x00` |
| `0x3ecf` | `admin_revoked` `+0x59` | `0x00` |
| `0x3ed0`..`0x3ee5` | one element | a 0x22-byte `Shareholder` allocated by `0x175b2` at `0x3ee5` with `r1 = 2` and `r2 = 0x22` |
| `0x3ee9`..`0x3ef0` | element `+0x00..+0x1f` | the argument key |
| `0x3ef1` | element `+0x20` | `0x2710`, i.e. 10000 bps |
| `0x3ef3`, `0x3ef4`, `0x3ef5` | vec ptr `+0x08`, len `+0x10`, cap `+0x00` | the element, `1`, `1` |

Both branches, `0x3ef7`:

| insns | config offset | value |
|---|---|---|
| `0x3ef8` | `version` `+0x5b` | `0x02` |

Nothing else is written: no store targets `bump` `+0x5a` or `mint` `+0x18..0x37`, and the packer
argument is the same base, so mint and bump persist exactly as `try_accounts` deserialised them.
Mapped through the packer ladder of 3.1 (`8 + 1 + 1 + 1 + 32 + 32 + 1 + 4 + 34n`), the five writes
land in account data at:

| field | data offset | `None` value | `Some` value |
|---|---:|---|---|
| `version` | `0x09` | `0x02` | `0x02` |
| `status` | `0x0a` | `0x00` | `0x01` |
| `admin` | `0x2b..0x4a` | 32 zero bytes | the argument key |
| `admin_revoked` | `0x4b` | `0x01` | `0x00` |
| `shareholders` | `0x4c` | 4 bytes, empty | 4 + 34 bytes, one element `{key, 10000}` |

The byte values are **[B]**. Reading `0x01` as `Active` and `0x00` as `Paused` is **[R]** from
specs-fees section 22, which also fixes the `Some` shape (a single 10000-bps shareholder) and the
`None` shape (paused, admin revoked, empty vector) that these writes reproduce one for one.

**The reset event the body then builds**

The event source struct `S` sits at `fp-0x198`, is 0xba bytes wide and ends at `fp-0xde`:

| S offset | field | written at | source |
|---:|---|---|---|
| `+0x00`..`+0x17` | `old_shareholders` vec cap, ptr, len | `0x3fbe`, `0x3fbc`, `0x3fbf` | the pre-write clone `0x3e79`..`0x3e99`, length from `fp-0x218` |
| `+0x18`..`+0x2f` | `new_shareholders` vec cap, ptr, len | `0x3fd5`, `0x3fd3`, `0x3fd4` | the post-write clone `0x3f89`..`0x3fa7` |
| `+0x30` | `timestamp` | `0x3faa`, `0x3fab` | `[fp-0x98]`, the `unix_timestamp` word of the `Clock` fetched at `0x3efb` |
| `+0x38`..`+0x57` | `mint` | `0x3fbb`..`0x3fb5` | key of accounts `+0x58` |
| `+0x58`..`+0x77` | `sharing_config` | `0x3fb3`..`0x3fad` | key of the info record at config `+0x60` |
| `+0x78`..`+0x97` | `old_admin` | `0x3fc7`..`0x3fc1` | the prologue snapshot `fp-0x1d0..fp-0x1b8` |
| `+0x98`..`+0xb7` | `new_admin` | `0x3fcf`..`0x3fc9` | `fp-0xc0..fp-0xa8`, the argument key on `Some` and four zero words on `None` |
| `+0xb8` | `old_version` | `0x3fd2` | the snapshot taken at `0x3e74` |
| `+0xb9` | `new_version` | `0x3fd0` | the value read back at `0x3fa9`, i.e. `0x02` |

Both vectors in this struct are the two heap clones, so the log and CPI payloads carry the old and
the new shareholder list without reading the account copy again. Both serialisations go through
`0xbd36`, whose location record is `admin_cto_sharing_config.rs:53`
(`docs/fees_locations_and_memmove.md:141`) and whose first store at `0xbd4f` is the discriminator
immediate `-0xc29c8871d683335`, i.e. the bytes `cbcc97e27837d6f3` = `ResetFeeSharingConfigEvent`
(`docs/discriminators.md:276`). Its read order matches `docs/event_layouts.md:204` field for field:
`src+0x30` timestamp at `0xbd52`, the four pubkeys at `0xbd54`..`0xbd6b` and `0xbda6`..`0xbdb7`, the
two vectors through `src+0x08`/`+0x10` and `src+0x20`/`+0x28` with the 0x22 element stride reapplied
at `0xbd76`, then `src+0xb8` and `src+0xb9`.

* first call `0x3fda` with destination `fp-0xc0`: the returned `Vec` is `{cap fp-0xc0, ptr fp-0xb8,
  len fp-0xb0}`, and `sol_log_data` `0x161a7` at `0x3fe3` logs it as one slice `{ptr fp-0x58, len
  fp-0x50}`.
* second call `0x4009` with destination `fp-0xd8`: the returned `Vec` is `{cap fp-0xd8, ptr fp-0xd0,
  len fp-0xc8}` and becomes the CPI payload.

**The emit_cpi chain, measured**

| # | insns | measured |
|---:|---|---|
| 1 | `0x400a`..`0x402c` | data length `r5 = [fp-0xc8]`, then `len + 8` bytes allocated with the carry check at `0x400e` and the heap guards at `0x4015` and `0x4029` |
| 2 | `0x402d`..`0x402f` | `0x1d9acb512ea545e4` stored at data `+0x00` |
| 3 | `0x4031`..`0x403e` | the `len` event bytes copied from `[fp-0xd0]` to data `+0x08` |
| 4 | `0x403f`..`0x4053` | one 0x22-byte `AccountMeta` allocated by `0x175b2` at `0x4053` with `r1 = 1`, `r2 = 0x22` |
| 5 | `0x4057`..`0x405f` | the 32-byte key from `r9`, the accounts `+0xa0` key, then `sth [r1+0x20], 1` so `is_signer = 1` and `is_writable = 0` |
| 6 | `0x4060`..`0x4062` | metas `Vec` `{cap fp-0x58 = 1, ptr fp-0x50, len fp-0x48 = 1}` |
| 7 | `0x4063`..`0x406a` | `0x16eb0` builds the instruction from `fp-0xc0` with program id `0xc4ead` |
| 8 | `0x406b`..`0x4078` | one account info image at `fp-0x58`: key `fp-0x58`, lamports `fp-0x50`, data `fp-0x48`, owner `fp-0x40`, rent_epoch `fp-0x38`, `is_signer` `fp-0x30`, `is_writable` `fp-0x2f`, `executable` `fp-0x2e`, the three flag bytes taken from `[r6+0xa0]` `+0x28` at `0x3fff`, `+0x29` at `0x3ffd` and `+0x2a` at `0x3ffb` |
| 9 | `0x4079`..`0x4086` | seeds `{0xc3ec2, 0x11}` = `__event_authority` at `fp-0x28`/`fp-0x20` and `{&fp-0x1, 1}` at `fp-0x18`/`fp-0x10`, count `2` at `fp-0x1a8`, seed pointer parked at `fp-0x1b0` |
| 10 | `0x3ff9`, `0x4082`, `0x4083` | the bump byte read from `[r4+0x22]` with `r4` the context object, then stored at `fp-0x1` as seed 1, i.e. `ctx+0x22` |
| 11 | `0x4087`..`0x4092` | account info array `{ptr fp-0x1000 = &fp-0x1b0, len fp-0xff8 = 1}`, then `invoke_signed` `0x161ae` with `r4 = 1` |
| 12 | `0x4097`..`0x40c2` | the two `Rc` pairs dropped at `0x4097`..`0x40a5` (lamports pair at `fp-0x218`, data pair in `r8`), the error arm wrapping through `0x15a5f` at `0x40ac`, `r2 = 2` at `0x40a6`, and the out slot written at `0x40c0`/`0x40c1` |

`ctx+0x22` is the third of three bump bytes. The wrapper prefills `fp-0x20..fp-0x1e` with
`0xffff`/`0xff` (`0x13a15`, `0x13a14`), hands that buffer to `try_accounts` through `[fp-0xff8]` at
`0x13a1a`, `try_accounts` writes the three real bumps at `0xbb31`, `0xbb9a` and `0xbcd8`, and the
wrapper copies them into `ctx+0x20` as a halfword (`0x13a65`, `0x13a66`) and into `ctx+0x22`
(`0x13a67`, `0x13a68`). The body signs with `ctx+0x22`, so that byte is `ctx.bumps.__event_authority`
**[B]**, the same convention 15.3 fixed for `set_social_claim_authority`.

**What stays open, and the 4.6 status**

`[partial]`, terminal on the bytes: the Rust type that makes `accounts+0x98` a pointer to the config
value and puts the account's own info record at config `+0x60`. The body and packer `0x989` agree on
the value base from the same word, so no offset used above depends on that name.

Status: (D1-c) is closed on the bytes and the 4.6 body status stays `[partial]` for one more item,
(D1-d), the reconstructed body. Everything (D1-c) asks for is now cited: the gate order, the single
`6001` at `admin_cto_sharing_config.rs:86`, and the five `SharingConfig` fields rewritten before the
wrapper hands the same base to packer `0x989`.

Severity: Informational
Sévérité : Informational
Severity justification: Static reverse engineering of one handler body from cited instruction addresses, with no execution and no account data built; the gate order and the rewritten field list carry no measured fund, admission or production effect.

---

### 15.5 (D1-d) closed: reconstructed body of `admin_cto_sharing_config`, every line cited

(D1-d) turns 15.4 into the body. Three things measured this tick that 15.4 did not name: the
pre-write snapshot block of the prologue, the second read of the `Option` tag at the event build
with its two mutually exclusive stagings of the `new_admin` field, and the exit path, which frees
nothing. Bytes read this tick: the pinned slice `scratch/slices/D1_admin_cto_body_0x3e64.txt`
(553 insns, `0x3e64`..`0x40ad`) end to end, and the IDL artefact through `tools/fees_idl_order.py`
(`ix admin_cto_sharing_config`, `ev ResetFeeSharingConfigEvent`) for the names. No program ran and
no account data was built.

**Prologue: three snapshots, all taken before the first write**

| insns | measured |
|---|---|
| `0x3e67` | `r6 = [ctx+0x08]`, the accounts struct copy (entry contract of 15.4) |
| `0x3e68` | `r1 = [r6+0x98]`, the `SharingConfig` value base |
| `0x3e69`..`0x3e70` | word loads of value `+0x50`, `+0x48`, `+0x40`, `+0x38` stored to `fp-0x1b8`, `fp-0x1c0`, `fp-0x1c8`, `fp-0x1d0`: the `old_admin` snapshot |
| `0x3e73` | `r2 = [r1+0x08]`, the old vector pointer, kept in `r2` as the clone source |
| `0x3e74`, `0x3e75` | `ldxb [r1+0x5b]` stored to `fp-0x228`: the `old_version` snapshot |
| `0x3e76`, `0x3e77` | `ldxdw [r1+0x10]` stored to `fp-0x218`: the old vector length |
| `0x3e71` | `r8 = 0x2`, the align-2 dangling pointer an empty vector keeps |
| `0x3e78` | `jeq r1,0x0,+0x1e` skips the copy when the vector is empty and leaves `r8` at that `0x2` |
| `0x3e7c`, `0x3e7d`, `0x3e7f` | `len * 0x22`, then the `0x3c3c3c3c3c3c3c3` overflow guard on the same multiply |
| `0x3e80`..`0x3e96` | the bump-allocator handshake, ending in `stxdw [0x300000000], r8` at `0x3e96` |
| `0x3e98`, `0x3e99` | destination `r8` (`and64 r8,-0x2` at `0x3e90`), then `sol_memcpy_` `0x184d9` with the source still in `r2` and the size in `r3` |

The clone is unconditional and it sits before the branch, so the event carries the shareholder list
as it stood before any write **[B]**. The empty-vector shortcut at `0x3e78` explains why the `None`
arm can store the same `0x2` as the empty vector pointer at `0x3ea9` without a second allocation.

**The match: one tag read, nine reloads of the value base**

`0x3e9a` `ldxb r1,[r7+0x00]` reads the tag and `0x3e9b` parks it at `fp-0x230`; `0x3e9d`
`jne r1,0x0,+0xe` sends tag `0` to `0x3e9e` and every other value to `0x3eac`. The value pointer is
never cached: `0x3e9e`, `0x3ea0`, `0x3ea5`, `0x3ea7`, `0x3ec3`, `0x3ec5`, `0x3ece`, `0x3ef2` and
`0x3ef7` each load `[r6+0x98]` again, so the reconstruction below presents nine separate field
statements and no local `&mut` binding **[B, codegen level]**. The argument key is addressed once,
`r9 = r7` then `add64 r9,0x1` at `0x3ebe`/`0x3ebf`, which puts it at record `+0x01..0x20` as 15.4
fixed from the wrapper side. The five writes and their two value sets are the table of 15.4 and are
not repeated here.

**IDL cross-check for the names used below**

| IDL entry | name | measured role in the body |
|---|---|---|
| account 4 | `mint` | accounts `+0x58`, info key copied to event field `mint` at `0x3f0e`..`0x3f17` |
| account 5, `mut` | `sharing_config` | accounts `+0x98`, the value base of 15.4 and the argument packer `0x989` receives at `0x13a81` |
| account 6 | `event_authority` | accounts `+0xa0`, the meta the event CPI signs at `0x3fe4`..`0x405f` |
| argument | `new_admin: Option<pubkey>` | tag at record `+0x00`, key at `+0x01..0x20`, the 41-byte frame of `docs/cpi_frames_all4.md:56` |

**`new_admin` is decided last, on a second read of the tag**

| arm | insns | measured |
|---|---|---|
| dispatch | `0x3f23`, `0x3f24` | `ldxdw r2,[fp-0x230]` reloads the tag saved at `0x3e9b`, and `jne r2,0x0,+0x57` sends a non-zero tag to `0x3f7c`, leaving the `None` path at `0x3f25` |
| `None` | `0x3f25`..`0x3f28` | four zero words stored at `fp-0xc0`, `fp-0xb8`, `fp-0xb0`, `fp-0xa8`, then `ja +0x5a` at `0x3f29` to `0x3f84` |
| `Some` | `0x3f7c`..`0x3f83` | the argument key words copied from `r7+0x19`, `+0x11`, `+0x9`, `+0x1` to `fp-0xa8`, `fp-0xb0`, `fp-0xb8`, `fp-0xc0`, then falls through to `0x3f84` |

Both arms land in the same four words, and those four words are exactly what `0x3fc8`..`0x3fcf`
copy into event `S+0x98..0xb7`. The four words are also the frame slot the `Clock::get` out image
occupied (`0x3efa` hands `fp-0xc0` as the out pointer, `0x3efc` reads its tag, `0x3f0c` reads the
timestamp), so the field is materialised after the clock lands and not from the argument record
directly. A tag read twice, once for the branch and once for the event field, is what the
reconstruction renders as `new_admin.unwrap_or_default()`, with the spelling **[R]** and the two
reads **[B]**. `Option<Pubkey>` is `Copy`, so the `match` leaves the argument usable at the event
build **[R]**.

**`new_shareholders` is cloned after the version write**

| insns | measured |
|---|---|
| `0x3f84`..`0x3f86` | `r1` still holds `[r6+0x98]` from `0x3f18`; `[r1+0x08]` is the vector pointer and `[r1+0x10]` the length the two writes just produced |
| `0x3f87`..`0x3fa7` | the same allocator and copy sequence as the prologue: `len*0x22` at `0x3f8b`, the `0x3c3c3c3c3c3c3c3` guard, `sol_memcpy_` `0x184d9` at `0x3fa7` into `r9`, length in `r7` |
| `0x3fd3`..`0x3fd5` | the clone becomes `S+0x18` cap (`r7`), `S+0x20` pointer (`r9`), `S+0x28` length (`r7`) |

The old clone goes in at `0x3fbc`, `0x3fbe`, `0x3fbf` as `S+0x08` pointer (`r8`), `S+0x00` cap and
`S+0x10` length (both the `fp-0x218` length), so the two heap lists are the only vectors the log
and the CPI payload carry **[B]**.

**Event assembly, in store order**

| S offset | field | source | insns |
|---:|---|---|---|
| `+0x30` | `timestamp` | `[fp-0x98]`, the `unix_timestamp` word read at `0x3f0c` and parked at `fp-0x240` | `0x3faa`, `0x3fab` |
| `+0x58`..`+0x77` | `sharing_config` | key of the info record at config `+0x60` (`0x3f19`..`0x3f22`) | `0x3fac`..`0x3fb3` |
| `+0x38`..`+0x57` | `mint` | key of accounts `+0x58` (`0x3f0e`..`0x3f17`) | `0x3fb4`..`0x3fbb` |
| `+0x08` | `old_shareholders` pointer | `r8`, the prologue clone | `0x3fbc` |
| `+0x00`, `+0x10` | `old_shareholders` cap, length | `fp-0x218` | `0x3fbe`, `0x3fbf` |
| `+0x78`..`+0x97` | `old_admin` | `fp-0x1d0`..`fp-0x1b8`, the prologue snapshot | `0x3fc0`..`0x3fc7` |
| `+0x98`..`+0xb7` | `new_admin` | `fp-0xc0`..`fp-0xa8`, the arm staged at `0x3f25`..`0x3f28` or `0x3f7c`..`0x3f83` | `0x3fc8`..`0x3fcf` |
| `+0xb9` | `new_version` | `[config+0x5b]` read back at `0x3fa8`, `0x3fa9` | `0x3fd0` |
| `+0xb8` | `old_version` | `fp-0x228`, the prologue snapshot | `0x3fd1`, `0x3fd2` |
| `+0x18`, `+0x20`, `+0x28` | `new_shareholders` cap, pointer, length | the post-write clone | `0x3fd5`, `0x3fd3`, `0x3fd4` |

The in-frame order is not the declaration order. The IDL lists the fields as `timestamp`, `mint`,
`sharing_config`, `old_admin`, `old_shareholders`, `new_admin`, `new_shareholders`, `old_version`,
`new_version`, which is also the order serialiser `0xbd36` reads them in (15.4), while the frame
stores `timestamp`, `sharing_config`, `mint` first and the two vectors after the key fields. So the
reconstruction is checked against the serialiser order and the frame offsets, not against the store
order **[B]**. Both serialisations, the log at `0x3fda` and the CPI payload at `0x4009`, read the
same `S`, and the emit and emit_cpi chains are the twelve measurements of 15.4.

**Reconstructed body**

```rust
// programs/pump-fees/src/instructions/fee_sharing/admin_cto_sharing_config.rs
pub fn admin_cto_sharing_config(
    ctx: Context<AdminCtoSharingConfig>,
    new_admin: Option<Pubkey>,                                  // [R] IDL: new_admin: Option<pubkey>
) -> Result<()> {
    // [B] prologue 0x3e68..0x3e99: the value base is re-read per statement, so no local
    //     &mut binding is presented here; the three snapshots are taken before any write.
    let old_admin = ctx.accounts.sharing_config.admin;           // [B] 0x3e69..0x3e70
    let old_version = ctx.accounts.sharing_config.version;       // [B] 0x3e74, 0x3e75
    let old_shareholders = ctx.accounts.sharing_config.shareholders.clone(); // [B] 0x3e76..0x3e99

    match new_admin {                                            // [B] tag 0x3e9a/0x3e9d
        None => {
            ctx.accounts.sharing_config.status = Paused;         // [B] 0x3e9f = 0x00; [R] name
            ctx.accounts.sharing_config.admin = Pubkey::default();   // [B] 0x3ea1..0x3ea4
            ctx.accounts.sharing_config.admin_revoked = true;    // [B] 0x3ea6 = 0x01
            ctx.accounts.sharing_config.shareholders = Vec::new();   // [B] 0x3ea8..0x3eaa
        }
        Some(key) => {
            require!(key != Pubkey::default());                  // [B] 0x3eac..0x3ec2, code 6001
            ctx.accounts.sharing_config.status = Active;         // [B] 0x3ec4 = 0x01; [R] name
            ctx.accounts.sharing_config.admin = key;             // [B] 0x3ec5..0x3ecd
            ctx.accounts.sharing_config.admin_revoked = false;   // [B] 0x3ecf = 0x00
            ctx.accounts.sharing_config.shareholders = vec![     // [B] 0x3ed0..0x3ef5
                Shareholder { address: key, share_bps: 10_000 },  // [B] 0x3ee9..0x3ef1; [R] field names
            ];
        }
    }

    ctx.accounts.sharing_config.version = 2;                     // [B] 0x3ef7, 0x3ef8

    let clock = Clock::get()?;                                   // [B] 0x3ef9..0x3f0b

    let event = ResetFeeSharingConfigEvent {                     // [R] name: docs/discriminators.md:276
        timestamp: clock.unix_timestamp,                         // [B] 0x3f0c, 0x3f0d, 0x3faa
        mint: ctx.accounts.mint.key(),                           // [B] 0x3f0e..0x3f17, 0x3fb4
        sharing_config: ctx.accounts.sharing_config.key(),       // [B] 0x3f19..0x3f22, 0x3fac
        old_admin,                                               // [B] 0x3fc0..0x3fc7
        old_shareholders,                                        // [B] 0x3fbc..0x3fbf
        new_admin: new_admin.unwrap_or_default(),                // [B] 0x3f23..0x3f29 / 0x3f7c..0x3f83
        new_shareholders: ctx.accounts.sharing_config.shareholders.clone(), // [B] 0x3f84..0x3fa7
        old_version,                                             // [B] 0x3fd1, 0x3fd2
        new_version: ctx.accounts.sharing_config.version,         // [B] 0x3fa8, 0x3fa9, 0x3fd0
    };
    emit!(event);                                                // [B] 0x3fd6..0x3fe3, sol_log_data 0x161a7
    emit_cpi!(event);                                            // [B] 0x3fe4..0x40a5, invoke_signed 0x161ae
    Ok(())                                                       // [B] 0x40a6, 0x40a7, 0x40c0
}
```

The raise is presented as `require!` without a payload and without an error type path: the bytes
carry the code word `0x1771` = 6001, the name `InvalidAdmin` (`docs/error_catalogs.md:274`), the
file `admin_cto_sharing_config.rs` at `0x3f58` and line `0x56` = 86, which is the Location record
the `require!` family builds, and they carry no enum type name **[R for the macro form and the
name, B for the record]**. The same holds for `Paused` and `Active`: the byte values `0x00` and
`0x01` are **[B]** (`docs/account_layouts.md:335`) and the enum names are **[R]**. The one
behavioural detail the exit adds is that nothing is freed: between the `invoke_signed` result check
at `0x4093` and the return at `0x40c0` the body only drops the two `Rc` pairs of the event
authority account info (`0x4097`..`0x40a5`, refcounts at `[r6+0x00]` and `[r8+0x00]`), so the two
vector clones stay on the heap for the rest of the instruction **[B]**.

**Citation check.** `tools/d1d_verify_155.py` reloads the pinned slice plus the `0x40ad`..`0x40c2`
exit tail read fresh from the deployed image, and asserts the mnemonic at each address cited above:
117 of 117 citations match across 576 parsed instructions, and the tail confirms `0x40c0` stores the
payload at `[r9+0x08]`, `0x40c1` the tag at `[r9+0x00]`, with `exit` at `0x40c2`.

**Residual `[partial]`, terminal, and the sublane status**

Three names remain, and the bytes cannot carry any of them:

1. the Rust type of the word at accounts `+0x98`, which points at the config value and puts the
   account's own info record at config `+0x60` (the same line 15.4 left open);
2. the enum type name behind `status` (values `0x00` / `0x01` are measured);
3. the error enum path behind `InvalidAdmin` (code, name and Location are measured).

None of the three moves an offset or an address used above, so both sublane D1 bodies are now
**[B]** and **SUBLANE D1 is retired**: `set_social_claim_authority` in 15.3 and
`admin_cto_sharing_config` here, with no open item left and no further tick required.

Severity: Informational
Sévérité : Informational
Severity justification: Static reconstruction of one handler body from cited instruction addresses, with no execution and no account data built; the reconstructed reset path carries no measured fund, admission or production effect.

---

## 16. SUBLANE D2 (tick t_e475ad46): `create_fee_sharing_config` body `0x56c7`, phase map

Scope: the body of `create_fee_sharing_config` only, `0x56c7` to `0x5cd2`. The wrapper `0x13810`
and its `try_accounts` `0xd95d` are not re-derived here; `set_social_claim_authority`,
`admin_cto_sharing_config` and the retired A/B1/B2/C handlers are not touched. Bytes read this
tick: the pinned slice `scratch/slices/D2_create_sharing_body_0x56c7.txt` (1472 printed
mnemonics, `0x56c7`..`0x5cac`), one targeted `dis 0x5cad 200` for the 38 slots the slice stops
short of, `dis 0x13810 40`, `dis 0x13837 22`, `dis 0x138a8 24` and `dis 0x5b40 10` for the
wrapper edges, `tools/dbg_rodata.py` for the rodata records and `tools/SC_consts.py` for the
discriminators. Tags as in the header **[B] / [R] / [partial]**.

This tick closes item **(D2-a)**, the phase map. Items (D2-b) to (D2-f) stay open.

### 16.1 Extent correction: the body is 1548 slots, not 1510 [B]

The pinned slice prints 1472 mnemonics, but 38 of them are `lddw`, which occupies two slots each,
so the slice covers exactly 1510 slots from `0x56c7` to `0x5cac`. The function does not stop
there. `dis 0x5cad 200` shows 38 further slots, `0x5cad`..`0x5cd2`, and the last of them is
`0x5cd2 ja -0x18d`, target `0x5b46`, the single return block. `0x5cd3` is a different function:
its first instruction is `mov64 r6, r1` and it reads the `SocialFeePda` bytes `+0xa8` / `+0xa9`
(`0x5cd5`, `0x5cd8`), which is the `create_social_fee_pda` body already documented in 4.8.1
**[B]**.

So the body is **1548 slots** `0x56c7`..`0x5cd2`, and the census over that range is: one `exit`
(`0x5b49`), one return block (`0x5b46`), 65 call sites and 26 distinct callees. The single
callee that decodes to its own address, `0x58b4 call -0x1`, is the relocation artifact already
seen in the claim bodies and is not read as a real call **[partial]**.

### 16.2 The `-0x8000000000000000` sentinel is the wrapper's error arm, not a body branch [B]

The sentinel compare does not exist inside `0x56c7`. It sits in the wrapper, three slots before
the body call:

| slot | instruction | measured role |
|---|---|---|
| `0x1382b` | `lddw r1, -0x8000000000000000` | the sentinel constant |
| `0x1382d` | `jeq r6, r1, +0x88` (target `0x138b6`) | taken on the sentinel value |
| `0x138b6`..`0x138b9` | `ldxdw r1, [fp-0xc10]`, `stxdw [r1+0x8], r9`, `stxdw [r1+0x0], r8`, `exit` | the arm the sentinel selects writes the two words read at `0x13828`/`0x13829` into the caller's out pointer and exits: it is the **error** return |
| `0x1382e`..`0x13836` | `mov64 r1, fp-0xbb8`, `mov64 r2, fp-0x5d0`, `mov64 r3, 0x5d0`, `call 0x184d9` | the fall-through arm copies the `0x5d0` byte accounts struct and is the **Ok** arm |
| `0x13847` | `call -0xe181` (target `0x56c7`) | the body is called only from the Ok arm |

Inside the body there is exactly one 64 bit sentinel immediate: `0x5c3e`
`lddw r1, -0x7fffffffffffffe6` (unsigned `0x800000000000001a`), tested at `0x5c41`
`jne r2, r1, +0x13` against the `invoke_signed` result read at `0x5c40`. Every other `Result`
test in the body compares the tag with **2**: `0x5861`, `0x58a9`, `0x59cf`, `0x5b25`, `0x5b73`
and `0x5ca4` are `jne r3, 0x2`, and `0x5cd1` is `jeq r3, 0x2`. The tag the body itself writes on
success is that same 2, set once at `0x56c7 mov64 r3, 0x2` and stored into the out pointer by the
return block at `0x5b47` / `0x5b48` (`stxdw [r1+0x8], r0`, `stxdw [r1+0x0], r3`) **[B]**.

### 16.3 Phase map, in execution order [B]

The emitter did not lay the phases out in address order (16.6), so the table follows the edges,
not the addresses. `ctx` is `r7`, the accounts struct obtained at `0x56c8` from `[r2+0x8]`; it is
the `0x5d0` byte image the wrapper copied at `0x13833`, plus the three header words stored at
`0x13834`..`0x13836`.

| # | slots | measured content | callees | goes to |
|---:|---|---|---|---|
| P1 | `0x56c7`..`0x56d8` | prologue: Ok tag 2 in `r3` (`0x56c7`), `ctx` in `r7` (`0x56c8`), guard on the byte at `ctx+0x5b` (`0x56c9`, `0x56ca`), then a four word census at `ctx+0x188`, `ctx+0x178`, `ctx+0x180`, `ctx+0x170` folded into `[fp-0x6e0]`, which ends at 1 only when all four are zero (`0x56cd`, `0x56cf`, `0x56d1`, `0x56d3`..`0x56d8`) | none | `ctx+0x5b != 0`: return block `0x5b46` with tag 2. Else `0x56d9` |
| P2 | `0x56d9`..`0x5703` | first key gate, two 32 byte comparisons: the 32 bytes behind `[ctx+0x5c8]` (`0x56de`, `0x56df`) staged at `fp-0x470` (`0x56e0`..`0x56e7`), compared against `ctx+0x308` (`0x56e8`/`0x56e9`, call `0x56ed`) and against `ctx+0x150` (`r8` = `ctx+0x150` at `0x56db`/`0x56dc`, call `0x5700`) | `0x184e6` x2 | equal on either arm: P10 at `0x5862`. `[fp-0x6e0]` set: P4 at `0x5726`. both unequal: P3 at `0x5704` |
| P3 | `0x5704`..`0x5725` | first error assembly: `0x8932` formats the record at `0xc3e5c` into `fp-0x60` (its first `u32` is `0x10` = 16 = 6016 NotAuthorized), `0x8dca` resolves the same record at `0x571a` | `0x8932`, `0x8dca` | resolve returns 0: P6 at `0x575e`. Non zero: panic block `0x571c`..`0x5725` (`0x178c8`, `0xc387d` len `0x37`) |
| P4 | `0x5726`..`0x572f` | reached when every optional tail is absent: `ctx+0x5bc == 2` raises `err!` with discriminant `0x13` (`0x572b`/`0x572c`), 19 = 6019 `AMM accounts are required for graduated coins` (2.2) | `0x8d8b` | error: `0x5861` then `0x5b46`. Else P5 at `0x5730` |
| P5 | `0x5730`..`0x5743` | third 32 byte comparison: the key reached through `[ctx+0xc0]->[+0]` staged at `0x5731`..`0x5739`, compared against `ctx+0x4e0` at `0x5740` | `0x184e6` | equal: P7 at `0x5796`. Unequal: P6 at `0x5744` |
| P6 | `0x5744`..`0x5795` | second error assembly: `0x8932` formats the record at `0xc3e88` (`0x5749`, first `u32` `0x08` = 8 = 6008 InvalidPool), `0x8dca` at `0x575b`, then two Location boxes, `0x15a4e` at `0x5776` (code `0x1780`, line `0x133`) and `0x15a4e` at `0x5792` (code `0x1778`, line `0x111`) | `0x8932`, `0x8dca`, `0x15a4e` x2 | both `ja 0x5861` then `0x5b46` |
| P7 | `0x5796`..`0x5821` | PDA derivation. `0x16f53` at `0x57b0` = `try_find_program_address` with seed literal `0xc4301` = `pool-authority` and program `0xc4ecd`, seeds array staged from `ctx+0x4c0` (`0x5796`..`0x579f`); its 32 byte output (`0x57b1`..`0x57b8`) compared at `0x57bd` against `ctx+0x4c0`. Then `0x16f7a` at `0x5817` = `create_program_address` with 6 seeds (`0x5814`), seed `0xc3e0c` = `pool` (`0x5806`) and program `0xc4f3c` = the AMM program id (`0x5815`) | `0x16f53`, `0x184e6`, `0x8932`, `0x8dca`, `0x15a4e` (`0x57f3`, code `0x1778` line `0x118`), `0x16f7a`, `0x8d8b` (`0x581d`, disc 8) | mismatch of the first: box at `0x57f3` then `0x5b46`. Second derivation fails: `err!` at `0x581d`. Ok: P8 at `0x5822` |
| P8 | `0x5822`..`0x5861` | assembles a 32 byte key from the bytes at `fp-0x327`, `fp-0x325`, `fp-0x308` (`0x5822`..`0x5833`), reads the key behind `[ctx+0x4b8]` (`0x5835`, `0x5836`) and compares the two at `0x5844` | `0x184e6`, `0x8932` (`0x584c`, record `0xc3e88`), `0x12f8` (`0x5851`), `0x15a4e` (`0x585e`, code `0x1778` line `0x129`) | equal: P9 at `0x5a8d`. Unequal: box at `0x585e` then `0x5b46` |
| P9 | `0x5a8d`..`0x5abc` | last key gate: the low 32 bits of `[fp-0x700]` decide whether a comparison runs (`0x5a8e`..`0x5a90`); when it runs, the 32 bytes staged at `fp-0x470` (`0x5a91`..`0x5a98`) are compared against `ctx+0x580` (`0x5a99`/`0x5a9a`, call `0x5a9e`) | `0x184e6`, `0x8932` (`0x5aa7`, record `0xc3e5c`), `0x12f8` (`0x5aac`), `0x15a4e` (`0x5ab9`, code `0x1780` line `0x12e`) | equal or skipped: P10 at `0x5862` (`0x5aa1`/`0x5aa2`). Unequal: box at `0x5ab9` then `0x5b46` |
| P10 | `0x5862`..`0x58b5` | the `SharingConfig` initialisation and its one element shareholders vector: bump byte read from `[arg+0x24]` and stored at `ctx+0x5a` (`0x5862`..`0x5864`), `ctx+0x5b = 2` (`0x5865`), `ctx+0x58 = 1` (`0x5866`), 32 byte mint from `[ctx+0xc0]->[+0]` into `ctx+0x18`..`0x38` (`0x5867`..`0x5870`), 32 byte admin from `r8` into `ctx+0x38`..`0x58` (`0x5871`..`0x5878`), `ctx+0x59 = 0` (`0x5879`); then one `Shareholder` allocated through `0x175b2` (`0x588f`) with the key at `r8` and `share_bps = 0x2710` (`0x5893`..`0x589b`), the vector written at `ctx+0x8` / `ctx+0x10` / `ctx+0x0` (`0x589c`..`0x589e`), then the serialiser `0x989` at `0x58a6` | `0x175b2`, `0x989` | tag `!= 2`: `0x5b46` (`0x58a9`). Else P11 at `0x58aa` |
| P11 | `0x58aa`..`0x59cb` | first borrow count clone walk: clusters of the shape `ldxdw rX, [ctx+OFF]`, `ldxdw rY, [rX+0x8]`, `ldxdw rZ, [rY]`, `add64 rZ, 1`, `stxdw [rY], rZ`, with the second counter at `+0x10`. Handles touched in this range: `ctx+0x5d8` (`0x58aa`, `0x5945`), `ctx+0x148` (`0x58bf`), `ctx+0x5c8` (`0x58df`), `ctx+0x5d0` (`0x5900`), `ctx+0x120` (`0x5923`), `ctx+0x118` (`0x5929`), `ctx+0x128` (`0x5937`), `ctx+0x138` (`0x5953`), `ctx+0x130` (`0x5954`) | none (only the `0x58b4` artifact) | falls into P12 at `0x59cc` |
| P12 | `0x59cc`..`0x59cf` | heap object through `0x10de9` (`0x59cc`) which stamps the 8 byte constant `0xe53e4892cbc226ea` at its `+0x00` (`0x10e02`) and fills the payload through `0x116f7` (one element list, `share_bps` `0x100` at `0x11711`); Ok tag 2 tested at `0x59cf` | `0x10de9` | tag `!= 2`: `0x5b46`. Else P13 |
| P13 | `0x59d0`..`0x5a8c` | second clone walk for the remaining handles: `ctx+0xc0` (`0x59e5`), `ctx+0x148` (`0x5a05`), `ctx+0x60` (`0x5a26`), `ctx+0x120` (`0x5a49`), `ctx+0x118` (`0x5a4f`), `ctx+0x128` (`0x5a5d`), `ctx+0x5d8` (`0x5a6b`), `ctx+0x138` (`0x5a79`), `ctx+0x130` (`0x5a7a`); the `0x5a8b`/`0x5a8c` pair loops back to `0x58b4` while the counter says so | none | falls into P14 at `0x5abd` |
| P14 | `0x5abd`..`0x5b25` | builds a second account image at `fp-0x5b8`..`fp-0x478` from the cloned keys and the staged values in 27 stores (`0x5abd`..`0x5b1e`), then `0x10fb9` at `0x5b22` stamps the 8 byte constant `0xe8d62634bf347c57` at its `+0x00` (`0x10fd0`) | `0x10fb9` | tag `!= 2`: `0x5b46` (`0x5b25`). Else P15 |
| P15 | `0x5b26`..`0x5b49` | `r8 = ctx+0x38` (`0x5b26`/`0x5b27`), then `[fp-0x6e0] & 1` decides (`0x5b28`..`0x5b2a`). Flag clear: `Clock::get` at `0x5b2d`, tag tested at `0x5b2f`. Flag set: the `ctx+0x5bc` check at `0x5b3e` | `0x1621e`, `0x15a5f` (`0x5b3a`), `0x8d8b` (`0x5b43`, disc `0x13`) | clock tag 0: P17 at `0x5b7d`. Clock error: `0x15a5f` then `0x5b46`. Flag set and `ctx+0x5bc != 2`: P16 at `0x5b4a`. Flag set and `ctx+0x5bc == 2`: `err!` 6019 at `0x5b43` |
| P16 | `0x5b4a`..`0x5b7c` | second write arm: one element vector from the config's own key at `ctx+0x580`, `ctx+0x588`, `ctx+0x590`, `ctx+0x598` (`0x5b4a`..`0x5b59`) with `share_bps = 0x2710` (`0x5b65`), vector stored at `ctx+0x8` / `0x10` / `0x0` (`0x5b66`..`0x5b68`), serialiser `0x989` at `0x5b70` | `0x19e3`, `0x989`, `0x8d8b` (`0x5b79`, disc `0x13`) | tag `!= 2`: `0x5b46` (`0x5b73`). `ctx+0x5e0 != 0`: P20 at `0x5c6d`. Else `err!` 6019 at `0x5b79` |
| P17 | `0x5b7d`..`0x5c3d` | the event and its self instruction: keys from `ctx+0xc0` (`0x5b7f`), `ctx+0x148` (`0x5b89`), `ctx+0x4b8` (`0x5b96`, only when `ctx+0x5bc != 2` at `0x5b95`), `ctx+0x60` (`0x5ba1`) and the mint at `r8` (`0x5bab`..`0x5bb2`); the shareholders vector serialised by `0x1c93` at `0x5bb8` (`r2 = [ctx+0x8]`, `r3 = [ctx+0x10]`, element stride `0x22` at `0x1c9a`); value block `0x5bb9`..`0x5bd8`; discriminator `0xc3dbf` = `e445a52e51cb9a1d` (`0x5bef`/`0x5bf1`); one `AccountMeta` through `0x19e3` at `0x5c07`; instruction through `0x16eb0` at `0x5c1e` (program `0xc4ead` at `0x5c1a`); the signer seed `__event_authority` (`0xc3ec2` at `0x5c2b`) | `0x1c93`, `0xe41c` x2, `0x161a7`, `0x21dc`, `0x19e3`, `0x16eb0`, `0x184d9` (`0x5c24`), `0x161ae` (`0x5c3d`) | P18 |
| P18 | `0x5c3e`..`0x5c54` | the `invoke_signed` result: sentinel `lddw` `0x5c3e`, test `0x5c41`; on the sentinel value both borrow counters are released (`0x5c44`..`0x5c52`) and `r3 = 2` is restored at `0x5c53` | none | `0x5c54 ja 0x5b46` |
| P19 | `0x5c55`..`0x5c6c` | invoke error: `0x15a5f` at `0x5c59` builds the `0x80` box with origin, then the same counter releases (`0x5c5c`..`0x5c6b`) | `0x15a5f` | `0x5c6c ja 0x5b46` |
| P20 | `0x5c6d`..`0x5c75` | `ctx+0x4b2 != 2` continues, `== 2` raises `err!` with disc `0x13` (`0x5c71`/`0x5c72`) | `0x8d8b` | continue: P21 at `0x5c76`. Else `0x5b46` |
| P21 | `0x5c76`..`0x5cd2` | teardown and last leg: six drops through `0x1ec6` (`0x5c7b`..`0x5c92`), `0x184d9` at `0x5c97` (`0xf0` bytes), a borsh writer record at `fp-0x470`, `0x10de9` at `0x5ca1` with its tag test at `0x5ca4`, more drops, two `0x184d9` (`0x5cbf` `0x30`, `0x5cc4` `0xc0`), then `0x11abc` at `0x5cce` which stamps the 8 byte constant `0x3a10af4a049f08d0` at its `+0x00` (`0x11ad3`) | `0x1ec6` x9, `0x184d9` x3, `0x10de9`, `0x11abc` | tag 2 at `0x5cd1`: jumps back to `0x5b2b`, the `Clock::get` slot of P15, which re-enters P17. Any other tag: `0x5cd2 ja 0x5b46` |

Two edges of the table are worth naming because they are not monotonic: `0x5cd1 jeq r3, 0x2, -0x1a7`
targets `0x5b2b` and not `0x5b26`, so that path skips the `[fp-0x6e0]` test and keeps the `r8`
set at `0x5b27`; and `0x5aa2 ja -0x241` targets `0x5862` from `0x5a8d`, so the last key gate runs
before the initialisation it guards **[B]**.

### 16.4 The five Location raise sites of 2.3, at instruction addresses [B]

All five `create_fee_sharing_config.rs` rows of 2.3 are now located. The box is built by
`0x15a4e` (AnchorError box, `0xa0`), the file pointer is the rodata `0xc4359`
(`programs/pump-fees/src/instructions/fee_sharing/...`, `stdw [fp-0x460], 0x4c` = length 76),
the column is the byte `0x2` in each block, and the code is the `stw` in the same tuple:

| raise site | box call | code | file line | formatted record | gate |
|---|---|---:|---:|---|---|
| `0x5776` | `0x15a4e` | `0x1780` = 6016 NotAuthorized | `0x133` = 307 | `0xc3e5c` (`u32` 16) | both P2 comparisons unequal |
| `0x5792` | `0x15a4e` | `0x1778` = 6008 InvalidPool | `0x111` = 273 | `0xc3e88` (`u32` 8) | P5 comparison unequal |
| `0x57f3` | `0x15a4e` | `0x1778` = 6008 InvalidPool | `0x118` = 280 | `0xc3e88` (`u32` 8) | `try_find_program_address` output differs from `ctx+0x4c0` |
| `0x585e` | `0x15a4e` | `0x1778` = 6008 InvalidPool | `0x129` = 297 | `0xc3e88` (`u32` 8) | P8 comparison unequal |
| `0x5ab9` | `0x15a4e` | `0x1780` = 6016 NotAuthorized | `0x12e` = 302 | `0xc3e5c` (`u32` 16) | P9 comparison unequal |

The code immediate and the displayed discriminant agree in all five rows, which double pins the
mapping: `0x1780` = 6016 is always paired with the record whose first `u32` is 16, and `0x1778`
= 6008 with the record whose first `u32` is 8. `0x8932` reads that `u32` (`0x8935 ldxw r2,
`[r2 +0x0]`) and `0x8dca` reads the same word, so the record at `0xc3e5c` carries
`FeeError::NotAuthorized` and the record at `0xc3e88` carries `FeeError::InvalidPool` **[B for the
words, the codes and the pairing; R for the variant names, which come from 2.2]**. **[B]**

### 16.5 The five `err!` sites (no Location) [B]

| site | discriminant | code | message (2.2) |
|---|---:|---:|---|
| `0x572c` | `0x13` = 19 | 6019 | `AMM accounts are required for graduated coins` |
| `0x581d` | `0x8` = 8 | 6008 | `Invalid Pool` |
| `0x5b43` | `0x13` = 19 | 6019 | same |
| `0x5b79` | `0x13` = 19 | 6019 | same |
| `0x5c72` | `0x13` = 19 | 6019 | same |

Every one is a `0x8d8b` call with `mov64 r2, <disc>` in the two slots before it (`0x572b`,
`0x581c`, `0x5b42`, `0x5b78`, `0x5c71`), so they carry no file and line. Four of the five are
the same `ctx+0x5bc == 2` / `ctx+0x4b2 == 2` condition on three different paths, read as the
same missing AMM accounts case **[B for sites and discriminants; [partial] for that reading]**.

### 16.6 Block layout is not address order [B]

The body's phases are emitted interleaved: the entry gates P1 and P2 sit at the lowest addresses,
the error arms P3 and P6 sit between them and P7, the initialisation P10 and the clone walk P11
sit after P8, and P9 is emitted after P11 while running before P10. The block graph measured from
the jumps is P1 -> P2 -> {P10, P4, P3}, P3 -> P6, P4 -> {P5, return}, P5 -> {P7, P6},
P6 -> return, P7 -> {P8, return}, P8 -> {P9, return}, P9 -> {P10, return}, P10 -> P11 -> P12 ->
P13 -> P14 -> P15 -> {P17, P16, return}, P16 -> {P20, return}, P20 -> P21 -> P15 or return,
P17 -> P18 or P19 -> return. Reader caution for the next tick: an address-ordered walk of this
body attributes the wrong gate to the wrong box.

### 16.7 What stays open on D2

* **(D2-b)** the three 6008 predicates at lines 273 / 280 / 297: the operands are now pinned to
  `[ctx+0x5c8]->[+0]` vs `ctx+0x4e0` (273), the `try_find_program_address` output vs `ctx+0x4c0`
  (280) and the assembled key vs `[ctx+0x4b8]->[+0]` (297), but which struct field each of those
  `ctx` offsets is remains **[B] (closed in P2-a)**.
* **(D2-c)** the two 6016 predicates at lines 302 / 307: same shape, the operands are
  `fp-0x470` (staged from `[ctx+0xc0]->[+0]` at `0x5a91`..`0x5a98`) vs `ctx+0x580` (302) and
  `[ctx+0x5c8]->[+0]` vs `ctx+0x150` (307), field names open.
* **(D2-d)** the field stores are measured in P10 (bump from `arg+0x24`, `version` 2, `status` 1,
  mint at `+0x18`, admin at `+0x38`, `admin_revoked` 0, vector at `+0x8`/`+0x10`/`+0x0`) but the
  mapping onto the 3.1 ladder, and the source of `arg+0x24` (the wrapper writes a cursor word at
  `fp-0x5c5` at `0x1383a`, and `fp-0x5e8 + 0x24 = fp-0x5c4` is that word's fourth byte), is not
  closed.
* **(D2-e)** the event field order: the discriminator `e445a52e51cb9a1d` and the writer chain
  `0x1c93` / `0x21dc` / `0xe41c` are located but the per field order is not read yet.
* **(D2-f)** the reconstructed Rust body.
* Open question carried to the next tick: the three heap object helpers `0x10de9`, `0x10fb9` and
  `0x11abc` stamp 8 byte constants `0xe53e4892cbc226ea`, `0xe8d62634bf347c57` and
  `0x3a10af4a049f08d0` at their `+0x00`. None of the three matches the `account:` / `event:` /
  `instruction:` / `global:` hash of any of the 1461 candidate identifiers collected from the
  repository, and none is in the four program discriminator table (`tools/handler_surface.py`,
  85 entries). Their role is **[partial]**.

Severity: Informational
Sévérité : Informational
Severity justification: Reverse-engineering measurement of one handler body's phase map and raise sites; no behavior, fund or consensus effect is measured.

### 16.8 The three `InvalidPool` gates of 2.3: predicate and field per operand (D2-b closed) [B]

The three 6008 sites are one chain of three key equalities over the `pool` account. Every operand
now resolves to a named field. The field map is measured twice over: once from where the
`try_accounts` epilogue places the `pool` image (16.8.1) and once from the out-layout of the two
PDA syscall wrappers (16.8.3). The two readings agree, which is what closes the item.

Correction to 16.7 first: the operand of the line 273 gate is **not** `[ctx+0x5c8]->[+0]`. The
three gates use two different accounts, `[ctx+0xc0]->[+0]` for 273 and `[ctx+0x5c8]->[+0]` for the
6016 gate at 307.

#### 16.8.1 The `pool` image sits at `ctx+0x4c0`, 0xfc bytes, and `ctx+0x4b8` is its `AccountInfo` [B]

`create_fee_sharing_config` reads the pool through the 121-slot `Account<Pool>` helper `0x541`
(call `0xda9a`, the account name raised on its missing arm is `pool`, rodata `0xc3e0c`, length 4
stored at `0xdaa4`). The five measured steps that place it in the accounts struct:

| step | slots | measured |
|---|---|---|
| read | `0xda96` to `0xda9a` | `0x541` with the out buffer at `fp-0x960`, the account at `fp-0x970`, the iterator in `r3` |
| tag | `0xda9d` to `0xdaa8` | out `+0x104` is the status byte (`0xda9d` reads `fp-0x85c` = `fp-0x960 + 0x104`); the value 3 takes the `pool` box at `0xdaa2`, so 2 is the present arm and 3 the missing one |
| header | `0xdaa9` to `0xdaab` | `ctx+0x5bc` = that status byte, `ctx+0x4b8` = out `+0x00`, `ctx+0x4c0` = out `+0x08` |
| copy | `0xdaac` to `0xdab1` | `memcpy(fp-0x2a0, fp-0x950, 0xf4)` where `fp-0x950` is out `+0x10` |
| store | `0xde57` | `memcpy(ctx+0x4c8, fp-0x2a0, 0xf4)`, so `ctx+0x4c8` to `ctx+0x5bb` |

`0xf4` = 244 bytes landing at `ctx+0x4c8` while the 8 bytes at `ctx+0x4c0` are stored as a
separate scalar word by `0xdaab`: the compiler split the copy of one 252-byte object, so the
object starts at `ctx+0x4c0` and ends at `ctx+0x5bb`, one byte before the status byte at
`ctx+0x5bc`.

The image base is pinned independently by the two numeric fields the body reads out of it. The
deserialiser `0x11951` fills the pump_fees `Pool` type from the borsh stream in declaration order
(`0x119963` reads the `u8` at stream `+0x8`, `0x119969` the `u16` at stream `+0x9`, then the
pubkeys at stream `+0xb`, `+0x2b`, `+0x4b`, ...) and stores the last two scalars at image `+0xf8`
(`0x11aa7 stxh [r6 +0xf8], r2`) and image `+0xfa` (`0x11aa5 stxb [r6 +0xfa], r7`). The body reads
exactly those two as `ldxh [ctx+0x5b8]` (`0x57f8`) and `ldxb [ctx+0x5ba]` (`0x57fc`). So
`ctx+0x4c0 + 0xf8 = ctx+0x5b8`, the image base is `ctx+0x4c0`, and image size 0xfc ends at
`ctx+0x5bb`, one byte before the status byte.

Field map of the image, in image offset order:

| image offset | ctx offset | field | cite |
|---:|---:|---|---|
| `+0x00` | `ctx+0x4c0` | `creator` (first pubkey of the borsh stream, head read at `r5 = stream+0xb`) | `0x11996a` to `0x11997a` stream head, image stores `0x11aa2`, `0x11aa1`, `0x11aa0`, `0x11a9f`, `0x11a9e` |
| `+0x20` | `ctx+0x4e0` | `base_mint` (stream `+0x2b`, head read at `r3 = stream+0x2b`) | `0x119974`/`0x119975` stream head, `0x11998f` tail read, image stores around `0x11ab7` |
| `+0x40` | `ctx+0x500` | `quote_mint` (stream `+0x4b`, head read at `r4 = stream+0x4b`) | `0x11998c`/`0x11998d` stream head, `0x1199a7` tail read |
| `+0xf8` | `ctx+0x5b8` | `index: u16` | `0x11aa7` store, `0x57f8` body read |
| `+0xfa` | `ctx+0x5ba` | `pool_bump: u8` | `0x11aa5` store, `0x57fc` body read |
| `+0xfb` | `ctx+0x5bb` | one trailing bool byte | last image byte, not read by the body |

`ctx+0x4b8` is the `pool` `AccountInfo` pointer: `0x5836` and `0x5b96` both dereference it once to
reach the 32-byte account key. `ctx+0x5e0`, read as a word at `0x5b66` and `0x5c6d`, is outside
the image and belongs to the next slot of the accounts struct.

#### 16.8.2 The three predicates [B]

Each comparison result is sign-extended (`lsh64 0x20`, `rsh64 0x20`) and tested with
`jeq r0, 0x0` which CONTINUES on equal (`0x5743` to `0x5796`, `0x57c0` to `0x57f7`, `0x5847` to
`0x5a8d`). The box is only built on the unequal arm. So each gate is "these two 32-byte keys must
be equal", and a mismatch raises the `InvalidPool` site already located in 16.4.

| line | raise | predicate | operand A | operand B |
|---:|---|---|---|---|
| 273 | `0x5792` | `pool.base_mint == mint.key()` | the 32 bytes behind `[ctx+0xc0]->[0]`, staged at `fp-0x470` by `0x5731` to `0x5739`; `ctx+0xc0` is the `mint` `AccountInfo`, the same key copied into `SharingConfig.mint` at `0x5867` to `0x5870` | `0x573b add64 r7, 0x4e0` then `0x5740` memcmp, so `ctx+0x4e0` = `Pool.base_mint` |
| 280 | `0x57f3` | `pool.creator == find_program_address([b"pool-authority", mint])` under the pump program | the `sol_try_find_program_address` out at `fp-0x470` (`0x57b0`), seeds at `fp-0x90`: `{0xc4301, len 0xe}` and `{fp-0x328, len 0x20}`, count 2 at `0x57ad`, program `0xc4ecd` at `0x57ae` | `0x5797 add64 r2, 0x4c0`, `0x579f mov64 r9, r2`, `0x57bd` memcmp, so `ctx+0x4c0` = `Pool.creator` |
| 297 | `0x585e` | `pool.key() == create_program_address([b"pool", index, creator, base_mint, quote_mint, bump])` under the pump AMM program | `[ctx+0x4b8]->[0]` staged at `fp-0x470` by `0x5835`/`0x5836` and `0x5837` to `0x583e` | the `sol_create_program_address` out at `fp-0x328` (`0x5817`), 6 seeds (count 6 at `0x5814`): `"pool"` `0xc3e0c` len 4 at `0x580f`, the `u16` at `ctx+0x5b8` staged at `fp-0x4` (`0x57f9`, len 2 at `0x580e`), `ctx+0x4c0` (len `0x20` at `0x580d`), `ctx+0x4e0` (len `0x20` at `0x580c`), `ctx+0x500` (len `0x20` at `0x580b`), the `u8` at `ctx+0x5ba` staged at `fp-1` (`0x5809`, len 1 at `0x580a`), program `0xc4f3c` at `0x5815` |

So the three 6008 gates read, in order, the AMM pool's base mint, its creator and its own address,
against the coin mint, the pump pool authority PDA of that mint, and the pool address re-derived
from the five pool seeds. The seed order at 297 is the same order the pump migration path uses to
create the account, which is why `creator` there carries the authority key.

#### 16.8.3 The two syscall wrapper out-layouts, which is what "assembled key" was [B]

`0x16f53` wraps `sol_try_find_program_address` (`0x16f61`) and writes its out as
`{address [u8;32] at +0x00, bump u8 at +0x20}` (`0x16f6f` to `0x16f78`).
`0x16f7a` wraps `sol_create_program_address` (`0x16f8f`) and writes its out as
`{tag u8 at +0x00, address [u8;32] at +0x01..+0x21}` (`0x16f9c` to `0x16fa4` on the Ok arm, tag
stores at `0x16f97` and `0x16f99`).

That closes the reading of 16.3/P8. The "32 byte key assembled from `fp-0x327`, `fp-0x325`,
`fp-0x308`" is not an assembly: the out slot of the derivation is `fp-0x328` (`0x5810`/`0x5811`),
the tag is the byte at `fp-0x328` (tested at `0x5818`, zero = Ok) and the address is the 32 bytes
at `fp-0x327`, copied to `fp-0x90` as one unaligned read of out `+0x01`
(`ldxb 0x5822`, `ldxh 0x5824`, `ldxw 0x5832`, then the word moves `0x5829`, `0x582c`, `0x582f`)
with an aligned shadow copy at `fp-0x40` (`0x5827` to `0x5831`). The memcmp at `0x5844` compares
that address with the pool key.

#### 16.8.4 Program ids and seed literals of the three gates [B]

| rodata | bytes | base58 | role |
|---:|---:|---|---|
| `0xc4ecd` | 32 | `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P` | pump program, the program of the 280 derivation (`0x57ae`) |
| `0xc4f3c` | 32 | `pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA` | pump AMM program, the program of the 297 derivation (`0x5815`) |
| `0xc4f5c` | 32 | `pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA` | owner accepted by the `pool` deserialiser (`0xe47`, memcmp against `[AccountInfo+0x18]`) |
| `0xc4ead` | 32 | `pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ` | this program's own id |
| `0xc4301` | 14 | ascii `pool-authority` | seed 0 of the 280 derivation, length stored at `0x57a8` |
| `0xc3e0c` | 4 | ascii `pool` | seed 0 of the 297 derivation, length stored at `0x580f` |

`tools/fees_b58.py` produced the four base58 rows from the rodata VAs. The same six values appear
as a 32-byte zero constant at `0xc36a0` (`11111111111111111111111111111111`) which `0xe3f`
compares first, the default-key arm of the same deserialiser.

[R] corroboration from the reconstruction tree, not from this binary: the pump migration path
declares the same two vectors, `seeds=[b"pool", &0u16.to_le_bytes(), pool_authority, mint,
wsol_mint]` with `seeds::program=pump_amm` for `pool`, and `seeds=[b"pool-authority", mint]` for
`pool_authority`. That is the seed list measured at 297 plus the authority derivation measured at
280, and it explains the `creator` operand: a graduated pool is created with the authority PDA as
its creator, so the coin's real creator sits in `Pool.coin_creator`.

**(D2-b) closed [B].** Still open on this body: the two 6016 gates of lines 302 and 307 (D2-c),
the store map of the `SharingConfig` initialisation onto the 3.1 ladder and the source of the
`arg+0x24` bump (D2-d), the event field order (D2-e) and the reconstructed body (D2-f).

Severity: Informational
Sévérité : Informational
Severity justification: Reverse-engineering measurement of three key-equality gates inside one handler body; no behavior, fund or consensus effect is measured.

### 16.9 The two 6016 `NotAuthorized` gates of 2.3: both read the `payer` key (D2-c closed) [B]

Scope of this tick: only the two 6016 rows of 2.3, lines 302 and 307, inside the body
`0x56c7..0x5cd2`. The three 6008 gates of 16.8 are not reopened, and nothing outside the body is
touched except the two `try_accounts` frame stores that place the operands. Bytes read this tick:
the pinned slice `scratch/slices/D2_create_sharing_body_0x56c7.txt`, `tools/fees_body.py 0xd95d`
(1321 insns, the accounts struct builder), `0x541` (43 insns), `0x2432` (68), `0x21c6` (22),
`0x22fd` (23), `0x226f` (23), `0x50` (23), `0x111f` (119), `0xdbb` (121) and the `Pool`
deserialiser `0x11951`.

#### 16.9.1 Correction to 16.3/P9: the left operand is one key, staged once at `0x56df` [B]

`0x56de ldxdw r1, [ctx+0x5c8]` then `0x56df ldxdw r6, [r1+0x00]`. `r6` is the pointer to the
32-byte key of the account record stored at `ctx+0x5c8`. It is staged for the 307 gate at
`0x56e0..0x56e7` (`fp-0x470` receives the key words in reverse: `+0x18` at `0x56e0`, `+0x10` at
`0x56e2`, `+0x08` at `0x56e4`, `+0x00` at `0x56e6`) and it is re-staged, unchanged, for the 302
gate at `0x5a91..0x5a98` (same reverse order into the same `fp-0x470`).

No instruction on that path rewrites `r6`: the whole range `0x5704..0x5796` contains no write to
`r6`, and the only `r6` writes in `0x5822..0x5a8d` sit inside the clone walks P11 (`0x58c6` to
`0x58cd`, `0x5908` to `0x590c`) and P13 (`0x59e1` onward, `0x5a4f`, `0x5a5d`, `0x5a73` to
`0x5a83`), which the P8 edge never traverses: `0x5847 jeq r0, 0x0, +0x245` targets `0x5a8d`
directly.

Withdraw the 16.3/P9 wording "the staging register `r6` ... comes out of the borrow-count clone
walk (`0x5a83 ldxdw r6, [r0+0x0]`)". `0x5a82`/`0x5a83` are inside the P13 loop body whose exit
edge `0x5a8b jne r8, 0x1, +0x31` goes to `0x5abd` (P14) and whose back edge `0x5a8c ja -0x1d9`
returns to `0x58b4`. Neither edge reaches `0x5a8d`, so the 302 staging register is the P2 one and
the two 6016 gates read the same 32 bytes.

#### 16.9.2 The account is `payer`, pinned twice [B]

`try_accounts 0xd95d` consumes the accounts one per helper and stores each record pointer into a
frame slot first. Step 2 is the call at `0xd994` (helper `0x21c6`, 22 insns: the cursor read
`ldxdw r3, [r2+0x8]` at `0x21c6`, the cursor bump at `0x21d3`, then the plain `AccountInfo` copy
`0x15970`), its result lands in `fp-0x968` at `0xd999`, and the tail store block moves that exact
slot to `ctx+0x5c8`:

| site | instruction | measured |
|---|---|---|
| `0xd994` to `0xd999` | `call 0x21c6`, then `stxdw [fp-0x968], r3` | step 2 result slot |
| `0xde3a` | `ldxdw r7, [fp-0x968]` | the tail block picks the slot up |
| `0xde85` | `stxdw [r6+0x5c8], r7` | and stores it at `ctx+0x5c8` |
| `0xd9c9` to `0xd9d1` | fail arm of step 2: `lddw r4, 0xc4bca`, `mov64 r5, 0x5` | the account name string is `payer` (rodata `0xc4bca` starts `payertoken_program...`), so step 2 is the `payer` field |
| `0x58df` | `ldxdw r2, [ctx+0x5c8]` then `ldxdw r3, [r2+0x8]` | the same offset is cloned like every other `AccountInfo` handle |

The interface record corroborates the name: `payer` is the only signer of this instruction, and a
`NotAuthorized` decision over an account key has to be taken on the signer. Both 6016 gates
therefore read `payer.key()`.

#### 16.9.3 Gate 307: `payer` against the `global` account and against `bonding_curve` [B]

The 32 bytes at `ctx+0x308` are inside the `global` image, and the 32 bytes at `ctx+0x150` are the
first key of the `bonding_curve` image:

* `global`: the step 3 deserialiser `0x111f` stages the image at its own `out+0x18`
  (`0x118b add64 r1, 0x18`, `0x118f mov64 r3, 0x2cb`, copy at `0x1190`), `try_accounts` moves
  `out+0x18` forward as `0x2d3` bytes (`0xd9e9` to `0xd9ee` into `fp-0x678`) and the tail store
  block copies those `0x2d3` bytes to `ctx+0x1b0` (`0xde62` to `0xde67`). So the image runs
  `ctx+0x1b0..0x47a` and `ctx+0x308` is image byte `0x158`.
* `bonding_curve`: step 6 at `0xda30` (helper `0x226f`, 23 insns, then the 121-insn decoder
  `0xdbb`; fail arm at `0xda38` names `bonding_curve`, rodata `0xc4d7c`, length `0xd`). Its out
  layout is the same shape as the `pool` one measured in 16.8.1:

| out | cite | lands at | measured |
|---|---|---|---|
| `+0x00` | `0xda57 stxdw [fp-0xca8], r2`, then `0xde93` | `ctx+0x148` | the `AccountInfo` record pointer (confirmed at `0x58bf..0x58cf`: `[r1+0x08]` borrow cell, `[r1+0x00]` key pointer, `[r1+0x18]` owner, `[r1+0x20]` rent epoch, `[r1+0x28..0x2a]` the three flags) |
| `+0x08` | `0xda58 stxdw [fp-0xcb0], r3`, then `0xde91` | `ctx+0x150` | `image[0x00..0x08]` |
| `+0x10` | `0xda5a..0xda5e` copy `0x41` bytes to `fp-0x308`; `0xde68..0xde6d` copy them to `ctx+0x158` | `ctx+0x158` | `image[0x08..0x49]` |
| `+0x51` | `0xda33`/`0xda56` and `0xde79` | `ctx+0x199` | the status byte |
| `+0x52` | `0xda5f`, `0xdeac` | `ctx+0x19a` | a `u32` |
| `+0x56` | `0xda61`, `0xdead` | `ctx+0x19e` | a `u16` |

So the `bonding_curve` field spans `ctx+0x148..0x19f`, its image is `0x49` bytes at
`ctx+0x150..0x198`, `ctx+0x150..0x16f` is `image[0x00..0x20]` and `ctx+0x170..0x18f` (the P1
census of 16.3) is `image[0x20..0x40]`.

The gate itself: `0x56e8/0x56e9` point the second operand at `ctx+0x308` and `0x56ed` compares
32 bytes (`0x184e6`, `r3 = 0x20`); `0x56f1`/`0x56f2` sign-extend the result and
`0x56f3 jeq r0, 0x0, +0x16e` jumps to the initialisation at `0x5862`. When the first comparison is
unequal the same key is compared a second time against `r8`, set to `ctx+0x150` at
`0x56db`/`0x56dc`, by `0x5700` (`r3 = 0x20`), and `0x5703 jeq r0, 0x0, +0x15e` also jumps to
`0x5862`. Both unequal falls into `0x5704`, the `NotAuthorized` record `0xc3e5c` (`0x8932` at
`0x5708`, first `u32` 16), which is boxed at `0x5776` with `0x1780` and line `0x133` = 307.

**Gate 307 is `payer.key() == global[0x158] || payer.key() == bonding_curve[0x00..0x20]`.**

Names: the first 32 bytes of the `bonding_curve` image are its first pubkey, the creator in the
pump bonding-curve layout, and `image[0x20..0x40]` that layout's mint, which is the field the P1
census tests for zero **[R for the two names, B for the offsets]**. The 32 bytes at
`global[0x158]` are a pubkey-sized field of the pump `global` account; the bytes pin the offset
but not the identifier, so the name stays **[partial]**.

#### 16.9.4 Gate 302: `payer` against `pool.coin_creator` [B offset, R name]

`0x5a99/0x5a9a` point the second operand at `ctx+0x580` and `0x5a9e` compares 32 bytes
(`r3 = 0x20`); `0x5aa1 jne r0, 0x0, +0x1` then `0x5aa2 ja -0x241` to `0x5862` continues, and the
unequal arm builds the same `NotAuthorized` record (`0x5aa5`, `0x8932` at `0x5aa7`, `0x12f8` at
`0x5aac`) and boxes it at `0x5ab9` with `0x1780` and line `0x12e` = 302.

`ctx+0x580` is `image+0xc0` of the `pool` image that starts at `ctx+0x4c0`, i.e. inside the `0xfc`
byte image and not past it. The `Pool` deserialiser `0x11951` tiles that image exactly, and this is
what names the operand:

| image bytes | store cites | measured content |
|---|---|---|
| `0x00..0x20` | `0x11a9e..0x11aa2` (`stxdw [r6+0x1e]`, `+0x18`, `+0x10`, `+0x08`, `+0x00`) | pubkey 1 |
| `0x20..0x40` | `0x11ab8`, `0x11ab9` | pubkey 2 |
| `0x40..0x60` | `0x11ab4`, `0x11ab6` | pubkey 3 |
| `0x60..0x80` | `0x11ab0`, `0x11ab2` | pubkey 4 |
| `0x80..0xa0` | `0x11a73`, `0x11a75`, `0x11aae` | pubkey 5 |
| `0xa0..0xc0` | `0x11a7d`, `0x11a7f`, `0x11aac` | pubkey 6 |
| `0xc0..0xe0` | `0x11a87`, `0x11a89`, `0x11aaa`, `0x11a8b`, `0x11a8d`, `0x11a8f` | pubkey 7, the gate 302 operand |
| `0xe0..0xf8` | `0x11a9d`, `0x11a9b`, `0x11aa9` | three `u64` |
| `0xf8..0xfa` | `0x11aa7 stxh [r6+0xf8]` | `index: u16` (16.8.1) |
| `0xfa` | `0x11aa5 stxb [r6+0xfa]` | `pool_bump: u8` (16.8.1) |
| `0xfb` | `0x11aa4 stxb [r6+0xfb]` | one trailing bool byte |

Seven 32-byte keys (`0xe0`), three `u64` (`0x18`), a `u16`, a `u8` and a bool tile the `0xfc`
bytes exactly with no gap, so the image holds exactly seven pubkeys and `0xc0` is the seventh. The
`pump_amm` field order puts them in the order `creator`, `base_mint`, `quote_mint`, `lp_mint`,
`pool_base_token_account`, `pool_quote_token_account`, `coin_creator`, and the first three were
already pinned that way in 16.8.1, so the seventh is `coin_creator` **[R for the name, B for the
count, the stride and the offset]**. The body agrees on the role: the second write arm of the
initialisation (P16) builds its one-element shareholder vector out of the same 32 bytes at
`ctx+0x580..0x598` with `share_bps = 0x2710` (`0x5b4a..0x5b65`).

**Gate 302 is `payer.key() == pool.coin_creator`.**

#### 16.9.5 The two gates as one ladder, and the mode selector that reaches them [B mechanics, partial intent]

| line | raise | left operand | right operand | compare cite | equal arm | unequal arm |
|---:|---|---|---|---|---|---|
| 307 | `0x5776` | `payer.key()` | `global[0x158]` | `0x56ed` | `0x56f3` to P10 `0x5862` | second compare |
| 307 | `0x5776` | `payer.key()` | `bonding_curve[0x00..0x20]` | `0x5700` | `0x5703` to P10 `0x5862` | P3 `0x5704`, box at `0x5776` |
| 302 | `0x5ab9` | `payer.key()` | `pool[0xc0]` | `0x5a9e` | `0x5aa1`/`0x5aa2` to P10 `0x5862` | box at `0x5ab9` |

Which gate runs is decided by the P1 census on `bonding_curve[0x20..0x40]`. `0x56cb` clears the
flag at `fp-0x6e0`; `0x56cd..0x56d2` test the three words at `ctx+0x188`, `ctx+0x178`, `ctx+0x180`
and jump out with the flag clear on any non-zero word; `0x56d3..0x56d8` set it to 1 only when the
fourth word at `ctx+0x170` is also zero. `0x56ee/0x56ef` read `[fp-0x6e0] & 1` and `0x56f0 jne`
takes the flag to P4 at `0x5726`, so an all-zero `bonding_curve` mint goes through the `pool` chain
(273 at `0x5740`, 280 at `0x57bd`, 297 at `0x5844`, 302 at `0x5a9e`) and never evaluates the 307
gate, while a live bonding curve evaluates the 307 gate and falls into the initialisation.

One dependency inside P9 is worth naming: `0x5a8d..0x5a90` reads `fp-0x700`, and
`0x5a90 jeq r1, 0x0, +0x11` skips the 302 comparison entirely when that word is zero. On the P8
path the last write to that slot is `0x5730 stxdw [fp-0x700], r0`, i.e. the sign-extended result of
the `0x56ed` comparison, so a payer that matched `global[0x158]` skips the `pool[0xc0]` test while
a payer that entered as the bonding-curve creator does not. The mechanics are `[B]`; the intent
(an admin bypass) is `[partial]`.

#### 16.9.6 One correction to 16.8.1 that this tick measures [B]

Helper `0x541` is the `Option<Account<Pool>>` reader, and its own code fixes the polarity of the
status byte that `try_accounts` stores at `ctx+0x5bc`: `0x54d..0x552` compares the account key
against the all-zero pubkey at `0xc36a0`, the equal arm `0x560..0x564` consumes the record and
writes `0x2` at `out+0x104`, while the deserialisation arm writes `0x3` at `0x55e`. So **2 is the
zero-key placeholder (the account was not supplied) and 3 is a real account**, not the other way
round; 16.8.1's parenthetical "(2 = present, 3 = missing)" is withdrawn. This is what makes P4
coherent: `0x5726 ldxb r1, [ctx+0x5bc]` with `0x5727 jeq r1, 0x2, +0x1` raises `err!` 6019 at
`0x572c` exactly when the `pool` placeholder was passed, and `0x5728 ja +0x7` reaches the 273 gate
at `0x5730` only for a real pool.

**(D2-c) closed [B].** Still open on this body: (D2-d) the store map of the `SharingConfig`
initialisation onto the 3.1 ladder and the source of the `arg+0x24` bump byte (the wrapper writes a
`u32` at `out+0x23` with `0x1383a`, so `arg+0x24` is that word's fourth byte), (D2-e) the event
field order and (D2-f) the reconstructed body.

#### 16.9.7 Corroboration from the initialisation arm: `ctx+0x150` is the creator both ways [B]

The same 32 bytes gate 307 compares `payer` against are the ones the initialisation writes into
`SharingConfig.admin` and into the single shareholder, which pins the role of the operand without
reading any name table. `r8` is set to `ctx+0x150` at `0x56db`/`0x56dc` and the slice contains no
write to `r8` between there and `0x5862`, so the arm reads it directly:

| site | measured |
|---|---|
| `0x5871..0x5878` | `ldxdw [r8+0x00]`, `+0x08`, `+0x10`, `+0x18` stored to `ctx+0x38`, `+0x40`, `+0x48`, `+0x50`, i.e. the `SharingConfig.admin` 32 bytes |
| `0x5893..0x589a` | the same four words stored into the freshly allocated shareholder element (`0x175b2` at `0x588f`) |
| `0x589b` | `sth [element+0x20], 0x2710` = `share_bps` 10000, matching the 34-byte `Shareholder` stride of 3.1 |
| `0x589c..0x589e` | the vector written at `ctx+0x8`, `ctx+0x10`, `ctx+0x0` |

So on this arm the config's admin and its only shareholder are both the bonding curve creator,
which is exactly the key gate 307 requires `payer` to equal (or the `global[0x158]` admin). D2-d
owns the full store map and the `arg+0x24` bump source; this row is cited here only because it
names the 307 operand.

Severity: Informational
Sévérité : Informational
Severity justification: Reverse-engineering measurement of two key-equality gates, one status byte and one register-sourced store inside one handler body; no behavior, fund or consensus effect is measured.

### 16.10 The `SharingConfig` initialisation: the store map onto 3.1 and where the bump comes from (D2-d closed) [B]

Scope: the eleven stores at `0x5862..0x589e`, the serialisation issued at `0x589f..0x58a9`, and the
one byte the body reads out of its own argument block at `0x5863`. The gates that reach this arm are
already closed (16.8 for 6008, 16.9 for 6016); nothing here re-derives them.

The target of every store is `r7`, which by 16.8.1 is the body context `fp-0xbd0`, i.e. the 0x5d0
byte block the wrapper copies out of the `try_accounts` image. `ctx+0x00..0x5c` is the
`SharingConfig` image of 3.1, so the stores below are the initialisation of that image and nothing
else.

#### 16.10.1 Store map, one row per 3.1 ladder row [B]

| 3.1 row | serialised field | memory target | storer | value measured |
|---:|---|---|---|---|
| 1 | `bump: u8` | `ctx+0x5a` | `0x5864 stxb` | `[arg+0x24]`, the bump slot of 16.10.2 |
| 2 | `version: u8` | `ctx+0x5b` | `0x5865 stb` | constant `0x2` |
| 3 | `status: u8` | `ctx+0x58` | `0x5866 stb` | constant `0x1` |
| 4 | `mint: [u8; 32]` | `ctx+0x18..0x38` | `0x586d`, `0x5870`, `0x586f`, `0x586e` | the 32-byte key of `ctx+0xc0`, i.e. the `mint` account |
| 5 | `admin: [u8; 32]` | `ctx+0x38..0x58` | `0x5871..0x5878` | the 32 bytes at `ctx+0x150` (`bonding_curve` image `[0x00..0x20]`) |
| 6 | `admin_revoked: u8` | `ctx+0x59` | `0x5879 stb` | constant `0x0` |
| 7 | `shareholders: Vec<Shareholder>` | cap `ctx+0x0`, ptr `ctx+0x8`, len `ctx+0x10` | `0x589e`, `0x589c`, `0x589d` | capacity 1, one element, length 1 |
| 7 | element `address` | element `+0x00..0x20` | `0x5893..0x589a` | the same `ctx+0x150` 32 bytes |
| 7 | element `share_bps` | element `+0x20` | `0x589b sth` | `0x2710` = 10000 |

Reading the rows against the packer of 3.1 settles two things that 3.1 could only mark `[partial]`
before this tick, because a picker that writes `bump` and `version` next to each other cannot be
ambiguous:

* `ctx+0x5a` is `bump`, since the byte stored there is the program-derived bump of 16.10.2 and not a
  constant. `ctx+0x5b` is `version`, since it is a constant `0x2`. Both names are `[R]`, the
  pairing is `[B]`.
* the `Vec<Shareholder>` head is exactly `(cap, ptr, len)` at `+0x0`, `+0x8`, `+0x10` as 3.1 tabulated,
  and the single element uses the 34-byte stride of 3.1 with `share_bps` at `+0x20`.

The two address copies are exact, and their instruction order is not the memory order:
`0x5869..0x586c` load `[key+0x8]`, `[key+0x10]`, `[key+0x18]`, `[key+0x0]` into `r2`, `r3`, `r4`,
`r1`, then `0x586d/0x5870/0x586f/0x586e` store them at `+0x18`, `+0x20`, `+0x28`, `+0x30`, which is
a linear 32-byte copy from `[ctx+0xc0] -> [0x00]` into `ctx+0x18`. The same holds for the admin
copy at `0x5871..0x5878`, which loads `[r8+0x00..0x18]` in order and stores at `+0x38..0x58`.

The one allocation in the arm is the shareholder element:

| site | measured |
|---|---|
| `0x587a..0x588c` | read the heap cursor at `0x300000000` (`0x587c`), form `cursor - 0x22` (`0x5880`), and compare against `0x300000007` (`0x588c`) and `0x300007fde` (`0x5885`) before use |
| `0x588d..0x588f` | `r1 = 2`, `r2 = 0x22`, `call 0x175b2`, a 19-insn shim that swaps its two arguments and calls `0x14ba9`; the element pointer comes back in `r2` |
| `0x5892` | the advanced cursor is written back to `0x300000000` |
| `0x589c` | the element pointer is stored at `ctx+0x8`, i.e. the vector pointer |

So the account is created with exactly one shareholder, the 100 percent holder being the same key
as `admin`. Both are the `bonding_curve` image `[0x00..0x20]`, which 16.9.7 already tied to the
gate 307 operand.

#### 16.10.2 The bump byte at `arg+0x24` is slot 4 of the bump block [B]

The body stores `[arg+0x24]` into `ctx+0x5a`, and `arg` is the wrapper's `try_accounts` out buffer:
`0x56d9 stxdw [fp-0x6f0], r2` saves the second argument, `0x5862 ldxdw r1, [fp-0x6f0]` reads it
back, and `r2` is `fp-0x5e8` (`0x13845`), the same base the wrapper passed to `try_accounts` at
`0x13827`. So `arg+0x24` is `out+0x24`.

The wrapper fills that byte twice, in this order:

| site | measured |
|---|---|
| `0x13819` | `stxb [fp-0xbe1], -1` |
| `0x1381a` | `stxw [fp-0xbe5], -1`, so `fp-0xbe5..fp-0xbe2` become `0xFF` |
| `0x1381b` | `stb [fp-0xbe7], 0x0` |
| `0x1381e`, `0x13820` | `r1 = fp-0xbe7`, `stxdw [fp-0xff8], r1`: the address of the 7-slot block is handed to `try_accounts` |
| `0x13837`, `0x13838` | `ldxw [fp-0xbe7]` stored to `out+0x20`, so `out+0x20..0x23` = slots 0..3 |
| `0x13839`, `0x1383a` | `ldxw [fp-0xbe4]` stored to `out+0x23`, so `out+0x23..0x26` = slots 3..6 |

With the block base at `fp-0xbe7`, slot 3 is `fp-0xbe4` and slot 4 is `fp-0xbe3`. The store at
`0x1383a` is little endian at `out+0x23`, therefore `out+0x23` = slot 3, **`out+0x24` = slot 4**,
`out+0x25` = slot 5, `out+0x26` = slot 6. Slot 3 is written twice (once as the top byte of the first
word, once as the bottom byte of the second), which is the compiler copying a 7-byte block as two
overlapping words.

This corrects the closing sentence of 16.9.6, which called `arg+0x24` the fourth byte of the word at
`0x1383a`. It is the second byte of that word, because the first byte landed at `out+0x23`. The
mechanism (`out+0x24` = slot 4) is `[B]`; the earlier byte arithmetic was off by one.

#### 16.10.3 No descriptor wrote `fp-0xbe4`: `try_accounts` wrote it through the caller slot [B]

`try_accounts` opens with `0xd962 ldxdw r2, [r5 -0xff8]`, where `r5` is the caller frame pointer set
at `0x13825`, and parks the result at `fp-0xc38` (`0xd963`). That pointer is read back six times and
each read is followed by exactly one one-byte store, which is the whole bump block:

| slot | write site | derivation | program id |
|---:|---|---|---|
| 0 | `0xde00 stb [r2+0x0], 0x1` | completion flag set after the six derivations | n/a |
| 1 | `0xddfe stb [r2+0x1]` | `find_program_address([b"__event_authority"])`, static seeds at `0xc8be8` | constant B = `pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA` |
| 2 | `0xdc13 stb [r2+0x2]` | `find_program_address([b"__event_authority"])`, static seeds at `0xc8be8` | `[fp-0x970]`, the executing program `pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ` |
| 3 | `0xdc47 stb [r2+0x3]` | `find_program_address([b"global"])`, static seeds at `0xc8c28` | constant A = `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P` |
| 4 | `0xdb3b stb [r2+0x4]` | `find_program_address([b"sharing-config", mint])`, literal at `0xc4c0e` length 14, second seed the 32-byte key of `[fp-0x348]` | `[fp-0x970]`, the executing program |
| 5 | `0xdd37 stb [r2+0x5]` | `find_program_address([b"bonding-curve", mint])`, literal at `0xc4d6f` length 13, same key at `0xdd07..0xdd0c` | constant A, the pump program |
| 6 | `0xdd92 stb [r2+0x6]` | `find_program_address([b"__event_authority"])`, static seeds at `0xc8be8` | constant A, the pump program |

Every derivation is a `sol_try_find_program_address` call to `0x16f53` whose bump is read back from
`out+0x20` (`0xdb38`, `0xdc11`, `0xdc45`, `0xdd35`, `0xdd90`, `0xddfd` all execute `ldxb r1, [r10-0x940]`),
and the address it returns is what the neighbouring key comparison checks. Slot 4 is the sharing
config arm: the literal is `sharing-config` (14 bytes, `0xc4c0e`), the second seed is the 32-byte key
at `[fp-0x348]`, and the same key is the second seed of the `bonding-curve` derivation at `0xdd07`,
which is the independent confirmation that the key is the mint.

The two 32-byte program ids are not rodata references but assembled immediates. `tools/d2_bumps_map.py`
reassembles each group of four `lddw` immediates and checks it against the rodata keys the 16.8.4
gates use: constant A reassembles to `6EF8rrec...` (`0xc4ecd`) and constant B to `pAMMBay...`
(`0xc4f3c`), both exact. The two static seed arrays decode as
`{ptr 0xc3ec2, len 17}` = `__event_authority` and `{ptr 0xc4b17, len 6}` = `global`, with the
pointer stored in the high half of the first word of each 16-byte entry.

So the answer to "which descriptor wrote `fp-0xbe4`" is: none. The wrapper only pre-fills the block
with placeholders (`0x0` at slot 0 and `0xFF` from slot 2 to slot 6), and slot 3 is overwritten by
`try_accounts` at `0xdc47` through the pointer it received at `fp-0xff8`. The byte the body reads,
`out+0x24`, is not touched by the wrapper at all.

#### 16.10.4 Serialisation issued in the same arm [B]

Immediately after the stores the body calls the 3.1 packer:

| site | measured |
|---|---|
| `0x589f`, `0x58a0` | `out = fp-0x638` |
| `0x58a1` | `r2 = r7`, the `SharingConfig` image just filled |
| `0x58a2`, `0x58a4` | `r3 = r4 = 0xc4ead`, so the packer's `crate::ID` guard of 3.1 compares the program against itself |
| `0x58a6` | `call 0x989` |
| `0x58a7`, `0x58a8`, `0x58a9` | payload `[fp-0x630]`, tag `[fp-0x638]`, and `jne r3, 0x2, +0x29c` as the error arm |

So the arm contains both the in-memory fill and one immediate serialisation of it, with the tag read
back in the same block. That is the last SharingConfig-specific step of the body; the borrow
bookkeeping that follows (`0x58aa..0x58be`) touches `ctx+0x5d8` and `ctx+0x148` and belongs to the
account drop path, not to this map.

#### 16.10.5 What D2-d settles and what it hands on

D2-d is closed as `[B]`: every one of the eleven stores is mapped onto a named row of the 3.1
ladder, the bump byte is a derived program bump and not a constant, and the writer of the wrapper
slot is `try_accounts` itself. Two residuals, both stated rather than guessed:

* `[B] (closed in P2-b)`: the reason `try_accounts` writes only slots 1 to 6 for six seeded accounts while the
  wrapper pre-fills seven slots is a source-level detail of the generated `try_accounts`; the
  measured behaviour is the table above. The only two slots this body reads are slot 4
  (`0x5863`) and slot 2 (`0x5beb` block, `0x5be8 ldxb [arg+0x22]`, which 16.10.5 hands to D2-e);
  slots 0, 1, 3, 5 and 6 have no consumer in `0x56c7..0x5cd2`.
* `[B] (closed in P2-b)`: `0x56ca jne r4, 0x0, +0x47c` sends a non-zero `ctx+0x5b` to `0x5b47`, which is the
  epilogue that returns the record already staged at `fp-0x6d8` (`0x5b44`, `0x5b45`), while the head
  of the 6019 raise that precedes it is `0x5b3e..0x5b43`. The jump target is `[B]`; whether that arm
  is meant to return that staged record is left to D2-f, since it is a raise path and not part of
  the initialisation map.

Still open on this body: (D2-e) the event emitted and its field order, starting from the
discriminator `0xc3dbf` at `0x5bef` and the earlier read `0x5be8 ldxdw [fp-0x6f0]` + `0x5be9 ldxb
[r1+0x22]` which touches slot 2 of the same bump block, and (D2-f) the reconstructed body.

Severity: Informational
Sévérité : Informational
Severity justification: Static measurement of the initialisation stores of one handler body and of the bump block it consumes; no behavior, fund or consensus effect is measured.

### 16.11 The event of `0x56c7`: identity, the eight-field borsh order and the two emissions (D2-e closed) [B]

D2-e asked for the event this body emits and for its field order. Answer, on the deployed bytes: the
body builds one `CreateFeeSharingConfigEvent` image at `fp-0x470`, serialises it twice through the
same monomorphised serialiser `0xe41c`, publishes the first copy with `sol_log_data` (`emit!`) and
wraps the second copy in a self instruction (`emit_cpi!`). The serialiser has exactly two callers in
the whole program (`0x5bd9` and `0x5bee`, both inside `0x56c7`; `p.callers(0xe41c)`), so the
serialiser, the struct and this handler stand in a one to one relation.

#### 16.11.1 Two 8-byte constants with two different jobs [B]

| constant | where written | what it prefixes |
|---|---|---|
| `0x58fb74b8c8aa6985` | `0xe434 lddw r2, 0x58fb74b8c8aa6985` then `0xe436 stxdw [r0+0x0], r2`, inside the serialiser | the payload only: it is the event discriminator |
| `0xe445a52e51cb9a1d` | rodata `0xc3dbf`, `0x5bef`/`0x5bf1` load the base and `0x5bf3` forms base+8 | the self-instruction data only: the Anchor event-CPI tag |

The payload discriminator is a preimage match, not a guess. `stxdw` stores little endian, so the
immediate `0x58fb74b8c8aa6985` materialises the bytes `85 69 aa c8 b8 74 fb 58`, and
`sha256("event:CreateFeeSharingConfigEvent")[0..8]` is exactly `8569aac8b874fb58`. The same test on
the discriminator 8.6 already measured for `claim_social_fee_pda` reproduces its bytes:
`sha256("event:SocialFeePdaClaimed")[0..8]` = `3212c141edd2eaec`, the memory bytes of the
`0xecead2ed41c11232` immediate at `0xc667`. The name is `[R]` (the deployed bytes carry no name
string); the discriminator value and the hash relation are `[B]`.

The tag at `0xc3dbf` sits in a byte table, not in an aligned 16-byte constant:
`tools/d2_va_read.py 0xc3db0 48` gives `... e4 45 a5 2e 51 cb 9a 1d  f1 9a 6d 04 11 b1 6d bc
44 65 61 64 6c 6f 63 6b 64 65 61 64 6c 6f 63 6b`, so the second word `f19a6d0411b16dbc` is the
next table entry followed by the ascii text `Deadlockdeadlock`. This body never copies it: the range
it hands to `0x21dc` is `[0xc3dbf, 0xc3dbf+8)`, because `0x5bf5` stores the base as the start and
`0x5bf4` stores base+8 as the end (`16.11.5`).

#### 16.11.2 The event image in memory at `fp-0x470` [B]

`0x5bb5`/`0x5bb6` set `r9 = fp-0x470`, every staging store below writes inside that block, and both
serialiser calls pass `r2 = r9`. With the block base `E = fp-0x470`:

| E+ | field | store site | source |
|---:|---|---|---|
| `0x00` | shareholder `Vec` capacity | `0x1cb9 stxdw [r7+0x0], r6` inside `0x1c93`, entered at `0x5bb8` with `r1 = fp-0x470` | the clone length |
| `0x08` | shareholder `Vec` pointer | `0x1cb7` | fresh allocation of `0x22 * len` bytes (`0x1c9a`, `0x1cb6` memcpy) from `[ctx+0x8]` |
| `0x10` | shareholder `Vec` length | `0x1cb8` | `[ctx+0x10]`, staged at `0x5bb3`/`0x5bb4` |
| `0x18` | timestamp `i64` | `0x5bbb stxdw [fp-0x458], r2` | `[fp-0x6e0]`, loaded at `0x5b7e` from `[fp-0x300]` (`16.11.3`) |
| `0x20` | mint `Pubkey` | `0x5bbc`..`0x5bc2` | `[fp-0x60..fp-0x48]`, staged at `0x5b82`..`0x5b88` from `[ctx+0xc0]->[0x00]` |
| `0x40` | bonding curve `Pubkey` | `0x5bc4`..`0x5bca` | `[fp-0x90..fp-0x78]`, staged at `0x5b8b`..`0x5b92` from `[ctx+0x148]->[0x00]` |
| `0x60` | sharing config `Pubkey` | `0x5ba1`..`0x5baa` | `[ctx+0x60]->[0x00]`, the key of the info record the 15.4 walk also uses for `sharing_config` |
| `0x80` | admin `Pubkey` | `0x5bab`..`0x5bb2` | `r8 = ctx+0x150` = bonding curve image `[0x00..0x20]`, the curve creator |
| `0xa0` | pool `Option` tag | `0x5bcc stxb [fp-0x3d0], r6` | `r6`, 0 at `0x5b93` and 1 at `0x5ba0` |
| `0xa1` | pool `Pubkey` | `0x5bce`..`0x5bd5` | `[fp-0x310..fp-0x328]`, staged at `0x5b96`..`0x5b9f` from `[ctx+0x4b8]->[0x00]` |
| `0xc1` | status `u8` | `0x5bcd stxb [fp-0x3af], r1` | `[ctx+0x58]`, the byte this same body wrote as 1 at `0x5866` (16.10) |

Three details that the table makes explicit:

* the base is `fp-0x470` for the whole block, so `E+0xa0`, `E+0xa1` and `E+0xc1` are `fp-0x3d0`,
  `fp-0x3cf` and `fp-0x3af`. The last 32 bytes of the pool key land at `E+0xa1..0xc1` and the status
  byte follows immediately, which is why the `sth` shape of the state ladder (`share_bps`) does not
  appear here.
* the pool arity is measured twice and agrees: the tag is 1 only when `[ctx+0x5bc] != 2` at
  `0x5b94`/`0x5b95`, and `ctx+0x5bc` is the `Option<Account<Pool>>` status byte whose 2 means the
  zero-key placeholder (16.9.6). A supplied pool therefore yields `Some(key)` and an absent pool
  yields the single byte 0.
* the shareholder vector in the event is a **clone**, not the state buffer: `0x1c93` allocates
  `0x22 * len` bytes, memcpys the state elements (`0x1cb6 call 0x184d9`) and writes
  `cap = ptr = len` words at `E+0x00`..`E+0x10`. The state image it reads is `ctx+0x0`/`ctx+0x8`/
  `ctx+0x10`, the ladder 3.1 fills at `0x589c`..`0x589e`.

#### 16.11.3 The timestamp is the clock sysvar, taken at event build time [B]

The `E+0x18` word does not come from the accounts struct. The chain is:

| site | measured |
|---|---|
| `0x5b2b`, `0x5b2c` | `r1 = fp-0x328` |
| `0x5b2d` | `call 0x1621e`, the `Clock::get` wrapper |
| `0x162224`..`0x162226` | it zeroes five words at its own `fp-0x28` and calls `sol_get_clock_sysvar` on that buffer |
| `0x162228`, `0x162234`, `0x162239` | it writes the tag at `r1+0x00` (`0` for Ok at `0x162234`, `1` for Err at `0x162238`) and the 40-byte `Clock` at `r1+0x08..0x30` |
| `0x5b2e`, `0x5b2f` | `ldxdw r1, [fp-0x328]`, `jeq r1, 0x0, +0x4d` continues only on the Ok tag |
| `0x5b30`..`0x5b3a` | the Err tag is folded into the error shim `0x15a5f` (`0x15a68` writes tag 2 into the new error object and `0x15a70`/`0x15a71` publish it as tag 1) |
| `0x5b7d`, `0x5b7e` | `ldxdw r1, [fp-0x300]` then `stxdw [fp-0x6e0], r1` |

With `fp-0x328` as the out base of `0x1621e`, the `Clock` image starts at `fp-0x320` and its fifth
word is `fp-0x320 + 0x20 = fp-0x300`. That fifth word is `unix_timestamp` in the solana
`Clock` layout (`slot`, `epoch_start_timestamp`, `epoch`, `leader_schedule_epoch`,
`unix_timestamp`), so `E+0x18` is the sysvar `unix_timestamp` of the slot that executes the
instruction.

Correction to a slot reading that earlier ticks left implicit: `[fp-0x6e0]` is the access-flag word
only up to `0x5b2a` (written `0x56cc`/`0x56d5`/`0x56d8`, read `0x56ee` and `0x5b28`). `0x5b7e`
overwrites it with the timestamp, `0x5bea` overwrites it again with the bump byte, and `0x5c7f` and
`0x5cab` reuse it for the pump-CPI staging. The slot carries three different values in this body and
the event's first field is the second of them.

#### 16.11.4 The borsh order of `0xe41c`, read off the cursor [B]

`0xe41c` reserves one `0x100`-byte buffer from the program heap (`0xe41d`..`0xe433`, cursor at
`0x300000000`) and appends through a cursor kept at `fp-0x10` (grown by `0x1af8` when needed). The
append sequence is the borsh order:

| step | site | bytes appended | source |
|---:|---|---:|---|
| 1 | `0xe434`, `0xe436` | 8 | the discriminator immediate |
| 2 | `0xe437`, `0xe438` | 8 | `[r7+0x18]` |
| 3 | `0xe439`..`0xe440` | 32 | `[r7+0x20..0x40]` |
| 4 | `0xe441`..`0xe448` | 32 | `[r7+0x40..0x60]` |
| 5 | `0xe449`..`0xe458` | 1, then 32 when the tag is 1 | `[r7+0xa0]`, `[r7+0xa1..0xc1]` |
| 6 | `0xe45b`..`0xe462` | 32 | `[r7+0x60..0x80]` |
| 7 | `0xe463`..`0xe46a` | 32 | `[r7+0x80..0xa0]` |
| 8 | `0xe46d`..`0xe4a0` | 4 then `0x22` per element | `u32 [r7+0x10]`, elements from `[r7+0x8]`, each `32` bytes plus `u16` at `+0x20` |
| 9 | `0xe4a1`, `0xe4b8` | 1 | `[r7+0xc1]` |
| 10 | `0xe4bb`..`0xe4c0` | none | publishes `{cap, ptr, len}` at the caller out slot `[fp-0x28]` |

Step 5 writes the tag byte first (`0xe44c` or `0xe44f`) and only appends the 32 key bytes on the
`Some` arm, which is borsh `Option<Pubkey>`. Step 8 writes a `u32` length (`0xe47d stxw`) and
guards it with `0xe46e lddw r3, 0xffffffff` plus `0xe470 jgt r6, r3, +0x54`, which is the
`as u32` width of a borsh sequence. Step 9 is one byte, so the status field is a byte-sized enum.

Folding 16.11.2 and 16.11.4 together gives the event, in borsh order, with the measured source of
every field:

| # | field | width | memory slot | source in the accounts struct |
|---:|---|---:|---|---|
| 1 | `timestamp: i64` | 8 | `E+0x18` | clock sysvar `unix_timestamp` |
| 2 | `mint` | 32 | `E+0x20` | `[ctx+0xc0]` key |
| 3 | `bonding_curve` | 32 | `E+0x40` | `[ctx+0x148]` key |
| 4 | `pool: Option<Pubkey>` | 1 or 33 | `E+0xa0` | `ctx+0x5bc != 2` and `[ctx+0x4b8]` key |
| 5 | `sharing_config` | 32 | `E+0x60` | `[ctx+0x60]` key |
| 6 | `admin` | 32 | `E+0x80` | `ctx+0x150`, the curve creator |
| 7 | `initial_shareholders: Vec<Shareholder>` | 4 + `0x22 n` | `E+0x00` | clone of `ctx+0x0`/`0x8`/`0x10` |
| 8 | `status` | 1 | `E+0xc1` | `ctx+0x58`, the byte written 1 at `0x5866` |

One shareholder (the case this body always writes, 16.10) makes the payload
`8 + 8 + 32 + 32 + 33 + 32 + 32 + 4 + 34 + 1 = 216 = 0xd8` bytes, so it fits the first `0x100`
allocation and the grow path `0x1af8` is not taken; with `pool = None` the same sum is `150`. The
memory order in 16.11.2 (`Vec`, timestamp, mint, bonding curve, sharing config, admin, pool, status)
is not the borsh order (`Option` before `sharing_config`, `Vec` before `status`), which is what makes
the two tables differ. Both orders are `[B]`; the reordering is the usual `repr(Rust)` alignment
layout (`[R]` for the reason).

#### 16.11.5 `emit!` and `emit_cpi!` are two independent serialisations of the same value [B]

First emission, the log:

| site | measured |
|---|---|
| `0x5bd8` | `r2 = r9`, the event image |
| `0x5bd9` | `call 0xe41c`, out `fp-0x328` |
| `0x5bda`, `0x5bdc` | length `[fp-0x318]` to `fp-0x88`, pointer `[fp-0x320]` to `fp-0x90` |
| `0x5bde`, `0x5be0`, `0x5be1` | `r1 = fp-0x90`, `r2 = 1`, `call 0x161a7` |

`0x161a7` is a two instruction shim (`0x161a7 call sol_log_data`, `0x161a8 exit`), and a
`SolBytes` element is `{addr, len}`, so the log carries exactly one field: the discriminator plus the
eight serialised fields.

Second emission, the self instruction:

| site | measured |
|---|---|
| `0x5beb`..`0x5bee` | `r1 = fp-0xf0`, `r2 = r9`, `call 0xe41c` (a second, independent `0x100` buffer) |
| `0x5bef`..`0x5bf5` | the tag base `0xc3dbf` at `fp-0xb8`, its end `0xc3dbf+8` at `fp-0xb0` |
| `0x5bf6`..`0x5bfd` | payload pointer `[fp-0xe8]` to `fp-0xd0` and `fp-0xd8`, payload end `[fp-0xe8]+[fp-0xe0]` to `fp-0xc0`, capacity `[fp-0xf0]` to `fp-0xc8` |
| `0x5c02` | `call 0x21dc`, the two-range concatenation, out `fp-0x20` |
| `0x21dc` `0x2239`..`0x2240` | copies `[r3+0x20]`..`[r3+0x28]`, the 8 tag bytes, into the first bytes of the new buffer |
| `0x21dc` `0x2243`..`0x224a` | then copies `[r3+0x8]`..`[r3+0x18]`, the payload |
| `0x5c03`, `0x5c04` | data pointer `[fp-0x18]`, data length `[fp-0x10]` |
| `0x5c05`..`0x5c07` | `r1 = 0x22`, `r2 = 1`, `call 0x19e3`: one `AccountMeta` allocation |
| `0x5c08`..`0x5c10` | its 32 key bytes from `[fp-0x120]`, the `AccountInfo` clone made at `0x5be7` from the inline record `ctx+0xe8` |
| `0x5c11` | `sth [r0+0x20], 0x1`, so `is_signer = 1` and `is_writable = 0` |
| `0x5c12`..`0x5c14` | metas `Vec` `{cap 1, ptr, len 1}` at `fp-0x90`/`fp-0x88`/`fp-0x80` |
| `0x5c15`..`0x5c1e` | `call 0x16eb0`: out `fp-0x328`, program id `0xc4ead`, data `r7`/`r9` |
| `0x5c1f`..`0x5c24` | one `0x30`-byte `AccountInfo` copy of the same clone at `fp-0x90` |
| `0x5c25`..`0x5c36` | the signer seed set `[[0xc3ec2 len 0x11], [bump len 1]]`, count 2 at `fp-0x38`, published through `fp-0x1000`/`fp-0xff8` |
| `0x5c3d` | `call 0x161ae` |
| `0x5c3e`, `0x5c41` | result tag compared with `i64::MIN + 0x1a`, anything else to the error shim `0x15a5f` at `0x5c59` |

Four measurements this block adds to the phase map:

* `0xc4ead` base58-decodes to `pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ`, so the self instruction
  is addressed to the executing program, which is what makes it a self CPI. The same constant is
  the `crate::ID` guard the packer `0x989` receives at `0x58a4` and `0x5b6e`.
* the seed literal is `__event_authority` (`0xc3ec2`, length `0x11`) and the bump is
  `[arg+0x22]`, the byte `0x5be9` reads from the `try_accounts` out image, which 16.10.3 already
  fixed as slot 2 of the 7-slot block under the executing program.
* `0x161ae` reaches `sol_invoke_signed_rust`: `0x161ae` calls `0x164a3` at `0x16214`, and `0x164a3`
  issues the syscall at `0x16502`. So the second emission signs with the PDA seeds instead of the
  plain `invoke` shape.
* the concatenation order is tag first, payload second (`0x2239` runs before `0x2243`), so the self
  instruction data is `e445a52e51cb9a1d` followed by the 216-byte event for a one-shareholder
  config, 224 bytes in total.

#### 16.11.6 Reach of the event block, and one correction to 16.3 P17 [B]

`0x5b7d` has exactly one predecessor: `0x5b2f`, the `Ok` arm of the clock read inside the block that
starts at `0x5b2b`. `0x5b2b` is entered two ways, and both are measured:

* fall-through from `0x5b2a jne r1, 0x0, +0x13` when the access flag is 0, that is when the second
  bonding curve key (`ctx+0x170`..`ctx+0x188`) is not all zero;
* `0x5cd1 jeq r3, 0x2, -0x1a7` at the end of the pump-CPI chain, which returns to `0x5b2b`.

The other arm of the flag test, `0x5b3e`..`0x5b73`, requires a supplied pool (`ctx+0x5bc != 2`,
`0x5b3f`) and rewrites the config admin and shareholder vector from `pool.coin_creator`
(`0x5b4a`..`0x5b68`) before re-serialising at `0x5b70`; it leaves through `0x5b74` to `0x5c6d` and
does not pass `0x5b7d`. Whether the block at `0x5cd1` can make the event arm run a second time is a
control-flow question about the CPI chain and stays open for D2-f.

One correction to the phase map: 16.3 P17 describes the last key staged before the value block as
"the mint at `r8` (`0x5bab`..`0x5bb2`)". It is the admin, not the mint. `r8` is `ctx+0x150`, the
bonding curve image `[0x00..0x20]` (16.9), and 16.10 already uses the same `r8` as the source of the
`admin` ladder row at `0x5871`..`0x5878`. The mint is `[ctx+0xc0]`, staged at `0x5b7f`..`0x5b88` and
stored at `E+0x20`.

#### 16.11.7 What D2-e settles and what it hands on

D2-e is closed as `[B]`: the event is the `CreateFeeSharingConfigEvent` value named by the
discriminator preimage, its eight borsh fields are read in a measured order, every field has a
measured source in the accounts struct or in the clock sysvar, and both emissions are walked down to
the syscall that carries them (`sol_log_data` for the log, `sol_invoke_signed_rust` for the self
CPI). Two residuals are stated rather than guessed:

* `[partial]`: the event arm sits behind the clock `Ok` arm and behind the access-flag test, and the
  `0x5cd1` edge can reach the same block a second time; whether a single instruction can therefore
  log the event twice is a D2-f control-flow question, not a field-order question.
* `[partial]`: that the two serialisations correspond to a macro pair (`emit!` then `emit_cpi!`) is
  the pattern 8.6 measured for another handler of this program; the bytes establish two
  independent serialisations of one value and do not carry the macro names.

The remaining D2 item is (D2-f), the reconstructed body, which inherits 16.11.6 as its first open
question.

Severity: Informational
Sévérité : Informational
Severity justification: Static reading of one handler body's event builder and its two emission paths, with no behaviour, fund or consensus effect measured.

### 16.12 The reconstructed body, the reach of the event block and the macro pairing (D2-f closed) [B]

This tick closes item **(D2-f)**, the last named item on the `create_fee_sharing_config` body. Bytes read
this tick: the pinned slice, targeted `dis` windows over `0x56c7..0x56f4`, `0x5726..0x5745`, `0x5862..0x58a8`,
`0x58a8..0x58c2`, `0x58f0..0x59cc`, `0x59c4..0x59d5`, `0x5a7c..0x5a8d`, `0x5abd..0x5b26`, `0x5b26..0x5b50`,
`0x5b50..0x5b7d`, `0x5bd9..0x5c12`, `0x5c12..0x5c6d` and `0x5c6d..0x5cd2`, plus `0x10de9` (`0x10e90..0x10f30`)
and `0xc3e80` as rodata. Three tools were written for this tick: `scratch/d2f_cfg.py` (CFG, predecessors,
reachability, Tarjan SCC over the 1548 slot body), `scratch/d2f_calls.py` (call census) and
`scratch/d2f_callers.py` / `scratch/d2f_builder_calls.py` (caller and callee census of the three CPI helpers),
plus the three preimage probes `scratch/d2f_consts.py`, `scratch/d2f_consts2.py` and `scratch/d2f_disc_cpi.py`.

#### 16.12.1 The body contains no loop: both cycles are panic paths [B]

The CFG over `0x56c7`..`0x5cd2` decodes **1510 instructions** (1548 slots minus the 38 second halves of `lddw`
immediates, which is the same bookkeeping 16.1 records). Edges are taken from `ja`, the 21 conditional jumps,
the call fall-through and the two-slot `lddw`. Tarjan gives 922 SCCs, of which exactly two are non trivial, and
both are abort paths rather than loops:

| cycle | members | why it cannot iterate |
|---|---|---|
| Rc overflow | `0x58b4`..`0x5a8c` | every entry into `0x58b4` is a failed refcount overflow guard (`0x58b3 jne r3, 0x1, +0x1` falling into `0x58b4`), and `0x58b4` is `call abort`: the relocation table names the symbol `abort` |
| Location display | `0x571c`..`0x57da` | `0x57da ja -0xbf` re-enters the panic block at `0x571c`, which formats through `0x178c8` (`0x5725`) and never returns |

No cycle contains `0x5b2b` (the join target), `0x5b7d` (the event block) or `0x5c76` (the last leg). The
predecessor sets are single-entry where it matters: `pred[0x5b7d] = {0x5b2f}`, `pred[0x5c6d] = {0x5b75}`,
`pred[0x5c76] = {0x5c6e}`, `pred[0x5b2b] = {0x5b2a, 0x5cd1}`, and `pred[0x5b46]` (the return block) holds
thirteen sites: `0x5861, 0x58a9, 0x59cf, 0x5b25, 0x5b3d, 0x5b45, 0x5b73, 0x5b7c, 0x5c68, 0x5c6c, 0x5c75, 0x5ca4,
0x5cd2`. Reachability, computed on the same graph: `0x5b7d` cannot reach `0x5c76`, `0x5cd1` or `0x5b2b`;
`0x5b2b` cannot reach `0x5c76`; `0x5c76` cannot reach itself **[B]**.

#### 16.12.2 Residual 1 answered: `0x5cd1` is a join edge and the event block runs once per instruction [B]

`0x5cd1 jeq r3, 0x2, -0x1a7` targets `0x5b2b`, which is the first slot of the **shared tail**, not a loop
head. Two arms enter that tail and each enters it once:

| arm | entry into the tail | how it arrives |
|---|---|---|
| non graduated (`[fp-0x6e0] & 1 == 0`) | fall-through `0x5b2a` -> `0x5b2b` | P15 leaves the flag test clear |
| graduated (`[fp-0x6e0] & 1 != 0`) | `0x5cd1` -> `0x5b2b` | P16, P20, P21 finish their CPI chain and jump into the same slot |

From `0x5b2b` the path is fixed and terminating: `0x5b2b`..`0x5b2f` reads the clock, `0x5b2f jeq r1, 0x0, +0x4d`
lands on `0x5b7d` (the event block), and both exits of the event block go to the single return block:
`0x5c54 ja -0x10e` on the invoke result and `0x5c6c ja -0x127` on the invoke error arm. So one instruction can
emit the `CreateFeeSharingConfigEvent` **exactly once**, on either arm, and the double emission that 16.11.7
kept open is excluded by the graph, not by reading intent. The tail also keeps the `r8 = ctx+0x38` that
`0x5b26`/`0x5b27` set on the first arm and re-enters at `0x5b2b` on the second, which is why the jump targets
`0x5b2b` and not `0x5b26` **[B]**.

#### 16.12.3 Residual 2 answered: the two emissions are the two Anchor event routes [B machinery, R names]

The 8 bytes that `0x21dc` copies first, from the rodata at `0xc3dbf` (`0x5bef lddw r1, 0xc3dbf`,
`0x5bf1/0x5bf3` form the end pointer `+8`), are `e4 45 a5 2e 51 cb 9a 1d`. Computed this tick with the method
16.11.1 validated: `sha256("anchor:event")[0..8] = 1d9acb512ea545e4`, whose little-endian memory image is exactly
those bytes (`scratch/d2f_consts.py`). The two emissions therefore are:

* `0x5bd9` serialise, `0x5be1 call 0x161a7`, which is `sol_log_data` followed by `exit` (`0x161a7 call -0x1`,
  syscall `sol_log_data`, `0x161a8 exit`): a log of the borsh payload alone.
* `0x5bee` serialise, `0x5c02 call 0x21dc` (tag bytes first, then payload), `0x5c1e call 0x16eb0` (inner
  instruction, program `0xc4ead`), `0x5c3d call 0x161ae` (invoke): an inner instruction whose data is
  `event_ix_tag || payload`, signed by the `__event_authority` seeds `0x5c2b`/`0x5c32` with the bump from
  slot 2 `0x5be8`/`0x5be9`.

Those are the two event routes of the framework: one that logs the borsh value and one that re-enters the
program as an inner instruction carrying the `anchor:event` prefix. The macro identifiers `emit!` and
`emit_cpi!` are **[R]**: the bytes fix the two mechanisms and the tag preimage, they do not carry the source
spelling **[B]**.

#### 16.12.4 Two corrections: `0x58b4` is `abort`, and P11/P13 are refcount increments [B]

* 16.1 tagged `0x58b4 call -0x1` as an unresolved relocation artifact **[partial]**. The relocation table
  resolves it: the symbol is `abort` (the call census prints `sys:abort` at `0x58b4`). The surrounding code is
  the shared-reference strong count increment with its overflow guard, `0x58aa..0x58b3`: load the handle at
  `[ctx+0x5d8]`, load `[handle+0x8]` (the reference block), load `[block]`, add one, and `0x58b3 jne r3, 0x1`
  falling into the abort. Every `ja -0x..` in P11 that targets `0x58b4` is that guard, not control flow.
* 16.3 calls P11 and P13 "borrow count clone walks". Measured shape per cluster: `ldxdw rX, [ctx+OFF]`,
  `ldxdw rY, [rX+0x8]`, `ldxdw rZ, [rY]`, `add64 rZ, 0x1`, `jeq rZ, 0x0` guard, `stxdw [rY], rZ`, with the
  second counter at `+0x10` loaded the same way (for example `0x5945..0x5957` for `ctx+0x5d8`). That is the
  strong count increment of the `AccountInfo` shared reference, that is a clone, not a borrow **[B]**.

#### 16.12.5 The body issues four external CPIs, through three monomorphised helpers [B; targets named in 16.13]

The three helpers 16.7 and 16.3 called "heap objects with an 8 byte tag" are CPI helpers. Each of them
allocates instruction data at the bump cursor `0x300000000`, stamps an 8 byte leading constant, fills a
per site argument payload, builds an `AccountMeta` array with stride `0x22`, and then invokes:

| helper | data alloc | leading constant | argument filler | invoke | error arm |
|---|---|---|---|---|---|
| `0x10de9` | `0x10deb..0x10dff`, tag written `0x10e00..0x10e02` | `0xe53e4896cbc266ea` | `0x116f7` (`0x10e09`) | `0x10f0e call 0x161ae` | `0x10f18 call 0x15a5f` |
| `0x10fb9` | same shape | `0xe8d62634bf347c57` | `0x1177d` (`0x10fd9`) | `0x110de call 0x161ae` | `0x110e8 call 0x15a5f` |
| `0x11abc` | same shape | `0x3a10af4a049f08d0` | `0x12169` (`0x11adc`) | `0x11be1 call 0x161ae` | `0x11beb call 0x15a5f` |

The metas are built at stride `0x22` (`0x10e13 mul64 r4, 0x22`), the signer seed slice is taken from the
context struct at `0x10f03..0x10f06` (`[r9+0x140]` and `[r9+0x138]`), and a result other than the
`invoke_signed` sentinel goes to the `0x15a5f` shim at `0x10f18`, which is the same sentinel compare the
`emit_cpi!` arm uses at `0x5c3e`/`0x5c41`. Caller census, whole program: `0x10de9` is called from `0x59cc` and
`0x5ca1`, `0x10fb9` from `0x5b22`, `0x11abc` from `0x5cce`. All four call sites are inside this body, so each
helper is monomorphised for its site (the `0x10de9` shape serves two).

| # | call site | helper | context struct | Ok tag read | failure |
|---|---|---|---|---|---|
| 1 | `0x59cc` (P12) | `0x10de9` | `fp-0x470`, out `fp-0x648` | `0x59cd..0x59cf` | `0x59cf jne r3, 0x2` -> return |
| 2 | `0x5b22` (P14) | `0x10fb9` | `fp-0x5b8`, out `fp-0x658` | `0x5b23..0x5b25` | `0x5b25 jne r3, 0x2` -> return |
| 3 | `0x5ca1` (P21) | `0x10de9` | `fp-0x470`, out `fp-0x678` | `0x5ca2..0x5ca4` | `0x5ca4 jne r3, 0x2` -> return |
| 4 | `0x5cce` (P21) | `0x11abc` | `fp-0x238`, out `fp-0x688` | `0x5ccf..0x5cd1` | `0x5cd1 jeq r3, 0x2` -> join |

So the CPI census of the body is **five**: calls 1 and 2 on both arms, calls 3 and 4 on the graduated arm
only, and the `emit_cpi!` inner instruction of 16.12.3. This corrects the reading of 16.3 P12/P14/P21 as
objects whose value is thrown away: each Ok tag is tested and each Err reaches the return block.

The leading constants were **[partial]** when this section was written and are closed in **16.13**. Three
preimage probes were run against the value `0xe53e4892cbc226ea` and all failed: the 129 instruction names of the four programs under
`global:`, `event:`, `account:`, `instruction:`, `state:` and the bare prefix (`scratch/d2f_disc_cpi.py`);
13776 preimages built from the 474 printable strings of the deployed program (`scratch/d2f_consts2.py`); and
a curated 60 name list (`scratch/d2f_consts.py`). That value is a transcription of the K1 slot and not the
slot's bytes: the raw `lddw` at `0x10e00` decodes to `0xe53e4896cbc266ea` (`16.13.1`), and with the slot
value the preimage is exact. The method was sound throughout, since the same code recovers
`sha256("anchor:event")[0..8]` and `sha256("event:CreateFeeSharingConfigEvent")[0..8]` exactly.

#### 16.12.6 The reconstructed body [B]

```rust
// programs/pump-fees/src/instructions/fee_sharing/create_fee_sharing_config.rs
// body 0x56c7..0x5cd2, 1548 slots; ctx = r7 = the try_accounts out image (16.8.1)
pub fn create_fee_sharing_config_impl(ctx: &mut CreateFeeSharingConfig) -> Result<()> {
    // P1  0x56c7 Ok tag 2, 0x56c8 ctx, 0x56c9/0x56ca: an already initialised config is a no-op
    if ctx.sharing_config.version != 0 {                        // 0x56c9 ldxb [ctx+0x5b]
        return Ok(());                                          // 0x56ca -> 0x5b47/0x5b48, 0x5b49 exit
    }

    // P1 flag: the bonding curve mint key (image[0x20..0x40]) is the default key
    let bc_mint_is_default =                                    // 0x56cd..0x56d8, flag at [fp-0x6e0]
        ctx.bc_image[0x20..0x40].iter().all(|b| *b == 0);

    // P2  payer key staged once, both later gates read this one key (16.9.1)
    let payer_key = ctx.payer.key();                            // 0x56de/0x56df, r6
    let payer_is_fee_authority =
        memcmp(payer_key, ctx.global[0x158], 32) == 0;          // 0x56e8..0x56ed, result parked at 0x5730

    if bc_mint_is_default {                                     // 0x56ee..0x56f0 jne -> 0x5726
        // P4  graduated coin: the AMM accounts are mandatory
        if ctx.pool.is_none() {                                 // 0x5726 ldxb [ctx+0x5bc], 0x5727 jeq 2
            return err!(FeeError::AmmAccountsRequired);         // 0x572b/0x572c, 6019
        }
        // P5  line 273: pool.base_mint == mint
        if memcmp(ctx.mint.key(), ctx+0x4e0, 32) != 0 {         // 0x5731..0x5743
            return err!(FeeError::InvalidPool);                 // box 0x5792, code 0x1778, line 0x111
        }
        // P7  line 280: pool.creator == find_program_address(["pool-authority", mint], pump)
        let (pool_authority, _) =
            Pubkey::find_program_address(&[b"pool-authority", &mint], &pump_id);   // 0x57a4..0x57b0
        if memcmp(pool_authority, ctx+0x4c0, 32) != 0 {          // 0x57bd
            return err!(FeeError::InvalidPool);                 // box 0x57f3, line 0x118
        }
        // P8  line 297: pool key == create_program_address(["pool", index, creator,
        //      base_mint, quote_mint, bump], amm)
        let pool_key = Pubkey::create_program_address(&seeds6, &amm_id)
            .map_err(|_| err!(FeeError::InvalidPool))?;         // 0x5817, err! 0x581d
        if memcmp(pool_key, ctx.pool.key(), 32) != 0 {           // 0x5844
            return err!(FeeError::InvalidPool);                 // box 0x585e, line 0x129
        }
        // P9  line 302: unless the payer is the fee authority, it must be pool.coin_creator
        if !payer_is_fee_authority {                            // 0x5a8d..0x5a90, [fp-0x700] != 0
            if memcmp(payer_key, ctx.pool_image[0xc0..0xe0], 32) != 0 {   // 0x5a9e
                return err!(FeeError::NotAuthorized);           // box 0x5ab9, line 0x12e
            }
        }
    } else {
        // P3/P6 line 307: on the non graduated arm the payer must be the fee authority
        // or the bonding curve creator
        let payer_is_bc_creator =
            memcmp(payer_key, ctx.bc_image[0x00..0x20], 32) == 0;   // 0x56f4..0x5700, 0x5703
        if !payer_is_fee_authority && !payer_is_bc_creator {
            return err!(FeeError::NotAuthorized);               // box 0x5776, line 0x133
        }
    }

    // P10 0x5862..0x58a9, the init image and its one element shareholder vector (16.10)
    ctx.sharing_config.bump = arg[0x24];                        // 0x5862..0x5864, slot 4 (16.10.2)
    ctx.sharing_config.version = 2;                             // 0x5865
    ctx.sharing_config.status = 1;                              // 0x5866
    ctx.sharing_config.mint = ctx.mint.key();                    // 0x5867..0x5870
    ctx.sharing_config.admin = ctx.bc_image[0x00..0x20];        // 0x5871..0x5878, r8 = ctx+0x150
    ctx.sharing_config.admin_revoked = false;                   // 0x5879
    ctx.sharing_config.initial_shareholders = vec![             // 0x587a..0x589b, element 0x22 bytes
        Shareholder { holder: ctx.sharing_config.admin, share_bps: 10_000 },
    ];
    serialize_sharing_config(ctx)?;                             // 0x589f..0x58a9 through the 0x989 packer

    // P11/P13 refcount increments for the accounts of the two CPIs below (16.12.4)
    cpi_1(ctx)?;                                                // 0x59c8..0x59cf, helper 0x10de9
    cpi_2(ctx)?;                                                // 0x5b1e..0x5b25, helper 0x10fb9

    // P15 0x5b26..0x5b2a
    if bc_mint_is_default {
        // P16 0x5b3e..0x5b7c: the graduated arm rewrites admin and shareholders from
        //      pool.coin_creator and re-serialises
        ctx.sharing_config.admin = ctx.pool_image[0xc0..0xe0];   // 0x5b4a..0x5b59
        ctx.sharing_config.initial_shareholders = vec![
            Shareholder { holder: ctx.sharing_config.admin, share_bps: 10_000 },  // 0x5b5a..0x5b68
        ];
        serialize_sharing_config(ctx)?;                          // 0x5b70, 0x5b71..0x5b73
        if ctx.second_option_word == 0 {                         // 0x5b74 ldxdw r9, [ctx+0x5e0]
            return err!(FeeError::AmmAccountsRequired);          // 0x5b78/0x5b79, 6019
        }
        // P20 0x5c6d..0x5c75 then P21 0x5c76..0x5cd1
        cpi_3(ctx)?;                                            // 0x5c9d..0x5ca4, helper 0x10de9
        cpi_4(ctx)?;                                            // 0x5cca..0x5cd1, helper 0x11abc
        // 0x5cd1 join into the shared tail
    }

    // tail 0x5b2b..0x5c54, entered by fall-through 0x5b2a or by the 0x5cd1 join
    let timestamp = Clock::get()?.unix_timestamp;                // 0x5b2b..0x5b2f, 0x5b7d, 0x5b7e, E+0x18
    let event = CreateFeeSharingConfigEvent {                     // 0x5b7f..0x5bcd, image at E = fp-0x470
        timestamp,
        mint: ctx.mint.key(),                                    // E+0x20
        bonding_curve: ctx.bonding_curve.key(),                  // E+0x40
        pool: ctx.pool.map(|p| p.key()),                         // E+0xa0 tag, E+0xa1 key
        sharing_config: ctx.sharing_config.key(),                // E+0x60
        admin: ctx.sharing_config.admin,                          // E+0x80
        initial_shareholders: ctx.sharing_config.initial_shareholders.clone(),  // E+0x00, 0x1c93 at 0x5bb8
        status: ctx.sharing_config.status,                        // E+0xc1
    };
    emit!(event);                                                // 0x5bd9..0x5be1, sol_log_data
    emit_cpi!(event);                                            // 0x5bee..0x5c3d, tag + invoke_signed
    Ok(())                                                       // 0x5c3e..0x5c54, 0x5b46/0x5b47
}
```

Every line above carries either an instruction address, a raise site from 16.4 or 16.5, or a section that
measured it. Field names on the accounts struct follow the interface record already grounded in 4.1 and
16.8 to 16.11. `cpi_1` to `cpi_4` are the four call sites of 16.12.5, named in **16.13**:
`pump::extend_account` at `0x59cc`, `pump::migrate_bonding_curve_creator` at `0x5b22`,
`pump_amm::extend_account` at `0x5ca1` and `pump_amm::migrate_pool_coin_creator` at `0x5cce`
**[B]**. Rendered as the reconstruction reads them:

```rust
    pump::extend_account(&ctx, ...)?;                            // 0x59cc, 5 metas
    pump::migrate_bonding_curve_creator(&ctx, ...)?;             // 0x5b22, 5 metas
    // graduated arm only
    pump_amm::extend_account(&ctx, ...)?;                        // 0x5ca1, 5 metas
    pump_amm::migrate_pool_coin_creator(&ctx, ...)?;             // 0x5cce, 4 metas
```

#### 16.12.7 What D2-f settles and what it hands on

D2-f is closed as **[B]** for the body: the gates and their operands (16.8, 16.9), the eleven initialisation
stores (16.10), the event and its two emissions (16.11), the control flow (16.12.1, 16.12.2) and the macro
pairing (16.12.3). The body has no loop, one return block, five CPI sites and one no-op early return.

One item was open at the end of this tick and is closed in **16.13**:

* **(D2-g) CLOSED [B] (§16.13)** name the four external CPIs: for each of the four call sites in
  16.12.5 the callee program comes from the program account the site stages at `[context+0x18]`, and the
  preimage of the leading constant is exact once the K1 slot is read from its raw bytes rather than from
  the transcription of 16.12.5. Result: `pump::extend_account` (`0x59cc`), `pump::migrate_bonding_curve_creator`
  (`0x5b22`), `pump_amm::extend_account` (`0x5ca1`), `pump_amm::migrate_pool_coin_creator` (`0x5cce`).

Severity: Informational
Sévérité : Informational
Severity justification: Static reconstruction of one handler body from its instructions, with no behaviour, fund or consensus effect measured.

### 16.13 The four external CPIs named: `extend_account` twice and the two creator migrations (D2-g closed) [B]

Scope of this tick: only item D2-g, the four external CPI sites of 16.12.5 and the three
monomorphised helpers behind them. Nothing in 16.8 to 16.12 is re-derived, the wrapper grounding of
4.1 is not reopened, and no retired A/B1/B2/C handler is touched. Bytes read this tick: the pinned
slice `scratch/slices/D2_create_sharing_body_0x56c7.txt`, `tools/fees_body.py` on `0x10de9`,
`0x10fb9`, `0x11abc`, `0x161ae`, `0x1ec6`, `0x116f7`, `0x1177d`, `0x12169`, `0xd95d`, the windows
`0x2376c..0x237c4` of pump and `0x1b804..0x1b83c` of pump_amm, the three interface records
`pump.json`, `pump_amm.json`, `pump_fees.json`, and the new probe scripts `scratch/d2g_match2.py`,
`scratch/d2g_imm.py`, `scratch/d2g_fillers.py`, `scratch/d2g_pid.py`, `scratch/d2g_win.py`.

#### 16.13.1 Correction to 16.12.5: the K1 bytes were transcribed wrong, which is why the probes failed [B]

The three preimage probe families of 16.12.5 (684 program instruction candidates, 13776 `.so`-string
preimages, the curated 60-name list) were all run against `0xe53e4892cbc226ea`, and that value is not
in the binary. The raw 16 bytes of the `lddw` slot are decisive (`scratch/d2g_raw.py`):

| slot | raw bytes | decoded imm | memory bytes written by the stamp |
|---|---|---|---|
| `0x10e00` | `18 01 00 00 ea 66 c2 cb  00 00 00 00 96 48 3e e5` | `0xe53e4896cbc266ea` (`-1928023777967184150`) | `ea 66 c2 cb 96 48 3e e5` |
| `0x10fd0` | `18 01 00 00 57 7c 34 bf  00 00 00 00 34 26 d6 e8` | `0xe8d62634bf347c57` (`-1669104603906147241`) | `57 7c 34 bf 34 26 d6 e8` |
| `0x11ad3` | `18 01 00 00 d0 08 9f 04  00 00 00 00 4a af 10 3a` | `0x3a10af4a049f08d0` (`-14262707287442388784`) | `d0 08 9f 04 4a af 10 3a` |

16.12.5 carries `ea 26 c2 cb 92 48 3e e5` for the first one (`0xe53e4892cbc226ea`), two nibbles away
from the slot. K2 and K3 as printed in 16.12.5 match their slots exactly, so only K1 was wrong, and
only K1 failed all three probe families. The corrected value resolves on the first hash comparison
(`scratch/d2g_match2.py`).

#### 16.13.2 Method: the program id of a CPI is the 32 bytes at `[context+0x18]` [B]

The three helpers build the same `SolInstruction` image at `fp-0x80` and hand it to the invoke
wrapper `0x161ae`:

* `0x10de9` (`0x10e08` saves the context, `0x10e09` calls the filler), `0x10fb9` (`0x10fd8`,
  `0x10fd9` -> `0x1177d`), `0x11abc` (`0x11adb`, `0x11adc` -> `0x12169`);
* the program id is copied as four words from the pointer held at `[context+0x18]` into
  `fp-0x50..fp-0x38`, which is the Instruction field at `+0x30`: `0x10e1d ldxdw r6, [r10 -0xc0]`,
  `0x10e1e ldxdw r3, [r6 +0x18]`, `0x10e1f..0x10e22` the four loads, `0x10e23..0x10e26` the four
  stores; the same shape in `0x11abc` at `0x11af1..0x11af9`;
* the wrapper reads that field: `0x161cf ldxdw r2, [r7 +0x30]`, while the account metas come from
  `+0x08`/`+0x10` (`0x161b2 ldxdw r1, [r2 +0x10]`, `0x161b9 ldxdw r6, [r2 +0x8]`), and the two
  `stdw` at `0x10e2b`/`0x10e2c` place the 8 byte data length and the meta capacity.

So the callee program of each site is whatever 32 byte key the site stages at `[context+0x18]`, and
the four sites stage exactly two distinct accounts.

#### 16.13.3 The four rows [B]

| # | site | helper | filler | leading constant | preimage | callee program | metas |
|---:|---|---|---|---|---|---|---:|
| 1 | `0x59cc` (P12) | `0x10de9` | `0x116f7` (`0x10e09`) | `0xe53e4896cbc266ea` (`0x10e00`) | `sha256("global:extend_account")[0..8]` = `ea66c2cb96483ee5` | pump | 5 |
| 2 | `0x5b22` (P14) | `0x10fb9` | `0x1177d` (`0x10fd9`) | `0xe8d62634bf347c57` (`0x10fd0`) | `sha256("global:migrate_bonding_curve_creator")[0..8]` = `577c34bf3426d6e8` | pump | 5 |
| 3 | `0x5ca1` (P21) | `0x10de9` | `0x116f7` (`0x10e09`) | `0xe53e4896cbc266ea` (`0x10e00`) | `sha256("global:extend_account")[0..8]` | pump AMM | 5 |
| 4 | `0x5cce` (P21) | `0x11abc` | `0x12169` (`0x11adc`) | `0x3a10af4a049f08d0` (`0x11ad3`) | `sha256("global:migrate_pool_coin_creator")[0..8]` = `d0089f044aaf103a` | pump AMM | 4 |

Two sites share `0x10de9` and therefore share the same leading constant, so the instruction is the
same on both and only the program account separates them.

#### 16.13.4 Which program account each site stages [B]

The four `[context+0x18]` values come from two fields of the accounts struct, `ctx+0x5d8` and
`ctx+0x5e0`:

| # | site | context base | `+0x18` slot | staged from | account field |
|---:|---|---|---|---|---|
| 1 | `0x59cc` | `fp-0x470` (`0x59cb`) | `fp-0x458` (`0x59c2`) | `[fp-0x700]` (`0x59c1`) | key of `[ctx+0x5d8]` |
| 2 | `0x5b22` | `fp-0x5b8` (`0x5b21`) | `fp-0x5a0` (`0x5b18`) | `[fp-0x700]` (`0x5b17`) | key of `[ctx+0x5d8]` |
| 3 | `0x5ca1` | `fp-0x470` (`0x5ca0`) | `fp-0x458` | AccountInfo clone out of `r9` (`0x5c7b`) | key of `[ctx+0x5e0]` |
| 4 | `0x5cce` | `fp-0x238` (`0x5ccd`) | `fp-0x220` (`0x5ca6`) | AccountInfo clone out of `r9` (`0x5ca8`) | key of `[ctx+0x5e0]` |

Traced per site:

* **site 1**: `0x58aa ldxdw r2, [ctx+0x5d8]`, `0x58b1 ldxdw r4, [r2 +0x0]`, `0x58be
  stxdw [fp-0x700], r4`. `[r2+0x0]` is the key pointer of the 48 byte `AccountInfo` record, since
  the same record's `+0x08` and `+0x10` are the two reference blocks the clone walk increments
  (`0x58ab..0x58b2`), `+0x18` its owner, `+0x20` its rent epoch and `+0x28..0x2a` its three flags
  (the staging at `0x58c6..0x58ce`).
* **site 2**: the same field again, `0x59d0 ldxdw r2, [ctx+0x5d8]`, `0x59d7 ldxdw r4, [r2 +0x0]`,
  `0x59e4 stxdw [fp-0x700], r4`, read back into the context at `0x5b17`/`0x5b18`. Sites 1 and 2
  therefore invoke the same program, and site 2's own discriminator names that program: pump.
* **sites 3 and 4**: `0x5b74 ldxdw r9, [ctx+0x5e0]` holds the second program account for the whole
  graduated arm. Site 3 clones it with the `AccountInfo` clone helper `0x1ec6` at `0x5c7b` into
  `fp-0x458`, and the clone's `+0x00` is the key pointer (`0x1ec6` bumps the two reference blocks at
  `[r2+8]` and `[r2+0x10]` and copies `[r2+0]` as the first word, aborting on either overflow
  against `0x1ecf`). Site 4 clones the same field at `0x5ca8` into `fp-0x220`. The two P21 CPIs
  therefore invoke the same program, and site 4's discriminator names it: the pump AMM program.

The null test on that field sits one branch earlier: `0x5b74 ldxdw r9, [ctx+0x5e0]`,
`0x5b75 jne r9, 0x0, +0xf7` -> P20 at `0x5c6d`, otherwise `err!(FeeError::AmmAccountsRequired)` at
`0x5b78`/`0x5b79` (6019). A missing AMM program account is exactly the case that raises 6019 there.

#### 16.13.5 Independent corroboration inside the callee binaries [B]

The same 8 byte values are entries of the pump and pump_amm dispatcher compare ladders, at one
`lddw r4, <imm>` plus one `jeq r3, r4, <off>` each (`scratch/d2g_imm.py`, `scratch/d2g_win.py`):

| program | constant | `lddw` | `jeq` | handler |
|---|---|---:|---:|---:|
| pump | `-0x1ac1b769343d9916` (K1) | `0x23777` | `0x23779 +0x22d` | `0x239a7` |
| pump | `-0x1729d9cb40cb83a9` (K2) | `0x237b3` | `0x237b5 +0x2c3` | `0x23a79` |
| pump_amm | `-0x1ac1b769343d9916` (K1) | `0x1b80f` | `0x1b811 +0x1bd` | `0x1b9cf` |
| pump_amm | `0x3a10af4a049f08d0` (K3) | `0x1b82f` | `0x1b831 +0x20d` | `0x1ba3f` |

mayhem carries K1 once, at `0xfb27` (function `0xfb06`), so `extend_account` exists in three of the
four programs and the constant alone does not name a callee. K1 does not occur in either binary under
the mistranscribed value, and the preimage is exact under the corrected one: the four probes are now
consistent, and the earlier negative result was a transcription artefact rather than a method limit.

#### 16.13.6 Account meta census, measured on the three fillers [B]

Each filler writes the `AccountMeta` array at stride `0x22` into the bump buffer: the 32 byte key is
copied from a pubkey pointer taken out of the arguments block (`r7+0x00`, `r7+0x30`, `r7+0x60`, ...)
and a two byte `sth` writes `is_signer`/`is_writable` at meta `+0x20` (`scratch/d2g_fillers.py`):

| filler | metas | key sources | `sth` flags (signer, writable) | count store |
|---|---:|---|---|---:|
| `0x116f7` | 5 | `+0x00`, `+0x30`, `+0x60`, `+0x90`, `+0xc0` | (0,1) `0x11711`, (1,1) `0x1172b`, (0,0) `0x11744`, (0,0) `0x1175d`, (0,0) `0x11775` | `0x1177b` = 5 |
| `0x1177d` | 5 | `+0x00`, `+0x30`, `+0x60`, `+0x90`, `+0xc0` | (0,0) `0x11797`, (0,1) `0x117b1`, (0,0) `0x117ca`, (0,0) `0x117e3`, (0,0) `0x117fb` | `0x11801` = 5 |
| `0x12169` | 4 | `+0x00`, `+0x30`, `+0x60`, `+0x90` | (0,1) `0x12183`, (0,0) `0x1219d`, (0,0) `0x121b6`, (0,0) `0x121ce` | `0x121d4` = 4 |

The three flag vectors reproduce the declared account lists of the three named instructions exactly,
which is an independent confirmation of the identity that does not use the discriminator:

| instruction (interface record) | declared accounts | declared flags | measured |
|---|---|---|---|
| pump `extend_account` | `account` (w), `user` (s, w), `system_program`, `event_authority`, `program` | (0,1) (1,1) (0,0) (0,0) (0,0) | `0x116f7`, identical |
| pump_amm `extend_account` | same five accounts | (0,1) (1,1) (0,0) (0,0) (0,0) | `0x116f7`, identical |
| pump `migrate_bonding_curve_creator` | `mint`, `bonding_curve` (w), `sharing_config`, `event_authority`, `program` | (0,0) (0,1) (0,0) (0,0) (0,0) | `0x1177d`, identical |
| pump_amm `migrate_pool_coin_creator` | `pool` (w), `sharing_config`, `event_authority`, `program` | (0,1) (0,0) (0,0) (0,0) | `0x12169`, identical |

`pump` and `pump_amm` declare `extend_account` with the identical five account vector, so the meta
shape separates sites 1 and 3 from sites 2 and 4 but not 1 from 3. What separates 1 from 3 is the
program account of 16.13.4: `ctx+0x5d8` for the pump pair, `ctx+0x5e0` for the AMM pair.

#### 16.13.7 What the bytes do not settle, and the status of D2 [B]

Three limits are stated once, so this item does not stay open on them:

* **Account names per meta are tagged [R], not [B].** The counts, order and signer/writable flags of
  the ten metas are measured (16.13.6), and the four program-account fields are measured (16.13.4),
  but the map from `ctx+OFF` to the declared account name for the whole 0x5e8 byte accounts struct
  is not built for this handler. Names in the tables above come from the interface records; only
  `payer` (`ctx+0x5c8`, 16.9.1), `global` (`ctx+0x148`/`ctx+0x150`, 16.9) and `pool`
  (`ctx+0x4b8`/`ctx+0x4c0`, 16.8.1) are independently pinned today. For site 1 the meta keys trace
  as `meta0 <- ctx+0x148` (`0x58bf`/`0x58d0`), `meta2 <- ctx+0x5d0` (`0x5900`/`0x5913`),
  `meta3 <- ctx+0x118` (`0x5929`/`0x592a`), `meta4 <- ctx+0x5d8` (`0x5945`/`0x5956`), which is
  consistent with the declared order and does not prove it.
* **The two program accounts carry no constant check.** try_accounts `0xd95d` never loads
  `0xc4ecd` (pump id) or `0xc4f3c` (pump AMM id); those constants appear only at `0x500a`, `0x56c7`
  and `0x7113` in this program (`scratch/d2g_pid.py`). So `ctx+0x5d8` and `ctx+0x5e0` are
  caller-supplied program accounts with no address constraint of their own, which is exactly why the
  binding to pump and to pump_amm has to be established through the discriminator of the sibling
  migration CPI (16.13.4) rather than by a key comparison.
* **The `Option` wrapper of the AMM program field is only measured as a null test** (`0x5b74`,
  `0x5b75`); the tag byte that a declared `Option` would carry is not measured at that offset.

Every address cited in 16.13.1 to 16.13.6 is asserted mechanically by `scratch/d2g_verify.py`: **48 of 48
citations match** (three `lddw` immediates, seven call targets, the context and staging slots, the three
meta counts, four flag vectors and the five constants in the callee binaries).

**(D2-g) closed [B].** All four external CPIs of `create_fee_sharing_config` now have a callee
program, a leading constant with an exact preimage, a measured meta count and a measured flag
vector. 4.1 and 16.12.5 flip to **[B]**. The only residual named above is the struct map from
`ctx+OFF` to declared account name, carried as a refinement of the accounts frame rather than as an
open item of this body.

Severity: Informational
Sévérité : Informational
Severity justification: Static reconstruction of four cross-program invocation sites from their instruction bytes, with no behaviour, fund or consensus effect measured.

## P2-a. The `ctx` to account map of `create_fee_sharing_config`

Scope: the accounts struct written by `try_accounts` `0xd95d` (1321 insns) and the `ctx` buffer the
wrapper `0x13810` builds from it, one row per declared `Accounts` field. The body `0x56c7`, the
`SharingConfig` initialisation and the gates are not re-derived here; every one of them is cited by
section and used as given. Bytes read this tick: `tools/fees_body.py 0xd95d` (the whole body, 1321
rows), the readers `0x2432` (68 insns), `0x21c6` (22), `0x22fd` (23), `0x50` (23), `0x235b` (69),
`0x226f` (23), `0x23e9` (68), `0x353` (28), `0x541` (43), `0x56c` (36), `0x4ff` (35), `0xdebe` (207),
the wrapper `0x13810` (168) and `tools/fees_ctx_walk.py 0xd95d`. Every address this section cites is
re-checked mechanically by `scratch/p2a_verify.py`, which re-disassembles each row through
`tools/sbftool.py dis` and re-runs the ctx walk: 153 instruction assertions and 28 ctx walk rows,
PASS.

### P2-a.1 Two sizes, both measured: the struct is `0x5e8`, the bulk leg is `0x5d0`

The pinned card and section 16 disagree on one number and both are right, because they measure two
different objects. Measured on this tick:

| what | measurement | cite |
|---|---|---|
| the `try_accounts` out struct | base `fp-0x5e8`, 0x5e8 bytes; the last write of the body is the 8 byte store at `+0x5e0`, so the struct ends at `+0x5e7` | `0x13822 add64 r1, -0x5e8` passes the buffer, `0x13827 call 0xd95d`, `0xde81 stxdw [r6 +0x5e0], r3` |
| the body `ctx` buffer | base `fp-0xbd0`, also 0x5e8 bytes: it runs from `fp-0xbd0` up to `fp-0x5e8`, i.e. the byte after the struct | `0x13841 stxdw [r10 -0x5e0], r1` stores `fp-0xbd0` at struct `+0x08`, and the body takes its base from that word: `0x56c8 ldxdw r7, [r2 +0x8]` |
| the bulk leg | 0x5d0 bytes, source `fp-0x5d0` (struct `+0x18`), destination `fp-0xbb8` (ctx `+0x18`) | `0x13831 mov64 r2, r10`, `0x13831 add64 r2, -0x5d0`, `0x13832 mov64 r3, 0x5d0`, `0x13833 call 0x184d9` (the 4 insn memcpy) |
| the scalar leg | the 0x18 bytes the bulk copy does not carry: `ctx+0x10`, `ctx+0x8`, `ctx+0x0` stored one word each from `r9`, `r8`, `r6` | `0x13834 stxdw [r10 -0xbc0], r9`, `0x13835 stxdw [r10 -0xbc8], r8`, `0x13836 stxdw [r10 -0xbd0], r6` |

So the map below is stated against the struct that `try_accounts` writes, with the `ctx` base
`fp-0xbd0` that the body reads at `0x56c8`: the two buffers hold the same bytes, `0x18` scalar plus
`0x5d0` bulk, and the `0x5d0` of 16.10 is the bulk leg, not the size of the struct. The statement of
16.10 that the body context is a `0x5d0` byte block is corrected here to `0x5e8` bytes filled in two
legs.

The struct is not a flat record of pointers. Three of the thirteen fields own a block whose internal
composition is only partly read here, and one of them (the `event_authority` field) is an
`AccountInfo` copied by value. The region table in P2-a.3 states exactly how far each block was
measured.

### P2-a.2 The thirteen accounts, in the order the cursor consumes them

The accounts arrive as one slice, and `try_accounts` walks it with a monotonic cursor: `0xd960
ldxdw r1, [r9 +0x8]` is the remaining count, `0xd966` picks the word at `[r9 +0x0]` and `0xd968
add64 r2, 0x30` advances it by 0x30, the size of one `AccountInfo`. Every reader takes the account at
the cursor as of its own entry, so the row order below is the deployed field order, and each name is
the string the failure arm of that same step builds with the boxed error helper `0x2b1`, at the row
cited. All thirteen names are carried by the deployed bytes; the map is name complete without the
interface file.

| # | field (name arm) | name len | reader row and helper | what the reader tests, cited | ctx offsets the field owns |
|---:|---|---:|---|---|---|
| 0 | `event_authority` `0xc4a24` `0xd9b4` | 0xf | no reader call: the raw `AccountInfo` copy of account 0 | the key words are staged from the record at `0xd966` to `0xd987` and the three flag bytes read at `0xd97e` to `0xd983`; the derived `__event_authority` key is compared with this account key at `0xdc22` (32 byte memcmp) and the mismatch arm is the `event_authority` box at `0xdcd9` (`0x1601e` with `0x7d6`, the `ConstraintSeeds` code) | `0xe8` key, `0xf0`, `0xf8`, `0x100`, `0x108`, `0x110`, `0x111`, `0x112` |
| 1 | `program` `0xc4a33` `0xd9c2` | 7 | `0xd98b call 0x2432` (68) | key compared with the 32 bytes at `0xc4ead`, this program id, at `0x2444`/`0x2447`, then the executable flag `[r8 +0x2a]` tested at `0x244b`, then the derivation helper `0x15a91` over the key and the 32 byte constant at `0x2415` to `0x2420` | `0x5c0` (`0xd990`) |
| 2 | `payer` `0xc4bca` `0xd9cb` | 5 | `0xd994 call 0x21c6` (22) | plain `AccountInfo` copy through `0x15970` at `0x21da`, no key test; the record is marked writable, tested at `0xdc26`/`0xdc27` with `[+0x29]` and the mismatch box is the `payer` name at `0xdd00` | `0x5c8` (`0xd999`) |
| 3 | `global` `0xc4b17` `0xd9a5` | 6 | `0xd99d call 0x22fd` (23) then the 119 insn decoder `0x111f` at `0x2312` | the decoder fills the pump `global` image; the placeholder tag byte it writes at out `+0x2e3` is tested at `0xd9a0` to `0xd9a2` | `0x1a0`, `0x1a8`, `0x1b0` to `0x482` (0x2d3 bytes), `0x483`, `0x484` |
| 4 | `mint` `0xc3eac` `0xd9fc` | 4 | `0xd9f4 call 0x50` (23) then `0x419` at `0x65` | cursor read and `try_from` of a plain account; the reader's out words are the source of the 0x80 byte block in P2-a.3, and the `AccountInfo` pointer the body dereferences at `ctx+0xc0` is the word at block `+0x58` | `0x68` to `0xe7` (0x80 byte block, see P2-a.3) |
| 5 | `system_program` `0xc4a3a` `0xda4f` | 0xe | `0xda26 call 0x235b` (69) | key compared with the 32 zero bytes staged at `0x236b` to `0x236e` and compared at `0x2374`; the zero key is the system program id, and the not-ok arm raises through `0x15a91` | `0x5d0` via `0xde47 ldxdw r9, [r10 -0x318]` and `0xde84 stxdw [r6 +0x5d0], r9` |
| 6 | `bonding_curve` `0xc4d7c` `0xda38` | 0xd | `0xda30 call 0x226f` (23) then the 121 insn decoder `0xdbb` at `0x2284` | cursor read plus the pump bonding curve decoder; its status byte is tested at `0xda33`/`0xda34` and the tail scalars are staged at `0xda56` to `0xda62` | `0x148`, `0x150` to `0x198` (0x49 bytes), `0x199`, `0x19a`, `0x19e` |
| 7 | `pump_program` `0xc4dd4` `0xda80` | 0xc | `0xda66 call 0x23e9` (68) | key compared with the 32 bytes at `0xc4eed` at `0x23fb`/`0x23fe`, same shape as the reader of field 1, with the executable test and the `0x15a91` derivation after it | `0x5d8` (`0xda6b`) |
| 8 | `pump_event_authority` `0xc4dc0` `0xda77` | 0x14 | `0xda6f call 0x353` (28) | cursor read with the two borrow counters of the record, no key test; the word the arm leaves in the out window at `+0x2a` is tested at `0xda73` and, when it is not the placeholder tag, stored | `0x142` (`0xda87`), one tag byte |
| 9 | `pool` `0xc3e0c` `0xdaa2` | 4 | `0xda9a call 0x541` (43) | `Option<Account<Pool>>`: key compared with the zero key at `0x54d` to `0x552`, the absent arm writes tag 2 at `0x564` and the present arm writes tag 3 at `0x55e` (this is the polarity withdrawn in 16.9.6), then the `Pool` decoder `0x2314` | `0x4b8`, `0x4c0` to `0x5bb` (0xfc bytes), `0x5bc`, `0x5bd`, `0x5bf` |
| 10 | `pump_amm_program` `0xc41b8` `0xdadb` | 0x10 | `0xdaba call 0x56c` (36) | key compared with the zero key at `0x57f`; the zero arm writes tag 2 at `0x58d` and the real account goes through `0x247b` | `0x5e0` (`0xdabf`) |
| 11 | `pump_amm_event_authority` `0xc4da8` `0xdacc` | 0x18 | `0xdac4 call 0x4ff` (35) | the missing account arm writes tag 3 at `0x50b`; the key words and flags of the record are staged into `fp-0x1a0` to `fp-0x178` at `0xdae9` to `0xdaf8`, and the tail copies that block | `0x488` to `0x4b7` (0x30 bytes, `0xde5e` to `0xde61`) |
| 12 | `sharing_config` `0xc4c1c` `0xdb57` | 0xe | `0xdbaa call 0xdebe` (207), whose own name arm is the same string at `0xded9` | PDA seeds `sharing-config` and the mint key: `0x16f53` at `0xdb2f` then a 32 byte memcmp at `0xdb4b`, mismatch box at `0xdb57` with the `ConstraintSeeds` code `0x7d6`; then the writable test `0xdbc2` on `[+0x29]` with the same name at `0xdc8a` | `0x00`, `0x08`, `0x10`, `0x18` to `0x5f`, `0x60` |

Two rows of the table deserve a word because they contradict a reading already in this document.

* Field 5 (`system_program`) sits at `ctx+0x5d0` and is read with the all-zero program id test, so the
  key the reader of field 1 accepts at `0xc4ead` and the zero key of this reader are two different
  program ids. That is consistent with the interface record, which gives `program` as this program
  and `system_program` as `11111111111111111111111111111111`.
* Field 12 (`sharing_config`) is consumed last, after `pump_amm_event_authority`. The cursor is
  monotonic, so the deployed slice order puts `sharing_config` at index 12, not at index 5.

### P2-a.3 The `ctx` region map, with the writer row of each region

`ctx` base is `fp-0xbd0` (P2-a.1). Every row below is one store or one memcpy of the tail block
`0xde3a` to `0xdeae`, or of the two block copies at `0xde3d` and `0xde5d`.

| ctx range | size | writer rows | source | field | tag |
|---|---:|---|---|---|---|
| `0x00` to `0x17` | 0x18 | `0xdeab`, `0xdea9`, `0xdea7` | out words 0, 8, 0x10 of the `0xdebe` read, staged at `0xdbb2`, `0xdbae`, `0xdbac` | `sharing_config`, the `Vec<Shareholder>` head of the 3.1 ladder | [B] |
| `0x18` to `0x5f` | 0x48 | `0xde46` memcpy from `fp-0x120`, which `0xdbbf` fills from `fp-0x948` | out bytes 0x18 to 0x60 of the `0xdebe` read | `sharing_config`, the rest of the 3.1 image: `mint`, `admin`, `admin_revoked`, `bump`, `version`, `status` | [B] for the extent, [B] for the two fills; the field by field assignment is 16.10.1 |
| `0x60` to `0x67` | 8 | `0xdea5` | `0xdbc1 stxdw [r10 -0xd28], r1` where `r1` came from `fp-0x900` | `sharing_config`, the `AccountInfo` pointer (the event field of 16.11.2) | [B] |
| `0x68` to `0xe7` | 0x80 | `0xde3d` to `0xde40` memcpy from `fp-0x3a0` | assembled at `0xda0e` to `0xda1a`: word `+0x10` from out `+0x10` (`0xda0e`, `0xda15`), word `+0x08` from out `+0x08` (`0xda17`), word `+0x04` from out `+0x04` (`0xda19`), `u32 +0x00` from out `+0x00` (`0xda1a`), and 0x68 bytes `+0x18` from out `+0x18` (`0xda0f` to `0xda14`) | `mint` | [B] for the extent, the writer and the `AccountInfo` word at `+0x58` (`ctx+0xc0`, the pointer 16.8.2 dereferences); the internal reading of the 0x68 byte tail is open |
| `0xe8` to `0x112` | 0x2b | `0xdea3`, `0xdea1`, `0xde9f`, `0xde9d`, `0xde9b`, `0xde75`, `0xde73`, `0xde71` | the raw record of account 0 staged at `0xd971` (key) and `0xd987`/`0xd985`/`0xd983`/`0xd981`/`0xd97f` (owner, rent epoch, executable, writable, signer) | `event_authority`, as one `AccountInfo` by value: key `+0x00`, `+0x08`, `+0x10`, owner `+0x18`, rent epoch `+0x20`, executable `+0x28`, writable `+0x29`, signer `+0x2a` | [B] |
| `0x114` to `0x147` | 0x34 | `0xde99`, `0xde97`, `0xde95`, `0xde93`, plus the staged scalars `0xde7d` and the two `0xda8b` to `0xda93` fills | `0xda87` to `0xda95` read the out window of the step 8 read: out `+0x00`, `+0x08`, `+0x10`, `+0x18`, `+0x20`, `+0x28`, `+0x2b`, `+0x2f` | the header of the step 8 record plus the `bonding_curve` head; the split between the two is not measured | [B] (closed in P2-f) |
| `0x148` to `0x19f` | 0x58 | `0xde93`, `0xde91`, `0xde6d`, `0xde6c`, `0xdead`, `0xdeac` | out `+0x00` and `+0x08` of the `0x226f` read, the 0x41 byte image copy, the status byte and the two tail scalars | `bonding_curve`: `AccountInfo` at `0x148`, image `0x150` to `0x198`, status `0x199` | [B], the field map inside the image is 16.9.3 |
| `0x1a0` to `0x487` | 0x2e8 | `0xde8f`, `0xde8d`, `0xde67` memcpy of 0x2d3 bytes, `0xde7b`, `0xde7d` | out words of the `0x22fd` read and the 0x2d3 byte image | `global`: header at `0x1a0`, image `0x1b0` to `0x482`, status `0x483`, one `u32` at `0x484` | [B] |
| `0x488` to `0x4b7` | 0x30 | `0xde5d` to `0xde61` memcpy from `fp-0x1a8` | staged at `0xdae9` to `0xdaf8`, after the `0x4ff` read and before any other reader runs | `pump_amm_event_authority`, one record by value | [B] for the block, [B] (closed in P2-g) for the name link (positional, no name string on the copy) |
| `0x4b8` to `0x5bf` | 0x108 | `0xde8b`, `0xde89`, `0xde57` memcpy of 0xf4 bytes, `0xde7f`, `0xde59`, `0xde5b` | out `+0x00`, `+0x08`, the image copy, the status byte and two tail scalars of the `0x541` read | `pool`: `AccountInfo` at `0x4b8`, image `0x4c0` to `0x5bb`, status `0x5bc` | [B], the field map inside the image is 16.8.1 |
| `0x5c0` | 8 | `0xde87` | `0xd990` | `program` | [B] |
| `0x5c8` | 8 | `0xde85` | `0xd999` | `payer` | [B] |
| `0x5d0` | 8 | `0xde84` | `0xde47`, from `0xda2c` | `system_program` | [B] |
| `0x5d8` | 8 | `0xde83` | `0xda6b` | `pump_program` | [B] |
| `0x5e0` | 8 | `0xde81` | `0xdabf` | `pump_amm_program` | [B] |

The five words from `0x5c0` to `0x5e7` are the five program and account handles of the struct tail,
in consumption order 1, 2, 5, 7, 10. They are also the reason the struct ends at `0x5e8`: the last
of them is an 8 byte store at `0xde81`.

### P2-a.4 The interface candidate order against the measured order

The reference reconstruction tree (lalalune/pumpfun-source, MIT) carries an interface candidate for
this instruction with thirteen account entries in the order `event_authority`, `program`, `payer`,
`global`, `mint`, `sharing_config`, `system_program`, `bonding_curve`, `pump_program`,
`pump_event_authority`, `pool`, `pump_amm_program`, `pump_amm_event_authority`. The deployed cursor
order is the column order of P2-a.2, which differs in two places and agrees everywhere else: the
deployed struct reads `system_program` at index 5 and `sharing_config` at index 12, while the
candidate puts `sharing_config` at index 5 and `system_program` at index 6. The name set is identical
in both, thirteen names, so no name is at stake; the order is, and a caller that fills the accounts
in the candidate order gives this instruction a `sharing_config` where it expects `system_program`.
The measured order is the one this document uses.

### P2-a.5 What this closes

* Item P2-a, the `ctx` to account map: closed for all thirteen fields, each with its reader
  row, its name row and its `ctx` offsets, and for the two sizes of the struct, which are now both
  measured and attributed (`0x5e8` struct, `0x5d0` bulk leg plus `0x18` scalar leg).
* The partial marker of 16.7 on the question "which struct field each of those `ctx` offsets is" is
  closed by this map and its token is flipped to `[B]`.
* The `[R]` tags that this map turns into `[B]`: the account names `pool` (16.9.4), `bonding_curve`
  and `global` (16.9.3) are now carried by the deployed name strings at `0xdaa2`, `0xda38` and
  `0xd9a5`, not only by the interface file. The names of another program's layout that 16.9.3 and
  16.9.4 read inside those images (the pump bonding curve `creator` and mint, the `pump_amm`
  `coin_creator`) stay `[R]`: they are names of a foreign borsh order and no string of this program
  carries them.

What stays open, carried to the next tick and recorded in the ledger:

1. The internal reading of the 0x68 byte tail at `ctx+0x80` to `0xe7` of the `mint` block, whose
   only measured consumer is the `AccountInfo` pointer at `ctx+0xc0` (16.8.2). The bytes cannot name
   it, so the row is [B] (closed in P2-h) with the extent and writer pinned.
2. The split of `ctx+0x114` to `0x147` between the record header of the `pump_event_authority` read
   and the head of the `bonding_curve` field, both fed from the same shared out window.
3. The name link of `ctx+0x488` to `0x4b7`: the block is assembled between the `0x4ff` read and every
   other reader, which fixes the account by position, and no name string is attached to that copy.

Severity: Informational
Sévérité : Informational
Severity justification: A static reconstruction of one accounts struct, its two stack buffers and its thirteen name strings, with no execution; no behaviour, fund, admission or consensus effect is measured.

## P1-a. The 0x73 gate of 0x250d: the account at each call row, and the correction of 3.1

Scope of this tick: the loader `0x250d` only, its two call rows, the accounts-struct slot each
one hands it, and the bullet of 3.1 that carries the last open mark of that section. The
behavior of the two bodies around the call (the 6031 and 6034 raises) is measured in 7.2.1,
7.3.1 and 7.4.2 and is not re-walked here.

Tooling used: `tools/sbftool.py`, `tools/fees_prog.py`, `tools/fees_body.py`,
`tools/fees_ctx_walk.py`, `tools/d2_va_read.py`, `tools/fees_b58.py`, and the scratch passes
`scratch/p1a_dis.py`, `scratch/p1a_slot.py`, `scratch/p1a_names.py`, `scratch/p1a_verify.py`
(the last one asserts all 75 addresses cited below and the caller census, and it exits 0).
Measures taken from the lalalune/pumpfun-source tree (MIT) and from the account layout tables
it carries.

### P1-a.1 The loader, instruction by instruction

| # | insn | what the bytes do | tag |
|---:|---|---|---|
| 1 | `0x250d`, `0x250e`, `0x250f` | `r7 = r2` (the account record), `r6 = r1` (the out block), `r1 = r7` | **[B]** |
| 2 | `0x2510` | `call 0x1652f`: the data-length accessor, `[acct+0x10]` then `[rc+0x20]` (`0x1652f`, `0x16534`) | **[B]** |
| 3 | `0x2511` | `jlt r0, 0x73, +0xf` to `0x2521`: a record whose data is shorter than `0x73` bytes answers through the default arm | **[B]** |
| 4 | `0x2521`, `0x2522`, `0x2523` | the default arm: `stdw [out+0x0], 0x2` (tag 2, the `Ok` discriminant) and `stb [out+0x8], 0x1` (the answer flag is 1), then `ja +0x24` | **[B]** |
| 5 | `0x2512`, `0x2513`, `0x251b` | `r7 = [r7+0x10]` (the data cell), `r8 = [rc+0x10]` (the borrow count, tested at `0x2516`), `r2 = [rc+0x20]` (the length again) | **[B]** |
| 6 | `0x251c`, `0x251d` to `0x2520` | `jgt r2, 0x72, +0x7` to `0x2524`; the fall-through is the slice bounds panic: `mov64 r1, 0x73`, `lddw r3, 0xc8a50`, `call 0x17eb1` | **[B]** |
| 7 | `0x2524` | `r1 = [rc+0x18]`, the data bytes | **[B]** |
| 8 | `0x2525` to `0x2533` | seven unaligned loads and stores that cover exactly `[0x53, 0x73)`, see the table below | **[B]** |
| 9 | `0x253f` | `call 0x184e6` (`sol_memcmp_`) of the 32 staged bytes against the zeroed buffer at `fp-0x40..fp-0x20`, `r3 = 0x20` | **[B]** |
| 10 | after `0x253f` | the flag at `out+0x8` is 1 when the 32 bytes are all zero, 0 otherwise; the loader writes nothing into the account | **[B]** |

The 32 bytes of the slice, one load each:

| data window | load | width |
|---|---|---:|
| `0x53..0x57` | `0x252a ldxw r4, [r1+0x53]` | 4 |
| `0x57..0x59` | `0x252c ldxh r4, [r1+0x57]` | 2 |
| `0x59..0x61` | `0x2525 ldxdw r2, [r1+0x59]` | 8 |
| `0x61` | `0x2526 ldxb r3, [r1+0x61]` | 1 |
| `0x62..0x6a` | `0x252e ldxdw r4, [r1+0x62]` | 8 |
| `0x6a..0x72` | `0x2530 ldxdw r4, [r1+0x6a]` | 8 |
| `0x72` | `0x2532 ldxb r1, [r1+0x72]` | 1 |

4 + 2 + 8 + 1 + 8 + 8 + 1 = 32, which is why the gate is `0x73` and not `0x72`: the last byte
of the window sits at `0x72`, so the shortest record that can be read is `0x73` bytes. The
second length test at `0x251c` is the slice assertion the compiler emits for that same window;
it can never fire on the path that reaches it, because `0x2511` has already sent every shorter
record to the default arm. **[B]**

The loader is a pure reader. Over its 60 instructions the only stores are the two out words at
`0x2521` and `0x2522` and the staging stores into its own frame at `0x2527` to `0x2534`; the
borrow count is incremented and released through the two `RefCell` cells it clones at `0x2512`
to `0x251a`, exactly the `try_borrow_data` shape 7.4.2 records. No `SharingConfig` record is
touched anywhere in the loader. **[B]**

### P1-a.2 Caller census

The whole image was scanned for `call` rows whose target is `0x250d`. Exactly two rows exist:

| # | call row | body |
|---:|---|---|
| 1 | `0x5e9a` | the `update_fee_shares` body `0x5e6f` |
| 2 | `0x6a39` | the `update_fee_shares_v2` body `0x673a` |

`scratch/p1a_verify.py` recomputes that census from the instruction stream and fails if a third
row appears. Both rows are listed in 7.2.1 item 2 and 7.3.1 item 8 as the quote-mint answer; the
two sections below add the operand chain each one uses. **[B]**

### P1-a.3 The v1 call row: accounts `+0x288` is `bonding_curve`

The record handed to the loader is built on the body's own frame from the word at accounts
`+0x288`:

| # | insn | what the bytes do | tag |
|---:|---|---|---|
| 1 | `0x5e70` | `r4 = [r2+0x8]`, the accounts struct of the `Context` | **[B]** |
| 2 | `0x5e72` | `r6 = [r4+0x288]`, the account record at struct offset `0x288` | **[B]** |
| 3 | `0x5e73`, `0x5e7d` | `r8 = [r6+0x8]` and `r4 = [r6+0x10]`, the two `Rc` cells; the counters are raised at `0x5e74` to `0x5e78` and `0x5e7e` to `0x5e87` | **[B]** |
| 4 | `0x5e8b` to `0x5e8d` | the three flag bytes `is_signer` `[r6+0x28]`, `is_writable` `[r6+0x29]`, `executable` `[r6+0x2a]` | **[B]** |
| 5 | `0x5e83` to `0x5e95` | the 0x2b-byte `AccountInfo` record staged at `fp-0x278`: key `[r6+0x0]`, the two `Rc` cells, owner `[r6+0x18]`, rent epoch `[r6+0x20]`, the three bytes | **[B]** |
| 6 | `0x5e96` to `0x5e9a` | `r1 = fp-0x40` (out), `r2 = fp-0x278` (the staged record), `call 0x250d` | **[B]** |

Which field that offset is comes from the struct builder `0xecba` (1927 insns), measured at four
points:

| # | cite | measured | tag |
|---:|---|---|---|
| 1 | `0xeda4`, `0xeda5` | `r2 = r8` (the account cursor), `call 0x226f`, the per-type fetch for this field | **[B]** |
| 2 | `0xedb4` | `stxdw [fp-0xe00], r2`, the single write of that slot in the whole builder, taken from `r2 = [fp-0x928]` = word `+0x00` of the helper out block | **[B]** |
| 3 | `0xf457`, `0xf458` | `ldxdw r5, [fp-0xe00]` then `stxdw [r6+0x288], r5`, so accounts `+0x288` is that same slot | **[B]** |
| 4 | `0x227b` | `stb [r6+0x51], 0x2`, the helper out block itself, the same `+0x51` status byte 16.9.3 measures for this helper | **[B]** |

The field is the bonding curve of the pump program:

* `0x226f` calls `0xdbb` at `0x2284`, the account decoder for that field.
* `0xdbb` compares the record owner `[acct+0x18]` (`0xdbd`) against the all-zero key at rodata
  `0xc36a0` (`0xdbf`, `call 0x17723` at `0xdc2`) and against rodata `0xc4eed` (`0xdc7`,
  `call 0x1771b` at `0xdca`), then raises code `0xbbf` at `0xdce` to `0xdd1` on the third arm.
  The 32 bytes at rodata `0xc4eed` are
  `0156e0f693665acf44db1568bf175baa5189cb97f5d2ff3b655d2bb6fd6d18b0`, which base58 as
  `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P`, the pump program id.
* the fail arm of that step formats the account name from rodata `0xc4d7c` with length `0xd`
  (`0xedad`, `0xedaf`), and `0xc4d7c` reads `bonding_curve` followed by `base_mint`.
* the helper pair `0x226f` then `0xdbb`, the `+0x51` status byte and the same name string are
  the three markers 16.9.3 uses to pin the `bonding_curve` field of the sibling accounts struct
  of `create_fee_sharing_config`; the same three markers sit on step 6 of `0xecba`.
* the same word is handed to the AMM payout call at `0x60ce` (`0x73f3`), whose curve key is the
  first operand of that call in 7.4.5. **[B]**

So the v1 row reads the `bonding_curve` field. **[B]**

### P1-a.4 The v2 call row: accounts `+0x248`, field name still open

| # | insn | what the bytes do | tag |
|---:|---|---|---|
| 1 | `0x673c` | `r7 = [r2+0x8]`, the accounts struct | **[B]** |
| 2 | `0x6a30`, `0x6a31` | `r1 = [r7+0x248]`, then `r2 = [r1+0x0]`: the struct word at `0x248` is one step away from the record | **[B]** |
| 3 | `0x6a32` to `0x6a35` | `r8 = fp-0x2d8`, then `call 0x1ec6`, the `AccountInfo` clone of that record into the frame | **[B]** |
| 4 | `0x6a36` to `0x6a39` | `r1 = fp-0x40` (out), `r2 = fp-0x2d8` (the cloned record), `call 0x250d` | **[B]** |

The producer of that offset is in `0xf52a` (2034 insns):

| # | cite | measured | tag |
|---:|---|---|---|
| 1 | `0xf5f4`, `0xf5f5` | `r3 = 0x68`, `call 0x8ee3`: a 0x68-byte allocation before the fetch | **[B]** |
| 2 | `0xf5f9`, `0xf5fa` | `call 0x4a7` with `out = fp-0x2e8`, then `r3 = [fp-0x2e0]` = the payload word | **[B]** |
| 3 | `0xf5fe` | `stxdw [fp-0xb08], r3`, the single write of that slot | **[B]** |
| 4 | `0xfd2c`, `0xfd2d` | `ldxdw r5, [fp-0xb08]` then `stxdw [r6+0x248], r5` | **[B]** |

So the offset is measured twice, once in the body and once in the builder. The **declared name**
of that field is not settled by the bytes read this tick: the name arm that follows the step
belongs to the next fetch (rodata `0xc4e48` at `0xf60a` reads `pump_creator_vault`), and the
same name string is not attested for this step anywhere in the image. It is carried as the open
row of the next tick rather than guessed. The three rows just above stay **[B]** for the offset
and **[R]** for the name. **[B] (closed in P1-e)**

### P1-a.5 Correction to the 3.1 bullet

The bullet in 3.1 says `0x250d` "is the loader used by `update_fee_shares`". That wording is
withdrawn, and the token at the end of the bullet is closed as **[B]** by 7.4.2 and by the rows
above:

* `0x250d` loads no account in the Anchor sense. It borrows the data of one already-fetched
  record, reads 32 bytes at `0x53`, and answers one flag byte. Over its 60 instructions it
  writes nothing except its out block and its own frame.
* In the same body the `SharingConfig` object is read at accounts `+0x5d0` (`0x5f1c`,
  `0x5f1d`) and handed to the authority gate at `0x5f21` (`0x724e`); in the v2 body the same
  object is read at accounts `+0x230` (`0x6764`, `0x6765`) and handed to `0x6768`. The gate
  reads `admin` at object `+0x38` (`0x725b`), `admin_revoked` at `+0x59` (`0x7263`) and
  `status` at `+0x58` (`0x726d`). None of those three reads happens in `0x250d`.
* The two callers are the two `update_fee_shares` bodies, which is the part of the bullet that
  survives: the loader is called by `update_fee_shares`, but it is the curve probe, not the
  config loader.

### P1-a.6 What the gate guards, and what it does not

The gate guards the width of one unaligned 32-byte read. It is not an identity check and not an
error path:

* a record whose data is shorter than `0x73` bytes answers "the quote window is the default"
  with tag 2 and flag 1 at `0x2521`/`0x2522`, so the caller cannot tell a short record from a
  zero quote window;
* the v1 body requires flag 1 for the 6031 gate, so a short record passes that gate;
* the identity of the record is enforced one layer up, at fetch time, by `0xdbb`, which accepts
  owner equal to the all-zero key or owner equal to the pump program id.
* the `0x73` value is the arithmetic of the window, measured in P1-a.1, not a magic constant.

Severity: Informational
Sévérité : Informational
Severity justification: a static reading of the deployed bytes that closes one documentation mark and corrects one sentence, with no execution and no fund, admission, consensus or production effect measured.

## P2-b. The seven-byte bump block and the record the version guard returns

Scope: the two residuals that 16.10.5 left open, both on the `create_fee_sharing_config` pair
`try_accounts` `0xd95d` and wrapper `0x13810`, with the body `0x56c7`. The slot table and the
derivation rows of 16.10.2 and 16.10.3 are used as given; what follows measures the seven writes of
the block, its readers, and the two words the `0x56ca` edge stores. Every address cited here is
re-read from the deployed image by `scratch/p2b_verify.py`, which also rebuilds the two 32-byte
program ids from the `lddw` immediates of their own rows: 123 assertions, PASS.

### P2-b.1 The seven writes, at their addresses

The wrapper parks the block address at `fp-0xff8` (`0x1381e`, `0x1381f`, `0x13820`), `try_accounts`
receives it at `0xd962 ldxdw r2, [r5 -0xff8]` and stages it at `fp-0xc38` (`0xd963`). Every later use
inside the callee is a reload of that cell (`0xdb3a`, `0xdc12`, `0xdc46`, `0xdd36`, `0xdd91`,
`0xddfe`), so the census below is a census of the object the wrapper handed over and not of the text
order:

| slot | store row | value | derivation call, read-back row | program id of the derivation |
|---:|---|---|---|---|
| 0 | `0xde00 stb [r2 +0x0], 0x1` | the immediate `0x1` | none | none |
| 1 | `0xddff stxb [r2 +0x1], r1` | bump, `0xddfd ldxb r1, [r10 -0x940]` | `0xddf4 call 0x915e` to `0x16f53`, static seeds `0xc8be8` | `pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA` |
| 2 | `0xdc13 stxb [r2 +0x2], r1` | `0xdc11` | `0xdc08 call 0x934a`, static seeds `0xc8be8` | `[fp-0x970]`, the executing program |
| 3 | `0xdc47 stxb [r2 +0x3], r1` | `0xdc45` | `0xdc3c call 0x9316`, static seeds `0xc8c28` | `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P` |
| 4 | `0xdb3b stxb [r2 +0x4], r1` | `0xdb38` | `0xdb2f call 0x9423`, seed array at `fp-0xd8` | `[fp-0x970]` |
| 5 | `0xdd37 stxb [r2 +0x5], r1` | `0xdd35` | `0xdd2c call 0x9226`, seed array at `fp-0x40` | `6EF8rrec...` |
| 6 | `0xdd92 stxb [r2 +0x6], r1` | `0xdd90` | `0xdd87 call 0x91cb`, static seeds `0xc8be8` | `6EF8rrec...` |

All six calls land on the same helper `0x16f53`, which reaches
`sol_try_find_program_address` at `0x16f61`; the bump comes back in that syscall out buffer and is read
at `[r10 -0x940]`. The two 32-byte ids are rebuilt from their own immediates: `0xdc29`, `0xdc2c`,
`0xdc2f`, `0xdc32` for slot 3, `0xdd19`, `0xdd1c`, `0xdd1f`, `0xdd22` for slot 5, `0xdd74`, `0xdd77`,
`0xdd7a`, `0xdd7d` for slot 6, and `0xdde1`, `0xdde4`, `0xdde7`, `0xddea` for slot 1. Slots 3, 5 and 6
reassemble to the same key, slot 1 to a different one, which is the pairing 16.10.3 names.

### P2-b.2 Why the six bump stores are slots 1 to 6

Because the object is six bump bytes plus one byte that no derivation writes. Three measurements:

* the six stores whose value is a derivation result are exactly the six calls of `0x16f53`, one per
  seeded account, and each value is read back from the same syscall out buffer at `0xdb38`, `0xdc11`,
  `0xdc45`, `0xdd35`, `0xdd90` and `0xddfd`;
* slot 0 is the only byte written with an immediate, `0xde00 stb [r2 +0x0], 0x1`, and it is written
  immediately after the slot 1 store at `0xddff`;
* slot 0 is also the only byte the wrapper sets itself, `0x1381b stb [fp-0xbe7], 0x0`, in the object it
  hands to `try_accounts` at `0x1381e` and `0x1381f`.

So the object leaves the wrapper with byte 0 at `0x0`, and it comes back with byte 0 at `0x1` and the
six bump bytes in slots 1 to 6. The store at `0xde00` is followed at `0xde01` by the block that loads a
32-byte key and compares it at `0xde0f`, which targets the `sol_memcmp_` shim `0x184e6` (its syscall at
`0x184e9`), so byte 0 is raised once the derivations are in place and before the first key check that
follows them.

Consumers, measured over both functions and the body:

* inside `try_accounts` `0xd95d` no byte of the block is loaded, the only accesses being the six pointer
  reloads listed in P2-b.1;
* the body loads two of the seven bytes, `0x5863 ldxb r1, [r1 +0x24]` (slot 4, the sharing config bump)
  and `0x5be9 ldxb r1, [r1 +0x22]` (slot 2, the event authority bump of the executing program), both
  through the out pointer the body keeps at `fp-0x6f0`;
* no byte of the block region is loaded through the body context register `r7`.

So slots 0, 1, 3, 5 and 6 have no consumer in this instruction, which is the statement of 16.10.5 with
the reader census behind it.

What stays TERMINAL: the source name and the source role of byte 0. The bytes settle the mechanism (a
byte the caller zeroes, the callee raises to 1 once the six derivations are done, no reader) but no
string, relocation or consumer carries a name for it.

The copy path explains why the body reads the block through the out pointer and not through `ctx`: the
wrapper writes the seven bytes into the accounts image at `out+0x20` to `out+0x26` with `0x13837` and
`0x13838` (slots 0 to 3) and `0x13839` and `0x1383a` (slots 3 to 6), and it does so after the 0x5d0
byte copy into `ctx` at `0x13833`.

### P2-b.3 Two corrections

* 16.10.5 says the wrapper pre-fills seven slots. Measured, it pre-fills six bytes: `0x1381b` sets slot
  0 to `0x0`, `0x1381a stxw [fp-0xbe5]` sets slots 2, 3, 4 and 5 to `0xFF` (the source register is `-1`
  from `0x13818`), and `0x13819 stxb [fp-0xbe1]` sets slot 6 to `0xFF`. There is no store to `fp-0xbe6`,
  which is slot 1, anywhere in `0x13810` to `0x138b9`, so that byte reaches the callee uninitialised and
  the callee writes it at `0xddff` before anything reads it.
* 16.10.3 lists the slot 1 store at `0xddfe`. Measured, `0xddfe` is the reload of the block pointer and
  the store is `0xddff`. The slot number in that row is unchanged.

### P2-b.4 The record the 0x56ca edge writes

The guard: `0x56c7 mov64 r3, 0x2`, `0x56c9 ldxb r4, [r7 +0x5b]` reads the version byte that
`0x5865 stb [r7 +0x5b], 0x2` initialises, and `0x56ca jne r4, 0x0, +0x47c` jumps to `0x5b47`.

Three registers at `0x5b47` on that edge, each from a reaching definition:

* `r1` is the pointer the body received in argument 1. Nothing from `0x56c7` to `0x56ca` writes it, and
  it is the same value the body stages at `0x56da` in `fp-0x6e8`. The wrapper passes `fp-0xbf8` there
  (`0x13843`, `0x13844`).
* `r3` is `0x2`, from `0x56c7`. `0x56cb mov64 r3, 0x0` lies on the fall-through and does not run on this
  edge.
* `r0` is never written in the body before this edge, so it carries the value the caller left in `r0` at
  the call `0x13847`. The last writer of `r0` in the wrapper before that call is the shim at `0x13833`,
  which targets `0x184d9` (`0x184d9 mov64 r6, r1`, `0x184da` the `sol_memcpy_` call, `0x184db mov64 r0,
  r6`), and the pointer handed to it is `fp-0xbb8` (`0x1382e`, `0x1382f`). The payload word is therefore
  a frame address of the caller, not a value this handler produced.

So the arm stores `{+0x0: 2, +0x8: fp-0xbb8}` at the return pointer: the Ok tag with a dead payload
word. The caller confirms both words: `0x13848 ldxdw r8, [r10 -0xbf8]` reads the tag, `0x13849 jeq r8,
0x2, +0x1` sends tag 2 to `0x1384b`, and the Ok path never loads `fp-0xbf0`, the payload word. That word
is read at one site only, `0x13883 ldxdw r9, [r10 -0xbf0]`, which is the arm for a tag other than 2. On
the Ok path the outgoing payload comes from `0x13855 ldxdw r9, [r10 -0xc00]`.

Two structural facts corroborate the reading. The exit block at `0x5b47` is entered directly by exactly
two edges, `0x56ca` and `0x5c54`, and both carry tag 2: the Ok tail sets it at `0x5c53` and reloads the
out pointer at `0x5c4e`. Every other edge enters at `0x5b46`, the reload of `fp-0x6e8`. The staged record
`{fp-0x6d8, fp-0x6d0}` belongs to the `0x5b3e` raise path only: `0x5b43 call 0x8d8b` builds it, `0x5b44`
and `0x5b45` read its two words, and `0x5b46` reloads the return pointer for the store.

### P2-b.5 What this closes

* 16.10.5 residual one, the reason `try_accounts` writes slots 1 to 6: closed as [B] for the mechanism
  (six derivations, six bumps, byte 0 raised by a constant) and TERMINAL for the source name of byte 0.
* 16.10.5 residual two, the payload of the `0x56ca` arm: closed as [B], with the correction that the arm
  returns the Ok tag and a dead payload word and does not return the record staged at `fp-0x6d8`.
* Ledger rows O1 (line 5220) and O3 (line 5215) are flipped to [B] (closed in P2-b). The two corrections
  of P2-b.3 are recorded here and are not carried as open rows.
* The rows of 16.10.2 and 16.10.3 that this section re-reads are unchanged: slot 4 is the sharing config
  bump, slot 2 the event authority bump of the executing program, and the two program ids reassemble to
  the two keys 16.10.3 names.

Measurements read from the deployed program image of the lalalune/pumpfun-source evidence set (MIT).

Severity: Informational
Sévérité : Informational
Severity justification: A static reading of one seven-byte stack object and of one return record inside a single handler, with no execution; no behaviour, fund, admission or consensus effect is measured.

## P1-b. The 7.5 supporting helpers: measured argument signatures, caller census and library identity

This section closes the item that 7.5 left as a table of addresses. For each row it gives
the argument signature measured at the call rows, the caller census over the whole image,
and the library identity where the bytes settle it. A row the bytes cannot name is stated
once as TERMINAL here and in the ledger.

### P1-b.1 Method, and the two body sizes a row has

Every claim below is computed, not read off the linear text:

* **Caller census.** A call row is an instruction with opcode `0x85` whose raw immediate is
  not relocated and whose target `pc + 1 + imm` equals the row address. The image holds
  4741 such calls, 155 relocated syscall sites and 121 register calls (`0x8d`). Every row of
  the table has at least 2 call rows and none is reached by a register call, so the census
  below is complete for those rows.
* **Argument signature.** For each of `r1` to `r5` at each call row, a reaching definition
  query over the basic block graph of the *caller*, then the operands of that definition
  resolved up to three levels. sBPF clobbers `r1` to `r5` on a call and preserves `r6` to
  `r10`, and the query models that, which is why a frame address reads as `r10 - N` and why
  a register that is not written after the previous call reads as clobbered.
  The classes are: frame address (`r10 - N`), static pointer (`lddw` through a `.rel.dyn`
  type 8 relocation), value staged in memory (`[rX + off]`), immediate, live-in register of
  the caller, two arms (a merge in the predecessor graph), clobbered.
* **Two body sizes.** `fees_prog` delimits functions by call targets only, so a root that
  nothing calls is merged with its neighbours. Each row therefore carries two numbers: the
  `func_of` span that 7.5 printed, and the **reached** body, obtained by following jumps and
  fallthroughs from the entry and stopping at `exit`. Where the two differ the reached body
  is the measurement and the span is only a range.
* **Library identity.** Three levers: the syscall relocations of `.rel.dyn` type 10 with the
  names in `.dynstr`; the Rust panic `Location` records embedded in `.data.rel.ro` as
  (string pointer, length, line, column) at 4-byte granularity, which carry the qualified
  source path of the crate that emitted the panic; and the string a `lddw` data pointer
  resolves to. Paths are quoted from the crate root; the build root that prefixes them in
  the image is omitted here.

### P1-b.2 Census and reach

| # | helper | byte | span | reached | exits | call rows |
|---:|---|---|---:|---:|---:|---:|
| 1 | `sol_memcpy_` thunk `0x184d9` | `0xc26c8` | 4 | 4 | 1 | 372 |
| 2 | `sol_memcmp_` thunk `0x184e6` | `0xc2730` | 8 | 8 | 1 | 274 |
| 3 | grow/reserve `0x1c03` | `0xe018` | 43 | 43 | 1 | 2 |
| 4 | grow `0x1bd6` | `0xdeb0` | 44 | 44 | 1 | 3 |
| 5 | grow `0x1ba9` | `0xdd48` | 44 | 44 | 1 | 10 |
| 6 | grow `0x1b21` | `0xd908` | 45 | 45 | 1 | 46 |
| 7 | grow core `0x1a5a` | `0xd2d0` | 101 | 101 | 1 | 10 |
| 8 | `0x1636` | `0xb1b0` | 636 | 823 | 4 | 2 |
| 9 | clock `0x1621e` | `0xb10f0` | 29 | 29 | 1 | 24 |
| 10 | `0x16eb0` | `0xb7580` | 118 | 58 | 2 | 25 |
| 11 | `0x161ae` | `0xb0d70` | 108 | 108 | 1 | 41 |
| 12 | packer `0x989` | `0x4c48` | 132 | 132 | 1 | 8 |
| 13 | `0x8d8b` | `0x46c58` | 59 | 59 | 1 | 37 |
| 14 | `0x1601e` | `0xb00f0` | 70 | 70 | 1 | 431 |
| 15 | message resolver `0x8dca` | `0x46e50` | 149 | 149 | 1 | 59 |
| 16 | formatter `0x8932` | `0x44990` | 917 | 917 | 1 | 69 |
| 17 | box `0x15a4e` | `0xad270` | 17 | 17 | 1 | 89 |
| 18 | `0x178c8` | `0xbc640` | 26 | 183 | 1 | 71 |
| 19 | `0x176d7` | `0xbb6b8` | 17 | 294 | 1 | 6 |
| 20 | `0x1ec6` | `0xf630` | 178 | 33 | 1 | 69 |
| 21 | `0x17148` | `0xb8a40` | 41 | 41 | 1 | 45 |
| 22 | `0x1424` | `0xa120` | 26 | 26 | 1 | 2 |
| 23 | `0x1652f` | `0xb2978` | 8 | 21 | 2 | 15 |

Rows 8, 10, 18, 19 and 20 are the five where the span and the reached body disagree.
For row 8 the span is too small (the body flows past it), for rows 10 and 20 the span is too
large (it swallows the next root), and for rows 18 and 19 the panic cold block is shared, so
the reached set is much larger than the printed count. **[B]**

### P1-b.3 The 20 rows of the table, one by one

**1. `sol_memcpy_` thunk `0x184d9` (byte `0xc26c8`, 4 insns).** The body is the thunk itself:
the relocated call at `0x184da` carries the `.dynstr` name `sol_memcpy_`. Signature over the
372 call rows: `r1` frame address 180, merge 77, other 69, staged 35; `r2` frame address 202,
staged 109, merge 33, other 15; `r3` immediate 280 (the length, `0x30` on the account-meta
copies), other 43, merge 25, staged 17; `r4` clobbered 267; `r5` clobbered 330. So the three
arguments are (destination, source, length) and the two remaining registers carry nothing.
Identity: the Solana C ABI symbol `sol_memcpy_`, settled by the relocation and the name. **[B]**

**2. `sol_memcmp_` thunk `0x184e6` (byte `0xc2730`, 8 insns).** Relocated call at `0x184e9`,
name `sol_memcmp_`. Signature over the 274 call rows: `r1` frame address 142, staged 94;
`r2` frame address 142, static pointer 76 (the all-zero pubkey constant at `0xc36a0` at
`0x38b`, and `0xc5404` at `0x394`), staged 23; `r3` immediate **274 of 274**, and it is
`0x20` on **272** of them, `0x15` once and `0x53` once, so all but two rows are 32-byte key
compares; `r4` and `r5` clobbered 208 and 210. Identity: the Solana C ABI symbol
`sol_memcmp_`. **[B]**

**3 to 7. The growth entries.** All five share the same frame: `r1` is always a frame address,
and the last two instructions before the call are `add64 r1, -0x30` and `add64 r4, -0x18`, so
the first argument is the receiver (a `Vec` or `RawVec` at 0x30 bytes) and the fourth a
`Result` out slot. What separates them is the element stride, measured as the immediate the
body multiplies by:

* `0x1bd6` multiplies by `0x22` at `0x1bed` and `0x1bf0`, so it is the 34-byte element grow.
* `0x1ba9` multiplies by `0x30` at `0x1bc0` and `0x1bc3`, so it is the 48-byte element grow.
* `0x1b21` multiplies by `0x30` at `0x1b39` and `0x1b3c`, so it is a second 48-byte element
  grow, the one that takes the element count in `r2` and the spare capacity in `r3`.
* `0x1c03` shifts by 5 (`lsh64 r7, 0x1` at `0x1c0e`, then `lsh64 r3, 0x5` at `0x1c19` and
  `lsh64 r4, 0x5` at `0x1c1c`, with the overflow guard `0x400000000000000` at `0x1c12`), so
  **its element stride is 0x20, not 0x22**: the 0x22 stride of the 7.5 row belongs to
  `0x1bd6`.
* `0x1a5a` is the shared core: no stride of its own, one call to the `sol_memcpy_` thunk at
  the copy site, and the bump allocator inlined in the body (`lddw r0, 0x300000000` at
  `0x1a64`, `lddw r7, 0x300008000` at `0x1a67`, then three more loads of the same cursor at
  `0x1a76`, `0x1a7a` and `0x1a8a`).

Each of the four outer entries calls `0x1a5a` once and `0x175af` once. `0x175af` is the
capacity-overflow path: it branches on its first argument at `0x175af`, calls `0x17528` at
`0x175b0`, and `0x17528` is the function whose body loads the record at `0xc9da0`, which
decodes to the panic location `library/alloc/src/raw_vec.rs:25:5`, the `capacity_overflow`
site of the alloc crate. Signature over the call rows: `0x1c03` (2 rows) `r1` frame 2,
`r2` merge 2, `r3` staged 2; `0x1bd6` (3 rows) `r1` frame 3, `r3` staged 2; `0x1ba9` (10 rows)
`r1` frame 10, `r3` merge 7 and staged 3, `r4` and `r5` staged 7; `0x1b21` (46 rows) `r1` frame
46, `r2` merge 33, staged 8, immediate 5, `r3` staged 46; `0x1a5a` (10 rows) `r1` frame 10,
`r2` merge 8, `r3` other arithmetic 7 (the product of the element size and the count), `r4`
frame 10, `r5` merge 6.
Identity: the alloc crate growth machinery. The stride is measured in the entry, and the crate
is settled one call down, through `0x175af` into `0x17528` and the
`library/alloc/src/raw_vec.rs:25:5` record. **[B]**

**8. `0x1636` (byte `0xb1b0`).** This row is not a bump allocator. Measured: the entry at
`0x1636` does guard the size against `0x15` and read the bump cursor (`lddw r2, 0x300000000`
at `0x163e`, load at `0x1640`, limit `0x300008000` at `0x1641`), but the reached body from
that entry is 823 instructions to `0x198c` with four exits (`0x1659`, `0x192c`, `0x1955`,
`0x198c`), and inside it sit twelve panic `Location` records whose path is
`library/core/src/slice/sort.rs` at lines 1083, 1096, 1097, 1098, 1166, 1204, 1218, 1325,
1342 and 155, the assertion string `assertion failed: end >= start && end <= len` at
`0xc395f` and `assertion failed: offset` at `0xc398b`, seven `sol_memcmp_` calls, five
`sol_memcpy_` calls and one call to the `sol_memmove_` thunk `0x184dd` at `0x171f` (the thunk
calls `sol_memmove_` at `0x184de`). So `0x1636` is the stable slice sort of the core crate
with the scratch allocation of the allocator inlined at the entry, and the heap cursor
belongs to that allocation, not to a standalone allocator. It is called twice, at `0x658c`
and `0x6f63`, once per fee body, with `r2` a staged value and `r1` a frame address merged
from two arms. The `func_of` span of 636 instructions therefore understates the body.
Identity: core `slice::sort`, settled by the ten Location records. **[B]**

**9. Clock `0x1621e` (byte `0xb10f0`, 29 insns).** Relocated call at `0x16226`, name
`sol_get_clock_sysvar`, then one call to the 122-instruction clock copy `0x16733`. Signature
over 24 call rows: `r1` **frame address 24 of 24** (the destination of the copy), `r2`
clobbered 9, staged 7, live-in 6, merge 2, `r3` clobbered 11, live-in 6, staged 5, `r4`
clobbered 13, `r5` clobbered 15. The clock is read into a caller frame slot every time, which
is what the 7.1 to 7.5 walks relied on. Identity: the Solana syscall `sol_get_clock_sysvar`. **[B]**

**10. `0x16eb0` (byte `0xb7580`).** The reached body is 58 instructions, not 118, with two
exits (`0x16ed8`, `0x16ee9`). It holds no `Location` record and no string: the
`BufferTooSmall`, `Utf8Error`, `valid_up_to` and `error_len` pointers at `0x16f0f`,
`0x16f1d`, `0x16f28` and `0x16f2b` lie in the `func_of` span but outside the reached body, so
the earlier attribution of those strings to this entry is withdrawn. What the reached body
does: `r1` frame address 25 of 25, `r2` the same static pointer `0xc4ead` on all 25 rows
(a table of small integers, not text), `r5` frame address 25 of 25, and the callees are one
`sol_memcpy_` at `0x184d9`, one `0x175af`, one `0x18438`, and the core integer formatters
`0x1828c` and `0x182b8`, whose bodies hold the record `library/core/src/fmt/num.rs:105:23`.
The call rows include `0x66e7` in the v1 apply helper `0x6479` and `0x70c0` in the v2 apply
helper `0x6e50`, so the entry formats the numeric fields of the event into the buffer the
caller staged at `r1`. Identity of the core formatter part: core, settled by the `num.rs`
record; the crate of `0x16eb0` itself is not attested by any string or record in its body. **[B]**

**11. `0x161ae` (byte `0xb0d70`, 108 insns).** The row says the event CPI emitter calls
`invoke_signed` at `0x16214`. Measured: `0x16214` is `call 0x28e`, whose target is `0x164a3`,
and the body of `0x161ae` holds no syscall at all. The single `sol_invoke_signed_rust` site
of the whole image is at `0x16502`, inside `0x164a3` (123 reached instructions, two exits
`0x16517` and `0x1651f`, one `sol_set_return_data` site at `0x1651e` in the neighbouring
entry `0x1651e`). So the row's role holds and its address does not: the emitter reaches the
one CPI site through the call at `0x16214` into `0x164a3`, and the address to cite is
`0x16502`. Signature over 41 call rows: `r1` frame address 40, `r2` frame address 40, `r3`
frame address 32 and staged 8, `r4` immediate 33, `r5` frame address 41. The two rows inside
the apply helpers that matter here are `0x6706` in the v1 helper `0x6479` and `0x70df` in the
v2 helper `0x6e50`. **[B]**

**12. Packer `0x989` (byte `0x4c48`, 132 insns).** Called 8 times: `0x58a6` and `0x5b70` in
`create_fee_sharing_config` (`0x56c7`), `0x644e` in the helper `0x63a6`, `0x6b07` in the v2
body `0x673a`, `0xe2ad` in `0xe2a5`, `0x1392f` and `0x139b6` in the two wrappers `0x138d4`
and `0x1395a`, and `0x13a81` in `0x139e4`. Signature: `r1` frame address 8 of 8
(the out image), `r2` the receiver or a staged pointer, `r3` a **static pointer 8 of 8**,
`r4` static pointer 4, live-in 2, staged 2, `r5` clobbered 6. The body calls the writer
`0x15991` seven times, the `sol_memcmp_` thunk once at `0x184e6`, and the error constructor
`0x1601e` once. `0x15991` is the function whose body holds the record
`src/bpf_writer.rs:28:9`; the path is crate-local, so it names no crate. The role is settled
(it writes the account image through a writer, then compares the result), the crate of the
writer is not. **[B]**

**13. `0x8d8b` (byte `0x46c58`, 59 insns).** Called 37 times. Signature: `r1` **frame address
37 of 37**, `r2` **immediate 37 of 37** with the values 16, 21, 19, 1, 25, 15, 35 and 7 among
them, `r3` clobbered 24, staged 7, merge 5, `r4` clobbered 31, `r5` clobbered 34. The body
calls the message resolver `0x8dca` once, the formatter `0x8932` once, the box `0x15a4e`
once and the panic entry `0x178c8` once, and it loads the record at `0xc8848`, which decodes
to the panic location `library/alloc/src/string.rs:2559:14` (with the message
`a Display implementation returned an error unexpectedly` at `0xc387d`, length `0x37`). The
shape is therefore: take a code index in `r2`, resolve its text through `0x8dca`, format it
into the `String` staged at `r1` through `0x8932`, box the error through `0x15a4e`, and take
the panic arm when formatting fails. The 7.5 role `err!(FeeError) ctor` matches the `r2`
immediate. Identity of the formatting part: alloc, settled by the `string.rs` record. **[B]**

**14. `0x1601e` (byte `0xb00f0`, 70 insns).** The largest census of the table: 431 call rows.
Signature: `r1` **frame address 431 of 431**, `r2` **immediate 431 of 431**, `r3` clobbered
321, staged 56, merge 33, live-in 20, `r4` clobbered 360, `r5` clobbered 370. The body loads
the record at `0xc8f68`, which decodes to `library/alloc/src/string.rs:2559:14`, and the same
message pair `0xc5487` and length, so its formatting arm is the same alloc path as row 13.
The `r2` immediate is the error code; one of the call rows is `0x13944` in the v1 wrapper,
which is the 102 raise the earlier sections attributed to this entry. Identity: alloc
formatting inside a program-side constructor. **[B]**

**15. Message resolver `0x8dca` (byte `0x46e50`, 149 insns).** No internal call instruction,
and one register call: the body ends at `0x8e81` with `callx r4`, where `r4` is loaded as the
slot at `+0x18` of the object at `+0x28` of the caller's record, so the text is handed to a
callback the caller supplies. It holds 36 data pointers, among them `Invalid admin` at
`0xc45b3`, `No fee tiers provided` at `0xc45c0`, `Fee tiers must be sorted` at `0xc460d`,
`Shareholder cannot have` at `0xc47c1`, `Pool creator_fees must be` at `0xc4961`,
`quote_mint is not the bo` at `0xc4999` and `User ID exceeds maximum` at `0xc4847`.
Signature over 59 rows: `r1` **static pointer 57 of 59** (the message), `r2` **frame address
59 of 59** (the out record), `r3` to `r5` clobbered 58. That is the message table of the
program: identity settled as program side by the strings themselves. **[B]**

**16. Formatter `0x8932` (byte `0x44990`, 917 insns).** The reached body is the whole span.
It has no string and no `Location` of its own; its only callee is `0x175af`, eighteen times.
Signature over 69 rows: `r1` **frame address 69 of 69**, `r2` **static pointer 68 of 69**
(the pieces array of a `fmt::Arguments` record, for instance `0xc3e88` and `0xc3e20`, whose
bytes are (pointer, length) pairs rather than text), `r3` clobbered 42, live-in 11, merge 9,
staged 4. So the shape is (out buffer, pieces array, staged arguments) and the body is the
`Display` writer that walks the pieces and the arguments. Identity: the formatting machinery
that the alloc `String` writer and the panic paths both use; the crate is not attested by a
record inside this body. **[R]**

**17. Box `0x15a4e` (byte `0xad270`, 17 insns).** Measured: `mov64 r1, 0xa0` at `0x15a50`,
`mov64 r2, 0x8` at `0x15a51`, allocator call at `0x15a52`, then `mov64 r1, 0x8` at `0x15a55`
and `mov64 r2, 0xa0` at `0x15a56` for the failure arm, then the two stores `stxdw [r6 +0x8],
r8` at `0x15a5c` and `stdw [r6 +0x0], 0x0` at `0x15a5d`. So it allocates a 160-byte, 8-aligned
box and hands back the pair (pointer, size) in the caller's frame. Signature over 89 rows:
`r1` frame address 89 of 89, `r2` frame address 89 of 89, `r3` to `r5` clobbered 89. The
two fee bodies call it twice each, at `0x5f18` and `0x5f5a` (v1, `r1` = `r10 - 0x2e8` and
`r10 - 0x2d8`, `r2` = `r10 - 0x278`) and at `0x6790` and `0x6879` (v2). Identity: a boxed
allocation of the 0xa0-byte error object, alloc shaped by the (size, align) allocator call. **[B]**

**18. `0x178c8` (byte `0xbc640`).** The reached body is 183 instructions, not 26. Signature
over 71 rows: `r1` **static pointer 71 of 71**, `r2` **immediate 71 of 71** with `55` on 51
rows, `43` on 19 rows and `51` on one row, `r3` **frame address 71 of 71**, `r4` and `r5`
**static pointers 71 of 71** (two `Location` records). The messages passed in are
`a Display implementation returned an error unexpectedly` at `0xc387d` (length `0x37` = 55),
`called \`Result::unwrap()\` on an \`Err\` value` at `0xc44f3` (length `0x2b` = 43) and
`a formatting trait implementation returned an error` at `0xc791f` (length 51). The rows
inside the two fee bodies are `0x5eff` and `0x6761`, both with `r3` a frame address. So the
shape is (message, length, staged record, location, location) and the entry is the shared
panic shim that formats a static message with a staged argument list. The crate of the shim
is not attested by a record inside its body. **[R]**

**19. `0x176d7` (byte `0xbb6b8`).** The reached body is 294 instructions, not 17. The six
call rows are `0x254b` (in the loader `0x250d`, `r1` the record at `0xc8a68` =
`programs/pump-fees/src/common/mod.rs:21:48`), `0x56c4` (`r1` the record at `0xc8a98` =
`33:48`), `0x6b1d` (`r1` the record at `0xc8a98`), `0x1652e`, `0x16538` and `0x16555`, which
are the internal raises of the borrowing family `0x16520`, `0x1652f` and `0x16549`. Signature: `r1` static
pointer 6 of 6, `r2` clobbered 3 and staged 3, `r3` other arithmetic 3, clobbered 2, staged 1,
`r4` and `r5` live-in 3. So the entry takes the `Location` record as its first argument and
the panic message machinery as the rest, which is the `Location`-carrying panic path of the
core crate; the body also reaches the record `library/core/src/escape.rs:56:11` at `0x177f7`.
**[B]**

**20. `0x1ec6` (byte `0xf630`).** The row calls this a drop. Measured, the reached body is 33
instructions and increments reference counts instead of releasing them: `ldxdw r5, [r3 +0x0]`
at `0x1ec7`, `add64 r5, 0x1` at `0x1ec8`, `stxdw [r3 +0x0], r5` at `0x1ecd`, the wrap test
`jeq r5, 0x0` at `0x1eca` with `call -0x1` (the relocated `abort` at `0x1ecf`), then the same
pattern again on `[r5 +0x0]` from `0x1ed0` to `0x1ed8`, and onward over the fields at
`+0x18`, `+0x20` and `+0x28` of the source record in `r2`. The strong and weak words of a
reference-counted header sit at `+0x0` and `+0x8`, and the image has no atomic opcode, so
this is the non-atomic `Rc` clone of a record that holds several `Rc` fields, aborting on
wrap. There is no store of a decremented count and no free call in the body, so the role
`drop / drop_in_place` of the 7.5 row is replaced by this measurement. Signature over 69
rows: `r1` frame address 69 of 69 (the out pair), `r2` staged 59 of 69 (the source record, for
instance `r2` loaded from `[r7 +0x10]` at `0x2748` and from `[r7 +0x0]` at `0x274d` at the v1
rows `0x274c` and `0x2751`), `r3` to `r5` clobbered. The crate is not attested by a record in
the body. **[R]**

**21. `0x17148` (byte `0xb8a40`, 41 insns).** Signature over 45 rows: `r1` **the single
static pointer `0xc87e0` on 45 of 45 rows**, `r2` clobbered 18 and live-in 8, `r3` clobbered
23 and merge 13, `r4` clobbered 24, `r5` clobbered 27. The body masks the low two bits of its
argument (`and64 r7, 0x3` at `0x1714a`), reads a byte at `+0xf` on one arm (`0x1714d`) and at
`+0x10` on the other (`0x17156`), compares it with `0x25` at `0x17159`, and calls `0x17079`
(a 157-instruction leaf with no call and no syscall), `0x17116` and `0x142ea`. It decrements
nothing and frees nothing, so it is not the drop the 7.5 row names. What it does with the one
static record is not settled by any string, `Location` record or syscall in the body:
TERMINAL, not re-dug. **[R]**

**22. `0x1424` (byte `0xa120`, 26 insns).** This one is a drop: `ldxdw r2, [r1 +0x10]` at
`0x1424`, the empty test `jeq r2, 0x0` at `0x1425`, the step `add64 r1, 0x30` at `0x1429` and
the countdown `add64 r2, -0x1` at `0x142a`, then per element the two decrements
`stxdw [r4 +0x0], r5` at `0x1431` (`r5 = [r4 +0x0] - 1`) and `stxdw [r4 +0x8], r5` at
`0x1435`, and the same pair for `[r3 +0x0]` and `[r3 +0x8]` at `0x1438` and `0x143c`, with
the loop back `ja -0x15` at `0x143d`. So it releases a `Vec` of 0x30-byte elements, each
holding two reference-counted words at `+0x0` and `+0x8`, which is the `drop` of the array of
`Rc` pairs that the two fee bodies build. It has exactly two call rows, `0x60eb` (v1, `r1` =
`r10 - 0x148`) and `0x6b17` (v2, `r1` = `r10 - 0x58`); `r2` to `r5` are clobbered at both.
Crate not attested by a record in the body. **[B]** for the role, **[R]** for the crate.

**23. `0x1652f` (byte `0xb2978`).** The reached body is 21 instructions, not 8. Measured:
`ldxdw r1, [r1 +0x10]` at `0x1652f`, `ldxdw r2, [r1 +0x10]` at `0x16530`, the bound
`lddw r3, 0x7ffffffffffffffe` at `0x16531` with `jgt r2, r3` at `0x16533`, the result
`ldxdw r0, [r1 +0x20]` at `0x16534` and `exit` at `0x16535`; on the failing arm the record at
`0xc98d0` (panic location `src/lib.rs:94:19`) is loaded at `0x16536` and the panic entry
`0x176d7` is called at `0x16538`. So the entry follows a pointer twice, bounds the length
word at `+0x10` against `isize::MAX - 1`, and returns the word at `+0x20`: the data pointer
and length pair of a borrowed account buffer. Signature over 15 rows: `r1` merge 6, staged 4,
frame 4, live-in 1, and at the row `0x67af` in the v2 body `r1` is `r10 - 0x728` and `r2` is
a chain of three loads. The path of the panic record is crate-local (`src/lib.rs`), so no
crate is named: TERMINAL for the crate, the shape above is the measurement. **[B]** for the
shape, TERMINAL for the crate.

### P1-b.4 Library identity, summarised

Settled by a name or a qualified path in the body:

| row | evidence | identity |
|---|---|---|
| 1, 2 | `.dynstr` names `sol_memcpy_` at `0x184da`, `sol_memcmp_` at `0x184e9` | Solana C ABI |
| 9 | `.dynstr` name `sol_get_clock_sysvar` at `0x16226` | Solana C ABI |
| 11 | `.dynstr` name `sol_invoke_signed_rust` at `0x16502`, reachable from `0x161ae` through `0x164a3` | Solana C ABI |
| 3 to 7 | record `library/alloc/src/raw_vec.rs:25:5` at `0xc9da0`, loaded by `0x17528`, called from `0x175af` from every growth entry | alloc |
| 8 | ten records `library/core/src/slice/sort.rs` lines 1083 to 1342 and 155 | core |
| 10 | records `library/core/src/fmt/num.rs:105:23` in the callees `0x1828c` and `0x182b8` | core, for the formatter reached |
| 13, 14 | record `library/alloc/src/string.rs:2559:14` at `0xc8848` and `0xc8f68` in the own body | alloc |
| 15 | the program message strings at `0xc45b3` to `0xc4847` in the own body | program |
| 19 | record `library/core/src/escape.rs:56:11` at `0x177f7` in the own body | core |
| 12, 17, 22 | writer `0x15991` with `src/bpf_writer.rs:28:9`, allocator call with (0xa0, 8), reference-count release | shape settled, crate not attested |

Terminal, stated once and not re-dug: the crate of `0x17148` (row 21), the crate of the
panic shim `0x178c8` (row 18), the crate of the clone `0x1ec6` (row 20), the crate of the
borrowing helper `0x1652f` (row 23, path `src/lib.rs:94:19` is crate-local), and the crate of
the formatter `0x8932` (row 16). In each of those five the bytes give the argument shape, the
caller census and the callee set, and no string, `Location` record or syscall names the
crate. **[R]**

### P1-b.5 What this closes, and what it corrects in 7.5

Closed: the argument signature, the caller census and the identity of every row of the 7.5
table. The census is recomputed for 23 entries (the two instantiations of the growth row are
counted separately, and the three drop candidates separately) and covers 1710 call rows in
total.

Corrected in 7.5, each on the bytes cited above:

1. Row 3 calls `0x1c03` the 0x22-stride reserve. Its stride is 0x20 (`lsh64 r3, 0x5` at
   `0x1c19`); the 0x22 stride is `0x1bd6` (`mul64 r3, 0x22` at `0x1bed`).
2. Row 7 calls `0x1636` a bump allocator. It is the core stable sort, with the scratch
   allocation of the bump allocator inlined at the entry, and it is called once per fee body.
3. Row 10 says the emitter calls `invoke_signed` at `0x16214`. `0x16214` calls `0x164a3`;
   the single `sol_invoke_signed_rust` site of the image is `0x16502`.
4. Row 9 attributes the `BufferTooSmall` and `Utf8Error` strings to `0x16eb0`. They sit
   outside its reached body, which is 58 instructions and holds no string.
5. Row 19 calls `0x1ec6` a drop. It increments reference counts and aborts on wrap.
6. Rows 15 and 18 print `26` and `17` instructions for `0x178c8` and `0x176d7`; the reached
   bodies are 183 and 294, because the panic cold block is shared.
7. Row 20 prints `178` instructions for `0x1ec6`; the reached body is 33, the rest of the
   span belongs to the neighbouring roots.

Still open after this tick, and left to P1-e: row 1b of the ledger, the declared `Accounts`
field name behind `accounts + 0x248` of the v2 body, and the three low-value pooled message
leaves of the recovery table (codes 6003 and 6011).

Severity: Informational
Sévérité : Informational
Severity justification: a read-only measurement and bookkeeping tick over the deployed bytes with no execution and no fund, admission, consensus or production effect.

## P1-e. The declared field behind `accounts+0x248` of the v2 struct is `bonding_curve`

Answer, stated once: the word at `accounts+0x248` of the `UpdateFeeSharesV2` accounts struct
is the declared field `bonding_curve`. The builder `0xf52a` stores it from the frame slot
`fp-0xb08` at `0xfd2d`; that slot has one writer, `0xf5fe`, fed by the fetch at `0xf5f9`
(`call 0x4a7`); the failure arm of that fetch prints rodata `0xc4d7c` with length `0xd`
(`bonding_curve`) through the message helper `0x2b1` and returns the tagged error at
`0xf619` to `0xf61c`. The same field then carries an Anchor seeds constraint whose seed
string is rodata `0xc4d6f` with length `0xd` (`bonding-curve`) under program id
`6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P` (the 32 bytes at `0xc4eed`), tested at
`0xf991` to `0xf9a4` and raised as code `0x7d6` at `0xf9a7`. Both halves of the marker left
by P1-a.4, offset and name, are settled by these rows.

### P1-e.1 The producer chain inside `0xf52a`

`0xf52a` is a function start of 2034 instructions and the only caller of it is `0x13981`,
inside the `update_fee_shares_v2` wrapper `0x1395a`, the same wrapper that calls the body
`0x673a` at `0x139ad`.

| # | insn | measured | tag |
|---:|---|---|---|
| 1 | `0xf5f9` | `call 0x4a7` with `out = fp-0x2e8`; `0xf5f9` is the only call row of `0x4a7` in the image | **[B]** |
| 2 | `0xf5fa`, `0xf5fb` | `r3 = [fp-0x2e0]` (the payload word of the fetch), `r2 = [fp-0x2e8]` (its tag word) | **[B]** |
| 3 | `0xf5fc` | `jeq r2, 0x2, +0x1`, target `0xf5fe`; this row is the only predecessor of `0xf5fe` | **[B]** |
| 4 | `0xf5fd` | `ja +0x13`, target `0xf611`; this row is the only predecessor of the name arm | **[B]** |
| 5 | `0xf5fe` | `stxdw [fp-0xb08], r3`, the single writer of that slot in the 2034 instructions of the builder | **[B]** |
| 6 | `0xfd2c`, `0xfd2d` | `ldxdw r5, [fp-0xb08]`, then `stxdw [r6+0x248], r5`; one store row to `accounts+0x248` in the builder and this is it | **[B]** |

The slot read at `0xfd2c` also has two readers in the verification phase of the same
function, `0xf991` and `0xf9b3`, which is where the seeds constraint of P1-e.4 sits.

### P1-e.2 The name arm of that fetch

| # | insn | measured | tag |
|---:|---|---|---|
| 1 | `0xf611`, `0xf612` | `mov64 r1, r10`, `add64 r1, -0x6c0`: the out block of the message | **[B]** |
| 2 | `0xf613` | `lddw r4, 0xc4d7c`, the string pointer | **[B]** |
| 3 | `0xf615` | `mov64 r5, 0xd`, the length immediate | **[B]** |
| 4 | `0xf616` | `call 0x2b1`, the same helper every other field name of this builder goes through (for example `0xf5ea` for `sharing_config` and `0xf60d` for `pump_creator_vault`) | **[B]** |
| 5 | `0xf617`, `0xf618` | `ldxdw r1, [fp-0x6c0]`, `ldxdw r2, [fp-0x6b8]`: the `(ptr, len)` pair back out | **[B]** |
| 6 | `0xf619` to `0xf61c` | `stxdw [r6+0x10], r2`, `stxdw [r6+0x8], r1`, `stw [r6+0x0], 0x2`, `exit`: the tagged `Err` return of the builder | **[B]** |

The 13 bytes at `0xc4d7c` are `bonding_curve`, which is the length the immediate at `0xf615`
carries. This is the arm of the step at `0xf5f9` and of no other step: its single
predecessor is `0xf5fd`, the branch taken on the tag test of that fetch.

The arm at `0xf60a` that P1-a.4 read as `pump_creator_vault` belongs to the next fetch, as
the measurement there said. Its fetch is `0xf602` (`call 0x353`), its tag test is `0xf606`
on the byte at `[fp-0x2be]`, its success branch is `0xf607` (`ja +0x15` to `0xf61d`), and
its string is rodata `0xc4e48` with length `0x12`, which the bytes spell `pump_creator_vault`.

### P1-e.3 The loader, and the parity row in the v1 builder

The fetch goes `0x4a7` to `0x226f` (`call` at `0x4aa`) to `0xdbb` (`call` at `0x2284`).
`0x226f` has four callers in the image, `0x4aa`, `0xd0c2`, `0xda30` and `0xeda5`, and
`0xdbb` has one caller, `0x2284`. `0xdbb` stages the 32-byte key at `[r7+0x18]` (`0xdbd`)
and compares it twice, at `0xdc2` against the 32 zero bytes at `0xc36a0` and at `0xdca`
against the 32 bytes at `0xc4eed`; only the second comparison continues into the record
tests at `0xdfa`. The 32 bytes at `0xc4eed` base58-encode to
`6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P`.

The v1 Context is built the same way for its own slot: fetch `0xeda5` (`call 0x226f`), the
tag test at `0xeda9` with the arm at `0xedad` printing `0xc4d7c`, the success store
`0xedb4` into `fp-0xe00`, and `0xf457`/`0xf458` storing that slot to `accounts+0x288`.
The builder of the v1 struct is `0xecba`, called once at `0x138fc` inside the
`update_fee_shares` wrapper `0x138d4`. So the two structs reach the same loader pair, the
same message string and the same key tests for this field, and the name that the v1 builder
prints for it is the name the v2 builder prints.

### P1-e.4 The seeds constraint on the same slot

The second phase of `0xf52a` derives the expected key of the field and compares it with the
key of the account the slot holds:

| # | insn | measured | tag |
|---:|---|---|---|
| 1 | `0xf962` to `0xf969` | the 32-byte key staged at `fp-0x308` from `[r8+0x00]` to `[r8+0x18]`: the first seed | **[B]** |
| 2 | `0xf96a` to `0xf971` | seed pointer `fp-0x308` at `fp-0x318` with length `0x20` at `fp-0x310`, seed pointer `0xc4d6f` at `fp-0x328` with length `0xd` at `fp-0x320` | **[B]** |
| 3 | `0xf972` to `0xf97d` | the four immediates of the program id stored at `fp-0x390` to `fp-0x378`; their bytes are the 32 bytes at `0xc4eed` | **[B]** |
| 4 | `0xf97e` to `0xf985` | `call 0x16f53` with the out block `fp-0x2e8`, the seed block `fp-0x328`, `r3 = 0x2` seeds and the program id at `fp-0x390`: the derived key | **[B]** |
| 5 | `0xf986` to `0xf98d` | the derived key moved to `fp-0x490` to `fp-0x478` | **[B]** |
| 6 | `0xf991` to `0xf9a1` | the slot `fp-0xb08` read again, the account key staged at `fp-0x2e8` to `fp-0x2d0`, and the 32-byte compare `call 0x184e6` with `r3 = 0x20` at `0xf9a0` | **[B]** |
| 7 | `0xf9a4` | `jeq r0, 0x0, +0x29`, target `0xf9ce`: equal answers and the constraint is satisfied | **[B]** |
| 8 | `0xf9a7` to `0xf9b0` | `mov64 r2, 0x7d6`, `call 0x1601e`, then `0xc4d7c` with length `0xd` through `0x2b1`: code 2006, the `ConstraintSeeds` code mapped in 2.4 (line 1622), raised under the field name | **[B]** |

The 13 bytes at `0xc4d6f` are `bonding-curve`, and the program id under which the key is
derived is the pump program id read above. The v1 builder runs the same block for
`accounts+0x288`: `0xf0e2` (`lddw r1, 0xc4d6f`), `0xf0f9` (`r3 = 0x2` seeds), `0xf0fa`
(`call 0x16f53`), `0xf106` (the slot `fp-0xe00` read), `0xf11b` (`0x7d6`) and `0xf121`
(`0xc4d7c`).

So the declared field that the v2 struct places at `accounts+0x248` is a pump bonding curve
account of the mint, held to the pump program id and to the `bonding-curve` seed, and it is
the field the builder calls `bonding_curve`.

### P1-e.5 What this tick closes

* Row 1b of the ledger, and with it the marker `[B offset, R name]` at the end of P1-a.4:
  the offset `accounts+0x248` keeps **[B]** and the name moves to **[B]**, on the rows above.
* The reconstruction in 7.3.2 that names `ctx.accounts.bonding_curve` at the `0x6a30`
  borrow and at the `0x250d` probe now stands on the builder rows of P1-e.1 to P1-e.4
  rather than on that name alone.
* Nothing else moves. The three pooled message leaves of the recovery table, codes 6003 and
  6011 at lines 123, 131 and 152 with their summary at 152, stay the next open row of this
  sublane. No row re-dug here is reopened.

Credit for the deployed bytes and for the source tree they were built from:
lalalune/pumpfun-source (MIT).

Severity: Informational
Sévérité : Informational
Severity justification: a static reading of the deployed bytes that names one struct field and its seeds constraint, with no execution and no fund, admission, consensus or production effect measured.

## P2-e. `global[0x158]`, the right operand of gate 307: the pump `Global` map, and why the offset is not a field [B map, TERMINAL name]

Scope of this tick: ledger row O2 only, the 32 bytes at `global[0x158]` that gate 307 compares a
second time at `0x56e8`/`0x56e9` (16.9.3). Nothing else in 16.9 is rewritten. Bytes read: the pump
program image and the `pump_fees` image of the same evidence set (both from the lalalune
`pumpfun-source` capture, MIT), the decoder `0x2c015` and its wrapper `0x2bfba` in the pump image,
the decoder `0x107c7` and its wrapper `0x1076c` and loader `0x111f` in the `pump_fees` image, the
borsh reader helpers `0x1f56`, `0x1a0d`, `0x1f78`, `0x205c`, `0x207e` (pump) and `0x1d5c`, `0x1958`,
`0x1d7e` (`pump_fees`), and the `try_accounts` sites `0xd9e9` and `0xde62`. Tools written this tick:
`scratch/p2e_find_disc.py`, `scratch/p2e_dis.py`, `scratch/p2e_cursor.py`, `scratch/p2e_cur2.py`,
`scratch/p2e_idl_map.py`, `scratch/p2e_disc_names.py`, checked by `scratch/p2e_verify.py`.

### P2-e.1 The discriminator is `account:Global`, in both images [B]

`0x7f726cc8b1e8e8a7` is the little endian encoding of `a7e8e8b1c86c727f`, which is
`sha256("account:Global")[0..8]` (`scratch/p2e_disc_names.py` recomputes the Anchor discriminator of
every account name tested in both IDLs; no other name collides). It is the only 64 bit immediate of that
value in the `pump_fees` image, at `0x10771`, and there are two in the pump image, at `0x77ad` and
`0x2bfbf`.

Three decoders read the same account:

| site | role | bound |
|---|---|---|
| pump `0x771b` | handler side loader, 629 insns, discriminator check at `0x77ad` | `0x7726 jgt r0, 0x7` (a length above the 8 byte discriminator) |
| pump `0x2bfba` | account wrapper, 82 insns, checks the discriminator at `0x2bfbf`, then `0x2c013 call -> 0x2c015` | tag stored at `0x2c010 stxb [r6+0x437], 0x2`, so the decoded struct is `0x438` = 1080 bytes |
| `pump_fees` `0x1076c` | account wrapper, 82 insns, checks at `0x10771`, then `0x107c5 call -> 0x107c7`; called from the loader `0x111f` at `0x1171` | tag stored at `0x107c2 stxb [r6+0x2db], 0x2`, so the mirror is `0x2dc` = 732 bytes |

### P2-e.2 The borsh field map of the pump `Global`, measured field by field [B]

The decoder `0x2c015` receives `r2` = the account data record, takes `r1 = [r2+0x00]` at `0x2c01d`
(the data pointer) and keeps its cursor in `fp-0x508` with the remaining length in `fp-0x500`. Every
field consumes a known number of bytes: scalars are read in line, and the key and array reads go
through five helpers whose own prologues fix their width (`0x1f56` and `0x205c` require `0x20`
remaining and `add64 r3, 0x20` before `stxdw [r2+0x00], r3`; `0x1f78` and `0x207e` step to `0xe0`,
seven 32 byte keys; `0x1a0d` does `add64 r3, -0x1` and `add64 r4, 0x1`, one byte). Walking that
graph (`scratch/p2e_cur2.py`) gives the field sequence below, cursor in data bytes with the struct
byte at `cursor - 8`:

| struct bytes | width | cursor cite (store to `fp-0x508`, or helper call) |
|---|---|---|
| `0x000` | 1 | `0x2c027 ldxb r8, [r1+0x8]`, cursor `0x8` at `0x2c020` |
| `0x001..0x021` | 32 | cursor `0x9` at `0x2c02b`, `0x29` at `0x2c035` |
| `0x021..0x041` | 32 | cursor `0x49` at `0x2c048` |
| `0x041` | 8 | `0x2c05c ldxdw r4, [r1+0x49]`, cursor `0x51` at `0x2c05f` |
| `0x049` | 8 | cursor `0x59` at `0x2c068` |
| `0x051` | 8 | cursor `0x61` at `0x2c071` |
| `0x059` | 8 | cursor `0x69` at `0x2c07a` |
| `0x061` | 8 | cursor `0x71` at `0x2c087` |
| `0x069..0x089` | 32 | `0x2c08c call 0x1f56`, cursor `0x91` |
| `0x089` | 1 | `0x2c0a1 call 0x1a0d`, cursor `0x92` |
| `0x08a` | 8 | cursor `0x9a` at `0x2c0c9` |
| `0x092` | 8 | cursor `0xa2` at `0x2c0d4` |
| `0x09a..0x17a` | 224 | `0x2c0d9 call 0x1f78`, cursor `0x182` |
| `0x17a..0x19a` | 32 | `0x2c0ed call 0x1f56`, cursor `0x1a2` |
| `0x19a..0x1ba` | 32 | `0x2c101 call 0x1f56`, cursor `0x1c2` |
| `0x1ba` | 1 | `0x2c115 call 0x1a0d`, cursor `0x1c3` |
| `0x1bb..0x1db` | 32 | `0x2c11f call 0x1f56`, cursor `0x1e3` |
| `0x1db..0x1fb` | 32 | `0x2c133 call 0x1f56`, cursor `0x203` |
| `0x1fb` | 1 | `0x2c147 call 0x1a0d`, cursor `0x204` |
| `0x1fc..0x2dc` | 224 | `0x2c151 call 0x1f78`, cursor `0x2e4` |
| `0x2dc` | 1 | `0x2c165 call 0x1a0d`, cursor `0x2e5` |
| `0x2dd..0x3bd` | 224 | `0x2c16f call 0x207e`, cursor `0x3c5` |
| `0x3bd` | 8 | cursor `0x3cd` at `0x2c186` |
| `0x3c5` | 8 | cursor `0x3d5` at `0x2c190` |
| `0x3cd..0x3ed` | 32 | `0x2c195 call 0x205c`, cursor `0x3f5` |
| `0x3ed` | 1 | `0x2c1a9 call 0x1a0d`, cursor `0x3f6` |
| `0x3ee` | 8 | cursor `0x3fe` at `0x2c1b7` |
| `0x3f6..0x416` | 32 | `0x2c1bc call 0x1f56`, cursor `0x41e` |
| `0x416` | 1 | `0x2c1d0 call 0x1a0d`, cursor `0x41f` |
| `0x417` | 1 | cursor `0x420` at `0x2c1dd` |

The sequence is the field order of the interface record for the pump `Global` account: a
`initialized` byte, two keys, five `u64`, a key, a `enable_migrate` byte, two `u64`, seven keys,
two keys, a bool, two keys, a bool, seven keys, a bool, seven keys, two `u64`, a key, a bool, a
`u64`, a key, a bool, a `u8`. Two shapes are fixed by this measurement and differ from the current
interface record: the deployed `buyback_fee_recipients` array is **seven** keys (`0x2c16f call
0x207e` consumes `0xe0`), not eight, which is why the measured total is `0x418` = 1048 bytes and not
the 1080 of the record, and the whole map is 32 bytes shorter from that field on. Every key boundary
in the measured map is therefore: `1, 33, 105, 154, 378, 410, 443, 475, 508, 733, 973, 1014`.

### P2-e.3 The reader is the `pump_fees` mirror, and the ctx image is that mirror, not the account [B]

The `pump_fees` reader walks the same bytes with the same widths (`scratch/p2e_cur2.py`, helper widths
`0x1d5c` = `0x20`, `0x1958` = `0x1`, `0x1d7e` = `0xe0`, each fixed by the helper prologue: `0x1d5e
jlt r1, 0x20`, `0x1d5f add64 r1, -0x20`; `0x195b add64 r3, -0x1`; `0x1d80` to `0x1dea add64 r0,
0xe0`). Cursor sequence: `0x8`, `0x9`, `0x29`, `0x49`, `0x51`, `0x59`, `0x61`, `0x69`, `0x71`,
`0x91` (`0x1083e`), `0x92` (`0x10853`), `0x9a`, `0xa2`, `0x182` (`0x10871`), `0x1a2` (`0x10885`),
`0x1c2` (`0x10899`), `0x1c3` (`0x108ad`), `0x1e3` (`0x108b7`), `0x203` (`0x108cb`), `0x204`
(`0x108df`), `0x2e4` (`0x108e8`). That is the first 732 bytes of the pump map of P2-e.2, field for
field, ending exactly on the boundary before `is_cashback_enabled`. The reader stops there: it does
not read the trailing fields of the pump account.

The 32 bytes that reach the gate are not those account bytes. The chain is three copies, each
measured:

1. `0x1189 stxdw [fp-0x338], r1`, `0x118a mov64 r1, r6`, `0x118b add64 r1, 0x18`,
   `0x118d mov64 r2, r10`, `0x118e add64 r2, -0x2d0`, `0x118f mov64 r3, 0x2cb`,
   `0x1190 call 0x184d9`: the loader copies `0x2cb` = 715 bytes of the decoder result into its own
   `out+0x18`. The decoder result base is `fp-0x2e0` (`0x1171 call 0x1076c` with `r1 = fp-0x2e0`),
   so the source is `body+0x10`, and the tag is at `body+0x2db`, so the copy is exactly the decoded
   field area of the mirror, 715 bytes.
2. `0xd9e9 mov64 r1, r10`, `0xd9ea add64 r1, -0x678`, `0xd9eb mov64 r2, r10`, `0xd9ec add64 r2,
   -0x950`, `0xd9ed mov64 r3, 0x2d3`, `0xd9ee call 0x184d9`: `try_accounts` copies `0x2d3` = 723
   bytes from the loader slot, whose `out+0x18` is `fp-0x950`, that is the 715 field bytes plus the
   tag byte and seven bytes past the mirror struct.
3. `0xde62 mov64 r1, r6`, `0xde63 add64 r1, 0x1b0`, `0xde65 add64 r2, -0x678`, `0xde66 mov64 r3,
   0x2d3`, `0xde67 call 0x184d9`: the tail store block lands those bytes at `ctx+0x1b0`.

Gate 307 reads `r2 = ctx+0x308` at `0x56e8`/`0x56e9` and compares 32 bytes (`0x56ec mov64 r3, 0x20`,
`0x56ed call 0x184e6`). `0x308 - 0x1b0 = 0x158`, so the operand is image byte `0x158`. Because the
image is the mirror and not the account, image byte `0x158` is a byte of the mirror struct, not a
byte of the pump `Global`.

### P2-e.4 What sits at image `0x158`: no borsh field of the pump `Global` sits there [B offsets, TERMINAL name]

Two independent readings agree that the number cannot be attached to a field name.

On the account side, the map of P2-e.2 has no boundary at `0x150` or at `0x158`: both fall inside
the fifth key of the `fee_recipients` array, which spans struct bytes `0x13a..0x15a` (314..346):
`0x150` is its byte 22 and `0x158` its byte 30. A 32 byte window at either offset crosses from
`fee_recipients[5]` into `fee_recipients[6]`.

On the reader side, the mirror keeps its pubkeys in one contiguous run. The stores of the decoder
into its own result (`r6`, image offset = `r6 offset - 0x10`) put the key heads at
`0x109b4 stxdw [r6+0x27]`, `0x109b2 stxdw [r6+0x47]`, `0x109b0 stxdw [r6+0x67]`, then the 209 byte
bulk copy of the seven key `fee_recipients` group (`0x10954 mov64 r1, r6`, `0x10955 add64 r1, 0x6f`,
`0x10958 mov64 r3, 0xd1`), then the single key heads at `0x109ae stxdw [r6+0x147]`, `0x109ac stxdw
[r6+0x167]`, `0x109aa stxdw [r6+0x187]`, `0x109a8 stxdw [r6+0x1a7]`, `0x109a6 stxdw [r6+0x1c7]`, and
the last seven key group at `0x10998` to `0x109a4`. Every head is on a `0x20` stride and the first
one is image `0x17`: image `0x17`, `0x37`, `0x57`, the seven slot run whose bulk copy starts at image
`0x5f`, then `0x137`, `0x157`, `0x177`, `0x197`, `0x1b7` and the last seven slot run. Image `0x158` is
one byte past the slot head at `0x157`, so the 32 bytes the gate compares are the last 31 bytes of
one mirror key plus the first byte of the next.

The two sides cannot both be right for a real key equality, and the bytes do not carry a table that
would settle which side is shifted by that one byte: the mirror struct is compiler ordered (its
`initialized` byte is stored at `0x10996 stxb [r6+0x2d8]`, i.e. image `0x2c8`, at the end of the
struct, and its bools sit at image `0x2c8` to `0x2ca`), so no source field order can be read off the
image offsets, and no string, relocation or type name in either image names a mirror field.

**Verdict for O2: TERMINAL.** The 32 bytes at `global[0x158]` are not a borsh field of the pump
`Global`; the offset is not a boundary of the pump layout (it lands inside `fee_recipients[5]`), and
inside the reading program's own struct it lands one byte past a pubkey slot head. The name of the
mirror field the gate reads therefore cannot be fixed from these bytes, and the row is not reopened.
What the row now carries instead of a name: the measured boundary set of the pump layout (P2-e.2),
the fact that the gate operand is an offset in the reader's struct (P2-e.3), and the two candidate
slots the offset straddles (P2-e.4). The sentence in 16.9.3 that "the bytes pin the offset but not
the identifier" is replaced by that statement: the bytes pin the offset and show that the offset is
not an identifier of the pump layout.

Severity: Informational
Sévérité : Informational
Severity justification: Static reading of the pump and pump_fees images only; the measured content of a 32 byte compare operand in one handler is corrected, with no behavior, fund or consensus effect measured.

## P1-f. Codes 6003 and 6011 both resolve to one 6-byte message, `format`

Answer, stated once: the ladder of `0x8dca` sends both codes to the same leaf row pair. `0x8e2a`
loads the string pointer `0xc45d5` into `r2`, `0x8e2c` loads the length `0x6` into `r3`, and the
six bytes are `format`. The row pair is read by `0x8e2d` (`ja +0x53` to `0x8e81`, `callx r4`), and
`0x8e2a` is the only `lddw` in the whole image that carries `0xc45d5`. What is pooled about those
six bytes is their placement inside the merged message blob; the entry itself is the declared
message of both variants, on the rows below.

### P1-f.1 The two paths through the ladder

The resolver is the 149-instruction function that starts at `0x8dca`, and the next function starts
at `0x8e83`. Its entry rows are `0x8dca` `mov64 r3, r1`, `0x8dcb` `ldxdw r1, [r2+0x20]`,
`0x8dcc` `ldxdw r2, [r2+0x28]`, `0x8dcd` `ldxdw r4, [r2+0x18]` and `0x8dce` `ldxw r2, [r3+0x0]`:
the word under test arrives by reference in `r1`, and the callee of the tail call is the word at
`+0x18` of the table at `[r2+0x28]`.

| code | word | search rows, with the direction each one takes | leaf rows |
|---:|---:|---|---|
| 6003 | 3 | `0x8dcf` not taken (3 <= 0x11), `0x8dd0` not taken (3 <= 8), `0x8dd1` not taken (3 <= 3), `0x8dd2` taken (3 > 1, target `0x8e29`), `0x8e29` not taken (3 != 2, so the fallthrough continues) | `0x8e2a`, `0x8e2c`, `0x8e2d` |
| 6011 | 11 | `0x8dcf` not taken (11 <= 0x11), `0x8dd0` taken (11 > 8, target `0x8de7`), `0x8de7` not taken (11 <= 0x12), `0x8de8` taken (11 > 0xa, target `0x8e24`), `0x8e24` taken (11 == 0xb, target `0x8e2a`) | `0x8e2a`, `0x8e2c`, `0x8e2d` |

Two rows keep the neighbours of those two codes apart, and each of them is the row that decides
whether the shared leaf is reached. `0x8e29` is `jeq r2, 0x2, +0x21`: taken for 6002, straight to
`0x8e4b`, which loads `0xc45c0` with length `0x15`. `0x8e24` is `jeq r2, 0xb, +0x5`: taken for
6011, target `0x8e2a`, and not taken for 6012, which then loads `0xc46f9` with length `0x1d` at
`0x8e25` and `0x8e27`. So the 6003 leaf is the fallthrough of the 6002 test and the 6011 leaf is
the taken side of the 6011 test, and both are the same two instructions.

Every leaf of the ladder ends the same way: `0x8e2d` `ja +0x53` reaches `0x8e81` `callx r4`, the
indirect call whose callee was staged in `r4` at `0x8dcd`, with the string pointer in `r2` and the
length in `r3`. `0x8e82` `exit` closes the function.

The word under test is the variant number and not the wire code: the call sites that stage a
constant pass a pointer to a 4-byte word of this image's small integer pool, for example `0x8145`
`lddw r1, 0xc3e68` with the word `6` at `0xc3e68` and the call at `0x8147`, which renders the leaf
`0xc4649` with length `0x23` (`Fee total must not exceed 10_000bps`). The variant numbers line up
with the codes as 2.2 measured them: variant 1 is `0xc45b3` with length `0xd` (`Invalid admin`),
the text of 6001. Variant 3 is therefore 6003 and variant 11 is 6011.

### P1-f.2 The six bytes, and the blob they sit in

| va | len | bytes | leaf of |
|---|---:|---|---|
| `0xc45c0` | `0x15` | `No fee tiers provided` | 6002 |
| `0xc45d5` | `0x6` | `format` | 6003 and 6011 |
| `0xc45db` | `0x32` | `The offset should be <= fee_config.fee_tiers.len()` | 6004 |

The three windows are consecutive: `0xc45c0` plus `0x15` is exactly `0xc45d5`, and `0xc45d5` plus
`0x6` is exactly `0xc45db`. The message strings of this image are packed one after the next with no
padding and no terminator, which is why a 16-byte read at `0xc45d5` shows `format` followed by the
first bytes of the 6004 message and why the first ledger tick read the entry as an artifact of a
pool. The literal `format` occurs twice in the image: at `0xc45d5`, which is this leaf, and at
`0xc7921`, inside the longer phrase `a formatting trait imp`, which is a different string and which
no ladder row references.

### P1-f.3 One leaf for two codes, and the (pointer, length) form of every string here

The ladder holds 36 distinct leaves for the 40 codes 6000 to 6039. Two of those leaves carry more
than one code: `0xc45d5` with length `0x6` carries 6003 and 6011, and `0xc4a11` with length `0x13`
(`Nothing to withdraw`) carries 6036, 6037, 6038 and 6039. A shared leaf is what a constant merge
of two equal (pointer, length) pairs looks like in this image, and the two pairs appear as such in
the IDL of the program: entry 6003 `TooManyFeeTiers` and entry 6011 `TooManyShareholders` carry the
message `format`, and no other entry of that file carries it.

The same (pointer, length) form stores every string this image reports. The four raise rows of the
two codes build their Anchor `Location` record that way, each with the file pointer, the length of
the file path and the source line:

| raise row | code stored | file pointer | length row | line row | file string |
|---|---|---|---|---|---|
| `0x811d` | `0x1773` = 6003 | `lddw r1, 0xc455b` at `0x811a` | `0x1f` at `0x8120` | `0x195` = 405 at `0x811f` | `programs/pump-fees/src/state.rs` |
| `0x8325` | `0x1773` = 6003 | `lddw r1, 0xc455b` at `0x8322` | `0x1f` at `0x8328` | `0x1ca` = 458 at `0x8327` | `programs/pump-fees/src/state.rs` |
| `0x653d` | `0x177b` = 6011 | `lddw r1, 0xc4432` at `0x653a` | `0x44` at `0x6540` | `0x103` = 259 at `0x653f` | `programs/pump-fees/src/instructions/fee_sharing/update_fee_shares.rs` |
| `0x6f14` | `0x177b` = 6011 | `lddw r1, 0xc4476` at `0x6f11` | `0x47` at `0x6f17` | `0x125` = 293 at `0x6f16` | `programs/pump-fees/src/instructions/fee_sharing/update_fee_shares_v2.rs` |

Each length equals the byte count of the path it delimits (`0x1f` = 31, `0x44` = 68, `0x47` = 71),
the three paths sit back to back in the same blob (`0xc4432` plus 68 is exactly `0xc4476`), and the
pointer alone cannot name a string here, the length does. The leaf of 6003 and 6011 is read in
exactly that form, `0xc45d5` with `0x6`, and the pair spells the message.

The raise rows sit in four functions: `0x7fd7` and `0x81df` for the two `state.rs` rows, `0x6479`
for the v1 shareholder set validator and `0x6e50` for the v2 side. Each stores the wire code as an
immediate in its error record next to that `Location` record, and the text a client renders for the
code is produced by the ladder rows of P1-f.1.

### P1-f.4 The declared message, and the reading this section supersedes

The recovered source of the same tree puts the message in the attribute of each variant:
`TooManyFeeTiers = 3` and `TooManyShareholders = 11` both read `#[msg("format")]` (**[R]** for the
source form), and the IDL entry of the deployed image agrees, `format` for 6003 and 6011 and for no
other code (**[R]**, `evidence/upstream/pump_fees.json`). So the six bytes are the declared message
text, four rows of the ladder and one declaration agree on it, and the sentence of 2.2 that reads
the entry as a string-pool artifact rather than a message is superseded here, once and in this
place: the placement of the six bytes is pooled, the entry is not.

What the two codes carry on the wire is a 6-byte message that names nothing: an instruction
rejected with 6003 or 6011 stores `0x1773` or `0x177b` in the error record of the rows in P1-f.3,
and the text the ladder renders for it is `format`. No offset, no predicate, no account reading and
no control flow depends on the text; the codes stay distinct, so a client that reports the numeric
code loses nothing, and a client that reports the message text reports a word with no diagnostic
content.

### P1-f.5 What this tick closes

* Rows 2 and 3 of the ledger, the leaves of codes 6003 and 6011 at 2.2 lines 123 and 131, and row
  4, the summary sentence at line 152. The three open markers flip in place to `[B] (closed in
  P1-f)` and nothing else on those three lines moves.
* The count of open markers in the deliverable moves from 85 to 82, three fewer and no other
  change.
* With this item the ledger of this sublane has no OPEN row left: row 1 closed in P1-a, row 1b
  closed in P1-e, and the two leaves with their summary close here. Nothing re-dug here is
  re-opened and nothing new is left open.

Credit for the deployed bytes, for the source form and for the IDL: lalalune/pumpfun-source (MIT).

Severity: Informational
Sévérité : Informational
Severity justification: a static reading of the deployed bytes that names the text two error codes render, with no execution and no fund, admission, consensus or production effect measured.

## P2-f. The `ctx` region `0x113` to `0x147`: the `pump_event_authority` record, its nine stores, and the five bytes the step 8 reader never writes [B, row 5979 closed]

Scope of this tick: ledger row 5979 only, the row the P2-a.3 region table left open when it wrote
`0x114` to `0x147` as one block. The handler body, the `SharingConfig` initialisation and the gates
are not re-walked here; 16.9.3 is used as given for the `bonding_curve` image offsets. Bytes read
this tick: `tools/fees_body.py 0xd95d` and `tools/sbftool.py dis` over the windows `0xda30` to
`0xdaa0`, `0xdbb` to `0xe40`, `0x353` to `0x386`, `0x4ff` to `0x540`, `0x58b0` to `0x5960`, `0x5a40`
to `0x5a90` and `0x13810` to `0x13850`; the store and load censuses are `scratch/p2f_census.py`.
Every address and every arithmetic claim below is re-checked mechanically by
`scratch/p2f_verify.py` (173 assertions, PASS). The 48 byte `AccountInfo` shape used as the field
names is the one 4.4 and `docs/account_layouts.md` record, and it comes off the reconstruction tree
(lalalune/pumpfun-source, MIT).

### P2-f.1 The extent: the record begins at `0x118`, and `0x113` to `0x117` carries no writer [B]

The store census of the tail block `0xde3a` to `0xdeae` splits the run into four parts, and one of
them carries no writer:

| ctx range | size | what it is | writer rows |
|---|---:|---|---|
| `0xe8` to `0x112` | 0x2b | the `event_authority` field, one record by value, already `[B]` in P2-a.3 | `0xdea3`, `0xdea1`, `0xde9f`, `0xde9d`, `0xde9b`, `0xde75`, `0xde73`, `0xde71` |
| `0x113` to `0x117` | 5 | trailing padding of that record: no store, no copy | none |
| `0x118` to `0x147` | 0x30 | the `pump_event_authority` record, field 8 | the nine stores of P2-f.2 |
| `0x148` to `0x19f` | 0x58 | `bonding_curve`, already `[B]` in P2-a.3 and 16.9.3 | `0xde93`, `0xde91`, `0xde6d`, `0xdead`, `0xdeac` |

The two boundaries are alignment arithmetic on the 48 byte shape: `0xe8 + 0x2b = 0x113`, the next 8
aligned offset is `0x118`, and `0x118 + 0x30 = 0x148`, which is exactly where the first store of the
`bonding_curve` field lands (`0xde92 ldxdw r3, [r10 -0xca8]` then `0xde93 stxdw [r6 +0x148], r3`).

What the census rules out for the 5 byte gap:

* no store of `0xd95d` lands in `0x113` to `0x117`. The last stores below it are the three flag
  bytes at `0xde71 stxb [r6 +0x110], r3`, `0xde73 stxb [r6 +0x111], r3` and
  `0xde75 stxb [r6 +0x112], r3`, and the next store is `0xde99 stxdw [r6 +0x118], r3`.
* none of the five copies of the same function reaches it: `0xde40` copies `0x80` bytes to `0x68`,
  `0xde46` copies `0x48` to `0x18`, `0xde61` copies `0x30` to `0x488`, `0xde67` copies `0x2d3` to
  `0x1b0` and `0xde6d` copies `0x41` to `0x158`, so the covered ranges are `0x68` to `0xe7`, `0x18`
  to `0x5f`, `0x488` to `0x4b7`, `0x1b0` to `0x482` and `0x158` to `0x198`.
* the only bytes that reach `ctx+0x113` to `ctx+0x117` are the wrapper bulk leg
  `0x1382f add64 r1, -0xbb8`, `0x13831 add64 r2, -0x5d0`, `0x13832 mov64 r3, 0x5d0`,
  `0x13833 call 0x184d9`, which copies struct bytes `0x18` to `0x5e7` forward, uninitialised stack
  bytes included.
* the handler body never reads them: `0x56c7` carries no load with `[r7 +0x113]` to `[r7 +0x117]`.

So the row is right about its end and one byte late about its start: `0x114` to `0x117` are the last
four padding bytes, and the record runs `0x118` to `0x147`. The pad is the same 5 byte tail the
48 byte shape gives the `event_authority` record at `0xe8` (which this function simply does not
store), and the two records are `0x30` apart.

### P2-f.2 The nine stores: width, writer row, source window offset, sub-field [B]

Every store of the record reloads one frame slot that the step 8 block filled from the shared out
window at `fp-0x960`. The source offset is `0x960` minus the slot, and each slot is written exactly
once inside `0xd95d` (staging rows in the fourth column).

| ctx | width | load row | store row | frame slot (staging row) | window offset | sub-field |
|---|---:|---|---|---|---:|---|
| `0x118` | 8 | `0xde98` | `0xde99` | `fp-0xcd8` (`0xda88`) | `+0x00` | key, word 0 |
| `0x120` | 8 | `0xde96` | `0xde97` | `fp-0xcc8` (`0xda89`) | `+0x08` | lamports, word 1 |
| `0x128` | 8 | `0xde94` | `0xde95` | `fp-0xcd0` (`0xda95`) | `+0x10` | data, word 2 |
| `0x130` | 8 | `0xde48` | `0xde49` | `fp-0x2b8` (`0xda8b`) | `+0x18` | owner, word 3 |
| `0x138` | 8 | `0xde4a` | `0xde4b` | `fp-0x2b0` (`0xda8d`) | `+0x20` | rent_epoch, word 4 |
| `0x140` | 2 | `0xde4c ldxh` | `0xde4d stxh` | `fp-0x2a8` (`0xda8f`) | `+0x28` | is_signer at `0x140` and is_writable at `0x141`, copied as one halfword |
| `0x142` | 1 | `0xde76` | `0xde77` | `fp-0xce0` (`0xda87`) | `+0x2a` | executable, and the tag slot of the step 8 read |
| `0x143` | 4 | `0xde50 ldxw` | `0xde51 stxw` | `fp-0x2c0` (`0xda91`) | `+0x2b` | no source field in the step 8 reader |
| `0x147` | 1 | `0xde4e ldxb` | `0xde4f stxb` | `fp-0x2bc` (`0xda93`) | `+0x2f` | no source field in the step 8 reader |

The staging rows are the whole of the step 8 block `0xda87` to `0xda95`, and they read the window at
`+0x00` (`0xda87` gets `r2`, set at `0xda71`), `+0x08` (`r3`, set at `0xda70`), `+0x10`
(`0xda94 ldxdw r1, [r10 -0x950]`), `+0x18` (`0xda8a ldxdw r1, [r10 -0x948]`), `+0x20`
(`0xda8c ldxdw r1, [r10 -0x940]`), `+0x28` as a halfword (`0xda8e ldxh r1, [r10 -0x938]`), `+0x2a`
(`0xda72 ldxb r1, [r10 -0x936]`, the byte tested at `0xda73`), `+0x2b` as a word
(`0xda90 ldxw r1, [r10 -0x935]`) and `+0x2f` as a byte (`0xda92 ldxb r1, [r10 -0x931]`).

Consumers, so the names are attached to bytes something reads: the block is cloned into the two
`pump_amm` CPI account vectors at `0x5929` (key), `0x5923` (lamports), `0x5937` (data), `0x5954`
(owner), `0x5953` (rent_epoch), `0x5951` (is_signer), `0x594f` (is_writable) and `0x594d`
(executable), with the second walk at `0x5a4f`, `0x5a49`, `0x5a5d`, `0x5a7a`, `0x5a79`, `0x5a77`,
`0x5a75` and `0x5a73` (P11 and P13 of the 16.3 phase map). The last two rows of the table have no
reader at all: no load of `[r7 +0x143]` to `[r7 +0x147]` exists in `0x56c7`.

### P2-f.3 The reader writes `0x2b` bytes, the record is `0x30` [B]

Step 8 calls the `Option<Account>` reader `0x353` with the window as its out pointer
(`0xda6c mov64 r1, r10`, `0xda6d add64 r1, -0x960`, `0xda6e mov64 r2, r9`, `0xda6f call 0x353`).
That reader writes eight stores and stops at `+0x2a`:

| window | cite | value |
|---|---|---|
| `+0x00` | `0x384 stxdw [r6 +0x0], r2` | entry word 0 |
| `+0x08` | `0x383 stxdw [r6 +0x8], r1` | entry word 1 |
| `+0x10` | `0x382 stxdw [r6 +0x10], r4` | entry word 2, after the two borrow counter increments of `0x367` to `0x377` |
| `+0x18` | `0x381 stxdw [r6 +0x18], r0` | `[entry +0x18]`, `0x37a` |
| `+0x20` | `0x380 stxdw [r6 +0x20], r7` | `[entry +0x20]`, `0x37b` |
| `+0x28` | `0x37f stxb [r6 +0x28], r8` | `[entry +0x28]`, `0x37c` |
| `+0x29` | `0x37e stxb [r6 +0x29], r3` | `[entry +0x29]`, `0x37d` |
| `+0x2a` | `0x385 stxb [r6 +0x2a], r5` | `[entry +0x2a]` on the present arm (`0x379`), the immediate `0x2` on the missing arm (`0x35e`) |

So the reader's out struct is `0x2b` bytes, which is the same shape the sibling
`Option<Account>` reader of field 11 uses: `0x4ff` writes `+0x28` and `+0x29` at `0x532` and `0x531`,
its tag at `0x53f stxb [r6 +0x2a], r3` with the immediate `0x3` on its missing arm (`0x50b`), and
nothing past `+0x2a`.

The destination record is `0x30` bytes, one byte wider on each of its last two stores than the
reader's shape. Bytes `0x118` to `0x142` are the record the reader produced (`0x2b` bytes), and bytes
`0x143` to `0x147` are window bytes `+0x2b` to `+0x2f` that this reader never writes. The copy at
`0xda90`/`0xda92` reads them anyway, so the record's trailing 5 bytes are the padding of the 48 byte
shape, filled from whatever the shared window held.

### P2-f.4 The five bytes are the `bonding_curve` decode left in the shared window [B]

Every reader in `try_accounts` is called with the same out window `fp-0x960`, so the bytes no reader
writes keep the value of the previous read. The order of the steps before the copy at `0xda90` is:

| step | row | what it writes in the window |
|---:|---|---|
| 6 `bonding_curve` | `0xda30 call 0x226f`, ok arm at `0xda35 ja` to `0xda56` | the decoder `0xdbb` copies `0x39` bytes to `+0x18` (`0xe26 mov64 r1, r6`, `0xe27 add64 r1, 0x18`, `0xe2a add64 r2, -0x40`, `0xe2b mov64 r3, 0x39`, `0xe2c call 0x184d9`), then `+0x10`, `+0x08`, `+0x00` at `0xe33`, `0xe35`, `0xe36` |
| 7 `pump_program` | `0xda66 call 0x23e9` | `+0x00` and `+0x08` only (`0x2429`, `0x2428`, `0x2404`), and no call to the copy helper `0x184d9` anywhere in its body |
| 8 `pump_event_authority` | `0xda6f call 0x353` | `+0x00` to `+0x2a`, P2-f.3 |

The `0x39` byte copy of step 6 covers window `+0x18` to `+0x50`, which contains `+0x2b` to `+0x2f`,
and neither of the two later reads writes those bytes. At `0xda90` the window bytes `+0x2b` to
`+0x2f` therefore still hold the step 6 decode, at image offsets `0x23` to `0x27` under the image
base `out+0x08` of 16.9.3.

The same window bytes also reach `ctx` legitimately in step 6, through the `0x41` byte copy
`0xda5a add64 r1, -0x308`, `0xda5c add64 r2, -0x950`, `0xda5d mov64 r3, 0x41`, `0xda5e call
0x184d9` from window `+0x10` to `fp-0x308`, and the tail copy `0xde69 add64 r1, 0x158`,
`0xde6b add64 r2, -0x308`, `0xde6c mov64 r3, 0x41`, `0xde6d call 0x184d9` to `ctx+0x158`. Since
`ctx+0x158` is image `0x08`, image `0x23` is `ctx+0x173` and image `0x27` is `ctx+0x177`. So on
every successful instruction, `ctx+0x143` to `ctx+0x147` holds the same five bytes as `ctx+0x173`
to `ctx+0x177`, and the tail of the record duplicates five bytes of the `bonding_curve` image.

The chain is deterministic and not a race: the `bonding_curve` account is not optional, its missing
arm raises at `0xda34 jeq r1, 0x2` to `0xda36`, so an instruction that reaches the step 8 copy has
already run the step 6 copy at `0xda5e` and the decoder copy at `0xe2c`. The five bytes carry no
information of their own and no instruction reads them.

### P2-f.5 What this closes

Row 5979 is closed on the bytes. The split the row asked for is not one between a record header and
a `bonding_curve` head inside `0x114` to `0x147`: the record is `0x118` to `0x147`, its first `0x2b`
bytes are the step 8 read, and its last 5 bytes are padding filled from the shared window, where they
hold five bytes of the `bonding_curve` image that also land at `ctx+0x173` to `ctx+0x177`. The
`bonding_curve` field itself starts at `0x148`.

Three corrections to carry, none of them a new row:

1. the region of the P2-a.3 row starts at `0x113`, not at `0x114`: `0x113` to `0x117` is the
   padding of the `event_authority` record, and it has no writer and no reader.
2. the row lists `0xde7d` among the writers of the region. That store is
   `0xde7d stxw [r6 +0x484], r3`, the `u32` of the `global` field, and it belongs to the P2-a.3 row
   for `0x1a0` to `0x487`.
3. the row reads the region as "the record header plus the head of the `bonding_curve` field". The
   field boundary is the store pair `0xde92` and `0xde93` at `0x148`; only five bytes of the
   `bonding_curve` image sit inside the record.

What stays open in this sublane: row 5982 (the name link of `ctx+0x488` to `0x4b7`) and row 6025
(the internal reading of the `0x68` byte tail at `ctx+0x80` to `0xe7`).

Severity: Informational
Sévérité : Informational
Severity justification: A static reading of one accounts struct that fixes nine store rows and shows five padding bytes are filled from a shared window; no execution and no behaviour, fund, admission or consensus effect is measured.

## P2-g. The `ctx` block `0x488` to `0x4b7`: one `AccountInfo` by value, its nine stores, and the name string of the step 11 read [B, row 5982 closed]

Scope of this tick: ledger row 5982 only, the row the P2-a.3 region table opened for the block
`0x488` to `0x4b7` of `create_fee_sharing_config`, whose name link it could only call positional.
The handler body, the `SharingConfig` initialisation and the gates are not re-walked here; 16.9.3 and
P2-f are used as given for the shared out window and for the readers around this one. Bytes read
this tick: the windows `0xda0e` to `0xdb00`, `0x4ff` to `0x540`, `0x2b1` to `0x2d0`, `0x353` to
`0x386`, `0x541` to `0x56b`, `0x56c` to `0x590`, `0x1ec6` to `0x1ee6`, `0x226f` to `0x2286`,
`0x2314` to `0x2341`, `0xdbb` to `0xe40`, `0x5c5c` to `0x5cc2`, `0x13810` to `0x13830` and
`0x184d9` to `0x184ee`, plus the strings at `0xc4da8`, `0xc41b8` and `0xc5217`. The store and load
censuses are `scratch/p2g_census.py`, the register walk is `scratch/p2g_reg.py`, and every address
and every arithmetic claim below is re-checked mechanically by `scratch/p2g_verify.py` (226
assertions, PASS). The 48 byte `AccountInfo` shape used as the field names is the one 4.4 and
`docs/account_layouts.md` record, and it comes off the reconstruction tree (lalalune/pumpfun-source,
MIT).

### P2-g.1 The block, its copy row and the object it copies [B]

The block has exactly one writer: the copy `0xde5c mov64 r1, r6`, `0xde5d add64 r1, 0x488`,
`0xde5e mov64 r2, r10`, `0xde5f add64 r2, -0x1a8`, `0xde60 mov64 r3, 0x30`,
`0xde61 call 0x184d9`, the `sol_memcpy_` helper. None of the four other copies of the same function
reaches that range: `0xde40` covers `0x68` to `0xe7`, `0xde46` covers `0x18` to `0x5f`, `0xde67`
covers `0x1b0` to `0x482` and `0xde6d` covers `0x158` to `0x198`.

The source is the frame object `fp-0x1a8` to `fp-0x179`, `0x30` bytes, assembled by nine stores of
`0xd95d` at `0xdae9` to `0xdaf8`. Those nine stores are the whole of the frame range: the store
census of `0xd95d` between `fp-0x1a8` and `fp-0x178` returns exactly nine rows, and their ranges
tile `fp-0x1a8` to `fp-0x178` with no hole. So the block is not a slice of the shared window and it
is not a slice of any other `ctx` field: it is one frame object, staged and then copied once.

### P2-g.2 The name link: the read that fills the block carries the name string [B]

Row 5982 left the name open because the copy itself carries no string. The bytes settle it at the
read, not at the copy. The step 11 read is called at `0xdac0` to `0xdac4`
(`0xdac0 ldxdw r2, [r10 -0x970]`, `0xdac1 mov64 r1, r10`, `0xdac2 add64 r1, -0x960`,
`0xdac3 mov64 r3, r9`, `0xdac4 call 0x4ff`), and `0xdac4` is the only call site of `0x4ff` in the
image. Its three immediate successors dispatch on the byte it leaves in the window:

| row | instruction | what it does |
|---|---|---|
| `0xdac5` | `ldxdw r3, [r10 -0x958]` | reload window `+0x08` |
| `0xdac6` | `ldxdw r2, [r10 -0x960]` | reload window `+0x00` |
| `0xdac7` | `ldxb r9, [r10 -0x936]` | reload window `+0x2a`, the tag byte |
| `0xdac8` | `jeq r9, 0x3, +0x1` to `0xdaca` | the count zero arm of the read |
| `0xdac9` | `ja +0x1f` to `0xdae9` | every other arm, the staging of P2-g.4 |

The `0xdaca` arm is the diagnostic of this read, and it names it:

| row | instruction | value |
|---|---|---|
| `0xdaca` | `mov64 r1, r10` | buffer |
| `0xdacb` | `add64 r1, -0xbb0` | buffer |
| `0xdacc` | `lddw r4, 0xc4da8` | the string |
| `0xdace` | `mov64 r5, 0x18` | 24 bytes |
| `0xdacf` | `call 0x2b1` | log the string, return the read's error |

The twenty four bytes at `0xc4da8` are `pump_amm_event_authority` and the length `0x18` is exactly
24, so the logged span is the whole name and nothing else. The two words the read left at window
`+0x00` and `+0x08` are then carried out as the error payload (`0xdad0 ldxdw r1, [r10 -0xbb0]`,
`0xdad1 ldxdw r2, [r10 -0xba8]`, then `0xdad2` to `0xdad6`), which is the code `0xbbd` = 3005, the
not enough keys code that the count zero arm of `0x4ff` built at `0x503` to `0x506`.

The neighbouring read proves that the strings sit one per read and not one per error path: the
`pump_amm_program` read at `0xdaba` has its own arm at `0xdad9`, `0xdadb lddw r4, 0xc41b8`,
`0xdadd mov64 r5, 0x10`, and `0xc41b8` reads `pump_amm_program`, sixteen bytes, exactly `0x10`.
So the string at `0xdacc` belongs to the read at `0xdac4`, the read whose out record the staging at
`0xdae9` reloads and the block at `ctx+0x488` receives. The name link of row 5982 is a string link:
the block is the record of the account the code names `pump_amm_event_authority`.

### P2-g.3 The read `0x4ff`: three arms, `0x2b` bytes of out, and a key comparison [B]

Signature, read off the body: `0x4ff mov64 r8, r3` (the slice iterator), `0x500 mov64 r6, r1` (the
out pointer), `[r8 +0x0]` the current element pointer (`0x50d ldxdw r9, [r8 +0x0]`), `[r8 +0x8]` the
remaining count (`0x501 ldxdw r7, [r8 +0x8]`), element stride `0x30` (`0x518 add64 r1, 0x30` and
`0x53c add64 r9, 0x30`), and the two `Rc` borrow counter increments of `0x51a` to `0x52b`.

| arm | rows | what it writes in out |
|---|---|---|
| count zero | `0x503` to `0x50c`: `0x1601e` error builder with `0xbbd`, then `0x509 stxdw [r6 +0x8]`, `0x50a stxdw [r6 +0x0]`, `0x50b mov64 r3, 0x3` | `+0x00`, `+0x08` and the tag `+0x2a` = 3 |
| key equal | `0x50e ldxdw r1, [r9 +0x0]`, `0x510 mov64 r3, 0x20`, `0x511 call 0x184e6`, `0x514 jeq r0, 0x0, +0x25` to `0x53a`, then `0x53e mov64 r3, 0x2` | the tag `+0x2a` = 2 and nothing else; the element is consumed first (`0x53a`, `0x53c`, `0x53d`) |
| present | `0x52c` to `0x538`, tag at `0x53f` | the eight entry fields and the tag `+0x2a` = `[entry +0x2a]` |

`0x184e6` is a `sol_memcmp_` wrapper: `0x184e6 stw [r10 -0x4], 0x0`, `0x184e7 mov64 r4, r10`,
`0x184e8 add64 r4, -0x4`, `0x184e9 call` (the relocation names `sol_memcmp_`), `0x184ea ldxw r0,
[r10 -0x4]`, two sign extend shifts and `exit`, so `r0 == 0` means the two 32 byte operands are
equal. The second operand is the pointer the read received in `r2`, which is the second argument of
`0xd95d`: `0xd95f stxdw [r10 -0x970], r2` saves it once in the whole image, and `0xdac0` reloads it
for this read. The wrapper hands its own second argument through at `0x13812 mov64 r7, r2`,
`0x13826 mov64 r2, r7`, `0x13827 call 0xd95d`.

The out record of the read is `0x2b` bytes. The store census of `0x4ff` returns ten stores with a
maximum end offset of `0x2b`, covering `0x00` to `0x2a` with no hole and writing nothing in
`0x2b` to `0x2f`. The eight entry loads and the eight out stores are:

| out | cite | entry offset |
|---|---|---|
| `+0x00` | `0x538 stxdw [r6 +0x0], r1`, value reloaded at `0x537` from `fp-0x18` | `+0x00`, loaded at `0x50e` |
| `+0x08` | `0x536 stxdw [r6 +0x8], r1` | `+0x08`, loaded at `0x51a` |
| `+0x10` | `0x535 stxdw [r6 +0x10], r2` | `+0x10`, loaded at `0x523` |
| `+0x18` | `0x534 stxdw [r6 +0x18], r4` | `+0x18`, loaded at `0x52d` |
| `+0x20` | `0x533 stxdw [r6 +0x20], r5` | `+0x20`, loaded at `0x52e` |
| `+0x28` | `0x532 stxb [r6 +0x28], r0` | `+0x28`, loaded at `0x52f` |
| `+0x29` | `0x531 stxb [r6 +0x29], r7` | `+0x29`, loaded at `0x530` |
| `+0x2a` | `0x53f stxb [r6 +0x2a], r3` | `+0x2a`, loaded at `0x52c`, on the present arm only |

So the answer to the question the row asked: the copied block is neither the out record of the read
nor a wider slice of it. It is a separate frame object of `0x30` bytes whose first `0x2b` bytes
reload the out record of `0x4ff` from the shared window, and whose last five bytes are window bytes
that read never writes.

### P2-g.4 The nine stores: width, source and sub-field [B]

Each row is one store of the staging block `0xdae9` to `0xdaf8`, and its source is one window offset,
taken as `0x960` minus the frame slot. The block offset is `0x1a8` minus the frame slot.

| ctx | width | store row | source load row | frame slot | window | sub-field |
|---|---:|---|---|---|---:|---|
| `0x488` | 8 | `0xdaf8 stxdw` | `0xdac6 ldxdw r2, [r10 -0x960]` | `fp-0x1a8` | `+0x00` | key |
| `0x490` | 8 | `0xdaf6 stxdw` | `0xdac5 ldxdw r3, [r10 -0x958]` | `fp-0x1a0` | `+0x08` | lamports, the `Rc` word |
| `0x498` | 8 | `0xdaf0 stxdw` | `0xdaef ldxdw r1, [r10 -0x950]` | `fp-0x198` | `+0x10` | data, the `Rc` word |
| `0x4a0` | 8 | `0xdaee stxdw` | `0xdaed ldxdw r1, [r10 -0x948]` | `fp-0x190` | `+0x18` | owner |
| `0x4a8` | 8 | `0xdaec stxdw` | `0xdaeb ldxdw r1, [r10 -0x940]` | `fp-0x188` | `+0x20` | rent_epoch |
| `0x4b0` | 2 | `0xdaea stxh` | `0xdae9 ldxh r1, [r10 -0x938]` | `fp-0x180` | `+0x28` | is_signer at `0x4b0` and is_writable at `0x4b1`, one halfword |
| `0x4b2` | 1 | `0xdaf5 stxb` | `0xdac7 ldxb r9, [r10 -0x936]` | `fp-0x17e` | `+0x2a` | executable on the present arm, the tag `2` or `3` on the read's other two arms |
| `0x4b3` | 4 | `0xdaf2 stxw` | `0xdaf1 ldxw r1, [r10 -0x935]` | `fp-0x17d` | `+0x2b` | no source in this read |
| `0x4b7` | 1 | `0xdaf4 stxb` | `0xdaf3 ldxb r1, [r10 -0x931]` | `fp-0x179` | `+0x2f` | no source in this read |

The widths sum to `0x30` and the nine ranges tile the block with no hole: `0x00`, `0x08`, `0x10`,
`0x18`, `0x20`, `0x28` (2), `0x2a` (1), `0x2b` (4), `0x2f` (1). The block is therefore the plain 48
byte `AccountInfo` by value: five 8 byte words, the three flag bytes at `0x28`, `0x29` and `0x2a`,
and five bytes of alignment padding at `0x2b` to `0x2f`. That is the same shape P2-f measured for
the `pump_event_authority` record at `0x118`, and the same padding tail.

### P2-g.5 The five bytes at `0x4b3` to `0x4b7`: no source in the read, the pool read is their last writer [B]

Every read of `0xd95d` is called with the same out window `fp-0x960`, so a byte no read writes keeps
the value of the previous one. The order of the reads before the copy at `0xde5d` and the highest
offset each one writes in that window:

| read | call row | function | max out offset | what it leaves in the window |
|---|---|---:|---:|---|
| bonding_curve | `0xda30` | `0x226f` | `0x52` | the decoder `0xdbb` copies `0x39` bytes to `+0x18` (`0xe26`, `0xe27`, `0xe2b`, `0xe2c`), then `+0x10`, `+0x08`, `+0x00`; its own count zero arm writes `+0x51` (`0x227b`) |
| pump_program | `0xda66` | `0x23e9` | `0x10` | `+0x00` and `+0x08` only |
| pump_event_authority | `0xda6f` | `0x353` | `0x2b` | `+0x00` to `+0x2a` (P2-f.3) |
| pool | `0xda9a` | `0x541` | `0x105` | its whole `0x108` byte record at `+0x00` to `+0x107` (`0x567`, `0x568`, `0x569`, `0x56a`) |
| pump_amm_program | `0xdaba` | `0x56c` | `0x10` | `+0x00` and `+0x08` only |
| pump_amm_event_authority | `0xdac4` | `0x4ff` | `0x2b` | `+0x00` to `+0x2a`, this tick |

The pool read is the last writer of window `+0x2b` to `+0x2f` before the copy: it copies its whole
record there, and neither of the two reads that follow it writes those five bytes (their out extent
stops at `0x10`, and neither `0x56c` nor `0x4ff` calls the copy helper `0x184d9`). Inside that record
the bytes `0x2b` to `0x2f` sit in the image the pool decoder copies at `0xea6 mov64 r1, r6`,
`0xea7 add64 r1, 0x18`, `0xeab mov64 r3, 0xec`, `0xeac call 0x184d9`, which covers record `0x18` to
`0x103`, so the five bytes the block receives are pool image bytes `0x13` to `0x17`. On the two arms
of the pool read that copy, and so the `0x108` copy, does not run; the window then keeps the step 6
decode that P2-f.4 measured.

Two things follow, and both are needed to read the row correctly. First, the five bytes are not part
of this read's record: the read stops at `+0x2a`, and the block's padding is filled from whatever the
shared window held, which for this row is the pool record and for the `pump_event_authority` record
of P2-f was the `bonding_curve` image. Second, no instruction reads them: `0x1ec6`, the clone that
consumes the block, writes out `0x00` to `0x2a` only, and no load of `ctx+0x4b3` to `ctx+0x4b7`
exists anywhere in the handler body.

### P2-g.6 Consumers, and what this closes

The handler touches the block in two ways. It reads one byte of it directly and it hands its address
to the account clone:

* `0x5c6d ldxb r1, [r7 +0x4b2]` then `0x5c6e jne r1, 0x2, +0x7` to `0x5c76`. The byte is `ctx+0x4b2`,
  the tag slot of P2-g.4. When it equals 2 the `0x5c6f` to `0x5c72` arm builds the error with the
  discriminant `0x13` = 19, 6019 `AMM accounts are required for graduated coins`, and returns
  through `0x5b46`; that is one of the four 6019 sites of 16.5 (`0x572c`, `0x5b43`, `0x5b79`,
  `0x5c72`), and this tick gives it its operand: the byte is set to 2 by the key equal arm of `0x4ff`
  (`0x53e`, `0x53f`), so the raise fires exactly when the account that arrived is the one the read
  compared against.
* `0x5c76 mov64 r6, r7`, `0x5c77 add64 r6, 0x488` takes the block's address, `0x5c8c stxdw
  [r10 -0x6f8], r6` saves it, and `0x1ec6` clones it twice: `0x5c8d mov64 r2, r6` with
  `0x5c8e call 0x1ec6` into `fp-0x298`, and `0x5cb9 ldxdw r2, [r10 -0x6f8]` with `0x5cba call
  0x1ec6` into `fp-0x410`. `0x1ec6` is the `AccountInfo` clone: two borrow counter increments at
  `0x1ec6` to `0x1ed8`, then the eight fields at `0x1ed9` to `0x1ee5`, out `0x00` to `0x2a` only. So
  the block enters the `pump_amm` CPI account array as an `AccountInfo` by value and its five padding
  bytes are dropped on the way.

The path to those consumers is guarded on the pool record: `0x5726 ldxb r1, [r7 +0x5bc]` with
`0x5727 jeq r1, 0x2, +0x1`, and `0x5b3e ldxb r1, [r7 +0x5bc]` with `0x5b3f jne r1, 0x2, +0xa`, both
raise 6019 on 2. Since `0x4b8 + 0x104 = 0x5bc`, that byte is the status byte of the pool record of
P2-g.5, so the block's consumers are reached only when the pool read took its copy arm. The block
itself has no other reader: the only direct load in the whole image with a displacement in `0x488`
to `0x4b7` is `0x5c6d`, and the only stores with a displacement in that range belong to `0x9690`,
a different function building its own object (`0x9690 mov64 r7, r5`, `0x9692 mov64 r6, r1`).

Row 5982 is closed on the bytes, with three corrections to carry, none of them a new row:

1. the row says the name link is positional with no name string on the copy. The name is on the read
   that fills the block: `0xdacc` logs the twenty four bytes at `0xc4da8`,
   `pump_amm_event_authority`, with the length `0x18`, and the read at `0xdac4` is the only one that
   can reach that arm. The link is by string.
2. the last five bytes of the block are not "the rest of the record". They are padding of the 48 byte
   shape filled from the shared window, and their content is whatever the last read into that window
   wrote, which for this row is the pool record.
3. `ctx+0x4b2` is not only the executable flag. It is the flag on the present arm of the read and the
   tag of the read on its other two arms, which is why the handler tests it against 2 at `0x5c6d`
   before it builds the `pump_amm` account array.

What stays open in this sublane: row 6025, the internal reading of the `0x68` byte tail at
`ctx+0x80` to `0xe7` of the `mint` block.

Severity: Informational
Sévérité : Informational
Severity justification: A static reading of one accounts field that fixes nine store rows, its window sources and the name string of the read that fills it; no execution and no behaviour, fund, admission or consensus effect is measured.

## P2-h. The `0x68` byte tail of the `mint` block: the split of the `0x80` byte read record, the source of each part, and the identity of the read [B, row 6025 closed]

Scope of this tick: ledger row 6025 only, the row P2-a.3 opened for the block `ctx+0x68` to `0xe7`
of `create_fee_sharing_config`. The extent, the writer, the `mint` field and the `AccountInfo` word at
`+0x58` were already `[B]`; what was open was the internal reading of the tail `+0x18` to `+0x7f`. The
handler body, the `SharingConfig` initialisation and the gates are not re-walked; P2-a, P2-f and P2-g
are used as given. Bytes read this tick: the windows `0xd9f0` to `0xda1b`, `0x50` to `0x67`,
`0x419` to `0x4a6`, `0x14f50` to `0x14fde`, `0x16577` to `0x16590`, `0xde3b` to `0xde40`, and the
strings at `0xc3eac`, `0xc36a0` and `0xc5404`. The store, load and consumer censuses are
`scratch/p2h_verify.py` (252 assertions, PASS) and `scratch/p2h_census.py` (`ctxrange`, `globalctx`,
`calls` modes). The field names of the 82 byte image are the published `spl_token` Mint field order,
which the reconstruction tree (lalalune/pumpfun-source, MIT) also carries for the token interface
account; every offset below is measured on the deployed bytes.

### P2-h.1 The `0x80` byte block is a flat copy of the read record, and the split is where the copy changes mechanism [B]

The block is assembled at `0xda09` to `0xda1a` from the out window `fp-0x960` of the read at `0xd9f4`
and copied to `ctx+0x68` by `0xde3b` to `0xde40`. Both halves are one record: the four scalar loads
land at the same offsets they are read from.

| block range | size | writer rows | source |
|---|---:|---|---|
| `+0x00` | 4 | `0xda1a stxw [r10 -0x3a0], r7` | out `+0x00`, loaded at `0xd9f5` |
| `+0x04` | 4 | `0xda0a ldxw` to `0xda0b stxdw [r10 -0xca8]`, then `0xda19 stxw [r10 -0x39c]` | out `+0x04` |
| `+0x08` | 8 | `0xda0c ldxdw` to `0xda0d stxdw [r10 -0xcb0]`, then `0xda17 stxdw [r10 -0x398]` | out `+0x08` |
| `+0x10` | 8 | `0xda0e ldxdw r8`, then `0xda15 stxdw [r10 -0x390]` | out `+0x10` |
| `+0x18` to `+0x7f` | 0x68 | `0xda0f` to `0xda14`: `add64 r1, -0x388`, `add64 r2, -0x948`, `mov64 r3, 0x68`, `call 0x184d9` | out `+0x18`, the `sol_memcpy_` helper |

The frame arithmetic is exact on both sides: `fp-0x3a0` plus `0x04`, `0x08`, `0x10` and `0x18` are
`fp-0x39c`, `fp-0x398`, `fp-0x390` and `fp-0x388`; `fp-0x960` plus the same offsets are `fp-0x95c`,
`fp-0x958`, `fp-0x950` and `fp-0x948`. So the block is one record copied in two mechanisms, the head
by four scalar loads and the tail by one `0x68` byte copy, and the boundary is a copy boundary, not a
boundary of the copied structure. The tail starts at record byte `0x18`.

### P2-h.2 The `0x80` byte record of the read at `0xd9f4` [B]

The read is called at `0xd9f1` to `0xd9f4` with `r1` the out window `fp-0x960`, `r2` the accounts
cursor `r9`. The callee is the shared account read helper `0x50`: it has twelve call sites in this
image, so the helper does not carry an identity. On its present arm (`0x51 jne r3, 0x0, +0xc` to
`0x5e`) it decrements the cursor count (`0x5f stxdw [r2 +0x8], r3`), advances the base by the `0x30`
byte entry size (`0x62 add64 r4, 0x30`, `0x63 stxdw [r2 +0x0], r4`), and calls `0x419` at `0x65` with
the entry in `r2` and `r1` still the out window: no instruction of `0x5e` to `0x64` writes `r1`.

`0x419` composes the whole `0x80` byte record. It takes the entry in `r7` once (`0x419 mov64 r7, r2`)
and the out pointer in `r6` once (`0x41a mov64 r6, r1`), loads the entry word once (`0x41b ldxdw r8, [r7 +0x18]`, the only
load off `r7` in that function), borrows the entry's data object at `0x44c` to `0x44f`
(`call 0x16577`, which reads `[r2 +0x10]` and hands back object `+0x18` at `0x16584`), reads the
`(ptr, len)` pair at `0x457` and `0x458`, and calls the decode `0x14f50` at `0x45f`. On the arm it
takes when the decode reports a present mint (`0x460 ldxw r1, [r10 -0x58]`, `0x461 jeq r1, 0x2`,
`0x462 ja` to `0x480`) it writes:

| record range | size | writer rows | source |
|---|---:|---|---|
| `+0x00` | 4 | `0x49d stxw [r6 +0x0], r1` from `0x49c ldxdw [r10 -0xc0]` | decode out `+0x00`, the `ldxw` of `0x460` staged at `0x486` |
| `+0x04` | 4 | `0x49b stxw [r6 +0x4]` from `0x49a ldxdw [r10 -0xb0]` | decode out `+0x04` |
| `+0x08` | 8 | `0x499 stxdw [r6 +0x8]` from `0x498 ldxdw [r10 -0xb8]` | decode out `+0x08` |
| `+0x10` | 8 | `0x497 stxdw [r6 +0x10]` from `0x496 ldxdw [r10 -0xc8]` | decode out `+0x10` |
| `+0x18` to `+0x57` | 0x40 | `0x487` to `0x48c`: `add64 r1, 0x18`, `add64 r2, -0x40`, `mov64 r3, 0x40`, `call 0x184d9` | decode out `+0x18` to `+0x58` |
| `+0x58` | 8 | `0x495 stxdw [r6 +0x58], r7` | the entry pointer |
| `+0x60` to `+0x7f` | 0x20 | `0x493`/`0x494`, `0x491`/`0x492`, `0x48f`/`0x490`, `0x48d`/`0x48e` | entry `+0x00`, `+0x08`, `+0x10`, `+0x18` |

The head and the first `0x40` bytes of the tail are the same object: the head carries the decode out
at the four offsets it is read from, and the `0x40` byte copy starts exactly at decode out `+0x18`,
so record `0x00` to `0x57` is a flat copy of the `0x58` byte decode out, `0x18` plus `0x40`. The last
`0x28` bytes of the record are not part of that object at all.

### P2-h.3 The internal reading of the `0x68` byte tail [B]

The tail is three parts, and the split between the first two falls inside a key, not between fields.

| tail range | ctx range | size | what it holds | cited rows |
|---|---|---:|---|---|
| `+0x18` to `+0x57` | `ctx+0x80` to `0xbf` | 0x40 | the rest of the 82 byte token mint image: image bytes `0x14` to `0x51`, then two bytes of padding | `0x487` to `0x48c`, decode stores below |
| `+0x58` to `+0x5f` | `ctx+0xc0` | 8 | the `0x30` byte accounts entry pointer, the word 16.8.2 dereferences | `0x495` |
| `+0x60` to `+0x7f` | `ctx+0xc8` to `0xe7` | 0x20 | the 32 byte owner key of that entry, `[r7 +0x18]` | `0x41b`, `0x48d` to `0x494` |

The decode `0x14f50` writes the image with the success arm stores at `0x14fc6` to `0x14fdc`, fourteen
stores whose ranges cover `0x00` to `0x58` with one eight byte overlap at `0x50`. The store offsets
are the field starts, and the resulting order is the published `spl_token` Mint order, 36 plus 8 plus
1 plus 1 plus 36 bytes, with the image at decode out `+0x04`:

| decode out | image offset | size | field | cited store |
|---|---:|---:|---|---|
| `+0x00` | none | 4 | the discriminant the arm tests against `2` | `0x14fdc`, fail arm `0x14fc4` |
| `+0x04` | `0x00` | 4 | the `Option` tag of the mint authority | `0x14fdb` |
| `+0x08`, `0x10`, `0x18`, `0x20` | `0x04` to `0x24` | 0x20 | the mint authority key, four words | `0x14fda`, `0x14fd9`, `0x14fd8`, `0x14fcb` |
| `+0x28` | `0x24` | 8 | supply | `0x14fc9` |
| `+0x30` | `0x2c` | 1 | decimals | `0x14fc7` |
| `+0x31` | `0x2d` | 1 | is initialized, required non zero at `0x14f6e` and `0x14f6f` | `0x14fd6` |
| `+0x32` to `+0x56` | `0x2e` to `0x52` | 0x24 | the `Option` of the freeze authority, tag and 32 byte key | `0x14fcd`, `0x14fcf`, `0x14fd1`, `0x14fd3`, `0x14fd5` |
| `+0x56` to `0x58` | `0x52` to `0x54` | 2 | padding to the `0x58` byte out | none |

So the `0x18` byte header of the record holds the discriminant and image bytes `0x00` to `0x13`, and
the tail opens inside the mint authority key, at image byte `0x14`. Read in tail coordinates the parts
are the second half of that key, two words (`tail +0x00` to `+0x0f`), then supply at tail `+0x10`
(`ctx+0x90`), decimals at tail `+0x18` (`ctx+0x98`), is initialized at tail `+0x19` (`ctx+0x99`), the
freeze authority from tail `+0x1a` to `+0x3d` (`ctx+0x9a` to `0xbd`), two bytes of padding at tail
`+0x3e` and `+0x3f`, the entry pointer at tail `+0x40` (`ctx+0xc0`) and the owner key at tail `+0x48`
to `+0x67` (`ctx+0xc8` to `0xe7`).

### P2-h.4 The identity of the read [B]

The name is carried by the caller arm, as in P2-g, and the arm is the one for a failed read:

| row | instruction | value |
|---|---|---|
| `0xd9f5` | `ldxw r7, [r10 -0x960]` | the record discriminant |
| `0xd9f6` | `jeq r7, 0x2, +0x1` to `0xd9f8` | the absent or failed arm |
| `0xd9fc` | `lddw r4, 0xc3eac` | the string |
| `0xd9fe` | `mov64 r5, 0x4` | 4 bytes |
| `0xd9ff` | `call 0x2b1` | the same name helper P2-g read at `0xdacf` |

The four bytes at `0xc3eac` are `mint`, and the logged length `0x4` is the whole name. Combined with
the consumed order of P2-a.2, where this read is the fifth entry, the record belongs to the `mint`
account, and the read is the one whose result the body consumes as the token mint of the sharing
configuration.

Three measurements fix that the record is a token mint and not a look alike. The owner word of the
entry, `[r7 +0x18]`, is first compared with the 32 zero bytes at `0xc36a0`, which is the all zero
program id, at `0x41c` to `0x423`; on equality `0x469` to `0x46b` asks `0x16520` whether the account
is initialised and raises the code `0xbc4` at `0x46e` when it is not. It is then compared with the
two 32 byte constants at `0xc5404` and `0xc5404 + 0x20`, which base58 encode to
`TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA` and
`TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb`, at `0x424` to `0x435`, and a mismatch raises the code
`0xbbf` at `0x438` and `0x439`. Finally `0x14f50` accepts the data length only when it is at least
`0x52` and not `0x163` (`0x14f54`, `0x14f55`), decodes `0x52` bytes at `0x14f5b`, and for a longer
account requires the account type byte at data `+0xa5` to be `1` (`0x14fb5`, `0x14fb6`), which is the
token mint account type of the extension layout.

### P2-h.5 What the row said that these bytes supersede, and what the body reads back [B]

The row and its open item at line 6025 said that the bytes cannot name the tail. The bytes do settle
it: the tail is the second half of the decoded token mint image, the accounts entry pointer, and the
owner key of the entry. The row's extent and writer stand unchanged.

One residual is declared TERMINAL here and is not re-dug: the source level type of the `0x04` byte
discriminant at record `+0x00` and decode out `+0x00`. Its measured role is fixed, a `u32` that the
decode writes as the literal `2` on its fail arm (`0x14fc4`) and that `0x419` tests against `2`
(`0x460`, `0x461`), with the first `u32` of the image written at `+0x04` (`0x14fdb`); its name is not
in the bytes.

The consumer census of the block inside the handler body `0x56c7` returns four loads and every one of
them is the word at `ctx+0xc0`: `0x56dd`, `0x5867`, `0x59e5` and `0x5b7f`. No other word of
`ctx+0x68` to `0xe7` is loaded in that function, and the `try_accounts` tail `0xd95d` loads nothing
from the block at all. So the mint image half and the owner half of the tail are carried for the
record shape and for the clone the body makes of the account, and the only field the sharing
configuration instruction itself reads back is the entry pointer.

Severity: Informational
Sévérité : Informational
Severity justification: A static reading of one already documented `ctx` region of a deployed program, with no execution, no state change and no fund, admission or consensus effect measured.
