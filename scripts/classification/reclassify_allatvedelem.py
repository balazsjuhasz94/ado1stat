"""
Re-classify KÖRNYEZET- ÉS ÁLLATVÉDELEM organizations.
The 2026 full-corpus classification run systematically confused two leaf
categories: 'más konkrét állatfajok' (a specific non-dog/cat/bird species)
vs. 'egyéb állatvédelem' (general multi-species shelters), lumping many
general animal shelters into the former. This re-runs just that parent
category with a prompt that makes the distinction explicit.

Usage: python scripts/classification/reclassify_allatvedelem.py
       python scripts/classification/reclassify_allatvedelem.py --apply
"""
import json
import os
import sys
import time
import argparse

import pandas as pd
from anthropic import Anthropic

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
ORGS_DIR = os.path.join(BASE_DIR, 'organizations_by_adoszam')
CSV_PATH = os.path.join(DATA_DIR, 'organization_categories_ALL_10000.csv')
API_KEY_PATH = os.path.join(DATA_DIR, 'api.txt')
LOG_PATH = os.path.join(DATA_DIR, 'allatvedelem_reclassification_log.jsonl')

PARENT = 'környezet- és állatvédelem'
ANIMAL_LEAVES = {
    'kutyák', 'macskák', 'madarak', 'más konkrét állatfajok', 'állatkertek',
    'egyéb állatvédelem', 'környezet- és természetvédelem',
}

CATEGORIES_TEXT = """
• környezet- és természetvédelem
  Használd, ha FÓKUSZA természetvédelem, környezetvédelem, ökológia --
  NEM konkrét állatok mentése/gondozása. Pl.: Greenpeace, WWF, madártani
  (ornitológiai) TÁRSASÁGOK kutatási/védelmi céllal, erdőtelepítés,
  klímavédelem, vízvédelem, hulladékcsökkentés, természetvédelmi
  területek, folyóvédelem. Ha a szervezet neve "Természetvédelmi",
  "Környezetvédő" és NEM konkrét állatmentésről/menhelyről szól, ide
  tartozik, még ha van benne "állat" szó is (pl. "Állat- és
  Természetvédő Egyesület" általános névvel, kutatás/oktatás fókusszal).

• kutyák
  Használd, ha FÓKUSZA kutyák védelme, mentése, gondozása.

• macskák
  Használd, ha FÓKUSZA macskák védelme, mentése, gondozása.

• madarak
  Használd, ha FÓKUSZA madarak védelme (gólyák, ragadozó madarak, madárgyűrűzés, stb.)

• más konkrét állatfajok
  Használd, ha FÓKUSZA EGY KONKRÉT állatfaj, ami NEM kutya/macska/madár.
  Pl.: lovak, nyulak, tengerimalacok, hörcsögök, görények, vadállatok,
  egzotikus állatok, víziállatok, hüllők, sünik. A szervezet nevében vagy
  céljában egyértelműen szerepel EGY konkrét faj.

• állatkertek
  Használd, ha FÓKUSZA állatkert, vadaspark támogatása.

• egyéb állatvédelem
  Használd, ha a szervezet ÁLTALÁNOS, TÖBB FAJRA kiterjedő állatmenhely,
  állatotthon vagy állatmentő szervezet -- azaz NEM egy konkrét fajra
  specializálódott, hanem kutyákat, macskákat és/vagy egyéb állatokat
  vegyesen fogad be/ment (konkrét mentés/gondozás, nem kutatás/oktatás).
  Ide tartoznak az "állatotthon", "állatmenhely", "állatmentő",
  "állatbarát", "állatvédő" nevű ÁLTALÁNOS szervezetek, még akkor is, ha
  a gyakorlatban főleg kutyákkal/macskákkal foglalkoznak -- hacsak a
  nevük/céljuk nem specifikusan EGY fajra utal.
"""


def load_api_key():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and os.path.exists(API_KEY_PATH):
        with open(API_KEY_PATH, 'r', encoding='utf-8') as f:
            api_key = f.read().strip()
    if not api_key:
        raise ValueError("No ANTHROPIC_API_KEY found")
    return api_key


def get_org_purpose(adoszam):
    for fn in os.listdir(ORGS_DIR):
        if fn.startswith(f'org_{adoszam}_') and fn.endswith('.json'):
            with open(os.path.join(ORGS_DIR, fn), 'r', encoding='utf-8') as f:
                data = json.load(f)
            fonadatok = data.get('alapadatok', {}).get('fonadatok', {})
            return fonadatok.get('céljának_leírása', '') or ''
    return ''


def classify_batch(client, orgs):
    orgs_text = ""
    for i, org in enumerate(orgs, 1):
        orgs_text += f"\n{i}. {org['name']}\n   Cél: {org['purpose'][:300] if org['purpose'] else 'Nincs leírás'}\n"

    prompt = f"""Kategorizáld az alábbi magyar állatvédelmi civil szervezeteket PONTOSAN EGY kategóriába.

KATEGÓRIÁK:
{CATEGORIES_TEXT}

SZERVEZETEK:
{orgs_text}

VÁLASZ FORMÁTUM - csak számozott lista, minden sorban: szám. kategória"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()
        results = []
        for line in text.split('\n'):
            line = line.strip()
            if not line or not line[0].isdigit() or '. ' not in line:
                continue
            cat = line.split('. ', 1)[1].strip().strip('"\'')
            results.append(cat)
        while len(results) < len(orgs):
            results.append(None)
        return results[:len(orgs)]
    except Exception as e:
        print(f"   HIBA: {e}")
        return [None] * len(orgs)


def main():
    api_key = load_api_key()
    client = Anthropic(api_key=api_key)

    df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
    df['Adószám'] = df['Adószám'].astype(str)
    subset = df[df['Szülő kategória'] == PARENT].copy()
    print(f"{len(subset)} szervezet a(z) '{PARENT}' kategóriában")
    print(subset['Új kategória (legalsó szint)'].value_counts().to_string())

    orgs = []
    for _, row in subset.iterrows():
        orgs.append({
            'adoszam': row['Adószám'],
            'name': row['Szervezet neve'],
            'old_category': row['Új kategória (legalsó szint)'],
            'purpose': get_org_purpose(row['Adószám']),
        })

    results = []
    BATCH = 10
    with open(LOG_PATH, 'w', encoding='utf-8') as log_file:
        for i in range(0, len(orgs), BATCH):
            batch = orgs[i:i + BATCH]
            cats = classify_batch(client, batch)
            for org, cat in zip(batch, cats):
                if cat is None or cat not in ANIMAL_LEAVES:
                    cat = org['old_category']  # keep as-is if parse failed
                changed = cat != org['old_category']
                entry = {'adoszam': org['adoszam'], 'name': org['name'],
                         'old_category': org['old_category'], 'new_category': cat, 'changed': changed}
                results.append(entry)
                log_file.write(json.dumps(entry, ensure_ascii=False) + '\n')
                if changed:
                    print(f"  {org['name'][:55]:<55} {org['old_category']} -> {cat}")
            log_file.flush()
            time.sleep(0.5)

    changed_count = sum(1 for r in results if r['changed'])
    print(f"\nFeldolgozva: {len(results)}  Változott: {changed_count}")
    print(f"Log mentve: {LOG_PATH}")


def apply_results():
    if not os.path.exists(LOG_PATH):
        print("Nincs log fájl, futtasd előbb klasszifikáció nélkül.")
        return
    results = {}
    with open(LOG_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            entry = json.loads(line)
            results[str(entry['adoszam'])] = entry

    changed = {k: v for k, v in results.items() if v['changed']}
    print(f"{len(changed)} szervezet kategóriája változik")

    df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
    df['Adószám'] = df['Adószám'].astype(str)
    for idx, row in df.iterrows():
        adoszam = row['Adószám']
        if adoszam in changed:
            df.at[idx, 'Új kategória (legalsó szint)'] = changed[adoszam]['new_category']
    df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
    print(f"CSV frissítve: {CSV_PATH}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if args.apply:
        apply_results()
    else:
        main()
