"""
Distill the raw kormany.hu civil-org state-funding snapshot
(data/kormany_atlathato_civil_szervezetek.json, ~36MB, full GeoJSON with
every scraped field) into a small per-adószám summary used by the
"Állami támogatás vs Adó 1%" dashboard page:
  - total 5-year (2022-2026) state funding received
  - breakdown by fund (NEA, VCA, NKA, FCA, CNP, MK)

Usage: python scripts/fixes/build_kormany_funding_data.py
"""
import json
import os
import re
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

SOURCE_FILE = os.path.join(DATA_DIR, 'kormany_atlathato_civil_szervezetek.json')
OUTPUT_FILE = os.path.join(DATA_DIR, 'allami_tamogatas_by_adoszam.json')

FUNDS = ['nea', 'vca', 'nka', 'fca', 'cnp', 'mk']
YEARS = ['2022', '2023', '2024', '2025', '2026']


def to_int(value):
    if value is None or value == '':
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def main():
    with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    features = data['features']
    print(f"Loaded {len(features)} state-funding records from {SOURCE_FILE}")

    by_adoszam = {}
    skipped_no_adoszam = 0
    skipped_dupe = 0

    for feat in features:
        props = feat.get('properties', {})
        fields = props.get('fields', {})
        adoszam_raw = fields.get('adoszam', '')
        m = re.match(r'^(\d{8})', str(adoszam_raw))
        if not m:
            skipped_no_adoszam += 1
            continue
        adoszam = m.group(1)

        total = to_int(fields.get('utalas_osszesen'))
        if total <= 0:
            # fall back to summing yearly totals if utalas_osszesen missing
            total = sum(to_int(fields.get(f'utalas_{y}')) for y in YEARS)
        if total <= 0:
            continue

        by_fund = {}
        for fund in FUNDS:
            fund_total = sum(to_int(fields.get(f'utalas_{fund}_{y}')) for y in YEARS)
            if fund_total > 0:
                by_fund[fund.upper()] = fund_total

        entry = {
            'nev': props.get('name', ''),
            'total': total,
            'by_fund': by_fund,
        }

        if adoszam in by_adoszam:
            # Duplicate adószám in source (rare) -- keep the larger total
            skipped_dupe += 1
            if total <= by_adoszam[adoszam]['total']:
                continue

        by_adoszam[adoszam] = entry

    print(f"Matched {len(by_adoszam)} orgs with a valid adószám and nonzero funding")
    print(f"  skipped (no adószám): {skipped_no_adoszam}, duplicates seen: {skipped_dupe}")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(by_adoszam, f, ensure_ascii=False)

    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"Saved to {OUTPUT_FILE} ({size_kb:.0f} KB)")


if __name__ == '__main__':
    main()
