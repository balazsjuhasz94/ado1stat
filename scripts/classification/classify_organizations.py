"""
Classify organizations into categories based on their purpose text
Uses the category hierarchy from categories.yaml
"""

import json
import os
import yaml
import pandas as pd
import re
import sys
from typing import List, Dict, Optional

# Set UTF-8 encoding for console output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def load_category_hierarchy(yaml_file: str) -> Dict:
    """Load and parse category hierarchy from YAML"""
    with open(yaml_file, 'r', encoding='utf-8') as f:
        raw_data = yaml.safe_load(f)
    return raw_data


def extract_leaf_categories(hierarchy: List, parent_path: List = None) -> Dict[str, List[str]]:
    """
    Extract all leaf (lowest level) categories with their parent path

    Returns:
        Dict mapping leaf category name to parent path
    """
    if parent_path is None:
        parent_path = []

    leaf_categories = {}

    for item in hierarchy:
        if isinstance(item, str):
            # This is a leaf node
            leaf_categories[item] = parent_path.copy()
        elif isinstance(item, dict):
            # This has children
            for parent, children in item.items():
                if isinstance(children, list):
                    # Recurse into children
                    child_leaves = extract_leaf_categories(children, parent_path + [parent])
                    leaf_categories.update(child_leaves)

    return leaf_categories


def create_category_rules() -> Dict[str, List[str]]:
    """
    Define keyword patterns for each leaf category
    Returns dict mapping category name to list of keywords/patterns
    """
    return {
        # Kulturális szervezetek
        'sajtó, média': ['sajtó', 'média', 'újság', 'hír', 'riport', 'tudósít', 'szerkeszt', 'kiadvány', 'lap ', 'rádió', 'televízió'],
        'vallás népszerűsítés': ['vallás', 'egyház', 'kereszt', 'bibliai', 'biblikus', 'isten', 'lelki', 'hitélet', 'hívő', 'katolikus', 'protestáns', 'református', 'evangélikus', 'baptista'],
        'etnikai szervezetek': ['etnikai', 'nemzeti', 'kisebbség', 'roma', 'cigány', 'zsidó', 'horvát', 'szerb', 'német', 'népcsoport', 'hagyomány'],
        'művészeti szervezetek': ['művész', 'zene', 'tánc', 'színház', 'festés', 'szobrász', 'galéria', 'kiállítás', 'koncert', 'előadás', 'kulturális program'],
        'demokráciát tevő szervezetek': ['demokrácia', 'átlátható', 'választás', 'jogállam', 'szabadság', 'vélemény', 'független'],

        # Oktatási szervezetek
        'tehetséggondozás': ['tehetség', 'versenyz', 'verseny', 'diák', 'tanulm'],
        'budapesti gimnáziumok': ['gimnázium', 'budapest', 'fővárosi', 'budapesti'],
        'Budapesten kívüli gimnáziumok': ['gimnázium', 'vidék'],
        'általános iskolák': ['általános iskola', 'alsó tagozat', 'felső tagozat'],
        'egyéb iskolák': ['óvoda', 'iskola', 'kollégium'],
        'egyéb oktatás szervezetek': ['oktat', 'képz', 'tanít', 'tanul', 'diák', 'hallgató', 'pedagóg'],

        # Jogvédő szervezetek
        'nőjogi szervezetek': ['nő', 'női', 'anyák', 'anya', 'lányok'],
        'nemi kisebbségek': ['lmbt', 'queer', 'meleg', 'leszbikus', 'transznemű', 'nemi identitás'],
        'egyéb jogvédő szervezetek': ['jogvéd', 'jog', 'szabadság', 'emberi jog', 'civil jog'],

        # Állatvédelem
        'kutyák': ['kutya', 'eb', 'kölyök', 'vakvezető', 'segítőkutya'],
        'macskák': ['macska', 'cica', 'kandúr'],
        'madarak': ['madár', 'repülő', 'fészek', 'góly', 'sas'],
        'egyéb konkrét állatok': ['ló', 'lovak', 'nyúl', 'hörcsög', 'tengerimalac', 'állat'],
        'állatkertek': ['állatkert', 'zoo'],
        'egyéb állatvédelem': ['állatvéd', 'állatment', 'állatotthon', 'állatbarát', 'menhely'],

        # Szociális szervezetek
        'rászorulók segítése': ['rászoruló', 'szegén', 'hajléktalan', 'nélkülöz', 'étkeztet', 'segély'],
        'hátrányos helyzetű gyerekek támogatása': ['hátrányos', 'halmozottan hátrányos', 'gyerek', 'gyermek'],
        'gyermekvédelem': ['gyermekvéd', 'gyermekotthon', 'árva', 'veszélyeztet'],
        'családsegítők': ['család', 'szülő', 'házasság', 'párkapcsolat'],
        'vakok': ['vak', 'látás', 'braille', 'gyengénlátó'],
        'süketek': ['süket', 'hallás', 'jelnyelv', 'nagyothalló'],
        'autistiák': ['autista', 'autizmus', 'spektrum'],
        'egyéb fogyatékkal élők': ['fogyatékos', 'mozgássérült', 'értelmi fogyatékos', 'down'],
        'beteg emberek lelki és szociális támogatása': ['beteg', 'kórház', 'gyógy'],
        'egyházhoz kötődő szociális szervezetek': ['egyház', 'kereszt', 'szeretet', 'karitász', 'máltai'],

        # Katasztrófavédelem
        'országos szervezetek': ['országos', 'mentő', 'mentés', 'életmentő', 'katasztrófa'],
        'helyi szervezetek': ['helyi', 'városi', 'települési', 'mentő', 'önkéntes tűzoltó'],

        # Egészségügy - Felnőtt
        'kórházak': ['kórház', 'klinika', 'intézet', 'osztály'],
        'női egészségügy': ['női', 'nőgyógy', 'szülészet', 'mell'],
        'daganatos betegek gyógyítása': ['daganat', 'rák', 'onkológia', 'tumor'],
        'egyéb felnőtt egészségügy': ['egészség', 'beteg', 'orvos', 'kezelés'],

        # Egészségügy - Gyermek
        'gyermekkórházak': ['gyermekkórház', 'gyermekklinika'],
        'beteg gyerekek lelki segítése': ['gyermek', 'gyerek', 'lelki', 'bohóc', 'játék'],
        'koraszülöttek': ['koraszülött', 'újszülött', 'incubator', 'perinát'],
        'cukorbeteg gyerekek': ['diabét', 'cukor', 'inzulin', '1-es típus'],
        'leukémiás és daganatos gyerekek': ['leukémia', 'rák', 'daganat', 'gyermek', 'gyerek'],
        'konkrét beteg gyerekek': ['gyermek', 'gyerek', 'emlékére', 'alapítvány'],
        'egyéb gyermek egészségügy': ['gyermek', 'gyerek', 'csecsemő', 'baba'],

        # Környezet és természetvédelem
        'környezet és természetvédelem': ['környezet', 'természet', 'erdő', 'fa', 'zöld', 'ökológia', 'fenntartható', 'klíma', 'hulladék'],

        # Szabadidős és sporttevékenységek
        'sportklubok': ['sport', 'futball', 'kosár', 'labda', 'úszás', 'atlétika', 'küzdősport', 'judo', 'golf'],
        'vadásztársaságok': ['vadász', 'vad', 'lövész', 'lövő'],
        'egyéb szabadidős szervezetek': ['szabadidő', 'hobbi', 'közösség', 'klub', 'szakkör'],
    }


def classify_organization(purpose_text: str, category_rules: Dict[str, List[str]]) -> Optional[str]:
    """
    Classify organization into a category based on purpose text

    Args:
        purpose_text: Organization's purpose description
        category_rules: Dict mapping category to keyword patterns

    Returns:
        Category name or None if no match
    """
    if not purpose_text or purpose_text == 'Nincs leírás':
        return None

    purpose_lower = purpose_text.lower()

    # Score each category based on keyword matches
    scores = {}
    for category, keywords in category_rules.items():
        score = 0
        for keyword in keywords:
            # Count occurrences of keyword (partial match)
            if keyword in purpose_lower:
                score += purpose_lower.count(keyword)

        if score > 0:
            scores[category] = score

    # Return category with highest score
    if scores:
        best_category = max(scores.items(), key=lambda x: x[1])
        return best_category[0]

    return None


def read_json_file(filepath):
    """Read JSON file with UTF-8 encoding"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    """Main classification process"""

    print("="*70)
    print("SZERVEZETEK KATEGORIZÁLÁSA")
    print("="*70)

    # Load category hierarchy
    print("\n1. Kategória hierarchia betöltése...")
    hierarchy = load_category_hierarchy('categories.yaml')
    leaf_categories = extract_leaf_categories(hierarchy)
    print(f"   Találtam {len(leaf_categories)} legalsó szintű kategóriát")

    # Create classification rules
    print("\n2. Klasszifikációs szabályok létrehozása...")
    category_rules = create_category_rules()
    print(f"   {len(category_rules)} kategóriához van szabály")

    # Read all organization JSON files
    print("\n3. Szervezetek betöltése...")
    organizations_folder = 'organizations'
    org_data = []

    if not os.path.exists(organizations_folder):
        print(f"   HIBA: '{organizations_folder}' mappa nem található!")
        return

    json_files = [f for f in os.listdir(organizations_folder) if f.endswith('.json')]
    print(f"   {len(json_files)} JSON fájl található")

    for i, filename in enumerate(json_files):
        if (i + 1) % 100 == 0:
            print(f"   Feldolgozás: {i+1}/{len(json_files)}...")

        filepath = os.path.join(organizations_folder, filename)
        try:
            json_data = read_json_file(filepath)

            # Skip if error
            if json_data.get('error'):
                continue

            # Extract data
            azonosito = json_data.get('alapadatok', {}).get('azonosito_adatok', {})
            fonadatok = json_data.get('alapadatok', {}).get('fonadatok', {})

            org_name = azonosito.get('teljes_név', json_data.get('search_name', 'Unknown'))
            purpose = fonadatok.get('céljának_leírása', 'Nincs leírás')
            original_category = fonadatok.get('szervezet_célja_szerinti_besorolás', '(Nincs kategória)')

            org_data.append({
                'name': org_name,
                'purpose': purpose,
                'original_category': original_category
            })
        except Exception as e:
            print(f"   Hiba {filename} olvasásakor: {e}")

    print(f"\n   Összesen {len(org_data)} szervezet betöltve")

    # Classify each organization
    print("\n4. Szervezetek klasszifikálása...")
    results = []

    for i, org in enumerate(org_data):
        if (i + 1) % 100 == 0:
            print(f"   Klasszifikálás: {i+1}/{len(org_data)}...")

        category = classify_organization(org['purpose'], category_rules)

        # Get parent categories
        parent_path = leaf_categories.get(category, []) if category else []

        results.append({
            'Szervezet neve': org['name'],
            'Új kategória (legalsó szint)': category if category else 'Kategorizálatlan',
            'Szülő kategória 1': parent_path[0] if len(parent_path) > 0 else '',
            'Szülő kategória 2': parent_path[1] if len(parent_path) > 1 else '',
            'Eredeti kategória': org['original_category'],
            'Cél (első 200 karakter)': org['purpose'][:200] if org['purpose'] else ''
        })

    # Statistics
    print("\n5. Statisztikák:")
    df_results = pd.DataFrame(results)

    categorized = df_results[df_results['Új kategória (legalsó szint)'] != 'Kategorizálatlan']
    uncategorized = df_results[df_results['Új kategória (legalsó szint)'] == 'Kategorizálatlan']

    print(f"   Kategorizált: {len(categorized)} ({len(categorized)/len(df_results)*100:.1f}%)")
    print(f"   Kategorizálatlan: {len(uncategorized)} ({len(uncategorized)/len(df_results)*100:.1f}%)")

    print("\n   Top 10 kategória:")
    category_counts = df_results['Új kategória (legalsó szint)'].value_counts()
    for cat, count in category_counts.head(10).items():
        print(f"     {cat}: {count}")

    # Save to CSV
    output_file = 'organization_categories.csv'
    df_results.to_csv(output_file, index=False, encoding='utf-8-sig')

    print(f"\n6. Eredmények mentve: {output_file}")
    print("="*70)
    print("\nKÉSZ!")


if __name__ == '__main__':
    main()
