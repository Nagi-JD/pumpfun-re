# Chantier Pump — specs de reconstruction des 207 fenêtres restantes (828 → 1035)

> **Nature.** Spécs d'analyse, aucun build, aucun patch binaire. Le `.so` déployé
> n'est jamais une entrée de build. Crédit oracle : **lalalune/pumpfun-source (MIT)**,
> `main` @ `6e6ac0fec28d186e76af23e0be4cb10af137e6f0`.

> **Cible.** `pump` = `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P`, `.so` sha256
> `7a19affaa2c6187e04a5fe0ea298cee81fa5eb8c24cfcc30d85f615e89f7b02d`,
> `.text` @ `0x120`, taille `0x1b58d0`, **1035 fenêtres**.

> **Profil mesuré.** Pump **828 / 1035 (161 raw)** (`research/chantier-T3-pump-quote-path`,
> candidate `2ec5872d…`). Les **207** fenêtres ci-dessous sont `828` → `1035`.

> **Correction importante sur l'oracle.** Au commit `6e6ac0fe` (round47 publié),
> lalalune est à **823 / 1035 (203 raw)** — pas 989. Son candidat est
> `0204c444fd17534f71b9f85424a1af2ef2550453630e3dad1578db008e1cf5f9`
> (`unstripped` `33717fcb…`). Conséquence mesurée : **67 des 207** fenêtres sont
> couvertes par leur source (ports exacts, T0) ; les **140** autres sont du résidu
> **partagé** (lalalune ne les a pas non plus). Si un checkpoint 989 existe sur une
> autre branche, fournir son sha : la worklist ci-dessous reste la liste mesurée
> contre le `main` public, et les 140 fenêtres partagées devront être traitées
> par forme source, pas par simple copie.

---

## 0. Méthode (reproductible)

1. **Fenêtres** : `window_map.windows()` sur le `.so` déployé → 1035 fenêtres
   (`address` = vaddr, `bytes`). `sbftool` indexe en `pc = vaddr / 8` ;
   `.text` commence à `0x120` (divisible par 8) → **`func <pump.so> $((addr/8))`**.
2. **Ensemble des 207** : reconstruit depuis `research/pump-r34-bodies-verified/measure/s7p-m.json`
   (profil 786, 249 non appariées), moins les **42** fenêtres gagnées et documentées
   par les paquets `chantier-T4-*` / `chantier-T3-*` / `chantier-T5-*` (chaque
   `measure.json` donne `gained_matched`). 249 − 42 = **207**, et 786 + 42 = **828**.
   Contrôle : `chantier-T3-pump-quote-path/measure.json` donne `after.matched=828`,
   `after.unmatched=207`.
   [M] ; si un build 828 exact diffère d'une fenêtre, le build/measure tranche.
3. **Noms** : (i) paires exactes `window_map` déployé ↔ candidat symbolé lalalune
   (`round47/unstripped.so`) → **67 ports** ; (ii) sinon
   `repro/pump/main-contract-round47-20261027/remaining-body-and-data-triage.json`
   (365 near-pairs, 212 résiduelles oracle, `candidate_symbol` + slots) ; (iii) sinon
   meilleure containment + `pump_handler_anatomy.json` + `Location` (fichier/ligne)
   pour les gros corps. Les noms T2/T4 sont marqués **[H]** quand ils viennent de
   la seule containment.
4. **Résidu réel** : on compare les instructions en masquant uniquement ce que la
   métrique masque (`call`, `lddw` relogés) ; on garde `off` et `imm` des `ld/st`.
   Classes : `line` (même slot, imm = ligne/colonne), `code` (imm ≥ 6000),
   `frame` (slot `r10` différent), `mem` (offset de champ), `call/import`.
5. **Ligne déployée** = immédiat du `stw/stdw [r10-…], N` : c'est la **ligne source
   d'origine**. La recette T1 est donc « amener le `error!/require!` à cette ligne »,
   comme `docs/WRAPPER_RECONSTRUCTION.md` et les paquets AMM `d1`/`d2`.

### Ce que le score compte

La signature d'une fenêtre garde : opcode, registres, `off` (donc les slots de
frame), `imm` (donc les lignes `Location`, les codes d'erreur, les constantes),
et les **imports** (`call` type 10). Sont masqués : cibles de `call` internes,
`lddw` relogés. D'où : (a) re-ligner la source est le levier n°1 ; (b) un
changement de slot de frame est visible ; (c) un changement d'import (`abort`,
`sol_log_`) est visible ; (d) les gros corps ne se règlent pas par une ligne.

---

## 1. Cinq causes racines

| # | Cause | Fenêtres | Levier |
|---|---|---:|---|
| **R1** | lignes `Location` déployées ≠ source compacte oracle | 17 T1 + une partie de T2/T4 | re-ligner le fichier (blank-lines dans les closures/entre items) |
| **R2** | slots de frame / lifetime / owned-vs-borrowed `AccountInfo` | ~10 | bindings nommés, tuples, `&UncheckedAccount`, owned `AccountInfo` |
| **R3** | layout de champs (`mem`) | 3 mesurés + gros corps | corriger les offsets/déclarations (`needs-layout`) |
| **R4** | modules absents (clients CPI `declare_program!`, distribution, quote payments) | ~35 | porter le module oracle (source MIT) |
| **R5** | gros corps (executors buy/sell/create/admin, distribution) | 56 | porter le corps oracle puis frontières d'inlining/ordre |

---

## 2. Répartition et classes

| Tier | Fenêtres | Classe (d) | Gain attendu |
|---|---:|---|---|
| **T0** | 67 | `port-exact` | +67 (source oracle déjà signature-égale) |
| **T1** | 17 | `re-ligne Location` | +17 facile (une passe par fichier) |
| **T2** | 67 | `frame-lifetime` / `needs-layout` / `error-form` / `handler-form` | +30–45 |
| **T4** | 56 | `gros handler-form` | le reste (port corps + forme) |
| **Total** | **207** | | **828 → 1035** |

Ordre d'attaque : **T0** (groupes A→F), puis **T1** fichier par fichier, puis
**T2** petits, puis **T4** par famille.

---

## 3. T0 — 67 ports exacts (l'oracle matche, pas nous)

Ces fenêtres sont **signature-égales** dans le candidat round47 de lalalune
(`window_map` pair unique, `diff` instruction = 0). La reconstruction est un
**port de source** : mêmes modules/structs/macros, mêmes chemins de fichiers et
mêmes lignes (leurs fenêtres sont appariées, donc leurs `Location` sont déjà
correctes). Mesurer après chaque groupe ; ne pas réécrire la logique.

### T0-A. clients CPI `declare_program!` (20)

| addr | octets | oracle (fn) | fichier oracle | action |
|---:|---:|---|---|---|
| 828968 | 1944 | `to_account_infos` | pump_fees client (declare_program!) | porter `declare_program!(pump_fees)` + IDL (forme générée) [M] |
| 1086600 | 3160 | `GlobalConfig::try_deserialize_unchecked` | pump_amm client (declare_program!) | porter `declare_program!(pump_amm)` + IDL (forme générée) [M] |
| 1089760 | 4056 | `admin_cto_pool` | pump_amm client (declare_program!) | porter `declare_program!(pump_amm)` + IDL (forme générée) [M] |
| 1093816 | 4096 | `collect_coin_creator_fee` | pump_amm client (declare_program!) | porter `declare_program!(pump_amm)` + IDL (forme générée) [M] |
| 1097912 | 5504 | `create_pool` | pump_amm client (declare_program!) | porter `declare_program!(pump_amm)` + IDL (forme générée) [M] |
| 1103416 | 4864 | `init_boost` | pump_amm client (declare_program!) | porter `declare_program!(pump_amm)` + IDL (forme générée) [M] |
| 1108280 | 4608 | `transfer_creator_fees_to_pump_v2` | pump_amm client (declare_program!) | porter `declare_program!(pump_amm)` + IDL (forme générée) [M] |
| 1112888 | 1472 | `to_account_metas` | pump_amm client (declare_program!) | porter `declare_program!(pump_amm)` + IDL (forme générée) [M] |
| 1114360 | 3144 | `to_account_infos` | pump_fees client (declare_program!) | porter `declare_program!(pump_fees)` + IDL (forme générée) [M] |
| 1117504 | 1672 | `to_account_metas` | pump_amm client (declare_program!) | porter `declare_program!(pump_amm)` + IDL (forme générée) [M] |
| 1119176 | 3672 | `to_account_metas` | pump_amm client (declare_program!) | porter `declare_program!(pump_amm)` + IDL (forme générée) [M] |
| 1122848 | 4520 | `to_account_infos` | pump_fees client (declare_program!) | porter `declare_program!(pump_fees)` + IDL (forme générée) [M] |
| 1127368 | 2872 | `to_account_metas` | pump_amm client (declare_program!) | porter `declare_program!(pump_amm)` + IDL (forme générée) [M] |
| 1130240 | 3656 | `to_account_infos` | pump_amm (declare_program! generated client) | porter `declare_program!(pump_amm)` + IDL (forme générée) [M] |
| 1133896 | 2472 | `to_account_metas` | pump_amm client (declare_program!) | porter `declare_program!(pump_amm)` + IDL (forme générée) [M] |
| 1137112 | 1176 | `FeeConfig::try_deserialize_unchecked` | pump_fees client (declare_program!) | porter `declare_program!(pump_fees)` + IDL (forme générée) [M] |
| 1140504 | 4040 | `admin_cto_sharing_config` | pump_fees client (declare_program!) | porter `declare_program!(pump_fees)` + IDL (forme générée) [M] |
| 1144544 | 3200 | `get_fees_with_quote_mint` | pump_fees client (declare_program!) | porter `declare_program!(pump_fees)` + IDL (forme générée) [M] |
| 1147744 | 1472 | `to_account_metas` | pump_fees client (declare_program!) | porter `declare_program!(pump_fees)` + IDL (forme générée) [M] |
| 1154128 | 2216 | `to_account_infos` | pump_amm (declare_program! generated client) | porter `declare_program!(pump_amm)` + IDL (forme générée) [M] |

### T0-B. distribution / holder_distribution (4)

| addr | octets | oracle (fn) | fichier oracle | action |
|---:|---:|---|---|---|
| 571760 | 608 | `sharing_config_shareholders` | distribution.rs | porter `distribution.rs` — forme signature-égale [M] |
| 784384 | 9560 | `try_accounts` | distribution.rs | porter `distribution.rs` — forme signature-égale [M] |
| 793944 | 7256 | `try_accounts` | distribution.rs | porter `distribution.rs` — forme signature-égale [M] |
| 808528 | 7344 | `try_accounts` | holder_distribution.rs | porter `holder_distribution.rs` — forme signature-égale [M] |

### T0-C. migration (9)

| addr | octets | oracle (fn) | fichier oracle | action |
|---:|---:|---|---|---|
| 278176 | 8448 | `create_pool` | migrate.rs | porter `migrate.rs` — forme signature-égale [M] |
| 294144 | 296 | `pool_authority_mint_token_account` | migrate.rs | porter `migrate.rs` — forme signature-égale [M] |
| 294440 | 768 | `base_token_program` | migrate.rs | porter `migrate.rs` — forme signature-égale [M] |
| 328432 | 8704 | `create_pool` | migrate_v2.rs | porter `migrate_v2.rs` — forme signature-égale [M] |
| 337136 | 368 | `boost_enabled` | migration_native_payments.rs | porter `migration_native_payments.rs` — forme signature-égale [M] |
| 347280 | 296 | `pool_authority_mint_token_account` | migrate_v2.rs | porter `migrate_v2.rs` — forme signature-égale [M] |
| 347952 | 1792 | `close_pool_authority_account` | migrate_v2.rs | porter `migrate_v2.rs` — forme signature-égale [M] |
| 875248 | 23608 | `try_accounts` | migrate_v2.rs | porter `migrate_v2.rs` — forme signature-égale [M] |
| 1556720 | 744 | `required_quote_account_len` | migrate_v2.rs | porter `migrate_v2.rs` — forme signature-égale [M] |

### T0-D. paiements quote/token (14)

| addr | octets | oracle (fn) | fichier oracle | action |
|---:|---:|---|---|---|
| 243096 | 416 | `ensure_rent_exempt` | legacy_native_payments.rs | porter `legacy_native_payments.rs` — forme signature-égale [M] |
| 243512 | 416 | `ensure_rent_exempt` | legacy_native_payments.rs | porter `legacy_native_payments.rs` — forme signature-égale [M] |
| 574168 | 1176 | `transfer_native_unchecked` | curve_quote_payments.rs | porter `curve_quote_payments.rs` — forme signature-égale [M] |
| 576600 | 1200 | `transfer` | legacy_native_payments.rs | porter `legacy_native_payments.rs` — forme signature-égale [M] |
| 579016 | 1232 | `transfer_native` | curve_quote_payments.rs | porter `curve_quote_payments.rs` — forme signature-égale [M] |
| 583944 | 1176 | `transfer_native_curve_unchecked` | lib.rs | porter `lib.rs` — forme signature-égale [M] |
| 591416 | 2088 | `transfer_tokens` | creator/collect_creator_fee.rs | porter `creator/collect_creator_fee.rs` — forme signature-égale [M] |
| 593504 | 2096 | `transfer_user_tokens_ref` | creator/collect_creator_fee.rs | porter `creator/collect_creator_fee.rs` — forme signature-égale [M] |
| 595600 | 2144 | `transfer_curve_tokens_ref` | v2_token_transfers.rs | porter `v2_token_transfers.rs` — forme signature-égale [M] |
| 600096 | 2096 | `transfer_user_quote_tokens` | creator/collect_creator_fee.rs | porter `creator/collect_creator_fee.rs` — forme signature-égale [M] |
| 604312 | 2088 | `transfer_vault_tokens` | creator/collect_creator_fee.rs | porter `creator/collect_creator_fee.rs` — forme signature-égale [M] |
| 614200 | 840 | `move_native` | curve_quote_payments.rs | porter `curve_quote_payments.rs` — forme signature-égale [M] |
| 615040 | 824 | `move_native` | curve_quote_payments.rs | porter `curve_quote_payments.rs` — forme signature-égale [M] |
| 618744 | 1160 | `transfer_to_owned` | lib.rs | porter `lib.rs` — forme signature-égale [M] |

### T0-E. entrées `#[program]` (7)

| addr | octets | oracle (fn) | fichier oracle | action |
|---:|---:|---|---|---|
| 1201576 | 1344 | `set_mayhem_virtual_params` | lib.rs | porter `lib.rs` — forme signature-égale [M] |
| 1221856 | 1768 | `buy` | lib.rs | porter `lib.rs` — forme signature-égale [M] |
| 1223624 | 1768 | `buy_exact_sol_in` | lib.rs | porter `lib.rs` — forme signature-égale [M] |
| 1227336 | 1072 | `migrate_v2` | lib.rs | porter `lib.rs` — forme signature-égale [M] |
| 1249576 | 1472 | `distribute_creator_fees` | lib.rs | porter `lib.rs` — forme signature-égale [M] |
| 1251048 | 1992 | `distribute_creator_fees_v2` | lib.rs | porter `lib.rs` — forme signature-égale [M] |
| 1277888 | 2912 | `set_mayhem_virtual_params` | lib.rs | porter `lib.rs` — forme signature-égale [M] |

### T0-F. helpers (13)

| addr | octets | oracle (fn) | fichier oracle | action |
|---:|---:|---|---|---|
| 832 | 1336 | `Error::with_values` | anchor_lang/error.rs | aligner la forme `Error::with_values` (une seule instanciation, §5.3) |
| 99688 | 272 | `control_account` | create_v2.rs | porter `create_v2.rs` — forme signature-égale [M] |
| 169240 | 472 | `token_frozen` | creator/admin_cto.rs | porter `creator/admin_cto.rs` — forme signature-égale [M] |
| 174312 | 2984 | `execute` | admin_set_idl_authority.rs | porter `admin_set_idl_authority.rs` — forme signature-égale [M] |
| 233408 | 6136 | `set` | creator/set_creator.rs | porter `creator/set_creator.rs` — forme signature-égale [M] |
| 239544 | 3552 | `sync` | creator/set_metaplex_creator.rs | porter `creator/set_metaplex_creator.rs` — forme signature-égale [M] |
| 429016 | 3488 | `validate_new_mint` | quote_control/state.rs | porter `quote_control/state.rs` — forme signature-égale [M] |
| 476840 | 3168 | `execute` | incentives.rs | porter `incentives.rs` — forme signature-égale [M] |
| 657464 | 192 | `tokens_for_quote` | util/constant_product.rs | porter `util/constant_product.rs` — forme signature-égale [M] |
| 664560 | 1168 | `sync_virtual_quote_reserves` | mayhem_virtual_params.rs | porter `mayhem_virtual_params.rs` — forme signature-égale [M] |
| 849168 | 576 | `exit` | mayhem_virtual_params.rs | porter `mayhem_virtual_params.rs` — forme signature-égale [M] |
| 907008 | 3512 | `try_accounts` | multi_hop_curve_swap.rs | porter `multi_hop_curve_swap.rs` — forme signature-égale [M] |
| 1751480 | 56 | `type_id` |  | aligner le type `Any` (type_id) sur le jeu de types oracle |

**Détails des groupes :**

- **T0-A — clients CPI** : ce sont les `ToAccountMetas` / `ToAccountInfos` /
  `AccountDeserialize` / `try_deserialize_unchecked` générés par
  `declare_program!(pump_amm)` et `declare_program!(pump_fees)` (`lib.rs:70-71`).
  Porter les deux `declare_program!` **et les IDL** `idls/pump_amm.json` +
  `idls/pump_fees.json` (mêmes versions), puis les appels CPI exacts
  (`create_pool`, `init_boost`, `collect_coin_creator_fee`,
  `transfer_creator_fees_to_pump_v2`, `admin_cto_pool`, `admin_cto_sharing_config`,
  `get_fees_with_quote_mint`, `update_fee_shares`, `claim_social_fee_pda_v2`).
  Ne pas réécrire ces wrappers à la main : la forme générée (ordre des metas,
  flags 0x0100/0x0001, discriminators) est déterministe.
- **T0-B — distribution** : `distribution.rs` + `holder_distribution.rs`
  (`#[path="creator/distribute_fee_to_holders.rs"]`). Comptes, execute,
  `get_distribution_amounts`, `execute_native_distribution`, `execute_v2`.
- **T0-C — migration** : `migrate.rs` / `migrate_v2.rs` : `create_pool`,
  `pool_authority_mint_token_account`, `base_token_program`,
  `close_pool_authority_account`, `required_quote_account_len`, `boost_enabled`.
- **T0-D — paiements** : `curve_quote_payments.rs`, `legacy_native_payments.rs`,
  `v2_token_transfers.rs`, `collect_creator_fee.rs`, plus `lib.rs`
  `transfer_native_curve_unchecked`/`transfer_to_owned`. Ce sont les helpers
  `transfer_*`/`move_native` (CPI token/native, owned `AccountInfo`).
- **T0-E — entrées `#[program]`** : `buy`, `buy_exact_sol_in`, `migrate_v2`,
  `distribute_creator_fees[_v2]`, `set_mayhem_virtual_params`. Vérifier le
  `msg!("Instruction: …")` et l'ordre des arguments (la longueur de chaîne est
  un immédiat : si le candidat logue `Instruction: Buy`, séparer les `pub fn`).
- **T0-F — helpers** : `control_account`, `token_frozen`, `ensure_rent_exempt`,
  `tokens_for_quote`, `sync_virtual_quote_reserves`, `validate_new_mint`,
  `sharing_config_shareholders`, `try_accounts`/`exit` des structs `#[derive(Accounts)]`.
  Pour `try_accounts` : la forme est le struct `#[derive(Accounts)]` du module
  (`distribution.rs`, `holder_distribution.rs`, `migrate_v2.rs`,
  `multi_hop_curve_swap.rs`, `mayhem_virtual_params.rs`) — champ ORDER + TYPE +
  contraintes, cf. WRAPPER_RECONSTRUCTION (b).

---

## 4. T1 — 17 re-lignes `Location` (le plus rapide après T0)

Recette : pour chaque site, le binaire déployé stocke `Location { file, line, col }`.
La ligne déployée est mesurée (colonne « lala→déployé »). Déplacer le
`error!/require!` correspondant vers cette ligne **sans bouger les autres sites** :
blank-lines **dans** la closure, ou jonction d'expressions, comme `d1`/`d2`.
Ne jamais changer le code d'erreur ni ajouter/retirer un check.

| addr | octets | fonction | fichier | lala→déployé |
|---:|---:|---|---|---|
| 407352 | 520 | `closure` | buy_v2.rs | 99→222, 27→31 ; code 6025→6024 |
| 516272 | 992 | `validate_trade` | trade_v3.rs | 60→149, 61→150 |
| 524792 | 656 | `add3` | trade_v3.rs | 65→285 |
| 525448 | 576 | `sub3` | trade_v3.rs | 67→294 |
| 530504 | 600 | `add` | trade_v3.rs | 75→390 |
| 557232 | 2136 | `output` | util/constant_product.rs | 7→17, 6→13, 8→19 |
| 610528 | 640 | `post_fee_amount` | util/transfer_fee.rs | 15→56 |
| 623672 | 1720 | `validate_buyback_fee_recipient` | lib.rs | 553→1879, 554→1884 |
| 625392 | 5464 | `set_buyback_fee_recipients` | lib.rs | 560→1905, 559→1895 |
| 631184 | 2712 | `add_quote_mint` | lib.rs | 571→1971, 569→1955, 568→1950, 570→1960 |
| 633896 | 1312 | `remove_quote_mint` | lib.rs | 575→1986, 574→1975 |
| 655472 | 1224 | `buy_quote` | lib.rs | 583→2428, 584→2430 |
| 656696 | 768 | `sell_quote` | lib.rs | 592→2454 |
| 657656 | 760 | `buy_fee_market_cap` | lib.rs | 599→2481 |
| 658416 | 2032 | `apply_buy` | lib.rs | 605→2496, 606→2501, 607→2506, 608→2511 |
| 660448 | 2040 | `apply_sell` | lib.rs | 614→2525, 613→2520, 615→2530, 616→2535 |
| 662488 | 1456 | `accrue_fees` | lib.rs | 628→2550, 629→2554 |

### 4.1 `lib.rs` (12 fenêtres) — re-ligne globale

Le fichier original avait ~2600 lignes ; la source oracle est compacte (~700).
Les cibles simultanées (lala→déployé) :

- `623672` `validate_buyback_fee_recipient` : 553→1879, 554→1884
- `625392` `set_buyback_fee_recipients` : 560→1905, 559→1895
- `631184` `add_quote_mint` : 571→1971, 569→1955, 568→1950, 570→1960
- `633896` `remove_quote_mint` : 575→1986, 574→1975
- `655472` `buy_quote` : 583→2428, 584→2430
- `656696` `sell_quote` : 592→2454
- `657656` `buy_fee_market_cap` : 599→2481
- `658416` `apply_buy` : 605→2496, 606→2501, 607→2506, 608→2511
- `660448` `apply_sell` : 614→2525, 613→2520, 615→2530, 616→2535
- `662488` `accrue_fees` : 628→2550, 629→2554

Contrainte : une seule passe doit satisfaire **tous** ces sites **et** garder les
autres `Location` de `lib.rs` (y compris les entrées T0-E déjà appariées).
Insérer des lignes entre les items/fonctions jusqu'à ce que chaque site tombe sur
sa cible ; mesurer après chaque insertion. Les deltas entre sites ne sont pas
uniformes (ex. `sell_quote` 592→2454 puis `buy_fee_market_cap` 599→2481 : 7 lignes
séparent les sites oracle, 27 les déployés) — il faut donc ajouter des blocs
d'espacement **entre** les fonctions, pas un padding global.

### 4.2 `trade_v3.rs` (5 fenêtres)

- `add3` 65→285, `sub3` 67→294, `add` 75→390, `validate_trade` 60→149 / 61→150.
- Les sites sont les `error!(Overflow)` et les `require!(BondingCurveComplete /
  CashbackCoinNotSupported)`. Placer `validate_trade` en premier (2 sites), puis
  `add3`/`sub3`/`add` (chaque fonction doit tomber sur sa ligne).

### 4.3 `util/constant_product.rs` (1 fenêtre)

`output` : 6→13, 7→17, 8→19. Trois `error!` (Overflow, Overflow, DivisionByZero)
dans les 3 lignes de la fonction ; espacer pour que les 3 sites tombent à 13/17/19.

### 4.4 `util/transfer_fee.rs` (1) et `buy_v2.rs` (1)

- `post_fee_amount` 15→56 (`error!(Overflow)` du `checked_sub`).
- `407352` closure `buy_handler` : 99→222, 27→31 ; **code 6025→6024** (garder 6024,
  vérifier la variante : index 24).

---

## 5. T2 — 67 fenêtres frame/lifetime/layout/error-form

| addr | octets | fonction | fichier | n | classe | levier mesuré |
|---:|---:|---|---|---:|---|---|
| 617800 | 944 | `transfer_to_user` | curve_quote_payments.rs | 0 | error-form/wrapper | import `abort` manquant (branche panic/abort) |
| 619904 | 944 | `transfer_to_user` | curve_quote_payments.rs | 0 | error-form/wrapper | import `abort` manquant (branche panic/abort) |
| 1136368 | 744 | `QuoteControl::try_deserialize_unchecked` | quote_control/state.rs | 3 | handler-form | champ alu [0, 9]→[0, 12]; lignes 16→84,40→24 |
| 52816 | 56 | `log` | buy.rs | 4 | handler-form | forme du corps (séquence : 4 diffs branch/alu/mem) |
| 1085872 | 728 | `UserVolumeAccumulator::try_deserialize_unchecked` | token_incentives/volume_accumulator.rs | 4 | needs-layout | champ alu [0, 12]→[0, 21]; mem [931, 2]→[97, 2]; lignes 15→83,56→24 |
| 1608904 | 56 | `log` | buy.rs | 4 | handler-form | forme du corps (séquence : 4 diffs branch/alu/mem) |
| 1679776 | 56 | `log` | buy.rs | 4 | handler-form | forme du corps (séquence : 4 diffs branch/alu/mem) |
| 1740328 | 56 | `log` | buy.rs | 4 | handler-form | forme du corps (séquence : 4 diffs branch/alu/mem) |
| 537800 | 736 | `fee` | util/fee.rs | 16 | handler-form | forme du corps (séquence : 16 diffs branch/alu/mem) |
| 609832 | 696 | `calculate_fee` | v3_native_transfer_fee.rs | 16 | handler-form | forme du corps (séquence : 16 diffs branch/alu/mem) |
| 611168 | 688 | `calculate_fee` | v3_native_transfer_fee.rs | 18 | handler-form | forme du corps (séquence : 18 diffs branch/alu/mem) |
| 411128 | 656 | `market_cap` | fee_cpi.rs | 22 | handler-form | forme du corps (séquence : 22 diffs branch/alu/mem) |
| 410456 | 672 | `set_buyback_basis_points` | lib.rs | 26 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 106184 | 2640 | `ancestor` | create_v2.rs | 28 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 455656 | 752 | `post_fee_amount` | util/transfer_fee.rs | 31 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 95192 | 768 | `fee` | util/fee.rs | 32 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 395904 | 1120 | `accrue_fees` | lib.rs | 33 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 635952 | 624 | `try_deserialize_unchecked` | distribution.rs | 34 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 363504 | 872 | `__idl_set_buffer` | util/transfer_fee.rs | 43 | error-form/wrapper | import []→['sol_log_'] |
| 253304 | 2008 | `validate_fee_recipient` | fee_recipient.rs | 49 | frame-lifetime | slots -360→-352,-352→-360,-352→-360,-360→-80; champ branch [221, 0]→[193, 0]; branch [205, 0]→[177, 0]; branch [196, 0]→[168, 0];  |
| 564040 | 896 | `tier` | util/fee.rs | 50 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 635208 | 744 | `try_deserialize_unchecked` | distribution.rs | 51 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 407872 | 944 | `__idl_set_buffer` | util/transfer_fee.rs | 53 | error-form/wrapper | import []→['sol_log_'] |
| 398152 | 1184 | `buy_quote` | lib.rs | 54 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 108824 | 784 | `validate_trade` | trade_v3.rs | 60 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 249168 | 1280 | `prepare_bonding_curve` | trade_types.rs | 65 | needs-layout | champ branch [89, 2]→[89, 165]; alu [0, 2]→[88, 2]; branch [87, 165]→[8, 0] |
| 467664 | 1344 | `update_buyback_config` | set_reserved_fee_recipients.rs | 67 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 535288 | 1424 | `checked_ceil_div` | util/fee.rs | 71 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 507864 | 1864 | `update` | token_incentives/volume_accumulator.rs | 79 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 411784 | 2480 | `vault_amount` | pump_quote.rs | 80 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 1558608 | 664 | `required_quote_account_len` | migrate_v2.rs | 80 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 397024 | 1128 | `remove_quote_mint` | lib.rs | 89 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 504400 | 2904 | `execute` | volume_sync.rs | 92 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 572368 | 1800 | `make_trade_event` | trade_types.rs | 93 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 408816 | 1640 | `control_entry` | quote_control/state.rs | 96 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 434656 | 1736 | `control_entry` | quote_control/state.rs | 96 | frame-lifetime | slots -296→-328,-288→-320,0→-80,104→-208; champ branch [81, 0]→[53, 0]; branch [29, 0]→[63, 0]; alu [0, -328]→[0, -296]; lignes 12 |
| 417456 | 1048 | `try_from_unchecked` | admin_set_idl_authority.rs | 107 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 523752 | 1040 | `prepare_bonding_curve` | trade_types.rs | 112 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 228872 | 4536 | `execute` | admin_set_idl_authority.rs | 119 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 608520 | 1312 | `check_token` | buy_v2.rs | 119 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 212048 | 2312 | `execute_native_distribution` | creator/distribute_creator_fees.rs | 122 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 536712 | 1088 | `selected` | util/fee.rs | 122 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 454360 | 1296 | `check_token` | buy_v2.rs | 125 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 362088 | 1416 | `validate_buyback_fee_recipient` | lib.rs | 127 | error-form/wrapper | import ['abort']→[] |
| 538536 | 1112 | `transfer_to_user` | curve_quote_payments.rs | 129 | error-form/wrapper | import []→['abort'] |
| 1555528 | 1192 | `quote_extensions_supported` | create_v2.rs | 141 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 527864 | 2120 | `output` | util/constant_product.rs | 142 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 564936 | 1640 | `selected` | util/fee.rs | 144 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 295208 | 1512 | `close_pool_authority_account` | migrate_v2.rs | 147 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 531104 | 1672 | `remove_mint` | quote_control/state.rs | 148 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 532776 | 2512 | `apply_buy` | lib.rs | 154 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 177296 | 2696 | `collect` | creator/collect_creator_fee.rs | 158 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 602192 | 2120 | `transfer_curve_tokens_ref` | v2_token_transfers.rs | 160 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 606400 | 2120 | `transfer_curve_tokens_ref` | v2_token_transfers.rs | 161 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 140440 | 1400 | `make_trade_event` | trade_types.rs | 168 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 401776 | 2352 | `output` | util/constant_product.rs | 171 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 526024 | 1840 | `vault_amount` | pump_quote.rs | 171 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 399336 | 2440 | `output` | util/constant_product.rs | 173 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 250448 | 2856 | `fund_bonding_curve_rent` | trade_types.rs | 195 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 561752 | 2288 | `trade_fees` | fee_cpi.rs | 198 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 298512 | 2296 | `close_pool_authority_account` | migrate.rs | 200 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 97520 | 2168 | `ancestor` | create_v2.rs | 203 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 351536 | 2344 | `close_pool_authority_account` | migrate_v2.rs | 214 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 585120 | 2088 | `transfer_vault_tokens` | creator/collect_creator_fee.rs | 220 | frame-lifetime | slots 0→-312,-312→-344,16→-304,-4064→-368; champ mem [8, 0]→[8, 0]; mem [0, 0]→[0, 0]; alu [0, 1]→[0, 1] |
| 360000 | 2088 | `ancestor` | create_v2.rs | 223 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 201208 | 4920 | `get_distribution_amounts` | creator/distribute_creator_fees.rs | 230 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |
| 320008 | 2336 | `transfer_curve_tokens_ref` | v2_token_transfers.rs | 231 | handler-form | forme du corps (séquence : 24 diffs branch/alu/mem) |

### 5.1 `needs-layout` (champs / offsets) — mesuré

- **1085872** `UserVolumeAccumulator::try_deserialize_unchecked` : `stb [r6+931]`
  vs `[r6+97]` → le **layout mémoire** du compte diffère (comme le
  `GlobalConfig` AMM : ordre mémoire ≠ ordre wire). Reproduire la déclaration
  oracle (champs à +931) tout en gardant le `try_deserialize` manuel ; mesurer
  les autres champs avec `field`.
- **249168** `trade_types::prepare_bonding_curve` : 7 offsets de champs (`mem`)
  → vérifier l'ordre des champs `BondingCurve`/`Global` et des comptes ; les
  65 diffs incluent aussi les `Location` (traiter lignes d'abord).
- **585120** `transfer_vault_tokens` : 7 frames + 11 champs ; traiter les
  `Location` (16→35) puis les slots/offsets ; forme `&AccountInfo`/owned.
- **253304**, **434656** : 10/19 frames, 0 offset de champ → `frame-lifetime`
  (voir §5.2), pas layout.

### 5.2 `frame-lifetime`

Rappel (WRAPPER_RECONSTRUCTION b.7) : slots = bindings nommés + tuples +
`let` de slices ; `&AccountInfo` en paramètre = `noalias` → reload manquant ;
`&UncheckedAccount` (ou `let x: &AccountInfo = x.as_ref();`) force le reload.
Ordre des blocs = ordre IR : `if/else` ≠ `match` ≠ `&&`.

- **434656** `QuoteControl::control_entry` : 19 frames (offsets -296/-288/-80/-208),
  ligne 124→145. Reconstruire les bindings nommés de la boucle et l'ordre des
  branches ; traiter la ligne d'abord.
- **253304**, **585120**, **1085872**, **1136368** : même méthode.

### 5.3 `error-form/wrapper` (imports `abort`/`sol_log_`)

- **617800**, **619904** `transfer_to_user` : le déployé importe `abort`, le
  candidat non (n=0 par ailleurs). C'est une branche froide de panic
  (`panic=abort`) : reproduire la forme `expect/unwrap`/`assert` oracle qui
  engendre l'`abort`, ou la branche `abort` manquante. Mesurer l'import.
- **363504**, **407872** `__idl_set_buffer` : import `sol_log_` en trop chez le
  candidat (ou l'inverse) ; retirer/ajouter le `msg!` exact du chemin IDL.
- **362088**, **538536** : import `abort` opposé → même recette.
- **52816 / 1608904 / 1679776 / 1740328** : `anchor_lang::error::Error::log`
  56 B. Ce sont des instantiations ; le déployé en a une/plusieurs, le candidat
  une autre. Aligner la forme des sites `error!` (une seule instanciation,
  `with_values` inclus) plutôt que de « porter » un stub.
- **832** `Error::with_values` : monomorphisation (racine `WHOLE_ELF_FRONTIER`).
  L'oracle la matche ; chez nous elle diverge. Restructurer les sites d'erreur
  pour n'émettre **qu'une** instanciation (même type de closure, même
  `with_values`) ; mesurer `matched` + `raw` (tension connue).

### 5.4 `handler-form` moyens (n = 3…231)

Ils se traitent par la forme, pas par une ligne. Familles et leviers :

- `trade_v3.rs` / `validate_trade` : ordre des `require!` et des `if`.
- `util/fee.rs` (`fee`, `tier`, `selected`, `checked_ceil_div`) : ordre des
  branches + `checked_*` ; aligner les `Location` puis les slots.
- `v3_native_transfer_fee.rs` (`calculate_fee`) : décodage TLV ; porter la
  dépendance/forme oracle (cf. T0-A pour les extensions).
- `fee_cpi.rs` (`market_cap`, `trade_fees`) : CPI + ordre ; `&UncheckedAccount`.
- `create_v2.rs` (`ancestor`, `quote_extensions_supported`, `vault_amount`) :
  walk récursif ; l'oracle a `pump_quote.rs` et `ancestor` — porter la forme,
  puis la frontière d'inlining.
- `trade_types.rs` (`prepare_bonding_curve`, `make_trade_event`,
  `fund_bonding_curve_rent`) : gros helpers ; port corps + ordre.
- `volume_sync.rs`, `token_incentives/volume_accumulator.rs` : corps +
  `try_into`/`checked_*`, slots.
- `quote_control/state.rs` (`control_entry`, `remove_mint`) : frames + lignes.
- `admin_set_idl_authority::execute` : gros corps ; ne pas se fier au nom
  fuzzy si `Location` pointe un autre fichier (voir T4).

---

## 6. T4 — 56 gros corps

| addr | octets | fonction (hypothèse) | fichier | n |
|---:|---:|---|---|---:|
| 90320 | 2792 | `ancestor` | create_v2.rs | 254 |
| 170160 | 4152 | `execute_legacy` | creator/collect_creator_fee.rs | 256 |
| 404128 | 2704 | `ancestor` | create_v2.rs | 268 |
| 271896 | 2632 | `transfer_quote_tokens` | v2_quote_token_transfers.rs | 270 |
| 1398760 | 5704 | `execute` | admin_set_idl_authority.rs | 270 |
| 517264 | 2944 | `ancestor` | create_v2.rs | 276 |
| 414264 | 3192 | `add_quote_mint` | lib.rs | 295 |
| 121736 | 3128 | `execute_legacy` | creator/collect_creator_fee.rs | 331 |
| 274528 | 3648 | `native_buyback` | multi_hop_curve_swap.rs | 346 |
| 179992 | 6664 | `get_token_distribution_amounts` | creator/distribute_creator_fee_v2.rs | 368 |
| 539648 | 3440 | `execute` | admin_set_idl_authority.rs | 377 |
| 436392 | 6328 | `add_quote_control_mint` | quote_control/update_quote_control_mints.rs | 388 |
| 485928 | 3864 | `claim` | token_incentives/claim_token_incentives.rs | 388 |
| 1342368 | 3672 | `execute` | admin_set_idl_authority.rs | 388 |
| 520208 | 3544 | `native_buyback` | multi_hop_curve_swap.rs | 416 |
| 206912 | 5136 | `execute` | admin_set_idl_authority.rs | 427 |
| 364376 | 4872 | `native_buyback` | multi_hop_curve_swap.rs | 490 |
| 267456 | 4440 | `claim` | token_incentives/claim_token_incentives.rs | 495 |
| 243928 | 5240 | `execute` | admin_set_idl_authority.rs | 500 |
| 840664 | 8504 | `try_accounts` | mayhem_virtual_params.rs | 513 |
| 369248 | 4432 | `closure` | multi_hop_curve_swap.rs | 517 |
| 509728 | 6312 | `update_schedule` | token_incentives/volume_accumulator.rs | 520 |
| 84240 | 6080 | `admit_associated_token_account` | buy_v2.rs | 523 |
| 1271744 | 5624 | `execute` | admin_set_idl_authority.rs | 544 |
| 480008 | 5920 | `add_quote_control_mint` | quote_control/update_quote_control_mints.rs | 548 |
| 116864 | 4872 | `closure` | multi_hop_curve_swap.rs | 550 |
| 354264 | 5216 | `admit_associated_token_account` | buy_v2.rs | 555 |
| 1353896 | 6032 | `execute` | sweep_fees.rs | 596 |
| 255312 | 5664 | `execute` | set_reserved_fee_recipients.rs | 603 |
| 260976 | 5440 | `claim` | token_incentives/claim_token_incentives.rs | 620 |
| 99960 | 5704 | `execute` | admin_set_idl_authority.rs | 637 |
| 195168 | 6040 | `execute` | admin_set_idl_authority.rs | 659 |
| 469008 | 7832 | `execute` | sweep_fees.rs | 692 |
| 1386632 | 8488 | `sell` | lib.rs | 692 |
| 322344 | 6088 | `closure` | multi_hop_curve_swap.rs | 696 |
| 286624 | 7520 | `create_pool` | migrate.rs | 771 |
| 489792 | 8832 | `claim_v2` | token_incentives/claim_token_incentives.rs | 827 |
| 109608 | 7256 | `closure` | multi_hop_curve_swap.rs | 844 |
| 1346040 | 7856 | `sell` | trade_v3.rs | 856 |
| 458488 | 9176 | `execute` | set_reserved_fee_recipients.rs | 879 |
| 186656 | 8512 | `execute_v2` | creator/distribute_creator_fee_v2.rs | 892 |
| 445816 | 8544 | `execute_v2` | creator/distribute_creator_fee_v2.rs | 922 |
| 301192 | 8888 | `sell` | lib.rs | 929 |
| 547248 | 8944 | `create` | lib.rs | 936 |
| 311640 | 8368 | `create` | lib.rs | 951 |
| 1359928 | 10880 | `buy` | lib.rs | 961 |
| 1280800 | 11928 | `create` | lib.rs | 1123 |
| 337504 | 9776 | `create` | lib.rs | 1160 |
| 214360 | 14512 | `execute` | creator/distribute_fee_to_holders.rs | 1291 |
| 1373408 | 13224 | `buy_exact_sol_in` | lib.rs | 1293 |
| 1328392 | 13976 | `execute` | sell_v2.rs | 1489 |
| 124864 | 15576 | `execute` | create_v2.rs | 1580 |
| 1292728 | 15480 | `buy_handler` | buy_v2.rs | 1602 |
| 373680 | 18584 | `buy_exact_quote_in_handler` | buy_v2.rs | 1930 |
| 1308208 | 20184 | `buy_exact_quote_in_handler` | buy_v2.rs | 2242 |
| 141840 | 27400 | `execute` | creator/admin_cto.rs | 3088 |

Les noms T4 viennent de la containment et du `Location` quand il existe ; les
autres sont **[H]**. Attention mesurée : `243928` (`extend_account`), `99960`
(`create_v2`), `195168` (`distribute_creator_fee_v2`), `445816` (`sell.rs`),
`354264` (`multi_hop_curve_swap`) et `480008` (`volume_accumulator`) portent des
`Location` vers **un autre module** que leur fuzzy-name : vérifier le `Location`
avant de porter. `214360` est confirmé `holder_distribution::execute` [M].
Le vrai levier est de **porter le corps oracle** (leur source
existe, même si la fenêtre n'est pas appariée) puis de n'éditer que :
frontières de helpers (`#[inline(never)]`/`#[inline(always)]`), ordre des blocs,
owned vs borrowed `AccountInfo`, et les monomorphisations (`buy` vs
`buy_exact_sol_in`, `create` vs `create_v2`).

Familles (ordre conseillé) :

1. **`admin_set_idl_authority::execute`** — `1398760` **[M]** (`Location`
   `admin_set_idl_authority.rs:86/96/101`). Les fenêtres `539648`, `206912`,
   `1342368`, `1271744` sont fuzzy-`execute` **[H]** : vérifier leur `Location`
   avant de les rattacher à ce fichier.
2. **buy_v2** : `buy_handler` (`1292728`, `373680`, `1308208`) ;
   `admit_associated_token_account` (`84240`) ; `check_token` /
   `v2_token_transfers`. `354264` porte un `Location` `multi_hop_curve_swap.rs`
   → le rattacher à multi-hop, pas à buy_v2.
3. **sell_v2** : `execute` (`1328392`). `445816` porte un `Location` `sell.rs`
   → `legacy_sell::execute`, pas `execute_v2`.
4. **create_v2** : `execute` (`124864`), `ancestor` (`90320`, `404128`,
   `517264`, `97520`, `360000`), `pump_quote` (`411784`, `526024`).
5. **create** : `create` (`547248`, `311640`, `1280800`, `337504`).
6. **buy legacy** : `buy` (`1359928`), `buy_exact_sol_in` (`1373408`).
7. **admin_cto** : `execute` (`141840`, 27400 B, le plus gros).
8. **distribution / holder_distribution** : `execute_v2` (`186656`),
   `get_token_distribution_amounts` (`179992`), `get_distribution_amounts`
   (`201208`), `native_buyback` (`274528`, `520208`, `364376`) ;
   `214360` **[M]** `creator/distribute_fee_to_holders.rs` ;
   `195168` **[M]** `creator/distribute_creator_fee_v2.rs`.
9. **claim_token_incentives** : `claim` (`485928`, `267456`, `260976`),
   `claim_v2` (`489792`), `update_schedule` (`509728` **[M]**
   `token_incentives/volume_accumulator.rs`).
10. **quote_control** : `add_quote_control_mint` (`436392`). `480008` **[M]**
    porte un `Location` `volume_accumulator.rs` → `update_schedule`, pas
    quote_control.
11. **sweep** : `sweep::execute` (`1353896`, `469008`).
12. **set_reserved_fee_recipients** : `execute` (`255312`, `458488`).
13. **extend_account** : `243928` **[M]** `Location` `extend_account.rs`.
14. **create_v2 / idl** : `99960` **[M]** `Location` `create_v2.rs`.

Pour chacun : (a) la fenêtre/adresse ; (b) l'oracle a le corps mais pas la
frontière d'inlining/l'ordre (n mesuré) ; (c) porter le corps oracle, puis
appliquer `#[inline(never)]` sur les helpers, l'ordre des `if` et les bindings
nommés ; (d) `gros handler-form`. Mesurer `matched` + `raw` à chaque étape.

---

## 7. Ordre d'exécution et acceptance

1. **T0** : groupes A (clients CPI) → B (distribution) → C (migration) →
   D (paiements) → E (entrées) → F (helpers). Mesurer après chaque groupe.
2. **T1** : `trade_v3.rs`, `util/constant_product.rs`, `util/transfer_fee.rs`,
   `buy_v2.rs`, puis `lib.rs` (une passe globale). Mesurer après chaque fichier.
3. **T2** : `needs-layout` (347280, 1085872, 1147744) puis `frame-lifetime`
   (434656, 253304, 585120), puis les `error-form` (617800/619904).
4. **T4** : dans l'ordre du §6.

Règles (reprises de `OPEN_TASKS.md`) :
- `matched` + `raw` avant/après, même profil/toolchain/remaps ; aucune perte sur
  `matched_set` ni `raw_set`.
- Comportement = déployé : citer l'adresse + le code d'erreur ; ne pas
  ajouter/retirer un check sans preuve.
- Pas de macro hardcodant file/line ; pas de `.so` déployé en input ; pas de
  patch binaire.
- Un paquet `research/<task>/` par PR avec `measure.json` + patch source.

### Commandes

```sh
# désassembler une fenêtre (pc = vaddr/8)
python tools/sbftool.py func <pump.so> $((0x14910/8))
# mesure officielle du profil
EXTRA="$(cat r34_r2.remap)" ./build.sh <tag> <tree>   # -> tools/measure.py
```

---

## 8. Annexes

### 8.1 Sources oracle (MIT, commit `6e6ac0fe`)

`programs/pump/src/` : `lib.rs` (BondingCurve/entrypoints), `buy.rs`,
`buy_v2.rs`, `sell.rs`, `sell_v2.rs`, `create.rs`, `create_v2.rs`,
`pump_quote.rs`, `trade_v3.rs`, `trade_types.rs`, `migrate.rs`, `migrate_v2.rs`,
`migration_native_payments.rs`, `distribution.rs`,
`creator/distribute_fee_to_holders.rs`, `creator/distribute_creator_fee_v2.rs`,
`creator/collect_creator_fee.rs`, `curve_quote_payments.rs`,
`legacy_native_payments.rs`, `v2_token_transfers.rs`, `v2_quote_token_transfers.rs`,
`quote_control/*`, `token_incentives/*`, `util/*`, `extend_account.rs`,
`sweep_fees.rs`, `admin_set_idl_authority.rs`, `mayhem_virtual_params.rs`,
`volume_sync.rs`, `multi_hop_curve_swap.rs`, `idl_authority` +
`declare_program!(pump_amm/pump_fees)` et leurs IDL.

### 8.2 Codes d'erreur vus dans les fenêtres

`6024` = Overflow (T1 407352 : garder 6024) ; `6006`/`6018`/etc. selon
`PumpError` — toujours conserver l'index déployé (cf. `docs/error_catalogs.md`).

### 8.3 Limites

- Les 207 sont reconstruites (786 → 828) : une erreur d'une fenêtre est possible ;
  le build/measure officiel tranche.
- Les noms T2/T4 marqués [H] sont des hypothèses de containment ; `Location` et
  `pump_handler_anatomy.json` priment.
- Aucune prétention whole-ELF : ce sont des specs de fenêtres.

---

*Analyse lecture seule du binaire déployé + source MIT de lalalune. Toute forme
reprise de leur source est créditée lalalune/pumpfun-source (MIT), round47
`6e6ac0fe`, candidat `0204c444…`. Aucun build, aucun patch, aucun PR de code.*
