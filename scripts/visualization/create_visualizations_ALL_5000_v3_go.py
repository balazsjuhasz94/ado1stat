"""
Create hierarchical visualizations using plotly.graph_objects
This version properly shows aggregated stats for category nodes
"""

import pandas as pd
import plotly.graph_objects as go
import json
import os
import sys
import re

# Set UTF-8 encoding for console output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Base directory paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(BASE_DIR, 'data')


def read_json_file(filepath):
    """Read JSON file with UTF-8 encoding"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_org_data(json_data):
    """Extract relevant data from organization JSON including historical yearly data"""
    try:
        if json_data.get('error'):
            return None

        azonosito = json_data.get('alapadatok', {}).get('azonosito_adatok', {})
        fonadatok = json_data.get('alapadatok', {}).get('fonadatok', {})

        org_name = azonosito.get('teljes_név', json_data.get('search_adoszam', 'Unknown'))
        adoszam = json_data.get('search_adoszam', azonosito.get('adószám', ''))
        szekhely = azonosito.get('székhely_címe', 'Nincs adat')
        purpose = fonadatok.get('céljának_leírása', 'Nincs leírás')
        nav_data = json_data.get('nav_1_percent', {}).get('kedvezmenyezett_adatok', [])

        return {
            'name': org_name,
            'adoszam': adoszam,
            'szekhely': szekhely,
            'purpose': purpose,
            'org_id': json_data.get('organization_id', 'N/A'),
            'historical_data': nav_data
        }
    except Exception as e:
        print(f"Error extracting data: {e}")
        return None


def format_historical_data_visual(hist_data):
    """Format historical yearly donation data as a visual chart"""
    if not hist_data or len(hist_data) == 0:
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

    blocks = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']
    max_amount = max(amounts)
    min_amount = min(amounts)

    lines = []
    for year, amount in zip(years[-10:], amounts[-10:]):
        if max_amount == min_amount:
            normalized = 7
        else:
            normalized = int(((amount - min_amount) / (max_amount - min_amount)) * 7)

        bar = blocks[normalized] * 10

        if amount >= 1_000_000:
            amount_formatted = f"{amount/1_000_000:.1f}M Ft"
        elif amount >= 1_000:
            amount_formatted = f"{amount/1_000:.0f}k Ft"
        else:
            amount_formatted = f"{amount} Ft"

        lines.append(f"{year}: {bar} {amount_formatted}")

    return '<br>'.join(lines)


def format_historical_data_with_percentage(hist_data, total_hist_data):
    """Format historical yearly donation data with percentage of total"""
    if not hist_data or len(hist_data) == 0:
        return 'Nincs éves adat'

    # Create dictionaries for easy lookup
    year_amounts = {}
    for entry in hist_data:
        year = entry.get('Év', 'N/A')
        amount_str = entry.get('Az érvényes civil kedvezményezettet megillető szja 1% összege', '0')
        try:
            amount = int(amount_str.replace('Ft', '').replace(' ', '').strip())
            year_amounts[year] = amount
        except:
            pass

    year_totals = {}
    for entry in total_hist_data:
        year = entry.get('Év', 'N/A')
        amount_str = entry.get('Az érvényes civil kedvezményezettet megillető szja 1% összege', '0')
        try:
            amount = int(amount_str.replace('Ft', '').replace(' ', '').strip())
            year_totals[year] = amount
        except:
            pass

    if not year_amounts:
        return 'Nincs éves adat'

    # Sort by year
    sorted_years = sorted(year_amounts.keys())
    amounts = [year_amounts[y] for y in sorted_years]

    blocks = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']
    max_amount = max(amounts)
    min_amount = min(amounts)

    lines = []
    for year in sorted_years[-10:]:  # Last 10 years
        amount = year_amounts[year]

        if max_amount == min_amount:
            normalized = 7
        else:
            normalized = int(((amount - min_amount) / (max_amount - min_amount)) * 7)

        bar = blocks[normalized] * 10

        if amount >= 1_000_000:
            amount_formatted = f"{amount/1_000_000:.1f}M Ft"
        elif amount >= 1_000:
            amount_formatted = f"{amount/1_000:.0f}k Ft"
        else:
            amount_formatted = f"{amount} Ft"

        # Calculate percentage of total
        percentage = ""
        if year in year_totals and year_totals[year] > 0:
            pct = (amount / year_totals[year]) * 100
            percentage = f" ({pct:.2f}%)"

        lines.append(f"{year}: {bar} {amount_formatted}{percentage}")

    return '<br>'.join(lines)


def aggregate_historical_data(df_subset):
    """Aggregate historical data from multiple organizations by year"""
    from collections import defaultdict

    year_totals = defaultdict(int)
    year_donors = defaultdict(int)

    for _, row in df_subset.iterrows():
        hist_data = row.get('historical_data')
        if hist_data and isinstance(hist_data, list):
            for entry in hist_data:
                year = entry.get('Év')
                amount_str = entry.get('Az érvényes civil kedvezményezettet megillető szja 1% összege', '0')
                try:
                    amount = int(amount_str.replace('Ft', '').replace(' ', '').strip())
                    year_totals[year] += amount
                except:
                    pass
                donor_str = entry.get('Érvényesen rendelkező magánszemélyek száma',
                                     entry.get('Felajánlók száma (fő)',
                                     entry.get('Felajánlók száma', '0')))
                try:
                    if isinstance(donor_str, (int, float)):
                        donors = int(donor_str)
                    else:
                        cleaned = str(donor_str).replace(' ', '').replace('fő', '').strip()
                        donors = int(cleaned) if cleaned else 0
                    year_donors[year] += donors
                except:
                    pass

    if not year_totals:
        return []

    aggregated = []
    for year, amount in sorted(year_totals.items()):
        aggregated.append({
            'Év': year,
            'Az érvényes civil kedvezményezettet megillető szja 1% összege': f'{amount} Ft',
            'Érvényesen rendelkező magánszemélyek száma': str(year_donors.get(year, 0))
        })

    return aggregated


def calculate_yoy_growth(hist_data):
    """Calculate year-over-year growth rate (2025 vs 2024)"""
    if not hist_data or len(hist_data) == 0:
        return 100.0  # Default to +100% if no data

    # Extract amounts by year
    year_amounts = {}
    for entry in hist_data:
        year = entry.get('Év', '')
        amount_str = entry.get('Az érvényes civil kedvezményezettet megillető szja 1% összege', '0')
        try:
            amount = int(amount_str.replace('Ft', '').replace(' ', '').strip())
            year_amounts[str(year)] = amount
        except:
            pass

    # Get 2024 and 2025 amounts
    amount_2024 = year_amounts.get('2024', 0)
    amount_2025 = year_amounts.get('2025', 0)

    # Calculate growth
    if amount_2024 == 0:
        return 100.0  # No 2024 data, default to +100%

    growth_rate = ((amount_2025 - amount_2024) / amount_2024) * 100
    return round(growth_rate, 1)  # Round to 1 decimal place


def wrap_line(text, max_length=100):
    """Wrap a single line to maximum length"""
    if len(text) <= max_length:
        return [text]

    words = text.split()
    lines = []
    current_line = []
    current_length = 0

    for word in words:
        word_length = len(word)
        needed_length = word_length if not current_line else word_length + 1

        if current_length + needed_length <= max_length:
            current_line.append(word)
            current_length += needed_length
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
            current_length = word_length

    if current_line:
        lines.append(' '.join(current_line))

    return lines


def format_purpose_multiline(purpose_text, max_line_length=100, max_lines=20):
    """Intelligently format organization purpose text"""
    if not purpose_text or purpose_text == 'Nincs leírás':
        return purpose_text

    text = str(purpose_text).strip()

    # Strategy 1: Dash-separated list
    if text.count('\n-') >= 2 or (text.startswith('-') and text.count('\n-') >= 1):
        parts = [part.strip() for part in re.split(r'\n-\s*', text) if part.strip()]
        if not text.startswith('-') and parts:
            parts[0] = parts[0].lstrip('-').strip()

        wrapped_parts = []
        for part in parts:
            wrapped = wrap_line(part, max_line_length)
            if len(wrapped) == 1:
                wrapped_parts.append('• ' + wrapped[0])
            else:
                wrapped_parts.append('• ' + wrapped[0])
                for line in wrapped[1:]:
                    wrapped_parts.append('  ' + line)

        if len(wrapped_parts) > max_lines:
            wrapped_parts = wrapped_parts[:max_lines]
            wrapped_parts.append('...')

        return '<br>'.join(wrapped_parts)

    # Strategy 2: Inline dash items
    if text.count(' - ') >= 2:
        parts = [part.strip() for part in text.split(' - ') if part.strip()]
        wrapped_parts = []
        for part in parts:
            wrapped = wrap_line(part, max_line_length)
            for line in wrapped:
                wrapped_parts.append('• ' + line)

        if len(wrapped_parts) > max_lines:
            wrapped_parts = wrapped_parts[:max_lines]
            wrapped_parts.append('...')

        return '<br>'.join(wrapped_parts)

    # Strategy 3: Semicolon-separated
    if ';' in text and text.count(';') >= 2:
        parts = [part.strip() for part in text.split(';') if part.strip()]
        wrapped_parts = []
        for part in parts:
            wrapped = wrap_line(part, max_line_length)
            for line in wrapped:
                wrapped_parts.append('• ' + line)

        if len(wrapped_parts) > max_lines:
            wrapped_parts = wrapped_parts[:max_lines]
            wrapped_parts.append('...')

        return '<br>'.join(wrapped_parts)

    # Strategy 4: Bullet-style (with parenthesis check to avoid false positives)
    # Only match a), b), 1), 2) patterns that appear after whitespace or at start
    # This avoids matching closing parentheses like "(example)"
    bullet_pattern = r'(?:^|\s)([a-z]\)|[0-9]+\))'
    matches = list(re.finditer(bullet_pattern, text, re.IGNORECASE))

    # Additional check: make sure we don't have more opening parens than these matches
    # (which would indicate they're inside parentheses)
    if len(matches) >= 2:
        # Count opening parens before each match
        valid_matches = []
        for match in matches:
            text_before = text[:match.start()]
            open_count = text_before.count('(')
            close_count = text_before.count(')')
            # If balanced or more closes than opens, this is likely a list item
            if close_count >= open_count:
                valid_matches.append(match)

        if len(valid_matches) >= 2:
            parts = re.split(r'(?=(?:^|\s)[a-z]\)|(?:^|\s)[0-9]+\))', text, flags=re.IGNORECASE)
            parts = [part.strip() for part in parts if part.strip()]

            wrapped_parts = []
            for part in parts:
                wrapped = wrap_line(part, max_line_length)
                wrapped_parts.extend(wrapped)

            if len(wrapped_parts) > max_lines:
                wrapped_parts = wrapped_parts[:max_lines]
                wrapped_parts.append('...')

            return '<br>'.join(wrapped_parts)

    # Strategy 5: Sentence boundaries
    sentences = re.split(r'(\.\s+)', text)

    full_sentences = []
    current = ""
    for i, part in enumerate(sentences):
        current += part
        if i % 2 == 1 or i == len(sentences) - 1:
            if current.strip():
                full_sentences.append(current.strip())
                current = ""

    wrapped_lines = []
    for sentence in full_sentences:
        wrapped = wrap_line(sentence, max_line_length)
        wrapped_lines.extend(wrapped)

    if len(wrapped_lines) > max_lines:
        wrapped_lines = wrapped_lines[:max_lines]
        wrapped_lines.append('...')

    return '<br>'.join(wrapped_lines)


def safe_format_historical(x):
    """Safely format historical data"""
    if x is None:
        return 'Nincs éves adat'

    try:
        if pd.isna(x):
            return 'Nincs éves adat'
    except:
        pass

    if isinstance(x, list):
        return format_historical_data_visual(x)

    return 'Nincs éves adat'


def main():
    print("=" * 80)
    print("HIERARCHICAL VISUALIZATION - ALL 5000 Organizations")
    print("graph_objects Version - Properly shows aggregated stats for category nodes")
    print("=" * 80)

    # 1. Load LLM classification results
    print("\n1. Loading LLM-classified organizations...")
    df_categories = pd.read_csv(os.path.join(DATA_DIR, 'organization_categories_ALL_5000.csv'), encoding='utf-8-sig')
    print(f"   Loaded {len(df_categories)} organizations")

    # 2. Load Excel data
    print("\n2. Loading Excel data...")
    excel_file = os.path.join(DATA_DIR, 'Szja 1-os felajanlasban reszesult civil kedvezmenyezettek_2025.xlsx')
    df_excel = pd.read_excel(excel_file, sheet_name='Munka1', header=1)
    df_excel['összeg'] = pd.to_numeric(df_excel['Felajánlott összeg (Ft)'], errors='coerce').fillna(0).astype(int)
    df_excel['db'] = pd.to_numeric(df_excel['Felajánlók száma (fő)'], errors='coerce').fillna(0).astype(int)
    df_amounts = df_excel[['Adószám', 'Név', 'összeg', 'db']].copy()
    print(f"   Loaded {len(df_amounts)} organizations from Excel")

    # 3. Load scraped JSON data
    print("\n3. Loading scraped JSON data...")
    organizations_folder = os.path.join(BASE_DIR, 'organizations_by_adoszam')
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
    df_orgs['adoszam'] = df_orgs['adoszam'].astype(str)
    df_amounts['Adószám'] = df_amounts['Adószám'].astype(str)

    # 4. Merge all data sources
    print("\n4. Merging data sources...")
    df_merged = df_categories.merge(df_orgs, left_on='Adószám', right_on='adoszam', how='left')
    df_merged = df_merged.merge(df_amounts, left_on='Adószám', right_on='Adószám', how='left')
    df_merged = df_merged.dropna(subset=['összeg'])
    df_merged['összeg'] = df_merged['összeg'].astype(int)
    df_merged['db'] = df_merged['db'].astype(int)
    df_merged['purpose'] = df_merged['purpose'].fillna(df_merged['Cél (első 200 karakter)'])

    print(f"   Merged: {len(df_merged)} organizations")
    print(f"   Total amount: {df_merged['összeg'].sum():,.0f} Ft")
    print(f"   Total donors: {df_merged['db'].sum():,}")

    # 5. Format data
    print("\n5. Formatting data...")
    df_merged['átlag_per_donor'] = (df_merged['összeg'] / df_merged['db']).round(0)
    df_merged['monthly_gross'] = (df_merged['átlag_per_donor'] * 100 * (100/15) / 12).round(0).astype(int)
    df_merged['short_name'] = df_merged['Szervezet neve'].str[:50]
    df_merged['formatted_purpose'] = df_merged['purpose'].apply(format_purpose_multiline)
    df_merged['historical_chart'] = df_merged['historical_data'].apply(safe_format_historical)
    df_merged['yoy_growth'] = df_merged['historical_data'].apply(calculate_yoy_growth)
    df_merged['szekhely'] = df_merged['szekhely'].fillna(df_merged['Székhely']).fillna('Nincs adat')
    df_merged['parent_category'] = df_merged['Szülő kategória']
    df_merged['leaf_category'] = df_merged['Új kategória (legalsó szint)']

    # Filter out rows with NaN categories (these cause tree structure issues)
    print(f"   Before filtering NaN categories: {len(df_merged)} organizations")
    df_merged = df_merged.dropna(subset=['parent_category', 'leaf_category'])
    print(f"   After filtering: {len(df_merged)} organizations")

    # 6. Build tree structure for graph_objects
    print("\n6. Building tree structure...")

    # Calculate totals
    total_összeg = df_merged['összeg'].sum()
    total_db = df_merged['db'].sum()

    # Aggregate total historical data for percentage calculations
    total_aggregated_hist = aggregate_historical_data(df_merged)

    # Build nodes for the tree - USE SHORT NUMERIC IDS
    # Format: (id, label, parent_id, összeg, db, customdata)
    nodes = []
    id_map = {}  # Map original keys to numeric IDs
    current_id = 0

    # Root node - aggregate all historical data (no percentage for root)
    all_hist_chart = format_historical_data_visual(total_aggregated_hist)
    all_yoy_growth = calculate_yoy_growth(total_aggregated_hist)

    nodes.append({
        'id': str(current_id),
        'label': 'Összes',
        'parent': '',
        'összeg': total_összeg,
        'db': total_db,
        'szekhely': '',
        'formatted_purpose': '',
        'historical_chart': all_hist_chart,
        'org_name': 'Összes szervezet',
        'yoy_growth': all_yoy_growth
    })
    id_map['__root__'] = str(current_id)
    current_id += 1

    # Parent category nodes (level 0)
    parent_categories = {}
    for parent_cat in df_merged['parent_category'].unique():
        if pd.notna(parent_cat):
            subset = df_merged[df_merged['parent_category'] == parent_cat]
            összeg = subset['összeg'].sum()
            db = subset['db'].sum()

            # Aggregate historical data for this category with percentage
            aggregated_hist = aggregate_historical_data(subset)
            hist_chart = format_historical_data_with_percentage(aggregated_hist, total_aggregated_hist)
            yoy_growth = calculate_yoy_growth(aggregated_hist)

            parent_categories[parent_cat] = {'összeg': összeg, 'db': db}

            nodes.append({
                'id': str(current_id),
                'label': parent_cat,
                'parent': id_map['__root__'],
                'összeg': összeg,
                'db': db,
                'szekhely': '',
                'formatted_purpose': '',
                'historical_chart': hist_chart,
                'org_name': parent_cat,
                'yoy_growth': yoy_growth
            })
            id_map[parent_cat] = str(current_id)
            current_id += 1

    # Leaf category nodes (level 1)
    leaf_categories = {}
    for parent_cat in df_merged['parent_category'].unique():
        if pd.notna(parent_cat):
            for leaf_cat in df_merged[df_merged['parent_category'] == parent_cat]['leaf_category'].unique():
                if pd.notna(leaf_cat):
                    subset = df_merged[(df_merged['parent_category'] == parent_cat) &
                                      (df_merged['leaf_category'] == leaf_cat)]
                    összeg = subset['összeg'].sum()
                    db = subset['db'].sum()

                    # Aggregate historical data for this category with percentage
                    aggregated_hist = aggregate_historical_data(subset)
                    hist_chart = format_historical_data_with_percentage(aggregated_hist, total_aggregated_hist)
                    yoy_growth = calculate_yoy_growth(aggregated_hist)

                    cat_key = f"{parent_cat}|{leaf_cat}"
                    leaf_categories[cat_key] = {'összeg': összeg, 'db': db}

                    nodes.append({
                        'id': str(current_id),
                        'label': leaf_cat,
                        'parent': id_map.get(parent_cat, '0'),
                        'összeg': összeg,
                        'db': db,
                        'szekhely': '',
                        'formatted_purpose': '',
                        'historical_chart': hist_chart,
                        'org_name': leaf_cat,
                        'yoy_growth': yoy_growth
                    })
                    id_map[cat_key] = str(current_id)
                    current_id += 1

    # Organization nodes (level 2)
    for idx, row in df_merged.iterrows():
        parent_cat = row['parent_category']
        leaf_cat = row['leaf_category']
        org_name = row['short_name']

        parent_key = f"{parent_cat}|{leaf_cat}"

        nodes.append({
            'id': str(current_id),
            'label': org_name,
            'parent': id_map.get(parent_key, '0'),
            'összeg': row['összeg'],
            'db': row['db'],
            'szekhely': row['szekhely'],
            'formatted_purpose': row['formatted_purpose'],
            'historical_chart': row['historical_chart'],
            'org_name': row['Szervezet neve'],
            'yoy_growth': row['yoy_growth']
        })
        current_id += 1

    print(f"   Built tree with {len(nodes)} nodes")

    # 7. Calculate derived fields and percentages for all nodes
    print("\n7. Calculating statistics...")

    for node in nodes:
        # Calculate average and monthly gross
        if node['db'] > 0:
            node['átlag'] = round(node['összeg'] / node['db'])
            node['monthly_gross'] = round(node['átlag'] * 100 * (100/15) / 12)
        else:
            node['átlag'] = 0
            node['monthly_gross'] = 0

        # Calculate percentage of total
        node['pct_of_total'] = (node['összeg'] / total_összeg * 100) if total_összeg > 0 else 0

        # Calculate percentage of parent and get parent label
        parent_id = node['parent']
        if parent_id:
            parent_node = next((n for n in nodes if n['id'] == parent_id), None)
            if parent_node:
                node['parent_label'] = parent_node['label']  # Store parent label
                if parent_node['összeg'] > 0:
                    node['pct_of_parent'] = (node['összeg'] / parent_node['összeg'] * 100)
                else:
                    node['pct_of_parent'] = 0
            else:
                node['parent_label'] = ''
                node['pct_of_parent'] = 0
        else:
            node['parent_label'] = ''
            node['pct_of_parent'] = 100

    # 8. Create lists for graph_objects
    ids = [n['id'] for n in nodes]
    labels = [n['label'] for n in nodes]
    parents = [n['parent'] for n in nodes]
    values = [n['összeg'] for n in nodes]

    # Debug: Print first 10 entries
    print("\n8. Debug - First 10 entries:")
    for i in range(min(10, len(ids))):
        print(f"   {i}: id={ids[i][:40]!r}, parent={parents[i][:40]!r}, value={values[i]:,.0f}")

    # Custom data for hover
    customdata = [[
        n['org_name'],
        n['szekhely'],
        n['összeg'],
        n['db'],
        n['átlag'],
        n['monthly_gross'],
        n['pct_of_parent'],
        n['pct_of_total'],
        n['parent_label'],  # Added parent label
        n['formatted_purpose'],
        n['historical_chart'],
        n['yoy_growth'],  # Year-over-year growth (numeric for coloring)
        f"{n['yoy_growth']:+.1f}"  # Formatted string with + sign for display
    ] for n in nodes]

    # 9. Create Sunburst charts with graph_objects
    print("\n9. Creating Sunburst charts...")

    # Calculate color scale for salary-based coloring
    colors_salary = [n['monthly_gross'] for n in nodes]
    min_color_salary = pd.Series([n['monthly_gross'] for n in nodes if n['db'] > 0]).quantile(0.05)
    max_color_salary = pd.Series([n['monthly_gross'] for n in nodes if n['db'] > 0]).quantile(0.85)

    # Calculate color scale for growth-based coloring (-50% to +50%)
    colors_growth = [n['yoy_growth'] for n in nodes]
    min_color_growth = -50.0
    max_color_growth = 50.0

    # 9a. Default coloring
    fig_sunburst_default = go.Figure(go.Sunburst(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        branchvalues='total',
        customdata=customdata,
        hovertemplate='<b>%{label}</b><br>' +
                      '%{customdata[1]}<br>' +
                      '<br><b>Összeg:</b> %{value:,.0f} Ft<br>' +
                      '<b>Felajánlók:</b> %{customdata[3]:,} fő<br>' +
                      '<b>Átlag/fő:</b> %{customdata[4]:,.0f} Ft<br>' +
                      '<b>Átlagos havi bruttó jövedelem:</b> %{customdata[5]:,.0f} Ft<br>' +
                      '<b>Részarány (%{customdata[8]}):</b> %{customdata[6]:.2f}%<br>' +
                      '<b>Részarány (teljes):</b> %{customdata[7]:.3f}%<br>' +
                      '<b>Előző évhez képest:</b> %{customdata[12]}%<br>' +
                      '<br><b>Cél:</b><br>%{customdata[9]}<br>' +
                      '<br><b>Éves történet:</b><br>%{customdata[10]}' +
                      '<extra></extra>',
        textfont=dict(size=10)
    ))

    fig_sunburst_default.update_layout(
        width=1400,
        height=1400,
        margin=dict(t=60, l=10, r=10, b=300),
        title={
            'text': 'Civil Szervezetek - Sunburst (Default Colors)<br><sub>Kategóriák is mutatnak aggregált statisztikákat</sub>',
            'x': 0.5,
            'xanchor': 'center'
        }
    )

    output_file = 'sunburst_chart_ALL_5000_go.html'
    fig_sunburst_default.write_html(output_file)
    print(f"   ✓ Saved to {output_file}")

    # 9b. Salary-based coloring
    fig_sunburst_salary = go.Figure(go.Sunburst(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        branchvalues='total',
        customdata=customdata,
        marker=dict(
            colorscale='RdYlGn',
            cmid=(min_color_salary + max_color_salary) / 2,
            cmin=min_color_salary,
            cmax=max_color_salary,
            showscale=False,  # Hide colorbar
            line=dict(width=2)
        ),
        marker_colors=colors_salary,
        hovertemplate='<b>%{label}</b><br>' +
                      '%{customdata[1]}<br>' +
                      '<br><b>Összeg:</b> %{value:,.0f} Ft<br>' +
                      '<b>Felajánlók:</b> %{customdata[3]:,} fő<br>' +
                      '<b>Átlag/fő:</b> %{customdata[4]:,.0f} Ft<br>' +
                      '<b>Átlagos havi bruttó jövedelem:</b> %{customdata[5]:,.0f} Ft<br>' +
                      '<b>Részarány (%{customdata[8]}):</b> %{customdata[6]:.2f}%<br>' +
                      '<b>Részarány (teljes):</b> %{customdata[7]:.3f}%<br>' +
                      '<b>Előző évhez képest:</b> %{customdata[12]}%<br>' +
                      '<br><b>Cél:</b><br>%{customdata[9]}<br>' +
                      '<br><b>Éves történet:</b><br>%{customdata[10]}' +
                      '<extra></extra>',
        textfont=dict(size=10)
    ))

    fig_sunburst_salary.update_layout(
        width=1400,
        height=1400,
        margin=dict(t=60, l=10, r=10, b=300),
        title={
            'text': 'Civil Szervezetek - Sunburst (Colored by Salary)<br><sub>Színezés: átlagos havi bruttó jövedelem alapján</sub>',
            'x': 0.5,
            'xanchor': 'center'
        }
    )

    output_file = 'sunburst_chart_ALL_5000_go_salary.html'
    fig_sunburst_salary.write_html(output_file)
    print(f"   ✓ Saved to {output_file}")

    # 9c. Interactive sunburst with color mode toggle
    fig_sunburst_interactive = go.Figure()

    # Add default colored trace
    fig_sunburst_interactive.add_trace(go.Sunburst(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        branchvalues='total',
        customdata=customdata,
        name='Default',
        visible=True,
        hovertemplate='<b>%{label}</b><br>' +
                      '%{customdata[1]}<br>' +
                      '<br><b>Összeg:</b> %{value:,.0f} Ft<br>' +
                      '<b>Felajánlók:</b> %{customdata[3]:,} fő<br>' +
                      '<b>Átlag/fő:</b> %{customdata[4]:,.0f} Ft<br>' +
                      '<b>Átlagos havi bruttó jövedelem:</b> %{customdata[5]:,.0f} Ft<br>' +
                      '<b>Részarány (%{customdata[8]}):</b> %{customdata[6]:.2f}%<br>' +
                      '<b>Részarány (teljes):</b> %{customdata[7]:.3f}%<br>' +
                      '<b>Előző évhez képest:</b> %{customdata[12]}%<br>' +
                      '<br><b>Cél:</b><br>%{customdata[9]}<br>' +
                      '<br><b>Éves történet:</b><br>%{customdata[10]}' +
                      '<extra></extra>',
        textfont=dict(size=10)
    ))

    # Add salary-colored trace
    fig_sunburst_interactive.add_trace(go.Sunburst(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        branchvalues='total',
        customdata=customdata,
        name='Salary',
        visible=False,
        marker=dict(
            colorscale='RdYlGn',
            cmid=(min_color_salary + max_color_salary) / 2,
            cmin=min_color_salary,
            cmax=max_color_salary,
            showscale=False,
            line=dict(width=2)
        ),
        marker_colors=colors_salary,
        hovertemplate='<b>%{label}</b><br>' +
                      '%{customdata[1]}<br>' +
                      '<br><b>Összeg:</b> %{value:,.0f} Ft<br>' +
                      '<b>Felajánlók:</b> %{customdata[3]:,} fő<br>' +
                      '<b>Átlag/fő:</b> %{customdata[4]:,.0f} Ft<br>' +
                      '<b>Átlagos havi bruttó jövedelem:</b> %{customdata[5]:,.0f} Ft<br>' +
                      '<b>Részarány (%{customdata[8]}):</b> %{customdata[6]:.2f}%<br>' +
                      '<b>Részarány (teljes):</b> %{customdata[7]:.3f}%<br>' +
                      '<b>Előző évhez képest:</b> %{customdata[12]}%<br>' +
                      '<br><b>Cél:</b><br>%{customdata[9]}<br>' +
                      '<br><b>Éves történet:</b><br>%{customdata[10]}' +
                      '<extra></extra>',
        textfont=dict(size=10)
    ))

    # Add growth-colored trace
    fig_sunburst_interactive.add_trace(go.Sunburst(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        branchvalues='total',
        customdata=customdata,
        name='Growth',
        visible=False,
        marker=dict(
            colorscale='RdYlGn',
            cmid=0,  # Center at 0% growth
            cmin=min_color_growth,
            cmax=max_color_growth,
            showscale=False,
            line=dict(width=2)
        ),
        marker_colors=colors_growth,
        hovertemplate='<b>%{label}</b><br>' +
                      '%{customdata[1]}<br>' +
                      '<br><b>Összeg:</b> %{value:,.0f} Ft<br>' +
                      '<b>Felajánlók:</b> %{customdata[3]:,} fő<br>' +
                      '<b>Átlag/fő:</b> %{customdata[4]:,.0f} Ft<br>' +
                      '<b>Átlagos havi bruttó jövedelem:</b> %{customdata[5]:,.0f} Ft<br>' +
                      '<b>Részarány (%{customdata[8]}):</b> %{customdata[6]:.2f}%<br>' +
                      '<b>Részarány (teljes):</b> %{customdata[7]:.3f}%<br>' +
                      '<b>Előző évhez képest:</b> %{customdata[12]}%<br>' +
                      '<br><b>Cél:</b><br>%{customdata[9]}<br>' +
                      '<br><b>Éves történet:</b><br>%{customdata[10]}' +
                      '<extra></extra>',
        textfont=dict(size=10)
    ))

    # Add buttons to toggle between color modes
    fig_sunburst_interactive.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                direction="down",
                buttons=list([
                    dict(
                        args=[{"visible": [True, False, False]}],
                        label="Kategóriánkénti színezés",
                        method="update"
                    ),
                    dict(
                        args=[{"visible": [False, True, False]}],
                        label="Átlagjövedelem szerinti színezés",
                        method="update"
                    ),
                    dict(
                        args=[{"visible": [False, False, True]}],
                        label="Előző évhez képesti színezés",
                        method="update"
                    )
                ]),
                pad={"r": 10, "t": 10},
                showactive=True,
                x=1.0,
                xanchor="right",
                y=1.0,
                yanchor="top"
            ),
        ],
        width=1400,
        height=1400,
        margin=dict(t=100, l=10, r=10, b=300),
        title={
            'text': 'Civil Szervezetek - Sunburst (Interactive)<br><sub>Használd a gombokat a színezés váltásához</sub>',
            'x': 0.5,
            'xanchor': 'center'
        }
    )

    output_file = 'sunburst_chart_ALL_5000_go_interactive.html'
    fig_sunburst_interactive.write_html(output_file)
    print(f"   ✓ Saved to {output_file}")

    print("\n" + "=" * 80)
    print("DONE! All sunburst visualizations created:")
    print("  - sunburst_chart_ALL_5000_go.html (default colors)")
    print("  - sunburst_chart_ALL_5000_go_salary.html (colored by salary)")
    print("  - sunburst_chart_ALL_5000_go_interactive.html (interactive toggle)")
    print("Category nodes show aggregated stats with yearly percentages!")
    print("=" * 80)


if __name__ == '__main__':
    main()
