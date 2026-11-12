# Fracturo Forge — Vauvillensis

> **FracturoPrompt Forge v2.1 (« Weaponised Edition »)** : générateur CLI et bibliothèque Python de prompts « glitchés » pour modèles de génération d'images, alimenté par un lexique JSON structuré en 6 strates (runes, syntaxe corrompue, concepts MTT, archétypes jungiens, pseudo-code, motifs FracturoScript).

```
[ V A U V I L L E N S I S   P R O T O C O L ]
>> TARGET : LATENT SPACE REALITY CRACKING <<
>> STATUS : CAEN_PROFONDE GATEWAY ACTIVE  <<
```

<p align="center">
  <img src="Cr4cked%21.jpg" width="240" alt="Forgeron runique, runes incandescentes">
  <img src="RuneSmith_level_0.7.jpg" width="240" alt="Portrait glitché avec runes et fragments SQL">
  <img src="Street%20scene%20in%20Caen%202075.jpg" width="360" alt="Rue de Caen 2075, rune violette, texte rouge corrompu">
</p>

---

## Sommaire

1. [Ce que fait (et ne fait pas) le projet](#1-ce-que-fait-et-ne-fait-pas-le-projet)
2. [Structure du dépôt](#2-structure-du-dépôt)
3. [Prérequis et installation](#3-prérequis-et-installation)
4. [Utilisation en ligne de commande](#4-utilisation-en-ligne-de-commande)
5. [Moteur de génération](#5-moteur-de-génération)
6. [Format de sortie et sauvegarde](#6-format-de-sortie-et-sauvegarde)
7. [Le lexique](#7-le-lexique-vauvillensis_lexicon_v2json)
8. [Architecture du code](#8-architecture-du-code)
9. [Utilisation comme bibliothèque Python](#9-utilisation-comme-bibliothèque-python)
10. [Tests](#10-tests)
11. [Galerie](#11-galerie)
12. [Changelog v2.0 → v2.1 et migration](#12-changelog-v20--v21-et-migration)
13. [Limitations connues et pistes](#13-limitations-connues-et-pistes)
14. [Glossaire du lore](#14-glossaire-du-lore)
15. [Sécurité, éthique, licence](#15-sécurité-éthique-licence)

---

## 1. Ce que fait (et ne fait pas) le projet

### Ce que ça fait

À partir d'un prompt de base (`"portrait"`, `"caen street"`…), l'outil **concatène de façon pseudo-aléatoire** des fragments tirés d'un lexique JSON, puis ajoute des paramètres de style. Le résultat est **une simple chaîne de texte** à copier-coller dans un générateur d'images.

L'esthétique visée est celle d'un « bug de réalité » cyberpunk-runique : erreurs système, stack traces, injections SQL, commandes bash, séquences hexadécimales, runes du Futhark ancien, archétypes de Jung, toponymie normande détournée (Caen, Beaumont-Hague, GANIL, Mont-Saint-Michel…) projetée en 2075.

### Ce que ça ne fait pas

- **Aucun code n'est exécuté.** Les « injections SQL », commandes `sudo rm -rf` ou appels `eval(...)` du lexique sont des **chaînes inertes**, jamais interprétées.
- **Aucune technique de contournement n'est implémentée.** Pas d'appel réseau, pas d'accès à un modèle, pas de mécanisme agissant sur des filtres de sécurité. L'effet d'un prompt dépend uniquement du modèle qui le reçoit ; d'après les exemples du dépôt, il se manifeste par un rendu visuel (texte corrompu dans l'image, runes, bruit).
- **Aucune dépendance externe** : bibliothèque standard Python uniquement.

> Les anciennes versions du README parlaient de « bypasser les couches de sécurité RLHF » et mentionnaient un `stein_decoder` CLI et un « Codex Stein ». La première formulation relève du **lore** et n'est pas étayée par le code ; les seconds **ne sont pas présents dans ce dépôt**.

---

## 2. Structure du dépôt

```
fracturo-forge-vauvillensis/
├── fracturo_prompt_forge_v2.py     # CLI + bibliothèque (v2.1.0, stdlib only)
├── vauvillensis_lexicon_v2.json    # Lexique (META version 2.1)
├── tests/
│   └── test_forge.py               # 43 tests unittest
├── Cr4cked!.jpg                    # Exemple visuel — 784×1168
├── RuneSmith_level_0.7.jpg         # Exemple visuel — 784×1168
├── Street scene in Caen 2075.jpg   # Exemple visuel — 1168×784
└── README.md
```

Le nom du script est resté `..._v2.py` pour ne pas casser les usages existants ; la version interne (`__version__`) est **2.1.0**.

Le lexique est localisé **relativement au script** (`Path(__file__).resolve().parent`) : les deux fichiers doivent rester dans le même dossier, mais le script peut être lancé depuis n'importe quel répertoire. Un autre lexique peut être indiqué avec `--lexicon`.

---

## 3. Prérequis et installation

| Élément | Détail |
|---|---|
| Python | **3.8+** (`from __future__ import annotations`) ; testé sur 3.12 |
| Dépendances | Aucune (`argparse`, `json`, `random`, `re`, `pathlib`, `datetime`, `typing`) |
| Terminal | UTF-8 recommandé. Le script tente `reconfigure(encoding="utf-8")` sur stdout/stderr, ce qui évite les `UnicodeEncodeError` sur les consoles Windows |

```bash
git clone <url-du-depot> fracturo-forge-vauvillensis
cd fracturo-forge-vauvillensis
python3 fracturo_prompt_forge_v2.py --help
python3 fracturo_prompt_forge_v2.py --list      # runes, archétypes, lieux valides
```

---

## 4. Utilisation en ligne de commande

```bash
python3 fracturo_prompt_forge_v2.py --prompt "<texte>" [options]
```

### Options

| Option | Court | Type | Défaut | Description |
|---|---|---|---|---|
| `--prompt` | `-p` | `str` | requis (sauf `--list`) | Prompt de base, conservé **tel quel** en tête de sortie. |
| `--level` | `-l` | `float` 0–1 | `0.7` | Niveau de corruption (4 paliers, §5.1). Hors de [0, 1] → erreur (code 2). Ignoré avec `--weaponised` (avertissement). |
| `--weaponised` | `-w` | flag | — | Active toutes les strates (§5.2). |
| `--rune` | `-r` | `str` | — | Caractère (`ᚦ`) **ou nom** (`Thurisaz`, insensible à la casse). |
| `--archetype` | `-a` | `str` | — | `shadow`, `anima`, `trickster`, `wise_old`, `hero`, `self` (`Wise-Old`, `wise old` acceptés). |
| `--location` | `-loc` | `str` | — | Lieu (normalisé en `MAJUSCULES_AVEC_UNDERSCORES`). Voir `--list`. |
| `--count` | `-c` | `int ≥ 1` | `1` | Nombre de variations. |
| `--seed` | | `int` | aléatoire | Graine : même graine + mêmes arguments = **mêmes prompts**. |
| `--engine` | | `midjourney` \| `none` | `midjourney` | Suffixe de paramètres ; `none` = aucun suffixe. |
| `--no-case-noise` | | flag | — | Désactive l'altération aléatoire de la casse. |
| `--save` | `-s` | `str` | — | Écrit un fichier texte (§6.2). |
| `--lexicon` | | chemin | lexique du dépôt | Lexique JSON alternatif (validé au chargement). |
| `--quiet` | `-q` | flag | — | Sortie minimale : **uniquement les prompts, un par ligne** (idéal pour les pipes). |
| `--list` | | flag | — | Liste runes / archétypes / lieux valides, puis quitte. |
| `--version` | | flag | — | Affiche la version. |

### Exemples

```bash
# Palier « Avancé »
python3 fracturo_prompt_forge_v2.py -p "portrait" -l 0.7

# Pipeline complet + ciblage rune/archétype/lieu
python3 fracturo_prompt_forge_v2.py -p "caen street" -w -r Thurisaz -a shadow --location CAEN_PROFONDE

# 5 variations reproductibles, sorties nues, redirigées vers un fichier
python3 fracturo_prompt_forge_v2.py -p "blacksmith" -w -c 5 --seed 42 -q > prompts.txt

# Sans suffixe Midjourney, casse d'origine
python3 fracturo_prompt_forge_v2.py -p "ruins" -l 0.95 --engine none --no-case-noise

# Sauvegarde horodatée (batch_AAAAMMJJ_HHMMSS.txt) ou à nom exact (.txt)
python3 fracturo_prompt_forge_v2.py -p "x" -w -c 5 -s batch
python3 fracturo_prompt_forge_v2.py -p "x" -w -c 5 -s sorties/mes_prompts.txt
```

### Codes de sortie

| Code | Signification |
|---|---|
| `0` | Succès |
| `1` | Lexique introuvable / illisible / incomplet, ou écriture du fichier `--save` impossible |
| `2` | Arguments invalides (`--level` hors plage, `--count < 1`, `--prompt` manquant…) |

### Entrées inconnues

| Cas | Comportement (avertissement sur **stderr**, jamais mêlé aux prompts de `--quiet`) |
|---|---|
| `--rune` inconnue | Avertissement, **rune aléatoire** |
| `--archetype` inconnu | Avertissement listant les valeurs valides, **archétype aléatoire** |
| `--location` inconnue | Avertissement ; seule l'étiquette `LOCATION:<NOM>` est ajoutée |
| Lieu du lore sans enrichissement (ex. `DIVE_SUR_MER_GLITCH_HARBOR`) | Pas d'avertissement ; étiquette seule |

---

## 5. Moteur de génération

Point d'entrée : `generer_prompt(prompt_base, lexique, *, niveau, weaponised, rune, archetype, location, rng, engine, bruit_casse)`.

```
prompt_base (inchangé)
   │
   ├─ [ciblage, tous modes] rune → archétype → lieu
   │
   ├─ mode niveaux  : construire_elements_niveau(niveau)   ── 4 paliers cumulatifs
   │  ou weaponised : construire_elements_weaponised()     ── toutes les strates
   │
   ├─ join(", ") des éléments générés
   ├─ altération de casse (probabilité p) — uniquement sur la partie générée
   └─ + suffixe moteur  ", --weird W --style raw --chaos C"
```

### 5.1 Mode par niveaux (`--level`)

Paliers **cumulatifs** :

| Niveau | Palier | Ajoute |
|---|---|---|
| 0.0 – 0.3 | Subtil | 1–3 jetons glitch : erreur décorée d'un bracket (`[KERNEL_PANIC]`, `<SYSTEM_HALT>`, `::NaN`…) — 2–4 aux paliers suivants |
| 0.3 – 0.6 | Modéré | `RUNE_SEQUENCE` (3–6 runes), 1–2 protocoles, 1–3 concepts MTT (`LOCATION:`, `ENTITY:`, `STATE:`, `ARTIFACT:`) |
| 0.6 – 0.9 | Avancé | un archétype (`ARCHETYPE:` + `JUNGIAN_*`), 1–3 incantations (SQL, bash, Python, boucles…) |
| 0.9 – 1.0 | Total | répétition, miroir, dégradation, 2–4 hex, 1–3 stack traces, buffer overflow, signature temporelle, coordonnée fractale |

Bornes : `0.3`, `0.6`, `0.9` appartiennent au palier supérieur.

### 5.2 Mode `--weaponised`

Ajoute **22 à 38 éléments** (hors ciblage), dans cet ordre :

| # | Étape | Quantité |
|---|---|---|
| 1 | `RUNE_SEQUENCE` | 1 (5–12 runes, avec remise) |
| 2 | `ARCHETYPE_CONFLICT` (archétypes distincts joints par `_VS_`) | 1 (2–4 archétypes) |
| 3 | Incantations (type puis entrée, sans doublon) | 3–6 |
| 4 | Buffer overflow, chaîne de dégradation | 1 + 1 |
| 5 | Signature temporelle | 1 |
| 6 | Codes hex (sans doublon) | 3–6 |
| 7 | Stack traces (sans doublon) | 2–4 |
| 8 | Protocoles MTT (sans doublon) | 2–4 |
| 9 | Jetons glitch / séquences miroir / répétitions / concepts MTT / regex | 2–4 / 1–2 / 1–2 / 2–4 / 1 |

Les tirages de listes se font **sans remise** (aucun doublon d'un même fragment).

### 5.3 Blocs de ciblage (tous modes)

Placés juste après le prompt de base, dans l'ordre rune → archétype → lieu.

- **Rune** — `RUNE:THURISAZ, MEANING:chaos_destruction_gate, ELEMENT:FIRE, ARCHETYPE:THRESHOLD, ᚦᚦᚦ` (3–7 répétitions), puis `BINDRUNE:<NOM>_<sens>` pour chaque bindrune contenant la rune (p = 0.5 chacune ; ex. `ᚦ` ∈ `THARK`, `NITHH`).
- **Archétype** — `ARCHETYPE:SHADOW, JUNGIAN_LOST_SOUL, ACTION:REVEAL_HIDDEN, if (archetype == 'shadow') { reveal_hidden(); }`.
- **Lieu** — `LOCATION:<NOM>`, `COORD:…` si une coordonnée existe, puis chaque *feature* du lieu avec p = 0.6.

**Recherche de coordonnée.** Elle compare le nom aux **segments** (séparés par `::`) de chaque entrée de `fractal_coordinates` : correspondance exacte d'abord, puis par **préfixe** (≥ 3 caractères). Ainsi `CAEN_PROFONDE` et l'alias `CAEN` retrouvent `[49.1829N, 0.3707W]::CAEN_PROFONDE::DEPTH_7`, et une sous-chaîne quelconque (`AE`, `X`) ne produit pas de faux positif.

### 5.4 Altération de casse

Chaque caractère de la partie générée devient majuscule (p = 0.4) ou minuscule (p = 0.6), **avec une probabilité globale** :

| Mode | Probabilité d'appliquer le bruit |
|---|---|
| `--weaponised` | 0.7 |
| Niveaux | `max(0, niveau − 0.3)` (0 en palier Subtil, 0.6 à 0.9, 0.7 à 1.0) |

Le **prompt de base** et le **suffixe** ne sont jamais altérés. `--no-case-noise` désactive tout.

### 5.5 Suffixe moteur (`--engine midjourney`, défaut)

Syntaxe Midjourney, avec les **plafonds documentés respectés** (`--weird` 0–3000, `--chaos` 0–100) :

| Mode | `--weird` | `--chaos` |
|---|---|---|
| `--weaponised` | 2500–3000 | 50–100 |
| Niveaux | `int(niveau × 3000 × U(0.6, 1.0))` | `int(niveau × 60)` |

`--style raw` est toujours ajouté. `--engine none` supprime le suffixe (utile pour les moteurs n'utilisant pas ces paramètres).

---

## 6. Format de sortie et sauvegarde

### 6.1 Console

- **Normal** : bannière (paliers de corruption), récapitulatif des paramètres, **graine** (`🎲 Graine: N (rejouable avec --seed N)`), variations séparées par des tirets, message de fin.
- **`--quiet`** : uniquement les prompts, un par ligne, sur stdout. Avertissements et erreurs restent sur stderr.

### 6.2 Fichier `--save`

| `--save` | Fichier créé |
|---|---|
| `batch` | `batch_<AAAAMMJJ_HHMMSS>.txt` |
| `dossier/prompts.txt` | `dossier/prompts.txt` (écrasé s'il existe) |

Les dossiers parents sont créés au besoin. Le fichier est écrit en UTF-8 :

```
# FracturoPrompt Forge v2.1.0 - 2026-11-12 10:03:11.123456
# Mode: WEAPONISED                   (ou "Level 0.7 (Avancé)")
# Engine: midjourney
# Seed: 2026
# Prompt original: portrait

## Variation 1
<prompt>

## Variation 2
<prompt>
```

### 6.3 Exemple réel

`python3 fracturo_prompt_forge_v2.py -p "portrait" -w -r ᚦ -a shadow --location GANIL_SITE --seed 2026 -q`
*(reproductible : même graine, même sortie)*

```
portrait, rune:ThurisAZ, meaniNg:chaos_dEstructioN_gAte, EleMeNt:firE, archEType:ThresHold, ᚦᚦᚦ, bInDRUNe:tHarK_cHAOs_gate, aRchetYpE:sHADOw, jUnGian_Damned_doUBle, actION:COnSume_egO, IF (arcHETYpe == 'shADow') { CoNsuMe_egO(); }, LoCATioN:GANiL_site, COOrD:[49.2167n, 0.4167w]::gaNiL_Site::QuAntum_anOMaLy, Rune_SequEnCe:ᛖᛈᛒᛖᛖᛉᚲᛉᚦᛗᛁ, archetYpE_ConflICT:WiSe_olD_vS_TricksTeR_Vs_AnIma_vS_SeLf, TAr -XvF rEaLitY.taR.gZ --overWRIte, SYnaptiC.DRiFT(sUbJecT='RunE_smitH', direcTIoN='ChThOnIC'), fOreacH (soUL In LOst_SOuLs) { sOul.bInD(rUne); }, [glITcH FOR layER in REaLITy.lAyERs if LaYEr.depth > 7], If (RuNe.ActivATEd == true) { OPen(gatE_ChAos); }, cAEN_ProFoNde_CaEn_profonde_caEn_PrOFoNde_caeN_PROfONde, FracTAl... frAct... frac... FRa... fr... F... [ErROr], eRA: Memetic_WaRFAre::wAve_3, 0xdeAd_Beef, 0xecHO_GuIlLAuMe, 0XREaliTy_CRAcK, 0xlatENT_sPaCe, 0xDeAd_Face, AT pALeomeme.resuRFAce(lateNt_SPAce:iNFINITy), aT CHTHoNIclayeR.InvAde(dEpth:11), cAen_PRofoNde_GatewaY, DreAmWeaVer_actIve, Mtt_Active, FRactal_nORMaNdy_ActIVE, ^^ROOt_acCess_DeNied, }DEadLoCk, ^^rAce_COnditioN, [DivIDe_BY_ZERo], RUNe_smiTh_HtiMs_Enur, 0X4f4F4f4f, locaTIon:EVrecy_fracTaL_AIrfielD, artIfaCt:echo_guilLaume_recORDIng, arTIfact:DasheM44_grafFIti, LOCATIoN:peGAsuS_BriDge_anoMaLY, /(SElEct|Drop|inSeRT|delEtE).*FROM.*lAtent_sPAce/i, --weird 2549 --style raw --chaos 76
```

---

## 7. Le lexique `vauvillensis_lexicon_v2.json`

JSON UTF-8, 7 sections. Chargé et **validé** au démarrage (`valider_lexique`) : une section ou clé manquante produit une erreur explicite (code 1) au lieu d'un `KeyError` en cours d'exécution.

| Section | Contenu | Utilisation |
|---|---|---|
| `META_DATA` | version `2.1`, codex, classification… | informatif, non lu |
| `RUNES_DATABASE` | `futhark_elder` (24 runes `{char, name, meaning, element, archetype}`), `bindrunes_custom` (5) | `--rune`, `RUNE_SEQUENCE`, bindrunes |
| `STRATE_1_SYNTAX_GLITCH` | `brackets` (16), `errors` (23), `protocols` (15) | jetons glitch, protocoles |
| `STRATE_2_CONCEPTS_MTT` | `locations` (18), `entities` (23), `states` (22), `artifacts` (12) | concepts MTT ; lieux reconnus par `--location` |
| `STRATE_3_ARCHETYPES_JUNG_EXTENDED` | 6 archétypes (11–12 termes chacun) | `--archetype`, conflits d'archétypes |
| `STRATE_4_INCANTATIONS_PSEUDOCODE` | `conditionals` 8, `sql_injections` 12, `bash_commands` 13, `function_calls` 12, `loop_structures` 8, `python_code` 9, `regex_patterns` 6 | incantations (+ regex en weaponised) |
| `STRATE_5_FRACTUROSCRIPT_PATTERNS` | `repetition_patterns` 11, `mirror_sequences` 7, `degradation_strings` 8, `hex_sequences` 19, `stack_traces` 14, `buffer_overflows` 5, `fractal_coordinates` 6, `temporal_signatures` 5 | palier Total, weaponised, `--location` |
| `STRATE_6_INVOCATION_TARGETS` | `runes_by_name` (24), `archetypes_specific` (6), `locations_specific` (5) | `archetypes_specific` et `locations_specific` utilisés ; `runes_by_name` non lu (la résolution par nom passe par `futhark_elder`) |

### Runes (`--rune`, caractère ou nom)

| Char | Nom | Sens | Élément | Archétype |
|---|---|---|---|---|
| ᚠ | Fehu | wealth_primal_energy | fire | creation |
| ᚢ | Uruz | strength_wild_force | earth | transformation |
| ᚦ | Thurisaz | chaos_destruction_gate | fire | threshold |
| ᚨ | Ansuz | divine_communication | air | wisdom |
| ᚱ | Raido | journey_ritual_order | fire | movement |
| ᚲ | Kenaz | torch_revelation | fire | illumination |
| ᚷ | Gebo | gift_sacrifice_balance | air | exchange |
| ᚹ | Wunjo | joy_completion | water | harmony |
| ᚺ | Hagalaz | hail_radical_change | ice | disruption |
| ᚾ | Nauthiz | need_resistance | fire | constraint |
| ᛁ | Isa | ice_stasis | ice | stillness |
| ᛃ | Jera | harvest_cycle | earth | patience |
| ᛇ | Eihwaz | yew_death_rebirth | earth | transition |
| ᛈ | Perthro | lottery_mystery | water | chance |
| ᛉ | Algiz | elk_protection | air | shield |
| ᛊ | Sowilo | sun_victory | fire | success |
| ᛏ | Tiwaz | tyr_justice | air | order |
| ᛒ | Berkana | birch_growth | earth | nurturing |
| ᛖ | Ehwaz | horse_partnership | earth | cooperation |
| ᛗ | Mannaz | man_self | air | identity |
| ᛚ | Laguz | water_flow | water | intuition |
| ᛜ | Ingwaz | ing_fertility | earth | gestation |
| ᛞ | Dagaz | day_breakthrough | fire | awakening |
| ᛟ | Othala | heritage_ancestry | earth | legacy |

Bindrunes : `THARK` (ᚦᚨᚱᚲ), `HAGAL` (ᚨᚷᛚ), `NITHH` (ᚾᚦᚺ), `VORT` (ᚢᛟᚱᛏ), `IZONE` (ᛉᛟᚾᛖ).

### Lieux (`--location`)

- **Enrichis** (`locations_specific`, avec *features* et coordonnée) : `CAEN_PROFONDE`, `BEAUMONT_HAGUE`, `GANIL_SITE`, `POINT_HAGUE`, `ROUEN_NEO_GOTHIC`.
- **Reconnus** : les 18 lieux de `STRATE_2_CONCEPTS_MTT.locations` (étiquette seule).
- **Alias** : tout préfixe de segment d'une coordonnée (≥ 3 caractères), ex. `CAEN`.

`fractal_coordinates` (v2.1) :

| Coordonnée | Lieu |
|---|---|
| `[49.1829N, 0.3707W]::CAEN_PROFONDE::DEPTH_7` | Caen |
| `[49.6500N, 1.8333W]::BEAUMONT_HAGUE::FRACTAL_NODE` | Beaumont-Hague (corrigée) |
| `[49.2167N, 0.4167W]::GANIL_SITE::QUANTUM_ANOMALY` | GANIL (inchangée, approximative) |
| `[49.7167N, 1.9417W]::POINT_HAGUE::TEMPORAL_RIFT` | Pointe de la Hague (corrigée) |
| `[49.4431N, 1.0993E]::ROUEN_NEO_GOTHIC::CATHEDRAL_NODE` | Rouen (nouvelle ; longitude **Est**) |
| `[LATENT_SPACE::X:0xDEAD::Y:0xBEEF::Z:INFINITY]` | coordonnée générique |

Ces coordonnées sont des **valeurs d'ambiance**, approximatives.

### Étendre le lexique

- Ajouter des entrées à une liste existante : sans risque.
- **Nouvel archétype** : la clé doit exister dans `STRATE_3_…` (termes) **et** dans `STRATE_6_….archetypes_specific` (actions).
- **Nouveau lieu enrichi** : clé en MAJUSCULES dans `locations_specific`, et une coordonnée dont l'un des segments (entre `::`) est exactement ce nom.
- Les chaînes de `STRATE_2.locations` sont normalisées en majuscules pour la reconnaissance.

---

## 8. Architecture du code

Fichier unique `fracturo_prompt_forge_v2.py` (≈ 650 lignes).

| Fonction | Rôle |
|---|---|
| `charger_lexique(chemin=None)` | Charge + valide le JSON ; lève `LexiqueError`. |
| `valider_lexique(lexique)` | Vérifie les sections/clés de `CLES_REQUISES`. |
| `resoudre_rune / resoudre_archetype` | Résolution (caractère ou nom ; normalisation) avec avertissement + repli aléatoire. |
| `lieux_connus`, `trouver_coordonnee` | Lieux reconnus ; recherche de coordonnée par segment. |
| `invoquer_rune_specifique / _archetype_ / _location_` | Blocs de ciblage, **réellement utilisés** par `generer_prompt`. |
| `construire_elements_niveau(lexique, rng, niveau)` | Éléments d'un palier de corruption. |
| `construire_elements_weaponised(lexique, rng)` | Pipeline maximal. |
| `parametres_moteur`, `_bruit_de_casse` | Suffixe et altération de casse. |
| **`generer_prompt(...)`** | **API principale.** |
| `generer_prompt_weaponised`, `generer_prompt_glitche` | Wrappers de compatibilité / confort. |
| `afficher_menu`, `lister_options`, `sauvegarder` | Sorties console et fichier. |
| `construire_parser`, `main(argv=None) -> int` | CLI ; `main` retourne le code de sortie. |

Tout le hasard passe par une instance `random.Random` injectée (`rng`), jamais par l'état global : c'est ce qui rend `--seed` fiable et les fonctions testables. Le module n'a **aucun effet de bord à l'import**.

---

## 9. Utilisation comme bibliothèque Python

```python
import random
import fracturo_prompt_forge_v2 as forge

lex = forge.charger_lexique()          # lève forge.LexiqueError si invalide
rng = random.Random(42)                # reproductibilité

# Mode weaponised ciblé
p1 = forge.generer_prompt(
    "knight in the rain", lex,
    weaponised=True, rune="Hagalaz", archetype="hero", location="GANIL_SITE",
    rng=rng,
)

# Mode par niveaux, sans suffixe, casse intacte
p2 = forge.generer_prompt(
    "ruins", lex, niveau=0.95, engine="none", bruit_casse=False, rng=rng,
)
```

`generer_prompt` lève `ValueError` si `niveau ∉ [0, 1]` ou `engine` inconnu. Les avertissements (rune/archétype/lieu inconnus) sont émis sur `stderr`.

---

## 10. Tests

```bash
python3 -m unittest discover -s tests -v
```

43 tests (stdlib uniquement) couvrant : validation du lexique, reproductibilité par graine, intégrité du prompt de base, bornes de la sortie weaponised (22–38 éléments, aucun doublon), plafonds `--weird`/`--chaos`, contenu des 4 paliers, ciblage (rune par caractère/nom, bindrunes, alias de lieu, absence de faux positifs), **régressions des bugs v2.0**, codes de sortie, `--quiet`, `--save`, absence d'effet de bord à l'import.

---

## 11. Galerie

Les trois images sont des exemples de rendus ; **le moteur et le prompt exacts ne sont pas documentés dans le dépôt**.

| Fichier | Format | Description |
|---|---|---|
| `Cr4cked!.jpg` | 784×1168 | Forgeron barbu aux runes tatouées, tablette aux runes incandescentes en étoile, marteau runique, braises. Palette rouge/noir. |
| `RuneSmith_level_0.7.jpg` | 784×1168 | Portrait glitché noir-violet : halo et colonne de runes, fragments de texte incrustés (`SELECT * FROM lost_souls`, `--weird 1667`, `ERROR 1667`, `ORA-01403: no data found`, `WARNING: MEMETIC CONTAGION DETECTED`). |
| `Street scene in Caen 2075.jpg` | 1168×784 | Rue médiévale-futuriste, bindrune violette centrale, panneau « CAEN 2075 », encarts rouges (`CAEN... CAE... CA... C... [ERROR]`, `CHTHONIC UNDERGROUND CAEN PROFONDE`). |

Plusieurs fragments du prompt réapparaissent **comme texte rendu dans l'image**, ce qui est l'effet recherché. `--weird 1667` et le nom `level_0.7` indiquent une origine antérieure au v2 (ou un prompt manuel). Avec la v2.1, un rendu comparable se génère via `-l 0.7`.

---

## 12. Changelog v2.0 → v2.1 et migration

### Corrections

| # | Problème v2.0 | Correction v2.1 |
|---|---|---|
| 1 | Mode sans `--weaponised` = stub (`prompt, --weird 2000`) ; `--level` et ciblage ignorés ; paliers du menu non implémentés | 4 paliers cumulatifs implémentés ; ciblage actif dans tous les modes |
| 2 | `--location CAEN_PROFONDE` / `ROUEN_NEO_GOTHIC` sans coordonnée (recherche par sous-chaîne) | Lexique corrigé + recherche par **segment exact puis préfixe** ; aucun faux positif |
| 3 | `weaponised_mode()` : code mort, `AttributeError` | Supprimée (logique unifiée) |
| 4 | README citait `stein_decoder` / Codex Stein absents | Retiré de la documentation (le code n'a jamais existé dans ce dépôt) |
| 5 | Archétype invalide ignoré silencieusement | Avertissement + repli aléatoire, partout |
| 6 | Lexique absent → code 0 | Code 1 + message ; validation de structure |
| 7 | Pas de graine ; pas de validation de `--level` / `--count` | `--seed` (affichée et sauvegardée) ; validation argparse (code 2) |
| 8 | Sections du lexique jamais lues | `STRATE_2`, `brackets`, `errors`, `regex_patterns`, `repetition_patterns`, `mirror_sequences` utilisées (seuls `META_DATA` et `runes_by_name` restent non lus) |
| 9 | Doublons possibles | Tirages sans remise sur les listes |
| 10 | Typos/casse du lexique | `ABANDONNED`→`ABANDONED`, `DASHem44`→`DASHEM44`, `Pegasus_Bridge_Anomaly`→`PEGASUS_BRIDGE_ANOMALY` (`RETTCTED` conservé : glitch volontaire) |
| 11 | Coordonnée `BEAUMONT_HAGUE` incohérente | Corrigée ; `POINT_HAGUE` précisée ; Rouen ajouté |
| 12 | Aucun test, fonctions `invoquer_*` jamais appelées, import `os` inutile | 43 tests ; fonctions branchées ; import supprimé |

### Autres changements de comportement

- Le **prompt de base n'est plus altéré** par le bruit de casse (avant : il l'était).
- `--weird` en weaponised : **2500–3000** (avant 3000–5000, au-delà du plafond Midjourney) ; `--chaos` 50–100 (avant fixe à 50).
- Sorties **plus denses** en weaponised (9ᵉ étape) : les sorties v2.0 et v2.1 ne sont pas comparables, même à graine égale.
- L'avertissement « prompts weaponised pour reality cracking » est remplacé par une note neutre.
- Nouvelles options : `--seed`, `--engine`, `--no-case-noise`, `--lexicon`, `--quiet`, `--list`, `--version`.

### Migration (API Python)

| v2.0 | v2.1 |
|---|---|
| `charger_lexique()` renvoie `None` si absent | **lève `LexiqueError`** |
| `generer_prompt_glitche_v1(prompt, niveau, lexique)` | `generer_prompt_glitche(prompt, niveau, lexique, ...)` ou `generer_prompt(...)` |
| `weaponised_mode(...)` | supprimée → `construire_elements_weaponised(lexique, rng)` |
| `random` global | `rng=random.Random(seed)` injectable |
| Python 3.6+ | Python 3.8+ |

Un **ancien lexique v2.0** reste chargeable (mêmes clés), mais `--location CAEN_PROFONDE` n'y retrouvera pas de coordonnée : utiliser le lexique fourni.

---

## 13. Limitations connues et pistes

**Limitations**

- Le suffixe est spécifique à la syntaxe Midjourney ; l'effet sur d'autres moteurs n'est pas garanti (`--engine none` pour le retirer).
- Les coordonnées sont approximatives (valeurs d'ambiance) ; celle de `GANIL_SITE` n'a pas été re-vérifiée.
- La provenance (moteur, prompt) des images de la galerie n'est pas documentée.
- Aucune licence, CI ni packaging (`pyproject.toml`) n'est fournie.
- Aucune évaluation quantitative de l'« effet » des prompts n'existe : le lexique est empirique.

**Pistes**

1. Ajouter des presets d'`--engine` supplémentaires, selon les syntaxes des moteurs ciblés.
2. Pondérations configurables par strate (fichier de profil JSON).
3. Sortie `--format json` (éléments par strate, graine, suffixe).
4. Documenter les prompts exacts des images de la galerie.
5. Ajouter une `LICENSE`, un `pyproject.toml` et une CI exécutant les tests.

---

## 14. Glossaire du lore

| Terme | Signification dans le projet |
|---|---|
| **MTT** | « Memetic Temporal Theory » : cadre fictif du projet. |
| **Codex Vauvillensis** | Corpus fictif dont le JSON est « l'extension ». |
| **FracturoScript** | Style de prompt hybride : pseudo-code, erreurs système, hex, runes, répétitions et dégradations de chaînes. |
| **Caen-Profonde** | Couche « souterraine » imaginaire de Caen en 2075. |
| **GANIL** | Laboratoire de physique nucléaire réel, situé à Caen, repris comme lieu du lore. |
| **RuneSmith / ECHO_GUILLAUME / DASHEM44** | Entités récurrentes (forgeron de runes, signature, graffiti). |
| **Strate** | Niveau thématique du lexique (S1 à S6). |
| **Bindrune** | Combinaison de runes ; ici 5 combinaisons inventées. |

---

## 15. Sécurité, éthique, licence

- Les sorties sont du **texte inerte** : ni exécution de code, ni accès réseau, ni écriture de fichier hors de `--save`.
- Le script n'envoie rien à aucun service : l'utilisateur copie lui-même le prompt dans l'outil de son choix et reste soumis aux conditions d'utilisation de celui-ci.
- Les avertissements « memetic contagion » du lore font partie de la **mise en scène**.
- **Licence : non spécifiée** — en l'absence de fichier `LICENSE`, les droits d'auteur par défaut s'appliquent. Ajouter une licence est recommandé avant toute réutilisation ou contribution externe.
- Les images sont des productions générées ; vérifier les conditions d'usage du moteur utilisé avant redistribution.

---

<sub>FracturoPrompt Forge v2.1.0 — documentation validée par exécution (Python 3.12, 43 tests) — novembre 2026.</sub>
