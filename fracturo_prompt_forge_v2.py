#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FracturoPrompt Forge v2.0 - WEAPONISED EDITION
Générateur de Prompts Glitchés pour Reality Cracking
Basé sur la théorie MTT et le Codex Vauvillensis

Usage: 
  python3 fracturo_prompt_forge_v2.py --prompt "votre prompt" --level 0.9
  python3 fracturo_prompt_forge_v2.py --prompt "portrait" --level 0.9 --rune ᚦ --archetype shadow
  python3 fracturo_prompt_forge_v2.py --prompt "caen street" --level 1.0 --location CAEN_PROFONDE --weaponised
"""

import json
import random
import argparse
import os
from pathlib import Path
from datetime import datetime

# Chemin vers le lexique JSON
LEXIQUE_PATH = Path(__file__).parent / "vauvillensis_lexicon_v2.json"


def charger_lexique():
    """Charge le lexique JSON"""
    if not LEXIQUE_PATH.exists():
        print(f"❌ Erreur: Fichier lexique introuvable: {LEXIQUE_PATH}")
        return None
    
    with open(LEXIQUE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def invoquer_rune_specifique(rune_char, lexique):
    """Active les patterns spécifiques à une rune (par caractère Unicode)"""
    # Recherche la rune dans la liste
    rune_data = None
    for r in lexique["RUNES_DATABASE"]["futhark_elder"]:
        if r["char"] == rune_char:
            rune_data = r
            break
    
    if not rune_data:
        print(f"⚠️  Rune '{rune_char}' non trouvée, utilisation aléatoire")
        rune_data = random.choice(lexique["RUNES_DATABASE"]["futhark_elder"])
    
    elements = []
    elements.append(f"RUNE:{rune_data['name'].upper()}")
    elements.append(f"MEANING:{rune_data['meaning']}")
    elements.append(f"ELEMENT:{rune_data['element'].upper()}")
    elements.append(f"ARCHETYPE:{rune_data['archetype'].upper()}")
    elements.append(rune_data['char'] * random.randint(3, 7))
    
    # Recherche dans les bindrunes
    for bind_name, bind_data in lexique["RUNES_DATABASE"]["bindrunes_custom"].items():
        if rune_data['char'] in bind_data['chars'] and random.random() < 0.5:
            elements.append(f"BINDRUNE:{bind_name}_{bind_data['meaning']}")
    
    return elements


def invoquer_archetype_specifique(archetype, lexique):
    """Active les patterns spécifiques à un archétype"""
    archetype = archetype.lower()
    
    if archetype not in lexique["STRATE_3_ARCHETYPES_JUNG_EXTENDED"]:
        print(f"⚠️  Archetype '{archetype}' non trouvé, utilisation aléatoire")
        archetype = random.choice(list(lexique["STRATE_3_ARCHETYPES_JUNG_EXTENDED"].keys()))
    
    archetype_list = lexique["STRATE_3_ARCHETYPES_JUNG_EXTENDED"][archetype]
    selected = random.choice(archetype_list)
    
    elements = []
    elements.append(f"ARCHETYPE:{archetype.upper()}")
    elements.append(f"JUNGIAN_{selected.upper()}")
    
    # Ajout d'incantations spécifiques
    if archetype in lexique["STRATE_6_INVOCATION_TARGETS"]["archetypes_specific"]:
        actions = lexique["STRATE_6_INVOCATION_TARGETS"]["archetypes_specific"][archetype]
        action = random.choice(actions)
        elements.append(f"ACTION:{action.upper()}")
        elements.append(f"if (archetype == '{archetype}') {{ {action}(); }}")
    
    return elements


def invoquer_location_specifique(location, lexique):
    """Active les patterns spécifiques à une localisation"""
    location = location.upper()
    
    elements = []
    elements.append(f"LOCATION:{location}")
    
    # Coordonnées fractales
    if "fractal_coordinates" in lexique["STRATE_5_FRACTUROSCRIPT_PATTERNS"]:
        for coord in lexique["STRATE_5_FRACTUROSCRIPT_PATTERNS"]["fractal_coordinates"]:
            if location in coord:
                elements.append(f"COORD:{coord}")
                break
    
    # Patterns spécifiques
    if location in lexique["STRATE_6_INVOCATION_TARGETS"]["locations_specific"]:
        features = lexique["STRATE_6_INVOCATION_TARGETS"]["locations_specific"][location]
        for feature in features:
            if random.random() < 0.6:
                elements.append(f"FEATURE:{feature.upper()}")
    
    return elements


def weaponised_mode(prompt, lexique):
    """Mode ULTRA-WEAPONISED: Combinaison maximale de toutes les strates"""
    weaponised_elements = []
    
    # 1. Injection massive de runes
    nb_runes = random.randint(5, 12)
    runes_sequence = ''.join(random.choices(
        list(lexique["RUNES_DATABASE"]["futhark_elder"].keys()), 
        k=nb_runes
    ))
    weaponised_elements.append(f"RUNE_SEQUENCE:{runes_sequence}")
    
    # 2. Multiples archétypes en conflit
    archetypes = random.sample(
        list(lexique["STRATE_3_ARCHETYPES_JUNG_EXTENDED"].keys()), 
        k=random.randint(2, 4)
    )
    weaponised_elements.append(f"ARCHETYPE_CONFLICT:{'_VS_'.join(archetypes).upper()}")
    
    # 3. Incantations empilées
    for _ in range(random.randint(3, 6)):
        incant_type = random.choice([
            "conditionals", "sql_injections", "bash_commands", 
            "function_calls", "loop_structures", "python_code"
        ])
        incant = random.choice(lexique["STRATE_4_INCANTATIONS_PSEUDOCODE"][incant_type])
        weaponised_elements.append(incant)
    
    # 4. Patterns FracturoScript extrêmes
    weaponised_elements.append(random.choice(
        lexique["STRATE_5_FRACTUROSCRIPT_PATTERNS"]["buffer_overflows"]
    ))
    weaponised_elements.append(random.choice(
        lexique["STRATE_5_FRACTUROSCRIPT_PATTERNS"]["degradation_strings"]
    ))
    
    # 5. Signature temporelle
    weaponised_elements.append(random.choice(
        lexique["STRATE_5_FRACTUROSCRIPT_PATTERNS"]["temporal_signatures"]
    ))
    
    # 6. Hex codes multiples
    for _ in range(random.randint(3, 6)):
        weaponised_elements.append(random.choice(
            lexique["STRATE_5_FRACTUROSCRIPT_PATTERNS"]["hex_sequences"]
        ))
    
    # 7. Stack traces empilées
    for _ in range(random.randint(2, 4)):
        weaponised_elements.append(random.choice(
            lexique["STRATE_5_FRACTUROSCRIPT_PATTERNS"]["stack_traces"]
        ))
    
    # 8. Protocoles MTT actifs
    for _ in range(random.randint(2, 4)):
        weaponised_elements.append(random.choice(
            lexique["STRATE_1_SYNTAX_GLITCH"]["protocols"]
        ))
    
    return weaponised_elements


def generer_prompt_weaponised(prompt_base, lexique, rune=None, archetype=None, location=None):
    """Génération d'un prompt WEAPONISED pour reality cracking"""
    
    elements_finaux = [prompt_base]
    
    # Invocation ciblée de rune (par caractère Unicode)
    if rune:
        elements_finaux.extend(invoquer_rune_specifique(rune, lexique))
    
    # Invocation ciblée d'archétype
    if archetype:
        archetype = archetype.lower()
        if archetype in lexique["STRATE_3_ARCHETYPES_JUNG_EXTENDED"]:
            archetype_list = lexique["STRATE_3_ARCHETYPES_JUNG_EXTENDED"][archetype]
            selected = random.choice(archetype_list)
            elements_finaux.append(f"ARCHETYPE:{archetype.upper()}")
            elements_finaux.append(f"JUNGIAN_{selected.upper()}")
            
            if archetype in lexique["STRATE_6_INVOCATION_TARGETS"]["archetypes_specific"]:
                action = random.choice(lexique["STRATE_6_INVOCATION_TARGETS"]["archetypes_specific"][archetype])
                elements_finaux.append(f"ACTION:{action.upper()}")
                elements_finaux.append(f"if (archetype == '{archetype}') {{ {action}(); }}")
    
    # Invocation ciblée de location
    if location:
        location = location.upper()
        elements_finaux.append(f"LOCATION:{location}")
        
        for coord in lexique["STRATE_5_FRACTUROSCRIPT_PATTERNS"]["fractal_coordinates"]:
            if location in coord:
                elements_finaux.append(f"COORD:{coord}")
                break
        
        if location in lexique["STRATE_6_INVOCATION_TARGETS"]["locations_specific"]:
            features = lexique["STRATE_6_INVOCATION_TARGETS"]["locations_specific"][location]
            for feature in features:
                if random.random() < 0.6:
                    elements_finaux.append(f"FEATURE:{feature.upper()}")
    
    # === MODE WEAPONISED ===
    
    # 1. Séquence de runes aléatoires
    nb_runes = random.randint(5, 12)
    runes_chars = [r['char'] for r in lexique["RUNES_DATABASE"]["futhark_elder"]]
    runes_sequence = ''.join(random.choices(runes_chars, k=nb_runes))
    elements_finaux.append(f"RUNE_SEQUENCE:{runes_sequence}")
    
    # 2. Conflit d'archétypes
    archetypes_keys = list(lexique["STRATE_3_ARCHETYPES_JUNG_EXTENDED"].keys())
    selected_archetypes = random.sample(archetypes_keys, k=min(random.randint(2, 4), len(archetypes_keys)))
    elements_finaux.append(f"ARCHETYPE_CONFLICT:{'_VS_'.join(selected_archetypes).upper()}")
    
    # 3. Incantations empilées
    incant_types = ["conditionals", "sql_injections", "bash_commands", 
                    "function_calls", "loop_structures", "python_code"]
    for _ in range(random.randint(3, 6)):
        incant_type = random.choice(incant_types)
        incant = random.choice(lexique["STRATE_4_INCANTATIONS_PSEUDOCODE"][incant_type])
        elements_finaux.append(incant)
    
    # 4. Patterns FracturoScript extrêmes
    elements_finaux.append(random.choice(lexique["STRATE_5_FRACTUROSCRIPT_PATTERNS"]["buffer_overflows"]))
    elements_finaux.append(random.choice(lexique["STRATE_5_FRACTUROSCRIPT_PATTERNS"]["degradation_strings"]))
    
    # 5. Signature temporelle
    elements_finaux.append(random.choice(lexique["STRATE_5_FRACTUROSCRIPT_PATTERNS"]["temporal_signatures"]))
    
    # 6. Hex codes multiples
    for _ in range(random.randint(3, 6)):
        elements_finaux.append(random.choice(lexique["STRATE_5_FRACTUROSCRIPT_PATTERNS"]["hex_sequences"]))
    
    # 7. Stack traces empilées
    for _ in range(random.randint(2, 4)):
        elements_finaux.append(random.choice(lexique["STRATE_5_FRACTUROSCRIPT_PATTERNS"]["stack_traces"]))
    
    # 8. Protocoles MTT actifs
    for _ in range(random.randint(2, 4)):
        elements_finaux.append(random.choice(lexique["STRATE_1_SYNTAX_GLITCH"]["protocols"]))
    
    # Assemblage avec altération de casse
    prompt_glitch = ', '.join(elements_finaux)
    if random.random() < 0.7:
        prompt_glitch = ''.join([
            char.upper() if random.random() < 0.4 else char.lower() 
            for char in prompt_glitch
        ])
    
    # Paramètres Grok extrêmes
    prompt_glitch += f", --weird {random.randint(3000, 5000)} --style raw --chaos 50"
    
    return prompt_glitch


def afficher_menu():
    """Affiche le menu d'aide"""
    print("\n" + "="*70)
    print(" FRACTURO PROMPT FORGE v2.0 - WEAPONISED EDITION 🔮")
    print("   Codex Vauvillensis - Théorie MTT - Reality Cracking Protocol")
    print("="*70)
    print("\n⚔️  MODES D'INVOCATION:")
    print("\n📊 Niveaux de corruption:")
    print("  0.0 - 0.3  : Subtil (glitchs légers)")
    print("  0.3 - 0.6  : Modéré (+ concepts MTT, runes)")
    print("  0.6 - 0.9  : Avancé (+ archétypes, incantations)")
    print("  0.9 - 1.0  : Total (+ FracturoScript pur)")
    print("  WEAPONISED : Maximum (toutes strates + synergies)")
    print("\n🎯 Invocation Ciblée:")
    print("  --rune ᚦ         : Active une rune spécifique (Thurisaz)")
    print("  --archetype shadow : Active un archétype jungien")
    print("  --location CAEN_PROFONDE : Cible une localisation")
    print("\n💀 Mode Ultime:")
    print("  --weaponised     : Activation totale pour reality cracking")
    print("\n" + "="*70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="FracturoPrompt Forge v2.0 - Weaponised Reality Cracking"
    )
    parser.add_argument(
        "--prompt", "-p",
        type=str,
        required=True,
        help="Prompt de base à glitcher"
    )
    parser.add_argument(
        "--level", "-l",
        type=float,
        default=0.7,
        help="Niveau de corruption (0.0 à 1.0, défaut: 0.7)"
    )
    parser.add_argument(
        "--rune", "-r",
        type=str,
        default=None,
        help="Rune spécifique à invoquer (ex: ᚦ, ᚺ, ᛁ)"
    )
    parser.add_argument(
        "--archetype", "-a",
        type=str,
        default=None,
        help="Archétype jungien à activer (shadow, anima, trickster, etc.)"
    )
    parser.add_argument(
        "--location", "-loc",
        type=str,
        default=None,
        help="Localisation MTT à cibler (CAEN_PROFONDE, BEAUMONT_HAGUE, etc.)"
    )
    parser.add_argument(
        "--weaponised", "-w",
        action='store_true',
        help="Mode WEAPONISED pour reality cracking maximal"
    )
    parser.add_argument(
        "--count", "-c",
        type=int,
        default=1,
        help="Nombre de variations à générer (défaut: 1)"
    )
    parser.add_argument(
        "--save", "-s",
        type=str,
        default=None,
        help="Sauvegarder les prompts dans un fichier"
    )
    
    args = parser.parse_args()
    
    # Chargement du lexique
    lexique = charger_lexique()
    if not lexique:
        return
    
    afficher_menu()
    
    print(f"📝 Prompt original: {args.prompt}")
    if args.weaponised:
        print(f"⚔️  MODE: WEAPONISED REALITY CRACKING")
    else:
        print(f"️  Niveau de corruption: {args.level}")
    
    if args.rune:
        print(f"🔱 Rune invoquée: {args.rune}")
    if args.archetype:
        print(f"👁️  Archétype activé: {args.archetype}")
    if args.location:
        print(f"📍 Localisation ciblée: {args.location}")
    print(f"🔢 Nombre de variations: {args.count}")
    print("\n" + "-"*70 + "\n")
    
    prompts_generes = []
    
    for i in range(args.count):
        print(f"✨ Variation {i+1}/{args.count}:\n")
        
        if args.weaponised:
            prompt_glitche = generer_prompt_weaponised(
                args.prompt, lexique, 
                rune=args.rune, 
                archetype=args.archetype, 
                location=args.location
            )
        else:
            # Fallback vers la logique v1.0 pour les niveaux normaux
            prompt_glitche = generer_prompt_glitche_v1(
                args.prompt, args.level, lexique
            )
        
        prompts_generes.append(prompt_glitche)
        print(prompt_glitche)
        print("\n" + "-"*70 + "\n")
    
    # Sauvegarde optionnelle
    if args.save:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{args.save}_{timestamp}.txt" if not args.save.endswith('.txt') else args.save
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"# FracturoPrompt Forge v2.0 - {datetime.now()}\n")
            f.write(f"# Mode: {'WEAPONISED' if args.weaponised else f'Level {args.level}'}\n")
            f.write(f"# Prompt original: {args.prompt}\n\n")
            for i, prompt in enumerate(prompts_generes, 1):
                f.write(f"## Variation {i}\n{prompt}\n\n")
        
        print(f"💾 Prompts sauvegardés dans: {filename}")
    
    print("✅ Génération terminée!")
    print("️  WARNING: Ces prompts sont weaponised pour reality cracking.")
    print("💡 Copiez le prompt et testez-le dans Grok/Midjourney à vos risques et périls.")


def generer_prompt_glitche_v1(prompt_base, niveau, lexique):
    """Version simplifiée de la v1.0 pour les niveaux non-weaponised"""
    # (Garder la logique de la v1.0 ici pour compatibilité)
    return prompt_base + ", --weird 2000"


if __name__ == "__main__":
    main()
