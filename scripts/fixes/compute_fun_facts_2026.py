"""
Recompute the specific numbers used in pages/fun_facts.md against the fresh
2026 dataset (run only after scraping + classification have finished and
organization_categories_ALL_10000.csv reflects the new top-10000 list).

Usage: python scripts/fixes/compute_fun_facts_2026.py
"""
import os
import sys
import json
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
ORG_DIR = os.path.join(PROJECT_ROOT, 'organizations_by_adoszam')
VIZ_DIR = os.path.join(PROJECT_ROOT, 'scripts', 'visualization')

sys.path.insert(0, VIZ_DIR)
import create_visualizations_ALL_5000_v3_go as original

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def build_df_merged():
    df_categories = pd.read_csv(os.path.join(DATA_DIR, 'organization_categories_ALL_10000.csv'), encoding='utf-8-sig')
    excel_file = os.path.join(DATA_DIR, 'Szja 1-os felajanlasban reszesult civil kedvezményezettek_2026.xlsx')
    df_excel = pd.read_excel(excel_file, sheet_name='Munka1', header=1)
    df_excel['összeg'] = pd.to_numeric(df_excel['Felajánlott összeg (Ft)'], errors='coerce').fillna(0).astype(int)
    df_excel['db'] = pd.to_numeric(df_excel['Felajánlók száma (fő)'], errors='coerce').fillna(0).astype(int)
    df_amounts = df_excel[['Adószám', 'Név', 'összeg', 'db']].copy()

    org_data_list = []
    for filename in os.listdir(ORG_DIR):
        if not filename.endswith('.json'):
            continue
        filepath = os.path.join(ORG_DIR, filename)
        try:
            json_data = original.read_json_file(filepath)
            org_info = original.extract_org_data(json_data)
            if org_info:
                org_data_list.append(org_info)
        except Exception:
            pass
    df_orgs = pd.DataFrame(org_data_list)

    df_categories['Adószám'] = df_categories['Adószám'].astype(str)
    df_orgs['adoszam'] = df_orgs['adoszam'].astype(str)
    df_amounts['Adószám'] = df_amounts['Adószám'].astype(str)

    df_merged = df_categories.merge(df_orgs, left_on='Adószám', right_on='adoszam', how='left')
    df_merged = df_merged.merge(df_amounts, left_on='Adószám', right_on='Adószám', how='left')
    df_merged = df_merged.dropna(subset=['összeg'])
    df_merged['összeg'] = df_merged['összeg'].astype(int)
    df_merged['db'] = df_merged['db'].astype(int)
    df_merged['átlag_per_donor'] = (df_merged['összeg'] / df_merged['db']).fillna(0)
    df_merged['monthly_gross'] = (df_merged['átlag_per_donor'] * 100 * (100 / 15) / 12).fillna(0).astype(int)
    df_merged['parent_category'] = df_merged['Szülő kategória']
    df_merged['leaf_category'] = df_merged['Új kategória (legalsó szint)']
    return df_merged


def pct_by_year_for_category(df_merged, leaf_category):
    total_hist = original.aggregate_historical_data(df_merged)
    cat_hist = original.aggregate_historical_data(df_merged[df_merged['leaf_category'] == leaf_category])
    total_by_year = {e['Év']: int(e['Az érvényes civil kedvezményezettet megillető szja 1% összege'].replace(' Ft', '').replace(' ', ''))
                     for e in total_hist}
    cat_by_year = {e['Év']: int(e['Az érvényes civil kedvezményezettet megillető szja 1% összege'].replace(' Ft', '').replace(' ', ''))
                   for e in cat_hist}
    years = sorted(set(total_by_year) & set(cat_by_year))
    return {y: round(cat_by_year[y] / total_by_year[y] * 100, 1) for y in years}


def main():
    df = build_df_merged()
    print(f"Total merged orgs: {len(df)}")

    print("\n=== SAJTÓ, MÉDIA % of total by year ===")
    for y, pct in pct_by_year_for_category(df, 'sajtó, média').items():
        print(f"  {y}: {pct}%")

    print("\n=== DEMOKRÁCIA ÉS ÁTLÁTHATÓSÁG % of total by year ===")
    for y, pct in pct_by_year_for_category(df, 'demokrácia és átláthatóság').items():
        print(f"  {y}: {pct}%")

    kutyak = df[df['leaf_category'] == 'kutyák']
    print(f"\n=== KUTYÁK category ===")
    print(f"  Orgs: {len(kutyak)}  Total összeg: {kutyak['összeg'].sum():,} Ft  Total donors: {kutyak['db'].sum():,}")

    sajto = df[df['leaf_category'] == 'sajtó, média']
    print(f"\n=== SAJTÓ, MÉDIA category (current year) ===")
    print(f"  Orgs: {len(sajto)}  Total összeg: {sajto['összeg'].sum():,} Ft")

    print("\n=== MÁS KONKRÉT ÁLLATFAJOK — top orgs by donor count ===")
    other_animals = df[df['leaf_category'] == 'más konkrét állatfajok'].nlargest(10, 'db')
    for _, r in other_animals.iterrows():
        print(f"  {r['Szervezet neve'][:60]:<60} db={r['db']:>6}  összeg={r['összeg']:>12,} Ft")

    print("\n=== GIMNÁZIUMOK vs KUTYÁK — avg monthly gross per donor ===")
    for cat in ['gimnáziumok', 'kutyák']:
        subset = df[(df['leaf_category'] == cat) & (df['db'] > 0)]
        print(f"  {cat}: n={len(subset)}  mean_monthly_gross={subset['monthly_gross'].mean():,.0f} Ft  median={subset['monthly_gross'].median():,.0f} Ft")

    print("\n=== VIETNAM-related orgs ===")
    viet = df[df['Szervezet neve'].str.contains('ietnam|ietná', case=False, regex=True, na=False)]
    overall_avg_monthly = df[df['db'] > 0]['monthly_gross'].mean()
    print(f"  Overall average monthly gross (all orgs): {overall_avg_monthly:,.0f} Ft")
    for _, r in viet.iterrows():
        pct_of_avg = r['monthly_gross'] / overall_avg_monthly * 100 if overall_avg_monthly else 0
        print(f"  {r['Szervezet neve'][:60]:<60} db={r['db']:>6}  monthly_gross={r['monthly_gross']:>10,} Ft  ({pct_of_avg:.0f}% of avg)")

    print("\n=== CSÁNYI-related orgs ===")
    csanyi = df[df['Szervezet neve'].str.contains('sányi', case=False, regex=True, na=False)]
    for _, r in csanyi.iterrows():
        print(f"  {r['Szervezet neve'][:70]:<70} db={r['db']:>6}  összeg={r['összeg']:>14,} Ft")


if __name__ == '__main__':
    main()
