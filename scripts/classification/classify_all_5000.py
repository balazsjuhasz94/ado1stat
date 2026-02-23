"""
Classify ALL organizations using LLM (Claude Haiku) - VERSION 3
- Processes all organizations in organizations_by_adoszam folder
- Saves to organization_categories_ALL_10000.csv
- Uses categories_with_descriptions_v2.yaml with updated category hierarchy
- Includes both organization purpose AND headquarters location
"""

import json
import os
import yaml
import pandas as pd
from anthropic import Anthropic
import sys
from typing import List, Dict
import time

# Set UTF-8 encoding for console output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def load_categories_with_descriptions(yaml_file: str) -> Dict[str, Dict]:
    """
    Load category descriptions from YAML file

    Returns:
        Dict mapping category name to {parent, description}
    """
    with open(yaml_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    categories = data.get('categories', {})
    return categories


def format_categories_for_prompt(categories: Dict[str, Dict]) -> str:
    """
    Format categories with descriptions for LLM prompt

    Returns:
        Formatted string with categories and their descriptions
    """
    lines = []

    # Group by parent
    by_parent = {}
    for cat_name, cat_info in categories.items():
        parent = cat_info.get('parent', 'Egyéb')
        if parent not in by_parent:
            by_parent[parent] = []
        by_parent[parent].append((cat_name, cat_info.get('description', '')))

    # Format output
    for parent in sorted(by_parent.keys()):
        lines.append(f"\n=== {parent.upper()} ===")
        for cat_name, description in by_parent[parent]:
            # Clean up description (remove extra whitespace, newlines)
            clean_desc = ' '.join(description.split())
            lines.append(f"\n• {cat_name}")
            lines.append(f"  {clean_desc}")

    return '\n'.join(lines)


def read_json_file(filepath):
    """Read JSON file with UTF-8 encoding"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def classify_batch(client: Anthropic, organizations: List[Dict], categories_text: str) -> List[str]:
    """
    Classify a batch of organizations using Claude Haiku

    Args:
        client: Anthropic client
        organizations: List of org dicts with 'name', 'purpose', and 'headquarters'
        categories_text: Formatted categories with descriptions

    Returns:
        List of assigned categories (same order as input)
    """

    # Build organizations text with name, headquarters, and purpose
    orgs_text = ""
    for i, org in enumerate(organizations, 1):
        name = org['name']
        headquarters = org.get('headquarters', 'Nincs adat')
        purpose = org['purpose'] if org['purpose'] else "Nincs leírás"

        orgs_text += f"\n{i}. {name}\n"
        orgs_text += f"   Székhely: {headquarters}\n"
        orgs_text += f"   Cél: {purpose}\n"

    prompt = f"""Kategorizáld a magyar civil szervezeteket a céljuk ÉS székhelyük alapján.
Válassz PONTOSAN EGY kategóriát minden szervezethez a lenti lehetőségek közül.

FONTOS SZABÁLYOK:
- Olvasd el FIGYELMESEN minden kategória leírását
- A kategória leírásában a "FÓKUSZA" azt jelenti, hogy ez a FŐDOLOG, nem csak mellékesen foglalkoznak vele
- A "Használd, ha..." rész pontosan megmondja, mikor válaszd azt a kategóriát
- A "NEM ide tartozik" rész segít elkerülni a tévesztést
- Ha bizonytalan vagy, válaszd az "egyéb..." kategóriát a megfelelő főkategórián belül

{categories_text}

SZERVEZETEK:
{orgs_text}

VÁLASZ FORMÁTUM - csak számozott lista, minden sorban: szám. kategória
FONTOS: Csak a kategória NEVÉT írd, ne a szülő kategóriát!

Példa:
1. kutyák
2. gimnáziumok
3. rászorulók segítése

A te válaszod:"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            temperature=0,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Parse response
        response_text = message.content[0].text.strip()
        lines = response_text.split('\n')

        results = []
        for line in lines:
            line = line.strip()
            if not line or not line[0].isdigit():
                continue
            # Parse "1. category name" or "1) category name" format
            if '. ' in line:
                parts = line.split('. ', 1)
                if len(parts) == 2:
                    category = parts[1].strip()
                    # Remove any quotes or extra characters
                    category = category.strip('"\'"')
                    results.append(category)
            elif ') ' in line:
                parts = line.split(') ', 1)
                if len(parts) == 2:
                    category = parts[1].strip()
                    category = category.strip('"\'"')
                    results.append(category)

        # Ensure we have the right number of results
        if len(results) != len(organizations):
            print(f"   FIGYELEM: {len(results)} választ kaptunk {len(organizations)} szervezetre")
            print(f"   JAVÍTÁS: Hiányzó címkék kitöltése 'Kategorizálatlan'-nal")
            # Pad with "Kategorizálatlan" to match expected count
            while len(results) < len(organizations):
                results.append("Kategorizálatlan")
            # Truncate if too many (shouldn't happen, but be safe)
            results = results[:len(organizations)]

        return results

    except Exception as e:
        print(f"   HIBA a klasszifikációnál: {e}")
        return ["Kategorizálatlan"] * len(organizations)


def main():
    """Main classification process"""

    # Resolve paths relative to project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
    data_dir = os.path.join(project_root, 'data')

    print("="*70)
    print("ÖSSZES SZERVEZET KATEGORIZÁLÁSA (10000 ORG) - Claude Haiku")
    print("Új kategóriák v2 leírásokkal + Székhely információval")
    print("="*70)

    # Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    api_txt_path = os.path.join(data_dir, 'api.txt')
    if not api_key and os.path.exists(api_txt_path):
        print("   API kulcs betöltése api.txt fájlból...")
        with open(api_txt_path, 'r', encoding='utf-8') as f:
            api_key = f.read().strip()

    if not api_key:
        print("\nHIBA: ANTHROPIC_API_KEY nincs beállítva!")
        print("Mentsd az API kulcsot data/api.txt fájlba vagy állítsd be környezeti változóként.")
        return

    print(f"   API kulcs betöltve (utolsó 8 karakter: ...{api_key[-8:]})")
    client = Anthropic(api_key=api_key)

    # Load categories with descriptions
    print("\n1. Kategóriák és leírások betöltése...")
    categories_yaml = os.path.join(data_dir, 'categories_with_descriptions_v2.yaml')
    categories = load_categories_with_descriptions(categories_yaml)
    print(f"   {len(categories)} kategória betöltve leírásokkal")

    # Format categories for prompt
    categories_text = format_categories_for_prompt(categories)

    # Load ALL organizations from organizations_by_adoszam folder
    print("\n2. ÖSSZES szervezet betöltése (organizations_by_adoszam)...")
    organizations_folder = os.path.join(project_root, 'organizations_by_adoszam')

    if not os.path.exists(organizations_folder):
        print(f"   HIBA: '{organizations_folder}' mappa nem található!")
        return

    json_files = [f for f in os.listdir(organizations_folder) if f.endswith('.json')]
    print(f"   {len(json_files)} JSON fájl a mappában")

    org_data = []
    errors_skipped = 0

    for i, filename in enumerate(json_files):
        if (i + 1) % 500 == 0:
            print(f"   Betöltés: {i+1}/{len(json_files)}...")

        filepath = os.path.join(organizations_folder, filename)
        try:
            json_data = read_json_file(filepath)

            # Skip files with errors (couldn't scrape)
            if json_data.get('error'):
                errors_skipped += 1
                continue

            azonosito = json_data.get('alapadatok', {}).get('azonosito_adatok', {})
            fonadatok = json_data.get('alapadatok', {}).get('fonadatok', {})

            org_name = azonosito.get('teljes_név', json_data.get('search_adoszam', 'Unknown'))
            purpose = fonadatok.get('céljának_leírása', '')
            headquarters = azonosito.get('székhely_címe', 'Nincs adat')
            adoszam = json_data.get('search_adoszam', '')

            org_data.append({
                'name': org_name,
                'purpose': purpose[:500],  # Limit to 500 chars
                'headquarters': headquarters[:200],  # Limit headquarters too
                'adoszam': adoszam
            })
        except Exception as e:
            print(f"   Hiba {filename} olvasásakor: {e}")
            errors_skipped += 1

    if errors_skipped > 0:
        print(f"   {errors_skipped} szervezet kihagyva (hiba a scrapingnél)")
    print(f"   {len(org_data)} szervezet betöltve feldolgozásra")

    if len(org_data) == 0:
        print("\n   HIBA: Nincsenek szervezetek!")
        return

    # Classify in batches
    print("\n3. Klasszifikálás (batch-enként, Claude Haiku)...")
    print(f"   Ez körülbelül {len(org_data) // 10} API hívást fog igénybe venni")
    print(f"   Becsült időtartam: {len(org_data) // 10 * 2 // 60} perc")

    batch_size = 10  # Process 10 organizations at a time
    all_results = []

    total_batches = (len(org_data) + batch_size - 1) // batch_size

    for i in range(0, len(org_data), batch_size):
        batch = org_data[i:i+batch_size]
        batch_num = i // batch_size + 1

        if batch_num % 10 == 0 or batch_num == 1:
            print(f"   Batch {batch_num}/{total_batches} ({len(batch)} szervezet)...")

        results = classify_batch(client, batch, categories_text)
        all_results.extend(results)

        # Small delay to avoid rate limits
        if batch_num < total_batches:
            time.sleep(1)

    # Match results with organizations
    print("\n4. Eredmények összeállítása...")

    # Get parent categories from the descriptions file
    category_parents = {}
    for cat_name, cat_info in categories.items():
        parent = cat_info.get('parent', '')
        category_parents[cat_name] = parent

    output_data = []
    for i, org in enumerate(org_data):
        category = all_results[i] if i < len(all_results) else "Kategorizálatlan"
        parent = category_parents.get(category, '')

        output_data.append({
            'Adószám': org['adoszam'],
            'Szervezet neve': org['name'],
            'Székhely': org['headquarters'],
            'Új kategória (legalsó szint)': category,
            'Szülő kategória': parent,
            'Cél (első 200 karakter)': org['purpose'][:200]
        })

    # Statistics
    df_results = pd.DataFrame(output_data)

    print("\n5. Statisztikák:")
    categorized = df_results[df_results['Új kategória (legalsó szint)'] != 'Kategorizálatlan']
    print(f"   Kategorizált: {len(categorized)} ({len(categorized)/len(df_results)*100:.1f}%)")

    print("\n   Top 10 kategória:")
    category_counts = df_results['Új kategória (legalsó szint)'].value_counts()
    for cat, count in category_counts.head(10).items():
        print(f"     {cat}: {count}")

    # Save to CSV
    output_file = os.path.join(data_dir, 'organization_categories_ALL_10000.csv')
    df_results.to_csv(output_file, index=False, encoding='utf-8-sig')

    print(f"\n6. Eredmények mentve: {output_file}")
    print("="*70)
    print("\nKÉSZ!")
    print(f"\nFájl neve: {output_file}")
    print(f"Feldolgozott szervezetek: {len(df_results):,}")


if __name__ == '__main__':
    main()
