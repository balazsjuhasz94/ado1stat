import json
import csv
import re
from pathlib import Path
from typing import Dict, List

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

def categorize_organization(name: str, goal: str) -> str:
    """
    Categorize organization based on name and goal using intelligent pattern matching.
    Returns the most specific (leaf) category.
    """
    name_lower = name.lower()
    goal_lower = goal.lower()
    combined = name_lower + " " + goal_lower

    # EGÉSZSÉGÜGY - GYERMEK (highest priority for child health)
    if any(word in combined for word in ['koraszülött', 'újszülött', 'csecsemő']):
        return "koraszülöttek"

    if any(word in combined for word in ['leukémia', 'leukémiás']) and any(word in combined for word in ['gyermek', 'gyerek']):
        return "leukémiás és daganatos gyerekek"

    if any(word in combined for word in ['daganat', 'rák', 'onkológi']) and any(word in combined for word in ['gyermek', 'gyerek']):
        return "leukémiás és daganatos gyerekek"

    if 'cukorbeteg' in combined and any(word in combined for word in ['gyermek', 'gyerek']):
        return "cukorbeteg gyerekek"

    if 'bohócdoktor' in combined or 'piros orr' in combined or ('bohóc' in combined and 'gyermek' in combined):
        return "beteg gyerekek lelki segítése"

    if 'gyermekkórház' in combined or 'gyermekklinika' in combined:
        return "gyermekkórházak"

    # Specific child names (Kornél, Zsombor, etc.)
    if re.search(r'(kornél|zsombor|bence|máté|dávid|ádám)ért', combined) and any(word in combined for word in ['beteg', 'gyógyít', 'támogat']):
        return "konkrét beteg gyerekek"

    # General child health
    if any(word in combined for word in ['gyermek', 'gyerek']) and any(word in combined for word in ['beteg', 'egészség', 'kórház', 'gyógyít']):
        return "egyéb gyermek egészségügy"

    # EGÉSZSÉGÜGY - FELNŐTT
    if 'hospice' in combined or 'haldokl' in combined or 'terminális' in combined:
        return "beteg emberek lelki és szociális támogatása"

    if 'mentőszolgálat' in combined or 'mentő alapítvány' in combined or 'légimentés' in combined:
        return "országos szervezetek"

    if 'daganat' in combined or 'rák' in combined or 'onkológi' in combined:
        return "daganatos betegek gyógyítása"

    if 'női egészség' in combined or 'nőgyógyász' in combined:
        return "női egészségügy"

    if 'kórház' in combined and 'gyermek' not in combined:
        return "kórházak"

    if any(word in combined for word in ['beteg', 'gyógyít', 'egészség', 'klinika']) and 'gyermek' not in combined:
        return "egyéb felnőtt egészségügy"

    # ÁLLATVÉDELEM
    if 'kuty' in combined or 'eb' in combined:
        if 'vakvezető' in combined or 'segítő kutya' in combined:
            return "vakok"
        return "kutyák"

    if 'macska' in combined or 'cica' in combined:
        return "macskák"

    if 'madár' in combined or 'madárkórház' in combined:
        return "madarak"

    if 'nyúl' in combined or 'ló' in combined or 'egzotikus' in combined:
        return "egyéb konkrét állatok"

    if 'állatkert' in combined or 'állatpark' in combined or 'zoo' in combined:
        return "állatkertek"

    if 'állat' in combined or 'állatvéd' in combined or 'állatment' in combined or 'állatotthon' in combined:
        return "egyéb állatvédelem"

    # SZOCIÁLIS SZERVEZETEK
    if 'vak' in combined or 'gyengénlátó' in combined or 'látássérült' in combined:
        return "vakok"

    if 'süket' in combined or 'hallássérült' in combined or 'siket' in combined:
        return "süketek"

    if 'autist' in combined or 'autizmus' in combined:
        return "autistiák"

    if 'fogyatékos' in combined or 'fogyatékkal élő' in combined or 'mozgássérült' in combined or 'Down' in combined:
        return "egyéb fogyatékkal élők"

    if 'gyermekvéd' in combined or 'bántalmazott gyerek' in combined:
        return "gyermekvédelem"

    if 'családsegít' in combined or 'családok' in combined and 'támogat' in combined:
        return "családsegítők"

    if any(word in combined for word in ['hátrányos helyzetű', 'szegény', 'rászoruló']) and 'gyerek' in combined:
        return "hátrányos helyzetű gyerekek támogatása"

    if 'gyermekétkez' in combined or 'gyerekek táplálás' in combined:
        return "hátrányos helyzetű gyerekek támogatása"

    if 'hajléktalan' in combined or 'nélkülöző' in combined or 'szegény' in combined or 'rászoruló' in combined:
        return "rászorulók segítése"

    if 'máltai' in combined or 'karit' in combined or ('egyház' in combined and 'szociális' in combined):
        return "egyházhoz kötődő szociális szervezetek"

    if 'oltalom' in combined and 'egyesület' in combined:
        return "egyházhoz kötődő szociális szervezetek"

    # OKTATÁSI SZERVEZETEK
    if 'tehetség' in combined or 'tehetséggondoz' in combined:
        return "tehetséggondozás"

    if 'gimnázium' in combined or 'középiskola' in combined:
        if 'budapest' in combined:
            return "budapesti gimnáziumok"
        else:
            return "Budapesten kívüli gimnáziumok"

    if 'általános iskola' in combined:
        return "általános iskolák"

    if any(word in combined for word in ['iskola', 'óvoda', 'szakiskola', 'szakgimnázium']):
        return "egyéb iskolák"

    if any(word in combined for word in ['oktat', 'képzés', 'tanul', 'diák']):
        return "egyéb oktatás szervezetek"

    # KULTURÁLIS SZERVEZETEK
    if any(word in combined for word in ['újság', 'média', 'sajtó', 'rádió', 'tv', 'televízió', 'hír']):
        return "sajtó, média"

    if any(word in combined for word in ['átlátszó', 'demokrácia', 'civil', 'jogvéd', 'szabadság', 'emberi jog', 'választó']):
        if 'nő' in combined or 'női' in combined:
            return "nőjogi szervezetek"
        if 'lgbtq' in combined or 'meleg' in combined or 'leszbikus' in combined or 'transznemű' in combined:
            return "nemi kisebbségek"
        return "demokráciát tevő szervezetek"

    if any(word in combined for word in ['egyház', 'keresztyén', 'keresztény', 'biblia', 'vallás', 'hit', 'templom']):
        return "vallás népszerűsítés"

    if any(word in combined for word in ['roma', 'horvát', 'német', 'szerb', 'szlovák', 'nemzetiség', 'etnikai']):
        return "etnikai szervezetek"

    if any(word in combined for word in ['művész', 'zene', 'színház', 'film', 'tánc', 'képzőművész', 'fúvós', 'kórus']):
        return "művészeti szervezetek"

    if 'kulturál' in combined or 'kultúra' in combined:
        return "egyéb kulturális szervezetek"

    # KÖRNYEZET ÉS TERMÉSZETVÉDELEM
    if any(word in combined for word in ['környezet', 'természetvéd', 'fa', 'erdő', 'zöld', 'biodiverzitás', 'klíma']):
        return "környezet és természetvédelem"

    # SPORT ÉS SZABADIDŐ
    if 'vadász' in combined:
        return "vadásztársaságok"

    if any(word in combined for word in ['sport', 'futball', 'kézilabda', 'labdarúg', 'atlétika', 'kosárlabda']):
        return "sportklubok"

    if 'cserkész' in combined or 'szabadidő' in combined or 'hobby' in combined:
        return "egyéb szabadidős szervezetek"

    # KATASZTRÓFAVÉDELEM
    if 'tűzoltó' in combined or 'katasztrófa' in combined or 'mentő' in combined:
        if 'országos' in combined:
            return "országos szervezetek"
        return "helyi szervezetek"

    # JOGVÉDŐ SZERVEZETEK
    if 'nőjog' in combined or 'nők jog' in combined:
        return "nőjogi szervezetek"

    if 'lgbtq' in combined or 'nemi kisebbség' in combined:
        return "nemi kisebbségek"

    if 'jogvéd' in combined or 'emberi jog' in combined:
        return "egyéb jogvédő szervezetek"

    # FALLBACK
    return "Kategorizálatlan"

def main():
    # Load organizations
    input_file = Path(r"c:\Users\juhib\home_projects\ado1\organizations_to_categorize.json")
    with open(input_file, 'r', encoding='utf-8') as f:
        organizations = json.load(f)

    print(f"Loaded {len(organizations)} organizations")

    # Categorize all organizations
    for i, org in enumerate(organizations):
        category = categorize_organization(org['name'], org['goal'])
        org['category'] = category

        if (i + 1) % 100 == 0:
            print(f"Processed {i + 1}/{len(organizations)} organizations...")

    print(f"Categorization complete!")

    # Save results to CSV
    output_file = Path(r"c:\Users\juhib\home_projects\ado1\organization_categories_llm.csv")
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Szervezet neve', 'Új kategória (legalsó szint)',
                        'Szülő kategória 1', 'Szülő kategória 2', 'Cél (első 200 karakter)'])

        for org in organizations:
            category = org.get('category', 'Kategorizálatlan')
            parents = CATEGORIES_MAP.get(category, [])
            parent1 = parents[0] if len(parents) > 0 else ""
            parent2 = parents[1] if len(parents) > 1 else ""
            goal_truncated = org['goal'][:200] if org['goal'] else ""

            writer.writerow([
                org['name'],
                category,
                parent1,
                parent2,
                goal_truncated
            ])

    print(f"\nResults saved to: {output_file}")

    # Print statistics
    category_counts = {}
    for org in organizations:
        cat = org.get('category', 'Kategorizálatlan')
        category_counts[cat] = category_counts.get(cat, 0) + 1

    print("\n=== CATEGORIZATION STATISTICS ===")
    print(f"Total organizations: {len(organizations)}")
    print(f"Uncategorized: {category_counts.get('Kategorizálatlan', 0)}")
    print(f"\nAll categories (sorted by count):")

    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat}: {count}")

if __name__ == "__main__":
    main()
