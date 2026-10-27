# Drift map (pump, s7p)

unique pairs 784, intervals with delta != 0: 77, matched raw-fail windows with lddw diffs: 431

| class | intervals | call-only locks (sum, overlapping) | sum abs delta (B) |
|---|---:|---:|---:|
| anchor_wrapper | 6 | 591 | 63288 |
| monomorph | 30 | 2123 | 189792 |
| order_island | 24 | 1594 | 25975960 |
| source_fn_size | 17 | 1156 | 156184 |

| rank | locked | class | delta | deployed interval | candidate left anchor |
|---:|---:|---|---:|---|---|
| 1 | 162 | monomorph | -616 | `0x199bf8`..`0x19a020` | `_ZN4core3ptr74drop_in_place$LT$$u5b$solana_account_info..AccountInfo$u...` |
| 2 | 158 | monomorph | -664 | `0x17c548`..`0x17cae8` | `_ZN14pump_recovered5trade19native_transfer_fee3Fee24calculate_pre_fee_...` |
| 3 | 158 | monomorph | -3424 | `0x18f7a8`..`0x1909f8` | `_ZN14spl_token_20229extension16metadata_pointer11instruction10initiali...` |
| 4 | 156 | anchor_wrapper | -1936 | `0x17bc38`..`0x17c3d8` | `__rust_alloc_error_handler` |
| 5 | 156 | anchor_wrapper | -896 | `0x19e090`..`0x19e730` | `_ZN11anchor_lang14system_program8transfer17hb648f3970dbe8794E` |
| 6 | 154 | monomorph | -1040 | `0x163bf0`..`0x1642b8` | `_ZN82_$LT$pump_recovered..trade..PostCompleteBuyEvent$u20$as$u20$ancho...` |
| 7 | 154 | order_island | 556568 | `0x177138`..`0x1774f8` | `_ZN85_$LT$pump_recovered..legacy_sell..LegacySell$u20$as$u20$anchor_la...` |
| 8 | 154 | order_island | -557608 | `0x177700`..`0x177908` | `_ZN14pump_recovered15legacy_buy_exec7execute28_$u7b$$u7b$closure$u7d$$...` |
| 9 | 152 | source_fn_size | -2664 | `0x184a60`..`0x1858a0` | `_ZN10anchor_spl21token_2022_extensions14token_metadata31token_metadata...` |
| 10 | 94 | monomorph | -40 | `0x1ab1f8`..`0x1ab248` | `_ZN221_$LT$$LT$alloc..boxed..Box$LT$dyn$u20$core..error..Error$u2b$cor...` |
| 11 | 73 | anchor_wrapper | -51368 | `0x107f78`..`0x116158` | `_ZN129_$LT$pump_recovered..UpdateGlobalAuthority$u20$as$u20$anchor_lan...` |
| 12 | 73 | monomorph | -8712 | `0x116158`..`0x118920` | `_ZN95_$LT$pump_recovered..distribution..SharingConfig$u20$as$u20$ancho...` |
| 13 | 73 | monomorph | -2216 | `0x118b50`..`0x11a4f8` | `_ZN14pump_recovered9create_v216mayhem_interface3cpi23initialize_mayhem...` |
| 14 | 73 | monomorph | -256 | `0x124a70`..`0x125ae8` | `_ZN14pump_recovered9__private8__global10set_params17hfb21600d4ed47df5E` |
| 15 | 73 | source_fn_size | 16 | `0x12a048`..`0x12b2b0` | `_ZN14pump_recovered9__private8__global17sweep_creator_fee17hc5b669326c...` |
| 16 | 73 | monomorph | -520 | `0x12b7d8`..`0x12be78` | `_ZN14pump_recovered9__private8__global7migrate17hd423af712c3750f7E` |
| 17 | 73 | monomorph | -512 | `0x130d40`..`0x131eb0` | `_ZN14pump_recovered9__private8__global29get_minimum_distributable_fee1...` |
| 18 | 73 | order_island | 790384 | `0x135d60`..`0x137db8` | `_ZN14pump_recovered14pump_recovered25update_creator_fee_config17hebd50...` |
| 19 | 73 | source_fn_size | -53136 | `0x137db8`..`0x14eab8` | `_ZN4core3ops8function6FnOnce9call_once17hd7ef4b489cf9f725E` |
| 20 | 73 | source_fn_size | 1040 | `0x14eab8`..`0x14ecc0` | `_ZN14pump_recovered15legacy_buy_exec7execute28_$u7b$$u7b$closure$u7d$$...` |
| 21 | 73 | source_fn_size | -10592 | `0x14f2d8`..`0x1549b0` | `_ZN14pump_recovered15legacy_buy_exec7execute28_$u7b$$u7b$closure$u7d$$...` |
| 22 | 73 | monomorph | 1040 | `0x1551d0`..`0x1553d8` | `_ZN14pump_recovered16legacy_sell_exec7execute28_$u7b$$u7b$closure$u7d$...` |
| 23 | 73 | order_island | -58704 | `0x1553d8`..`0x1555e0` | `_ZN14pump_recovered16legacy_sell_exec7execute28_$u7b$$u7b$closure$u7d$...` |
| 24 | 73 | order_island | -654256 | `0x1555e0`..`0x156e30` | `_ZN4core3ops8function6FnOnce9call_once17hea50381b2d50f9ffE` |
| 25 | 71 | source_fn_size | -23608 | `0xd5878`..`0xdb728` | `_ZN93_$LT$pump_recovered..migrate..CompletePumpAmmMigrationEvent$u20$a...` |
| 26 | 70 | source_fn_size | -16816 | `0xbf668`..`0xc39b0` | `_ZN77_$LT$pump_recovered..CollectCreatorFeeEvent$u20$as$u20$anchor_lan...` |
| 27 | 70 | anchor_wrapper | -8504 | `0xcd230`..`0xcf750` | `_ZN81_$LT$pump_recovered..extend..ExtendAccountEvent$u20$as$u20$anchor...` |
| 28 | 69 | anchor_wrapper | -32 | `0xc4fc0`..`0xc7300` | `_ZN103_$LT$pump_recovered..distribution..DistributeCreatorFeesEvent$u2...` |
| 29 | 69 | source_fn_size | -1944 | `0xc8bf8`..`0xcadc0` | `_ZN133_$LT$pump_recovered..set_creator..SetCreator$u20$as$u20$anchor_l...` |
| 30 | 68 | order_island | 1254448 | `0xabe78`..`0xac2b8` | `_ZN75_$LT$pump_recovered..buy_v2..BuyV2$u20$as$u20$anchor_lang..Accoun...` |
| 31 | 68 | order_island | -1255488 | `0xac4c0`..`0xac6c8` | `_ZN14pump_recovered6buy_v213execute_inner28_$u7b$$u7b$closure$u7d$$u7d...` |
| 32 | 67 | monomorph | -3048 | `0x969f0`..`0x97930` | `_ZN14pump_recovered5trade14quote_payments15transfer_native17hc7fac06ff...` |
| 33 | 67 | monomorph | -7184 | `0x97eb0`..`0x9a048` | `_ZN14pump_recovered19user_quote_payments24transfer_from_user_owned17h3...` |
| 34 | 67 | anchor_wrapper | -552 | `0x9a048`..`0x9b6a0` | `_ZN14pump_recovered6buy_v218recipient_payments18split_protocol_fee17hf...` |
| 35 | 67 | monomorph | -8472 | `0x9f500`..`0xa2880` | `_ZN14pump_recovered11trade_types16historical_curve9decode_v817hb00e444...` |
| 36 | 65 | monomorph | -1664 | `0x95bd8`..`0x965b8` | `_ZN14pump_recovered5trade14quote_payments15transfer_native17h5f18ae913...` |
| 37 | 64 | monomorph | -13240 | `0x91ef0`..`0x95bd8` | `_ZN14pump_recovered7sell_v221quote_token_transfers21transfer_quote_tok...` |
| 38 | 63 | monomorph | -6328 | `0x8fe18`..`0x91ef0` | `_ZN14pump_recovered7sell_v220user_token_transfers20transfer_user_token...` |
| 39 | 61 | monomorph | -3264 | `0x8e450`..`0x8f5c8` | `_ZN14pump_recovered7migrate15native_payments15transfer_native17h536091...` |
| 40 | 58 | source_fn_size | -1232 | `0x8d108`..`0x8da98` | `_ZN14pump_recovered19user_quote_payments25transfer_native_recipient17h...` |
| 41 | 57 | source_fn_size | -1200 | `0x8c770`..`0x8d108` | `_ZN14pump_recovered7migrate15transfer_native17h27709daa49839e8cE` |
| 42 | 56 | order_island | 1446784 | `0x54db8`..`0x57c38` | `_ZN14pump_recovered10migrate_v212quote_amount17hfac67fec3795cb74E` |
| 43 | 56 | monomorph | -32264 | `0x57c38`..`0x5fc48` | `_ZN14pump_recovered15multi_hop_curve7execute28_$u7b$$u7b$closure$u7d$$...` |
| 44 | 56 | order_island | -1441408 | `0x60878`..`0x662c8` | `_ZN14pump_recovered15multi_hop_curve7execute28_$u7b$$u7b$closure$u7d$$...` |
| 45 | 56 | source_fn_size | -3488 | `0x68918`..`0x69978` | `_ZN14pump_recovered13quote_control5state12QuoteControl5space17hfea2fda...` |
| 46 | 56 | source_fn_size | -1744 | `0x69f28`..`0x6c160` | `_ZN14pump_recovered13quote_control5state12QuoteControl17set_mint_reser...` |
| 47 | 56 | order_island | 1391856 | `0x6c160`..`0x6f6d8` | `_ZN14pump_recovered13quote_control26update_quote_control_mints25remove...` |
| 48 | 56 | monomorph | 46608 | `0x6f8e0`..`0x6fae8` | `_ZN14pump_recovered7sell_v27execute28_$u7b$$u7b$closure$u7d$$u7d$17h7c...` |
| 49 | 56 | order_island | -47128 | `0x6fae8`..`0x6fcf0` | `_ZN14pump_recovered7sell_v27execute28_$u7b$$u7b$closure$u7d$$u7d$17h29...` |
| 50 | 56 | order_island | -1405016 | `0x6fcf0`..`0x79bc0` | `_ZN14pump_recovered7sell_v27execute28_$u7b$$u7b$closure$u7d$$u7d$17h1f...` |
| 51 | 56 | source_fn_size | -200 | `0x7a6c0`..`0x7bda8` | `_ZN14pump_recovered14pump_recovered28init_user_volume_accumulator17hee...` |
| 52 | 56 | source_fn_size | -8176 | `0x7bec0`..`0x7dfc8` | `_ZN14pump_recovered16token_incentives18volume_accumulator21record_cash...` |
| 53 | 56 | order_island | 1341896 | `0x7dfc8`..`0x81640` | `_ZN14pump_recovered16token_incentives18volume_accumulator7end_day17h88...` |
| 54 | 56 | monomorph | 33504 | `0x81640`..`0x84970` | `_ZN14pump_recovered5trade4sell28_$u7b$$u7b$closure$u7d$$u7d$17h9857641...` |
| 55 | 56 | order_island | -46608 | `0x84970`..`0x84b78` | `_ZN14pump_recovered5trade4sell28_$u7b$$u7b$closure$u7d$$u7d$17hbcc2f68...` |
| 56 | 56 | source_fn_size | -8944 | `0x857a8`..`0x87ca0` | `_ZN14pump_recovered5trade15buy_exact_quote28_$u7b$$u7b$closure$u7d$$u7...` |
| 57 | 56 | order_island | -1364096 | `0x87ea8`..`0x8a530` | `_ZN14pump_recovered5trade15buy_exact_quote28_$u7b$$u7b$closure$u7d$$u7...` |
| 58 | 56 | monomorph | -3584 | `0x8b818`..`0x8c770` | `_ZN74_$LT$pump_recovered..OptionBool$u20$as$u20$borsh..de..BorshDeseri...` |
| 59 | 55 | monomorph | 6456 | `0x32530`..`0x410b0` | `_ZN14pump_recovered7minimum7execute17h6663f383a7441471E` |
| 60 | 55 | order_island | 1469992 | `0x410b0`..`0x412b8` | `_ZN14pump_recovered7migrate7execute28_$u7b$$u7b$closure$u7d$$u7d$17h61...` |
| 61 | 55 | order_island | -1512232 | `0x412b8`..`0x4bb40` | `_ZN14pump_recovered7migrate7execute28_$u7b$$u7b$closure$u7d$$u7d$17hc3...` |
| 62 | 55 | order_island | 1467528 | `0x4bd48`..`0x4bf50` | `_ZN14pump_recovered10migrate_v27execute28_$u7b$$u7b$closure$u7d$$u7d$1...` |
| 63 | 55 | order_island | -1503984 | `0x4bf50`..`0x54db8` | `_ZN14pump_recovered10migrate_v27execute28_$u7b$$u7b$closure$u7d$$u7d$1...` |
| 64 | 54 | source_fn_size | -20344 | `0x296f0`..`0x32530` | `_ZN14pump_recovered9admin_cto16token_raw_amount17hb6ef5124005cbf60E` |
| 65 | 53 | order_island | 1587880 | `0x146c8`..`0x16bb8` | `_ZN99_$LT$anchor_lang..accounts..program..Program$LT$T$GT$$u20$as$u20$...` |
| 66 | 53 | source_fn_size | 1040 | `0x16dc0`..`0x16fc8` | `_ZN14pump_recovered6buy_v213execute_inner24creator_fee_add_overflow17h...` |
| 67 | 53 | monomorph | -768 | `0x171d0`..`0x176d8` | `_ZN14pump_recovered6buy_v213execute_inner28_$u7b$$u7b$closure$u7d$$u7d...` |
| 68 | 53 | order_island | -19720 | `0x17ae8`..`0x19cc0` | `_ZN14pump_recovered6buy_v213execute_inner28_$u7b$$u7b$closure$u7d$$u7d...` |
| 69 | 53 | order_island | -1605280 | `0x19cc0`..`0x296f0` | `_ZN4core3ops8function6FnOnce9call_once17ha54e7800f0b62a79E` |
| 70 | 52 | order_island | 1597960 | `0x12850`..`0x12ae8` | `_ZN97_$LT$anchor_lang..accounts..sysvar..Sysvar$LT$T$GT$$u20$as$u20$an...` |
| 71 | 52 | order_island | -1599136 | `0x12ae8`..`0x12f80` | `_ZN98_$LT$alloc..vec..Vec$LT$T$GT$$u20$as$u20$alloc..vec..spec_from_it...` |
| 72 | 50 | monomorph | -1424 | `0xefc8`..`0xf6c0` | `_ZN69_$LT$$u5b$T$u3b$$u20$N$u5d$$u20$as$u20$borsh..ser..BorshSerialize...` |
| 73 | 48 | monomorph | -1240 | `0xe9e8`..`0xef40` | `_ZN63_$LT$solana_pubkey..PubkeyError$u20$as$u20$core..fmt..Debug$GT$3f...` |
| 74 | 30 | monomorph | -448 | `0xd258`..`0xd4c0` | `_ZN58_$LT$alloc..string..String$u20$as$u20$core..fmt..Write$GT$9write_...` |
| 75 | 28 | monomorph | -336 | `0xce88`..`0xd068` | `_ZN51_$LT$u64$u20$as$u20$borsh..de..BorshDeserialize$GT$18deserialize_...` |
| 76 | 11 | monomorph | -688 | `0x6e78`..`0x7b40` | `_ZN11anchor_lang8accounts7account16Account$LT$T$GT$24exit_with_expecte...` |
| 77 | 6 | monomorph | -232 | `0x2930`..`0x2ca8` | `_ZN11anchor_lang5error5Error17with_account_name17hb6c5748ba3896f3aE` |
