"""
Backfill JSON files for the small number of 2026 new-entrant orgs that
civil.info.hu search couldn't find, using the official xlsx as the source
of truth for name/address/amount (same pattern as create_json_for_errors.py
used for the original 2025 dataset).
"""
import json
import os
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
ORG_DIR = os.path.join(PROJECT_ROOT, 'organizations_by_adoszam')
XLSX_2026 = os.path.join(DATA_DIR, 'Szja 1-os felajanlasban reszesult civil kedvezményezettek_2026.xlsx')


def main():
    import pandas as pd

    df26 = pd.read_excel(XLSX_2026, sheet_name='Munka1', header=1)
    df26['Adószám'] = df26['Adószám'].astype(str)
    lookup = {
        row['Adószám']: (row['Név'], row['Székhely'], int(row['Felajánlott összeg (Ft)']), int(row['Felajánlók száma (fő)']))
        for _, row in df26.iterrows()
    }

    fixed = 0
    still_missing = []
    for filename in os.listdir(ORG_DIR):
        if not filename.endswith('.json'):
            continue
        filepath = os.path.join(ORG_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            d = json.load(f)
        if not d.get('error'):
            continue

        adoszam = str(d.get('search_adoszam', '')).strip()
        info = lookup.get(adoszam)
        if not info:
            still_missing.append(adoszam)
            continue

        name, szekhely, amount, donors = info
        amount_str = f"{amount:,}".replace(',', ' ') + " Ft"

        d['alapadatok'] = {
            'azonosito_adatok': {
                'teljes_név': name,
                'székhely_ország': 'Magyarország',
                'székhely_címe': str(szekhely),
                'adószám': adoszam,
            },
            'fonadatok': {
                'céljának_leírása': '',
            },
        }
        d['nav_1_percent'] = {
            'kedvezmenyezett_adatok': [{
                'Év': '2026',
                'Érvényesen rendelkező magánszemélyek száma': str(donors),
                'Az érvényes civil kedvezményezettet megillető szja 1% összege': amount_str,
            }],
        }
        d['error'] = None

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        fixed += 1

    print(f"Backfilled {fixed} org JSON files from xlsx data")
    if still_missing:
        print(f"WARN: {len(still_missing)} adószám had no xlsx match either: {still_missing}")


if __name__ == '__main__':
    main()
