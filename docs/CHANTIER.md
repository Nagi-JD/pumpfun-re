# Chantier bit-à-bit — tâches claimables

Objectif : **byte-for-byte (whole-ELF)** sur les programmes core, en commençant par **pump**.
Le per-site est épuisé ; ce qui reste est la reconstruction de la **structure source**, source de
dérive par source de dérive. Contexte complet : [`WHOLE_ELF_FRONTIER.md`](WHOLE_ELF_FRONTIER.md).

**Base de mesure (pump, profil s7p) :** **802 normalized / 161 raw** / 1035 (après la chaîne
vérifiée #22–#32, mergée le 28 oct — partie de 786/137).
**Cible de la course :** rattraper lalalune, désormais à **823 / 203 raw** (Round-37, 28 oct).

## Règles (toutes les tâches)

- **PR-only.** Un claim = une issue/PR = un packet `research/chantier-<id>/`.
- **Mesure obligatoire** avant/après : matched, raw, `lost[]` (matched ET raw). Pas de chiffre sans JSON.
- **Garde-fou :** revert si le raw baisse **ou** si le normalized passe sous 786.
- **Fidèle au déployé :** aucun check ajouté/retiré, aucun changement de comportement.
- **Ne pas re-tenter** (mesuré mort) : reorder `ordered.ld` seul, `mergefunc`, `codegen-units`,
  `share-generics=on`.
- Pas de `.so` ni de secrets committés.

## Outils

- **Solveur de dérive** : pour chaque intervalle entre deux fonctions appariées,
  `Δ = taille_candidat − taille_déployé` ; `Δ_call = Σ Δ` entre caller et callee ; une fenêtre est
  raw-able **ssi tous ses `Δ_call = 0`**. Il classe chaque source de dérive par nombre de raw débloqués.
  → **Tâche T0** ci-dessous : le publier comme outil réutilisable.
- `tools/sbftool.py` — désassembleur sBPF (diff de corps, ordre des symboles, tailles).

---

## T0 — Publier le solveur de dérive (prérequis, outil)

Porter le solveur en `tools/drift_solver.py` : entrée = `deployed.so` + `candidate-symbols.so`,
sortie = (a) potentiel raw si Δ=0, (b) classement des fonctions/intervalles qui gâtent le plus de raw,
(c) premier Δ≠0 en ordre d'adresse (racine). Doit reproduire sur s7clean : **238** fenêtres call-only,
potentiel **137 → 375**, racine = `with_values` @ 0x11b0/0x1c40/0x2178.
**Livrable :** outil + JSON de référence. **Effort :** S.

## T1 — Racine `with_values` : 3 monomorphs → 1 (priorité #1)

Notre build émet 3 monomorphs de `anchor_lang::error::Error::with_values` (1336 B chacun,
`h5fec…`/`h95410…`/`h970a…`), le déployé en a **un** (0x11b0). +2672 B de dérive dès le début du `.text`.
Répartition des call-sites : 0x11b0 → 14 (handlers/legacy/init), 0x1c40 → 22
(set_params/buy_v2/sell_v2/trade), 0x2178 → 4 (cluster 0x15e748).

1. **Diagnostic** : quel paramètre générique sépare les 3 instanciations (types concrets passés par
   chaque groupe d'error-sites) ? Combien de types distincts le déployé utilise-t-il ?
2. **Reshape** : faire converger les 40 call-sites vers **une seule** instanciation, behavior-preserving
   (même code d'erreur, même ligne baked, même variante).
3. Mesurer. Attention : les closures `error!` placées pour le normalized sont la source probable des
   instanciations en trop — le normalized est le garde-fou.

**Livrable :** patch + mesure. **Effort :** L. **Gain attendu :** supprime la dérive racine (cross-root calls).

## T2 — Cartographier toutes les sources de dérive (après T0)

Avec le solveur, après T1 : lister **chaque** intervalle Δ≠0 restant, trié par raw débloqués, et
classer chaque source : `monomorph` / `wrapper Anchor` / `taille de fonction source` / `data-reloc`.
**Livrable :** `research/chantier-T2/drift-map.json` + table. **Effort :** M. Alimente T3–T5.

## T3 — Wrappers Anchor (`try_accounts` / `try_deserialize`)

> **MÉTHODE PROUVÉE : [`docs/WRAPPER_RECONSTRUCTION.md`](WRAPPER_RECONSTRUCTION.md)** — lalalune a
> atteint le whole-ELF Fees (585/585) en reconstruisant exactement ces wrappers. **Notre verdict
> « whole-ELF, non éditable » était faux** : le wrapper est une fonction déterministe de
> (version macro Anchor) × (ordre des champs) × (type des champs) × (contraintes). On reconstruit le
> `#[derive(Accounts)]` struct, jamais l'ELF.

Les gros gateurs (≈154 fenêtres chacun) : `LegacyBuy::try_accounts` (8128 B), `Create::try_accounts`
(6672 / 6464 B), `Initialize::try_accounts` (5896 B), `IdlAccount::try_deserialize` / `Global::try_deserialize`
(728 B). Recette : diff généré vs désassemblage → attribuer chaque écart à {ordre, type, contrainte,
version macro} → changer ce construct exact → rebuild → re-diff. **Deux leviers clés** :
- **champ `AccountInfo` possédé** (vs emprunté) → décale les offsets du `exit`/parser généré ;
- **`&UncheckedAccount` (pas `&AccountInfo`) passé aux helpers** → tue la divergence regalloc par
  noalias dans les corps de handler (`let x: &AccountInfo = x.as_ref();`).

**Un sous-claim par instruction.** **Effort :** L chacun.

**→ Spec complète et claimable : [`docs/T3_WRAPPERS.md`](T3_WRAPPERS.md)** (prérequis macro vendored,
cibles à confirmer au solveur, recette par wrapper, protocole de mesure, découpage en sous-claims).

## T4 — Tailles de fonctions source (Δ résiduels)

Pour chaque fonction appariée-normalisée dont la **taille** diffère encore (les ~21 % hors match de taille)
et qui gâte du raw selon T2 : égaliser la taille (inline/outline, `#[inline(never)]`, forme closure,
split/merge) sans casser la signature normalisée.
**Effort :** M par fonction. Prioriser par raw débloqués.

## T5 — Data / relocations (`lddw`)

Les cibles `lddw` (`.rodata` / `.data.rel.ro` : Location records, strings, discriminants, tables d'erreurs)
ont une adresse = cumul des enregistrements précédents. Énumérer les enregistrements déployé vs candidat,
mapper chacun à son origine source, reproduire **ordre + taille** (ordre des strings, dédup, tables).
**Livrable :** carte data + patch. **Effort :** L. Débloque les fenêtres raw-fail à diff `lddw`.

## T6 — Couche de layout whole-ELF (après T1–T5)

> Pas « juste un reorder ». Le whole-ELF Fees de lalalune a nécessité une **couche de layout**
> complète (voir [`WRAPPER_RECONSTRUCTION.md`](WRAPPER_RECONSTRUCTION.md) §d). À porter sur pump :
> 1. `ordered.ld` appliqué via un **wrapper de linker** autour de `rust-lld` (on l'a déjà sur s7clean) ;
> 2. **`relayout.py`** — régénère `ordered.ld` après **chaque** changement source (bind par nom /
>    identité de contenu / graphe d'appels) ; chaque edit = un re-bind. ← **à construire** ;
> 3. **macro `anchor-attribute-program` vendored avec `#[used]`, Anchor 0.32.1** — les crates stock
>    crates.io ne reproduisent pas les bytes de wrapper. ← **prérequis dur, à vérifier/vendorer** ;
> 4. **padding par lignes blanches** pour préserver les numéros de ligne (ils alimentent les records
>    `.rodata` Source/Location → load-bearing) ;
> 5. **`--gc-sections`** pour supprimer tout helper candidat-only non appelé (égalise le compte de fenêtres).
>
> Reorder seul, tant que Δ≠0, est **inutile** (mesuré : −9 raw). **Effort :** L.

## T7 — Porter sur PumpSwap (après succès pump)

PumpSwap n'a **pas** de levier d'ordre aujourd'hui (build `cargo rustc` nu). Porter le profil
text-layout (`RUSTC_WRAPPER` + `ordered.ld` + shim host) sur `pump_amm`, puis rejouer T0→T6.
Plafond estimé par ordre seul ≈ +100 raw ; 333 fenêtres exigent T5 (data/reloc).
**Effort :** L.

---

## Tableau de bord

| Tâche | Statut | Owner | Raw avant → après |
|---|---|---|---|
| T0 solveur | **merged** (#22) | Shuai-Qing | — |
| T1 with_values | superseded | — | (root is `with_account_name`, addressed by #24) |
| T2 drift map | **merged** (#23) | Shuai-Qing | — |
| T3 wrappers | open (method ready) | — | — |
| T4 tailles | **merged #24–#32** | Shuai-Qing | 137 → **161** |
| T5 data/reloc | open | — | — |
| T6 layout (relayout+anchor vendored) | open | — | — |
| T7 PumpSwap | blocked (pump) | — | — |

Next: **T6 infra** (relayout.py + vendored Anchor 0.31.2 `#[used]` macro — we already have it from Fees) is the enabler for T3/T5; a measured "wire vendored macro into pump" experiment is in flight.

Pour claimer : ouvre une issue `chantier: T<n> <titre>` puis une PR avec le packet mesuré.
