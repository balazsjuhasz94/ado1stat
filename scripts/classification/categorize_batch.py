import json
import csv
from pathlib import Path

# Category hierarchy mapping
CATEGORIES_MAP = {
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

    # Fallback
    "Kategorizálatlan": [],
}

def load_organizations():
    """Load organizations from JSON file"""
    input_file = Path(r"c:\Users\juhib\home_projects\ado1\organizations_to_categorize.json")
    with open(input_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_categorized_orgs(categorized_orgs, output_file):
    """Save categorized organizations to CSV"""
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Szervezet neve', 'Új kategória (legalsó szint)',
                        'Szülő kategória 1', 'Szülő kategória 2', 'Cél (első 200 karakter)'])

        for org in categorized_orgs:
            category = org.get('category', 'Kategorizálatlan')

            # Get parent categories
            parents = CATEGORIES_MAP.get(category, [])
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

def print_batch_for_categorization(organizations, start_idx, batch_size=50):
    """Print a batch of organizations for manual categorization"""
    end_idx = min(start_idx + batch_size, len(organizations))

    print(f"\n=== BATCH {start_idx//batch_size + 1}: Organizations {start_idx+1}-{end_idx} ===\n")

    for i in range(start_idx, end_idx):
        org = organizations[i]
        print(f"{i}. {org['name']}")
        print(f"   Cél: {org['goal'][:300]}...")
        print()

def apply_categorization(organizations, categorization_dict):
    """Apply categorization to organizations"""
    for idx, category in categorization_dict.items():
        if idx < len(organizations):
            organizations[idx]['category'] = category
    return organizations

def print_statistics(organizations):
    """Print categorization statistics"""
    category_counts = {}
    uncategorized_count = 0

    for org in organizations:
        cat = org.get('category', 'Kategorizálatlan')
        if cat is None or cat == 'Kategorizálatlan':
            uncategorized_count += 1
        category_counts[cat] = category_counts.get(cat, 0) + 1

    print("\n=== CATEGORIZATION STATISTICS ===")
    print(f"Total organizations: {len(organizations)}")
    print(f"Categorized: {len(organizations) - uncategorized_count}")
    print(f"Uncategorized: {uncategorized_count}")
    print(f"\nTop 30 categories:")

    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:30]:
        print(f"  {cat}: {count}")

if __name__ == "__main__":
    # Load organizations
    organizations = load_organizations()
    print(f"Loaded {len(organizations)} organizations")

    # Print first batch
    print_batch_for_categorization(organizations, 0, 50)
