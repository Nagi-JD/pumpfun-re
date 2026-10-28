# Chantier DS residual — specs de fermeture des 30 fenêtres non appariées (pump + pump_amm)

> **Nature.** Analyse + specs, aucun build. Source : lalalune/pumpfun-source (MIT),
> `main` @ `6e6ac0fec28d186e76af23e0be4cb10af137e6f0`. Cibles déployées :
> `pump` `7a19affa…` (1035 fenêtres) et `pump_amm` `6a7ad345…` (785 fenêtres).

> **Résidu analysé** (l'oracle, pas nous) :
> - `research/claude-pump-integration-20261027/r37-layout-33` → pump **1010/1035**,
>   **25 non appariées** (candidate `b20fdec4…`, unstripped `9392550f…`).
> - `research/claude-amm-union7-20261028` → pump_amm **780/785**, **5 non appariées**
>   (candidate `605430b8…`, symbols `781859ca…`).
> Ce sont les 30 fenêtres que personne n'a fermées (l'oracle le note : « 25 of 1035 »,
> « 5 windows are unmatched », « Whole-ELF identity is still false »).

> **Méthode.** `window_map` sur le déployé, `sbftool func <so> $((addr/8))` pour désassembler,
> diff d'instructions en masquant `call`/`lddw` (on garde `off`+`imm`), puis classification :
> `Location-line` (imms de ligne/colonne), `forme de fonction` (frame/regalloc/ordre de
> contrôle/owned-vs-borrowed), `reorder` (ordre de blocs seul), `corps non reconstruit (T3)`.

---

## 0. Lecture des 30 fenêtres

Le résidu est **presque exclusivement des corps** : aucune fenêtre n'est un pur
`Location-line` ni un pur `reorder` (les lignes sont déjà alignées partout ailleurs par les
lanes `r5-coord-*`/`mg-P-*`/`fz-P-*`). Répartition mesurée :

| Classe | pump | pump_amm | total |
|---|---:|---:|---:|
| `forme de fonction` (corps présent, codegen diverge) | 4 | 1 | **5** |
| `corps non reconstruit (T3)` | 21 | 4 | **25** |
| `Location-line` pur | 0 | 0 | 0 |
| `reorder` pur | 0 | 0 | 0 |

Tri par facilité : les 5 « forme de fonction » d'abord (le corps existe, il faut la forme),
puis les 25 « T3 » par `n` croissant (le nombre d'instructions significativement différentes).

---

## 1. Classe A — forme de fonction (7)

Le corps est déjà reconstruit (containment ≥ 0.59, souvent ~0.8) ; le résidu est la **forme** :
owned vs borrowed `AccountInfo` (`noalias`), frame slots, ordre de contrôle-flow, frontière
de helper. Leviers déjà prouvés sur les fenêtres voisines (à réutiliser) :
- `*const AccountInfo` déréférencé (`unsafe { &*payer }`) pour casser `noalias` et forcer le
  reload de `payer.key` (fz-P-buyv2a-r1-01) ;
- `&Context<…>` au lieu de `&Struct` pour retirer `noalias` des comptes (r5-z04-02) ;
- `let x = &mut ctx.accounts.x;` (reload du pointeur d'`AccountInfo` à chaque CPI, mg-P-cash-01) ;
- helper `#[inline(always)]` générique (`&impl ToAccountInfo`) et `#[inline(never)]` privé,
  seeds inlinés, `let`-bindings des montants avant l'évènement (fz-P-*) ;
- Source sites replacés sur les lignes d'origine via les pads `// layout-pad` (L12+).

| addr | octets | identité | n | containment | levier |
|---:|---:|---|---:|---:|---|
| 0x4c750 | 9024 | legacy_sell::cashback | 712 | 0.961 | owned/&mut AccountInfo reload + 59 Location lines (le même levier que mg-P-cash-01) |
| 0x3fb70 | 5440 | migrate helper (callee de migrate) | 84 | 0.808 | ordre des branches + let-bindings (c=0.808) |
| 0x83c00 | 3440 | trade::v3_execute_buy (H) | 114 | 0.763 | ordre de contrôle-flow v3 (c=0.763) |
| 0x4c158 | 8368 | migrate_v2::create_token_account_v2 (H) | 444 | 0.83 | helper A4 (create_token_account_v2) + owned AccountInfo (c=0.830) |
| 0x13f630 | 20184 | buy_exact_quote_in_v2 handler | 757 | 0.778 | ordre de contrôle-flow quote/amount (c=0.778) |

### Specs (forme de fonction)

#### pump_amm :: legacy_sell::cashback (9024 B)

- **Identité** : `legacy_sell::cashback` (`instructions/swap/sell.rs`) — [M] si `Location`/anatomie, sinon [H].
- **Dérive mesurée** : n=712, containment=0.961, classes {'alu': 154, 'stack': 24, 'mem': 88, 'frame': 250, 'branch': 57, 'literal': 26, 'line': 59, 'call': 54}.
- **Classe** : `forme de fonction`. Le corps est présent (même taille/±, containment élevé) ;
  l'écart est la forme codegen, pas la logique.
- **Construct à changer** : owned/&mut AccountInfo reload + 59 Location lines (le même levier que mg-P-cash-01).
- **Risque de régression** : toute forme d'emprunt/ABI d'un helper partagé déplace les
  fenêtres appariées de ses **appelants** (dans le même fichier) ; re-mesurer la famille
  entière (`buy_v2.rs`, `migrate_v2.rs`, `trade_v3.rs`, `sell.rs`).

#### pump :: migrate helper (callee de migrate) (5440 B)

- **Identité** : `migrate helper (callee de migrate)` (`migrate.rs`) — [M] si `Location`/anatomie, sinon [H].
- **Dérive mesurée** : n=84, containment=0.808, classes {'branch': 55, 'stack': 14, 'alu': 10, 'literal': 1, 'call': 2, 'mem': 2}.
- **Classe** : `forme de fonction`. Le corps est présent (même taille/±, containment élevé) ;
  l'écart est la forme codegen, pas la logique.
- **Construct à changer** : ordre des branches + let-bindings (c=0.808).
- **Risque de régression** : toute forme d'emprunt/ABI d'un helper partagé déplace les
  fenêtres appariées de ses **appelants** (dans le même fichier) ; re-mesurer la famille
  entière (`buy_v2.rs`, `migrate_v2.rs`, `trade_v3.rs`, `sell.rs`).

#### pump :: trade::v3_execute_buy (H) (3440 B)

- **Identité** : `trade::v3_execute_buy (H)` (`trade_v3.rs`) — [M] si `Location`/anatomie, sinon [H].
- **Dérive mesurée** : n=114, containment=0.763, classes {'branch': 24, 'stack': 43, 'alu': 13, 'mem': 34}.
- **Classe** : `forme de fonction`. Le corps est présent (même taille/±, containment élevé) ;
  l'écart est la forme codegen, pas la logique.
- **Construct à changer** : ordre de contrôle-flow v3 (c=0.763).
- **Risque de régression** : toute forme d'emprunt/ABI d'un helper partagé déplace les
  fenêtres appariées de ses **appelants** (dans le même fichier) ; re-mesurer la famille
  entière (`buy_v2.rs`, `migrate_v2.rs`, `trade_v3.rs`, `sell.rs`).

#### pump :: migrate_v2::create_token_account_v2 (H) (8368 B)

- **Identité** : `migrate_v2::create_token_account_v2 (H)` (`migrate_v2.rs`) — [M] si `Location`/anatomie, sinon [H].
- **Dérive mesurée** : n=444, containment=0.83, classes {'mem': 128, 'stack': 233, 'branch': 53, 'alu': 30}.
- **Classe** : `forme de fonction`. Le corps est présent (même taille/±, containment élevé) ;
  l'écart est la forme codegen, pas la logique.
- **Construct à changer** : helper A4 (create_token_account_v2) + owned AccountInfo (c=0.830).
- **Risque de régression** : toute forme d'emprunt/ABI d'un helper partagé déplace les
  fenêtres appariées de ses **appelants** (dans le même fichier) ; re-mesurer la famille
  entière (`buy_v2.rs`, `migrate_v2.rs`, `trade_v3.rs`, `sell.rs`).

#### pump :: buy_exact_quote_in_v2 handler (20184 B)

- **Identité** : `buy_exact_quote_in_v2 handler` (`buy_v2.rs`) — [M] si `Location`/anatomie, sinon [H].
- **Dérive mesurée** : n=757, containment=0.778, classes {'alu': 126, 'mem': 150, 'stack': 354, 'branch': 125, 'literal': 1, 'call': 1}.
- **Classe** : `forme de fonction`. Le corps est présent (même taille/±, containment élevé) ;
  l'écart est la forme codegen, pas la logique.
- **Construct à changer** : ordre de contrôle-flow quote/amount (c=0.778).
- **Risque de régression** : toute forme d'emprunt/ABI d'un helper partagé déplace les
  fenêtres appariées de ses **appelants** (dans le même fichier) ; re-mesurer la famille
  entière (`buy_v2.rs`, `migrate_v2.rs`, `trade_v3.rs`, `sell.rs`).

---

## 2. Classe B — corps non reconstruit (T3) (23)

Le corps déployé n'est pas reproduit par la source (containment < 0.7, souvent ≪ 0.6,
beaucoup de `mem`/`stack` structurantes). Il faut **reconstruire le corps** depuis le
désassemblage déployé, en réutilisant la décomposition de helpers + l'ordre de
contrôle-flow + les sites Source des lanes déjà byte-égalées (fz-P-mig2-r1-02, fz-P-cfee1/2,
fz-P-hop, fz-P-v3a/v3b, fz-P-inc, fz-P-sweep, fz-P-legacy).

| addr | octets | identité | n | containment | levier |
|---:|---:|---|---:|---:|---|
| 0x19138 | 9176 | admin::set_reserved_fee_recipients | 152 | 0.823 | boucle 8 comptes + format!/with_account_name + ordre rent/executable |
| 0x6db20 | 6312 | GlobalVolumeAccumulator (impl) | 235 | 0.652 | méthodes update_token_incentives/update_schedule + try_into (ordre des blocs) |
| 0x351a8 | 8104 | buy::distribute_cashback | 539 | 0.687 | frontière de helper + ordre des branches cashback |
| 0x2ba60 | 10240 | create_pool::execute | 877 | 0.658 | décomposition helpers + ordre des CPI + inlining |
| 0x7bfd8 | 1864 | volume_accumulator::update | 78 | 0.615 | update (c=0.615, petit corps) |
| 0x147ba0 | 3672 | buy_v3 | 198 | 0.532 | corps buy_v3 |
| 0x80df8 | 2120 | trade helper (H) | 203 | 0.335 | Location lib.rs |
| 0x14a8a8 | 6032 | sell_v3 | 530 | 0.592 | corps sell_v3 |
| 0x567d8 | 5216 | multi_hop_curve_swap helper | 571 | 0.318 | native_buyback/route |
| 0x18678 | 5704 | create_v2 helper (walk) (M) | 649 | 0.452 | walk récursif nested_create (Location create_v2.rs) |
| 0x1489f8 | 7856 | buy_exact_quote_in_v3 | 665 | 0.594 | ordre v3 quote (c=0.594, borderline) |
| 0x72810 | 7832 | sweep::execute | 695 | 0.488 | sweep creator/protocol + transfer |
| 0x152888 | 8488 | sell (business) | 736 | 0.589 | corps legacy sell |
| 0x1ac28 | 7256 | create_v2::initialize_metadata (H) | 758 | 0.571 | init metadata CPI |
| 0x6fef8 | 9176 | set_reserved_fee_recipients::execute | 879 | 0.578 | boucle + transferts |
| 0x77940 | 8832 | claim_cashback_v2 | 907 | 0.571 | cashback V2 |
| 0x6cd78 | 8544 | sell helper (M) | 955 | 0.351 | Location sell.rs |
| 0x13b9b8 | 15480 | buy_v2::buy_handler | 1006 | 0.646 | corps buy_v2 (buy_handler) |
| 0x14f4e0 | 13224 | buy_exact_sol_in (business) | 1116 | 0.523 | corps legacy buy_exact_sol_in |
| 0x138b20 | 11928 | create (business) | 1123 | 0.697 | frontière helpers + ordre (c=0.697, borderline) |
| 0x144508 | 13976 | sell_v2::execute | 1435 | 0.541 | corps sell_v2 |
| 0x34558 | 14512 | holder_distribution::execute | 1438 | 0.556 | boucle holders + transferts |
| 0x1e7c0 | 15576 | create_v2::execute | 1590 | 0.466 | gros corps (mint/quote/metadata CPI) |
| 0x5b3b0 | 18584 | buy_v2 handler (buy_exact_quote_in) (H) | 2098 | 0.389 | second handler buy_v2 |
| 0x22a10 | 27400 | admin_cto::execute | 3088 | 0.302 | le plus gros (27400 B) ; révision gardes 6080/6088/6092/6095 |

### Specs (T3)

#### pump_amm :: admin::set_reserved_fee_recipients (9176 B)

- **Identité** : `admin::set_reserved_fee_recipients` (`instructions/admin/set_reserved_fee_recipients.rs`).
- **Dérive mesurée** : n=152, containment=0.823, classes {'branch': 41, 'stack': 61, 'mem': 34, 'alu': 15, 'literal': 1}.
- **Classe** : `corps non reconstruit (T3)`. La logique déployée n'est pas dans la source.
- **Construct à changer** : reconstruire le corps depuis `sbftool func <so> $((0x19138/8))` :
  boucle 8 comptes + format!/with_account_name + ordre rent/executable.
- **Risque de régression** : ces corps sont appelés par les entrées `#[program]` déjà
  appariées ; toute décomposition de helper modifie le graphe d'appel. Garder les sites
  Source/lignes des callees déjà byte-égalées ; mesurer `matched`+`raw` sur tout le programme.

#### pump_amm :: GlobalVolumeAccumulator (impl) (6312 B)

- **Identité** : `GlobalVolumeAccumulator (impl)` (`state/volume_accumulator.rs`).
- **Dérive mesurée** : n=235, containment=0.652, classes {'stack': 100, 'mem': 5, 'branch': 74, 'alu': 44, 'literal': 6, 'call': 6}.
- **Classe** : `corps non reconstruit (T3)`. La logique déployée n'est pas dans la source.
- **Construct à changer** : reconstruire le corps depuis `sbftool func <so> $((0x6db20/8))` :
  méthodes update_token_incentives/update_schedule + try_into (ordre des blocs).
- **Risque de régression** : ces corps sont appelés par les entrées `#[program]` déjà
  appariées ; toute décomposition de helper modifie le graphe d'appel. Garder les sites
  Source/lignes des callees déjà byte-égalées ; mesurer `matched`+`raw` sur tout le programme.

#### pump_amm :: buy::distribute_cashback (8104 B)

- **Identité** : `buy::distribute_cashback` (`instructions/swap/buy.rs`).
- **Dérive mesurée** : n=539, containment=0.687, classes {'alu': 48, 'branch': 57, 'stack': 288, 'mem': 146}.
- **Classe** : `corps non reconstruit (T3)`. La logique déployée n'est pas dans la source.
- **Construct à changer** : reconstruire le corps depuis `sbftool func <so> $((0x351a8/8))` :
  frontière de helper + ordre des branches cashback.
- **Risque de régression** : ces corps sont appelés par les entrées `#[program]` déjà
  appariées ; toute décomposition de helper modifie le graphe d'appel. Garder les sites
  Source/lignes des callees déjà byte-égalées ; mesurer `matched`+`raw` sur tout le programme.

#### pump_amm :: create_pool::execute (10240 B)

- **Identité** : `create_pool::execute` (`instructions/create_pool.rs`).
- **Dérive mesurée** : n=877, containment=0.658, classes {'alu': 119, 'stack': 476, 'mem': 186, 'literal': 13, 'call': 17, 'branch': 66}.
- **Classe** : `corps non reconstruit (T3)`. La logique déployée n'est pas dans la source.
- **Construct à changer** : reconstruire le corps depuis `sbftool func <so> $((0x2ba60/8))` :
  décomposition helpers + ordre des CPI + inlining.
- **Risque de régression** : ces corps sont appelés par les entrées `#[program]` déjà
  appariées ; toute décomposition de helper modifie le graphe d'appel. Garder les sites
  Source/lignes des callees déjà byte-égalées ; mesurer `matched`+`raw` sur tout le programme.

#### pump :: volume_accumulator::update (1864 B)

- **Identité** : `volume_accumulator::update` (`token_incentives/volume_accumulator.rs`).
- **Dérive mesurée** : n=78, containment=0.615, classes {'branch': 29, 'stack': 4, 'alu': 25, 'mem': 17, 'literal': 2, 'call': 1}.
- **Classe** : `corps non reconstruit (T3)`. La logique déployée n'est pas dans la source.
- **Construct à changer** : reconstruire le corps depuis `sbftool func <so> $((0x7bfd8/8))` :
  update (c=0.615, petit corps).
- **Risque de régression** : ces corps sont appelés par les entrées `#[program]` déjà
  appariées ; toute décomposition de helper modifie le graphe d'appel. Garder les sites
  Source/lignes des callees déjà byte-égalées ; mesurer `matched`+`raw` sur tout le programme.

#### pump :: buy_v3 (3672 B)

- **Identité** : `buy_v3` (`trade_v3.rs`).
- **Dérive mesurée** : n=198, containment=0.532, classes {'stack': 90, 'alu': 49, 'mem': 22, 'branch': 36, 'call': 1}.
- **Classe** : `corps non reconstruit (T3)`. La logique déployée n'est pas dans la source.
- **Construct à changer** : reconstruire le corps depuis `sbftool func <so> $((0x147ba0/8))` :
  corps buy_v3.
- **Risque de régression** : ces corps sont appelés par les entrées `#[program]` déjà
  appariées ; toute décomposition de helper modifie le graphe d'appel. Garder les sites
  Source/lignes des callees déjà byte-égalées ; mesurer `matched`+`raw` sur tout le programme.

#### pump :: trade helper (H) (2120 B)

- **Identité** : `trade helper (H)` (`lib.rs`).
- **Dérive mesurée** : n=203, containment=0.335, classes {'stack': 89, 'alu': 57, 'mem': 14, 'branch': 26, 'literal': 10, 'call': 7}.
- **Classe** : `corps non reconstruit (T3)`. La logique déployée n'est pas dans la source.
- **Construct à changer** : reconstruire le corps depuis `sbftool func <so> $((0x80df8/8))` :
  Location lib.rs.
- **Risque de régression** : ces corps sont appelés par les entrées `#[program]` déjà
  appariées ; toute décomposition de helper modifie le graphe d'appel. Garder les sites
  Source/lignes des callees déjà byte-égalées ; mesurer `matched`+`raw` sur tout le programme.

#### pump :: sell_v3 (6032 B)

- **Identité** : `sell_v3` (`trade_v3.rs`).
- **Dérive mesurée** : n=530, containment=0.592, classes {'alu': 112, 'stack': 267, 'mem': 74, 'branch': 60, 'literal': 3, 'call': 14}.
- **Classe** : `corps non reconstruit (T3)`. La logique déployée n'est pas dans la source.
- **Construct à changer** : reconstruire le corps depuis `sbftool func <so> $((0x14a8a8/8))` :
  corps sell_v3.
- **Risque de régression** : ces corps sont appelés par les entrées `#[program]` déjà
  appariées ; toute décomposition de helper modifie le graphe d'appel. Garder les sites
  Source/lignes des callees déjà byte-égalées ; mesurer `matched`+`raw` sur tout le programme.

#### pump :: multi_hop_curve_swap helper (5216 B)

- **Identité** : `multi_hop_curve_swap helper` (`multi_hop_curve_swap.rs`).
- **Dérive mesurée** : n=571, containment=0.318, classes {'alu': 94, 'branch': 45, 'mem': 97, 'stack': 304, 'literal': 14, 'call': 17}.
- **Classe** : `corps non reconstruit (T3)`. La logique déployée n'est pas dans la source.
- **Construct à changer** : reconstruire le corps depuis `sbftool func <so> $((0x567d8/8))` :
  native_buyback/route.
- **Risque de régression** : ces corps sont appelés par les entrées `#[program]` déjà
  appariées ; toute décomposition de helper modifie le graphe d'appel. Garder les sites
  Source/lignes des callees déjà byte-égalées ; mesurer `matched`+`raw` sur tout le programme.

#### pump :: create_v2 helper (walk) (M) (5704 B)

- **Identité** : `create_v2 helper (walk) (M)` (`create_v2.rs`).
- **Dérive mesurée** : n=649, containment=0.452, classes {'alu': 115, 'branch': 57, 'mem': 46, 'stack': 373, 'call': 30, 'literal': 28}.
- **Classe** : `corps non reconstruit (T3)`. La logique déployée n'est pas dans la source.
- **Construct à changer** : reconstruire le corps depuis `sbftool func <so> $((0x18678/8))` :
  walk récursif nested_create (Location create_v2.rs).
- **Risque de régression** : ces corps sont appelés par les entrées `#[program]` déjà
  appariées ; toute décomposition de helper modifie le graphe d'appel. Garder les sites
  Source/lignes des callees déjà byte-égalées ; mesurer `matched`+`raw` sur tout le programme.

#### pump :: buy_exact_quote_in_v3 (7856 B)

- **Identité** : `buy_exact_quote_in_v3` (`trade_v3.rs`).
- **Dérive mesurée** : n=665, containment=0.594, classes {'alu': 144, 'stack': 417, 'mem': 13, 'branch': 77, 'literal': 3, 'call': 11}.
- **Classe** : `corps non reconstruit (T3)`. La logique déployée n'est pas dans la source.
- **Construct à changer** : reconstruire le corps depuis `sbftool func <so> $((0x1489f8/8))` :
  ordre v3 quote (c=0.594, borderline).
- **Risque de régression** : ces corps sont appelés par les entrées `#[program]` déjà
  appariées ; toute décomposition de helper modifie le graphe d'appel. Garder les sites
  Source/lignes des callees déjà byte-égalées ; mesurer `matched`+`raw` sur tout le programme.

#### pump :: sweep::execute (7832 B)

- **Identité** : `sweep::execute` (`sweep_fees.rs`).
- **Dérive mesurée** : n=695, containment=0.488, classes {'alu': 129, 'mem': 163, 'stack': 311, 'branch': 69, 'literal': 6, 'call': 17}.
- **Classe** : `corps non reconstruit (T3)`. La logique déployée n'est pas dans la source.
- **Construct à changer** : reconstruire le corps depuis `sbftool func <so> $((0x72810/8))` :
  sweep creator/protocol + transfer.
- **Risque de régression** : ces corps sont appelés par les entrées `#[program]` déjà
  appariées ; toute décomposition de helper modifie le graphe d'appel. Garder les sites
  Source/lignes des callees déjà byte-égalées ; mesurer `matched`+`raw` sur tout le programme.

#### pump :: sell (business) (8488 B)

- **Identité** : `sell (business)` (`sell.rs`).
- **Dérive mesurée** : n=736, containment=0.589, classes {'stack': 414, 'mem': 67, 'alu': 143, 'branch': 83, 'literal': 9, 'call': 20}.
- **Classe** : `corps non reconstruit (T3)`. La logique déployée n'est pas dans la source.
- **Construct à changer** : reconstruire le corps depuis `sbftool func <so> $((0x152888/8))` :
  corps legacy sell.
- **Risque de régression** : ces corps sont appelés par les entrées `#[program]` déjà
  appariées ; toute décomposition de helper modifie le graphe d'appel. Garder les sites
  Source/lignes des callees déjà byte-égalées ; mesurer `matched`+`raw` sur tout le programme.

#### pump :: create_v2::initialize_metadata (H) (7256 B)

- **Identité** : `create_v2::initialize_metadata (H)` (`create_v2.rs`).
- **Dérive mesurée** : n=758, containment=0.571, classes {'alu': 111, 'stack': 396, 'mem': 169, 'call': 10, 'branch': 70, 'literal': 2}.
- **Classe** : `corps non reconstruit (T3)`. La logique déployée n'est pas dans la source.
- **Construct à changer** : reconstruire le corps depuis `sbftool func <so> $((0x1ac28/8))` :
  init metadata CPI.
- **Risque de régression** : ces corps sont appelés par les entrées `#[program]` déjà
  appariées ; toute décomposition de helper modifie le graphe d'appel. Garder les sites
  Source/lignes des callees déjà byte-égalées ; mesurer `matched`+`raw` sur tout le programme.

#### pump :: set_reserved_fee_recipients::execute (9176 B)

- **Identité** : `set_reserved_fee_recipients::execute` (`set_reserved_fee_recipients.rs`).
- **Dérive mesurée** : n=879, containment=0.578, classes {'alu': 178, 'mem': 187, 'branch': 67, 'literal': 27, 'stack': 368, 'call': 52}.
- **Classe** : `corps non reconstruit (T3)`. La logique déployée n'est pas dans la source.
- **Construct à changer** : reconstruire le corps depuis `sbftool func <so> $((0x6fef8/8))` :
  boucle + transferts.
- **Risque de régression** : ces corps sont appelés par les entrées `#[program]` déjà
  appariées ; toute décomposition de helper modifie le graphe d'appel. Garder les sites
  Source/lignes des callees déjà byte-égalées ; mesurer `matched`+`raw` sur tout le programme.

#### pump :: claim_cashback_v2 (8832 B)

- **Identité** : `claim_cashback_v2` (`cashback.rs`).
- **Dérive mesurée** : n=907, containment=0.571, classes {'alu': 197, 'mem': 149, 'call': 48, 'stack': 406, 'branch': 83, 'literal': 24}.
- **Classe** : `corps non reconstruit (T3)`. La logique déployée n'est pas dans la source.
- **Construct à changer** : reconstruire le corps depuis `sbftool func <so> $((0x77940/8))` :
  cashback V2.
- **Risque de régression** : ces corps sont appelés par les entrées `#[program]` déjà
  appariées ; toute décomposition de helper modifie le graphe d'appel. Garder les sites
  Source/lignes des callees déjà byte-égalées ; mesurer `matched`+`raw` sur tout le programme.

#### pump :: sell helper (M) (8544 B)

- **Identité** : `sell helper (M)` (`sell.rs`).
- **Dérive mesurée** : n=955, containment=0.351, classes {'alu': 182, 'branch': 88, 'stack': 485, 'mem': 113, 'literal': 39, 'call': 48}.
- **Classe** : `corps non reconstruit (T3)`. La logique déployée n'est pas dans la source.
- **Construct à changer** : reconstruire le corps depuis `sbftool func <so> $((0x6cd78/8))` :
  Location sell.rs.
- **Risque de régression** : ces corps sont appelés par les entrées `#[program]` déjà
  appariées ; toute décomposition de helper modifie le graphe d'appel. Garder les sites
  Source/lignes des callees déjà byte-égalées ; mesurer `matched`+`raw` sur tout le programme.

#### pump :: buy_v2::buy_handler (15480 B)

- **Identité** : `buy_v2::buy_handler` (`buy_v2.rs`).
- **Dérive mesurée** : n=1006, containment=0.646, classes {'alu': 207, 'stack': 455, 'mem': 199, 'branch': 124, 'call': 19, 'literal': 2}.
- **Classe** : `corps non reconstruit (T3)`. La logique déployée n'est pas dans la source.
- **Construct à changer** : reconstruire le corps depuis `sbftool func <so> $((0x13b9b8/8))` :
  corps buy_v2 (buy_handler).
- **Risque de régression** : ces corps sont appelés par les entrées `#[program]` déjà
  appariées ; toute décomposition de helper modifie le graphe d'appel. Garder les sites
  Source/lignes des callees déjà byte-égalées ; mesurer `matched`+`raw` sur tout le programme.

#### pump :: buy_exact_sol_in (business) (13224 B)

- **Identité** : `buy_exact_sol_in (business)` (`buy.rs`).
- **Dérive mesurée** : n=1116, containment=0.523, classes {'alu': 274, 'stack': 514, 'mem': 123, 'branch': 128, 'call': 51, 'literal': 26}.
- **Classe** : `corps non reconstruit (T3)`. La logique déployée n'est pas dans la source.
- **Construct à changer** : reconstruire le corps depuis `sbftool func <so> $((0x14f4e0/8))` :
  corps legacy buy_exact_sol_in.
- **Risque de régression** : ces corps sont appelés par les entrées `#[program]` déjà
  appariées ; toute décomposition de helper modifie le graphe d'appel. Garder les sites
  Source/lignes des callees déjà byte-égalées ; mesurer `matched`+`raw` sur tout le programme.

#### pump :: create (business) (11928 B)

- **Identité** : `create (business)` (`create.rs`).
- **Dérive mesurée** : n=1123, containment=0.697, classes {'alu': 127, 'stack': 656, 'mem': 246, 'branch': 86, 'call': 4, 'literal': 4}.
- **Classe** : `corps non reconstruit (T3)`. La logique déployée n'est pas dans la source.
- **Construct à changer** : reconstruire le corps depuis `sbftool func <so> $((0x138b20/8))` :
  frontière helpers + ordre (c=0.697, borderline).
- **Risque de régression** : ces corps sont appelés par les entrées `#[program]` déjà
  appariées ; toute décomposition de helper modifie le graphe d'appel. Garder les sites
  Source/lignes des callees déjà byte-égalées ; mesurer `matched`+`raw` sur tout le programme.

#### pump :: sell_v2::execute (13976 B)

- **Identité** : `sell_v2::execute` (`sell_v2.rs`).
- **Dérive mesurée** : n=1435, containment=0.541, classes {'stack': 654, 'mem': 260, 'alu': 304, 'branch': 141, 'literal': 20, 'call': 56}.
- **Classe** : `corps non reconstruit (T3)`. La logique déployée n'est pas dans la source.
- **Construct à changer** : reconstruire le corps depuis `sbftool func <so> $((0x144508/8))` :
  corps sell_v2.
- **Risque de régression** : ces corps sont appelés par les entrées `#[program]` déjà
  appariées ; toute décomposition de helper modifie le graphe d'appel. Garder les sites
  Source/lignes des callees déjà byte-égalées ; mesurer `matched`+`raw` sur tout le programme.

#### pump :: holder_distribution::execute (14512 B)

- **Identité** : `holder_distribution::execute` (`creator/distribute_fee_to_holders.rs`).
- **Dérive mesurée** : n=1438, containment=0.556, classes {'mem': 279, 'alu': 225, 'branch': 160, 'stack': 735, 'literal': 18, 'call': 21}.
- **Classe** : `corps non reconstruit (T3)`. La logique déployée n'est pas dans la source.
- **Construct à changer** : reconstruire le corps depuis `sbftool func <so> $((0x34558/8))` :
  boucle holders + transferts.
- **Risque de régression** : ces corps sont appelés par les entrées `#[program]` déjà
  appariées ; toute décomposition de helper modifie le graphe d'appel. Garder les sites
  Source/lignes des callees déjà byte-égalées ; mesurer `matched`+`raw` sur tout le programme.

#### pump :: create_v2::execute (15576 B)

- **Identité** : `create_v2::execute` (`create_v2.rs`).
- **Dérive mesurée** : n=1590, containment=0.466, classes {'stack': 917, 'mem': 114, 'branch': 117, 'alu': 317, 'literal': 53, 'call': 72}.
- **Classe** : `corps non reconstruit (T3)`. La logique déployée n'est pas dans la source.
- **Construct à changer** : reconstruire le corps depuis `sbftool func <so> $((0x1e7c0/8))` :
  gros corps (mint/quote/metadata CPI).
- **Risque de régression** : ces corps sont appelés par les entrées `#[program]` déjà
  appariées ; toute décomposition de helper modifie le graphe d'appel. Garder les sites
  Source/lignes des callees déjà byte-égalées ; mesurer `matched`+`raw` sur tout le programme.

#### pump :: buy_v2 handler (buy_exact_quote_in) (H) (18584 B)

- **Identité** : `buy_v2 handler (buy_exact_quote_in) (H)` (`buy_v2.rs`).
- **Dérive mesurée** : n=2098, containment=0.389, classes {'alu': 378, 'stack': 1043, 'mem': 378, 'branch': 189, 'call': 85, 'literal': 25}.
- **Classe** : `corps non reconstruit (T3)`. La logique déployée n'est pas dans la source.
- **Construct à changer** : reconstruire le corps depuis `sbftool func <so> $((0x5b3b0/8))` :
  second handler buy_v2.
- **Risque de régression** : ces corps sont appelés par les entrées `#[program]` déjà
  appariées ; toute décomposition de helper modifie le graphe d'appel. Garder les sites
  Source/lignes des callees déjà byte-égalées ; mesurer `matched`+`raw` sur tout le programme.

#### pump :: admin_cto::execute (27400 B)

- **Identité** : `admin_cto::execute` (`creator/admin_cto.rs`).
- **Dérive mesurée** : n=3088, containment=0.302, classes {'stack': 1621, 'mem': 477, 'alu': 544, 'branch': 304, 'call': 89, 'literal': 53}.
- **Classe** : `corps non reconstruit (T3)`. La logique déployée n'est pas dans la source.
- **Construct à changer** : reconstruire le corps depuis `sbftool func <so> $((0x22a10/8))` :
  le plus gros (27400 B) ; révision gardes 6080/6088/6092/6095.
- **Risque de régression** : ces corps sont appelés par les entrées `#[program]` déjà
  appariées ; toute décomposition de helper modifie le graphe d'appel. Garder les sites
  Source/lignes des callees déjà byte-égalées ; mesurer `matched`+`raw` sur tout le programme.

---

## 3. Ordre d'exécution et acceptance

1. **Classe A** (5) dans l'ordre du tableau (amm `0x4c750` d'abord : containment 0.961,
   le plus proche).
2. **Classe B** (25) par `n` croissant (le tableau est déjà trié).
3. Mesurer `matched`+`raw` après chaque fenêtre ; garder seulement sans perte sur les voisines.

Commandes :
```sh
python tools/sbftool.py func <deployed.so> $((0x22a10/8))   # admin_cto, le plus gros
python research/claude-pump-integration-20261027/r37-layout-33/verify.py
python research/claude-amm-union7-20261028/verify.py
```

---

*Analyse lecture seule : binaires déployés + candidats/sources MIT de lalalune. Aucun
build, aucun patch, aucun PR de code. Crédit lalalune/pumpfun-source (MIT).*
