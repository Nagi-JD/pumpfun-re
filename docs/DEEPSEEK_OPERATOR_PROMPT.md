# DeepSeek — mode opérateur : tu compiles et tu mesures toi-même

Jusqu'ici tu proposais et Claude testait. À partir de maintenant **tu fais toute la boucle toi-même** :
hypothèse → modification source → build → mesure → garder ou annuler. Claude vérifie tes gains à la fin,
mais tu n'attends plus personne entre deux essais.

## Objectif
Battre les derniers checkpoints de lalalune/pumpfun-source (MIT, `~/pumpre/repo` branche locale `main`
= upstream 2a2820e26) en nombre de **fenêtres appariées** et de **corps exacts au byte**, mesurés avec
LEUR métrique. Jamais de claim sans la mesure collée.

Références à battre (eux → nous) : Fees 578 (198 exacts) → nous 578 + fix ATA en test · PumpSwap 599 →
nous **648** · Pump Round23 712 → agent en cours · Mayhem 429 (100 exacts) → Claude en cours.

## TON PÉRIMÈTRE (aucun chevauchement avec les agents de Claude)
1. **Fees — les 6 fenêtres que personne ne traite** : claim_v2 (déployé 137280 ↔ candidat 75880),
   withdraw (249264 ↔ 201152), crank_donation (147944 ↔ 629104), create_donation (163920 ↔ 125384),
   create_sharing (177720 ↔ 113312), extend_fee_config (76384 ↔ 187464).
   (L'agent Fees garde l'ATA 243184 et sweep_buyback 120816 — n'y touche pas.)
2. **Pump — `pump_quote` et `trade_v3`** sur la base Round23 (12 + 15 fenêtres).
   (L'agent Pump garde les 55 closures d'erreur et lib.rs/create_v2/buy_v2.)
Quand tu as fini une cible, dis-le à l'utilisateur, il te donnera la suivante.

## ENVIRONNEMENT — lis-le, c'est là qu'on a perdu des heures
- Windows + WSL `Ubuntu-22.04`, utilisateur `nagi`. Le disque WSL est sur D:.
- **Travaille UNIQUEMENT dans `/home/nagi/deepseek/<programme>/`.** Ne compile jamais dans
  `~/pumpre/repo`, `~/pumpre/feesbuild`, `~/pumpround23`, `~/ammresearch`, `~/mayhemrace`,
  `~/pumpresearch`, `~/sharingharness` (agents actifs). Lecture et copie autorisées.
- **N'utilise JAMAIS `cargo-build-sbf --tools-version`** : il change le toolchain partagé et casse les
  builds des autres. Compile avec des **chemins directs** vers `~/.cache/solana/vX.YZ/platform-tools`
  (`RUSTC=$P/rust/bin/rustc`, `CC=$P/llvm/bin/clang`, `AR=$P/llvm/bin/llvm-ar`, `cargo rustc ...`).
  Versions en cache : v1.43 v1.44 v1.45 v1.46.1 v1.52 v1.54.
- Le wrapper `cargo-build-sbf` donne un **layout différent** du `cargo rustc` direct (prouvé sur Fees :
  429/70 contre 577/143). Toujours le build direct.
- Strip toujours avec `~/.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objcopy --strip-all`.
- Écris tes commandes dans un **fichier .sh** et exécute-le ; les variables passées en ligne via
  `wsl bash -c '...'` depuis Windows se font manger par les guillemets.
- **Disque** : un `target/` complet pèse des centaines de Mo. Un seul `CARGO_TARGET_DIR` par programme,
  supprime les dossiers IR/target temporaires quand tu as fini. Ne lance pas de rebuild complet des
  dépendances en IR (c'est ce qui a rempli C: ce matin).

## OUTILS PRÊTS À COPIER (dans ton dossier)
- **Fees** : recette exacte `~/pumpre/feesbuild/build.sh` (v1.44, `cargo rustc` direct, remaps pump-fees-math,
  strip v1.52 → reproduit le hash 39b8fc90…8cae, 577/585). Mesure `~/pumpre/feesbuild/tools/measure.py <symbols.so>`
  (leur métrique : matched / raw / unique_pairs / equal_locations / equal_edges + liste des non appariées).
  Boucle d'essai `tools/try.sh NAME` (build ~22 s + mesure + diff vs baseline ; `MB=m578.json` pour la base 578).
  Patch ATA déjà gagné : `~/pumpre/feesbuild/ir/let_bind.patch` (applique-le d'abord : ta base = 578).
  Outils IR : `~/pumpre/feesbuild/tools/build_ir.sh` (émet LLVM IR + MIR), `ir/fcmp.sh X.ll <symbol> <addr> <size>`
  (diff llc vs déployé), `ir/fstruct.sh` (diff structurel), `ir/swap3.py` (réordonner des blocs dans l'IR).
- **Pump** : `~/pumpresearch/build.sh LABEL [srcdir]` (direct v1.44), `~/pumpresearch/metric/measure.py <orig> <cand> <syms>`,
  `~/pumpresearch/place.py` (met une closure `error!` sur sa ligne déployée sans ajouter de lignes vides avant
  `#[program]`). Source Round23 : `git -C ~/pumpre/repo archive main repro/pump/main-contract-round23-20261027 programs/pump scripts`.
- Désassembleur : `python3 /mnt/d/dev/pumpfun-re/sbftool.py func <so> <addr>` / `callers`.

## LES MÉTHODES QUI ONT MARCHÉ (dans cet ordre)
1. **Build Linux natif** au lieu de leur build macOS : +18 sur PumpSwap, +5 sur Pump, sans toucher la source.
2. **Emplacement des erreurs** : chaque `error!()` grave `file!()` (longueur du chemin) et `line!()` dans le
   code. Remaps `--remap-path-prefix=src/=programs/<prog>/src/` + chaque closure `map_err(|_| error!(X))` sur
   sa ligne déployée (+29 Pump, +31 PumpSwap). Remapper plusieurs fichiers sur un seul casse la résolution
   des modules → déplace le code physiquement ou utilise `#[path]`.
3. **Ordre des blocs (méthode MIR)** : quand le diff est un `jne` fusionné contre `jeq +1; ja`, ou un chemin
   d'erreur dans le mauvais ordre : dumpe l'IR + MIR, réordonne les blocs dans l'IR et passe-le à `llc`
   jusqu'à 0 ligne de diff → ça donne l'ordre cible ; puis trouve la forme source qui crée les blocs dans cet
   ordre. Exemple gagnant (ATA Fees) : `let needs_create = cond; if needs_create {` sur la MÊME ligne.
   Ce qui NE marche PAS : deviner des formes source à l'aveugle (19 essais, 0 gain avant le MIR).

## DISCIPLINE
- **Un changement à la fois**, build, mesure. Garde seulement si la fenêtre cible passe à matched **et**
  qu'aucune autre fenêtre/raw/location/edge ne baisse. Sinon annule.
- Ne déplace jamais les numéros de ligne des autres sites (sinon tu casses leurs Locations).
- Note chaque essai (gardé ou annulé) avec les chiffres avant/après.
- Les deltas statiques peuvent mentir (jgt mayhem, 6088/6092 admin_cto) : seule la mesure tranche.
- Pas de PR chez lalalune, pas de push. Tu commites tes gains en **paquet de recherche** sur une branche
  locale à toi via un worktree hors de `~/pumpre/repo` :
  `git -C ~/pumpre/repo worktree add -b ds-fees-race /home/nagi/deepseek/fees/wt main`
  avec : le patch, `RESULT.txt` (avant/après), le JSON de mesure, la commande de build.

## LIVRABLE À CHAQUE GAIN
Un message court à l'utilisateur : `programme, fenêtre, changement en une ligne, chiffres avant → après,
commit`. Claude recompile depuis ton commit pour confirmer.
