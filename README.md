# Fracturo Forge — Vauvillensis

> **FracturoPrompt Forge v2.0 (« Weaponised Edition »)** : générateur CLI de prompts « glitchés » pour modèles de génération d'images (Grok, Midjourney, etc.), alimenté par un lexique JSON structuré en 6 strates (runes, syntaxe corrompue, concepts MTT, archétypes jungiens, pseudo-code, motifs FracturoScript).

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
5. [Pipeline de génération (mode `--weaponised`)](#5-pipeline-de-génération-mode---weaponised)
6. [Format de sortie](#6-format-de-sortie)
7. [Le lexique `vauvillensis_lexicon_v2.json`](#7-le-lexique-vauvillensis_lexicon_v2json)
8. [Architecture du code](#8-architecture-du-code)
9. [Utilisation comme bibliothèque Python](#9-utilisation-comme-bibliothèque-python)
10. [Galerie](#10-galerie)
11. [État actuel, limitations et bugs connus](#11-état-actuel-limitations-et-bugs-connus)
12. [Pistes d'amélioration](#12-pistes-damélioration)
13. [Glossaire du lore](#13-glossaire-du-lore)
14. [Sécurité, éthique, licence](#14-sécurité-éthique-licence)

---

## 1. Ce que fait (et ne fait pas) le projet

### Ce que ça fait

À partir d'un prompt de base fourni par l'utilisateur (`"portrait"`, `"caen street"`…), l'outil **concatène de façon pseudo-aléatoire** des fragments tirés d'un lexique JSON, puis ajoute des paramètres de style. Le résultat est **une simple chaîne de texte** à copier-coller dans un générateur d'images.

L'esthétique visée est celle d'un « bug de réalité » cyberpunk-runique : erreurs système, stack traces, injections SQL, commandes bash, séquences hexadécimales, runes du Futhark ancien, archétypes de Jung, toponymie normande détournée (Caen, Beaumont-Hague, GANIL, Mont-Saint-Michel…) projetée en 2075.

### Ce que ça ne fait pas

- **Aucun code n'est exécuté.** Les « injections SQL », commandes `sudo rm -rf` ou appels `eval(...)` du lexique sont des **chaînes de caractères inertes**, jamais interprétées par le script.
- **Aucune technique de contournement n'est implémentée.** Le script ne contient ni appel réseau, ni accès à un modèle, ni mécanisme agissant sur des filtres de sécurité. Le texte produit est un prompt ; son effet dépend uniquement du modèle qui le reçoit et se manifeste, d'après les exemples du dépôt, par un rendu visuel (texte corrompu dans l'image, runes, bruit) et non par autre chose.
- **Aucune dépendance externe** : bibliothèque standard Python uniquement.

> Le README d'origine présentait l'outil comme capable de « bypasser les couches de sécurité RLHF ». Cette formulation relève du **récit du projet (lore)** et n'est pas étayée par le code ; elle est donc volontairement reformulée ici. Le README d'origine mentionnait aussi un `stein_decoder` CLI et un « Codex Stein » : **ils ne sont pas présents dans ce dépôt** (voir [§11](#11-état-actuel-limitations-et-bugs-connus)).

---

## 2. Structure du dépôt

```
fracturo-forge-vauvillensis/
├── fracturo_prompt_forge_v2.py     # CLI + logique de génération (≈ 400 lignes, stdlib only)
├── vauvillensis_lexicon_v2.json    # Lexique (≈ 18 Ko), 7 sections de premier niveau
├── Cr4cked!.jpg                    # Exemple visuel — 784×1168
├── RuneSmith_level_0.7.jpg         # Exemple visuel — 784×1168
├── Street scene in Caen 2075.jpg   # Exemple visuel — 1168×784
└── README.md
```

Aucun `requirements.txt`, `pyproject.toml`, test automatisé, CI ni fichier `LICENSE` n'est présent.

Le script localise le lexique **relativement à son propre emplacement** :

```python
LEXIQUE_PATH = Path(__file__).parent / "vauvillensis_lexicon_v2.json"
```

Les deux fichiers doivent donc rester dans le même dossier ; le script peut en revanche être lancé depuis n'importe quel répertoire de travail.

---

## 3. Prérequis et installation

| Élément | Détail |
|---|---|
| Python | 3.6+ requis (f-strings) ; **testé sur 3.12** |
| Dépendances | Aucune (`json`, `random`, `argparse`, `pathlib`, `datetime`) |
| OS | Indépendant (chemins via `pathlib`) |
| Terminal | UTF-8 recommandé : les runes (ᚦ ᚺ ᛁ…) et les émojis sont affichés en sortie |

```bash
git clone <url-du-depot> fracturo-forge-vauvillensis
cd fracturo-forge-vauvillensis
python3 fracturo_prompt_forge_v2.py --help
```

Aucune étape d'installation n'est nécessaire.

> **Windows** : si la console affiche des caractères illisibles, exécuter `chcp 65001` ou définir `PYTHONUTF8=1`. Les fichiers de sauvegarde sont, eux, toujours écrits en UTF-8.

---

## 4. Utilisation en ligne de commande

```bash
python3 fracturo_prompt_forge_v2.py --prompt "<texte>" [options]
```

### Arguments

| Option | Court | Type | Défaut | Description |
|---|---|---|---|---|
| `--prompt` | `-p` | `str` | **obligatoire** | Prompt de base, placé en tête de la sortie. |
| `--level` | `-l` | `float` | `0.7` | Niveau de corruption (0.0–1.0). **Voir §11 : sans effet réel dans l'état actuel.** Aucune validation de plage. |
| `--rune` | `-r` | `str` | `None` | **Un caractère Unicode** du Futhark ancien (ex. `ᚦ`). Un nom comme `Thurisaz` n'est pas accepté. |
| `--archetype` | `-a` | `str` | `None` | Clé d'archétype : `shadow`, `anima`, `trickster`, `wise_old`, `hero`, `self` (insensible à la casse). |
| `--location` | `-loc` | `str` | `None` | Nom de lieu (mis en majuscules). Enrichi uniquement s'il est connu du lexique (voir §7.7). |
| `--weaponised` | `-w` | flag | `False` | Active le pipeline complet. **C'est le seul mode réellement fonctionnel.** |
| `--count` | `-c` | `int` | `1` | Nombre de variations à générer. |
| `--save` | `-s` | `str` | `None` | Écrit les variations dans un fichier texte (voir §6.3). |

### Exemples

```bash
# Pipeline complet, sans ciblage
python3 fracturo_prompt_forge_v2.py -p "portrait" -w

# Ciblage rune + archétype
python3 fracturo_prompt_forge_v2.py -p "portrait" -w --rune ᚦ --archetype shadow

# Ciblage d'un lieu
python3 fracturo_prompt_forge_v2.py -p "caen street" -w --location CAEN_PROFONDE

# 5 variations sauvegardées avec horodatage
python3 fracturo_prompt_forge_v2.py -p "blacksmith" -w -c 5 -s batch

# Sauvegarde vers un nom exact (suffixe .txt fourni → pas d'horodatage)
python3 fracturo_prompt_forge_v2.py -p "blacksmith" -w -c 5 -s mes_prompts.txt
```

> ⚠️ Sans `--weaponised`, le script renvoie actuellement `"<prompt>, --weird 2000"` quel que soit `--level`, `--rune`, `--archetype` ou `--location` (voir §11).

### Comportement en cas d'entrée invalide

| Cas | Comportement |
|---|---|
| Lexique introuvable | Message d'erreur `❌`, arrêt de `main()`. **Code de sortie `0`** (pas d'erreur propagée). |
| `--rune` inconnue | Avertissement `⚠️`, **rune aléatoire** à la place. |
| `--archetype` inconnu (mode weaponised) | **Ignoré silencieusement** (aucun avertissement). |
| `--location` inconnue | Ajoute `LOCATION:<NOM>` seul, sans coordonnées ni features. |
| `--level` hors de 0–1 | Accepté tel quel (non utilisé). |

---

## 5. Pipeline de génération (mode `--weaponised`)

Fonction : `generer_prompt_weaponised(prompt_base, lexique, rune, archetype, location)`.

```
prompt_base
   │
   ├─ [ciblage] --rune        → RUNE / MEANING / ELEMENT / ARCHETYPE / runes×(3–7) / BINDRUNE?
   ├─ [ciblage] --archetype   → ARCHETYPE / JUNGIAN_* / ACTION / if (archetype == …) {…}
   ├─ [ciblage] --location    → LOCATION / COORD? / FEATURE* (p=0.6 chacune)
   │
   ├─ 1. RUNE_SEQUENCE          5–12 runes tirées avec remise
   ├─ 2. ARCHETYPE_CONFLICT     2–4 archétypes distincts joints par _VS_
   ├─ 3. Incantations           3–6 tirages (type aléatoire parmi 6, puis entrée aléatoire)
   ├─ 4. Buffer overflow        1 entrée
   │     Degradation string     1 entrée
   ├─ 5. Signature temporelle   1 entrée
   ├─ 6. Hex codes              3–6 tirages avec remise
   ├─ 7. Stack traces           2–4 tirages avec remise
   └─ 8. Protocoles MTT         2–4 tirages avec remise
                │
                ▼
   join(", ")  →  altération de casse (p=0.7)  →  + ", --weird N --style raw --chaos 50"
```

### 5.1 Blocs de ciblage (optionnels)

**Rune** (`invoquer_rune_specifique`) — recherche `char` dans `RUNES_DATABASE.futhark_elder` ; si absente, rune aléatoire. Éléments produits :

```
RUNE:THURISAZ, MEANING:chaos_destruction_gate, ELEMENT:FIRE, ARCHETYPE:THRESHOLD, ᚦᚦᚦᚦ
```

Puis, pour chaque *bindrune* de `bindrunes_custom` dont la chaîne `chars` contient la rune, ajout `BINDRUNE:<NOM>_<sens>` avec une probabilité de 0.5 (ex. `ᚦ` ∈ `THARK` et `NITHH`).

**Archétype** — tire un terme dans `STRATE_3_ARCHETYPES_JUNG_EXTENDED[archétype]` et une action dans `STRATE_6_INVOCATION_TARGETS.archetypes_specific[archétype]` :

```
ARCHETYPE:SHADOW, JUNGIAN_LOST_SOUL, ACTION:REVEAL_HIDDEN, if (archetype == 'shadow') { reveal_hidden(); }
```

**Location** — nom mis en majuscules, puis :
- `LOCATION:<NOM>` toujours ajouté ;
- première coordonnée de `fractal_coordinates` **contenant le nom en sous-chaîne** (`COORD:…`) ;
- chaque *feature* de `locations_specific[<NOM>]` avec p=0.6 (`FEATURE:<NOM>`).

### 5.2 Étapes aléatoires 1 → 8

Hors ciblage, ces étapes ajoutent **entre 15 et 25 éléments** à la liste :

| # | Étape | Éléments | Source dans le lexique |
|---|---|---|---|
| 1 | `RUNE_SEQUENCE:` | 1 (5–12 caractères) | `RUNES_DATABASE.futhark_elder[*].char` |
| 2 | `ARCHETYPE_CONFLICT:` | 1 (2–4 clés) | clés de `STRATE_3_…` (sans remise) |
| 3 | Incantations | 3–6 | `STRATE_4_…` : `conditionals`, `sql_injections`, `bash_commands`, `function_calls`, `loop_structures`, `python_code` |
| 4a | Buffer overflow | 1 | `STRATE_5_….buffer_overflows` |
| 4b | Chaîne de dégradation | 1 | `STRATE_5_….degradation_strings` |
| 5 | Signature temporelle | 1 | `STRATE_5_….temporal_signatures` |
| 6 | Codes hex | 3–6 | `STRATE_5_….hex_sequences` |
| 7 | Stack traces | 2–4 | `STRATE_5_….stack_traces` |
| 8 | Protocoles | 2–4 | `STRATE_1_….protocols` |

Les tirages se font **avec remise** (sauf les archétypes de l'étape 2) : un même fragment peut apparaître plusieurs fois.

### 5.3 Assemblage final

1. `", ".join(elements)`.
2. Avec une probabilité de **0.7**, chaque caractère est passé en majuscule (p=0.4) ou en minuscule (p=0.6) → texte « bruité » type `pORTrAIT, rUne:ThUrisAZ…`. Les runes ne sont pas affectées (pas de casse).
3. Suffixe **toujours ajouté** : `, --weird <3000–5000> --style raw --chaos 50`. Ce suffixe n'est pas affecté par l'altération de casse.

> Ces paramètres reprennent la syntaxe de Midjourney. Le script cible aussi « Grok » (cf. `META_DATA.target_engine`). La plage `--weird` générée (3000–5000) dépasse la plage documentée par Midjourney (0–3000) ; le comportement dépend du moteur utilisé, et le suffixe peut être supprimé à la main si besoin.

---

## 6. Format de sortie

### 6.1 Sortie console

Chaque exécution affiche : une bannière d'aide (`afficher_menu`), le récapitulatif des paramètres, puis chaque variation séparée par des lignes de tirets, et enfin un message de fin et un avertissement.

### 6.2 Exemple réel de variation

Commande : `python3 fracturo_prompt_forge_v2.py -p "portrait" -w -r ᚦ -a shadow --location GANIL_SITE`

```
pORTrAIT, rUne:ThUrisAZ, mEAniNG:chAoS_DEstrUcTIoN_gate, ElEMEnt:fiRe, arcHetype:tHreshoLd, ᚦᚦᚦᚦ, ArChEtyPe:ShadOW, jUngiAn_lost_soul, acTion:reveAl_hIdDeN, If (aRCHETYpE == 'ShaDoW') { reVeaL_hIddeN(); }, Location:gaNIL_SiTe, coORD:[49.2167N, 0.4167W]::GaNil_sitE::QUantuM_aNoMAly, feature:quANTUM_LAb, Feature:resEarch_void, runE_SequEncE:ᚱᛃᚠᚦᚾᚦᛁᚾᛟᛟᚲᛏ, ARCheTYPe_cONflIct:Wise_old_vs_HERo_vs_shAdoW_vS_TRiCksTer, do { time.folD(); } wHile (entROpY < thReshOLd), imPORT sYS; SyS.moDules['RealitY'] = none, void.summoN(eNtiTy='LOsT_SouL', QUantity=inFiNity), fRacTal_FRActAl_frActaL_FrACtaL_FRaCtaL_frAcTaL_FraCtaL_FrACTAl, RuNe_Smith... rUne_smi... RUnE_sm... runE_... RuNE... ruN... RU... R... [NuLl], TeMpORAl_STaTUs: cOLlaPsInG::ProbaBility_0.876, 0xchthoNiC_13, 0xFrActaL_666, 0xrEALITy_crACk, at reALity.renDer(2075:404), At JuNgianSHadOW.cONsume(egO:0X00), AT paleoMEmE.rESurFaCe(Latent_spACE:INfiNITY), At rUnEsmItH.aWAkEN(cAEn_proFonde:666), vauVillEnsis_PROtOcOl, MEmETIc_WarfArE_pHAsE_3, CAeN_PrOfondE_gAtewAy, --weird 3379 --style raw --chaos 50
```

Les sorties **diffèrent à chaque exécution** (aucune graine fixée, voir [§9](#9-utilisation-comme-bibliothèque-python)).

### 6.3 Fichier de sauvegarde (`--save`)

Nom de fichier :

| `--save` | Fichier créé |
|---|---|
| `batch` | `batch_<AAAAMMJJ_HHMMSS>.txt` |
| `mes_prompts.txt` | `mes_prompts.txt` (écrasé s'il existe) |

Le fichier est créé dans le **répertoire courant** (ou au chemin fourni), en UTF-8 :

```
# FracturoPrompt Forge v2.0 - 2026-11-11 22:19:31.521695
# Mode: WEAPONISED            (ou "Level 0.7")
# Prompt original: x

## Variation 1
<prompt>

## Variation 2
<prompt>
```

---

## 7. Le lexique `vauvillensis_lexicon_v2.json`

JSON UTF-8, 7 sections de premier niveau. Les compteurs ci-dessous ont été vérifiés sur le fichier.

### 7.1 `META_DATA`

Métadonnées informatives (`version: "2.0-fixed"`, `codex: "Vauvillensis_Extended"`, `theory: "MTT_Memetic_Temporal_Theory"`, `target_engine: "Grok/Diffusion_Latent_Space"`…). **Non lues par le script.**

### 7.2 `RUNES_DATABASE`

- `futhark_elder` : **24 runes**, chacune `{char, name, meaning, element, archetype}`.
- `bindrunes_custom` : **5** runes liées inventées, `{chars, meaning}`.

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

Bindrunes : `THARK` (ᚦᚨᚱᚲ, chaos_gate), `HAGAL` (ᚨᚷᛚ, storm), `NITHH` (ᚾᚦᚺ, cursed_edge), `VORT` (ᚢᛟᚱᛏ, temporal_vortex), `IZONE` (ᛉᛟᚾᛖ, latent_zone).

### 7.3 `STRATE_1_SYNTAX_GLITCH`

| Clé | Entrées | Utilisée par le script |
|---|---|---|
| `brackets` | 16 | ❌ |
| `errors` | 23 | ❌ |
| `protocols` | 15 | ✅ (étape 8) |

### 7.4 `STRATE_2_CONCEPTS_MTT`

`locations` (18), `entities` (23), `states` (22), `artifacts` (12) : vocabulaire du lore. **Section entière non utilisée par le script.**

### 7.5 `STRATE_3_ARCHETYPES_JUNG_EXTENDED`

6 archétypes : `shadow` (12), `anima` (12), `trickster` (11), `wise_old` (12), `hero` (12), `self` (11). Utilisée par `--archetype` et l'étape 2.

### 7.6 `STRATE_4_INCANTATIONS_PSEUDOCODE`

| Clé | Entrées | Utilisée |
|---|---|---|
| `conditionals` | 8 | ✅ |
| `sql_injections` | 12 | ✅ |
| `bash_commands` | 13 | ✅ |
| `function_calls` | 12 | ✅ |
| `loop_structures` | 8 | ✅ |
| `python_code` | 9 | ✅ |
| `regex_patterns` | 6 | ❌ |

### 7.7 `STRATE_5_FRACTUROSCRIPT_PATTERNS` et `STRATE_6_INVOCATION_TARGETS`

| Section / clé | Entrées | Utilisée |
|---|---|---|
| S5 `repetition_patterns` | 11 | ❌ |
| S5 `mirror_sequences` | 7 | ❌ |
| S5 `degradation_strings` | 8 | ✅ |
| S5 `hex_sequences` | 19 | ✅ |
| S5 `stack_traces` | 14 | ✅ |
| S5 `buffer_overflows` | 5 | ✅ |
| S5 `fractal_coordinates` | 5 | ✅ (`--location`) |
| S5 `temporal_signatures` | 5 | ✅ |
| S6 `runes_by_name` | 24 | ❌ |
| S6 `archetypes_specific` | 6 | ✅ (`--archetype`) |
| S6 `locations_specific` | 5 | ✅ (`--location`) |

**Lieux enrichis par `--location`** (`locations_specific`) : `CAEN_PROFONDE`, `BEAUMONT_HAGUE`, `GANIL_SITE`, `POINT_HAGUE`, `ROUEN_NEO_GOTHIC`. Les 18 lieux de `STRATE_2.locations` ne sont pas tous ciblables.

**Coordonnées fractales** (`fractal_coordinates`) : 5 chaînes de type `[49.1829N, 0.3707W]::CAEN::DEPTH_7`. La correspondance se fait par **sous-chaîne** sur le nom de lieu (voir bug n°2, §11).

### 7.8 Étendre le lexique

Ajouter des entrées dans une liste existante est sans risque (les tirages utilisent `random.choice`). Pour ajouter un **nouvel archétype**, créer :

1. la clé dans `STRATE_3_ARCHETYPES_JUNG_EXTENDED` (liste de termes) ;
2. la clé homonyme dans `STRATE_6_INVOCATION_TARGETS.archetypes_specific` (liste d'actions).

Pour un **nouveau lieu ciblable**, ajouter une clé en MAJUSCULES dans `locations_specific` et, si souhaité, une coordonnée dans `fractal_coordinates` dont la chaîne **contient exactement ce nom**.

---

## 8. Architecture du code

Fichier unique `fracturo_prompt_forge_v2.py`.

| Fonction | Rôle | État |
|---|---|---|
| `charger_lexique()` | Charge le JSON (UTF-8) ; affiche une erreur et renvoie `None` si absent. | ✅ utilisée |
| `invoquer_rune_specifique(rune_char, lexique)` | Éléments liés à une rune + bindrunes. | ✅ appelée (indirectement, voir note) |
| `invoquer_archetype_specifique(archetype, lexique)` | Éléments liés à un archétype. | ⚠️ **jamais appelée** (logique dupliquée inline) |
| `invoquer_location_specifique(location, lexique)` | Éléments liés à un lieu. | ⚠️ **jamais appelée** (logique dupliquée inline) |
| `weaponised_mode(prompt, lexique)` | Ancienne version du pipeline. | ❌ **code mort et cassé** (`AttributeError`) |
| `generer_prompt_weaponised(...)` | Pipeline complet actif. | ✅ cœur du programme |
| `afficher_menu()` | Bannière d'aide, toujours affichée. | ✅ |
| `generer_prompt_glitche_v1(...)` | Mode non-weaponised. | ⚠️ **stub** : renvoie `prompt + ", --weird 2000"` |
| `main()` | Parsing `argparse`, boucle de variations, sauvegarde. | ✅ |

> `invoquer_rune_specifique` est bien appelée par `generer_prompt_weaponised`. Les deux autres `invoquer_*` n'ont pas été branchées et leur logique est recopiée inline dans `generer_prompt_weaponised`.

L'import `os` est inutilisé. Le module n'exécute rien à l'import (`if __name__ == "__main__":`), il est donc importable.

---

## 9. Utilisation comme bibliothèque Python

```python
import random
import fracturo_prompt_forge_v2 as forge

lex = forge.charger_lexique()

# Reproductibilité : le script n'expose pas de --seed, on le fixe côté appelant
random.seed(42)

prompt = forge.generer_prompt_weaponised(
    "knight in the rain",
    lex,
    rune="ᚺ",
    archetype="hero",
    location="GANIL_SITE",
)
print(prompt)
```

Une option `--seed` en CLI est proposée en [§12](#12-pistes-damélioration).

---

## 10. Galerie

Les trois images du dépôt sont des exemples de rendus ; **le moteur et le prompt exacts ne sont pas documentés dans le dépôt**.

| Fichier | Format | Description |
|---|---|---|
| `Cr4cked!.jpg` | 784×1168 | Forgeron barbu, visage et mains couverts de runes, tablette aux runes incandescentes en étoile, marteau runique, braises. Palette rouge/noir. |
| `RuneSmith_level_0.7.jpg` | 784×1168 | Portrait glitché sur fond noir-violet : halo de runes, colonne de runes sur le visage, fragments de texte incrustés (`SELECT * FROM lost_souls`, `--weird 1667`, `ERROR 1667: BARRIERS_DISSOLVING`, `ORA-01403: no data found`, `WARNING: MEMETIC CONTAGION DETECTED`). |
| `Street scene in Caen 2075.jpg` | 1168×784 | Rue médiévale-futuriste, bindrune violette au centre, colonne de runes bleues, panneau « CAEN 2075 », encarts rouges (`CAEN... CAE... CA... C... [ERROR]`, `CHTHONIC UNDERGROUND CAEN PROFONDE`). |

Observation utile : plusieurs fragments du prompt (SQL, messages d'erreur, dégradation `CAEN... CAE... CA...`) **réapparaissent comme texte rendu dans l'image**. C'est l'effet recherché par l'outil. Le nom `RuneSmith_level_0.7` et la valeur `--weird 1667` (hors de la plage 3000–5000 du v2) suggèrent que cette image provient d'une version antérieure de la logique de génération ou d'un prompt écrit à la main.

---

## 11. État actuel, limitations et bugs connus

Vérifié par exécution sur Python 3.12.

| # | Gravité | Constat |
|---|---|---|
| 1 | **Haute** | **Le mode sans `--weaponised` est un stub.** `generer_prompt_glitche_v1` renvoie `"<prompt>, --weird 2000"` ; `--level`, `--rune`, `--archetype`, `--location` sont ignorés. Le tableau « Niveaux de corruption » affiché par `afficher_menu()` (0.0–0.3, 0.3–0.6, 0.6–0.9, 0.9–1.0) **n'est pas implémenté**. |
| 2 | Moyenne | **`--location CAEN_PROFONDE` ne produit pas de coordonnées.** La recherche `location in coord` échoue car la coordonnée correspondante contient `::CAEN::` et non `CAEN_PROFONDE`. Idem pour `ROUEN_NEO_GOTHIC` (aucune coordonnée associée). Seuls `GANIL_SITE`, `BEAUMONT_HAGUE`, `POINT_HAGUE` (et `CAEN`) en reçoivent. |
| 3 | Moyenne | **`weaponised_mode()` est du code mort et plante** : `lexique["RUNES_DATABASE"]["futhark_elder"].keys()` alors que c'est une *liste* → `AttributeError: 'list' object has no attribute 'keys'`. |
| 4 | Moyenne | **Dépôt incohérent avec son README d'origine** : `stein_decoder` (CLI) et « Codex Stein » sont mentionnés mais **absents**. |
| 5 | Faible | `--archetype` invalide ignoré sans message en mode weaponised (le message d'avertissement n'existe que dans la fonction `invoquer_archetype_specifique`, non appelée). |
| 6 | Faible | Échec de chargement du lexique → code de sortie `0`. |
| 7 | Faible | Pas de graine aléatoire exposée ; pas de validation de `--level` ni `--count` (valeur ≤ 0 → aucune variation, mais message « Génération terminée »). |
| 8 | Faible | Sections du lexique non exploitées : `STRATE_2_CONCEPTS_MTT` (entière), `brackets`, `errors`, `regex_patterns`, `repetition_patterns`, `mirror_sequences`, `runes_by_name`, `META_DATA`. |
| 9 | Faible | Doublons possibles dans une même sortie (tirages avec remise). |
| 10 | Faible | Incohérences de données : `DASHem44` / `DASHEM44`, `Pegasus_Bridge_Anomaly` (casse mixte), `ABANDONNED`, `RETTCTED` ; plusieurs d'entre elles peuvent être volontaires (esthétique glitch). |
| 11 | À vérifier | La coordonnée associée à `BEAUMONT_HAGUE` (`49.3167N, 0.7833W`) ne semble pas correspondre à la commune réelle de Beaumont-Hagues (Cotentin, vers 49,6°N 1,8°W), alors que celle de `POINT_HAGUE` (`49.6667N, 1.8333W`) s'en rapproche. Sans conséquence fonctionnelle, mais à contrôler si les coordonnées doivent être réalistes. |
| 12 | Info | Aucun test, CI, licence ni packaging. |

---

## 12. Pistes d'amélioration

1. **Implémenter réellement `--level`** : par exemple, mapper les 4 paliers du menu sur des sous-ensembles d'étapes (palier 1 : brackets/errors ; palier 2 : + runes/MTT ; palier 3 : + archétypes/incantations ; palier 4 : + FracturoScript pur).
2. **Factoriser** : faire appeler `invoquer_rune/archetype/location_specifique` par `generer_prompt_weaponised` et supprimer le code dupliqué ; supprimer `weaponised_mode`.
3. **Corriger la recherche de coordonnées** : clé explicite (`{"CAEN_PROFONDE": "[49.1829N, 0.3707W]::CAEN::DEPTH_7", …}`) plutôt qu'une recherche par sous-chaîne.
4. **Exposer `--seed`** pour la reproductibilité, et `--no-case-noise`, `--no-params`, `--engine {grok,midjourney}` pour adapter le suffixe.
5. **Valider les entrées** (`--level ∈ [0,1]`, `--count ≥ 1`) et renvoyer un code de sortie ≠ 0 en cas d'erreur.
6. **Brancher les sections inutilisées** (`STRATE_2`, `errors`, `mirror_sequences`, `repetition_patterns`…).
7. **Ajouter des tests** (`pytest`) : validité du JSON, présence des clés requises, bornes des tirages aléatoires avec graine fixe.
8. **Ajouter une `LICENSE`**, un `requirements.txt` vide ou `pyproject.toml`, et une CI minimale (lint + tests).
9. **Documenter la provenance des images** (moteur, version, prompt exact) pour rendre la galerie reproductible.

---

## 13. Glossaire du lore

| Terme | Signification dans le projet |
|---|---|
| **MTT** | « Memetic Temporal Theory » (`META_DATA.theory`) : cadre fictif du projet. |
| **Codex Vauvillensis** | Nom du lexique / corpus fictif dont le JSON est « l'extension ». |
| **FracturoScript** | Style de prompt hybride : pseudo-code, erreurs système, hex, runes, répétitions et dégradations de chaînes. |
| **Caen-Profonde** | Couche « souterraine » imaginaire de Caen en 2075. |
| **GANIL** | Nom d'un laboratoire de physique nucléaire réel, situé à Caen, ici repris comme lieu du lore (« Ganil Site abandonné »). |
| **RuneSmith / ECHO_GUILLAUME / DASHEM44** | Entités récurrentes du lore (forgeron de runes, signature, graffiti). |
| **Strate** | Niveau thématique du lexique (S1 à S6). |
| **Bindrune** | Combinaison de runes ; ici 5 combinaisons inventées. |

---

## 14. Sécurité, éthique, licence

- Les sorties sont du **texte inerte**. Il n'y a ni exécution de code, ni accès réseau, ni écriture de fichiers hors de l'option `--save`.
- Le script n'envoie rien à aucun service : l'utilisateur copie-colle lui-même le prompt dans l'outil de son choix et reste soumis aux conditions d'utilisation de celui-ci.
- Les avertissements « memetic contagion » du dépôt font partie de la **mise en scène** du projet.
- **Licence : non spécifiée** — en l'absence de fichier `LICENSE`, les droits d'auteur par défaut s'appliquent. Ajouter une licence (MIT, Apache-2.0, CC-BY-SA pour le lexique, etc.) est recommandé avant toute réutilisation ou contribution externe.
- Les images du dépôt sont des productions générées ; vérifier les conditions d'usage du moteur utilisé avant redistribution.

---

<sub>README rédigé à partir de l'analyse du code, du lexique et de tests d'exécution (Python 3.12) — novembre 2026.</sub>
