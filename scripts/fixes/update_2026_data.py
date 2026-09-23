"""
One-off update for the 2026 (rendelkező év) data release.
- Computes the new top-10,000 list from the 2026 xlsx
- Appends the 2026 donation figure directly into each continuing org's JSON
  (no need to re-scrape civil.info.hu for orgs we already have, since the
  new-year amount/donor-count is already in the official xlsx)
- Writes the list of newly-entered adószám to scrape
- Removes JSON files for orgs that fell out of the top 10,000
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
CATEGORIES_CSV = os.path.join(DATA_DIR, 'organization_categories_ALL_10000.csv')

NEW_ENTRANTS_TXT = os.path.join(DATA_DIR, 'adoszam_new_2026.txt')
DROPPED_LOG = os.path.join(DATA_DIR, 'dropped_orgs_2026.txt')


def main():
    import pandas as pd

    df26 = pd.read_excel(XLSX_2026, sheet_name='Munka1', header=1)
    df26['Adószám'] = df26['Adószám'].astype(str)
    top26 = df26.sort_values('Felajánlott összeg (Ft)', ascending=False).head(10000).copy()
    top26_map = {
        row['Adószám']: (int(row['Felajánlott összeg (Ft)']), int(row['Felajánlók száma (fő)']))
        for _, row in top26.iterrows()
    }
    top26_set = set(top26_map.keys())

    cur = pd.read_csv(CATEGORIES_CSV, encoding='utf-8-sig')
    cur['Adószám'] = cur['Adószám'].astype(str)
    current_set = set(cur['Adószám'])

    new_entrants = top26_set - current_set
    dropped = current_set - top26_set
    continuing = current_set & top26_set

    print(f"Current top-10000 (2025 basis): {len(current_set)}")
    print(f"New top-10000 (2026 basis):     {len(top26_set)}")
    print(f"Continuing: {len(continuing)}  New entrants: {len(new_entrants)}  Dropped: {len(dropped)}")

    # Build adoszam -> filepath map by reading search_adoszam from each JSON
    adoszam_to_path = {}
    for fname in os.listdir(ORG_DIR):
        if not fname.endswith('.json'):
            continue
        fpath = os.path.join(ORG_DIR, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                d = json.load(f)
            adoszam = str(d.get('search_adoszam', '')).strip()
            if adoszam:
                adoszam_to_path[adoszam] = fpath
        except Exception as e:
            print(f"  WARN: could not read {fname}: {e}")

    print(f"Indexed {len(adoszam_to_path)} existing org JSON files by adószám")

    # --- Merge 2026 figures into continuing orgs ---
    merged = 0
    missing_files = []
    for adoszam in continuing:
        fpath = adoszam_to_path.get(adoszam)
        if not fpath:
            missing_files.append(adoszam)
            continue
        with open(fpath, 'r', encoding='utf-8') as f:
            d = json.load(f)

        amount, donors = top26_map[adoszam]
        amount_str = f"{amount:,}".replace(',', ' ') + " Ft"

        nav = d.setdefault('nav_1_percent', {})
        if not isinstance(nav, dict):
            nav = {}
            d['nav_1_percent'] = nav
        hist = nav.setdefault('kedvezmenyezett_adatok', [])

        # Remove any pre-existing 2026 row (idempotency) then append fresh
        hist = [h for h in hist if str(h.get('Év', '')) != '2026']
        hist.append({
            'Év': '2026',
            'Érvényesen rendelkező magánszemélyek száma': str(donors),
            'Az érvényes civil kedvezményezettet megillető szja 1% összege': amount_str,
        })
        nav['kedvezmenyezett_adatok'] = hist

        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        merged += 1

    print(f"Merged 2026 figures into {merged} continuing orgs' JSON files")
    if missing_files:
        print(f"  WARN: {len(missing_files)} continuing adószám had no matching JSON file: {missing_files[:10]}...")

    # --- Write new-entrants list for the scraper ---
    with open(NEW_ENTRANTS_TXT, 'w', encoding='utf-8') as f:
        for adoszam in sorted(new_entrants):
            f.write(adoszam + '\n')
    print(f"Wrote {len(new_entrants)} new-entrant adószám to {NEW_ENTRANTS_TXT}")

    # --- Remove dropped orgs' JSON files ---
    removed = 0
    removed_paths = []
    for adoszam in dropped:
        fpath = adoszam_to_path.get(adoszam)
        if fpath and os.path.exists(fpath):
            removed_paths.append(fpath)
            os.remove(fpath)
            removed += 1
    print(f"Removed {removed} JSON files for orgs that dropped out of top 10000")

    with open(DROPPED_LOG, 'w', encoding='utf-8') as f:
        for p in removed_paths:
            f.write(p + '\n')

    print("\nDone. Next steps:")
    print(f"  1. Scrape new entrants: python run_scraper_adoszam.py --input \"{NEW_ENTRANTS_TXT}\" --folder \"{ORG_DIR}\"")
    print(f"  2. Re-run classification over all files in organizations_by_adoszam/")


if __name__ == '__main__':
    main()
