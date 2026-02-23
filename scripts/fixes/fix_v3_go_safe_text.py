"""
Fix for create_visualizations_adoszam_500_v3_go.py
Safely handles text in customdata to prevent rendering issues
"""
import pandas as pd
import plotly.graph_objects as go
import json
import os
import sys
import re

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def safe_str(value, default=''):
    """Convert value to safe string, handling None/NaN"""
    if value is None:
        return default
    if pd.isna(value):
        return default
    s = str(value)
    # Remove any problematic characters that might break JSON
    s = s.replace('\x00', '')  # Null bytes
    s = s.replace('\r', ' ')   # Carriage returns
    return s


def read_json_file(filepath):
    """Read JSON file with fallback encoding"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            return json.load(f)


def extract_org_data(json_data):
    """Extract organization data from JSON"""
    if 'error' in json_data:
        return None

    alapadatok = json_data.get('alapadatok', {})
    azonosito = alapadatok.get('azonosito_adatok', {})
    fonadatok = alapadatok.get('fonadatok', {})
    nav_data = json_data.get('nav_1_percent', {})

    org_info = {
        'adoszam': json_data.get('search_adoszam', ''),
        'szekhely': azonosito.get('szekhely_cime', ''),
        'purpose': fonadatok.get('celjanak_leirasa', ''),
        'historical_data': nav_data.get('kedvezmenyezett_adatok', [])
    }

    return org_info


def format_historical_data_visual(hist_data):
    """Create visual representation of historical data using Unicode blocks"""
    if not hist_data or not isinstance(hist_data, list):
        return 'Nincs éves adat'

    sorted_data = sorted(hist_data, key=lambda x: x.get('Év', '0'))

    amounts = []
    years = []
    for entry in sorted_data:
        year = entry.get('Év', 'N/A')
        amount_str = entry.get('Az érvényes civil kedvezményezettet megillető szja 1% összege', '0')
        try:
            amount = int(amount_str.replace('Ft', '').replace(' ', '').strip())
            amounts.append(amount)
            years.append(year)
        except:
            pass

    if not amounts:
        return 'Nincs éves adat'

    max_amount = max(amounts)
    if max_amount == 0:
        return 'Nincs éves adat'

    blocks = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']

    visual_parts = []
    for year, amount in zip(years, amounts):
        normalized = amount / max_amount
        block_index = min(int(normalized * len(blocks)), len(blocks) - 1)
        block = blocks[block_index]
        visual_parts.append(f"{year}: {block} {amount:,} Ft")

    return ' | '.join(visual_parts)


def main():
    print("=" * 80)
    print("HIERARCHICAL VISUALIZATION - graph_objects Version (SAFE TEXT)")
    print("=" * 80)

    # 1. Load data
    print("\n1. Loading LLM-classified organizations...")
    df_categories = pd.read_csv('organization_categories_adoszam_500.csv', encoding='utf-8-sig')
    print(f"   Loaded {len(df_categories)} organizations")

    # 2. Load Excel data
    print("\n2. Loading Excel data...")
    excel_file = 'Szja 1-os felajanlasban reszesult civil kedvezmenyezettek_2025.xlsx'
    df_excel = pd.read_excel(excel_file, sheet_name='Munka1', header=1)
    df_excel['összeg'] = pd.to_numeric(df_excel['Felajánlott összeg (Ft)'], errors='coerce').fillna(0).astype(int)
    df_excel['db'] = pd.to_numeric(df_excel['Felajánlók száma (fő)'], errors='coerce').fillna(0).astype(int)
    df_amounts = df_excel[['Adószám', 'Név', 'összeg', 'db']].copy()
    print(f"   Loaded {len(df_amounts)} organizations from Excel")

    # 3. Load scraped JSON data
    print("\n3. Loading scraped JSON data...")
    organizations_folder = 'organizations_by_adoszam'
    org_data_list = []

    if os.path.exists(organizations_folder):
        json_files = [f for f in os.listdir(organizations_folder) if f.endswith('.json')]
        print(f"   Found {len(json_files)} JSON files")

        for i, filename in enumerate(json_files):
            if (i + 1) % 200 == 0:
                print(f"   Processing {i+1}/{len(json_files)}...")

            filepath = os.path.join(organizations_folder, filename)
            try:
                json_data = read_json_file(filepath)
                org_info = extract_org_data(json_data)
                if org_info:
                    org_data_list.append(org_info)
            except Exception as e:
                pass

        print(f"   Successfully extracted data from {len(org_data_list)} organizations")
    else:
        print(f"   Folder '{organizations_folder}' not found!")
        return

    df_orgs = pd.DataFrame(org_data_list)

    # Convert tax numbers to string
    df_categories['Adószám'] = df_categories['Adószám'].astype(str)
    if len(df_orgs) > 0:
        df_orgs['adoszam'] = df_orgs['adoszam'].astype(str)
    df_amounts['Adószám'] = df_amounts['Adószám'].astype(str)

    # 4. Merge all data sources
    print("\n4. Merging data sources...")
    if len(df_orgs) > 0:
        df_merged = df_categories.merge(df_orgs, left_on='Adószám', right_on='adoszam', how='left')
    else:
        df_merged = df_categories.copy()
        df_merged['szekhely'] = None
        df_merged['purpose'] = None
        df_merged['historical_data'] = None

    df_merged = df_merged.merge(df_amounts, left_on='Adószám', right_on='Adószám', how='left')
    df_merged = df_merged.dropna(subset=['összeg'])
    df_merged['összeg'] = df_merged['összeg'].astype(int)
    df_merged['db'] = df_merged['db'].astype(int)

    if 'purpose' not in df_merged.columns:
        df_merged['purpose'] = df_merged.get('Cél (első 200 karakter)', '')
    else:
        df_merged['purpose'] = df_merged['purpose'].fillna(df_merged.get('Cél (első 200 karakter)', ''))

    print(f"   Merged: {len(df_merged)} organizations")
    print(f"   Total amount: {df_merged['összeg'].sum():,.0f} Ft")
    total_összeg = df_merged['összeg'].sum()
    total_db = df_merged['db'].sum()
    print(f"   Total donors: {total_db:,}")

    # 5. Format data (use simple versions without HTML)
    print("\n5. Formatting data...")
    df_merged['short_name'] = df_merged['Szervezet neve'].str[:50]
    df_merged['safe_szekhely'] = df_merged['szekhely'].fillna(df_merged['Székhely']).fillna('Nincs adat')
    df_merged['safe_purpose'] = df_merged['purpose'].fillna('Nincs leírás').str[:300]  # Truncate
    df_merged['historical_visual'] = df_merged['historical_data'].apply(format_historical_data_visual)

    # 6. Build tree structure
    print("\n6. Building tree structure...")
    nodes = []

    # Root node
    nodes.append({
        'id': '__root__',
        'label': 'Összes',
        'parent': '',
        'összeg': total_összeg,
        'db': total_db,
        'org_name': 'Összes szervezet',
        'szekhely': '',
        'purpose': '',
        'historical': ''
    })

    # Parent category nodes
    parent_categories = {}
    for parent_cat in df_merged['Szülő kategória'].unique():
        if pd.notna(parent_cat):
            subset = df_merged[df_merged['Szülő kategória'] == parent_cat]
            összeg = subset['összeg'].sum()
            db = subset['db'].sum()

            parent_categories[parent_cat] = {'összeg': összeg, 'db': db}

            nodes.append({
                'id': parent_cat,
                'label': parent_cat,
                'parent': '__root__',
                'összeg': összeg,
                'db': db,
                'org_name': parent_cat,
                'szekhely': '',
                'purpose': '',
                'historical': ''
            })

    # Leaf category nodes
    leaf_categories = {}
    for _, row in df_merged.groupby(['Szülő kategória', 'Új kategória (legalsó szint)']).first().reset_index().iterrows():
        parent_cat = row['Szülő kategória']
        leaf_cat = row['Új kategória (legalsó szint)']

        if pd.notna(parent_cat) and pd.notna(leaf_cat):
            subset = df_merged[(df_merged['Szülő kategória'] == parent_cat) &
                              (df_merged['Új kategória (legalsó szint)'] == leaf_cat)]
            összeg = subset['összeg'].sum()
            db = subset['db'].sum()

            cat_id = f"{parent_cat}|{leaf_cat}"
            leaf_categories[cat_id] = {'összeg': összeg, 'db': db}

            nodes.append({
                'id': cat_id,
                'label': leaf_cat,
                'parent': parent_cat,
                'összeg': összeg,
                'db': db,
                'org_name': leaf_cat,
                'szekhely': '',
                'purpose': '',
                'historical': ''
            })

    # Organization nodes
    for idx, row in df_merged.iterrows():
        parent_cat = row['Szülő kategória']
        leaf_cat = row['Új kategória (legalsó szint)']
        org_name = row['short_name']

        parent_id = f"{parent_cat}|{leaf_cat}"
        org_id = f"{parent_cat}|{leaf_cat}|{org_name}|{idx}"

        nodes.append({
            'id': org_id,
            'label': org_name,
            'parent': parent_id,
            'összeg': row['összeg'],
            'db': row['db'],
            'org_name': safe_str(row['Szervezet neve']),
            'szekhely': safe_str(row['safe_szekhely']),
            'purpose': safe_str(row['safe_purpose']),
            'historical': safe_str(row['historical_visual'])
        })

    print(f"   Built tree with {len(nodes)} nodes")

    # 7. Calculate statistics
    print("\n7. Calculating statistics...")
    for node in nodes:
        if node['db'] > 0:
            node['átlag'] = round(node['összeg'] / node['db'])
            node['monthly_gross'] = round(node['átlag'] * 100 * (100/15) / 12)
        else:
            node['átlag'] = 0
            node['monthly_gross'] = 0

        node['pct_of_total'] = (node['összeg'] / total_összeg * 100) if total_összeg > 0 else 0

        parent_id = node['parent']
        if parent_id:
            parent_node = next((n for n in nodes if n['id'] == parent_id), None)
            if parent_node and parent_node['összeg'] > 0:
                node['pct_of_parent'] = (node['összeg'] / parent_node['összeg'] * 100)
            else:
                node['pct_of_parent'] = 0
        else:
            node['pct_of_parent'] = 100

    # 8. Create arrays - KEEP TEXT SIMPLE
    ids = [n['id'] for n in nodes]
    labels = [n['label'] for n in nodes]
    parents = [n['parent'] for n in nodes]
    values = [n['összeg'] for n in nodes]

    # NUMERIC-ONLY customdata (text causes rendering issues)
    customdata = [[
        n['összeg'],
        n['db'],
        n['átlag'],
        n['monthly_gross'],
        n['pct_of_parent'],
        n['pct_of_total']
    ] for n in nodes]

    # 9. Create Sunburst
    print("\n9. Creating Sunburst chart...")

    fig_sunburst = go.Figure(go.Sunburst(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        customdata=customdata,
        hovertemplate='<b>%{label}</b><br>' +
                      'Összeg: %{customdata[0]:,.0f} Ft<br>' +
                      'Felajánlók: %{customdata[1]:,} fő<br>' +
                      'Átlag/fő: %{customdata[2]:,.0f} Ft<br>' +
                      'Havi bruttó: %{customdata[3]:,.0f} Ft<br>' +
                      'Részarány (szülő): %{customdata[4]:.2f}%<br>' +
                      'Részarány (teljes): %{customdata[5]:.3f}%' +
                      '<extra></extra>',
        textfont=dict(size=10)
    ))

    fig_sunburst.update_layout(
        width=1400,
        height=900,
        margin=dict(t=60, l=10, r=10, b=10),
        title='Civil Szervezetek - Sunburst (Safe Text Version)'
    )

    output_file = 'sunburst_chart_adoszam_500_go_safe.html'
    fig_sunburst.write_html(output_file)
    print(f"   Saved to {output_file}")

    print("\n" + "=" * 80)
    print("DONE!")
    print("=" * 80)


if __name__ == '__main__':
    main()
