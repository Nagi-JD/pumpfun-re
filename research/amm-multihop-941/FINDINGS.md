# AMM multi_hop 941 / fenêtre 520 B — findings d'analyse (2026-10-27)

Travail privé (pas de PR). Basé sur lalalune/pumpfun-source (MIT).
Binaires : `../pumpfun-source/evidence/original/pump_amm/deployed.so`.
Outils : `tools/sbftool.py`, `tools/hunt_closure.py` (nouveau, local).

## Terminologie (relevé pendant l'analyse)

- La métrique fenêtre exprime les adresses en **offsets octets** dans `.text`.
- `sbftool.py` exprime les PCs en **index d'instructions** (1 insn = 8 octets).
  Conversion : `idx = octet / 8`. `dis`, `callers`, `field` convertissent
  automatiquement ; `func` NON (lui passer un index).
- Les fermetures `error!` sont construites ainsi :
  `lddw rX, <vaddr chemin>` ; `stdw ... , <len>` ; `stw ..., <LIGNE>` ;
  `stw ..., <code erreur Anchor>` ; `call <constructeur 0x205f7>`.
  Les codes Anchor = 6000 + discriminant. Côté pump_amm : 6023 = `Overflow`
  (docs/error_catalogs.md), 6044 = NotEnoughRemainingAccounts,
  6084/6085/6086 = MultiHopDiscontinuousPath/CurveRunMismatch/MixedDirection.

## Ce que sont les deux items OPEN_TASKS « multi_hop 941 » et « 0x89d0 »

1. **« multi_hop 941 closure »** = fermeture `Overflow` (6023) à
   `programs/pump-amm/src/instructions/swap/multi_hop_swap.rs:941`
   (0x3ad), construite à pc 0x17288 (octet 0xb9440).
   Elle vit **dans la fenêtre 520 octets non-matchée 0xb92c8** (idx 0x17259–0x17299).

2. **« fenêtre 520 B sans error tuple (0x89d0) »** = la fenêtre à octet 0x89d0,
   qui est le **glue de drop/décompte Rc** (boucle de `add64 -1` sur des
   compteurs de ref, fin `exit`). Elle est **déjà matched + raw** dans
   u0/u1/u2 (dès 599) — item déjà résolu côté « here », l'intérêt restant est
   le vrai trou : **0xb92c8**.

## Structure de la fenêtre 0xb92c8 (520 B, non-matchée u0→u2)

C'est une **arm d'erreur à froid (outlined)** d'un contrôle de dépassement :
l'appelant (idx 0x92b8–0x92c3) fait
`r2 = r4 + r6 ; jlt r2, r4 → overflow`, et le bras d'erreur appelle
cette fonction qui :
1. appelle 0xea7f / 0xf574 (mise en place d'un Formatter core::fmt,
   vtable 0x1221e0, table de longueurs 0x11c040) ;
2. en cas d'échec de fmt, panique « a Display implementation returned an
   error unexpectedly » (0x11c0fa, len 55, via 0x225f3) ;
3. construit `Err(Overflow)` avec (multi_hop_swap.rs, len 57, **ligne 941**) ;
4. écrit les 16 octets du Result dans la struct de retour (r6) et `exit`.

Elle est le **clone exact** d'une autre fonction (idx 0x8999, octet 0x44CC8)
dont la seule différence est la ligne de la closure : **636** (0x27c).
Chaque copie a **un seul appelant** :
- idx 0x85a3 → clone ligne 636 (bras froid d'un `jlt`-chain, seq idx 0x8596-0x85a0) ;
- idx 0x92c3 → clone ligne 941 (bras froid de `r2 = r4 + r6`, idx 0x92b8-0x92bd).

## Hypothèse de reconstruction

Le code déployé **sépare en fonction le bras d'erreur froid** (outline LLVM ou
fn explicite). Notre candidat inline ce bras dans l'appelant → la fenêtre
(qui couvre l'arm outline dans le déployé) ne matche pas. Deux pistes :

1. **Forme source** : exprimer le contrôle comme un helper `fn` dédié (p. ex.
   un `fn overflow_at(...) -> PumpAmmError` / un `ok_or_else` vers un item
   `fn`, cf. la méthode « fn-item » déjà utilisée dans les paquets pump :
   `ok_or_else(crate::xxx::overflow)`), avec la fermeture/`error!` posée sur
   la ligne 941 (et 636 pour l'autre copie).
2. **LLVM-IR** : si la décision d'outline dépend de la taille/du voisinage,
   émettre l'IR et vérifier le point de bascule, comme prescrit par
   OPEN_TASKS (méthode llc pour les écarts d'ordre de blocs).

## À faire ensuite (mesure obligatoire)

- [ ] Monter la chaîne de build (WSL + platform-tools Solana v1.44, `cargo rustc`
      direct + `--remap-path-prefix`, cf. `research/amm-race/build.sh` et
      `remap-path-prefix.txt`).
- [ ] Extraire le source du checkpoint AMM (lalalune
      `repro/pump_amm/native-fee-cpi-recovery-20261027`, dans le pack git) +
      appliquer `amm-race/closure-placement.patch` + `amm-race-2/closure-placement-2.patch`.
- [ ] Reconstruire les deux bras (636 et 941) en fonctions séparées, mesurer
      avec la métrique fenêtre (avant : u2 = 657/785, 128 raw ; objectif :
      +0xb92c8 sans rien perdre — matched set ET raw set).
- [ ] Règles : aucun macro fichier/ligne hardcodé, jamais le .so comme input,
      pas de régression, chiffres collés dans le RESULT.
