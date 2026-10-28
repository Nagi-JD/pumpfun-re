# Chantier AMM — specs de reconstruction des 104 fenêtres PumpSwap restantes

> **Nature de ce document.** Spécs d'analyse, pas un build. Rien n'a été compilé, patché,
> ni écrit dans le binaire. Le `.so` déployé n'est jamais une entrée de build.
>
> **Crédit oracle (MIT).** Toute forme de source citée comme « oracle » vient de
> **lalalune/pumpfun-source** (`main` @ `6e6ac0fec28d186e76af23e0be4cb10af137e6f0`,
> 28 oct. 2026 ; checkpoint publié `dbb5dcfd…`, **660/785**), et de leurs paquets
> `repro/pump_amm/*`. Leur source est utilisée en lecture seule, comme ORACLE de forme.
> Aucun de leurs artefacts n'est un input de build et aucun `.so` capturé n'est embarqué.
>
> **Cible déployée.** `pump_amm` = `pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA`,
> `.so` sha256 `6a7ad34596d83b4c435b32f458a56e718e9f82eb4ad38e4316616d15d24d8ff7`,
> `.text` @ vaddr `0x120`, taille `0x11bb38`, **785 fenêtres**.
>
> **Notre profil mesuré.** `research/amm-r34-verified` état **g3** : **681/785**,
> 148 raw. Les 104 fenêtres ci-dessous sont exactement `g3.json["unmatched"]` (104 entrées).
>
> **Comment lire une entrée.** `(a)` fenêtre + instruction ; `(b)` candidat vs déployé ;
> `(c)` reconstruction exacte ; `(d)` classe ∈ {`wrapper`, `handler-form`, `needs-layout`}.
> `[M]` = mesuré dans le binaire déployé ; `[O]` = forme issue de l'oracle MIT ;
> `[H]` = hypothèse à valider par la mesure (le build/measure tranche).

---

## 0. Méthode de nommage (reproductible)

1. Découpage : `window_map.windows()` sur le `.so` déployé → 785 fenêtres
   (`address` = vaddr, `bytes`). `sbftool` indexe en `pc = vaddr / 8` (le `.text`
   déployé commence à `0x120`, divisible par 8) : **`func <so> $((addr/8))`**.
2. Nommage : (i) paires exactes avec le candidat symbolé de l'oracle
   — leur `results/build/unstripped.so` publié sert **uniquement** à lire les noms
   de symboles (mapping fenêtre→nom), jamais d'input de build — (660 fenêtres
   appariées → nom de symbole Rust) ; (ii) sinon
   `repro/pump_amm/v2-mint-clone-recovery-20261028/remaining-work.json`
   (125 fenêtres résiduelles de l'oracle, avec `historical_source_hint` = `file:line`
   déployé et `candidate_call_target_names`).
3. Résidu réel : on compare les instructions **en masquant ce que la métrique masque**
   (`lddw` littéral, cible de `call`, déplacement de pile `r10`), puis on ne garde que
   les octets significatifs. Les « littéraux » listés ici sont donc exclus ; les vrais
   écarts sont **les immédiats de `stw/stdw [r10-…], N` (ligne/colonne de `Location`
   ou code d'erreur)**, les **offsets de champ** et les **slots de frame**.
4. Pour chaque site `error!/require!`, l'immédiat déployé est la **ligne source
   d'origine**. C'est la même mécanique que `docs/WRAPPER_RECONSTRUCTION.md`
   (A2 / recipe b.7) et que les paquets `d1`/`d2` déjà vérifiés (+27 fenêtres).

### Ce que le score compte (rappel court)

La signature d'une fenêtre est le SHA des octets **moins** : adresses de `call`,
`lddw` relogés, imports. **Restent dans la signature** : `stw/stdw [r10-off], imm`
(donc la **ligne source** et le **code d'erreur**), les offsets de champ, les slots de
frame, l'ordre des blocs. C'est pourquoi « re-ligner » la source est le levier n°1, et
pourquoi deux copies identiques d'une même fonction peuvent être deux fenêtres
distinctes avec des lignes différentes.

---

## 1. Cinq causes racines (et ce qu'elles débloquent)

| # | Cause | Fenêtres | Levier source |
|---|---|---:|---|
| **R1** | `Location.line`/`col` déployés ≠ source compacte de l'oracle | ~45-55 | re-ligner le fichier : blank-lines **dans** les closures / entre items, en préservant les lignes des autres sites |
| **R2** | slots de frame / lifetime de temporaires / ordre de blocs | ~14 | bindings nommés, tuples, `let` de slice, `&UncheckedAccount` (noalias), fusion/défusion de helpers, ordre `if` |
| **R3** | layout `GlobalConfig` (ordre mémoire ≠ ordre wire) | 4 | réordonner la déclaration + `AnchorSerialize` manuel, cf. §6 |
| **R4** | inlining / clonage de corps (deux copies `quote_for_sell`, `select_and_apply`, gros handlers) | ~20 | dupliquer la logique au bon endroit, `#[inline(never)]`, séparer les helpers |
| **R5** | dépendances (native-transfer-fee, extensions T2022) | 4 | ajouter la dépendance / le chemin de crate de l'oracle |

**Rendement attendu** : R1 seule ≈ +40 à +55 ; T0 (17 portes exactes) ≈ +17 ;
R2/R3/R5 ≈ +10 ; le reste (R4, gros corps) ferme la distance à 785.

---

## 2. Table maîtresse des 104 fenêtres

Tri par facilité (T0 → T1 → T2 → T3 → T4). `n` = instructions significativement
différentes vs la meilleure fenêtre oracle (hors littéraux/calls masqués) ; `0` = la
forme est déjà identique au niveau instruction → il ne reste qu'un écart de
coordonnées/relocation (port ou re-ligne).

### T0 — port exact depuis l'oracle (17)

| addr | octets | fonction / module | n | action |
|---:|---:|---|---:|---|
| 96608 | 3024 | `__global::disable` (`lib.rs`) | 0 | copier le corps `disable` de l'oracle (déjà signature-égal chez eux) |
| 339032 | 1784 | `swap::trade_v2::create_sell_event` | 0 | idem |
| 360488 | 3552 | `swap::prepare_pool` | 0 | idem |
| 455856 | 344 | `create::OptionBool: BorshDeserialize` | 0 | idem (`create.rs:10-23`) |
| 474864 | 568 | `utils::token::supported_mint` | 0 | idem (`token.rs:186`) |
| 478768 | 1480 | `utils::token::harvest_withheld_tokens_to_mint` | 0 | idem (`token.rs:267`) |
| 930208 | 3064 | `__global::create_pool` | 0 | idem (`lib.rs`, wrapper args+`create::execute`) |
| 947784 | 1856 | `__global::buy` | 0 | idem |
| 949640 | 1856 | `__global::buy_exact_quote_in` | 0 | idem |
| 953064 | 1064 | `__global::buy_v2` | 0 | idem |
| 954128 | 1064 | `__global::buy_exact_quote_in_v2` | 0 | idem |
| 955192 | 1064 | `__global::sell_v2` | 0 | idem |
| 957328 | 1072 | `__global::sweep_protocol_fee` | 0 | idem |
| 958400 | 1072 | `__global::sweep_creator_fee` | 0 | idem |
| 994656 | 368 | `native_transfer_fee::DecodedTransferFee::calculate_fee` | 0 | ajouter la path-dep `crates/native-transfer-fee` (cf. §3) |
| 995024 | 776 | `native_transfer_fee::DecodedTransferFee::calculate_pre_fee_amount` | 0 | idem |
| 1011376 | 2664 | `anchor_spl` T2022 `harvest_withheld_tokens_to_mint` | 0 | feature `token_2022_extensions` + appel `transfer_fee::harvest_withheld_tokens_to_mint` (cf. §3) |

### T1 — re-ligne `Location` (le gros lot)

| addr | octets | fonction / module | n | cible |
|---:|---:|---|---:|---|
| 72136 | 1192 | `curve::constant_product::quote_for_base` | 2 | `constant_product.rs` 8→21, 10→24 |
| 73328 | 1184 | `quote_for_sell` (copie A) | 2 | 19→45, 20→47 |
| 74656 | 1184 | `quote_for_sell` (copie B) | 2 | 19→85, 20→87 (corps dupliqué, cf. §5) |
| 76552 | 1672 | `curve::fees::ceil_div` | 2 | `fees.rs` 18→19, 19→21 |
| 81200 | 856 | `curve::fees::tier` | 1 | `fees.rs` 62→160 |
| 111888 | 688 | `__global::toggle_cashback_enabled` | 6 | `toggle_cashback_enabled.rs` require 21 ; **+ champ `bool` à +946 (R3)** |
| 112576 | 832 | `__global::toggle_boost` | 2 | `toggle_boost.rs` require 14 |
| 113408 | 688 | `__global::toggle_mayhem_mode` | 2 | `toggle_mayhem_mode.rs` require 17 |
| 126168 | 696 | `boost::calculate_virtual_quote_reserves` | 1 | `boost.rs` 30→22 |
| 142464 | 520 | `execute_sell` closure | 2 | `trade_v2.rs` 387→258, 51→43 |
| 189024 | 520 | `execute_sell` closure | 3 | 387→290, + code 6003 au lieu de 6023 |
| 195384 | 7128 | `liquidity::deposit::deposit` | 6 | `deposit.rs` 14→77, 5→56, 15→79, 23→100 (+1 swap de loads, §5) |
| 206672 | 7200 | `liquidity::withdraw::withdraw` | 28 | même recette de re-ligne (mesurer site par site) |
| 225616 | 1376 | `buy::get_buyback_accounts` | 2 | `buy.rs` 477→116, 479→121 |
| 252112 | 752 | `multi_hop_swap::is_curve_hop` | 1 | `multi_hop_swap.rs` 256→239 |
| 262400 | 520 | `execute_sell` closure | 3 | 387→307, + code 6044 |
| 262920 | 1416 | `multi_hop_swap::program_for` | 1 | 133→414 |
| 283360 | 1256 | `multi_hop_swap::vault_for_mint` | 1 | 244→777 |
| 322192 | 1320 | `sell::validate_pool_v2` | 2 | `sell.rs` 8→520, 10→526 |
| 323512 | 544 | `trade_v2::validate_cashback_coin` | 1 | `trade_v2.rs` 59→103 |
| 324056 | 2280 | `trade_v2::validate_buyback_token_account` | 2 | 70→138, 75→146 |
| 327448 | 1664 | `trade_v2::total_quote` | 3 | 101→241 (×3) |
| 330920 | 600 | `BuyResult::total_user_quote` | 1 | 144→302 |
| 333536 | 1576 | `trade_v2::calculate_sell_quote` | 3 | 182→376, 183→377, 187→385 |
| 335984 | 3048 | `trade_v2::create_buy_event` | 1 | 288→515 |
| 359968 | 520 | `execute_sell` closure | 1 | 387→913 |
| 364040 | 1536 | `validate_protocol_fee_recipient` | 1 | `swap/mod.rs` 23→164 |
| 365576 | 4456 | `sweep_fees::execute` | 2 | `sweep_fees.rs` 32→91, 43→113 |
| 398896 | 616 | `GlobalConfig::set_lp_fee_basis_points` | 1 | 7→220 |
| 399512 | 616 | `GlobalConfig::set_protocol_fee_basis_points` | 2 | 7→230 ; offset mémoire 904 (R3, §6) |
| 400128 | 616 | `GlobalConfig::set_coin_creator_fee_basis_points` | 2 | 7→243 ; offset mémoire 912 (R3, §6) |
| 400744 | 2336 | `GlobalConfig::set_protocol_fee_recipients` | 2 | 25→256, 27→263 |
| 403080 | 1464 | `GlobalConfig::validate_boost_authority` | 2 | 92→297, 91→292 |
| 404544 | 552 | `GlobalConfig::set_buyback_basis_points` | 1 | 70→306 |
| 405096 | 2320 | `GlobalConfig::validate_buyback_recipient` | 3 | 47→336, 42→321, 43→326 |
| 407416 | 5472 | `GlobalConfig::set_buyback_fee_recipients` | 2 | 80→357, 76→347 |
| 443176 | 1088 | `Pool::effective_quote_reserves` | 2 | `pool.rs` 47→439, 48→440 |
| 444264 | 2496 | `Pool::accrue_fees` | 4 | 31→462, 27→458, 34→465, 38→469 |
| 475432 | 1312 | `transfer_fee::from_mint` | 1 | `transfer_fee.rs` → ligne 32 (`UnsupportedQuoteMint`) |
| 476744 | 696 | `transfer_fee::calculate_fee` | 1 | → ligne 49 |
| 478080 | 688 | `transfer_fee::amount_before_fee` | 1 | → ligne 67 |
| 717744 | 8128 | `TradeV2::try_accounts` closure (wrapper) | 2 | 31→133, 51→46 (`trade_v2.rs` derive) |
| 758472 | 520 | `execute_sell` closure | 2 | 387→941 |
| 869600 | 728 | `GlobalVolumeAccumulator::try_deserialize` | 1 | `volume_accumulator.rs` 3→8 |
| 872336 | 728 | `UserVolumeAccumulator::try_deserialize` | 1 | 13→25 |

### T2 — frame-slot / lifetime / ordre de blocs / aliasing

| addr | octets | fonction | n | levier |
|---:|---:|---|---:|---|
| 8840 | 232 | `anchor_lang::error::Error::from(io::Error)` | 21 | forme du `From` (ordre des `store`/branches) ; cf. §5.7 |
| 50640 | 1240 | `[T; N] : BorshSerialize::serialize` | 6 | arrangement des champs/`for` ; 6 slots de frame |
| 64264 | 704 | `slice::Concat::concat` | 74 | ordre des blocs + slots (bibliothèque) |
| 116880 | 1344 | `admin::update_buyback_config` | 5 | slots `-528/-112/-272` → tuples/named locals |
| 142984 | 4024 | `__global::collect_coin_creator_fee` | 29 | mélange line + frame ; traiter R1 d'abord, puis slots |
| 190240 | 5144 | `__global::extend_account` | 292 | inlining de `extend` ; helper boundary |
| 206672 | 7200 | `withdraw` | 28 | R1 puis slots (voir §4) |
| 281264 | 536 | `multi_hop_swap::apply_hop_fees` | 39 | ordre des blocs (`if` chain) + slots -56/-48 |
| 335112 | 872 | `trade::buy_transfers` | 5 | shape de branchement (`jne` vs `jeq;ja`) |
| 447496 | 1816 | `volume_accumulator` (helpers) | 141 | forme des méthodes, `try_into` |
| 449312 | 6312 | `GlobalVolumeAccumulator` impl | 528 | gros corps, ordre des blocs |
| 455624 | 232 | `<T as ToString>::to_string` | 18 | `format!`/`write!` shape (bibliothèque) |
| 993464 | 1192 | `native_transfer_fee::supported_mint_data` | 99 | formes de décodage TLV ; dépendance |
| 995800 | 664 | `native_transfer_fee::decode_transfer_fees` | 27 | ordre des branchements TLV |

### T3 — layout explicite

| addr | octets | fonction | n | levier |
|---:|---:|---|---:|---|
| 399512 | 616 | `set_protocol_fee_basis_points` | 2 | `u64` à l'offset mémoire **904** (cf. §6) |
| 400128 | 616 | `set_coin_creator_fee_basis_points` | 2 | `u64` à l'offset mémoire **912** (cf. §6) |
| 111888 | 688 | `toggle_cashback_enabled` | 6 | `bool` à l'offset mémoire **946** (cf. §6) |
| 113408 | 688 | `toggle_mayhem_mode` | 2 | ordre mémoire ; sonder le bool avant de changer |

### T4 — handler-form / refactor de corps

| addr | octets | fonction | n | levier principal |
|---:|---:|---|---:|---|
| 78936 | 2264 | `curve::fees::select_and_apply` | 155 | inlining CPI + ordre ; corps inliné dans create_pool |
| 82056 | 1656 | `curve::fees::select_and_apply_v2` | 94 | idem |
| 84256 | 6152 | `admin_cto_pool` | 182 | **révision différente** (gardes 6080/6088/6092/6095), cf. `MASTER_GAPS` B/Track2 |
| 90408 | 3168 | `admin_update_token_incentives` | 95 | corps + frames ; cf. paquet `incentives-thirty-one` |
| 102712 | 9176 | `set_reserved_fee_recipients` | 682 | boucle 8 comptes, `format!`/`with_account_name`, ordre |
| 126864 | 3912 | `boost::execute` | 110 | inlining/`&UncheckedAccount` |
| 130776 | 11688 | `boost_buy_and_burn` | 415 | gros corps + CPI |
| 147008 | 4504 | `migrate_pool_coin_creator` | 66 | ordre des comptes/CPI |
| 151512 | 7632 | `set_coin_creator` | 292 | corps |
| 159144 | 8232 | `transfer_creator_fees_to_pump` | 495 | corps + transferts |
| 167376 | 11024 | `transfer_creator_fees_to_pump_v2` | 559 | corps |
| 178784 | 10240 | `create_pool::execute` | 500 | corps (le plus gros du module) |
| 217512 | 8104 | `buy::distribute_cashback` | 543 | helper boundary |
| 226992 | 9936 | `__global::buy` (legacy) | 535 | corps legacy |
| 239008 | 12936 | `__global::buy_exact_quote_in` | 646 | corps legacy |
| 252864 | 9536 | `multi_hop::execute` | 963 | route/CPI ; cf. `multi-hop-thirty-seven` |
| 264712 | 15512 | `multi_hop` (route) | 1579 | gros routeur |
| 284992 | 16912 | `multi_hop_swap::amm_hop` | 1926 | plus grosse fenêtre |
| 301904 | 9184 | `__global::sell` | 614 | corps legacy sell |
| 313168 | 9024 | `legacy_sell::cashback` | 714 | corps cashback |
| 329112 | 1808 | `trade_v2::calculate_buy_result` | 57 | corps |
| 331520 | 2016 | `trade_v2::estimate_buy_quote` | 74 | corps |
| 340816 | 5840 | `trade_v2::execute_buy` | 265 | corps |
| 346656 | 7112 | `trade_v2::execute_buy_exact_quote` | 254 | corps |
| 354064 | 5904 | `trade_v2::execute_sell` | 191 | corps |
| 370032 | 4168 | `__global::claim_token_incentives` | 197 | corps ; `incentives-thirty-one` |
| 374200 | 4056 | `__global::claim_cashback` | 98 | corps ; `cashback-thirty-two` |
| 378256 | 2816 | `close_user_volume_accumulator` | 54 | corps |
| 384032 | 2904 | `sync_user_volume_accumulator` | 69 | corps |

> Couverture exacte des **104** : **17** (T0) + **45** (T1) + **13** nouveaux en T2
> (14 lignes, dont 206672 déjà en T1) + **29** (T4). Le T3 est **transversal** : ses
> 4 fenêtres (399512, 400128, 111888, 113408) sont déjà comptées en T1 ; il ne crée
> pas de fenêtre supplémentaire, il ajoute la correction de champ.

---

### Classement (d) — une classe par fenêtre

- **`wrapper` (13)** : `930208`, `947784`, `949640`, `953064`, `954128`, `955192`,
  `957328`, `958400`, `96608`, `455856`, `717744`, `869600`, `872336`.
  Entrées `#[program]` / arg-codec Anchor / `try_accounts` / `try_deserialize` ;
  `455856` est le `BorshDeserialize` de `OptionBool`, assimilé wrapper de serde.
- **`needs-layout` (4)** : `399512`, `400128`, `111888`, `113408` (ordre mémoire
  `GlobalConfig`, §6). `84256` est `handler-form` **mais** relève d'une **révision
  différente** (gardes), à traiter à part (§7.14).
- **`handler-form` (toutes les autres, 87 fenêtres)** : corps métier, helpers,
  closures, monomorphisations ; levier = forme source (ligne, frame, inlining,
  alias), jamais le wrapper.

> Total : 13 wrapper + 4 needs-layout + 87 handler-form = **104**. Chaque ligne des
> tableaux T0–T4 hérite de cette classe ; les cas mixtes sont signalés dans la
> colonne action.

## 3. T0 — reconstruction exacte des 17 portes

Ces fenêtres sont **déjà signature-égales** dans le build de l'oracle (660). La
reconstruction est donc un **port de source**, pas une invention. Deux familles.
Mesure d'abord : si le corps est déjà textuellement identique dans notre arbre, le
résidu est dans la **table des chemins/lignes** (wrapper/arg-codec) ou dans une
monomorphisation voisine — aligner alors chemins et lignes de la définition, pas la
logique.

### 3.1 Corps purs (`lib.rs`, `trade_v2.rs`, `swap/mod.rs`, `create.rs`, `utils/token.rs`)

Pour chacune, copier la définition de l'oracle **telle quelle** (mêmes noms, même
ordre d'arguments, mêmes `msg!`, même `Context<…>`), dans le fichier au **même chemin
déployé** (le chemin est baked dans `.rodata`, et les lignes des `error!` comptent) :

- `96608` `pub fn disable(...)` — `lib.rs` (5 booléens, ordre
  create/deposit/withdraw/buy/sell, event `DisableEvent`, `emit!` + `emit_cpi!`).
- `930208` `create_pool`, `947784` `buy`, `949640` `buy_exact_quote_in`,
  `953064` `buy_v2`, `954128` `buy_exact_quote_in_v2`, `955192` `sell_v2`,
  `957328` `sweep_protocol_fee`, `958400` `sweep_creator_fee` — `lib.rs`.
  Vérifier en particulier : le `msg!("Instruction: <PascalName>")` est généré par
  `#[program]` ; les longueurs de la chaîne dans `__private::__global::*` doivent
  être 28 (`BuyExactQuoteIn`), 30 (`BuyExactQuoteInV2`), 19 (`SellV2`), 28
  (`SweepCreatorFee`). Si le candidat logue `Instruction: Buy`, c'est que la
  fonction a été aliasée/fusionnée : **séparer les `pub fn`** (déjà le cas dans
  l'oracle) et ne pas partager de helper `#[inline(always)]`.
- `339032` `create_sell_event`, `360488` `prepare_pool` — corps exacts.
- `455856` `OptionBool: BorshDeserialize::deserialize_reader` — `create.rs:10-23`
  (read_exact 1 octet, `InvalidData` sinon, `UnexpectedEof => Ok(false)`).
- `474864` `supported_mint`, `478768` `harvest_withheld_tokens_to_mint` —
  `utils/token.rs:186` et `:267`.

### 3.2 Dépendances (`native-transfer-fee`, extensions T2022)

- `994656`, `995024`, `993464`, `995800` : ajouter
  `native-transfer-fee = { path = "../../crates/native-transfer-fee" }`
  (déclaration oracle `programs/pump-amm/Cargo.toml`) et importer
  `pub use native_transfer_fee::DecodedTransferFee;`. Le crate porte
  `calculate_fee` / `calculate_pre_fee_amount` / `decode_transfer_fees` /
  `supported_mint_data` ; ne pas les réécrire en Rust local (le layout des slots
  diffère, cf. `utils/transfer_fee.rs` de l'oracle qui ne fait que l'adaptation).
- `1011376` : `anchor-spl` T2022 extension
  `transfer_fee::harvest_withheld_tokens_to_mint`. Activer
  `token_2022_extensions` (déjà dans le Cargo oracle) et appeler la fonction
  d'extension (pas une ré-implémentation). Le wrapper métier est
  `utils/token.rs::harvest_withheld_tokens_to_mint`.

**Vérification** : `tools/measure.py` doit voir +17 sans perte sur `matched_set`
ni `raw_set`. Ces 17 sont indépendants ; les faire en premier.

---

## 4. T1 — re-ligne `Location` : recette exacte

### 4.1 Principe

Pour un site `error!(E)` / `require!(…, E)`, le binaire stocke
`Location { file, line, col }`. Dans la fenêtre, la ligne apparaît comme
`stw [r10-…], <line>` et la colonne comme l'immédiat voisin. La **ligne déployée
est connue** (colonne `cible` ci-dessus). Il faut que le `error!` compile sur
**cette** ligne.

Méthode (identique à `d1`/`d2`, déjà +27) :
1. Repérer dans le fichier oracle le `error!/require!` qui produit le site
   (la ligne compacte de l'oracle est donnée par la colonne « source » ci-dessous).
2. Déplacer ce site vers la ligne déployée **sans déplacer les autres** :
   insérer des lignes vides **à l'intérieur** de la closure/expression (comme
   `amm-r34-d1.patch`), ou joindre des expressions, de sorte que :
   `site_i < cible_i`, et `site_{i+1}` garde sa ligne.
3. Ne jamais ajouter/retirer un `require!`, ne jamais changer le code d'erreur.
4. Rebuild + measure ; garder si `matched` monte et `raw` ne perd rien.

Les fichiers ci-dessous ont **plusieurs fenêtres** : une seule passe de re-ligne
par fichier, puis mesure.

### 4.2 `curve/constant_product.rs` — 3 fenêtres (R1 + R4)

Sites oracle (fichier compact de 28 lignes) :
- `8` `.ok_or_else(|| error!(BuyMoreBaseAmountThanPoolReserves))?`
- `10` `u64::try_from(quote).map_err(|_| error!(Truncation))`
- `19` `.ok_or_else(|| error!(DivisionByZero))?;`
- `20` `u64::try_from(quote).map_err(|_| error!(Truncation))`

Cibles déployées :
| fenêtre | site | ligne déployée |
|---:|---|---:|
| 72136 (`quote_for_base`) | 8 | **21** |
| 72136 | 10 | **24** |
| 73328 (`quote_for_sell`, copie A) | 19 | **45** |
| 73328 | 20 | **47** |
| 74656 (`quote_for_sell`, copie B) | 19 | **85** |
| 74656 | 20 | **87** |

Pour 72136/73328 : padder le fichier pour amener 8→21 et 10→24 (et 19→45, 20→47)
en gardant les autres. Pour **74656** : c'est une **seconde copie** du corps
(`quote_for_sell` inliné/dupliqué). La forme oracle a `#[inline(never)]` et un seul
corps ; le déployé en a deux (lignes 85/87). Reconstruction : dans la fonction
appelante (celle qui produit la 2e copie, vraisemblablement `base_for_quote`),
**dupliquer l'expression** de `quote_for_sell` (ou ajouter une seconde fonction
`#[inline(never)] fn quote_for_sell_copy` utilisée par `base_for_quote`) et placer
ses deux `error!` aux lignes 85/87. Classe `handler-form` (clonage), pas wrapper.
Si le mesure montre que la 2e copie vient d'un `#[inline(always)]`, préférer la
duplication locale (ne pas changer les appels des autres sites).

### 4.3 `curve/fees.rs` — 2 fenêtres

| fenêtre | construction oracle | l. oracle | l. déployée |
|---:|---|---:|---:|
| 76552 (`ceil_div`) | `.checked_sub(1).ok_or_else(|| error!(Overflow))?` | 18 | **19** |
| 76552 | `.checked_div(denominator).ok_or_else(|| error!(DivisionByZero))` | 19 | **21** |
| 81200 (`tier`) | `require!(!tiers.is_empty(), FeeTiersEmpty);` | 62 | **160** |

Pad entre les deux `checked_*` pour 18→19/19→21 (attention : 19→21 décale la suite,
compenser). Pour `tier`, le site doit être à 160 → ajouter ~98 lignes **avant** le
`require!` de `tier` (commentaires/blanks dans les items précédents), ou déplacer
`tier` plus bas dans le fichier en gardant les autres sites.

### 4.4 `instructions/boost.rs` — 126168

`calculate_virtual_quote_reserves` : `.map_err(|_| error!(Truncation))` oracle l.30 →
déployé **22**. Padder **au-dessus** de la closure (ou remonter la fonction) de 8
lignes.

### 4.5 `instructions/swap/buy.rs` — 225616

`get_buyback_accounts` : deux `.ok_or_else(|| error!(BuybackFeeRecipientMissing))?`
oracle l.477 et 479 → déployé **116** et **121**. Il faut donc **remonter** ces deux
sites de 361/358 lignes : la fonction est beaucoup plus haut dans le fichier
d'origine. Déplacer `get_buyback_accounts` (et son contenu) vers le haut du fichier
pour que les sites tombent à 116/121, en conservant les lignes des autres sites de
`buy.rs`. Si un autre site de `buy.rs` est déjà apparié, il ne doit pas bouger.

### 4.6 `instructions/swap/sell.rs` — 322192

`validate_pool_v2` : `require!(index < len, InvalidPoolV2)` oracle l.8 → **520** ;
`require_keys_eq!(remaining[index].key(), expected, InvalidPoolV2)` l.10 → **526**.
Déplacer la fonction vers la ligne ~520 (fichier d'origine long) — même technique.

### 4.7 `instructions/swap/trade_v2.rs` — 11 fenêtres

Sites et cibles :

| fenêtre | fonction | oracle → déployé |
|---:|---|---|
| 323512 | `validate_cashback_coin` | 59 → **103** |
| 324056 | `validate_buyback_token_account` | 70 → **138** ; 75 → **146** |
| 327448 | `total_quote` | 101 → **241** (les 3 occurrences) |
| 330920 | `BuyResult::total_user_quote` | 144 → **302** |
| 333536 | `calculate_sell_quote` | 182 → **376** ; 183 → **377** ; 187 → **385** |
| 335984 | `create_buy_event` | 288 → **515** |
| 359968 | `execute_sell` closure | 387 → **913** |
| 189024 | idem | 387 → **290** (et code 6003 ≠ 6023) |
| 262400 | idem | 387 → **307** (et code 6044) |
| 142464 | idem | 387 → **258** ; 51 → **43** |
| 758472 | idem (`multi_hop_swap.rs:941` dans le hint) | 387 → **941** |

Remarques :
- 189024 et 262400 stockent un **code d'erreur** (6003/6044) là où l'oracle met
  6023 (`Overflow`). Rappel de l'enum : `6003 = 6000+3 = TooLittlePoolTokenLiquidity`,
  `6044 = 6000+44 = NotEnoughRemainingAccounts`, `6023 = Overflow`. **Ne pas changer
  le code sans preuve** : dans le déployé c'est bien 6003/6044 ; identifier le
  `require!/error!` du corps `execute_sell` qui porte cet index et placer **sa**
  ligne, sans toucher aux autres sites.
- 142464 : le site `51` oracle est le `#[account(mut)] pub buyback_fee_recipient`
  (ce n'est pas un `error!`) ; le vrai site de ligne est 387→258. Traiter 258
  d'abord, puis vérifier 51→43 (déclaration de compte, wrapper).
- 758472 : le hint pointe `multi_hop_swap.rs:941` ; le corps est une closure
  `execute_sell` **inlinée dans** `multi_hop_swap`. Placer le `error!` à 941 dans
  la source de `execute_sell` ne suffit pas si le fichier est différent : il faut
  que la **Location** pointe `.../swap/multi_hop_swap.rs` ligne 941, donc dupliquer
  la closure dans `multi_hop_swap.rs` (forme handler) ou déplacer l'appel.

### 4.8 `instructions/swap/mod.rs` — 364040

`validate_protocol_fee_recipient` : `err!(InvalidProtocolFeeRecipient)` oracle l.23
→ déployé **164**. Déplacer la fonction / padder.

### 4.9 `instructions/sweep_fees.rs` — 365576

`execute` : `require_keys_neq!(…)` oracle l.32 → **91** ; `require_keys_eq!(…)`
l.43 → **113**. Padder entre les deux (attention au décalage cumulé).

### 4.10 `state/global_config.rs` — 8 fenêtres (R1 + R3)

| fenêtre | méthode | site oracle → déployé |
|---:|---|---|
| 398896 | `set_lp_fee_basis_points` | 7 → **220** |
| 399512 | `set_protocol_fee_basis_points` | 7 → **230** (+ offset champ) |
| 400128 | `set_coin_creator_fee_basis_points` | 7 → **243** (+ offset champ) |
| 400744 | `set_protocol_fee_recipients` | 25 → **256** ; 27 → **263** |
| 403080 | `validate_boost_authority` | 92 → **297** ; 91 → **292** |
| 404544 | `set_buyback_basis_points` | 70 → **306** |
| 405096 | `validate_buyback_recipient` | 47 → **336** ; 42 → **321** ; 43 → **326** |
| 407416 | `set_buyback_fee_recipients` | 80 → **357** ; 76 → **347** |

Le fichier d'origine avait ces méthodes réparties jusqu'à la ligne ~360 ; le
fichier oracle compact les met à 7-92. **Réordonner/padder** le fichier pour
reproduire ces lignes (les `impl` peuvent rester, mais l'ordre et les blanks
doivent placer chaque `require!` sur sa cible). Faire les offsets de champ (R3,
§6) **dans la même passe** pour 399512/400128.

### 4.11 `state/pool.rs` — 2 fenêtres

| fenêtre | méthode | oracle → déployé |
|---:|---|---|
| 443176 | `effective_quote_reserves` | 47 → **439** ; 48 → **440** |
| 444264 | `accrue_fees` | 31 → **462** ; 27 → **458** ; 34 → **465** ; 38 → **469** |

Même recette : le fichier d'origine est long ; placer les 4 `error!(Overflow)` de
`accrue_fees` aux lignes 458/462/465/469 et les 2 de `effective_quote_reserves` à
439/440.

### 4.12 `utils/transfer_fee.rs` — 3 fenêtres

| fenêtre | fonction | ligne déployée | site |
|---:|---|---:|---|
| 475432 | `from_mint` | **32** | `error!(UnsupportedQuoteMint)` (oracle l.30) |
| 476744 | `calculate_fee` | **49** | `error!(Overflow)` de `fee.calculate_fee(amount)` |
| 478080 | `amount_before_fee` | **67** | `error!(Overflow)` de `calculate_pre_fee_amount` |

Pad de 2/… lignes dans chaque closure. **Attention** : l'oracle a beaucoup de
doc-commentaires ; ils sont utiles pour atteindre les lignes sans toucher au code.

### 4.13 `state/volume_accumulator.rs` — 2 fenêtres (wrapper)

`GlobalVolumeAccumulator::try_deserialize` : le `#[account]` oracle est l.3 →
déployé **8** ; `UserVolumeAccumulator` l.13 → **25**. Ce sont les `Location` du
discriminator/`AccountDeserialize` générés : déplacer les attributs/structs pour
que les `#[account]` soient aux lignes 8 et 25 (ajouter des blanks/commentaires
au-dessus), sans changer l'ordre des champs.

### 4.14 Toggles — 3 fenêtres (R1 + R3)

Le déployé a des **fichiers dédiés** (`instructions/admin/toggle_*.rs`) ; l'oracle
les a dans `lib.rs`. Pour la signature, seules les lignes/colonnes et le champ
comptent, mais pour le raw/loc il faut les **chemins dédiés** :

| fenêtre | fichier déployé | require | ligne |
|---:|---|---|---:|
| 111888 | `toggle_cashback_enabled.rs` | `require_neq!(is_cashback_enabled, enabled, CashbackNotInDesiredState)` (code **6051**) | **21** |
| 112576 | `toggle_boost.rs` | `require_keys_neq!(boost_authority, default, InvalidAdmin)` (code 6005) | **14** |
| 113408 | `toggle_mayhem_mode.rs` | `require_neq!(mayhem_mode_enabled, enabled, MayhemModeInDesiredState)` (6043) | **17** |

Reconstruction : créer les 3 fichiers, y déplacer les 3 corps depuis `lib.rs`
(le `#[program]` appelle le module), placer chaque `require!` à sa ligne, et
corriger le champ (`disable_flags`/bool à +946, cf. §6). Vérifier que les codes
d'erreur restent 6051/6005/6043.

### 4.15 `liquidity/deposit.rs` — 195384

Sites : `14→77` (Truncation), `5→56` (DisabledDeposit), `15→79`
(ExceededSlippage base), `23→100` (ExceededSlippage quote). Plus un **swap de
deux loads** aux indices +563/+564 (`ldxdw r1,[r8]` vs `ldxdw r1,[r10-832]`) :
c'est un **choix d'allocation/ordre d'évaluation** (R2), pas sémantique.
Faire R1 d'abord ; si le swap reste, nommer les temporaires
(`let base_account = &...; let quote_account = &...;` puis les usages dans l'ordre
déployé) — mesurer.

### 4.16 `liquidity/withdraw.rs` — 206672

28 diffs, majoritairement des lignes de `Location` (le fichier d'origine place les
`require_gte!`/`checked_*` bien plus bas). Extraire les cibles en désassemblant
`sbftool func 0x32750/8` et en lisant les `stw [r10-…], <line>` des sites, puis
appliquer la même re-ligne site par site. **Ne pas** réutiliser les placements
`withdraw 162/166/170` du paquet u2 :
le profil g3 a déjà ces gains, les sites restants sont d'autres lignes.

### 4.17 `TradeV2::try_accounts` closure — 717744 (wrapper)

Deux sites : l.31 (`#[derive(Accounts)]`) → **133** et l.51
(`#[account(mut)] buyback_fee_recipient: UncheckedAccount`) → **46**. Ce sont des
`Location` du parser généré (contraintes). Réordonner/padder la déclaration
`TradeV2` pour que les `#[account(...)]` concernés tombent aux lignes déployées ;
le **type** du champ doit rester `UncheckedAccount` (sinon l'`exit` change, cf.
WRAPPER_RECONSTRUCTION A1). Mesurer, puis ajuster l'ordre des champs si les
offsets de struct bougent.

---

## 5. T2 — frame-slots, lifetimes, ordre de blocs, aliasing

Rappel de la recette b.7 (`WRAPPER_RECONSTRUCTION.md`) :
- **inlining** : un helper `fn` (pas de `#[inline(always)]`) appelé depuis un site
  froid peut être inliné ou non ; pour forcer la frontière, `#[inline(never)]`.
- **ordre des blocs** : SBF `analyzeBranch` ne plie pas les branches conditionnelles ;
  l'ordre des blocs suit l'ordre IR. Un `if/else` ≠ `match` ≠ `&&`.
- **slots de frame** : SROA/StackColoring assigne les offsets selon les bindings
  nommés, les tuples et les slices. Deux écritures dans le même temporaire
  fusionnent ; un `let` nommé sépare.
- **noalias** : passer `&AccountInfo` à un helper marque `noalias readonly` et fait
  réutiliser un pointeur après `pack()`. Passer **`&UncheckedAccount`** (ou
  `let x: &AccountInfo = x.as_ref();`) force le reload.

Applications :

- **116880** `update_buyback_config` : 4 `add64 r?, -528/-112/-272` déplacés. C'est
  l'allocation des temporaires de `Option<u64>` + `[Pubkey;8]`. Forme à essayer :
  `let mut recipients = [Pubkey::default(); 8];` **avant** le `if let Some(bps)`,
  et `let accounts = &mut *ctx.accounts;` en un seul binding ; mesurer les offsets
  (§ paquet oracle `admin-five`/`update_buyback_config`).
- **190240** `extend_account` : 292 diffs → l'oracle a un helper
  `extend_global_config` (admin/mod.rs) ; le déployé l'inline dans `extend_account`.
  Essayer `#[inline(always)]` sur `extend_global_config`, ou dupliquer le corps.
- **281264** `apply_hop_fees` : 39 diffs, slots `-56/-48` et ordre de branches.
  Réécrire avec des bindings nommés (`let fee = ...?; let net = ...?;`) et l'ordre
  `if` déployé (extraire les branches de `amm_hop`).
- **335112** `trade::buy_transfers` : 5 diffs de **branchement** uniquement
  (`jne` vs `ja`). C'est l'ordre des `if` ; inverser la condition ou remplacer
  `if a {..} else if b {..}` par l'ordre déployé. Mesurer.
- **142984** `collect_coin_creator_fee` : traiter d'abord les 12 sites `Location`
  (R1), puis les 2 diffs `mem` (`ldxdw [r7+752]` vs `[r8+32]`, `ldxb`) qui sont un
  **déréférencement de compte** (borrow) — forme `&UncheckedAccount`/`as_ref()`.
- **447496 / 449312** volume accumulator : ordre des méthodes et `try_into` ;
  l'oracle a ces corps dans `state/volume_accumulator.rs` (lignes ~137/271/285/300/
  334/339) ; les gros écarts sont des frontières d'inlining. Découper les helpers
  comme l'oracle, `#[inline(never)]`.
- **8840 / 50640 / 64264 / 455624** : fonctions de bibliothèque (`Error::from`,
  Borsh serialize, slice concat, ToString). Elles ne se règlent pas par source
  métier : elles suivent la version de `core`/`alloc`/`borsh` et le profil de
  build. **Ne pas** les prendre avant la fin ; si le compte le permet, aligner la
  version de `borsh`/`rustc` sur l'oracle (même toolchain v1.44) et mesurer.
- **993464 / 995800** : dépendance `native-transfer-fee` ; porter le crate oracle
  (pas de réécriture) et vérifier l'ordre TLV.

---

## 6. T3 — layout `GlobalConfig` (mesuré, à corriger)

**Ce n'est pas un « +1/+8 de padding » : c'est un ordre de champs en mémoire
différent de la déclaration oracle.** Mesures directes sur le déployé [M] :

| fenêtre | méthode | store déployé | offset **mémoire** |
|---:|---|---|---:|
| 398896 | `set_lp_fee_basis_points` | `stxdw [r2+0x380]` | **896** |
| 399512 | `set_protocol_fee_basis_points` | `stxdw [r2+0x388]` | **904** |
| 400128 | `set_coin_creator_fee_basis_points` | `stxdw [r2+0x390]` | **912** |
| 111888 | `toggle_cashback_enabled` | `ldxb/stxb [r1+0x3b2]` | **946** |

Les trois `u64` de frais sont donc **contigus à la fin** de la structure en mémoire
(896/904/912), et le bool cashback est à 946 — alors que la déclaration oracle
(`state.rs:19-38`) place ces champs tôt (32/40/305/634). En revanche les offsets
**sérialisés** (`docs/account_layouts.md` §2.1 : lp 40, protocol 48, coin_creator
313, recipients 57, mayhem 417, cashback 642, buyback 643, buyback_bps 899,
boost 907/939/940/941, total 949) sont ceux du **wire**.

Conclusion : le `GlobalConfig` d'origine a un **layout mémoire différent du layout
wire**. C'est cohérent avec le fait que l'oracle implémente déjà
`AccountDeserialize` **à la main** (`state.rs:49-145`, `read_global_config_*`) ;
mais il laisse `try_serialize` appeler `self.serialize(writer)` (dérive = ordre de
déclaration), donc son ordre mémoire == ordre wire. Le déployé, lui, ne peut pas
être dans ce cas.

Reconstruction à appliquer :
1. **Déclarer** `GlobalConfig` dans l'ordre **mémoire** déployé. Les trois `u64`
   `lp_fee_basis_points`, `protocol_fee_basis_points`,
   `coin_creator_fee_basis_points` vont **à la fin** (positions 896/904/912), suivis
   des champs nécessaires pour que `is_cashback_enabled` tombe à 946. Sonder les
   autres champs avec `sbftool field <deployed.so> <callsite> <base> <off>` /
   les fenêtres setters déjà appariées (set_protocol_fee_recipients, validate_*)
   pour fixer l'ordre complet ; ne pas deviner.
2. **Garder le wire exact** en écrivant `AnchorSerialize` **à la main** (remplacer
   `self.serialize(writer)` par une écriture champ-par-champ dans l'ordre wire
   40/48/313/…/941). `AccountDeserialize` manuel existant reste la référence.
   Ne pas utiliser `#[derive(AnchorSerialize)]` si l'ordre de déclaration change.
3. Vérifier que le total mémoire reste compatible avec les copies
   (`realloc`/`extend_global_config` 949) et que les offsets wire 313/899/941
   sont inchangés.
4. Mesurer : 398896 (déjà matched) doit rester matched ; 399512/400128/111888/113408
   doivent passer sans perdre les setters/validators déjà appariés.

> Piège : si l'on se contente d'ajouter un champ, on décale aussi les offsets wire
> et on casse `set_protocol_fee_recipients`/`validate_*`. C'est bien l'**ordre de
> déclaration + sérialisation manuelle** qu'il faut changer, pas un padding.

---

## 7. T4 — gros corps : ordre d'attaque et formes

Ces fenêtres ne se règlent pas par une ligne. Pour chacune, la source oracle
**existe** (MIT) et est le point de départ ; le résidu est une frontière
d'inlining / un ordre de blocs / une révision. Protocole : porter le corps oracle,
mesurer `ndiff`, puis n'éditer que la forme (helpers, inline, ordre) — jamais la
sémantique sans preuve binaire.

Ordre recommandé (du plus rentable au plus dur) :

1. **90408 `admin_update_token_incentives`** (95) — paquet oracle
   `repro/pump_amm/incentives-thirty-one` ; corps + ordre des 8 gardes.
2. **370032 `claim_token_incentives`** (197) — même paquet ; formule
   `reward = sol_volume * supply[prev] / sol_volumes[prev]`.
3. **374200 `claim_cashback`** (98) — paquet `cashback-thirty-two` /
   `cashback-exit-order-20261027`.
4. **378256/384032** close/sync volume accumulator (54/69) — helpers + ordre.
5. **329112/331520** `calculate_buy_result` / `estimate_buy_quote` (57/74) —
   réordonner les appels (`calculate_*` → event) et les `checked_*`.
6. **147008 `migrate_pool_coin_creator`** (66) — ordre comptes/CPI.
7. **126864 `boost::execute`** (110) — paquet `boost-*` ; `&UncheckedAccount`.
8. **159144/167376 transfer_creator** (495/559) et **151512 set_coin_creator**
   (292) — paquets `creator-*` ; corps + CPI.
9. **178784 `create_pool::execute`** (500) — paquet `create-eighteen` /
   `create-pool-fields-recovery-20261028` (V2 mint clone, cf. README oracle).
10. **226992/239008 buy / buy_exact_quote_in** (535/646) et **301904 sell** (614),
    **313168 legacy_sell::cashback** (714) — paquets `legacy-*-thirty-*` ;
    séparer les monomorphisations (`execute::<false>` vs `::<true>`), ne pas
    partager de helper.
11. **217512 `distribute_cashback`** (543) — helper boundary.
12. **252864/264712/284992 multi_hop** (963/1579/1926) — paquets
    `multi-hop-thirty-seven` ; le plus dur. Attaquer après tout le reste.
13. **78936/82056 select_and_apply[_v2]** (155/94) — CPI `pump_fees` ; l'oracle
    a la forme, le résidu est l'inlining dans `create_pool`. Essayer
    `#[inline(never)]` sur `select_and_apply` et `select_and_apply_v2`.
14. **84256 `admin_cto_pool`** (182) — **attention** : révision différente du
    source (cf. `docs/MASTER_GAPS.md`, Track 2). Les codes 6080/6088/6092/6095 et
    l'ordre des gardes du déployé ne sont pas ceux de l'oracle. Spec : partir du
    désassemblage `sbftool func 0x14920/8` et reproduire les gardes **dans l'ordre
    déployé** ; ne pas « nettoyer ».
15. **102712 `set_reserved_fee_recipients`** (682) — boucle 8 comptes,
    `format!("reserved_fee_recipients[{}]", i)`, `with_account_name`, ordre
    rent/executable ; paquet `admin-ten`/`admin-twelve`.

Pour chaque : `(a)` fenêtre ci-dessus ; `(b)` l'oracle a le corps mais la frontière
d'inlining/l'ordre diffère (n mesuré) ; `(c)` porter le corps oracle puis appliquer
la forme (`#[inline(never)]`, helper séparé, ordre des `if`, `let` nommés) ; `(d)`
`handler-form`.

---

## 8. Ordre d'exécution et acceptance

1. **T0** (17) — ports exacts ; mesurer après chaque groupe (5 groupes).
2. **T1 par fichier** — commencer par `constant_product.rs`, `fees.rs`,
   `global_config.rs`, `pool.rs`, `transfer_fee.rs` (une passe = plusieurs fenêtres).
   Mesurer après **chaque fichier** ; ne garder que si `matched` monte et `raw` ne
   perd rien.
3. **T3** avec T1 sur `global_config` (offsets) — vérifier les setters déjà matched.
4. **T2** petits (335112, 116880, 281264, 142984).
5. **T4** dans l'ordre du §7.

Règles d'acceptation (reprises de `OPEN_TASKS.md`) :
- `matched` avant/après + `raw` avant/après, sur le profil g3 (même toolchain,
  mêmes remaps). Aucune régression sur `matched_set` **ni** `raw_set`.
- Le comportement doit correspondre au **déployé** : citer l'adresse + le code
  d'erreur. Ne jamais ajouter/retirer un check sans preuve (sauf le cas déjà
  documenté `multi_hop 307`, qui ne peut pas fire).
- Pas de macro qui hardcode file/line ; pas de `.so` déployé en input ; pas de
  patch de binaire.
- Un paquet `research/<task>/` par PR avec le JSON de mesure et le patch source.

### Commandes utiles

```sh
# désassembler une fenêtre (pc = vaddr/8 ; vaddr = adresse de la table §2)
python tools/sbftool.py func <deployed.so> $((0x32750/8))
# Localiser un site : le lddw de la Location est un reloc type 8
#   -> record 24 B {u32 0, u32 file_ptr, u64 len, u32 line, u32 col}
#   (même lecture que tools/measure.py:location()).
# mesure officielle (profil du paquet)
EXTRA="$(cat r34_r2.remap)" ./build.sh <tag> <tree>   # -> tools/measure.py
```

---

## 9. Annexes — données par fenêtre

### 9.1 Cartographie fichier → fenêtres (T1)

- `curve/constant_product.rs` : 72136, 73328, 74656
- `curve/fees.rs` : 76552, 81200
- `instructions/boost.rs` : 126168
- `instructions/swap/buy.rs` : 225616
- `instructions/swap/sell.rs` : 322192
- `instructions/swap/trade_v2.rs` : 323512, 324056, 327448, 330920, 333536,
  335984, 359968, 189024, 262400, 142464, 717744
- `instructions/swap/multi_hop_swap.rs` : 252112, 262920, 283360, 758472
- `instructions/swap/mod.rs` : 364040
- `instructions/sweep_fees.rs` : 365576
- `instructions/liquidity/deposit.rs` : 195384
- `instructions/liquidity/withdraw.rs` : 206672
- `instructions/admin/toggle_{cashback_enabled,boost,mayhem_mode}.rs` : 111888,
  112576, 113408
- `state/global_config.rs` : 398896, 399512, 400128, 400744, 403080, 404544,
  405096, 407416
- `state/pool.rs` : 443176, 444264
- `state/volume_accumulator.rs` : 869600, 872336
- `utils/transfer_fee.rs` : 475432, 476744, 478080

### 9.2 Codes d'erreur observés dans les fenêtres T1 (à conserver)

`6003` (index 3), `6023` (Overflow, index 23), `6043` (MayhemModeInDesiredState),
`6044` (NotEnoughRemainingAccounts), `6051` (CashbackNotInDesiredState),
`6005` (InvalidAdmin). La valeur immédiate dans `stw [r10-120], N` est
`6000+index` ; toute modification doit garder l'index.

### 9.3 Ce qui n'est **pas** dans ce document

- Aucun essai de reorder de symboles / `ordered.ld` : mesuré mort pour le raw
  (`WHOLE_ELF_FRONTIER.md`).
- Aucun flag de compilateur : `codegen-units`, `mergefunc`, `share-generics` sont
  mesurés sans effet/négatifs.
- Aucune prétention de byte-identité whole-ELF : ce sont des specs de fenêtres.

---

*Analyse : lecture du binaire déployé + source MIT de lalalune. Toute forme
reprise de leur source est créditée lalalune/pumpfun-source (MIT), y compris les
paquets `repro/pump_amm/*` cités. Aucun build, aucun patch, aucun PR de code.*
