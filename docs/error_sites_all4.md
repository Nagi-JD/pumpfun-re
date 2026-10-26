# Custom-error raise-site catalog, all four deployed programs

Every Anchor custom-error raise in the deployed binaries: the code stored, the
instruction address, the enclosing function, the original source `file:line` the
build emitted with it, and the instruction handler(s) that can reach it.

Method: `stw/sth/stb/stdw [r10+off], imm` with `imm` in the Anchor custom-error
range; the origin is the `lddw` of a source-path VA plus the store-immediates
that follow it (file length as the 64-bit store equal to the path byte length,
line as the neighbouring 32-bit store); handler attribution is a BFS over the
relocation-aware call graph from each instruction handler, reporting the first
depth at which a site is reachable. The code -> variant name column for
`pump` and `pump_amm` comes from executing that program's own
`ErrorCode::name()` (binary search over the discriminant returning a
pointer/length pair) for every discriminant in range.

## Summary

| program | raise sites | codes | name table | sites with origin | sites with handler |
|---|---:|---:|---|---:|---:|
| pump | 366 | 96 | 111 names @0x2bd95 | 366/366 | 356/366 |
| pump_amm | 233 | 74 | 89 names @0xf6e3 | 227/233 | 233/233 |
| pump_fees | 68 | 28 | builtin table only | 68/68 | 68/68 |
| mayhem | 29 | 14 | builtin table only | 21/29 | 29/29 |

696 raise sites in total, 212 program/code pairs, 147 instruction handlers attributed.

Validation: the `pump` row reproduces the published pump table exactly - 111/111 code -> name assignments, 366/366 raise sites, and 366/366 `file:line` origins agree.

## pump

- sha256 `7a19affaa2c6187e04a5fe0ea298cee81fa5eb8c24cfcc30d85f615e89f7b02d`
- 215873 instructions / 906 functions (relocation-aware starts), 53 instruction handlers
- custom-error raise sites **366**, distinct codes **96**
- program error-name table: function `0x2bd95`, ABI `value`, **111 distinct variant names** recovered by executing it over every discriminant in range, covering 96 of the 96 observed codes
- 366/366 sites carry an inline origin tuple (file + line), 356/366 resolve to at least one instruction handler

### codes

| code | name (binary) | sites | origins (file:line, first 3) |
|---:|---|---:|---|
| 6000 | NotAuthorized | 6 | fee_recipient.rs:35, fee_recipient.rs:19, sweep_fees.rs:123 |
| 6002 | TooMuchSolRequired | 6 | buy_v2.rs:494, buy_v2.rs:967, trade_v3.rs:842 |
| 6003 | TooLittleSolReceived | 3 | sell_v2.rs:379, trade_v3.rs:1148, lib.rs:1012 |
| 6004 | MintDoesNotMatchBondingCurve | 3 | buy_v2.rs:88, buy_v2.rs:116, trade_v3.rs:180 |
| 6005 | BondingCurveComplete | 7 | trade_v3.rs:149, buy_v2.rs:345, buy_v2.rs:767 |
| 6006 | BondingCurveNotComplete | 2 | migrate.rs:251, migrate_v2.rs:249 |
| 6010 | AccountTypeNotSupported | 12 | buy_v2.rs:81, buy_v2.rs:109, buy_v2.rs:121 |
| 6011 | InitialRealTokenReservesShouldBeLessThanTokenTotalSupply | 1 | lib.rs:222 |
| 6012 | InitialVirtualTokenReservesShouldBeGreaterThanInitialRealTokenReserves | 1 | lib.rs:228 |
| 6013 | FeeBasisPointsGreaterThanMaximum | 2 | lib.rs:278, lib.rs:242 |
| 6014 | AllZerosWithdrawAuthority | 1 | lib.rs:249 |
| 6015 | PoolMigrationFeeShouldBeLessThanFinalRealSolReserves | 1 | lib.rs:270 |
| 6019 | InvalidCreator | 1 | creator/admin_cto.rs:312 |
| 6020 | BuyZeroAmount | 8 | multi_hop_curve_swap.rs:208, multi_hop_curve_swap.rs:590, buy_v2.rs:354 |
| 6021 | NotEnoughTokensToBuy | 9 | multi_hop_curve_swap.rs:599, trade_v3.rs:506, trade_v3.rs:518 |
| 6022 | SellZeroAmount | 4 | multi_hop_curve_swap.rs:686, sell_v2.rs:245, trade_v3.rs:1126 |
| 6023 | NotEnoughTokensToSell | 3 | sell_v2.rs:247, trade_v3.rs:1127, lib.rs:972 |
| 6024 | Overflow | 98 | buy_v2.rs:469, buy_v2.rs:949, buy_v2.rs:995 |
| 6025 | Truncation | 22 | buy_v2.rs:465, buy_v2.rs:881, buy_v2.rs:927 |
| 6026 | DivisionByZero | 10 | pump_quote.rs:106, pump_quote.rs:121, pump_quote.rs:131 |
| 6027 | NotEnoughRemainingAccounts | 12 | create_v2.rs:198, creator/distribute_creator_fee_v2.rs:152, creator/distribute_creator_fee_v2.rs:149 |
| 6028 | AllFeeRecipientsShouldBeNonZero | 2 | fee_recipient.rs:60, set_reserved_fee_recipients.rs:60 |
| 6029 | UnsortedNotUniqueFeeRecipients | 1 | fee_recipient.rs:78 |
| 6030 | CreatorShouldNotBeZero | 3 | create_v2.rs:732, creator/admin_cto.rs:307, lib.rs:334 |
| 6031 | StartTimeInThePast | 1 | token_incentives/volume_accumulator.rs:359 |
| 6032 | EndTimeInThePast | 1 | token_incentives/volume_accumulator.rs:369 |
| 6033 | EndTimeBeforeStartTime | 1 | token_incentives/volume_accumulator.rs:371 |
| 6034 | TimeRangeTooLarge | 1 | token_incentives/volume_accumulator.rs:373 |
| 6035 | EndTimeBeforeCurrentDay | 1 | token_incentives/volume_accumulator.rs:394 |
| 6036 | SupplyUpdateForFinishedRange | 1 | token_incentives/volume_accumulator.rs:297 |
| 6037 | DayIndexAfterEndIndex | 2 | token_incentives/volume_accumulator.rs:309, token_incentives/volume_accumulator.rs:337 |
| 6038 | DayInActiveRange | 1 | token_incentives/volume_accumulator.rs:338 |
| 6041 | BuyNotEnoughSolToCoverFees | 8 | trade_v3.rs:317, buy_v2.rs:771, buy_v2.rs:873 |
| 6042 | BuySlippageBelowMinTokensOut | 9 | trade_v3.rs:326, buy_v2.rs:921, buy_v2.rs:986 |
| 6043 | NameTooLong | 1 | create_v2.rs:541 |
| 6044 | SymbolTooLong | 1 | create_v2.rs:547 |
| 6045 | UriTooLong | 1 | create_v2.rs:553 |
| 6046 | CreateV2Disabled | 1 | create_v2.rs:738 |
| 6048 | MayhemModeDisabled | 1 | create_v2.rs:709 |
| 6050 | UnableToDistributeCreatorVaultMigratedToSharingConfig | 2 | creator/collect_creator_fee.rs:103, creator/collect_creator_fee.rs:198 |
| 6051 | SharingConfigNotActive | 2 | creator/distribute_creator_fee_v2.rs:205, creator/distribute_creator_fees.rs:241 |
| 6052 | UnableToDistributeCreatorFeesToExecutableRecipient | 2 | creator/distribute_creator_fee_v2.rs:125, creator/distribute_creator_fees.rs:116 |
| 6054 | ShareholdersAndRemainingAccountsMismatch | 3 | creator/distribute_creator_fee_v2.rs:101, creator/distribute_creator_fee_v2.rs:112, creator/distribute_creator_fees.rs:103 |
| 6055 | InvalidShareBps | 2 | creator/distribute_creator_fee_v2.rs:163, creator/distribute_creator_fees.rs:148 |
| 6057 | BuybackFeeRecipientNotAuthorized | 1 | lib.rs:1884 |
| 6058 | AllBuybackFeeRecipientsShouldBeNonZero | 1 | lib.rs:1895 |
| 6059 | NotUniqueBuybackFeeRecipients | 1 | lib.rs:1905 |
| 6060 | BuybackBasisPointsOutOfRange | 1 | lib.rs:1870 |
| 6061 | WrongBuybackFeeRecipientsCount | 1 | set_reserved_fee_recipients.rs:121 |
| 6062 | BuybackFeeRecipientMissing | 2 | sell.rs:145, lib.rs:1879 |
| 6063 | UnsupportedQuoteMint | 10 | create_v2.rs:345, create_v2.rs:390, create_v2.rs:528 |
| 6064 | InvalidQuoteTokenProgram | 3 | create_v2.rs:205, create_v2.rs:210, token_incentives/claim_token_incentives.rs:305 |
| 6065 | InvalidAssociatedQuoteBondingCurve | 1 | create_v2.rs:258 |
| 6066 | QuoteMintWhitelistFull | 2 | quote_control/state.rs:82, lib.rs:1971 |
| 6067 | QuoteMintAlreadyWhitelisted | 2 | quote_control/state.rs:77, lib.rs:1960 |
| 6068 | QuoteMintNotWhitelisted | 3 | quote_control/state.rs:99, quote_control/state.rs:113, lib.rs:1986 |
| 6069 | QuoteMintNotEligibleForWhitelist | 7 | quote_control/state.rs:67, quote_control/state.rs:72, quote_control/state.rs:62 |
| 6070 | UnableToDistributeCreatorFeesToUninitializedAccount | 1 | creator/distribute_creator_fee_v2.rs:173 |
| 6071 | MayhemModeQuoteMintNotAllowed | 1 | create_v2.rs:758 |
| 6072 | MissingCashbackAccounts | 1 | sell.rs:23 |
| 6073 | InvalidCashbackAccumulator | 3 | sell.rs:33, sell.rs:81, sell.rs:85 |
| 6074 | InvalidBondingCurveV2 | 4 | sell.rs:107, sell.rs:114, sell.rs:133 |
| 6075 | InvalidQuoteControl | 5 | create_v2.rs:348, create_v2.rs:353, quote_control/state.rs:145 |
| 6076 | InvalidCashbackRecipient | 1 | token_incentives/claim_token_incentives.rs:342 |
| 6077 | CreatorFeeNotConfigurable | 2 | create_v2.rs:774, creator/admin_cto.rs:334 |
| 6078 | CreatorFeeBpsOutOfRange | 2 | create_v2.rs:778, creator/admin_cto.rs:338 |
| 6080 | CreatorFeeNotAllowedForCashbackCoin | 1 | creator/admin_cto.rs:330 |
| 6082 | CashbackDeprecated | 1 | create_v2.rs:716 |
| 6083 | HolderRewardCreatorImmutable | 2 | creator/admin_cto.rs:289, creator/migrate_bonding_curve_creator.rs:46 |
| 6084 | HolderRewardDisabled | 2 | create_v2.rs:719, creator/admin_cto.rs:296 |
| 6085 | HolderRewardRecipientsMismatch | 2 | creator/distribute_fee_to_holders.rs:82, creator/distribute_fee_to_holders.rs:122 |
| 6086 | HolderRewardsRentFloor | 1 | creator/distribute_fee_to_holders.rs:164 |
| 6087 | HolderRewardTokenAccountMissing | 1 | creator/distribute_fee_to_holders.rs:120 |
| 6088 | CtoNotAllowedForMayhemCoin | 1 | creator/admin_cto.rs:284 |
| 6089 | CtoNewCreatorRequired | 1 | creator/admin_cto.rs:306 |
| 6090 | CtoNewCreatorNotAllowed | 1 | creator/admin_cto.rs:298 |
| 6091 | CreatorFeeNotConfigurableForQuote | 1 | creator/admin_cto.rs:326 |
| 6092 | CtoCreatorAccountNotWritable | 1 | creator/admin_cto.rs:556 |
| 6093 | CtoSharedVaultFrozen | 2 | creator/admin_cto.rs:719, creator/admin_cto.rs:660 |
| 6094 | CashbackCoinNotSupported | 1 | trade_v3.rs:150 |
| 6095 | CreatorFeesNotSwept | 4 | creator/admin_cto.rs:410, creator/distribute_creator_fee_v2.rs:213, creator/distribute_creator_fees.rs:249 |
| 6096 | FeeTiersEmpty | 1 | util/fee.rs:162 |
| 6097 | FeeConfigTooShort | 1 | util/fee.rs:183 |
| 6098 | MultiHopDiscontinuousPath | 2 | multi_hop_curve_swap.rs:262, multi_hop_curve_swap.rs:546 |
| 6099 | InvalidQuoteBondingCurve | 3 | create_v2.rs:442, create_v2.rs:437, create_v2.rs:449 |
| 6100 | QuoteBondingCurveNotEligible | 2 | create_v2.rs:395, pump_quote.rs:90 |
| 6101 | QuotePoolAccountsRequired | 1 | create_v2.rs:493 |
| 6102 | QuotePoolNotFound | 1 | pump_quote.rs:407 |
| 6103 | InvalidQuotePool | 11 | pump_quote.rs:279, pump_quote.rs:280, pump_quote.rs:307 |
| 6104 | QuoteReservesOutOfRange | 1 | pump_quote.rs:241 |
| 6105 | CurveDepthExceeded | 1 | pump_quote.rs:62 |
| 6106 | MultiHopHopFeesMismatch | 1 | multi_hop_curve_swap.rs:218 |
| 6107 | QuoteCurveAwaitingMigration | 1 | create_v2.rs:466 |
| 6108 | MultiHopMayhemCurveNotSupported | 1 | multi_hop_curve_swap.rs:484 |
| 6109 | QuoteChainAccountsRequired | 1 | create_v2.rs:412 |
| 6110 | QuoteMintNotWritable | 1 | migrate_v2.rs:335 |

### per handler

`direct` = raise site inside the handler body (call-graph depth 0); `+d` = first raise reachable at call-graph depth d.

| handler | handler pc | raises (depth) |
|---|---|---|
| `add_quote_mint` | 0x24774 | +1: 6066 QuoteMintWhitelistFull, 6067 QuoteMintAlreadyWhitelisted, 6069 QuoteMintNotEligibleForWhitelist |
| `admin_cto` | 0x25b40 | +1: 6019 InvalidCreator, 6030 CreatorShouldNotBeZero, 6077 CreatorFeeNotConfigurable, 6078 CreatorFeeBpsOutOfRange, 6080 CreatorFeeNotAllowedForCashbackCoin, 6083 HolderRewardCreatorImmutable, 6084 HolderRewardDisabled, 6088 CtoNotAllowedForMayhemCoin, 6089 CtoNewCreatorRequired, 6090 CtoNewCreatorNotAllowed, 6091 CreatorFeeNotConfigurableForQuote, 6092 CtoCreatorAccountNotWritable, 6093 CtoSharedVaultFrozen, 6095 CreatorFeesNotSwept; +2: 6050 UnableToDistributeCreatorVaultMigratedToSharingConfig; +3: 6024 Overflow; +4: 6024 Overflow |
| `admin_set_idl_authority` | 0x260a3 | +1: 6010 AccountTypeNotSupported |
| `admin_update_token_incentives` | 0x25c54 | +2: 6031 StartTimeInThePast, 6032 EndTimeInThePast, 6033 EndTimeBeforeStartTime, 6034 TimeRangeTooLarge, 6035 EndTimeBeforeCurrentDay, 6036 SupplyUpdateForFinishedRange, 6037 DayIndexAfterEndIndex, 6038 DayInActiveRange |
| `buy` | 0x2549c | +1: 6002 TooMuchSolRequired, 6005 BondingCurveComplete, 6020 BuyZeroAmount, 6021 NotEnoughTokensToBuy, 6024 Overflow; +2: 6000 NotAuthorized, 6024 Overflow, 6025 Truncation, 6026 DivisionByZero, 6062 BuybackFeeRecipientMissing, 6074 InvalidBondingCurveV2; +3: 6024 Overflow, 6025 Truncation, 6026 DivisionByZero, 6057 BuybackFeeRecipientNotAuthorized, 6062 BuybackFeeRecipientMissing; +4: 6024 Overflow, 6026 DivisionByZero |
| `buy_exact_quote_in_v2` | 0x24f6b | +1: 6002 TooMuchSolRequired, 6005 BondingCurveComplete, 6020 BuyZeroAmount, 6021 NotEnoughTokensToBuy, 6041 BuyNotEnoughSolToCoverFees, 6042 BuySlippageBelowMinTokensOut, 6063 UnsupportedQuoteMint; +2: 6000 NotAuthorized, 6004 MintDoesNotMatchBondingCurve, 6010 AccountTypeNotSupported, 6024 Overflow, 6025 Truncation, 6026 DivisionByZero, 6057 BuybackFeeRecipientNotAuthorized, 6062 BuybackFeeRecipientMissing, 6063 UnsupportedQuoteMint; +3: 6024 Overflow, 6026 DivisionByZero; +4: 6024 Overflow |
| `buy_exact_quote_in_v3` | 0x25185 | +1: 6002 TooMuchSolRequired, 6020 BuyZeroAmount, 6021 NotEnoughTokensToBuy, 6041 BuyNotEnoughSolToCoverFees, 6042 BuySlippageBelowMinTokensOut; +2: 6005 BondingCurveComplete, 6021 NotEnoughTokensToBuy, 6024 Overflow, 6025 Truncation, 6026 DivisionByZero, 6041 BuyNotEnoughSolToCoverFees, 6042 BuySlippageBelowMinTokensOut, 6094 CashbackCoinNotSupported; +3: 6004 MintDoesNotMatchBondingCurve, 6010 AccountTypeNotSupported, 6024 Overflow, 6025 Truncation, 6026 DivisionByZero, 6063 UnsupportedQuoteMint, 6097 FeeConfigTooShort; +4: 6024 Overflow, 6026 DivisionByZero, 6096 FeeTiersEmpty |
| `buy_exact_sol_in` | 0x25579 | +1: 6002 TooMuchSolRequired, 6005 BondingCurveComplete, 6020 BuyZeroAmount, 6021 NotEnoughTokensToBuy, 6024 Overflow, 6041 BuyNotEnoughSolToCoverFees, 6042 BuySlippageBelowMinTokensOut; +2: 6000 NotAuthorized, 6024 Overflow, 6025 Truncation, 6026 DivisionByZero, 6062 BuybackFeeRecipientMissing, 6074 InvalidBondingCurveV2; +3: 6024 Overflow, 6026 DivisionByZero, 6057 BuybackFeeRecipientNotAuthorized, 6062 BuybackFeeRecipientMissing; +4: 6024 Overflow |
| `buy_v2` | 0x24ea2 | +1: 6002 TooMuchSolRequired, 6005 BondingCurveComplete, 6020 BuyZeroAmount, 6021 NotEnoughTokensToBuy, 6063 UnsupportedQuoteMint; +2: 6000 NotAuthorized, 6004 MintDoesNotMatchBondingCurve, 6010 AccountTypeNotSupported, 6024 Overflow, 6025 Truncation, 6026 DivisionByZero, 6057 BuybackFeeRecipientNotAuthorized, 6062 BuybackFeeRecipientMissing, 6063 UnsupportedQuoteMint; +3: 6024 Overflow, 6025 Truncation, 6026 DivisionByZero; +4: 6024 Overflow, 6026 DivisionByZero |
| `buy_v3` | 0x250d9 | +1: 6002 TooMuchSolRequired, 6020 BuyZeroAmount, 6021 NotEnoughTokensToBuy; +2: 6005 BondingCurveComplete, 6021 NotEnoughTokensToBuy, 6024 Overflow, 6025 Truncation, 6026 DivisionByZero, 6094 CashbackCoinNotSupported; +3: 6004 MintDoesNotMatchBondingCurve, 6010 AccountTypeNotSupported, 6024 Overflow, 6026 DivisionByZero, 6063 UnsupportedQuoteMint, 6097 FeeConfigTooShort; +4: 6024 Overflow, 6096 FeeTiersEmpty |
| `claim_cashback` | 0x25d99 | +1: 6024 Overflow |
| `claim_cashback_v2` | 0x25e2a | +1: 6010 AccountTypeNotSupported, 6064 InvalidQuoteTokenProgram, 6076 InvalidCashbackRecipient |
| `claim_token_incentives` | 0x25d0e | +2: 6025 Truncation |
| `close_user_volume_accumulator` | 0x25f6d | - |
| `collect_creator_fee` | 0x2586e | +1: 6050 UnableToDistributeCreatorVaultMigratedToSharingConfig |
| `create` | 0x24c1b | +1: 6030 CreatorShouldNotBeZero |
| `create_v2` | 0x24d15 | +1: 6027 NotEnoughRemainingAccounts, 6030 CreatorShouldNotBeZero, 6043 NameTooLong, 6044 SymbolTooLong, 6045 UriTooLong, 6046 CreateV2Disabled, 6048 MayhemModeDisabled, 6063 UnsupportedQuoteMint, 6064 InvalidQuoteTokenProgram, 6065 InvalidAssociatedQuoteBondingCurve, 6071 MayhemModeQuoteMintNotAllowed, 6077 CreatorFeeNotConfigurable, 6078 CreatorFeeBpsOutOfRange, 6082 CashbackDeprecated, 6084 HolderRewardDisabled; +2: 6024 Overflow, 6063 UnsupportedQuoteMint, 6075 InvalidQuoteControl, 6100 QuoteBondingCurveNotEligible, 6101 QuotePoolAccountsRequired, 6107 QuoteCurveAwaitingMigration; +3: 6024 Overflow, 6075 InvalidQuoteControl, 6099 InvalidQuoteBondingCurve, 6100 QuoteBondingCurveNotEligible, 6104 QuoteReservesOutOfRange, 6105 CurveDepthExceeded, 6109 QuoteChainAccountsRequired; +4: 6024 Overflow, 6026 DivisionByZero, 6102 QuotePoolNotFound, 6103 InvalidQuotePool; +5: 6024 Overflow, 6026 DivisionByZero, 6103 InvalidQuotePool; +6: 6103 InvalidQuotePool |
| `distribute_creator_fees` | 0x26225 | +1: 6051 SharingConfigNotActive, 6095 CreatorFeesNotSwept; +2: 6024 Overflow, 6027 NotEnoughRemainingAccounts, 6052 UnableToDistributeCreatorFeesToExecutableRecipient, 6054 ShareholdersAndRemainingAccountsMismatch, 6055 InvalidShareBps |
| `distribute_creator_fees_v2` | 0x262dd | +1: 6051 SharingConfigNotActive, 6095 CreatorFeesNotSwept; +2: 6024 Overflow, 6027 NotEnoughRemainingAccounts, 6052 UnableToDistributeCreatorFeesToExecutableRecipient, 6054 ShareholdersAndRemainingAccountsMismatch, 6055 InvalidShareBps, 6070 UnableToDistributeCreatorFeesToUninitializedAccount |
| `distribute_fee_to_holders` | 0x258fa | +1: 6024 Overflow, 6085 HolderRewardRecipientsMismatch, 6086 HolderRewardsRentFloor, 6087 HolderRewardTokenAccountMissing |
| `extend_account` | 0x257cf | +1: 6010 AccountTypeNotSupported |
| `get_minimum_distributable_fee` | 0x261a8 | +2: 6024 Overflow, 6027 NotEnoughRemainingAccounts, 6052 UnableToDistributeCreatorFeesToExecutableRecipient, 6054 ShareholdersAndRemainingAccountsMismatch, 6055 InvalidShareBps |
| `init_user_volume_accumulator` | 0x25ebc | - |
| `initialize` | 0x2421b | - |
| `initialize_quote_control` | 0x264a2 | - |
| `migrate` | 0x256fb | +1: 6006 BondingCurveNotComplete; +2: 6024 Overflow, 6027 NotEnoughRemainingAccounts |
| `migrate_bonding_curve_creator` | 0x26118 | +1: 6083 HolderRewardCreatorImmutable, 6095 CreatorFeesNotSwept |
| `migrate_v2` | 0x25749 | +1: 6006 BondingCurveNotComplete, 6110 QuoteMintNotWritable; +2: 6024 Overflow, 6027 NotEnoughRemainingAccounts, 6063 UnsupportedQuoteMint |
| `multi_hop_curve_swap` | 0x252b8 | +1: 6020 BuyZeroAmount, 6027 NotEnoughRemainingAccounts, 6098 MultiHopDiscontinuousPath, 6106 MultiHopHopFeesMismatch; +2: 6020 BuyZeroAmount, 6021 NotEnoughTokensToBuy, 6022 SellZeroAmount, 6024 Overflow, 6098 MultiHopDiscontinuousPath, 6108 MultiHopMayhemCurveNotSupported; +3: 6004 MintDoesNotMatchBondingCurve, 6005 BondingCurveComplete, 6010 AccountTypeNotSupported, 6024 Overflow, 6025 Truncation, 6026 DivisionByZero, 6041 BuyNotEnoughSolToCoverFees, 6042 BuySlippageBelowMinTokensOut, 6094 CashbackCoinNotSupported, 6097 FeeConfigTooShort; +4: 6021 NotEnoughTokensToBuy, 6024 Overflow, 6026 DivisionByZero, 6096 FeeTiersEmpty; +5: 6025 Truncation |
| `remove_quote_control_mint` | 0x26667 | +2: 6068 QuoteMintNotWhitelisted, 6069 QuoteMintNotEligibleForWhitelist |
| `remove_quote_mint` | 0x24826 | +1: 6068 QuoteMintNotWhitelisted, 6069 QuoteMintNotEligibleForWhitelist |
| `sell` | 0x25656 | +1: 6003 TooLittleSolReceived, 6005 BondingCurveComplete, 6022 SellZeroAmount, 6023 NotEnoughTokensToSell; +2: 6000 NotAuthorized, 6024 Overflow, 6025 Truncation, 6026 DivisionByZero, 6062 BuybackFeeRecipientMissing, 6072 MissingCashbackAccounts, 6073 InvalidCashbackAccumulator, 6074 InvalidBondingCurveV2; +3: 6025 Truncation, 6057 BuybackFeeRecipientNotAuthorized, 6062 BuybackFeeRecipientMissing |
| `sell_v2` | 0x25034 | +1: 6003 TooLittleSolReceived, 6005 BondingCurveComplete, 6022 SellZeroAmount, 6023 NotEnoughTokensToSell, 6063 UnsupportedQuoteMint; +2: 6000 NotAuthorized, 6004 MintDoesNotMatchBondingCurve, 6010 AccountTypeNotSupported, 6024 Overflow, 6025 Truncation, 6026 DivisionByZero, 6057 BuybackFeeRecipientNotAuthorized, 6062 BuybackFeeRecipientMissing, 6063 UnsupportedQuoteMint; +3: 6024 Overflow |
| `sell_v3` | 0x25231 | +1: 6003 TooLittleSolReceived, 6022 SellZeroAmount, 6023 NotEnoughTokensToSell; +2: 6005 BondingCurveComplete, 6024 Overflow, 6025 Truncation, 6026 DivisionByZero, 6094 CashbackCoinNotSupported; +3: 6004 MintDoesNotMatchBondingCurve, 6010 AccountTypeNotSupported, 6024 Overflow, 6097 FeeConfigTooShort; +4: 6096 FeeTiersEmpty |
| `set_creator` | 0x25a82 | - |
| `set_max_curve_depth` | 0x24566 | - |
| `set_mayhem_virtual_params` | 0x24ab5 | - |
| `set_metaplex_creator` | 0x259f2 | - |
| `set_params` | 0x2494e | +1: 6011 InitialRealTokenReservesShouldBeLessThanTokenTotalSupply, 6012 InitialVirtualTokenReservesShouldBeGreaterThanInitialRealTokenReserves, 6013 FeeBasisPointsGreaterThanMaximum, 6014 AllZerosWithdrawAuthority, 6015 PoolMigrationFeeShouldBeLessThanFinalRealSolReserves; +2: 6025 Truncation, 6027 NotEnoughRemainingAccounts, 6028 AllFeeRecipientsShouldBeNonZero, 6029 UnsortedNotUniqueFeeRecipients |
| `set_quote_control_admin` | 0x264e3 | - |
| `set_quote_control_mint_reserves` | 0x267e9 | +2: 6068 QuoteMintNotWhitelisted |
| `set_quote_control_reserves_admin` | 0x26728 | - |
| `set_reserved_fee_recipients` | 0x24b5d | +1: 6027 NotEnoughRemainingAccounts, 6028 AllFeeRecipientsShouldBeNonZero |
| `set_virtual_quote_reserves` | 0x248d8 | - |
| `sweep_creator_fee` | 0x25409 | +1: 6000 NotAuthorized; +2: 6004 MintDoesNotMatchBondingCurve, 6010 AccountTypeNotSupported |
| `sweep_protocol_fee` | 0x25376 | +1: 6000 NotAuthorized; +2: 6004 MintDoesNotMatchBondingCurve, 6010 AccountTypeNotSupported |
| `sync_user_volume_accumulator` | 0x25ff1 | - |
| `toggle_cashback_enabled` | 0x243d8 | +1: 6000 NotAuthorized |
| `toggle_create_v2` | 0x2430e | +1: 6000 NotAuthorized |
| `toggle_mayhem_mode` | 0x245dc | +1: 6000 NotAuthorized |
| `update_creator_fee_config` | 0x246a6 | - |
| `update_global_authority` | 0x24261 | - |
| `update_holder_reward_config` | 0x244a2 | - |

## pump_amm

- sha256 `6a7ad34596d83b4c435b32f458a56e718e9f82eb4ad38e4316616d15d24d8ff7`
- 139524 instructions / 663 functions (relocation-aware starts), 38 instruction handlers
- custom-error raise sites **233**, distinct codes **74**
- program error-name table: function `0xf6e3`, ABI `value`, **89 distinct variant names** recovered by executing it over every discriminant in range, covering 74 of the 74 observed codes
- 227/233 sites carry an inline origin tuple (file + line), 233/233 resolve to at least one instruction handler

### codes

| code | name (binary) | sites | origins (file:line, first 3) |
|---:|---|---:|---|
| 6000 | FeeBasisPointsExceedsMaximum | 3 | state/global_config.rs:220, state/global_config.rs:230, state/global_config.rs:243 |
| 6001 | ZeroBaseAmount | 10 | instructions/boost.rs:273, instructions/create_pool.rs:198, instructions/swap/buy.rs:326 |
| 6002 | ZeroQuoteAmount | 9 | instructions/boost.rs:250, instructions/boost.rs:255, instructions/create_pool.rs:199 |
| 6003 | TooLittlePoolTokenLiquidity | 5 | instructions/boost.rs:280, instructions/create_pool.rs:290, instructions/swap/buy.rs:781 |
| 6004 | ExceededSlippage | 10 | instructions/boost.rs:274, instructions/liquidity/deposit.rs:79, instructions/liquidity/deposit.rs:100 |
| 6005 | InvalidAdmin | 3 | instructions/admin/toggle_boost.rs:14, state/global_config.rs:297, state/global_config.rs:292 |
| 6006 | UnsupportedBaseMint | 1 | instructions/create_pool.rs:201 |
| 6007 | UnsupportedQuoteMint | 2 | instructions/create_pool.rs:215, utils/transfer_fee.rs:32 |
| 6009 | InvalidQuoteMint | 1 | instructions/swap/trade_v2.rs:146 |
| 6011 | AllProtocolFeeRecipientsShouldBeNonZero | 2 | instructions/admin/set_reserved_fee_recipients.rs:60, state/global_config.rs:256 |
| 6012 | UnsortedNotUniqueProtocolFeeRecipients | 1 | state/global_config.rs:263 |
| 6013 | InvalidProtocolFeeRecipient | 2 | instructions/swap/mod.rs:164, instructions/sweep_fees.rs:91 |
| 6016 | BuyMoreBaseAmountThanPoolReserves | 1 | curve/constant_product.rs:21 |
| 6017 | DisabledCreatePool | 1 | instructions/create_pool.rs:193 |
| 6018 | DisabledDeposit | 1 | instructions/liquidity/deposit.rs:56 |
| 6019 | DisabledWithdraw | 1 | instructions/liquidity/withdraw.rs:57 |
| 6020 | DisabledBuy | 6 | instructions/boost.rs:240, instructions/swap/buy.rs:317, instructions/swap/buy.rs:625 |
| 6021 | DisabledSell | 3 | instructions/swap/multi_hop_swap.rs:474, instructions/swap/sell.rs:101, instructions/swap/trade_v2.rs:865 |
| 6022 | SameMint | 1 | instructions/create_pool.rs:217 |
| 6023 | Overflow | 63 | curve/fees.rs:19, curve/fees.rs:17, instructions/boost.rs:258 |
| 6024 | Truncation | 12 | curve/constant_product.rs:24, curve/constant_product.rs:47, curve/constant_product.rs:87 |
| 6025 | DivisionByZero | 6 | curve/constant_product.rs:45, curve/constant_product.rs:85, curve/constant_product.rs:112 |
| 6027 | AccountTypeNotSupported | 6 | instructions/extend_account.rs:91, instructions/extend_account.rs:114, instructions/swap/multi_hop_swap.rs:239 |
| 6028 | OnlyCanonicalPumpPoolsCanHaveCoinCreator | 3 | instructions/admin/admin_cto_pool.rs:64, instructions/coin_creator/set_coin_creator.rs:63, instructions/create_pool.rs:279 |
| 6030 | StartTimeInThePast | 1 | state/volume_accumulator.rs:313 |
| 6031 | EndTimeInThePast | 1 | state/volume_accumulator.rs:327 |
| 6032 | EndTimeBeforeStartTime | 1 | state/volume_accumulator.rs:329 |
| 6033 | TimeRangeTooLarge | 1 | state/volume_accumulator.rs:331 |
| 6034 | EndTimeBeforeCurrentDay | 1 | state/volume_accumulator.rs:352 |
| 6035 | SupplyUpdateForFinishedRange | 1 | state/volume_accumulator.rs:251 |
| 6036 | DayIndexAfterEndIndex | 2 | state/volume_accumulator.rs:263, state/volume_accumulator.rs:291 |
| 6037 | DayInActiveRange | 1 | state/volume_accumulator.rs:292 |
| 6039 | BuyNotEnoughQuoteTokensToCoverFees | 4 | instructions/swap/buy.rs:646, instructions/swap/buy.rs:700, instructions/swap/trade_v2.rs:328 |
| 6040 | BuySlippageBelowMinBaseAmountOut | 6 | instructions/swap/buy.rs:733, instructions/swap/buy.rs:754, instructions/swap/buy.rs:776 |
| 6041 | MayhemModeDisabled | 1 | instructions/create_pool.rs:171 |
| 6042 | OnlyPumpPoolsMayhemMode | 1 | instructions/create_pool.rs:177 |
| 6043 | MayhemModeInDesiredState | 1 | instructions/admin/toggle_mayhem_mode.rs:17 |
| 6044 | NotEnoughRemainingAccounts | 3 | instructions/admin/set_reserved_fee_recipients.rs:40, instructions/swap/multi_hop_swap.rs:278, instructions/swap/multi_hop_swap.rs:307 |
| 6048 | CreatorVaultMigratedToSharingConfig | 1 | instructions/coin_creator/collect_coin_creator_fee.rs:68 |
| 6049 | CashbackNotEnabled | 1 | instructions/create_pool.rs:183 |
| 6050 | OnlyPumpPoolsCashback | 1 | instructions/create_pool.rs:189 |
| 6051 | CashbackNotInDesiredState | 1 | instructions/admin/toggle_cashback_enabled.rs:21 |
| 6053 | BuybackFeeRecipientNotAuthorized | 3 | state/global_config.rs:336, state/global_config.rs:321, state/global_config.rs:326 |
| 6054 | AllBuybackFeeRecipientsShouldBeNonZero | 1 | state/global_config.rs:347 |
| 6055 | NotUniqueBuybackFeeRecipients | 1 | state/global_config.rs:357 |
| 6056 | BuybackBasisPointsOutOfRange | 1 | state/global_config.rs:306 |
| 6057 | WrongBuybackFeeRecipientsCount | 1 | instructions/admin/update_buyback_config.rs:40 |
| 6058 | BuybackFeeRecipientMissing | 2 | instructions/swap/buy.rs:116, instructions/swap/buy.rs:121 |
| 6059 | MissingCashbackAccounts | 3 | instructions/swap/buy.rs:44, instructions/swap/sell.rs:378, instructions/swap/sell.rs:383 |
| 6060 | InvalidCashbackAccumulator | 4 | instructions/swap/sell.rs:392, instructions/swap/sell.rs:395, instructions/swap/sell.rs:444 |
| 6061 | InvalidCashbackAccumulatorAta | 4 | instructions/swap/buy.rs:54, instructions/swap/buy.rs:57, instructions/swap/sell.rs:464 |
| 6062 | InvalidPoolV2 | 2 | instructions/swap/sell.rs:520, instructions/swap/sell.rs:526 |
| 6063 | InsufficientRealQuoteReserves | 2 | instructions/swap/sell.rs:171, instructions/swap/trade_v2.rs:377 |
| 6065 | PoolCannotBoost | 1 | instructions/boost.rs:245 |
| 6066 | BoostDisabled | 1 | instructions/boost.rs:238 |
| 6067 | SeedLockViolation | 1 | instructions/liquidity/withdraw.rs:62 |
| 6068 | CreatorFeeNotConfigurable | 1 | instructions/admin/admin_cto_pool.rs:107 |
| 6069 | CreatorFeeBpsOutOfRange | 1 | instructions/admin/admin_cto_pool.rs:111 |
| 6071 | CreatorFeeNotAllowedForCashbackCoin | 1 | instructions/admin/admin_cto_pool.rs:103 |
| 6074 | HolderRewardCreatorImmutable | 2 | instructions/admin/admin_cto_pool.rs:77, instructions/coin_creator/migrate_pool_coin_creator.rs:52 |
| 6075 | CtoNotAllowedForMayhemPool | 1 | instructions/admin/admin_cto_pool.rs:68 |
| 6076 | InvalidHolderRewardCoinCreator | 1 | instructions/admin/admin_cto_pool.rs:83 |
| 6077 | CreatorFeeNotConfigurableForQuote | 1 | instructions/admin/admin_cto_pool.rs:99 |
| 6078 | OnlyPumpPools | 1 | instructions/swap/trade_v2.rs:119 |
| 6079 | CashbackCoinNotSupported | 2 | instructions/swap/trade_v2.rs:120, instructions/swap/trade_v2.rs:103 |
| 6080 | MayhemPoolNotSupported | 1 | instructions/swap/trade_v2.rs:124 |
| 6081 | CreatorFeesNotSwept | 2 | instructions/admin/admin_cto_pool.rs:121, instructions/coin_creator/migrate_pool_coin_creator.rs:59 |
| 6082 | FeeTiersEmpty | 1 | curve/fees.rs:160 |
| 6083 | FeeConfigTooShort | 1 | curve/fees.rs:184 |
| 6084 | MultiHopDiscontinuousPath | 3 | instructions/swap/multi_hop_swap.rs:300, instructions/swap/multi_hop_swap.rs:251, instructions/swap/multi_hop_swap.rs:777 |
| 6085 | MultiHopCurveRunMismatch | 2 | instructions/swap/multi_hop_swap.rs:929, instructions/swap/multi_hop_swap.rs:936 |
| 6086 | MultiHopMixedDirection | 1 | instructions/swap/multi_hop_swap.rs:295 |
| 6087 | SelfTransferNotAllowed | 1 | utils/token.rs:21 |
| 6088 | QuoteMintNotWritable | 1 | instructions/boost.rs:403 |

### per handler

`direct` = raise site inside the handler body (call-graph depth 0); `+d` = first raise reachable at call-graph depth d.

| handler | handler pc | raises (depth) |
|---|---|---|
| `admin_cto_pool` | 0x1d5fe | +1: 6028 OnlyCanonicalPumpPoolsCanHaveCoinCreator, 6068 CreatorFeeNotConfigurable, 6069 CreatorFeeBpsOutOfRange, 6071 CreatorFeeNotAllowedForCashbackCoin, 6074 HolderRewardCreatorImmutable, 6075 CtoNotAllowedForMayhemPool, 6076 InvalidHolderRewardCoinCreator, 6077 CreatorFeeNotConfigurableForQuote, 6081 CreatorFeesNotSwept |
| `admin_update_token_incentives` | 0x1cb9d | +2: 6030 StartTimeInThePast, 6031 EndTimeInThePast, 6032 EndTimeBeforeStartTime, 6033 TimeRangeTooLarge, 6034 EndTimeBeforeCurrentDay, 6035 SupplyUpdateForFinishedRange, 6036 DayIndexAfterEndIndex, 6037 DayInActiveRange |
| `boost_buy_and_burn` | 0x1c8e7 | +1: 6001 ZeroBaseAmount, 6002 ZeroQuoteAmount, 6003 TooLittlePoolTokenLiquidity, 6004 ExceededSlippage, 6020 DisabledBuy, 6065 PoolCannotBoost, 6066 BoostDisabled, 6088 QuoteMintNotWritable; +2: 6005 InvalidAdmin, 6007 UnsupportedQuoteMint, 6023 Overflow; +3: 6023 Overflow, 6024 Truncation, 6025 DivisionByZero, 6087 SelfTransferNotAllowed |
| `buy` | 0x1cec9 | +1: 6001 ZeroBaseAmount, 6002 ZeroQuoteAmount, 6004 ExceededSlippage, 6020 DisabledBuy; +2: 6007 UnsupportedQuoteMint, 6013 InvalidProtocolFeeRecipient, 6016 BuyMoreBaseAmountThanPoolReserves, 6023 Overflow, 6024 Truncation, 6058 BuybackFeeRecipientMissing, 6059 MissingCashbackAccounts, 6061 InvalidCashbackAccumulatorAta, 6062 InvalidPoolV2; +3: 6023 Overflow, 6025 DivisionByZero, 6053 BuybackFeeRecipientNotAuthorized, 6087 SelfTransferNotAllowed; +4: 6024 Truncation |
| `buy_exact_quote_in` | 0x1cfb1 | +1: 6001 ZeroBaseAmount, 6002 ZeroQuoteAmount, 6003 TooLittlePoolTokenLiquidity, 6020 DisabledBuy, 6039 BuyNotEnoughQuoteTokensToCoverFees, 6040 BuySlippageBelowMinBaseAmountOut; +2: 6007 UnsupportedQuoteMint, 6013 InvalidProtocolFeeRecipient, 6023 Overflow, 6024 Truncation, 6058 BuybackFeeRecipientMissing, 6059 MissingCashbackAccounts, 6061 InvalidCashbackAccumulatorAta, 6062 InvalidPoolV2; +3: 6023 Overflow, 6024 Truncation, 6025 DivisionByZero, 6053 BuybackFeeRecipientNotAuthorized, 6087 SelfTransferNotAllowed |
| `buy_exact_quote_in_v2` | 0x1d1e2 | +1: 6001 ZeroBaseAmount, 6002 ZeroQuoteAmount, 6003 TooLittlePoolTokenLiquidity, 6020 DisabledBuy, 6039 BuyNotEnoughQuoteTokensToCoverFees, 6040 BuySlippageBelowMinBaseAmountOut; +2: 6007 UnsupportedQuoteMint, 6009 InvalidQuoteMint, 6023 Overflow, 6027 AccountTypeNotSupported, 6039 BuyNotEnoughQuoteTokensToCoverFees, 6040 BuySlippageBelowMinBaseAmountOut, 6079 CashbackCoinNotSupported; +3: 6023 Overflow, 6024 Truncation, 6025 DivisionByZero, 6053 BuybackFeeRecipientNotAuthorized, 6083 FeeConfigTooShort; +4: 6023 Overflow, 6025 DivisionByZero, 6082 FeeTiersEmpty |
| `buy_v2` | 0x1d15d | +1: 6001 ZeroBaseAmount, 6002 ZeroQuoteAmount, 6004 ExceededSlippage, 6020 DisabledBuy; +2: 6007 UnsupportedQuoteMint, 6009 InvalidQuoteMint, 6016 BuyMoreBaseAmountThanPoolReserves, 6023 Overflow, 6024 Truncation, 6027 AccountTypeNotSupported, 6079 CashbackCoinNotSupported; +3: 6023 Overflow, 6025 DivisionByZero, 6053 BuybackFeeRecipientNotAuthorized, 6083 FeeConfigTooShort; +4: 6025 DivisionByZero, 6082 FeeTiersEmpty; +5: 6024 Truncation |
| `claim_cashback` | 0x1da42 | +1: 6023 Overflow |
| `claim_token_incentives` | 0x1cc57 | +2: 6024 Truncation; +3: 6087 SelfTransferNotAllowed |
| `close_user_volume_accumulator` | 0x1cd93 | - |
| `collect_coin_creator_fee` | 0x1d51d | +1: 6048 CreatorVaultMigratedToSharingConfig; +3: 6087 SelfTransferNotAllowed |
| `create_config` | 0x1c17f | +2: 6000 FeeBasisPointsExceedsMaximum, 6011 AllProtocolFeeRecipientsShouldBeNonZero, 6012 UnsortedNotUniqueProtocolFeeRecipients |
| `create_pool` | 0x1c634 | +1: 6001 ZeroBaseAmount, 6002 ZeroQuoteAmount, 6006 UnsupportedBaseMint, 6007 UnsupportedQuoteMint, 6017 DisabledCreatePool, 6022 SameMint, 6028 OnlyCanonicalPumpPoolsCanHaveCoinCreator, 6041 MayhemModeDisabled, 6042 OnlyPumpPoolsMayhemMode, 6049 CashbackNotEnabled, 6050 OnlyPumpPoolsCashback; +2: 6003 TooLittlePoolTokenLiquidity, 6024 Truncation; +3: 6087 SelfTransferNotAllowed |
| `deposit` | 0x1ca4f | +1: 6004 ExceededSlippage, 6018 DisabledDeposit, 6024 Truncation; +2: 6007 UnsupportedQuoteMint, 6023 Overflow, 6024 Truncation, 6025 DivisionByZero; +3: 6023 Overflow |
| `disable` | 0x1c2a1 | - |
| `extend_account` | 0x1d47e | +1: 6027 AccountTypeNotSupported |
| `init_boost` | 0x1c7b3 | +2: 6024 Truncation; +3: 6023 Overflow |
| `init_user_volume_accumulator` | 0x1cce2 | - |
| `migrate_pool_coin_creator` | 0x1d8e7 | +1: 6074 HolderRewardCreatorImmutable, 6081 CreatorFeesNotSwept |
| `multi_hop_swap` | 0x1d2ec | +1: 6001 ZeroBaseAmount, 6002 ZeroQuoteAmount, 6004 ExceededSlippage, 6044 NotEnoughRemainingAccounts, 6084 MultiHopDiscontinuousPath, 6086 MultiHopMixedDirection; +2: 6001 ZeroBaseAmount, 6002 ZeroQuoteAmount, 6003 TooLittlePoolTokenLiquidity, 6020 DisabledBuy, 6021 DisabledSell, 6023 Overflow, 6027 AccountTypeNotSupported, 6044 NotEnoughRemainingAccounts, 6078 OnlyPumpPools, 6079 CashbackCoinNotSupported, 6080 MayhemPoolNotSupported, 6084 MultiHopDiscontinuousPath, 6085 MultiHopCurveRunMismatch; +3: 6009 InvalidQuoteMint, 6023 Overflow, 6024 Truncation, 6025 DivisionByZero, 6027 AccountTypeNotSupported, 6039 BuyNotEnoughQuoteTokensToCoverFees, 6040 BuySlippageBelowMinBaseAmountOut, 6063 InsufficientRealQuoteReserves; +4: 6023 Overflow, 6024 Truncation, 6025 DivisionByZero, 6083 FeeConfigTooShort; +5: 6082 FeeTiersEmpty |
| `sell` | 0x1d099 | +1: 6001 ZeroBaseAmount, 6004 ExceededSlippage, 6021 DisabledSell, 6063 InsufficientRealQuoteReserves; +2: 6013 InvalidProtocolFeeRecipient, 6023 Overflow, 6024 Truncation, 6025 DivisionByZero, 6058 BuybackFeeRecipientMissing, 6059 MissingCashbackAccounts, 6060 InvalidCashbackAccumulator, 6061 InvalidCashbackAccumulatorAta, 6062 InvalidPoolV2; +3: 6023 Overflow, 6025 DivisionByZero, 6053 BuybackFeeRecipientNotAuthorized; +4: 6024 Truncation |
| `sell_v2` | 0x1d267 | +1: 6001 ZeroBaseAmount, 6004 ExceededSlippage, 6021 DisabledSell; +2: 6009 InvalidQuoteMint, 6023 Overflow, 6024 Truncation, 6025 DivisionByZero, 6027 AccountTypeNotSupported, 6063 InsufficientRealQuoteReserves, 6079 CashbackCoinNotSupported; +3: 6053 BuybackFeeRecipientNotAuthorized, 6083 FeeConfigTooShort; +4: 6025 DivisionByZero, 6082 FeeTiersEmpty |
| `set_boost_authority` | 0x1c839 | - |
| `set_coin_creator` | 0x1d56e | +1: 6028 OnlyCanonicalPumpPoolsCanHaveCoinCreator |
| `set_reserved_fee_recipients` | 0x1c98d | +1: 6011 AllProtocolFeeRecipientsShouldBeNonZero, 6044 NotEnoughRemainingAccounts |
| `sweep_creator_fee` | 0x1d3f8 | +1: 6013 InvalidProtocolFeeRecipient; +2: 6013 InvalidProtocolFeeRecipient, 6023 Overflow |
| `sweep_protocol_fee` | 0x1d372 | +1: 6013 InvalidProtocolFeeRecipient; +2: 6013 InvalidProtocolFeeRecipient, 6023 Overflow |
| `sync_user_volume_accumulator` | 0x1ce17 | - |
| `toggle_boost` | 0x1d7cc | +1: 6005 InvalidAdmin |
| `toggle_cashback_enabled` | 0x1d977 | +1: 6051 CashbackNotInDesiredState |
| `toggle_mayhem_mode` | 0x1d701 | +1: 6043 MayhemModeInDesiredState |
| `transfer_creator_fees_to_pump` | 0x1d846 | +1: 6023 Overflow |
| `transfer_creator_fees_to_pump_v2` | 0x1d898 | +1: 6023 Overflow |
| `update_admin` | 0x1c398 | - |
| `update_buyback_config` | 0x1dacc | +1: 6057 WrongBuybackFeeRecipientsCount; +2: 6054 AllBuybackFeeRecipientsShouldBeNonZero, 6055 NotUniqueBuybackFeeRecipients, 6056 BuybackBasisPointsOutOfRange |
| `update_creator_fee_config` | 0x1c565 | - |
| `update_fee_config` | 0x1c446 | +2: 6000 FeeBasisPointsExceedsMaximum, 6011 AllProtocolFeeRecipientsShouldBeNonZero, 6012 UnsortedNotUniqueProtocolFeeRecipients |
| `withdraw` | 0x1caf6 | +1: 6004 ExceededSlippage, 6019 DisabledWithdraw, 6024 Truncation, 6067 SeedLockViolation; +2: 6023 Overflow, 6024 Truncation, 6025 DivisionByZero |

## pump_fees

- sha256 `4f2955d0f6b40cc9ff7daa18ccad7d19119ba1249759f4e7e3bb691beee6b35e`
- 96083 instructions / 489 functions (relocation-aware starts), 31 instruction handlers
- custom-error raise sites **68**, distinct codes **28**
- no per-program error-name table: the only table reachable from this build is `0x15ea0` (ABI `r2ptr`), 68 distinct names over codes from 2000 (ConstraintMut, ConstraintHasOne, ConstraintSigner, ConstraintRaw...), and it returns its `Deprecated` fallback for every program code. The table below therefore carries codes and origins only
- 68/68 sites carry an inline origin tuple (file + line), 68/68 resolve to at least one instruction handler

### codes

| code | name (binary) | sites | origins (file:line, first 3) |
|---:|---|---:|---|
| 6001 | - | 2 | instructions/admin/update_fee_program_global.rs:47, instructions/fee_sharing/admin_cto_sharing_config.rs:86 |
| 6002 | - | 2 | state.rs:383, state.rs:436 |
| 6003 | - | 2 | state.rs:405, state.rs:458 |
| 6004 | - | 2 | state.rs:385, state.rs:438 |
| 6005 | - | 2 | state.rs:418, state.rs:471 |
| 6006 | - | 4 | state.rs:365, state.rs:372, state.rs:411 |
| 6007 | - | 3 | instructions/fee_sharing/create_donation_fee_pda.rs:192, instructions/fee_sharing/create_donation_fee_pda.rs:197, instructions/fee_sharing/create_donation_fee_pda.rs:204 |
| 6008 | - | 7 | instructions/fee_sharing/create_donation_fee_pda.rs:148, instructions/fee_sharing/create_donation_fee_pda.rs:152, instructions/fee_sharing/create_donation_fee_pda.rs:156 |
| 6010 | - | 2 | instructions/fee_sharing/update_fee_shares.rs:258, instructions/fee_sharing/update_fee_shares_v2.rs:292 |
| 6011 | - | 2 | instructions/fee_sharing/update_fee_shares.rs:259, instructions/fee_sharing/update_fee_shares_v2.rs:293 |
| 6012 | - | 2 | instructions/fee_sharing/update_fee_shares.rs:292, instructions/fee_sharing/update_fee_shares_v2.rs:326 |
| 6013 | - | 4 | instructions/fee_sharing/update_fee_shares.rs:186, instructions/fee_sharing/update_fee_shares_v2.rs:237, instructions/fee_sharing/update_fee_shares_v2.rs:234 |
| 6014 | - | 2 | instructions/fee_sharing/update_fee_shares.rs:291, instructions/fee_sharing/update_fee_shares_v2.rs:325 |
| 6016 | - | 5 | instructions/fee_sharing/create_donation_fee_pda.rs:221, instructions/fee_sharing/create_donation_fee_pda.rs:213, instructions/fee_sharing/create_fee_sharing_config.rs:307 |
| 6017 | - | 2 | instructions/fee_sharing/update_fee_shares.rs:269, instructions/fee_sharing/update_fee_shares_v2.rs:303 |
| 6018 | - | 2 | instructions/fee_sharing/create_donation_fee_pda.rs:214, instructions/fee_sharing/mod.rs:99 |
| 6020 | - | 2 | instructions/fee_sharing/update_fee_shares.rs:188, instructions/fee_sharing/update_fee_shares_v2.rs:239 |
| 6022 | - | 1 | instructions/fee_sharing/create_social_fee_pda.rs:67 |
| 6023 | - | 2 | lib.rs:183, lib.rs:188 |
| 6024 | - | 2 | instructions/fee_sharing/update_fee_shares.rs:130, instructions/fee_sharing/update_fee_shares_v2.rs:137 |
| 6026 | - | 4 | instructions/admin/update_buyback_authority.rs:36, instructions/admin/update_buyback_authority.rs:47, instructions/buyback/mod.rs:94 |
| 6028 | - | 5 | instructions/admin/extend_fee_config.rs:47, instructions/admin/extend_fee_config.rs:52, instructions/admin/extend_fee_config.rs:63 |
| 6029 | - | 1 | instructions/fee_sharing/mod.rs:299 |
| 6030 | - | 1 | instructions/fee_sharing/mod.rs:306 |
| 6031 | - | 1 | instructions/fee_sharing/update_fee_shares.rs:129 |
| 6033 | - | 1 | instructions/fee_sharing/mod.rs:83 |
| 6034 | - | 1 | instructions/fee_sharing/update_fee_shares_v2.rs:152 |
| 6036 | - | 2 | instructions/withdraw.rs:91, instructions/withdraw.rs:125 |

### per handler

`direct` = raise site inside the handler body (call-graph depth 0); `+d` = first raise reachable at call-graph depth d.

| handler | handler pc | raises (depth) |
|---|---|---|
| `admin_cto_sharing_config` | 0x139e4 | +1: 6001 |
| `claim_social_fee_pda` | 0x13b5d | - |
| `claim_social_fee_pda_v2` | 0x13c64 | +2: 6029, 6030 |
| `crank_donation_fee_pda` | 0x140b8 | - |
| `create_donation_fee_pda` | 0x14044 | +1: 6007, 6008, 6016, 6018 |
| `create_fee_sharing_config` | 0x13810 | +1: 6008, 6016 |
| `create_social_fee_pda` | 0x13a95 | +1: 6022 |
| `extend_fee_config` | 0x134a2 | +1: 6028 |
| `get_fees` | 0x136a0 | - |
| `get_fees_with_quote_mint` | 0x13763 | - |
| `initialize_buyback` | 0x13d6a | +1: 6026 |
| `initialize_fee_config` | 0x12d72 | - |
| `initialize_fee_program_global` | 0x12e01 | - |
| `revoke_fee_sharing_authority` | 0x138ba | +1: 6023 |
| `set_authority` | 0x130de | +1: 6001 |
| `set_claim_rate_limit` | 0x13034 | - |
| `set_disable_flags` | 0x12f8a | - |
| `set_exotic_flat_fees` | 0x13541 | +2: 6006 |
| `set_social_claim_authority` | 0x12eca | - |
| `sweep_buyback` | 0x13e01 | +1: 6026 |
| `transfer_fee_sharing_authority` | 0x138c7 | +1: 6023 |
| `update_admin` | 0x135f3 | - |
| `update_buyback_authority` | 0x13ea6 | +1: 6026 |
| `update_buyback_claim_rate_limit` | 0x13f80 | +1: 6026 |
| `update_fee_config` | 0x1319e | +2: 6002, 6003, 6004, 6005, 6006 |
| `update_fee_shares` | 0x138d4 | +1: 6024, 6031; +2: 6010, 6011, 6012, 6013, 6014, 6016, 6017, 6018, 6033; +3: 6013, 6020 |
| `update_fee_shares_v2` | 0x1395a | +1: 6024, 6034; +2: 6010, 6011, 6012, 6013, 6014, 6016, 6017, 6018, 6020, 6033 |
| `update_stable_fee_config` | 0x13329 | +2: 6002, 6003, 6004, 6005, 6006 |
| `upsert_fee_tiers` | 0x13267 | +2: 6002, 6003, 6004, 6005, 6006 |
| `upsert_stable_fee_tiers` | 0x133e0 | +2: 6002, 6003, 6004, 6005, 6006 |
| `withdraw` | 0x14121 | +1: 6036 |

## mayhem

- sha256 `a87fa9f866272514e6acb852b668c4a08aeb173d56c883039991d114d1199bdb`
- 83947 instructions / 374 functions (relocation-aware starts), 25 instruction handlers
- custom-error raise sites **29**, distinct codes **14**
- no per-program error-name table: the only table reachable from this build is `0x1333d` (ABI `r2ptr`), 71 distinct names over codes from 2000 (ConstraintMut, ConstraintHasOne, ConstraintSigner, ConstraintRaw...), and it returns its `Deprecated` fallback for every program code. The table below therefore carries codes and origins only
- 21/29 sites carry an inline origin tuple (file + line), 29/29 resolve to at least one instruction handler

### codes

| code | name (binary) | sites | origins (file:line, first 3) |
|---:|---|---:|---|
| 6000 | - | 3 | state.rs:215, state.rs:221, state.rs:556 |
| 6002 | - | 5 | - |
| 6003 | - | 1 | - |
| 6004 | - | 2 | instructions/burn.rs:82, state.rs:579 |
| 6005 | - | 1 | - |
| 6006 | - | 1 | state.rs:243 |
| 6007 | - | 1 | state.rs:250 |
| 6008 | - | 4 | instructions/pump_interface.rs:313, instructions/pump_interface.rs:436, instructions/pump_interface_v2.rs:376 |
| 6010 | - | 2 | instructions/pump_amm_interface.rs:376, instructions/pump_amm_interface.rs:568 |
| 6014 | - | 2 | state.rs:110, state.rs:125 |
| 6015 | - | 1 | - |
| 6016 | - | 4 | instructions/extend_account.rs:89, instructions/extend_account.rs:108, instructions/fee_recipients.rs:399 |
| 6017 | - | 1 | instructions/fee_recipients.rs:186 |
| 6019 | - | 1 | instructions/fee_recipients.rs:61 |

### per handler

`direct` = raise site inside the handler body (call-graph depth 0); `+d` = first raise reachable at call-graph depth d.

| handler | handler pc | raises (depth) |
|---|---|---|
| `burn_tokens` | 0xffe1 | +1: 6004, 6005 |
| `buy` | 0x1027f | +1: 6008; +2: 6000, 6002, 6003, 6004, 6006, 6007, 6015 |
| `buy_pump_swap` | 0x1041f | +1: 6002; +2: 6000, 6002, 6003, 6004, 6006, 6007, 6010, 6015 |
| `buy_v2` | 0x1034f | +1: 6008; +2: 6000, 6002, 6003, 6004, 6006, 6007, 6015 |
| `extend_account` | 0x1001c | +1: 6016 |
| `initialize_fee_recipient` | 0xfc41 | +1: 6017 |
| `initialize_global_params` | 0xfbfc | - |
| `initialize_mayhem_state` | 0x101de | - |
| `reset_sol_deployed` | 0xff2d | - |
| `reset_stable_deployed` | 0xff59 | - |
| `reset_state` | 0xfef1 | - |
| `resume_trading` | 0xff85 | +1: 6000 |
| `sell` | 0x10217 | +1: 6008; +2: 6000, 6002, 6003, 6004, 6015 |
| `sell_pump_swap` | 0x103b7 | +1: 6002; +2: 6000, 6002, 6003, 6004, 6010, 6015 |
| `sell_v2` | 0x102e7 | +1: 6008; +2: 6000, 6002, 6003, 6004, 6015 |
| `stop_trading` | 0xffb3 | +1: 6000 |
| `sweep_fees` | 0xfc96 | +1: 6016; +2: 6019 |
| `sweep_fees_admin` | 0xfcd3 | +1: 6016 |
| `update_admin` | 0xfe93 | - |
| `update_global_params` | 0x1004b | +2: 6002 |
| `update_max_sol_per_sweep` | 0xfd10 | - |
| `update_max_stable_per_sweep` | 0xfd50 | - |
| `update_trader` | 0xfe35 | - |
| `withdraw_admin` | 0xfd90 | +2: 6014 |
| `withdraw_quote_admin` | 0xfde2 | +2: 6014 |

