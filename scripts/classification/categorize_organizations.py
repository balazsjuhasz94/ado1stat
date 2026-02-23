import json
import os
import csv
from pathlib import Path
import anthropic
from typing import Dict, List, Tuple
import time

# Load categories from YAML
def load_categories():
    """Load and parse the category hierarchy to find all leaf categories"""
    categories = {
        # Kulturális szervezetek
        "sajtó, média": ["kulturális szervezetek"],
        "vallás népszerűsítés": ["kulturális szervezetek"],
        "etnikai szervezetek": ["kulturális szervezetek"],
        "művészeti szervezetek": ["kulturális szervezetek"],
        "demokráciát tevő szervezetek": ["kulturális szervezetek"],
        "egyéb kulturális szervezetek": ["kulturális szervezetek"],

        # Oktatási szervezetek
        "tehetséggondozás": ["oktatási szervezetek"],
        "budapesti gimnáziumok": ["oktatási szervezetek", "oktatási intézmények"],
        "Budapesten kívüli gimnáziumok": ["oktatási szervezetek", "oktatási intézmények"],
        "általános iskolák": ["oktatási szervezetek", "oktatási intézmények"],
        "egyéb iskolák": ["oktatási szervezetek", "oktatási intézmények"],
        "egyéb oktatás szervezetek": ["oktatási szervezetek"],

        # Jogvédő szervezetek
        "nőjogi szervezetek": ["jogvédő szervezetek"],
        "nemi kisebbségek": ["jogvédő szervezetek"],
        "egyéb jogvédő szervezetek": ["jogvédő szervezetek"],

        # Állatvédelem
        "kutyák": ["állatvédelem"],
        "macskák": ["állatvédelem"],
        "madarak": ["állatvédelem"],
        "egyéb konkrét állatok": ["állatvédelem"],
        "állatkertek": ["állatvédelem"],
        "egyéb állatvédelem": ["állatvédelem"],

        # Szociális szervezetek
        "rászorulók segítése": ["szociális szervezetek"],
        "hátrányos helyzetű gyerekek támogatása": ["szociális szervezetek"],
        "gyermekvédelem": ["szociális szervezetek"],
        "családsegítők": ["szociális szervezetek"],
        "vakok": ["szociális szervezetek", "fogyatékkal élők"],
        "süketek": ["szociális szervezetek", "fogyatékkal élők"],
        "autistiák": ["szociális szervezetek", "fogyatékkal élők"],
        "egyéb fogyatékkal élők": ["szociális szervezetek", "fogyatékkal élők"],
        "beteg emberek lelki és szociális támogatása": ["szociális szervezetek"],
        "egyházhoz kötődő szociális szervezetek": ["szociális szervezetek"],

        # Katasztrófavédelem
        "országos szervezetek": ["katasztófavédelem"],
        "helyi szervezetek": ["katasztófavédelem"],

        # Egészségügy - Felnőtt
        "kórházak": ["egészségügy", "felnőtt egészségügy"],
        "női egészségügy": ["egészségügy", "felnőtt egészségügy"],
        "daganatos betegek gyógyítása": ["egészségügy", "felnőtt egészségügy"],
        "egyéb felnőtt egészségügy": ["egészségügy", "felnőtt egészségügy"],

        # Egészségügy - Gyermek
        "gyermekkórházak": ["egészségügy", "gyermek egészségügy"],
        "beteg gyerekek lelki segítése": ["egészségügy", "gyermek egészségügy"],
        "koraszülöttek": ["egészségügy", "gyermek egészségügy"],
        "cukorbeteg gyerekek": ["egészségügy", "gyermek egészségügy"],
        "leukémiás és daganatos gyerekek": ["egészségügy", "gyermek egészségügy"],
        "konkrét beteg gyerekek": ["egészségügy", "gyermek egészségügy"],
        "egyéb gyermek egészségügy": ["egészségügy", "gyermek egészségügy"],

        # Other top-level
        "környezet és természetvédelem": [],
        "sportklubok": ["szabadidős és sporttevékenységek"],
        "vadásztársaságok": ["szabadidős és sporttevékenységek"],
        "egyéb szabadidős szervezetek": ["szabadidős és sporttevékenységek"],
    }
    return categories

def create_category_description():
    """Create a comprehensive description of all categories for the LLM"""
    return """
KATEGÓRIA HIERARCHIA:

KULTURÁLIS SZERVEZETEK:
- sajtó, média: újságírás, média outlets, rádió, TV, online hírek
- vallás népszerűsítés: egyházak, vallási közösségek támogatása
- etnikai szervezetek: nemzeti kisebbségek, etnikai csoportok támogatása
- művészeti szervezetek: képzőművészet, zene, színház, film, irodalom
- demokráciát tevő szervezetek: civil társadalom, politikai részvétel, átláthatóság
- egyéb kulturális szervezetek: egyéb kulturális tevékenységek

OKTATÁSI SZERVEZETEK:
- tehetséggondozás: tehetséges diákok támogatása
- budapesti gimnáziumok: budapesti középiskolák
- Budapesten kívüli gimnáziumok: vidéki középiskolák
- általános iskolák: általános iskolák támogatása
- egyéb iskolák: óvodák, szakiskolák, egyéb oktatási intézmények
- egyéb oktatás szervezetek: oktatás-fejlesztés, továbbképzés, nem formális oktatás

JOGVÉDŐ SZERVEZETEK:
- nőjogi szervezetek: nők jogai, nemi egyenlőség
- nemi kisebbségek: LGBTQ+ közösség támogatása
- egyéb jogvédő szervezetek: emberi jogok, kisebbségi jogok, jogi segítségnyújtás

ÁLLATVÉDELEM:
- kutyák: kutyamentés, kutyaotthonok, kutyák támogatása
- macskák: macskamentés, macska menhelyek
- madarak: vadmadarak védelme, madármentés
- egyéb konkrét állatok: nyulak, lovak, egzotikus állatok
- állatkertek: állatkert fejlesztése, állatkert támogatása
- egyéb állatvédelem: általános állatvédelem, több állatfaj

SZOCIÁLIS SZERVEZETEK:
- rászorulók segítése: hajléktalanok, szegények, idősek támogatása
- hátrányos helyzetű gyerekek támogatása: szegény, marginalizált gyerekek
- gyermekvédelem: bántalmazás elleni védelem, veszélyeztetett gyerekek
- családsegítők: családok támogatása, családi krízis kezelése
- vakok: látássérültek támogatása, vakvezető kutyák
- süketek: hallássérültek, siket közösség
- autistiák: autizmus spektrum zavarral élők támogatása
- egyéb fogyatékkal élők: fizikai, mentális fogyatékkal élők (nem specifikus)
- beteg emberek lelki és szociális támogatása: hospice, terminális betegek
- egyházhoz kötődő szociális szervezetek: karitatív egyházi szervezetek

KATASZTRÓFAVÉDELEM:
- országos szervezetek: országos mentőszolgálatok, tűzoltóság
- helyi szervezetek: helyi önkéntes tűzoltók, helyi mentők

EGÉSZSÉGÜGY - FELNŐTT:
- kórházak: felnőtt kórházak fejlesztése
- női egészségügy: nők egészségügyi ellátása
- daganatos betegek gyógyítása: rák elleni küzdelem felnőtteknél
- egyéb felnőtt egészségügy: egyéb felnőtt betegségek

EGÉSZSÉGÜGY - GYERMEK:
- gyermekkórházak: gyermekkórházak fejlesztése
- beteg gyerekek lelki segítése: bohócdoktorok, pszichológiai támogatás
- koraszülöttek: koraszülött babák mentése
- cukorbeteg gyerekek: gyerekek cukorbetegség kezelése
- leukémiás és daganatos gyerekek: gyerek rákbetegek támogatása
- konkrét beteg gyerekek: egy vagy néhány konkrét gyermek gyógyítására
- egyéb gyermek egészségügy: egyéb gyerek betegségek

EGYÉB:
- környezet és természetvédelem: környezetvédelem, élőhelyek, természet megőrzése
- sportklubok: sportcsapatok, sportolók támogatása
- vadásztársaságok: vadászat szervezése
- egyéb szabadidős szervezetek: hobbik, szabadidős tevékenységek

- Kategorizálatlan: ha semmi nem illik
"""

def categorize_organizations_batch(organizations_data: List[Dict], api_key: str, categories_desc: str) -> List[Dict]:
    """Categorize a batch of organizations using Claude API"""
    client = anthropic.Anthropic(api_key=api_key)

    # Create batch prompt
    batch_text = ""
    for idx, org_data in enumerate(organizations_data):
        name = org_data['name']
        goal = org_data['goal'][:500] if org_data['goal'] else "Nincs célinformáció"
        batch_text += f"\n\n[{idx}] SZERVEZET: {name}\nCÉL: {goal}\n"

    prompt = f"""Kategorizáld az alábbi magyar civil szervezeteket a megadott kategória hierarchia szerint.

{categories_desc}

SZERVEZETEK:
{batch_text}

FONTOS SZABÁLYOK:
1. Mindig a LEGSPECIFIKUSABB (legalsó szintű) kategóriát válaszd
2. Ha egy szervezet több dologgal is foglalkozik, válaszd a LEGDOMINÁNSABB célt
3. NE használj keyword matching-et, ÉRTELMEZD a célt
4. Ha bizonytalan vagy, inkább válassz egy "egyéb..." kategóriát
5. Csak akkor használj "Kategorizálatlan"-t, ha semmi sem illik

VÁLASZ FORMÁTUM (JSON lista, minden szervezetre egy elem):
[
  {{"index": 0, "category": "kategória neve"}},
  {{"index": 1, "category": "kategória neve"}},
  ...
]

Válaszolj CSAK a JSON listával, semmi más szöveggel!"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        response_text = response.content[0].text.strip()

        # Parse JSON response
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        results = json.loads(response_text)

        # Match results back to organizations
        categorized = []
        for result in results:
            idx = result['index']
            if idx < len(organizations_data):
                org_data = organizations_data[idx]
                org_data['category'] = result['category']
                categorized.append(org_data)

        return categorized

    except Exception as e:
        print(f"Error in batch categorization: {e}")
        # Return with "Kategorizálatlan" as fallback
        for org_data in organizations_data:
            org_data['category'] = "Kategorizálatlan"
        return organizations_data

def main():
    # Load categories
    categories_map = load_categories()
    categories_desc = create_category_description()

    # API key
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        return

    # Load all organizations
    org_dir = Path(r"c:\Users\juhib\home_projects\ado1\organizations")
    org_files = list(org_dir.glob("*.json"))

    print(f"Found {len(org_files)} organization files")

    organizations_data = []

    # Read all organizations
    for org_file in org_files:
        try:
            with open(org_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

                # Extract relevant information
                name = data.get('name', 'Ismeretlen')
                goal = ""

                if 'alapadatok' in data and 'fonadatok' in data['alapadatok']:
                    goal = data['alapadatok']['fonadatok'].get('céljának_leírása', '')

                organizations_data.append({
                    'name': name,
                    'goal': goal,
                    'file': org_file.name,
                    'category': None
                })
        except Exception as e:
            print(f"Error reading {org_file}: {e}")

    print(f"Successfully loaded {len(organizations_data)} organizations")

    # Process in batches (10 at a time to avoid token limits)
    batch_size = 10
    categorized_orgs = []

    for i in range(0, len(organizations_data), batch_size):
        batch = organizations_data[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(organizations_data) + batch_size - 1)//batch_size}...")

        categorized_batch = categorize_organizations_batch(batch, api_key, categories_desc)
        categorized_orgs.extend(categorized_batch)

        # Small delay to respect API rate limits
        time.sleep(1)

    # Write results to CSV
    output_file = Path(r"c:\Users\juhib\home_projects\ado1\organization_categories_llm.csv")

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Szervezet neve', 'Új kategória (legalsó szint)',
                        'Szülő kategória 1', 'Szülő kategória 2', 'Cél (első 200 karakter)'])

        for org in categorized_orgs:
            category = org.get('category', 'Kategorizálatlan')

            # Get parent categories
            parents = categories_map.get(category, [])
            parent1 = parents[0] if len(parents) > 0 else ""
            parent2 = parents[1] if len(parents) > 1 else ""

            # Truncate goal
            goal_truncated = org['goal'][:200] if org['goal'] else ""

            writer.writerow([
                org['name'],
                category,
                parent1,
                parent2,
                goal_truncated
            ])

    print(f"\nResults written to {output_file}")

    # Statistics
    category_counts = {}
    for org in categorized_orgs:
        cat = org.get('category', 'Kategorizálatlan')
        category_counts[cat] = category_counts.get(cat, 0) + 1

    print("\n=== STATISTICS ===")
    print(f"Total organizations: {len(categorized_orgs)}")
    print(f"\nTop 20 categories:")
    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:20]:
        print(f"  {cat}: {count}")

if __name__ == "__main__":
    main()
