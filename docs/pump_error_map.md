> **[VERIFIED 2026-10-26]** There is NO PumpError enum revision mismatch. The recovered
> lib.rs enum matches the deployed binary exactly: index 3=TooLittleSolReceived(6003),
> 4=MintDoesNotMatchBondingCurve(6004), 5=BondingCurveComplete(6005), 10=AccountTypeNotSupported(6010),
> 22=SellZeroAmount(6022) — all confirmed by enumerating the recovered enum AND the deployed
> PumpError::name() table + raise-site counts. Any 'different revision / 6010-vs-6022 shift'
> statement below is SUPERSEDED and wrong. (The admin_cto guard-SET difference is a separate,
> real divergence — not about the error enum.)

# pump error map - binary-grounded code -> name -> raise site

Generated from the deployed `pump` program only. No reconstruction-enum numbers are used
for the code assignment or the variant names; the recovered source is referenced only where
explicitly marked `[R]` as a cross-check.

- Binary: `D:\dev\ext\pumpfun-source\evidence\original\pump\deployed.so`
- SHA-256: `7a19affaa2c6187e04a5fe0ea298cee81fa5eb8c24cfcc30d85f615e89f7b02d`
- Method: scan every `stw [r10+off], imm` with `imm` in `[6000, 6110]` (Anchor custom-error
  code stores), then resolve `imm -> variant name` by emulating the deployed
  `PumpError::name()` at pc `0x2bd95` (byte `0x15eca8`), which is a binary search over the
  enum discriminant and returns the `&str` name (e.g. `0x1b81c6/13 = "NotAuthorized"`).
- Code assignment is `code = 6000 + discriminant`. The table is internally consistent with
  the site contexts: 6004 sites are mint-equality checks, 6005 sites are curve-complete
  checks, 6010 sites are account owner/type checks, and 6022 sites are zero-amount sell
  checks. Examples: 6000 NotAuthorized, 6003 TooLittleSolReceived, 6004
  MintDoesNotMatchBondingCurve, 6005 BondingCurveComplete, 6010 AccountTypeNotSupported,
  6022 SellZeroAmount.
- `origin` = the nearest binary-stored `file!()` pointer and `line!()` immediate in the
  AnchorError construction tuple. It is the ORIGINAL source location; the recovered source
  has different formatting/line numbers, so only the file name is directly comparable.

## Corrections to prior code attributions (important)

| code | binary name `[B]` | prior claim | status |
|---:|---|---|---|
| 6004 | MintDoesNotMatchBondingCurve | 6005 in spec/06 (shifted +1) | **corrected**; name ptr `0x1b820b/28`; 3 sites in mint-equality checks |
| 6005 | BondingCurveComplete | MintDoesNotMatchBondingCurve | **corrected**; name ptr `0x1b8227/20`; 7 sites, curve-complete checks |
| 6010 | AccountTypeNotSupported | 6022 AccountTypeNotSupported | **corrected**; name ptr `0x1b8298/23`; 12 sites in account-type checks |
| 6022 | SellZeroAmount | AccountTypeNotSupported | **corrected**; name ptr `0x1b83f7/14`; 4 sites, sell/trade paths |

The earlier `6022 = AccountTypeNotSupported` came from the recovered source enum order,
not the deployed binary. The binary name table puts `AccountTypeNotSupported` at
discriminant 10 = `6010`, and `SellZeroAmount` at discriminant 22 = `6022`. The site
contexts agree: the `6010` sites are in `buy_v2.rs`, `extend_account.rs`,
`claim_token_incentives.rs`, and `admin_set_idl_authority.rs` (account owner/type checks),
while the `6022` sites are in `sell_v2.rs`, `trade_v3.rs`, `multi_hop_curve_swap.rs`, and
`lib.rs` (zero-amount sell paths). In `sell_v2.rs` the `6022` site at line 245 is
immediately followed by the `6023` NotEnoughTokensToSell site at line 247, matching the
sell zero/min order. Do not use the reconstructed enum numbers.

## Summary

| code | name `[B]` | `stw` sites | distinct origins (top 3) |
|---:|---|---:|---|
| 6000 | NotAuthorized | 6 | `fee_recipient.rs:35` x1, `fee_recipient.rs:19` x1, `sweep_fees.rs:123` x1 |
| 6002 | TooMuchSolRequired | 6 | `buy_v2.rs:494` x1, `buy_v2.rs:967` x1, `trade_v3.rs:842` x1 |
| 6003 | TooLittleSolReceived | 3 | `sell_v2.rs:379` x1, `trade_v3.rs:1148` x1, `lib.rs:1012` x1 |
| 6004 | MintDoesNotMatchBondingCurve | 3 | `buy_v2.rs:88` x1, `buy_v2.rs:116` x1, `trade_v3.rs:180` x1 |
| 6005 | BondingCurveComplete | 7 | `trade_v3.rs:149` x1, `buy_v2.rs:345` x1, `buy_v2.rs:767` x1 |
| 6006 | BondingCurveNotComplete | 2 | `migrate.rs:251` x1, `migrate_v2.rs:249` x1 |
| 6010 | AccountTypeNotSupported | 12 | `buy_v2.rs:81` x1, `buy_v2.rs:109` x1, `buy_v2.rs:121` x1 |
| 6011 | InitialRealTokenReservesShouldBeLessThanTokenTotalSupply | 1 | `lib.rs:222` x1 |
| 6012 | InitialVirtualTokenReservesShouldBeGreaterThanInitialRealTokenReserves | 1 | `lib.rs:228` x1 |
| 6013 | FeeBasisPointsGreaterThanMaximum | 2 | `lib.rs:278` x1, `lib.rs:242` x1 |
| 6014 | AllZerosWithdrawAuthority | 1 | `lib.rs:249` x1 |
| 6015 | PoolMigrationFeeShouldBeLessThanFinalRealSolReserves | 1 | `lib.rs:270` x1 |
| 6019 | InvalidCreator | 1 | `admin_cto.rs:312` x1 |
| 6020 | BuyZeroAmount | 8 | `multi_hop_curve_swap.rs:208` x1, `multi_hop_curve_swap.rs:590` x1, `buy_v2.rs:354` x1 |
| 6021 | NotEnoughTokensToBuy | 9 | `multi_hop_curve_swap.rs:599` x1, `trade_v3.rs:506` x1, `trade_v3.rs:518` x1 |
| 6022 | SellZeroAmount | 4 | `multi_hop_curve_swap.rs:686` x1, `sell_v2.rs:245` x1, `trade_v3.rs:1126` x1 |
| 6023 | NotEnoughTokensToSell | 3 | `sell_v2.rs:247` x1, `trade_v3.rs:1127` x1, `lib.rs:972` x1 |
| 6024 | Overflow | 98 | `sell.rs:102` x2, `claim_token_incentives.rs:252` x2, `lib.rs:747` x2 |
| 6025 | Truncation | 22 | `buy_v2.rs:465` x1, `buy_v2.rs:881` x1, `buy_v2.rs:927` x1 |
| 6026 | DivisionByZero | 10 | `pump_quote.rs:106` x1, `pump_quote.rs:121` x1, `pump_quote.rs:131` x1 |
| 6027 | NotEnoughRemainingAccounts | 12 | `create_v2.rs:198` x1, `distribute_creator_fee_v2.rs:152` x1, `distribute_creator_fee_v2.rs:149` x1 |
| 6028 | AllFeeRecipientsShouldBeNonZero | 2 | `fee_recipient.rs:60` x1, `set_reserved_fee_recipients.rs:60` x1 |
| 6029 | UnsortedNotUniqueFeeRecipients | 1 | `fee_recipient.rs:78` x1 |
| 6030 | CreatorShouldNotBeZero | 3 | `create_v2.rs:732` x1, `admin_cto.rs:307` x1, `lib.rs:334` x1 |
| 6031 | StartTimeInThePast | 1 | `volume_accumulator.rs:359` x1 |
| 6032 | EndTimeInThePast | 1 | `volume_accumulator.rs:369` x1 |
| 6033 | EndTimeBeforeStartTime | 1 | `volume_accumulator.rs:371` x1 |
| 6034 | TimeRangeTooLarge | 1 | `volume_accumulator.rs:373` x1 |
| 6035 | EndTimeBeforeCurrentDay | 1 | `volume_accumulator.rs:394` x1 |
| 6036 | SupplyUpdateForFinishedRange | 1 | `volume_accumulator.rs:297` x1 |
| 6037 | DayIndexAfterEndIndex | 2 | `volume_accumulator.rs:309` x1, `volume_accumulator.rs:337` x1 |
| 6038 | DayInActiveRange | 1 | `volume_accumulator.rs:338` x1 |
| 6041 | BuyNotEnoughSolToCoverFees | 8 | `trade_v3.rs:317` x1, `buy_v2.rs:771` x1, `buy_v2.rs:873` x1 |
| 6042 | BuySlippageBelowMinTokensOut | 9 | `trade_v3.rs:326` x1, `buy_v2.rs:921` x1, `buy_v2.rs:986` x1 |
| 6043 | NameTooLong | 1 | `create_v2.rs:541` x1 |
| 6044 | SymbolTooLong | 1 | `create_v2.rs:547` x1 |
| 6045 | UriTooLong | 1 | `create_v2.rs:553` x1 |
| 6046 | CreateV2Disabled | 1 | `create_v2.rs:738` x1 |
| 6048 | MayhemModeDisabled | 1 | `create_v2.rs:709` x1 |
| 6050 | UnableToDistributeCreatorVaultMigratedToSharingConfig | 2 | `collect_creator_fee.rs:103` x1, `collect_creator_fee.rs:198` x1 |
| 6051 | SharingConfigNotActive | 2 | `distribute_creator_fee_v2.rs:205` x1, `distribute_creator_fees.rs:241` x1 |
| 6052 | UnableToDistributeCreatorFeesToExecutableRecipient | 2 | `distribute_creator_fee_v2.rs:125` x1, `distribute_creator_fees.rs:116` x1 |
| 6054 | ShareholdersAndRemainingAccountsMismatch | 3 | `distribute_creator_fee_v2.rs:101` x1, `distribute_creator_fee_v2.rs:112` x1, `distribute_creator_fees.rs:103` x1 |
| 6055 | InvalidShareBps | 2 | `distribute_creator_fee_v2.rs:163` x1, `distribute_creator_fees.rs:148` x1 |
| 6057 | BuybackFeeRecipientNotAuthorized | 1 | `lib.rs:1884` x1 |
| 6058 | AllBuybackFeeRecipientsShouldBeNonZero | 1 | `lib.rs:1895` x1 |
| 6059 | NotUniqueBuybackFeeRecipients | 1 | `lib.rs:1905` x1 |
| 6060 | BuybackBasisPointsOutOfRange | 1 | `lib.rs:1870` x1 |
| 6061 | WrongBuybackFeeRecipientsCount | 1 | `set_reserved_fee_recipients.rs:121` x1 |
| 6062 | BuybackFeeRecipientMissing | 2 | `sell.rs:145` x1, `lib.rs:1879` x1 |
| 6063 | UnsupportedQuoteMint | 10 | `create_v2.rs:345` x1, `create_v2.rs:390` x1, `create_v2.rs:528` x1 |
| 6064 | InvalidQuoteTokenProgram | 3 | `create_v2.rs:205` x1, `create_v2.rs:210` x1, `claim_token_incentives.rs:305` x1 |
| 6065 | InvalidAssociatedQuoteBondingCurve | 1 | `create_v2.rs:258` x1 |
| 6066 | QuoteMintWhitelistFull | 2 | `state.rs:82` x1, `lib.rs:1971` x1 |
| 6067 | QuoteMintAlreadyWhitelisted | 2 | `state.rs:77` x1, `lib.rs:1960` x1 |
| 6068 | QuoteMintNotWhitelisted | 3 | `state.rs:99` x1, `state.rs:113` x1, `lib.rs:1986` x1 |
| 6069 | QuoteMintNotEligibleForWhitelist | 7 | `state.rs:67` x1, `state.rs:72` x1, `state.rs:62` x1 |
| 6070 | UnableToDistributeCreatorFeesToUninitializedAccount | 1 | `distribute_creator_fee_v2.rs:173` x1 |
| 6071 | MayhemModeQuoteMintNotAllowed | 1 | `create_v2.rs:758` x1 |
| 6072 | MissingCashbackAccounts | 1 | `sell.rs:23` x1 |
| 6073 | InvalidCashbackAccumulator | 3 | `sell.rs:33` x1, `sell.rs:81` x1, `sell.rs:85` x1 |
| 6074 | InvalidBondingCurveV2 | 4 | `sell.rs:107` x1, `sell.rs:114` x1, `sell.rs:133` x1 |
| 6075 | InvalidQuoteControl | 5 | `create_v2.rs:348` x1, `create_v2.rs:353` x1, `state.rs:145` x1 |
| 6076 | InvalidCashbackRecipient | 1 | `claim_token_incentives.rs:342` x1 |
| 6077 | CreatorFeeNotConfigurable | 2 | `create_v2.rs:774` x1, `admin_cto.rs:334` x1 |
| 6078 | CreatorFeeBpsOutOfRange | 2 | `create_v2.rs:778` x1, `admin_cto.rs:338` x1 |
| 6080 | CreatorFeeNotAllowedForCashbackCoin | 1 | `admin_cto.rs:330` x1 |
| 6082 | CashbackDeprecated | 1 | `create_v2.rs:716` x1 |
| 6083 | HolderRewardCreatorImmutable | 2 | `admin_cto.rs:289` x1, `migrate_bonding_curve_creator.rs:46` x1 |
| 6084 | HolderRewardDisabled | 2 | `create_v2.rs:719` x1, `admin_cto.rs:296` x1 |
| 6085 | HolderRewardRecipientsMismatch | 2 | `distribute_fee_to_holders.rs:82` x1, `distribute_fee_to_holders.rs:122` x1 |
| 6086 | HolderRewardsRentFloor | 1 | `distribute_fee_to_holders.rs:164` x1 |
| 6087 | HolderRewardTokenAccountMissing | 1 | `distribute_fee_to_holders.rs:120` x1 |
| 6088 | CtoNotAllowedForMayhemCoin | 1 | `admin_cto.rs:284` x1 |
| 6089 | CtoNewCreatorRequired | 1 | `admin_cto.rs:306` x1 |
| 6090 | CtoNewCreatorNotAllowed | 1 | `admin_cto.rs:298` x1 |
| 6091 | CreatorFeeNotConfigurableForQuote | 1 | `admin_cto.rs:326` x1 |
| 6092 | CtoCreatorAccountNotWritable | 1 | `admin_cto.rs:556` x1 |
| 6093 | CtoSharedVaultFrozen | 2 | `admin_cto.rs:719` x1, `admin_cto.rs:660` x1 |
| 6094 | CashbackCoinNotSupported | 1 | `trade_v3.rs:150` x1 |
| 6095 | CreatorFeesNotSwept | 4 | `admin_cto.rs:410` x1, `distribute_creator_fee_v2.rs:213` x1, `distribute_creator_fees.rs:249` x1 |
| 6096 | FeeTiersEmpty | 1 | `fee.rs:162` x1 |
| 6097 | FeeConfigTooShort | 1 | `fee.rs:183` x1 |
| 6098 | MultiHopDiscontinuousPath | 2 | `multi_hop_curve_swap.rs:262` x1, `multi_hop_curve_swap.rs:546` x1 |
| 6099 | InvalidQuoteBondingCurve | 3 | `create_v2.rs:442` x1, `create_v2.rs:437` x1, `create_v2.rs:449` x1 |
| 6100 | QuoteBondingCurveNotEligible | 2 | `create_v2.rs:395` x1, `pump_quote.rs:90` x1 |
| 6101 | QuotePoolAccountsRequired | 1 | `create_v2.rs:493` x1 |
| 6102 | QuotePoolNotFound | 1 | `pump_quote.rs:407` x1 |
| 6103 | InvalidQuotePool | 11 | `pump_quote.rs:279` x1, `pump_quote.rs:280` x1, `pump_quote.rs:307` x1 |
| 6104 | QuoteReservesOutOfRange | 1 | `pump_quote.rs:241` x1 |
| 6105 | CurveDepthExceeded | 1 | `pump_quote.rs:62` x1 |
| 6106 | MultiHopHopFeesMismatch | 1 | `multi_hop_curve_swap.rs:218` x1 |
| 6107 | QuoteCurveAwaitingMigration | 1 | `create_v2.rs:466` x1 |
| 6108 | MultiHopMayhemCurveNotSupported | 1 | `multi_hop_curve_swap.rs:484` x1 |
| 6109 | QuoteChainAccountsRequired | 1 | `create_v2.rs:412` x1 |
| 6110 | QuoteMintNotWritable | 1 | `migrate_v2.rs:335` x1 |

## Variants with no `stw` raise site in this binary

These names exist in the deployed `name()` table but no `stw ..., imm` site in `pump` uses
their code. They may be raised by a sibling program (`pump_amm`, `pump_fees`, `mayhem`),
be dead in this build, or be raised through a non-`stw` path (none found).

| code | name `[B]` |
|---:|---|
| 6001 | AlreadyInitialized |
| 6007 | NotInitialized |
| 6008 | WithdrawTooFrequent |
| 6009 | NewSizeShouldBeGreaterThanCurrentSize |
| 6016 | PoolMigrationFeeShouldBeGreaterThanCreatorFeePlusMaxMigrateFees |
| 6017 | DisabledWithdraw |
| 6018 | DisabledMigrate |
| 6039 | InvalidIncentiveMint |
| 6040 | BuyNotEnoughSolToCoverRent |
| 6047 | CpitializeMayhemFailed |
| 6049 | CreatorMigratedToSharingConfig |
| 6053 | BondingCurveAndSharingConfigCreatorMismatch |
| 6056 | CashbackNotEnabled |
| 6079 | CreatorFeeNotEditable |
| 6081 | BondingCurveAlreadyMigrated |

## Full raise-site table (all 366 `stw` sites)

`pc` is the sbftool instruction index (address = pc*8); `byte` is the ELF virtual address.
Origin paths are the full strings stored in the binary (all under `programs/pump/src/`).

| code | name `[B]` | pc | byte | handler/helper func | origin `[B]` |
|---:|---|---:|---:|---:|---|
| 6000 | NotAuthorized | `0x7c7c` | `0x3e3e0` | `0x7baf` | `programs/pump/src/fee_recipient.rs:35` |
| 6000 | NotAuthorized | `0x7c98` | `0x3e4c0` | `0x7baf` | `programs/pump/src/fee_recipient.rs:19` |
| 6000 | NotAuthorized | `0xe5a4` | `0x72d20` | `0xe502` | `programs/pump/src/sweep_fees.rs:123` |
| 6000 | NotAuthorized | `0x26aee` | `0x135770` | `0x26ab0` | `programs/pump/src/lib.rs:114` |
| 6000 | NotAuthorized | `0x26b42` | `0x135a10` | `0x26b04` | `programs/pump/src/lib.rs:121` |
| 6000 | NotAuthorized | `0x26b96` | `0x135cb0` | `0x26b58` | `programs/pump/src/lib.rs:149` |
| 6002 | TooMuchSolRequired | `0x27a70` | `0x13d380` | `0x27737` | `programs/pump/src/buy_v2.rs:494` |
| 6002 | TooMuchSolRequired | `0x2837d` | `0x141be8` | `0x27f22` | `programs/pump/src/buy_v2.rs:967` |
| 6002 | TooMuchSolRequired | `0x290e6` | `0x148730` | `0x28f74` | `programs/pump/src/trade_v3.rs:842` |
| 6002 | TooMuchSolRequired | `0x29422` | `0x14a110` | `0x2913f` | `programs/pump/src/trade_v3.rs:935` |
| 6002 | TooMuchSolRequired | `0x2994a` | `0x14ca50` | `0x29807` | `programs/pump/src/lib.rs:654` |
| 6002 | TooMuchSolRequired | `0x2a27a` | `0x1513d0` | `0x29e9c` | `programs/pump/src/buy.rs:133` |
| 6003 | TooLittleSolReceived | `0x28bd7` | `0x145eb8` | `0x288a1` | `programs/pump/src/sell_v2.rs:379` |
| 6003 | TooLittleSolReceived | `0x29622` | `0x14b110` | `0x29515` | `programs/pump/src/trade_v3.rs:1148` |
| 6003 | TooLittleSolReceived | `0x2a682` | `0x153410` | `0x2a511` | `programs/pump/src/lib.rs:1012` |
| 6004 | MintDoesNotMatchBondingCurve | `0x2a70` | `0x15380` | `0x2922` | `programs/pump/src/buy_v2.rs:88` |
| 6004 | MintDoesNotMatchBondingCurve | `0x2c91` | `0x16488` | `0x2c1a` | `programs/pump/src/buy_v2.rs:116` |
| 6004 | MintDoesNotMatchBondingCurve | `0xfd75` | `0x7eba8` | `0xfc92` | `programs/pump/src/trade_v3.rs:180` |
| 6005 | BondingCurveComplete | `0xfc67` | `0x7e338` | `0xfc16` | `programs/pump/src/trade_v3.rs:149` |
| 6005 | BondingCurveComplete | `0x277b1` | `0x13bd88` | `0x27737` | `programs/pump/src/buy_v2.rs:345` |
| 6005 | BondingCurveComplete | `0x27fa8` | `0x13fd40` | `0x27f22` | `programs/pump/src/buy_v2.rs:767` |
| 6005 | BondingCurveComplete | `0x288ee` | `0x144770` | `0x288a1` | `programs/pump/src/sell_v2.rs:243` |
| 6005 | BondingCurveComplete | `0x2989f` | `0x14c4f8` | `0x29807` | `programs/pump/src/lib.rs:608` |
| 6005 | BondingCurveComplete | `0x29f20` | `0x14f900` | `0x29e9c` | `programs/pump/src/buy.rs:53` |
| 6005 | BondingCurveComplete | `0x2a56a` | `0x152b50` | `0x2a511` | `programs/pump/src/lib.rs:968` |
| 6006 | BondingCurveNotComplete | `0x7fce` | `0x3fe70` | `0x7f6e` | `programs/pump/src/migrate.rs:251` |
| 6006 | BondingCurveNotComplete | `0x93f2` | `0x49f90` | `0x9311` | `programs/pump/src/migrate_v2.rs:249` |
| 6010 | AccountTypeNotSupported | `0x2990` | `0x14c80` | `0x2922` | `programs/pump/src/buy_v2.rs:81` |
| 6010 | AccountTypeNotSupported | `0x2d13` | `0x16898` | `0x2c1a` | `programs/pump/src/buy_v2.rs:109` |
| 6010 | AccountTypeNotSupported | `0x2d46` | `0x16a30` | `0x2c1a` | `programs/pump/src/buy_v2.rs:121` |
| 6010 | AccountTypeNotSupported | `0x7769` | `0x3bb48` | `0x771b` | `programs/pump/src/extend_account.rs:84` |
| 6010 | AccountTypeNotSupported | `0x7820` | `0x3c100` | `0x7816` | `programs/pump/src/extend_account.rs:107` |
| 6010 | AccountTypeNotSupported | `0xb132` | `0x58990` | `0xb0d8` | `programs/pump/src/multi_hop_curve_swap.rs:359` |
| 6010 | AccountTypeNotSupported | `0xf04c` | `0x78260` | `0xefaa` | `programs/pump/src/token_incentives/claim_token_incentives.rs:310` |
| 6010 | AccountTypeNotSupported | `0xf2bc` | `0x795e0` | `0xf1af` | `programs/pump/src/token_incentives/claim_token_incentives.rs:333` |
| 6010 | AccountTypeNotSupported | `0xfce3` | `0x7e718` | `0xfc92` | `programs/pump/src/trade_v3.rs:172` |
| 6010 | AccountTypeNotSupported | `0x2ab52` | `0x155a90` | `0x2aafd` | `programs/pump/src/admin_set_idl_authority.rs:72` |
| 6010 | AccountTypeNotSupported | `0x2aca8` | `0x156540` | `0x2ab74` | `programs/pump/src/admin_set_idl_authority.rs:79` |
| 6010 | AccountTypeNotSupported | `0x2acdb` | `0x1566d8` | `0x2ab74` | `programs/pump/src/admin_set_idl_authority.rs:90` |
| 6011 | InitialRealTokenReservesShouldBeLessThanTokenTotalSupply | `0x26e4f` | `0x137278` | `0x26cf8` | `programs/pump/src/lib.rs:222` |
| 6012 | InitialVirtualTokenReservesShouldBeGreaterThanInitialRealTokenReserves | `0x26d7e` | `0x136bf0` | `0x26cf8` | `programs/pump/src/lib.rs:228` |
| 6013 | FeeBasisPointsGreaterThanMaximum | `0x26dd2` | `0x136e90` | `0x26cf8` | `programs/pump/src/lib.rs:278` |
| 6013 | FeeBasisPointsGreaterThanMaximum | `0x26df1` | `0x136f88` | `0x26cf8` | `programs/pump/src/lib.rs:242` |
| 6014 | AllZerosWithdrawAuthority | `0x26e75` | `0x1373a8` | `0x26cf8` | `programs/pump/src/lib.rs:249` |
| 6015 | PoolMigrationFeeShouldBeLessThanFinalRealSolReserves | `0x26ead` | `0x137568` | `0x26cf8` | `programs/pump/src/lib.rs:270` |
| 6019 | InvalidCreator | `0x479e` | `0x23cf0` | `0x4542` | `programs/pump/src/creator/admin_cto.rs:312` |
| 6020 | BuyZeroAmount | `0xad74` | `0x56ba0` | `0xacfb` | `programs/pump/src/multi_hop_curve_swap.rs:208` |
| 6020 | BuyZeroAmount | `0xbb70` | `0x5db80` | `0xb70e` | `programs/pump/src/multi_hop_curve_swap.rs:590` |
| 6020 | BuyZeroAmount | `0x277d0` | `0x13be80` | `0x27737` | `programs/pump/src/buy_v2.rs:354` |
| 6020 | BuyZeroAmount | `0x27f4b` | `0x13fa58` | `0x27f22` | `programs/pump/src/buy_v2.rs:769` |
| 6020 | BuyZeroAmount | `0x29000` | `0x148000` | `0x28f74` | `programs/pump/src/trade_v3.rs:801` |
| 6020 | BuyZeroAmount | `0x291b5` | `0x148da8` | `0x2913f` | `programs/pump/src/trade_v3.rs:881` |
| 6020 | BuyZeroAmount | `0x298c0` | `0x14c600` | `0x29807` | `programs/pump/src/lib.rs:617` |
| 6020 | BuyZeroAmount | `0x29f41` | `0x14fa08` | `0x29e9c` | `programs/pump/src/buy.rs:57` |
| 6021 | NotEnoughTokensToBuy | `0xbaef` | `0x5d778` | `0xb70e` | `programs/pump/src/multi_hop_curve_swap.rs:599` |
| 6021 | NotEnoughTokensToBuy | `0x104f1` | `0x82788` | `0x10425` | `programs/pump/src/trade_v3.rs:506` |
| 6021 | NotEnoughTokensToBuy | `0x105c4` | `0x82e20` | `0x1055f` | `programs/pump/src/trade_v3.rs:518` |
| 6021 | NotEnoughTokensToBuy | `0x2795b` | `0x13cad8` | `0x27737` | `programs/pump/src/buy_v2.rs:356` |
| 6021 | NotEnoughTokensToBuy | `0x28533` | `0x142998` | `0x27f22` | `programs/pump/src/buy_v2.rs:997` |
| 6021 | NotEnoughTokensToBuy | `0x2902d` | `0x148168` | `0x28f74` | `programs/pump/src/trade_v3.rs:802` |
| 6021 | NotEnoughTokensToBuy | `0x292cc` | `0x149660` | `0x2913f` | `programs/pump/src/trade_v3.rs:926` |
| 6021 | NotEnoughTokensToBuy | `0x2985a` | `0x14c2d0` | `0x29807` | `programs/pump/src/lib.rs:619` |
| 6021 | NotEnoughTokensToBuy | `0x2a0fa` | `0x1507d0` | `0x29e9c` | `programs/pump/src/buy.rs:151` |
| 6022 | SellZeroAmount | `0xba48` | `0x5d240` | `0xb70e` | `programs/pump/src/multi_hop_curve_swap.rs:686` |
| 6022 | SellZeroAmount | `0x28945` | `0x144a28` | `0x288a1` | `programs/pump/src/sell_v2.rs:245` |
| 6022 | SellZeroAmount | `0x29583` | `0x14ac18` | `0x29515` | `programs/pump/src/trade_v3.rs:1126` |
| 6022 | SellZeroAmount | `0x2a5c0` | `0x152e00` | `0x2a511` | `programs/pump/src/lib.rs:970` |
| 6023 | NotEnoughTokensToSell | `0x28abf` | `0x1455f8` | `0x288a1` | `programs/pump/src/sell_v2.rs:247` |
| 6023 | NotEnoughTokensToSell | `0x295af` | `0x14ad78` | `0x29515` | `programs/pump/src/trade_v3.rs:1127` |
| 6023 | NotEnoughTokensToSell | `0x2a5ef` | `0x152f78` | `0x2a511` | `programs/pump/src/lib.rs:972` |
| 6024 | Overflow | `0x2dea` | `0x16f50` | `0x2db8` | `programs/pump/src/buy_v2.rs:469` |
| 6024 | Overflow | `0x2ebf` | `0x175f8` | `0x2e7b` | `programs/pump/src/buy_v2.rs:949` |
| 6024 | Overflow | `0x2f8f` | `0x17c78` | `0x2f5d` | `programs/pump/src/buy_v2.rs:995` |
| 6024 | Overflow | `0x3382` | `0x19c10` | `0x30cf` | `programs/pump/src/create_v2.rs:473` |
| 6024 | Overflow | `0x3678` | `0x1b3c0` | `0x35e9` | `programs/pump/src/create_v2.rs:586` |
| 6024 | Overflow | `0x36c0` | `0x1b600` | `0x35e9` | `programs/pump/src/create_v2.rs:588` |
| 6024 | Overflow | `0x5a9d` | `0x2d4e8` | `0x5961` | `programs/pump/src/creator/distribute_creator_fee_v2.rs:168` |
| 6024 | Overflow | `0x6206` | `0x31030` | `0x5f61` | `programs/pump/src/creator/distribute_creator_fee_v2.rs:378` |
| 6024 | Overflow | `0x640a` | `0x32050` | `0x633e` | `programs/pump/src/creator/distribute_creator_fees.rs:158` |
| 6024 | Overflow | `0x6499` | `0x324c8` | `0x633e` | `programs/pump/src/creator/distribute_creator_fees.rs:165` |
| 6024 | Overflow | `0x6889` | `0x34448` | `0x679e` | `programs/pump/src/creator/distribute_creator_fees.rs:343` |
| 6024 | Overflow | `0x6d0a` | `0x36850` | `0x6c3e` | `programs/pump/src/creator/distribute_fee_to_holders.rs:157` |
| 6024 | Overflow | `0x7ba0` | `0x3dd00` | `0x7abf` | `programs/pump/src/extend_account.rs:141` |
| 6024 | Overflow | `0x8248` | `0x41240` | `0x8216` | `programs/pump/src/migrate.rs:280` |
| 6024 | Overflow | `0x8289` | `0x41448` | `0x8257` | `programs/pump/src/migrate.rs:282` |
| 6024 | Overflow | `0x979a` | `0x4bcd0` | `0x9768` | `programs/pump/src/migrate_v2.rs:309` |
| 6024 | Overflow | `0x97db` | `0x4bed8` | `0x97a9` | `programs/pump/src/migrate_v2.rs:313` |
| 6024 | Overflow | `0x981c` | `0x4c0e0` | `0x97ea` | `programs/pump/src/migrate_v2.rs:326` |
| 6024 | Overflow | `0xafb9` | `0x57dc8` | `0xaf87` | `programs/pump/src/multi_hop_curve_swap.rs:259` |
| 6024 | Overflow | `0xbfbb` | `0x5fdd8` | `0xbf89` | `programs/pump/src/multi_hop_curve_swap.rs:571` |
| 6024 | Overflow | `0xc03d` | `0x601e8` | `0xc00b` | `programs/pump/src/multi_hop_curve_swap.rs:624` |
| 6024 | Overflow | `0xc0bf` | `0x605f8` | `0xc08d` | `programs/pump/src/multi_hop_curve_swap.rs:692` |
| 6024 | Overflow | `0xc100` | `0x60800` | `0xc0ce` | `programs/pump/src/multi_hop_curve_swap.rs:736` |
| 6024 | Overflow | `0xc141` | `0x60a08` | `0xc10f` | `programs/pump/src/multi_hop_curve_swap.rs:744` |
| 6024 | Overflow | `0xc1a7` | `0x60d38` | `0xc150` | `programs/pump/src/pump_quote.rs:61` |
| 6024 | Overflow | `0xc2b7` | `0x615b8` | `0xc269` | `programs/pump/src/pump_quote.rs:104` |
| 6024 | Overflow | `0xc394` | `0x61ca0` | `0xc2fd` | `programs/pump/src/pump_quote.rs:117` |
| 6024 | Overflow | `0xc3ca` | `0x61e50` | `0xc2fd` | `programs/pump/src/pump_quote.rs:119` |
| 6024 | Overflow | `0xc41f` | `0x620f8` | `0xc2fd` | `programs/pump/src/pump_quote.rs:122` |
| 6024 | Overflow | `0xc4e3` | `0x62718` | `0xc42e` | `programs/pump/src/pump_quote.rs:134` |
| 6024 | Overflow | `0xc50e` | `0x62870` | `0xc42e` | `programs/pump/src/pump_quote.rs:137` |
| 6024 | Overflow | `0xc5eb` | `0x62f58` | `0xc554` | `programs/pump/src/pump_quote.rs:199` |
| 6024 | Overflow | `0xc6d8` | `0x636c0` | `0xc6a6` | `programs/pump/src/pump_quote.rs:212` |
| 6024 | Overflow | `0xc719` | `0x638c8` | `0xc6e7` | `programs/pump/src/pump_quote.rs:222` |
| 6024 | Overflow | `0xc900` | `0x64800` | `0xc8bf` | `programs/pump/src/pump_quote.rs:334` |
| 6024 | Overflow | `0xd16c` | `0x68b60` | `0xd123` | `programs/pump/src/quote_control/state.rs:52` |
| 6024 | Overflow | `0xd56d` | `0x6ab68` | `0xd539` | `programs/pump/src/quote_control/update_quote_control_mints.rs:71` |
| 6024 | Overflow | `0xdd1e` | `0x6e8f0` | `0xdbb5` | `programs/pump/src/sell.rs:102` |
| 6024 | Overflow | `0xdd7c` | `0x6ebe0` | `0xdbb5` | `programs/pump/src/sell.rs:102` |
| 6024 | Overflow | `0xdf4e` | `0x6fa70` | `0xdf1c` | `programs/pump/src/sell_v2.rs:366` |
| 6024 | Overflow | `0xdf8f` | `0x6fc78` | `0xdf5d` | `programs/pump/src/sell_v2.rs:368` |
| 6024 | Overflow | `0xdfd0` | `0x6fe80` | `0xdf9e` | `programs/pump/src/sell_v2.rs:386` |
| 6024 | Overflow | `0xee4c` | `0x77260` | `0xedd3` | `programs/pump/src/token_incentives/claim_token_incentives.rs:252` |
| 6024 | Overflow | `0xef03` | `0x77818` | `0xedd3` | `programs/pump/src/token_incentives/claim_token_incentives.rs:252` |
| 6024 | Overflow | `0x10082` | `0x80410` | `0x1003f` | `programs/pump/src/trade_v3.rs:285` |
| 6024 | Overflow | `0x100c6` | `0x80630` | `0x10091` | `programs/pump/src/trade_v3.rs:294` |
| 6024 | Overflow | `0x10289` | `0x81448` | `0x101bf` | `programs/pump/src/trade_v3.rs:371` |
| 6024 | Overflow | `0x102aa` | `0x81550` | `0x101bf` | `programs/pump/src/trade_v3.rs:375` |
| 6024 | Overflow | `0x102fa` | `0x817d0` | `0x102c8` | `programs/pump/src/trade_v3.rs:382` |
| 6024 | Overflow | `0x10345` | `0x81a28` | `0x10309` | `programs/pump/src/trade_v3.rs:390` |
| 6024 | Overflow | `0x103e0` | `0x81f00` | `0x10354` | `programs/pump/src/trade_v3.rs:442` |
| 6024 | Overflow | `0x10415` | `0x820a8` | `0x10354` | `programs/pump/src/trade_v3.rs:446` |
| 6024 | Overflow | `0x1047f` | `0x823f8` | `0x10425` | `programs/pump/src/trade_v3.rs:494` |
| 6024 | Overflow | `0x104b4` | `0x825a0` | `0x10425` | `programs/pump/src/trade_v3.rs:498` |
| 6024 | Overflow | `0x10513` | `0x82898` | `0x10425` | `programs/pump/src/trade_v3.rs:502` |
| 6024 | Overflow | `0x10548` | `0x82a40` | `0x10425` | `programs/pump/src/trade_v3.rs:507` |
| 6024 | Overflow | `0x10879` | `0x843c8` | `0x10780` | `programs/pump/src/trade_v3.rs:691` |
| 6024 | Overflow | `0x10960` | `0x84b00` | `0x1092e` | `programs/pump/src/trade_v3.rs:721` |
| 6024 | Overflow | `0x109a1` | `0x84d08` | `0x1096f` | `programs/pump/src/trade_v3.rs:767` |
| 6024 | Overflow | `0x10ae6` | `0x85730` | `0x10ab4` | `programs/pump/src/trade_v3.rs:970` |
| 6024 | Overflow | `0x11007` | `0x88038` | `0x10fd5` | `programs/pump/src/trade_v3.rs:1155` |
| 6024 | Overflow | `0x1109b` | `0x884d8` | `0x11016` | `programs/pump/src/util/constant_product.rs:17` |
| 6024 | Overflow | `0x110f2` | `0x88790` | `0x11016` | `programs/pump/src/util/constant_product.rs:13` |
| 6024 | Overflow | `0x1116e` | `0x88b70` | `0x11121` | `programs/pump/src/util/fee.rs:17` |
| 6024 | Overflow | `0x111c5` | `0x88e28` | `0x11121` | `programs/pump/src/util/fee.rs:15` |
| 6024 | Overflow | `0x12a0d` | `0x95068` | `0x129c5` | `programs/pump/src/util/transfer_fee.rs:48` |
| 6024 | Overflow | `0x12a5d` | `0x952e8` | `0x12a1c` | `programs/pump/src/util/transfer_fee.rs:56` |
| 6024 | Overflow | `0x12ab3` | `0x95598` | `0x12a6c` | `programs/pump/src/util/transfer_fee.rs:66` |
| 6024 | Overflow | `0x14065` | `0xa0328` | `0x1400e` | `programs/pump/src/lib.rs:2428` |
| 6024 | Overflow | `0x141d0` | `0xa0e80` | `0x1417e` | `programs/pump/src/lib.rs:2496` |
| 6024 | Overflow | `0x14219` | `0xa10c8` | `0x1417e` | `programs/pump/src/lib.rs:2501` |
| 6024 | Overflow | `0x1424e` | `0xa1270` | `0x1417e` | `programs/pump/src/lib.rs:2506` |
| 6024 | Overflow | `0x1426d` | `0xa1368` | `0x1417e` | `programs/pump/src/lib.rs:2511` |
| 6024 | Overflow | `0x142d4` | `0xa16a0` | `0x1427c` | `programs/pump/src/lib.rs:2525` |
| 6024 | Overflow | `0x14330` | `0xa1980` | `0x1427c` | `programs/pump/src/lib.rs:2520` |
| 6024 | Overflow | `0x1434e` | `0xa1a70` | `0x1427c` | `programs/pump/src/lib.rs:2530` |
| 6024 | Overflow | `0x1436e` | `0xa1b70` | `0x1427c` | `programs/pump/src/lib.rs:2535` |
| 6024 | Overflow | `0x143f2` | `0xa1f90` | `0x1437b` | `programs/pump/src/lib.rs:2550` |
| 6024 | Overflow | `0x14412` | `0xa2090` | `0x1437b` | `programs/pump/src/lib.rs:2554` |
| 6024 | Overflow | `0x1446f` | `0xa2378` | `0x14431` | `programs/pump/src/lib.rs:2562` |
| 6024 | Overflow | `0x15889` | `0xac448` | `0x15857` | `programs/pump/src/buy_v2.rs:498` |
| 6024 | Overflow | `0x158ca` | `0xac650` | `0x15898` | `programs/pump/src/buy_v2.rs:500` |
| 6024 | Overflow | `0x29aae` | `0x14d570` | `0x29807` | `programs/pump/src/lib.rs:747` |
| 6024 | Overflow | `0x29c65` | `0x14e328` | `0x29807` | `programs/pump/src/lib.rs:747` |
| 6024 | Overflow | `0x29dca` | `0x14ee50` | `0x29d98` | `programs/pump/src/lib.rs:674` |
| 6024 | Overflow | `0x29e0b` | `0x14f058` | `0x29dd9` | `programs/pump/src/lib.rs:679` |
| 6024 | Overflow | `0x29e4c` | `0x14f260` | `0x29e1a` | `programs/pump/src/lib.rs:684` |
| 6024 | Overflow | `0x29e8d` | `0x14f468` | `0x29e5b` | `programs/pump/src/lib.rs:689` |
| 6024 | Overflow | `0x2a2ea` | `0x151750` | `0x29e9c` | `programs/pump/src/buy.rs:232` |
| 6024 | Overflow | `0x2a317` | `0x1518b8` | `0x29e9c` | `programs/pump/src/buy.rs:232` |
| 6024 | Overflow | `0x2a9a9` | `0x154d48` | `0x2a977` | `programs/pump/src/lib.rs:1007` |
| 6024 | Overflow | `0x2a9ea` | `0x154f50` | `0x2a9b8` | `programs/pump/src/lib.rs:1009` |
| 6024 | Overflow | `0x2aa2b` | `0x155158` | `0x2a9f9` | `programs/pump/src/lib.rs:1022` |
| 6024 | Overflow | `0x2aa6c` | `0x155360` | `0x2aa3a` | `programs/pump/src/lib.rs:1027` |
| 6024 | Overflow | `0x2aaad` | `0x155568` | `0x2aa7b` | `programs/pump/src/lib.rs:1032` |
| 6024 | Overflow | `0x2aaee` | `0x155770` | `0x2aabc` | `programs/pump/src/lib.rs:1037` |
| 6024 | Overflow | `0x2eed1` | `0x177688` | `0x2ee9f` | `programs/pump/src/lib.rs:664` |
| 6024 | Overflow | `0x2ef12` | `0x177890` | `0x2eee0` | `programs/pump/src/lib.rs:666` |
| 6025 | Truncation | `0x2da9` | `0x16d48` | `0x2d77` | `programs/pump/src/buy_v2.rs:465` |
| 6025 | Truncation | `0x2e2b` | `0x17158` | `0x2df9` | `programs/pump/src/buy_v2.rs:881` |
| 6025 | Truncation | `0x2e6c` | `0x17360` | `0x2e3a` | `programs/pump/src/buy_v2.rs:927` |
| 6025 | Truncation | `0x2f0d` | `0x17868` | `0x2edb` | `programs/pump/src/buy_v2.rs:959` |
| 6025 | Truncation | `0x2f4e` | `0x17a70` | `0x2f1c` | `programs/pump/src/buy_v2.rs:983` |
| 6025 | Truncation | `0xb014` | `0x580a0` | `0xafc8` | `programs/pump/src/multi_hop_curve_swap.rs:295` |
| 6025 | Truncation | `0xbffc` | `0x5ffe0` | `0xbfca` | `programs/pump/src/multi_hop_curve_swap.rs:589` |
| 6025 | Truncation | `0xc07e` | `0x603f0` | `0xc04c` | `programs/pump/src/multi_hop_curve_swap.rs:673` |
| 6025 | Truncation | `0xdf0d` | `0x6f868` | `0xdedb` | `programs/pump/src/sell_v2.rs:341` |
| 6025 | Truncation | `0xf892` | `0x7c490` | `0xf7fb` | `programs/pump/src/token_incentives/volume_accumulator.rs:103` |
| 6025 | Truncation | `0x105e9` | `0x82f48` | `0x1055f` | `programs/pump/src/trade_v3.rs:526` |
| 6025 | Truncation | `0x106e3` | `0x83718` | `0x10699` | `programs/pump/src/trade_v3.rs:591` |
| 6025 | Truncation | `0x109e2` | `0x84f10` | `0x109b0` | `programs/pump/src/trade_v3.rs:811` |
| 6025 | Truncation | `0x10a23` | `0x85118` | `0x109f1` | `programs/pump/src/trade_v3.rs:904` |
| 6025 | Truncation | `0x10a64` | `0x85320` | `0x10a32` | `programs/pump/src/trade_v3.rs:911` |
| 6025 | Truncation | `0x10aa5` | `0x85528` | `0x10a73` | `programs/pump/src/trade_v3.rs:930` |
| 6025 | Truncation | `0x10b27` | `0x85938` | `0x10af5` | `programs/pump/src/trade_v3.rs:997` |
| 6025 | Truncation | `0x10fc6` | `0x87e30` | `0x10f94` | `programs/pump/src/trade_v3.rs:1140` |
| 6025 | Truncation | `0x11239` | `0x891c8` | `0x111f2` | `programs/pump/src/util/fee.rs:34` |
| 6025 | Truncation | `0x26fe9` | `0x137f48` | `0x26fb7` | `programs/pump/src/lib.rs:268` |
| 6025 | Truncation | `0x29d89` | `0x14ec48` | `0x29d57` | `programs/pump/src/lib.rs:629` |
| 6025 | Truncation | `0x2a968` | `0x154b40` | `0x2a936` | `programs/pump/src/lib.rs:981` |
| 6026 | DivisionByZero | `0xc2ec` | `0x61760` | `0xc269` | `programs/pump/src/pump_quote.rs:106` |
| 6026 | DivisionByZero | `0xc3ff` | `0x61ff8` | `0xc2fd` | `programs/pump/src/pump_quote.rs:121` |
| 6026 | DivisionByZero | `0xc4ae` | `0x62570` | `0xc42e` | `programs/pump/src/pump_quote.rs:131` |
| 6026 | DivisionByZero | `0xc543` | `0x62a18` | `0xc42e` | `programs/pump/src/pump_quote.rs:139` |
| 6026 | DivisionByZero | `0xc64f` | `0x63278` | `0xc554` | `programs/pump/src/pump_quote.rs:201` |
| 6026 | DivisionByZero | `0x11114` | `0x888a0` | `0x11016` | `programs/pump/src/util/constant_product.rs:19` |
| 6026 | DivisionByZero | `0x111e5` | `0x88f28` | `0x11121` | `programs/pump/src/util/fee.rs:19` |
| 6026 | DivisionByZero | `0x14096` | `0xa04b0` | `0x1400e` | `programs/pump/src/lib.rs:2430` |
| 6026 | DivisionByZero | `0x140f6` | `0xa07b0` | `0x140a7` | `programs/pump/src/lib.rs:2454` |
| 6026 | DivisionByZero | `0x1416d` | `0xa0b68` | `0x1411f` | `programs/pump/src/lib.rs:2481` |
| 6027 | NotEnoughRemainingAccounts | `0x3f79` | `0x1fbc8` | `0x3cf8` | `programs/pump/src/create_v2.rs:198` |
| 6027 | NotEnoughRemainingAccounts | `0x5a1c` | `0x2d0e0` | `0x5961` | `programs/pump/src/creator/distribute_creator_fee_v2.rs:152` |
| 6027 | NotEnoughRemainingAccounts | `0x5af4` | `0x2d7a0` | `0x5961` | `programs/pump/src/creator/distribute_creator_fee_v2.rs:149` |
| 6027 | NotEnoughRemainingAccounts | `0x618e` | `0x30c70` | `0x5f61` | `programs/pump/src/creator/distribute_creator_fee_v2.rs:346` |
| 6027 | NotEnoughRemainingAccounts | `0x61ea` | `0x30f50` | `0x5f61` | `programs/pump/src/creator/distribute_creator_fee_v2.rs:340` |
| 6027 | NotEnoughRemainingAccounts | `0x647d` | `0x323e8` | `0x633e` | `programs/pump/src/creator/distribute_creator_fees.rs:143` |
| 6027 | NotEnoughRemainingAccounts | `0x686d` | `0x34368` | `0x679e` | `programs/pump/src/creator/distribute_creator_fees.rs:325` |
| 6027 | NotEnoughRemainingAccounts | `0x7dd1` | `0x3ee88` | `0x7caa` | `programs/pump/src/fee_recipient.rs:47` |
| 6027 | NotEnoughRemainingAccounts | `0x8c46` | `0x46230` | `0x8bf4` | `programs/pump/src/migrate.rs:527` |
| 6027 | NotEnoughRemainingAccounts | `0xa518` | `0x528c0` | `0xa4cc` | `programs/pump/src/migrate_v2.rs:658` |
| 6027 | NotEnoughRemainingAccounts | `0xad96` | `0x56cb0` | `0xacfb` | `programs/pump/src/multi_hop_curve_swap.rs:214` |
| 6027 | NotEnoughRemainingAccounts | `0xe287` | `0x71438` | `0xdfdf` | `programs/pump/src/set_reserved_fee_recipients.rs:40` |
| 6028 | AllFeeRecipientsShouldBeNonZero | `0x7df4` | `0x3efa0` | `0x7caa` | `programs/pump/src/fee_recipient.rs:60` |
| 6028 | AllFeeRecipientsShouldBeNonZero | `0xe2ac` | `0x71560` | `0xdfdf` | `programs/pump/src/set_reserved_fee_recipients.rs:60` |
| 6029 | UnsortedNotUniqueFeeRecipients | `0x7f0b` | `0x3f858` | `0x7caa` | `programs/pump/src/fee_recipient.rs:78` |
| 6030 | CreatorShouldNotBeZero | `0x3de1` | `0x1ef08` | `0x3cf8` | `programs/pump/src/create_v2.rs:732` |
| 6030 | CreatorShouldNotBeZero | `0x47b8` | `0x23dc0` | `0x4542` | `programs/pump/src/creator/admin_cto.rs:307` |
| 6030 | CreatorShouldNotBeZero | `0x273f1` | `0x139f88` | `0x271d4` | `programs/pump/src/lib.rs:334` |
| 6031 | StartTimeInThePast | `0xfb97` | `0x7dcb8` | `0xf8e4` | `programs/pump/src/token_incentives/volume_accumulator.rs:359` |
| 6032 | EndTimeInThePast | `0xf99a` | `0x7ccd0` | `0xf8e4` | `programs/pump/src/token_incentives/volume_accumulator.rs:369` |
| 6033 | EndTimeBeforeStartTime | `0xfa2f` | `0x7d178` | `0xf8e4` | `programs/pump/src/token_incentives/volume_accumulator.rs:371` |
| 6034 | TimeRangeTooLarge | `0xfab2` | `0x7d590` | `0xf8e4` | `programs/pump/src/token_incentives/volume_accumulator.rs:373` |
| 6035 | EndTimeBeforeCurrentDay | `0xfbbe` | `0x7ddf0` | `0xf8e4` | `programs/pump/src/token_incentives/volume_accumulator.rs:394` |
| 6036 | SupplyUpdateForFinishedRange | `0xf9dc` | `0x7cee0` | `0xf8e4` | `programs/pump/src/token_incentives/volume_accumulator.rs:297` |
| 6037 | DayIndexAfterEndIndex | `0xfa58` | `0x7d2c0` | `0xf8e4` | `programs/pump/src/token_incentives/volume_accumulator.rs:309` |
| 6037 | DayIndexAfterEndIndex | `0xfaf1` | `0x7d788` | `0xf8e4` | `programs/pump/src/token_incentives/volume_accumulator.rs:337` |
| 6038 | DayInActiveRange | `0xfb37` | `0x7d9b8` | `0xf8e4` | `programs/pump/src/token_incentives/volume_accumulator.rs:338` |
| 6041 | BuyNotEnoughSolToCoverFees | `0x1017a` | `0x80bd0` | `0x100d9` | `programs/pump/src/trade_v3.rs:317` |
| 6041 | BuyNotEnoughSolToCoverFees | `0x27fc6` | `0x13fe30` | `0x27f22` | `programs/pump/src/buy_v2.rs:771` |
| 6041 | BuyNotEnoughSolToCoverFees | `0x281fc` | `0x140fe0` | `0x27f22` | `programs/pump/src/buy_v2.rs:873` |
| 6041 | BuyNotEnoughSolToCoverFees | `0x282c6` | `0x141630` | `0x27f22` | `programs/pump/src/buy_v2.rs:907` |
| 6041 | BuyNotEnoughSolToCoverFees | `0x291d7` | `0x148eb8` | `0x2913f` | `programs/pump/src/trade_v3.rs:882` |
| 6041 | BuyNotEnoughSolToCoverFees | `0x29260` | `0x149300` | `0x2913f` | `programs/pump/src/trade_v3.rs:891` |
| 6041 | BuyNotEnoughSolToCoverFees | `0x29f61` | `0x14fb08` | `0x29e9c` | `programs/pump/src/buy.rs:59` |
| 6041 | BuyNotEnoughSolToCoverFees | `0x2a01c` | `0x1500e0` | `0x29e9c` | `programs/pump/src/buy.rs:92` |
| 6042 | BuySlippageBelowMinTokensOut | `0x101a7` | `0x80d38` | `0x100d9` | `programs/pump/src/trade_v3.rs:326` |
| 6042 | BuySlippageBelowMinTokensOut | `0x282fc` | `0x1417e0` | `0x27f22` | `programs/pump/src/buy_v2.rs:921` |
| 6042 | BuySlippageBelowMinTokensOut | `0x283b8` | `0x141dc0` | `0x27f22` | `programs/pump/src/buy_v2.rs:986` |
| 6042 | BuySlippageBelowMinTokensOut | `0x28513` | `0x142898` | `0x27f22` | `programs/pump/src/buy_v2.rs:979` |
| 6042 | BuySlippageBelowMinTokensOut | `0x2931d` | `0x1498e8` | `0x2913f` | `programs/pump/src/trade_v3.rs:1001` |
| 6042 | BuySlippageBelowMinTokensOut | `0x29388` | `0x149c40` | `0x2913f` | `programs/pump/src/trade_v3.rs:993` |
| 6042 | BuySlippageBelowMinTokensOut | `0x2949f` | `0x14a4f8` | `0x2913f` | `programs/pump/src/trade_v3.rs:971` |
| 6042 | BuySlippageBelowMinTokensOut | `0x2a03e` | `0x1501f0` | `0x29e9c` | `programs/pump/src/buy.rs:110` |
| 6042 | BuySlippageBelowMinTokensOut | `0x2a08a` | `0x150450` | `0x29e9c` | `programs/pump/src/buy.rs:143` |
| 6043 | NameTooLong | `0x411c` | `0x208e0` | `0x3cf8` | `programs/pump/src/create_v2.rs:541` |
| 6044 | SymbolTooLong | `0x420c` | `0x21060` | `0x3cf8` | `programs/pump/src/create_v2.rs:547` |
| 6045 | UriTooLong | `0x422f` | `0x21178` | `0x3cf8` | `programs/pump/src/create_v2.rs:553` |
| 6046 | CreateV2Disabled | `0x3e44` | `0x1f220` | `0x3cf8` | `programs/pump/src/create_v2.rs:738` |
| 6048 | MayhemModeDisabled | `0x41e5` | `0x20f28` | `0x3cf8` | `programs/pump/src/create_v2.rs:709` |
| 6050 | UnableToDistributeCreatorVaultMigratedToSharingConfig | `0x536d` | `0x29b68` | `0x535b` | `programs/pump/src/creator/collect_creator_fee.rs:103` |
| 6050 | UnableToDistributeCreatorVaultMigratedToSharingConfig | `0x56d8` | `0x2b6c0` | `0x56c6` | `programs/pump/src/creator/collect_creator_fee.rs:198` |
| 6051 | SharingConfigNotActive | `0x5b90` | `0x2dc80` | `0x5b24` | `programs/pump/src/creator/distribute_creator_fee_v2.rs:205` |
| 6051 | SharingConfigNotActive | `0x6574` | `0x32ba0` | `0x6508` | `programs/pump/src/creator/distribute_creator_fees.rs:241` |
| 6052 | UnableToDistributeCreatorFeesToExecutableRecipient | `0x598a` | `0x2cc50` | `0x5961` | `programs/pump/src/creator/distribute_creator_fee_v2.rs:125` |
| 6052 | UnableToDistributeCreatorFeesToExecutableRecipient | `0x6367` | `0x31b38` | `0x633e` | `programs/pump/src/creator/distribute_creator_fees.rs:116` |
| 6054 | ShareholdersAndRemainingAccountsMismatch | `0x58ca` | `0x2c650` | `0x5877` | `programs/pump/src/creator/distribute_creator_fee_v2.rs:101` |
| 6054 | ShareholdersAndRemainingAccountsMismatch | `0x591a` | `0x2c8d0` | `0x5877` | `programs/pump/src/creator/distribute_creator_fee_v2.rs:112` |
| 6054 | ShareholdersAndRemainingAccountsMismatch | `0x62f7` | `0x317b8` | `0x623f` | `programs/pump/src/creator/distribute_creator_fees.rs:103` |
| 6055 | InvalidShareBps | `0x5a51` | `0x2d288` | `0x5961` | `programs/pump/src/creator/distribute_creator_fee_v2.rs:163` |
| 6055 | InvalidShareBps | `0x6426` | `0x32130` | `0x633e` | `programs/pump/src/creator/distribute_creator_fees.rs:148` |
| 6057 | BuybackFeeRecipientNotAuthorized | `0x13151` | `0x98a88` | `0x13087` | `programs/pump/src/lib.rs:1884` |
| 6058 | AllBuybackFeeRecipientsShouldBeNonZero | `0x132ec` | `0x99760` | `0x1315e` | `programs/pump/src/lib.rs:1895` |
| 6059 | NotUniqueBuybackFeeRecipients | `0x13241` | `0x99208` | `0x1315e` | `programs/pump/src/lib.rs:1905` |
| 6060 | BuybackBasisPointsOutOfRange | `0x13078` | `0x983c0` | `0x13042` | `programs/pump/src/lib.rs:1870` |
| 6061 | WrongBuybackFeeRecipientsCount | `0xe4f3` | `0x72798` | `0xe45a` | `programs/pump/src/set_reserved_fee_recipients.rs:121` |
| 6062 | BuybackFeeRecipientMissing | `0xdec8` | `0x6f640` | `0xde7d` | `programs/pump/src/sell.rs:145` |
| 6062 | BuybackFeeRecipientMissing | `0x13120` | `0x98900` | `0x13087` | `programs/pump/src/lib.rs:1879` |
| 6063 | UnsupportedQuoteMint | `0x3040` | `0x18200` | `0x2f9e` | `programs/pump/src/create_v2.rs:345` |
| 6063 | UnsupportedQuoteMint | `0x3361` | `0x19b08` | `0x30cf` | `programs/pump/src/create_v2.rs:390` |
| 6063 | UnsupportedQuoteMint | `0x3573` | `0x1ab98` | `0x3523` | `programs/pump/src/create_v2.rs:528` |
| 6063 | UnsupportedQuoteMint | `0x434a` | `0x21a50` | `0x3cf8` | `programs/pump/src/create_v2.rs:220` |
| 6063 | UnsupportedQuoteMint | `0x437f` | `0x21bf8` | `0x3cf8` | `programs/pump/src/create_v2.rs:243` |
| 6063 | UnsupportedQuoteMint | `0xa96d` | `0x54b68` | `0xa54d` | `programs/pump/src/migrate_v2.rs:747` |
| 6063 | UnsupportedQuoteMint | `0x129a0` | `0x94d00` | `0x12921` | `programs/pump/src/util/transfer_fee.rs:31` |
| 6063 | UnsupportedQuoteMint | `0x279bb` | `0x13cdd8` | `0x27737` | `programs/pump/src/buy_v2.rs:369` |
| 6063 | UnsupportedQuoteMint | `0x281a9` | `0x140d48` | `0x27f22` | `programs/pump/src/buy_v2.rs:780` |
| 6063 | UnsupportedQuoteMint | `0x28b1d` | `0x1458e8` | `0x288a1` | `programs/pump/src/sell_v2.rs:260` |
| 6064 | InvalidQuoteTokenProgram | `0x404c` | `0x20260` | `0x3cf8` | `programs/pump/src/create_v2.rs:205` |
| 6064 | InvalidQuoteTokenProgram | `0x4186` | `0x20c30` | `0x3cf8` | `programs/pump/src/create_v2.rs:210` |
| 6064 | InvalidQuoteTokenProgram | `0xf017` | `0x780b8` | `0xefaa` | `programs/pump/src/token_incentives/claim_token_incentives.rs:305` |
| 6065 | InvalidAssociatedQuoteBondingCurve | `0x3f4a` | `0x1fa50` | `0x3cf8` | `programs/pump/src/create_v2.rs:258` |
| 6066 | QuoteMintWhitelistFull | `0xd31b` | `0x698d8` | `0xd17b` | `programs/pump/src/quote_control/state.rs:82` |
| 6066 | QuoteMintWhitelistFull | `0x13484` | `0x9a420` | `0x13432` | `programs/pump/src/lib.rs:1971` |
| 6067 | QuoteMintAlreadyWhitelisted | `0xd27c` | `0x693e0` | `0xd17b` | `programs/pump/src/quote_control/state.rs:77` |
| 6067 | QuoteMintAlreadyWhitelisted | `0x1355a` | `0x9aad0` | `0x13432` | `programs/pump/src/lib.rs:1960` |
| 6068 | QuoteMintNotWhitelisted | `0xd37a` | `0x69bd0` | `0xd32f` | `programs/pump/src/quote_control/state.rs:99` |
| 6068 | QuoteMintNotWhitelisted | `0xd427` | `0x6a138` | `0xd3e5` | `programs/pump/src/quote_control/state.rs:113` |
| 6068 | QuoteMintNotWhitelisted | `0x135c3` | `0x9ae18` | `0x13585` | `programs/pump/src/lib.rs:1986` |
| 6069 | QuoteMintNotEligibleForWhitelist | `0xd1dc` | `0x68ee0` | `0xd17b` | `programs/pump/src/quote_control/state.rs:67` |
| 6069 | QuoteMintNotEligibleForWhitelist | `0xd22c` | `0x69160` | `0xd17b` | `programs/pump/src/quote_control/state.rs:72` |
| 6069 | QuoteMintNotEligibleForWhitelist | `0xd2ec` | `0x69760` | `0xd17b` | `programs/pump/src/quote_control/state.rs:62` |
| 6069 | QuoteMintNotEligibleForWhitelist | `0xd3b8` | `0x69dc0` | `0xd32f` | `programs/pump/src/quote_control/state.rs:92` |
| 6069 | QuoteMintNotEligibleForWhitelist | `0x134b9` | `0x9a5c8` | `0x13432` | `programs/pump/src/lib.rs:1955` |
| 6069 | QuoteMintNotEligibleForWhitelist | `0x1352b` | `0x9a958` | `0x13432` | `programs/pump/src/lib.rs:1950` |
| 6069 | QuoteMintNotEligibleForWhitelist | `0x13601` | `0x9b008` | `0x13585` | `programs/pump/src/lib.rs:1975` |
| 6070 | UnableToDistributeCreatorFeesToUninitializedAccount | `0x5b10` | `0x2d880` | `0x5961` | `programs/pump/src/creator/distribute_creator_fee_v2.rs:173` |
| 6071 | MayhemModeQuoteMintNotAllowed | `0x414b` | `0x20a58` | `0x3cf8` | `programs/pump/src/create_v2.rs:758` |
| 6072 | MissingCashbackAccounts | `0xda58` | `0x6d2c0` | `0xd9af` | `programs/pump/src/sell.rs:23` |
| 6073 | InvalidCashbackAccumulator | `0xda3b` | `0x6d1d8` | `0xd9af` | `programs/pump/src/sell.rs:33` |
| 6073 | InvalidCashbackAccumulator | `0xdab8` | `0x6d5c0` | `0xd9af` | `programs/pump/src/sell.rs:81` |
| 6073 | InvalidCashbackAccumulator | `0xdc12` | `0x6e090` | `0xdbb5` | `programs/pump/src/sell.rs:85` |
| 6074 | InvalidBondingCurveV2 | `0xdd52` | `0x6ea90` | `0xdbb5` | `programs/pump/src/sell.rs:107` |
| 6074 | InvalidBondingCurveV2 | `0xddcb` | `0x6ee58` | `0xdbb5` | `programs/pump/src/sell.rs:114` |
| 6074 | InvalidBondingCurveV2 | `0xde51` | `0x6f288` | `0xdddb` | `programs/pump/src/sell.rs:133` |
| 6074 | InvalidBondingCurveV2 | `0xde6d` | `0x6f368` | `0xdddb` | `programs/pump/src/sell.rs:126` |
| 6075 | InvalidQuoteControl | `0x300d` | `0x18068` | `0x2f9e` | `programs/pump/src/create_v2.rs:348` |
| 6075 | InvalidQuoteControl | `0x3080` | `0x18400` | `0x2f9e` | `programs/pump/src/create_v2.rs:353` |
| 6075 | InvalidQuoteControl | `0xd48e` | `0x6a470` | `0xd43c` | `programs/pump/src/quote_control/state.rs:145` |
| 6075 | InvalidQuoteControl | `0xd4aa` | `0x6a550` | `0xd43c` | `programs/pump/src/quote_control/state.rs:146` |
| 6075 | InvalidQuoteControl | `0xd504` | `0x6a820` | `0xd43c` | `programs/pump/src/quote_control/state.rs:158` |
| 6076 | InvalidCashbackRecipient | `0xf18b` | `0x78c58` | `0xefaa` | `programs/pump/src/token_incentives/claim_token_incentives.rs:342` |
| 6077 | CreatorFeeNotConfigurable | `0x3db0` | `0x1ed80` | `0x3cf8` | `programs/pump/src/create_v2.rs:774` |
| 6077 | CreatorFeeNotConfigurable | `0x4839` | `0x241c8` | `0x4542` | `programs/pump/src/creator/admin_cto.rs:334` |
| 6078 | CreatorFeeBpsOutOfRange | `0x3fff` | `0x1fff8` | `0x3cf8` | `programs/pump/src/create_v2.rs:778` |
| 6078 | CreatorFeeBpsOutOfRange | `0x481f` | `0x240f8` | `0x4542` | `programs/pump/src/creator/admin_cto.rs:338` |
| 6080 | CreatorFeeNotAllowedForCashbackCoin | `0x4800` | `0x24000` | `0x4542` | `programs/pump/src/creator/admin_cto.rs:330` |
| 6082 | CashbackDeprecated | `0x3d56` | `0x1eab0` | `0x3cf8` | `programs/pump/src/create_v2.rs:716` |
| 6083 | HolderRewardCreatorImmutable | `0x4654` | `0x232a0` | `0x4542` | `programs/pump/src/creator/admin_cto.rs:289` |
| 6083 | HolderRewardCreatorImmutable | `0x7011` | `0x38088` | `0x6fc1` | `programs/pump/src/creator/migrate_bonding_curve_creator.rs:46` |
| 6084 | HolderRewardDisabled | `0x3e81` | `0x1f408` | `0x3cf8` | `programs/pump/src/create_v2.rs:719` |
| 6084 | HolderRewardDisabled | `0x4752` | `0x23a90` | `0x4542` | `programs/pump/src/creator/admin_cto.rs:296` |
| 6085 | HolderRewardRecipientsMismatch | `0x68e6` | `0x34730` | `0x68ab` | `programs/pump/src/creator/distribute_fee_to_holders.rs:82` |
| 6085 | HolderRewardRecipientsMismatch | `0x6d74` | `0x36ba0` | `0x6c3e` | `programs/pump/src/creator/distribute_fee_to_holders.rs:122` |
| 6086 | HolderRewardsRentFloor | `0x6e57` | `0x372b8` | `0x6c3e` | `programs/pump/src/creator/distribute_fee_to_holders.rs:164` |
| 6087 | HolderRewardTokenAccountMissing | `0x6d3f` | `0x369f8` | `0x6c3e` | `programs/pump/src/creator/distribute_fee_to_holders.rs:120` |
| 6088 | CtoNotAllowedForMayhemCoin | `0x5043` | `0x28218` | `0x4ec9` | `programs/pump/src/creator/admin_cto.rs:284` |
| 6089 | CtoNewCreatorRequired | `0x471d` | `0x238e8` | `0x4542` | `programs/pump/src/creator/admin_cto.rs:306` |
| 6090 | CtoNewCreatorNotAllowed | `0x468c` | `0x23460` | `0x4542` | `programs/pump/src/creator/admin_cto.rs:298` |
| 6091 | CreatorFeeNotConfigurableForQuote | `0x4780` | `0x23c00` | `0x4542` | `programs/pump/src/creator/admin_cto.rs:326` |
| 6092 | CtoCreatorAccountNotWritable | `0x5062` | `0x28310` | `0x4ec9` | `programs/pump/src/creator/admin_cto.rs:556` |
| 6093 | CtoSharedVaultFrozen | `0x4980` | `0x24c00` | `0x48e6` | `programs/pump/src/creator/admin_cto.rs:719` |
| 6093 | CtoSharedVaultFrozen | `0x49fb` | `0x24fd8` | `0x48e6` | `programs/pump/src/creator/admin_cto.rs:660` |
| 6094 | CashbackCoinNotSupported | `0xfc83` | `0x7e418` | `0xfc16` | `programs/pump/src/trade_v3.rs:150` |
| 6095 | CreatorFeesNotSwept | `0x48c4` | `0x24620` | `0x4542` | `programs/pump/src/creator/admin_cto.rs:410` |
| 6095 | CreatorFeesNotSwept | `0x5b52` | `0x2da90` | `0x5b24` | `programs/pump/src/creator/distribute_creator_fee_v2.rs:213` |
| 6095 | CreatorFeesNotSwept | `0x6536` | `0x329b0` | `0x6508` | `programs/pump/src/creator/distribute_creator_fees.rs:249` |
| 6095 | CreatorFeesNotSwept | `0x702d` | `0x38168` | `0x6fc1` | `programs/pump/src/creator/migrate_bonding_curve_creator.rs:53` |
| 6096 | FeeTiersEmpty | `0x113bf` | `0x89df8` | `0x11369` | `programs/pump/src/util/fee.rs:162` |
| 6097 | FeeConfigTooShort | `0x1144d` | `0x8a268` | `0x113d9` | `programs/pump/src/util/fee.rs:183` |
| 6098 | MultiHopDiscontinuousPath | `0xae20` | `0x57100` | `0xacfb` | `programs/pump/src/multi_hop_curve_swap.rs:262` |
| 6098 | MultiHopDiscontinuousPath | `0xb8f6` | `0x5c7b0` | `0xb70e` | `programs/pump/src/multi_hop_curve_swap.rs:546` |
| 6099 | InvalidQuoteBondingCurve | `0x3434` | `0x1a1a0` | `0x33d9` | `programs/pump/src/create_v2.rs:442` |
| 6099 | InvalidQuoteBondingCurve | `0x34bf` | `0x1a5f8` | `0x33d9` | `programs/pump/src/create_v2.rs:437` |
| 6099 | InvalidQuoteBondingCurve | `0x3506` | `0x1a830` | `0x33d9` | `programs/pump/src/create_v2.rs:449` |
| 6100 | QuoteBondingCurveNotEligible | `0x3137` | `0x189b8` | `0x30cf` | `programs/pump/src/create_v2.rs:395` |
| 6100 | QuoteBondingCurveNotEligible | `0xc25c` | `0x612e0` | `0xc1dc` | `programs/pump/src/pump_quote.rs:90` |
| 6101 | QuotePoolAccountsRequired | `0x3301` | `0x19808` | `0x30cf` | `programs/pump/src/create_v2.rs:493` |
| 6102 | QuotePoolNotFound | `0xca86` | `0x65430` | `0xca47` | `programs/pump/src/pump_quote.rs:407` |
| 6103 | InvalidQuotePool | `0xc7ee` | `0x63f70` | `0xc79e` | `programs/pump/src/pump_quote.rs:279` |
| 6103 | InvalidQuotePool | `0xc80a` | `0x64050` | `0xc79e` | `programs/pump/src/pump_quote.rs:280` |
| 6103 | InvalidQuotePool | `0xc8ae` | `0x64570` | `0xc86b` | `programs/pump/src/pump_quote.rs:307` |
| 6103 | InvalidQuotePool | `0xc971` | `0x64b88` | `0xc911` | `programs/pump/src/pump_quote.rs:365` |
| 6103 | InvalidQuotePool | `0xc9a8` | `0x64d40` | `0xc911` | `programs/pump/src/pump_quote.rs:366` |
| 6103 | InvalidQuotePool | `0xc9d4` | `0x64ea0` | `0xc911` | `programs/pump/src/pump_quote.rs:371` |
| 6103 | InvalidQuotePool | `0xca10` | `0x65080` | `0xc911` | `programs/pump/src/pump_quote.rs:372` |
| 6103 | InvalidQuotePool | `0xca35` | `0x651a8` | `0xc911` | `programs/pump/src/pump_quote.rs:378` |
| 6103 | InvalidQuotePool | `0xcb13` | `0x65898` | `0xca47` | `programs/pump/src/pump_quote.rs:406` |
| 6103 | InvalidQuotePool | `0xcb4a` | `0x65a50` | `0xca47` | `programs/pump/src/pump_quote.rs:410` |
| 6103 | InvalidQuotePool | `0xcb8a` | `0x65c50` | `0xca47` | `programs/pump/src/pump_quote.rs:415` |
| 6104 | QuoteReservesOutOfRange | `0xc789` | `0x63c48` | `0xc728` | `programs/pump/src/pump_quote.rs:241` |
| 6105 | CurveDepthExceeded | `0xc1c6` | `0x60e30` | `0xc150` | `programs/pump/src/pump_quote.rs:62` |
| 6106 | MultiHopHopFeesMismatch | `0xadb2` | `0x56d90` | `0xacfb` | `programs/pump/src/multi_hop_curve_swap.rs:218` |
| 6107 | QuoteCurveAwaitingMigration | `0x32e5` | `0x19728` | `0x30cf` | `programs/pump/src/create_v2.rs:466` |
| 6108 | MultiHopMayhemCurveNotSupported | `0xb6dd` | `0x5b6e8` | `0xb676` | `programs/pump/src/multi_hop_curve_swap.rs:484` |
| 6109 | QuoteChainAccountsRequired | `0x33ca` | `0x19e50` | `0x3398` | `programs/pump/src/create_v2.rs:412` |
| 6110 | QuoteMintNotWritable | `0x9674` | `0x4b3a0` | `0x94f0` | `programs/pump/src/migrate_v2.rs:335` |

## Notes and caveats

- `stw` sites: 366, distinct codes: 96, named variants in `name()`: 111 (0..110).
- The scan of `[6000,6120]` also sees 9 `call` immediates and 1 `add64` immediate in that
  range; those are relative call targets/arithmetic constants, not error codes, and are
  excluded. This is why a raw immediate count can differ from the `stw`-site count.
- `6024 Overflow` (98 sites) and `6025 Truncation` (22 sites) are emitted by the arithmetic
  helpers and therefore dominate the site count; they are not distinct guards.
- `6047` is spelled `CpitializeMayhemFailed` in the deployed name table (`0x1b85a6/22`);
  this is a binary string typo, not a transcription error here. It has no `stw` site in
  `pump` (see unraised list).
- The `name()` table is the deployed variant-name table (not the `#[msg]` text table).
  The function range is pc `0x2bd95..0x2bfb9` (438 insns); the common epilogue is
  pc `0x2bf54` (`mov r1,r4; call 0x35e6e; exit`). The emulator returns the `(ptr,len)` set on
  the taken path; anchor checks: `0x1b81c6/13` NotAuthorized, `0x1b81f7/20`
  TooLittleSolReceived, `0x1b820b/28` MintDoesNotMatchBondingCurve, `0x1b8227/20`
  BondingCurveComplete, `0x1b8298/23` AccountTypeNotSupported, `0x1b83f7/14` SellZeroAmount.
- `line` is the nearest small-`stw` immediate in the AnchorError tuple (+/-6 insns). For
  reused error structs the store can be before the code store (e.g. `0x2a70`: line 88 at
  `0x2a6d`, code 6004 at `0x2a70`); the extractor checks both directions. All 366 sites
  resolved a file and a line, but the line is from the original source revision and cannot
  be checked against the reformatted recovered source line-by-line.
- `handler/helper func` is the sbftool function start containing the site; many sites live
  in shared helpers (e.g. `0x2922`) called by several handlers. The origin file is the
  stronger attribution than the helper address.

## Reproduce

```
python sbftool.py dis D:\dev\ext\pumpfun-source\evidence\original\pump\deployed.so 0x2bd95 12
# scan: for ins in Prog(so).ins.values(): if ins.mn=="stw" and 6000 <= ins.imm <= 6110
# name: emulate pc 0x2bd95 with r1=imm-6000; read (r2,r3) at pc 0x2bf54
```

Machine-readable dump of all sites and names: `pump_error_sites.json`.
