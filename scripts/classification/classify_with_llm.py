"""
Classify organizations using LLM (Claude Haiku) to read purpose and assign categories
Much more accurate than keyword matching
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


def load_category_hierarchy(yaml_file: str) -> List[str]:
    """Load category hierarchy and extract all leaf categories"""
    with open(yaml_file, 'r', encoding='utf-8') as f:
        raw_data = yaml.safe_load(f)

    def extract_leaves(data, parent=None):
        """Recursively extract leaf categories"""
        leaves = []
        for item in data:
            if isinstance(item, str):
                # Leaf node
                full_path = f"{parent} > {item}" if parent else item
                leaves.append(full_path)
            elif isinstance(item, dict):
                for key, value in item.items():
                    if isinstance(value, list):
                        leaves.extend(extract_leaves(value, key))
        return leaves

    return extract_leaves(raw_data)


def read_json_file(filepath):
    """Read JSON file with UTF-8 encoding"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def classify_batch(client: Anthropic, organizations: List[Dict], categories: List[str]) -> List[str]:
    """
    Classify a batch of organizations using Claude Haiku

    Args:
        client: Anthropic client
        organizations: List of org dicts with 'name' and 'purpose'
        categories: List of available categories

    Returns:
        List of assigned categories (same order as input)
    """

    # Build prompt
    categories_text = "\n".join([f"- {cat}" for cat in categories])

    orgs_text = ""
    for i, org in enumerate(organizations, 1):
        purpose = org['purpose'] if org['purpose'] else "Nincs leírás"
        orgs_text += f"\n{i}. {org['name']}\n   Cél: {purpose}\n"

    prompt = f"""Kategorizáld a magyar civil szervezeteket a céljuk alapján. Válassz PONTOSAN EGY kategóriát minden szervezethez.

KATEGÓRIÁK:
{categories_text}

SZERVEZETEK:
{orgs_text}

VÁLASZ FORMÁTUM - csak számozott lista, minden sorban: szám. kategória
Példa:
1. környezet és természetvédelem
2. kutyák
3. gyermekkórházak

A te válaszod:"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",  # Correct Haiku 4.5 model ID
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

        return results

    except Exception as e:
        print(f"   HIBA a klasszifikációnál: {e}")
        return ["Kategorizálatlan"] * len(organizations)


def main():
    """Main classification process"""

    print("="*70)
    print("SZERVEZETEK KATEGORIZÁLÁSA LLM-MEL (Claude Haiku)")
    print("="*70)

    # Check for API key - first from env, then from api.txt file
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key and os.path.exists("api.txt"):
        print("   API kulcs betöltése api.txt fájlból...")
        with open("api.txt", 'r', encoding='utf-8') as f:
            api_key = f.read().strip()

    if not api_key:
        print("\nHIBA: ANTHROPIC_API_KEY nincs beállítva!")
        print("Két lehetőség:")
        print("  1. Mentsd az API kulcsot api.txt fájlba")
        print("  2. Állítsd be környezeti változóként:")
        print("     Windows: set ANTHROPIC_API_KEY=your-key-here")
        print("     Linux/Mac: export ANTHROPIC_API_KEY=your-key-here")
        return

    print(f"   API kulcs betöltve (utolsó 8 karakter: ...{api_key[-8:]})")
    client = Anthropic(api_key=api_key)

    # Load categories
    print("\n1. Kategóriák betöltése...")
    categories = load_category_hierarchy('categories.yaml')
    print(f"   {len(categories)} kategória betöltve")

    # Load organizations
    print("\n2. Szervezetek betöltése...")
    organizations_folder = 'organizations'

    if not os.path.exists(organizations_folder):
        print(f"   HIBA: '{organizations_folder}' mappa nem található!")
        return

    json_files = [f for f in os.listdir(organizations_folder) if f.endswith('.json')]
    print(f"   {len(json_files)} JSON fájl")

    org_data = []
    for filename in json_files:
        filepath = os.path.join(organizations_folder, filename)
        try:
            json_data = read_json_file(filepath)

            if json_data.get('error'):
                continue

            azonosito = json_data.get('alapadatok', {}).get('azonosito_adatok', {})
            fonadatok = json_data.get('alapadatok', {}).get('fonadatok', {})

            org_name = azonosito.get('teljes_név', json_data.get('search_name', 'Unknown'))
            purpose = fonadatok.get('céljának_leírása', '')

            org_data.append({
                'name': org_name,
                'purpose': purpose[:500]  # Limit to 500 chars to save tokens
            })
        except Exception as e:
            print(f"   Hiba {filename} olvasásakor: {e}")

    print(f"   {len(org_data)} szervezet betöltve")

    # Classify in batches
    print("\n3. Klasszifikálás (batch-enként, Claude Haiku)...")
    batch_size = 10  # Process 10 organizations at a time
    all_results = []

    total_batches = (len(org_data) + batch_size - 1) // batch_size

    for i in range(0, len(org_data), batch_size):
        batch = org_data[i:i+batch_size]
        batch_num = i // batch_size + 1

        print(f"   Batch {batch_num}/{total_batches} ({len(batch)} szervezet)...")

        results = classify_batch(client, batch, categories)
        all_results.extend(results)

        # Small delay to avoid rate limits
        if batch_num < total_batches:
            time.sleep(1)

    # Match results with organizations
    print("\n4. Eredmények összeállítása...")

    output_data = []
    for i, org in enumerate(org_data):
        category = all_results[i] if i < len(all_results) else "Kategorizálatlan"

        # Parse category path
        parts = category.split(' > ')

        output_data.append({
            'Szervezet neve': org['name'],
            'Új kategória (legalsó szint)': parts[-1] if parts else category,
            'Szülő kategória 1': parts[0] if len(parts) > 1 else '',
            'Szülő kategória 2': parts[1] if len(parts) > 2 else '',
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
    output_file = 'organization_categories_llm.csv'
    df_results.to_csv(output_file, index=False, encoding='utf-8-sig')

    print(f"\n6. Eredmények mentve: {output_file}")
    print("="*70)
    print("\nKÉSZ!")


if __name__ == '__main__':
    main()
