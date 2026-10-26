> **[VERIFIED 2026-10-26]** There is NO PumpError enum revision mismatch. The recovered
> lib.rs enum matches the deployed binary exactly: index 3=TooLittleSolReceived(6003),
> 4=MintDoesNotMatchBondingCurve(6004), 5=BondingCurveComplete(6005), 10=AccountTypeNotSupported(6010),
> 22=SellZeroAmount(6022) — all confirmed by enumerating the recovered enum AND the deployed
> PumpError::name() table + raise-site counts. Any 'different revision / 6010-vs-6022 shift'
> statement below is SUPERSEDED and wrong. (The admin_cto guard-SET difference is a separate,
> real divergence — not about the error enum.)

# Error-code catalogs (deployed programs)

Private analysis for the user. Tags: **[B]** = the code immediate and raise site are present in
the deployed ELF; **[R]** = the name comes from the recovered source/IDL; **[partial]** = the
code/name attribution is not independently verified for this capture.

Method: every instruction immediate in `[6000, 6120]` was scanned in each ELF and grouped by
code; sites are `sbftool` pc units (vaddr/8). Custom codes are `6000 + enum discriminant`.
For **pump**, the name is now resolved from the deployed binary's `PumpError::name()` table
(pc `0x2bd95`) rather than the recovered enum; see `pump_error_map.md` for the full
code -> name -> site map. The earlier revision-conflict claim was wrong: the binary puts
`AccountTypeNotSupported` at **6010** (not 6022), `SellZeroAmount` at **6022**,
`MintDoesNotMatchBondingCurve` at **6004**, and `BondingCurveComplete` at **6005**. The
pump rows below are corrected accordingly. For non-pump programs the name still comes from
the recovered enum / official IDL; where a cluster spec binary-verified a name it is used
verbatim, and unverified names are marked **(source-enum candidate)**. Codes outside a
program's enum range were ignored (they are other immediates, not that program's error
codes).

Anchor built-in codes are listed per program as a summary (they are account/constraint
errors, not program enums).

## pump

### Program error codes (observed in `.text`)

| code | name | sites (first 4) | tag |
|---:|---|---|---|
| 6000 | `NotAuthorized` | 0x7c7c 0x7c98 0xe5a4 0x26aee | [B] name-table + site |
| 6002 | `TooMuchSolRequired` | 0x27a70 0x2837d 0x290e6 0x29422 | [B] name-table + site |
| 6003 | `TooLittleSolReceived` | 0x28bd7 0x29622 0x2a682 | [B] name-table + site |
| 6004 | `MintDoesNotMatchBondingCurve` | 0x2a70 0x2c91 0xfd75 | [B] name-table (`0x1b820b/28`) + site |
| 6005 | `BondingCurveComplete` | 0xfc67 0x277b1 0x27fa8 0x288ee | [B] name-table (`0x1b8227/20`) + site |
| 6006 | `BondingCurveNotComplete` | 0x7fce 0x93f2 | [B] name-table + site (0x34f58 is a call imm, not a store) |
| 6010 | `AccountTypeNotSupported` | 0x2990 0x2d13 0x2d46 0x7769 | [B] name-table (`0x1b8298/23`) + site |
| 6011 | `InitialRealTokenReservesShouldBeLessThanTokenTotalSupply` | 0x26e4f | [B] name-table + site (0x338bc is a call imm, not a store) |
| 6012 | `InitialVirtualTokenReservesShouldBeGreaterThanInitialRealTokenReserves` | 0x26d7e | [B] name-table + site |
| 6013 | `FeeBasisPointsGreaterThanMaximum` | 0x26dd2 0x26df1 | [B] name-table + site |
| 6014 | `AllZerosWithdrawAuthority` | 0x26e75 | [B] name-table + site |
| 6015 | `PoolMigrationFeeShouldBeLessThanFinalRealSolReserves` | 0x26ead | [B] name-table + site |
| 6018 | `DisabledMigrate` | (no stw site in pump; 0x338b5 is a call imm) | [B] name-table; unraised here |
| 6019 | `InvalidCreator` | 0x479e | [B] name-table + site |
| 6020 | `BuyZeroAmount` | 0xad74 0xbb70 0x277d0 0x27f4b | [B] name-table + site |
| 6021 | `NotEnoughTokensToBuy` | 0xbaef 0x104f1 0x105c4 0x2795b | [B] name-table + site |
| 6022 | `SellZeroAmount` | 0xba48 0x28945 0x29583 0x2a5c0 | [B] name-table (`0x1b83f7/14`) + site |
| 6023 | `NotEnoughTokensToSell` | 0x28abf 0x295af 0x2a5ef | [B] name-table + site |
| 6024 | `Overflow` | 0x2dea 0x2ebf 0x2f8f 0x3382 | [B] name-table + site |
| 6025 | `Truncation` | 0x2da9 0x2e2b 0x2e6c 0x2f0d | [B] name-table + site |
| 6026 | `DivisionByZero` | 0xc2ec 0xc3ff 0xc4ae 0xc543 | [B] name-table + site |
| 6027 | `NotEnoughRemainingAccounts` | 0x3f79 0x5a1c 0x5af4 0x618e | [B] name-table + site |
| 6028 | `AllFeeRecipientsShouldBeNonZero` | 0x7df4 0xe2ac | [B] name-table + site |
| 6029 | `UnsortedNotUniqueFeeRecipients` | 0x7f0b | [B] name-table + site |
| 6030 | `CreatorShouldNotBeZero` | 0x3de1 0x47b8 0x273f1 | [B] name-table + site |
| 6031 | `StartTimeInThePast` | 0xfb97 | [B] name-table + site |
| 6032 | `EndTimeInThePast` | 0xf99a | [B] name-table + site (0x34f31 is a call imm, not a store) |
| 6033 | `EndTimeBeforeStartTime` | 0xfa2f | [B] name-table + site |
| 6034 | `TimeRangeTooLarge` | 0xfab2 | [B] name-table + site |
| 6035 | `EndTimeBeforeCurrentDay` | 0xfbbe | [B] name-table + site |
| 6036 | `SupplyUpdateForFinishedRange` | 0xf9dc | [B] name-table + site |
| 6037 | `DayIndexAfterEndIndex` | 0xfa58 0xfaf1 | [B] name-table + site |
| 6038 | `DayInActiveRange` | 0xfb37 | [B] name-table + site |
| 6041 | `BuyNotEnoughSolToCoverFees` | 0x1017a 0x27fc6 0x281fc 0x282c6 | [B] name-table + site |
| 6042 | `BuySlippageBelowMinTokensOut` | 0x101a7 0x282fc 0x283b8 0x28513 | [B] name-table + site |
| 6043 | `NameTooLong` | 0x411c | [B] name-table + site |
| 6044 | `SymbolTooLong` | 0x420c | [B] name-table + site |
| 6045 | `UriTooLong` | 0x422f | [B] name-table + site (0x346d0 is a call imm, not a store) |
| 6046 | `CreateV2Disabled` | 0x3e44 | [B] name-table + site |
| 6048 | `MayhemModeDisabled` | 0x41e5 | [B] name-table + site |
| 6050 | `UnableToDistributeCreatorVaultMigratedToSharingConfig` | 0x536d 0x56d8 | [B] name-table + site |
| 6051 | `SharingConfigNotActive` | 0x5b90 0x6574 | [B] name-table + site |
| 6052 | `UnableToDistributeCreatorFeesToExecutableRecipient` | 0x598a 0x6367 | [B] name-table + site |
| 6054 | `ShareholdersAndRemainingAccountsMismatch` | 0x58ca 0x591a 0x62f7 | [B] name-table + site |
| 6055 | `InvalidShareBps` | 0x5a51 0x6426 | [B] name-table + site |
| 6057 | `BuybackFeeRecipientNotAuthorized` | 0x13151 | [B] name-table + site |
| 6058 | `AllBuybackFeeRecipientsShouldBeNonZero` | 0x132ec | [B] name-table + site |
| 6059 | `NotUniqueBuybackFeeRecipients` | 0x13241 | [B] name-table + site |
| 6060 | `BuybackBasisPointsOutOfRange` | 0x13078 | [B] name-table + site |
| 6061 | `WrongBuybackFeeRecipientsCount` | 0xe4f3 | [B] name-table + site |
| 6062 | `BuybackFeeRecipientMissing` | 0xdec8 0x13120 | [B] name-table + site |
| 6063 | `UnsupportedQuoteMint` | 0x3040 0x3361 0x3573 0x434a | [B] name-table + site |
| 6064 | `InvalidQuoteTokenProgram` | 0x404c 0x4186 0xf017 | [B] name-table + site |
| 6065 | `InvalidAssociatedQuoteBondingCurve` | 0x3f4a | [B] name-table + site |
| 6066 | `QuoteMintWhitelistFull` | 0xd31b 0x13484 | [B] name-table + site |
| 6067 | `QuoteMintAlreadyWhitelisted` | 0xd27c 0x1355a | [B] name-table + site |
| 6068 | `QuoteMintNotWhitelisted` | 0xd37a 0xd427 0x135c3 | [B] name-table + site |
| 6069 | `QuoteMintNotEligibleForWhitelist` | 0xd1dc 0xd22c 0xd2ec 0xd3b8 | [B] name-table + site |
| 6070 | `UnableToDistributeCreatorFeesToUninitializedAccount` | 0x5b10 | [B] name-table + site |
| 6071 | `MayhemModeQuoteMintNotAllowed` | 0x414b | [B] name-table + site |
| 6072 | `MissingCashbackAccounts` | 0xda58 | [B] name-table + site |
| 6073 | `InvalidCashbackAccumulator` | 0xda3b 0xdab8 0xdc12 | [B] name-table + site |
| 6074 | `InvalidBondingCurveV2` | 0xdd52 0xddcb 0xde51 0xde6d | [B] name-table + site |
| 6075 | `InvalidQuoteControl` | 0x300d 0x3080 0xd48e 0xd4aa | [B] name-table + site |
| 6076 | `InvalidCashbackRecipient` | 0xf18b | [B] name-table + site |
| 6077 | `CreatorFeeNotConfigurable` | 0x3db0 0x4839 | [B] name-table + site |
| 6078 | `CreatorFeeBpsOutOfRange` | 0x3fff 0x481f | [B] name-table + site (0x344ad is a call imm, not a store) |
| 6080 | `CreatorFeeNotAllowedForCashbackCoin` | 0x4800 | [B] name-table + site |
| 6081 | `BondingCurveAlreadyMigrated` | (no stw site in pump; 0x23917 is a call imm) | [B] name-table; unraised here |
| 6082 | `CashbackDeprecated` | 0x3d56 | [B] name-table + site |
| 6083 | `HolderRewardCreatorImmutable` | 0x4654 0x7011 | [B] name-table + site |
| 6084 | `HolderRewardDisabled` | 0x3e81 0x4752 | [B] name-table + site |
| 6085 | `HolderRewardRecipientsMismatch` | 0x68e6 0x6d74 | [B] name-table + site |
| 6086 | `HolderRewardsRentFloor` | 0x6e57 | [B] name-table + site |
| 6087 | `HolderRewardTokenAccountMissing` | 0x6d3f | [B] name-table + site |
| 6088 | `CtoNotAllowedForMayhemCoin` | 0x5043 | [B] name-table + site |
| 6089 | `CtoNewCreatorRequired` | 0x471d | [B] name-table + site |
| 6090 | `CtoNewCreatorNotAllowed` | 0x468c | [B] name-table + site |
| 6091 | `CreatorFeeNotConfigurableForQuote` | 0x4780 | [B] name-table + site |
| 6092 | `CtoCreatorAccountNotWritable` | 0x5062 | [B] name-table + site |
| 6093 | `CtoSharedVaultFrozen` | 0x4980 0x49fb | [B] name-table + site |
| 6094 | `CashbackCoinNotSupported` | 0xfc83 | [B] name-table + site |
| 6095 | `CreatorFeesNotSwept` | 0x48c4 0x5b52 0x6536 0x702d | [B] name-table + site |
| 6096 | `FeeTiersEmpty` | 0x113bf | [B] name-table + site |
| 6097 | `FeeConfigTooShort` | 0x1144d | [B] name-table + site |
| 6098 | `MultiHopDiscontinuousPath` | 0xae20 0xb8f6 | [B] name-table + site |
| 6099 | `InvalidQuoteBondingCurve` | 0x3434 0x34bf 0x3506 | [B] name-table + site |
| 6100 | `QuoteBondingCurveNotEligible` | 0x3137 0xc25c | [B] name-table + site |
| 6101 | `QuotePoolAccountsRequired` | 0x3301 | [B] name-table + site |
| 6102 | `QuotePoolNotFound` | 0xca86 | [B] name-table + site |
| 6103 | `InvalidQuotePool` | 0xc7ee 0xc80a 0xc8ae 0xc971 | [B] name-table + site |
| 6104 | `QuoteReservesOutOfRange` | 0xc789 | [B] name-table + site |
| 6105 | `CurveDepthExceeded` | 0xc1c6 | [B] name-table + site |
| 6106 | `MultiHopHopFeesMismatch` | 0xadb2 | [B] name-table + site |
| 6107 | `QuoteCurveAwaitingMigration` | 0x32e5 | [B] name-table + site |
| 6108 | `MultiHopMayhemCurveNotSupported` | 0xb6dd | [B] name-table + site |
| 6109 | `QuoteChainAccountsRequired` | 0x33ca | [B] name-table + site |
| 6110 | `QuoteMintNotWritable` | 0x9674 | [B] name-table + site |

- In the enum but no `stw` site in pump (15): 6001 AlreadyInitialized, 6007 NotInitialized, 6008 WithdrawTooFrequent, 6009 NewSizeShouldBeGreaterThanCurrentSize, 6016 PoolMigrationFeeShouldBeGreaterThanCreatorFeePlusMaxMigrateFees, 6017 DisabledWithdraw, 6018 DisabledMigrate, 6039 InvalidIncentiveMint, 6040 BuyNotEnoughSolToCoverRent, 6047 CpitializeMayhemFailed, 6049 CreatorMigratedToSharingConfig, 6053 BondingCurveAndSharingConfigCreatorMismatch, 6056 CashbackNotEnabled, 6079 CreatorFeeNotEditable, 6081 BondingCurveAlreadyMigrated.
- Full `stw`-only site list (366 rows), the binary name table, and the correction rationale: `pump_error_map.md`.

### Anchor built-in codes observed

| code | Anchor name | count |
|---:|---|---:|
| 2000 | ConstraintMut | 172 |
| 2001 | ConstraintHasOne | 4 |
| 2002 | ConstraintSigner | 5 |
| 2003 | ConstraintRaw | 6 |
| 2004 | ConstraintOwner | 6 |
| 2005 | ConstraintRentExempt | 23 |
| 2006 | ConstraintSeeds | 193 |
| 2007 | ConstraintExecutable | 2 |
| 2009 | ConstraintAssociated | 9 |
| 2011 | ConstraintClose | 2 |
| 2012 | ConstraintAddress | 5 |
| 2013 | ConstraintZero | 1 |
| 2014 | ConstraintTokenMint | 8 |
| 2015 | ConstraintTokenOwner | 12 |
| 2019 | ConstraintSpace | 5 |
| 2021 | ConstraintTokenTokenProgram | 1 |
| 2022 | ConstraintMintTokenProgram | 1 |
| 2023 | ConstraintAssociatedTokenAccount | 11 |

## pump_amm

### Program error codes (observed in `.text`)

| code | name | sites (first 4) | tag |
|---:|---|---|---|
| 6000 | `FeeBasisPointsExceedsMaximum` | 0xc2fd 0xc34a 0xc397 0xf566 | [B]/[R] |
| 6001 | `ZeroBaseAmount` | 0x41cf 0x59e1 0x6f66 0x753c | [B]/[R] |
| 6002 | `ZeroQuoteAmount` | 0x411a 0x4167 0x5a1b 0x6fe0 | [B]/[R] |
| 6003 | `TooLittlePoolTokenLiquidity` | 0x42d1 0x5c7e 0x780e 0x861a | [B]/[R] |
| 6004 | `ExceededSlippage` | 0x41ac 0x6055 0x615a 0x65ea | [B]/[R] |
| 6005 | `InvalidAdmin` | 0x373d 0xc511 0xc566 | [B]/[R] |
| 6006 | `UnsupportedBaseMint` | 0x5a9f | [B]/[R] |
| 6007 | `UnsupportedQuoteMint` | 0x5ac1 0xddfc 0xe8a4 | [B]/[R] |
| 6009 | `InvalidQuoteMint` | 0x9f09 | [B]/[R] |
| 6011 | `AllProtocolFeeRecipientsShouldBeNonZero` | 0x34f4 0xc4a6 | [B]/[R] |
| 6012 | `UnsortedNotUniqueProtocolFeeRecipients` | 0xc4c4 | [B]/[R] |
| 6013 | `InvalidProtocolFeeRecipient` | 0xb274 0xb316 | [B]/[R] |
| 6016 | `BuyMoreBaseAmountThanPoolReserves` | 0x239e | [B]/[R] |
| 6017 | `DisabledCreatePool` | 0x59ac | [B]/[R] |
| 6018 | `DisabledDeposit` | 0x6025 | [B]/[R] |
| 6019 | `DisabledWithdraw` | 0x65aa | [B]/[R] |
| 6020 | `DisabledBuy` | 0x403c 0x6fc2 0x7598 0x824f | [B]/[R] |
| 6021 | `DisabledSell` | 0x81dc 0x940e 0xad8f | [B]/[R] |
| 6022 | `SameMint` | 0x5adb | [B]/[R] |
| 6023 | `Overflow` | 0x25ae 0x2605 0x45c2 0x4e8d | [B]/[R] |
| 6024 | `Truncation` | 0x23bc 0x2453 0x24f9 0x2679 | [B]/[R] |
| 6025 | `DivisionByZero` | 0x2433 0x24d9 0x2550 0x2625 | [B]/[R] |
| 6027 | `AccountTypeNotSupported` | 0x5d32 0x5dea 0x7b5e 0x80c6 | [B]/[R] |
| 6028 | `OnlyCanonicalPumpPoolsCanHaveCoinCreator` | 0x297c 0x4a6d 0x597b | [B]/[R] |
| 6030 | `StartTimeInThePast` | 0xde17 | [B]/[R] |
| 6031 | `EndTimeInThePast` | 0xdc1a | [B]/[R] |
| 6032 | `EndTimeBeforeStartTime` | 0xdcaf 0xdde3 | [B]/[R] |
| 6033 | `TimeRangeTooLarge` | 0xdd32 | [B]/[R] |
| 6034 | `EndTimeBeforeCurrentDay` | 0xde3e | [B]/[R] |
| 6035 | `SupplyUpdateForFinishedRange` | 0xdc5c 0x21b7f | [B]/[R] |
| 6036 | `DayIndexAfterEndIndex` | 0xdcd8 0xdd71 | [B]/[R] |
| 6037 | `DayInActiveRange` | 0xddb7 | [B]/[R] |
| 6039 | `BuyNotEnoughQuoteTokensToCoverFees` | 0x7631 0x76e8 0xa291 0xab27 | [B]/[R] |
| 6040 | `BuySlippageBelowMinBaseAmountOut` | 0x7737 0x77bb 0x77e7 0xa2c0 | [B]/[R] |
| 6041 | `MayhemModeDisabled` | 0x5a77 | [B]/[R] |
| 6042 | `OnlyPumpPoolsMayhemMode` | 0x57e6 | [B]/[R] |
| 6043 | `MayhemModeInDesiredState` | 0x379f | [B]/[R] |
| 6044 | `NotEnoughRemainingAccounts` | 0x34cf 0x7cee 0x8052 | [B]/[R] |
| 6048 | `CreatorVaultMigratedToSharingConfig` | 0x467d | [B]/[R] |
| 6049 | `CashbackNotEnabled` | 0x5850 | [B]/[R] |
| 6050 | `OnlyPumpPoolsCashback` | 0x5809 | [B]/[R] |
| 6051 | `CashbackNotInDesiredState` | 0x36e1 | [B]/[R] |
| 6053 | `BuybackFeeRecipientNotAuthorized` | 0xc670 0xc6ae 0xc6e2 | [B]/[R] |
| 6054 | `AllBuybackFeeRecipientsShouldBeNonZero` | 0xc87d | [B]/[R] |
| 6055 | `NotUniqueBuybackFeeRecipients` | 0xc7d2 | [B]/[R] |
| 6056 | `BuybackBasisPointsOutOfRange` | 0xc5be | [B]/[R] |
| 6057 | `WrongBuybackFeeRecipientsCount` | 0x39ab | [B]/[R] |
| 6058 | `BuybackFeeRecipientMissing` | 0x6e7a 0x6ec2 | [B]/[R] |
| 6059 | `MissingCashbackAccounts` | 0x6aeb 0x9938 0x99d4 | [B]/[R] |
| 6060 | `InvalidCashbackAccumulator` | 0x9a0a 0x9a41 0x9a73 0x9b72 | [B]/[R] |
| 6061 | `InvalidCashbackAccumulatorAta` | 0x6ace 0x6b45 0x9c3b 0x9cf4 | [B]/[R] |
| 6062 | `InvalidPoolV2` | 0x9dcb 0x9de7 0x21935 | [B]/[R] |
| 6063 | `InsufficientRealQuoteReserves` | 0x949c 0xa368 | [B]/[R] |
| 6065 | `PoolCannotBoost` | 0x4071 | [B]/[R] |
| 6066 | `BoostDisabled` | 0x40fc | [B]/[R] |
| 6067 | `SeedLockViolation` | 0x6546 | [B]/[R] |
| 6068 | `CreatorFeeNotConfigurable` | 0x2c01 | [B]/[R] |
| 6069 | `CreatorFeeBpsOutOfRange` | 0x2ae1 | [B]/[R] |
| 6071 | `CreatorFeeNotAllowedForCashbackCoin` | 0x2a9b | [B]/[R] |
| 6074 | `HolderRewardCreatorImmutable` | 0x2a17 0x4818 | [B]/[R] |
| 6075 | `CtoNotAllowedForMayhemPool` | 0x29fb | [B]/[R] |
| 6076 | `InvalidHolderRewardCoinCreator` | 0x2a58 | [B]/[R] |
| 6077 | `CreatorFeeNotConfigurableForQuote` | 0x2ac2 | [B]/[R] |
| 6078 | `OnlyPumpPools` | 0x81f8 | [B]/[R] |
| 6079 | `CashbackCoinNotSupported` | 0x8284 0x9e2c | [B]/[R] |
| 6080 | `MayhemPoolNotSupported` | 0x836c | [B]/[R] |
| 6081 | `CreatorFeesNotSwept` | 0x2aff 0x4834 | [B]/[R] |
| 6082 | `FeeTiersEmpty` | 0x27fc | [B]/[R] |
| 6083 | `FeeConfigTooShort` | 0x287a | [B]/[R] |
| 6084 | `MultiHopDiscontinuousPath` | 0x7d3c 0x7d70 0x8ab4 | [B]/[R] |
| 6085 | `MultiHopCurveRunMismatch` | 0x92e6 0x9341 | [B]/[R] |
| 6086 | `MultiHopMixedDirection` | 0x7fbb | [B]/[R] |
| 6087 | `SelfTransferNotAllowed` | 0xdf04 | [B]/[R] |
| 6088 | `QuoteMintNotWritable` | 0x44d3 | [B]/[R] |

- In the enum but no direct immediate isolated: 6008 InvalidBaseMint, 6010 InvalidLpMint, 6014 InvalidPoolBaseTokenAccount, 6015 InvalidPoolQuoteTokenAccount, 6026 NewSizeLessThanCurrentSize, 6029 InvalidAdminSetCoinCreatorAuthority, 6038 InvalidIncentiveMint, 6045 InvalidSharingConfigBaseMint, 6046 InvalidSharingConfigCoinCreator, 6047 CoinCreatorMigratedToSharingConfig, 6052 TokensInVaultLessThanCashbackEarned, 6064 BoostPoolLiquidityUnsupported, 6070 CreatorFeeNotEditable, 6072 SharingConfigNotActive, 6073 NotAuthorized.

### Anchor built-in codes observed

| code | Anchor name | count |
|---:|---|---:|
| 2000 | ConstraintMut | 111 |
| 2001 | ConstraintHasOne | 4 |
| 2002 | ConstraintSigner | 2 |
| 2003 | ConstraintRaw | 6 |
| 2004 | ConstraintOwner | 5 |
| 2005 | ConstraintRentExempt | 23 |
| 2006 | ConstraintSeeds | 73 |
| 2007 | ConstraintExecutable | 2 |
| 2009 | ConstraintAssociated | 6 |
| 2011 | ConstraintClose | 2 |
| 2013 | ConstraintZero | 1 |
| 2014 | ConstraintTokenMint | 9 |
| 2015 | ConstraintTokenOwner | 16 |
| 2019 | ConstraintSpace | 4 |
| 2021 | ConstraintTokenTokenProgram | 2 |
| 2022 | ConstraintMintTokenProgram | 2 |
| 2023 | ConstraintAssociatedTokenAccount | 13 |

## pump_fees

### Program error codes (observed in `.text`)

| code | name | sites (first 4) | tag |
|---:|---|---|---|
| 6000 | `UnauthorizedProgram` | 0x8dbc | [B]/[R] |
| 6001 | `InvalidAdmin` | 0x32e2 0x3f5b | [B]/[R] |
| 6002 | `NoFeeTiers` | 0x8028 0x8230 | [B]/[R] |
| 6003 | `TooManyFeeTiers` | 0x811d 0x8325 | [B]/[R] |
| 6004 | `OffsetNotContinuous` | 0x8085 0x828d | [B]/[R] |
| 6005 | `FeeTiersNotSorted` | 0x8195 0x839d | [B]/[R] |
| 6006 | `InvalidFeeTotal` | 0x7f7a 0x7fc8 0x8159 0x8361 | [B]/[R] |
| 6007 | `InvalidSharingConfig` | 0x520e 0x5257 0x558e | [B]/[R] |
| 6008 | `InvalidPool` | 0x52cd 0x54be 0x5540 0x5649 | [B]/[R] |
| 6010 | `NoShareholders` | 0x6508 0x6edf | [B]/[R] |
| 6011 | `TooManyShareholders` | 0x653d 0x6f14 | [B]/[R] |
| 6012 | `DuplicateShareholder` | 0x666c 0x7045 | [B]/[R] |
| 6013 | `NotEnoughRemainingAccounts` | 0x62ed 0x6d04 0x6d5b 0x71fc | [B]/[R] |
| 6014 | `InvalidShareTotal` | 0x660e 0x6fe5 | [B]/[R] |
| 6016 | `NotAuthorized` | 0x5141 0x5603 0x576d 0x5ab4 | [B]/[R] |
| 6017 | `ZeroShareNotAllowed` | 0x6572 0x6f49 | [B]/[R] |
| 6018 | `SharingConfigNotActive` | 0x56b8 0x72d8 | [B]/[R] |
| 6020 | `ShareholderAccountMismatch` | 0x6309 0x6d77 | [B]/[R] |
| 6022 | `UserIdTooLong` | 0x5d73 | [B]/[R] |
| 6023 | `DeprecatedInstruction` | 0x14249 0x1428a | [B]/[R] |
| 6024 | `FeeSharesAlreadyUpdated` | 0x5f51 0x6787 | [B]/[R] |
| 6026 | `InvalidBuybackIndex` | 0x2f92 0x2fe2 0x3ae9 0x3b68 | [B]/[R] |
| 6028 | `InvalidFeeConfigAccount` | 0x25bb 0x25de 0x263c 0x26a7 | [B]/[R] |
| 6029 | `AccountTypeNotSupported` | 0x772c | [B]/[R] |
| 6030 | `InvalidMint` | 0x780c | [B]/[R] |
| 6031 | `UnsupportedQuoteMint` | 0x5f0f | [B]/[R] |
| 6033 | `PoolCreatorFeesNotSwept` | 0x723e | [B]/[R] |
| 6034 | `InvalidQuoteMint` | 0x6870 | [B]/[R] |
| 6036 | `NothingToWithdraw` | 0x7a6c 0x7c30 | [B]/[R] |

- In the enum but no direct immediate isolated: 6009 SharingConfigAdminRevoked, 6015 ShareCalculationOverflow, 6019 AmmAccountsRequiredForGraduatedCoin, 6021 FeatureDeactivated, 6025 MathOverflow, 6027 ClaimRateLimitExceeded, 6032 InvalidRemainingAccounts, 6035 IncompleteTokenAccounts.

### Anchor built-in codes observed

| code | Anchor name | count |
|---:|---|---:|
| 2000 | ConstraintMut | 68 |
| 2001 | ConstraintHasOne | 4 |
| 2002 | ConstraintSigner | 2 |
| 2003 | ConstraintRaw | 6 |
| 2004 | ConstraintOwner | 3 |
| 2005 | ConstraintRentExempt | 12 |
| 2006 | ConstraintSeeds | 92 |
| 2007 | ConstraintExecutable | 2 |
| 2009 | ConstraintAssociated | 2 |
| 2011 | ConstraintClose | 1 |
| 2012 | ConstraintAddress | 4 |
| 2013 | ConstraintZero | 1 |
| 2014 | ConstraintTokenMint | 4 |
| 2015 | ConstraintTokenOwner | 6 |
| 2019 | ConstraintSpace | 3 |
| 2020 | ConstraintAccountIsNone | 4 |
| 2021 | ConstraintTokenTokenProgram | 2 |
| 2022 | ConstraintMintTokenProgram | 2 |
| 2023 | ConstraintAssociatedTokenAccount | 4 |

## mayhem

### Program error codes (observed in `.text`)

| code | name | sites (first 4) | tag |
|---:|---|---|---|
| 6000 | `TradingPaused` | 0x2b0c 0x3021 0x380a 0x3f5e | [B]/[R] |
| 6002 | `MathOverflow` | 0x2a52 0x2f5d 0x581c 0x5933 | [B]/[R] |
| 6003 | `SolReservesTooLow` | 0x5cba 0x11d92 | [B]/[R] |
| 6004 | `MayhemModeEnded` | 0x1b6f 0x5c7b | [B]/[R] |
| 6005 | `MayhemModeNotEnded` | 0x1b43 | [B]/[R] |
| 6006 | `OverallRiskExceeded` | 0x59d7 | [B]/[R] |
| 6007 | `CoinRiskExceeded` | 0x59a2 | [B]/[R] |
| 6008 | `PumpCpiFailed` | 0x3cd2 0x4336 0x4c11 0x54e9 | [B]/[R] |
| 6010 | `PumpSwapCpiFailed` | 0x2eb5 0x3769 | [B]/[R] |
| 6013 | `?` | 0x44ba | [B]/[R] |
| 6014 | `WithdrawRateLimit` | 0x56cc 0x572c | [B]/[R] |
| 6015 | `TradeRateLimit` | 0x5c10 | [B]/[R] |
| 6016 | `AccountTypeNotSupported` | 0x1e2b 0x1f41 0x220d 0x25f5 | [B]/[R] |
| 6017 | `MaxFeeRecipientsExceeded` | 0x2093 | [B]/[R] |

- In the enum but no direct immediate isolated: 6001 TradingActive, 6011 PumpSwapCpiMathOverflow, 6012 PumpCpiSlippage.

### Anchor built-in codes observed

| code | Anchor name | count |
|---:|---|---:|
| 2000 | ConstraintMut | 116 |
| 2001 | ConstraintHasOne | 11 |
| 2002 | ConstraintSigner | 2 |
| 2004 | ConstraintOwner | 1 |
| 2005 | ConstraintRentExempt | 8 |
| 2006 | ConstraintSeeds | 55 |
| 2009 | ConstraintAssociated | 20 |
| 2012 | ConstraintAddress | 13 |
| 2014 | ConstraintTokenMint | 4 |
| 2015 | ConstraintTokenOwner | 24 |
| 2023 | ConstraintAssociatedTokenAccount | 14 |

## Notes

- The same numeric code has different meanings across programs (e.g. 6000 is `NotAuthorized`
  in pump and `FeeBasisPointsExceedsMaximum` in the AMM; 6058 is `BuybackFeeRecipientMissing`
  in the AMM but `AllBuybackFeeRecipientsShouldBeNonZero` in the pump source enum). Always
  pair the code with the program id.
- AMM codes 6000-6088 and fees codes 6000-6036 are consistent with their source/IDL enums;
  the AMM scan also hit 6103/6115, which are outside the AMM enum and are other immediates,
  not AMM errors (excluded above by the range filter).
- Mayhem sites are now direct immediates for most source enum codes; 6013 is observed but has
  no recovered enum name (marked `?`); codes 6001/6009/6011/6012/6013 are either not raised
  or use a different lowering. The source enums are `MayhemError`, `SellError`, `BurnError`,
  `BuyError`, `PumpSwapError` (combined).
- Pump: the observed code set is 98 values; the verified names are the cluster-spec ones
  (creator cluster table in `spec/08`, trade codes 6003/6005/6022, 6000). The remaining
  names are source-enum candidates and should be confirmed by triggering the gate (the
  source enum MATCHES the binary here (no shift) — see verified note above.
- `error_catalogs.md` lists raise *sites*, not every branch: a code may be emitted from
  several gates (e.g. 6024 Overflow in the pump has 98 sites).
