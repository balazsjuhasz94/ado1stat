"""
Re-classify Oktatás organizations using Claude with web search capability.
When the org type is ambiguous from name+purpose alone, the model searches
the web to determine the correct school type.
"""

import json
import os
import sys
import yaml
import pandas as pd
from anthropic import Anthropic
import time
import re

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(BASE_DIR, 'data')
ORGS_DIR = os.path.join(BASE_DIR, 'organizations_by_adoszam')
CSV_PATH = os.path.join(DATA_DIR, 'organization_categories_ALL_10000.csv')
YAML_PATH = os.path.join(DATA_DIR, 'categories_with_descriptions_v2.yaml')
API_KEY_PATH = os.path.join(DATA_DIR, 'api.txt')
RESULTS_PATH = os.path.join(DATA_DIR, 'oktatas_reclassified.csv')
LOG_PATH = os.path.join(DATA_DIR, 'oktatas_reclassification_log.jsonl')


def load_api_key():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and os.path.exists(API_KEY_PATH):
        with open(API_KEY_PATH, 'r') as f:
            api_key = f.read().strip()
    if not api_key:
        raise ValueError("No ANTHROPIC_API_KEY found")
    return api_key


def load_oktatas_categories():
    """Load only the oktatás subcategories from YAML."""
    with open(YAML_PATH, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    cats = data.get('categories', {})
    oktatas_cats = {}
    for name, info in cats.items():
        if info.get('parent') == 'oktatás':
            oktatas_cats[name] = info
    return oktatas_cats


def format_oktatas_categories(cats):
    """Format oktatás categories for the prompt."""
    lines = []
    for name, info in cats.items():
        desc = ' '.join(info.get('description', '').split())
        lines.append(f"• {name}\n  {desc}")
    return '\n'.join(lines)


def load_oktatas_orgs():
    """Load all orgs with parent_category=oktatás from CSV."""
    df = pd.read_csv(CSV_PATH)
    oktat = df[df['Szülő kategória'] == 'oktatás'].copy()
    return oktat


def get_org_json_data(adoszam):
    """Try to load the JSON file for an org to get full purpose."""
    for fn in os.listdir(ORGS_DIR):
        if fn.startswith(f'org_{adoszam}') and fn.endswith('.json'):
            path = os.path.join(ORGS_DIR, fn)
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            fonadatok = data.get('alapadatok', {}).get('fonadatok', {})
            azonosito = data.get('alapadatok', {}).get('azonosito_adatok', {})
            purpose = fonadatok.get('céljának_leírása', '')
            hq = azonosito.get('székhely_címe', '')
            full_name = azonosito.get('teljes_név', '')
            return purpose, hq, full_name
    return '', '', ''


def classify_single_org(client, org_name, purpose, headquarters, categories_text, valid_categories):
    """
    Classify a single org using Claude with web search tool.
    Returns (category, reasoning, searched).
    """
    system_prompt = f"""Te egy magyar civil szervezet kategorizáló rendszer vagy.
A feladatod: az alábbi oktatási szervezetet a megfelelő alkategóriába sorolni.

ELÉRHETŐ OKTATÁSI KATEGÓRIÁK:
{categories_text}

SZABÁLYOK:
1. Ha a szervezet neve és célja alapján EGYÉRTELMŰ, melyik kategória illik rá, válaszd azt közvetlenül.
2. Ha NEM EGYÉRTELMŰ (pl. nem derül ki, hogy gimnázium-e vagy általános iskola, vagy szakiskola-e),
   KERESS RÁ a szervezet nevére a weben, hogy megtudd az intézmény típusát.
3. Különösen figyelj arra, hogy sok alapítvány neve nem árulja el az iskola típusát
   (pl. "Petőfi Sándor Alapítvány" - lehet gimnázium ÉS általános iskola is).
4. A válaszodban add meg a kategóriát és egy rövid indoklást.

VÁLASZ FORMÁTUM (mindig ezt kövesd):
KATEGÓRIA: [kategória neve]
INDOKLÁS: [1-2 mondat, miért választottad ezt]"""

    user_msg = f"""Kategorizáld ezt a szervezetet:

Név: {org_name}
Székhely: {headquarters}
Cél: {purpose if purpose else 'Nincs leírás'}"""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            temperature=0,
            system=system_prompt,
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 3
            }],
            messages=[{"role": "user", "content": user_msg}]
        )

        # Extract text from response (may include tool use blocks)
        searched = False
        result_text = ""
        for block in response.content:
            if block.type == "text":
                result_text += block.text
            elif block.type == "web_search_tool_use":
                searched = True

        # Parse KATEGÓRIA from response
        cat_match = re.search(r'KATEGÓRIA:\s*(.+?)(?:\n|$)', result_text)
        reason_match = re.search(r'INDOKLÁS:\s*(.+?)(?:\n|$)', result_text, re.DOTALL)

        if cat_match:
            category = cat_match.group(1).strip().strip('"\'')
            reasoning = reason_match.group(1).strip() if reason_match else ""

            # Validate against known categories
            if category not in valid_categories:
                # Try fuzzy match
                for valid in valid_categories:
                    if valid.lower() in category.lower() or category.lower() in valid.lower():
                        category = valid
                        break
                else:
                    # Default to egyéb
                    reasoning += f" [Eredeti válasz: {category}, nem ismert kategória]"
                    category = "egyéb oktatási szervezetek"

            return category, reasoning, searched
        else:
            return "egyéb oktatási szervezetek", f"Nem sikerült parse-olni: {result_text[:200]}", searched

    except Exception as e:
        return "egyéb oktatási szervezetek", f"HIBA: {str(e)}", False


def classify_batch_simple(client, orgs_batch, categories_text, valid_categories):
    """
    Classify a batch of obvious orgs (where name clearly indicates type) without web search.
    Returns list of (category, reasoning).
    """
    orgs_text = ""
    for i, org in enumerate(orgs_batch, 1):
        orgs_text += f"\n{i}. {org['name']}\n   Székhely: {org['hq']}\n   Cél: {org['purpose'][:300] if org['purpose'] else 'Nincs'}\n"

    prompt = f"""Kategorizáld az alábbi magyar oktatási szervezeteket.
Válassz PONTOSAN EGY kategóriát minden szervezethez.

ELÉRHETŐ KATEGÓRIÁK:
{categories_text}

SZERVEZETEK:
{orgs_text}

VÁLASZ: Minden szervezethez egy sor, a formátum:
szám. kategória neve | rövid indoklás"""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4000,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        results = []
        for line in text.split('\n'):
            line = line.strip()
            if not line or not line[0].isdigit():
                continue
            # Parse "1. category | reason"
            match = re.match(r'\d+\.\s*(.+?)(?:\s*\|\s*(.+))?$', line)
            if match:
                cat = match.group(1).strip().strip('"\'')
                reason = match.group(2).strip() if match.group(2) else ""
                # Validate
                if cat not in valid_categories:
                    for valid in valid_categories:
                        if valid.lower() in cat.lower() or cat.lower() in valid.lower():
                            cat = valid
                            break
                    else:
                        cat = "egyéb oktatási szervezetek"
                results.append((cat, reason))
        return results
    except Exception as e:
        print(f"   Batch hiba: {e}")
        return [("egyéb oktatási szervezetek", f"HIBA: {e}")] * len(orgs_batch)


def main():
    print("=" * 70)
    print("OKTATÁSI SZERVEZETEK ÚJ KATEGORIZÁLÁSA")
    print("Web kereséssel támogatott LLM klasszifikáció")
    print("=" * 70)

    # Load API key
    api_key = load_api_key()
    print(f"API kulcs betöltve (...{api_key[-8:]})")
    client = Anthropic(api_key=api_key)

    # Load categories
    oktatas_cats = load_oktatas_categories()
    valid_categories = set(oktatas_cats.keys())
    categories_text = format_oktatas_categories(oktatas_cats)
    print(f"\n{len(oktatas_cats)} oktatási alkategória betöltve:")
    for name in oktatas_cats:
        print(f"  • {name}")

    # Load orgs
    df_oktat = load_oktatas_orgs()
    print(f"\n{len(df_oktat)} oktatási szervezet betöltve")
    print(f"\nJelenlegi eloszlás:")
    print(df_oktat['Új kategória (legalsó szint)'].value_counts().to_string())

    # Check for existing progress
    processed_adoszams = set()
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                entry = json.loads(line)
                processed_adoszams.add(entry['adoszam'])
        print(f"\n{len(processed_adoszams)} szervezet már feldolgozva (folytatás)")

    # Process each org
    remaining = df_oktat[~df_oktat['Adószám'].astype(str).isin(processed_adoszams)]
    total = len(remaining)
    print(f"\n{total} szervezet feldolgozandó")

    # Phase 1: Batch classify orgs where category seems obvious
    # (óvodák, gimnáziumok, ált. iskolák with clear names)
    # Phase 2: Individual classify with web search for ambiguous ones

    searched_count = 0
    batch_count = 0
    error_count = 0

    # Collect all orgs with their data
    org_list = []
    print("\nSzervezet adatok betöltése...")
    for idx, (_, row) in enumerate(remaining.iterrows()):
        adoszam = str(row['Adószám'])
        name = row['Szervezet neve']
        csv_purpose = str(row.get('Cél (első 200 karakter)', ''))
        if csv_purpose == 'nan':
            csv_purpose = ''

        # Try to get fuller data from JSON
        json_purpose, json_hq, json_name = get_org_json_data(adoszam)
        purpose = json_purpose if json_purpose else csv_purpose
        hq = json_hq if json_hq else ''
        full_name = json_name if json_name else name

        org_list.append({
            'adoszam': adoszam,
            'name': full_name,
            'csv_name': name,
            'purpose': purpose,
            'hq': hq,
            'old_category': row['Új kategória (legalsó szint)']
        })

    print(f"{len(org_list)} szervezet adatai betöltve")

    # Process in batches of 10 for efficiency, with web search fallback
    BATCH_SIZE = 10
    log_file = open(LOG_PATH, 'a', encoding='utf-8')

    try:
        for i in range(0, len(org_list), BATCH_SIZE):
            batch = org_list[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            total_batches = (len(org_list) + BATCH_SIZE - 1) // BATCH_SIZE

            print(f"\n--- Batch {batch_num}/{total_batches} ({i+1}-{min(i+BATCH_SIZE, len(org_list))}/{len(org_list)}) ---")

            # First try batch classification
            results = classify_batch_simple(client, batch, categories_text, valid_categories)

            if len(results) != len(batch):
                print(f"   Batch eredmény nem egyezik ({len(results)} vs {len(batch)}), egyénileg dolgozom fel")
                results = [(None, None)] * len(batch)

            for j, org in enumerate(batch):
                cat = results[j][0] if j < len(results) and results[j][0] else None
                reason = results[j][1] if j < len(results) and results[j][1] else ""
                searched = False

                # If batch result is "egyéb iskolák" or "egyéb oktatási szervezetek" and
                # old category was also ambiguous, try individual with web search
                needs_search = (
                    cat is None or
                    (cat == "egyéb oktatási szervezetek" and org['old_category'] in
                     ['egyéb iskolák', 'egyéb oktatási szervezetek']) or
                    (cat == org['old_category'] and cat in ['egyéb iskolák', 'egyéb oktatási szervezetek'])
                )

                if needs_search:
                    print(f"   🔍 Web keresés: {org['name'][:60]}...")
                    cat, reason, searched = classify_single_org(
                        client, org['name'], org['purpose'], org['hq'],
                        categories_text, valid_categories
                    )
                    if searched:
                        searched_count += 1
                    time.sleep(0.5)  # Rate limit for web search

                changed = cat != org['old_category']
                symbol = "🔄" if changed else "✓"
                search_symbol = " 🌐" if searched else ""
                print(f"   {symbol} {org['csv_name'][:50]}: {org['old_category']} → {cat}{search_symbol}")

                # Log result
                entry = {
                    'adoszam': org['adoszam'],
                    'name': org['csv_name'],
                    'old_category': org['old_category'],
                    'new_category': cat,
                    'reasoning': reason,
                    'searched': searched,
                    'changed': changed
                }
                log_file.write(json.dumps(entry, ensure_ascii=False) + '\n')
                log_file.flush()
                batch_count += 1

            # Small delay between batches
            time.sleep(0.3)

    except KeyboardInterrupt:
        print("\n\n⚠️  Megszakítva! Az eddigi eredmények elmentve.")
    finally:
        log_file.close()

    # Summary
    print("\n" + "=" * 70)
    print("ÖSSZEFOGLALÓ")
    print("=" * 70)
    print(f"Feldolgozva: {batch_count}")
    print(f"Web kereséssel: {searched_count}")

    # Load all results and create summary
    if os.path.exists(LOG_PATH):
        results = []
        with open(LOG_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                results.append(json.loads(line))

        changed = sum(1 for r in results if r['changed'])
        print(f"Változott kategória: {changed}/{len(results)}")

        # Show new distribution
        from collections import Counter
        new_dist = Counter(r['new_category'] for r in results)
        print(f"\nÚj eloszlás:")
        for cat, count in sorted(new_dist.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count}")

        # Save results CSV
        results_df = pd.DataFrame(results)
        results_df.to_csv(RESULTS_PATH, index=False, encoding='utf-8-sig')
        print(f"\nEredmények mentve: {RESULTS_PATH}")
        print(f"Részletes log: {LOG_PATH}")


def apply_results():
    """Apply the reclassification results to the main CSV and JSON files."""
    print("=" * 70)
    print("EREDMÉNYEK ALKALMAZÁSA")
    print("=" * 70)

    if not os.path.exists(LOG_PATH):
        print("Nincs eredmény fájl! Futtasd először a klasszifikációt.")
        return

    # Load results
    results = {}
    with open(LOG_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            entry = json.loads(line)
            results[str(entry['adoszam'])] = entry

    print(f"{len(results)} eredmény betöltve")
    changed = {k: v for k, v in results.items() if v['changed']}
    print(f"{len(changed)} szervezet kategóriája változott")

    if not changed:
        print("Nincs változás az alkalmazáshoz.")
        return

    # Update CSV
    df = pd.read_csv(CSV_PATH)
    csv_changes = 0
    for idx, row in df.iterrows():
        adoszam = str(row['Adószám'])
        if adoszam in changed:
            new_cat = changed[adoszam]['new_category']
            df.at[idx, 'Új kategória (legalsó szint)'] = new_cat
            # parent stays "oktatás"
            csv_changes += 1

    df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
    print(f"CSV frissítve: {csv_changes} sor")

    # Update JSON files
    json_changes = 0
    for adoszam, result in changed.items():
        for fn in os.listdir(ORGS_DIR):
            if fn.startswith(f'org_{adoszam}') and fn.endswith('.json'):
                path = os.path.join(ORGS_DIR, fn)
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                data['leaf_category'] = result['new_category']
                data['parent_category'] = 'oktatás'
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                json_changes += 1
                break

    print(f"JSON fájlok frissítve: {json_changes}")
    print("\nKész! A dashboard újraindítás után az új kategóriákat fogja mutatni.")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Re-classify Oktatás organizations')
    parser.add_argument('--apply', action='store_true', help='Apply results to CSV and JSON files')
    args = parser.parse_args()

    if args.apply:
        apply_results()
    else:
        main()
