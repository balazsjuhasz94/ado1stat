"""
Unified Dashboard for Civil Organization Visualizations
Combines: Sunburst, Map, Time Series, Scatter Plot
With sidebar navigation and professional styling
"""

import pandas as pd
import plotly.graph_objects as go
import numpy as np
import json
import os
import sys
import re
from datetime import date
from flask import send_from_directory

# Base directory paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(BASE_DIR, 'data')

sys.path.insert(0, SCRIPT_DIR)

from dash import Dash, dcc, html, Input, Output, State, callback, no_update, dash_table
import copy
import dash_bootstrap_components as dbc
import create_visualizations_ALL_5000_v3_go as original

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def parse_historical_data_to_dict(historical_data):
    """Parse historical data into a dictionary of {year: amount}"""
    if not historical_data or len(historical_data) == 0:
        return {}
    year_amounts = {}
    if isinstance(historical_data, list):
        for entry in historical_data:
            try:
                year_str = entry.get('Év', '')
                amount_str = entry.get('Az érvényes civil kedvezményezettet megillető szja 1% összege', '0')
                year_int = int(year_str)
                amount_cleaned = amount_str.replace('Ft', '').replace(' ', '').strip()
                amount_int = int(amount_cleaned) if amount_cleaned else 0
                year_amounts[year_int] = amount_int
            except (ValueError, TypeError, KeyError):
                continue
    return year_amounts


def get_donor_count(historical_data, year):
    """Extract donor count for a specific year"""
    if not historical_data or not isinstance(historical_data, list):
        return 0
    for entry in historical_data:
        if entry.get('Év') == str(year):
            donor_str = entry.get('Érvényesen rendelkező magánszemélyek száma',
                                 entry.get('Felajánlók száma (fő)',
                                 entry.get('Felajánlók száma', '0')))
            if isinstance(donor_str, (int, float)):
                return int(donor_str)
            try:
                cleaned = str(donor_str).replace(' ', '').replace('fő', '').strip()
                return int(cleaned) if cleaned else 0
            except (ValueError, TypeError):
                return 0
    return 0


def extract_coordinates(json_data):
    """Extract lat/lon coordinates from JSON data"""
    try:
        azonosito = json_data.get('alapadatok', {}).get('azonosito_adatok', {})
        x_str = azonosito.get('x_koordináta', '')
        y_str = azonosito.get('y_koordináta', '')
        lat = float(x_str) if x_str else None
        lon = float(y_str) if y_str else None
        return lat, lon
    except:
        return None, None


def format_historical_table(hist_data):
    """Create table-format hover with Év, Összeg, Fő, Havi br. columns"""
    if not hist_data or not isinstance(hist_data, list):
        return 'Nincs éves adat'
    sorted_data = sorted(hist_data, key=lambda x: x.get('Év', '0'))
    rows = []
    rows.append("<span style='font-family: monospace;'>")
    rows.append("─────────────────────────────────────<br>")
    rows.append(f"{'Év':<4}  {'Összeg':>10}  {'Fő':>6}  {'Havi br.':>10}<br>")
    rows.append("─────────────────────────────────────<br>")
    has_data = False
    for entry in sorted_data:
        year = entry.get('Év', 'N/A')
        amount_str = entry.get('Az érvényes civil kedvezményezettet megillető szja 1% összege', '0')
        try:
            amount = int(amount_str.replace('Ft', '').replace(' ', '').strip())
        except:
            amount = 0
        if amount <= 0:
            continue
        has_data = True
        donors = 0
        donor_str = entry.get('Érvényesen rendelkező magánszemélyek száma',
                              entry.get('Felajánlók száma (fő)',
                              entry.get('Felajánlók száma', '0')))
        if isinstance(donor_str, (int, float)):
            donors = int(donor_str)
        else:
            try:
                cleaned = str(donor_str).replace(' ', '').replace('fő', '').strip()
                donors = int(cleaned) if cleaned else 0
            except:
                donors = 0
        if donors > 0:
            monthly_gross = int((amount / donors) * 100 * (100/15) / 12)
        else:
            monthly_gross = 0
        amount_s = f"{amount/1e6:>9.1f}M" if amount >= 1e6 else f"{amount/1e3:>9.0f}K"
        monthly_s = f"{monthly_gross/1e6:>9.1f}M" if monthly_gross >= 1e6 else (
            f"{monthly_gross/1e3:>9.0f}K" if monthly_gross >= 1e3 else f"{monthly_gross:>9}")
        rows.append(f"{year:<4}  {amount_s:>10}  {donors:>6}  {monthly_s:>10}<br>")
    rows.append("</span>")
    if not has_data:
        return 'Nincs éves adat'
    return ''.join(rows)


def format_historical_table_with_pct(hist_data, total_hist_data):
    """Table format with category percentage column"""
    if not hist_data or not isinstance(hist_data, list):
        return 'Nincs éves adat'
    # Build total lookup
    total_by_year = {}
    if total_hist_data and isinstance(total_hist_data, list):
        for entry in total_hist_data:
            y = entry.get('Év', '')
            a = entry.get('Az érvényes civil kedvezményezettet megillető szja 1% összege', '0')
            try:
                total_by_year[y] = int(a.replace('Ft', '').replace(' ', '').strip())
            except:
                pass
    sorted_data = sorted(hist_data, key=lambda x: x.get('Év', '0'))
    rows = []
    rows.append("<span style='font-family: monospace;'>")
    rows.append("──────────────────────────────────────────────<br>")
    rows.append(f"{'Év':<4}  {'Összeg':>10}  {'Fő':>6}  {'Havi br.':>10}  {'%':>6}<br>")
    rows.append("──────────────────────────────────────────────<br>")
    has_data = False
    for entry in sorted_data:
        year = entry.get('Év', 'N/A')
        amount_str = entry.get('Az érvényes civil kedvezményezettet megillető szja 1% összege', '0')
        try:
            amount = int(amount_str.replace('Ft', '').replace(' ', '').strip())
        except:
            amount = 0
        if amount <= 0:
            continue
        has_data = True
        donors = 0
        donor_str = entry.get('Érvényesen rendelkező magánszemélyek száma',
                              entry.get('Felajánlók száma (fő)',
                              entry.get('Felajánlók száma', '0')))
        if isinstance(donor_str, (int, float)):
            donors = int(donor_str)
        else:
            try:
                cleaned = str(donor_str).replace(' ', '').replace('fő', '').strip()
                donors = int(cleaned) if cleaned else 0
            except:
                donors = 0
        if donors > 0:
            monthly_gross = int((amount / donors) * 100 * (100/15) / 12)
        else:
            monthly_gross = 0
        total = total_by_year.get(year, 0)
        pct = (amount / total * 100) if total > 0 else 0
        amount_s = f"{amount/1e6:>9.1f}M" if amount >= 1e6 else f"{amount/1e3:>9.0f}K"
        monthly_s = f"{monthly_gross/1e6:>9.1f}M" if monthly_gross >= 1e6 else (
            f"{monthly_gross/1e3:>9.0f}K" if monthly_gross >= 1e3 else f"{monthly_gross:>9}")
        rows.append(f"{year:<4}  {amount_s:>10}  {donors:>6}  {monthly_s:>10}  {pct:>5.1f}%<br>")
    rows.append("</span>")
    if not has_data:
        return 'Nincs éves adat'
    return ''.join(rows)


def lighten_color(hex_color, factor=0.3):
    """Lighten a hex color by mixing with white"""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f'#{r:02x}{g:02x}{b:02x}'


def get_countdown_text():
    """Calculate days remaining until May 20 tax 1% donation deadline."""
    today = date.today()
    deadline = date(today.year, 5, 20)
    if today > deadline:
        deadline = date(today.year + 1, 5, 20)
    days_left = (deadline - today).days
    if days_left == 0:
        return "Ma van a határidő!", "today"
    elif days_left <= 7:
        return f"{days_left} nap van hátra", "urgent"
    elif days_left <= 30:
        return f"{days_left} nap van hátra", "soon"
    else:
        return f"{days_left} nap van hátra", "normal"


def make_banner():
    """Create the top banner with project info and countdown."""
    countdown_text, urgency = get_countdown_text()
    urgency_colors = {
        "today": "#dc3545", "urgent": "#e85d04",
        "soon": "#f4a261", "normal": "#2a9d8f",
    }
    badge_color = urgency_colors.get(urgency, "#2a9d8f")

    return html.Div([
        html.Div([
            html.Div([
                html.Span("Civil Szervezetek Adó 1% Elemzése", style={
                    'fontWeight': '700', 'fontSize': '15px', 'color': '#ffffff'
                }),
                html.Span(" — ", style={'color': 'rgba(255,255,255,0.5)', 'margin': '0 8px'}),
                html.Span(
                    "A legnagyobb szervezetek felajánlásainak interaktív áttekintése",
                    style={'fontSize': '13px', 'color': 'rgba(255,255,255,0.8)'}
                ),
            ], style={'flex': '1'}),
            html.Div([
                html.Span("Felajánlási határidő: május 20.", style={
                    'fontSize': '12px', 'color': 'rgba(255,255,255,0.7)', 'marginRight': '12px'
                }),
                html.Span(countdown_text, style={
                    'backgroundColor': badge_color, 'color': '#fff',
                    'padding': '6px 18px', 'borderRadius': '20px',
                    'fontSize': '15px', 'fontWeight': '700', 'whiteSpace': 'nowrap',
                    'boxShadow': '0 2px 4px rgba(0,0,0,0.2)',
                }),
            ], style={'display': 'flex', 'alignItems': 'center'}),
        ], style={
            'display': 'flex', 'alignItems': 'center',
            'justifyContent': 'space-between', 'flexWrap': 'wrap', 'gap': '8px',
        }),
    ], className="top-banner")


PAGE_DESCRIPTIONS = {
    'sunburst': (
        "Itt a szervezeteket kategóriák szerint látod hierarchikus megoszlásban. "
        "Kattints egy szektorra, hogy belenézz a részletekbe — a középső körre kattintva tudsz visszalépni. "
        "A felső gombokkal válthatsz a kategória szín, a becsült jövedelem és az előző évhez képesti változás nézetek között."
    ),
    'map': (
        "A térképen a szervezetek földrajzi elhelyezkedését látod. "
        "A keresővel rákereshetsz egy szervezetre, görgetéssel tudsz nagyítani, "
        "és bármelyik pontra kattintva megnézheted a részleteket."
    ),
    'timeseries': (
        "Itt az egyes szervezetek éves adó 1%-os bevételeit tudod nyomon követni. "
        "Válassz kategóriát a bal oldali legördülőből, és szűrj összeg szerint a csúszkával. "
        "A három nézet között gombokkal válthatsz: "
        "az Összeg nézet a nyers forint értékeket mutatja szervezetenként; "
        "a Kat. % nézet azt mutatja, hogy az adott szervezet a kategóriáján belül mekkora részt képvisel (%); "
        "az Eloszlás nézet pedig azt, hogyan oszlik meg a kategória összege a szervezetek között (halmozott terület). "
        "⚠ A korábbi évek adatai csak azon szervezeteket tartalmazzák, amelyek 2025-ben is kaptak felajánlást — "
        "így az összesített összegek az egyes években a valósnál alacsonyabbak lehetnek."
    ),
    'category_timeseries': (
        "Ez az oldal a kategóriák összesített éves trendjeit mutatja. "
        "Válassz egy szülő kategóriát, vagy nézd meg az összeset egyben. "
        "Az Összeg nézet a kategóriák forint értékeit mutatja; "
        "az Arány (%) nézet megmutatja, hogyan változott az egyes kategóriák részesedése az összes felajánlásból; "
        "az Eloszlás nézet pedig a kategóriák egymásra halmozott trendjét, hogy lásd, melyik nőtt vagy csökkent. "
        "⚠ A korábbi évek adatai csak azon szervezeteket tartalmazzák, amelyek 2025-ben is kaptak felajánlást — "
        "így az összesített összegek az egyes években a valósnál alacsonyabbak lehetnek."
    ),
    'scatter': (
        "Ezen a pontdiagramon az adó 1%-os összeget veted össze a felajánlók becsült átlagos havi bruttó jövedelmével. "
        "Minden pont egy szervezet — vidd rá az egeret a részletekért. "
        "A jelmagyarázatban kategóriákat tudsz ki/be kapcsolni."
    ),
    'city': (
        "Keress rá egy településre, és nézd meg az ott bejegyzett vagy a közelben lévő szervezeteket. "
        "A székhely/10 km gombokkal válthatsz a pontos székhely és a 10 km-es körzet között. "
        "Bal oldalon a térkép, jobb oldalon az éves trend látható."
    ),
    'about': None,
}


def make_page_info(page_key):
    """Create a subtle info box with page explanation."""
    text = PAGE_DESCRIPTIONS.get(page_key)
    if not text:
        return html.Div()
    return html.Div([
        html.Span("ℹ ", style={
            'fontWeight': 'bold', 'marginRight': '6px', 'fontSize': '14px', 'color': '#4a9eff'
        }),
        html.Span(text),
    ], className="page-info-box")


def wrap_page(page_key, title, content_children):
    """Wrap page content with banner and info box."""
    return html.Div([
        make_banner(),
        html.H2(title, className="page-title"),
        make_page_info(page_key),
        *content_children
    ])


# ============================================================================
# DATA LOADING (shared across all pages)
# ============================================================================

print("=" * 60)
print("Loading data for dashboard...")
print("=" * 60)

# 1. Load CSV categories
df_categories = pd.read_csv(os.path.join(DATA_DIR, 'organization_categories_ALL_10000.csv'), encoding='utf-8-sig')
print(f"  Categories: {len(df_categories)} organizations")

# 2. Load Excel data
excel_file = os.path.join(DATA_DIR, 'Szja 1-os felajanlasban reszesult civil kedvezmenyezettek_2025.xlsx')
df_excel = pd.read_excel(excel_file, sheet_name='Munka1', header=1)
df_excel['összeg'] = pd.to_numeric(df_excel['Felajánlott összeg (Ft)'], errors='coerce').fillna(0).astype(int)
df_excel['db'] = pd.to_numeric(df_excel['Felajánlók száma (fő)'], errors='coerce').fillna(0).astype(int)
df_amounts = df_excel[['Adószám', 'Név', 'összeg', 'db']].copy()
print(f"  Excel: {len(df_amounts)} organizations")

# 3. Load JSON data (with coordinates for map)
organizations_folder = os.path.join(BASE_DIR, 'organizations_by_adoszam')
org_data_list = []
coord_data = {}  # adoszam -> (lat, lon)

if os.path.exists(organizations_folder):
    json_files = [f for f in os.listdir(organizations_folder) if f.endswith('.json')]
    print(f"  JSON files: {len(json_files)}")
    for i, filename in enumerate(json_files):
        if (i + 1) % 500 == 0:
            print(f"    Processing {i+1}/{len(json_files)}...")
        filepath = os.path.join(organizations_folder, filename)
        try:
            json_data = original.read_json_file(filepath)
            org_info = original.extract_org_data(json_data)
            if org_info:
                org_data_list.append(org_info)
                # Also extract coordinates
                lat, lon = extract_coordinates(json_data)
                if lat is not None and lon is not None:
                    coord_data[str(org_info['adoszam'])] = (lat, lon)
        except:
            pass
    print(f"  Extracted: {len(org_data_list)} orgs, {len(coord_data)} with coordinates")

df_orgs = pd.DataFrame(org_data_list)

# 4. Merge all data
df_categories['Adószám'] = df_categories['Adószám'].astype(str)
df_orgs['adoszam'] = df_orgs['adoszam'].astype(str)
df_amounts['Adószám'] = df_amounts['Adószám'].astype(str)

df_merged = df_categories.merge(df_orgs, left_on='Adószám', right_on='adoszam', how='left')
df_merged = df_merged.merge(df_amounts, left_on='Adószám', right_on='Adószám', how='left')
df_merged = df_merged.dropna(subset=['összeg'])
df_merged['összeg'] = df_merged['összeg'].astype(int)
df_merged['db'] = df_merged['db'].astype(int)
df_merged['purpose'] = df_merged['purpose'].fillna(df_merged.get('Cél (első 200 karakter)', ''))

# Calculate common metrics
df_merged['átlag_per_donor'] = (df_merged['összeg'] / df_merged['db']).fillna(0).round(0)
df_merged['monthly_gross'] = (df_merged['átlag_per_donor'] * 100 * (100/15) / 12).fillna(0).round(0).astype(int)
df_merged['short_name'] = df_merged['Szervezet neve'].str[:50]
df_merged['formatted_purpose'] = df_merged['purpose'].apply(original.format_purpose_multiline)
df_merged['formatted_purpose_short'] = df_merged['purpose'].apply(
    lambda x: (str(x)[:50] + '…') if x and len(str(x)) > 50 else (x or 'Nincs leírás'))
df_merged['historical_table'] = df_merged['historical_data'].apply(format_historical_table)
df_merged['historical_table_short'] = df_merged['historical_data'].apply(
    lambda h: format_historical_table(sorted(h, key=lambda x: x.get('Év', '0'))[-3:]) if h and isinstance(h, list) else 'Nincs éves adat')
df_merged['yoy_growth'] = df_merged['historical_data'].apply(original.calculate_yoy_growth)
df_merged['szekhely'] = df_merged['szekhely'].fillna(df_merged.get('Székhely', '')).fillna('Nincs adat')
df_merged['parent_category'] = df_merged['Szülő kategória']
df_merged['leaf_category'] = df_merged['Új kategória (legalsó szint)']
df_merged = df_merged.dropna(subset=['parent_category', 'leaf_category'])

# Add coordinates
df_merged['lat'] = df_merged['Adószám'].map(lambda x: coord_data.get(x, (None, None))[0])
df_merged['lon'] = df_merged['Adószám'].map(lambda x: coord_data.get(x, (None, None))[1])

# Historical dict for time series
df_merged['historical_dict'] = df_merged['historical_data'].apply(parse_historical_data_to_dict)
# historical_table already computed above, reuse it


# Time series specific data
df_ts = df_merged[df_merged['historical_dict'].apply(lambda x: len(x) > 0)].copy()
all_years = set()
for hist_dict in df_ts['historical_dict']:
    all_years.update(hist_dict.keys())
all_years = sorted(list(all_years))
leaf_categories = sorted(df_ts['leaf_category'].unique())

print(f"\nData ready: {len(df_merged)} total orgs, {len(df_ts)} with history")
print(f"Years: {min(all_years)} - {max(all_years)}, Categories: {len(leaf_categories)}")

# Pre-compute category-level yearly aggregations for fast timeseries
print("Pre-computing category timeseries aggregations...")
cat_year_totals = {}  # {('leaf', leaf_cat, year): amount, ('parent', parent_cat, year): amount}
for _, row in df_ts.iterrows():
    hist = row['historical_dict']
    lc = row['leaf_category']
    pc = row['parent_category']
    for year, amount in hist.items():
        if amount > 0:
            cat_year_totals[('leaf', lc, year)] = cat_year_totals.get(('leaf', lc, year), 0) + amount
            cat_year_totals[('parent', pc, year)] = cat_year_totals.get(('parent', pc, year), 0) + amount
            cat_year_totals[('all', '__all__', year)] = cat_year_totals.get(('all', '__all__', year), 0) + amount
print(f"Pre-computed {len(cat_year_totals)} category-year aggregations")

# Pre-compute leaf_category → parent_category mapping
leaf_to_parent_map = {}
for _, row in df_ts[['leaf_category', 'parent_category']].drop_duplicates().iterrows():
    leaf_to_parent_map[row['leaf_category']] = row['parent_category']

# Load pre-computed city radius data
city_data_path = os.path.join(DATA_DIR, 'city_radius_data.json')
if os.path.exists(city_data_path):
    with open(city_data_path, 'r', encoding='utf-8') as f:
        city_radius_data = json.load(f)
    print(f"  City data: {len(city_radius_data)} cities loaded")
else:
    city_radius_data = {}
    print("  WARNING: city_radius_data.json not found!")

# Build székhely-based city data (exact city match from szekhely field)
import re as _re
city_szekhely_data = {}  # city -> {'adoszamok': [...], 'lat': ..., 'lon': ...}
for _, row in df_merged.iterrows():
    sz = row.get('szekhely', '')
    if not sz or sz == 'Nincs adat':
        continue
    m = _re.match(r'^\d{4}\s+(.+)$', str(sz).strip())
    if not m:
        continue
    tokens = m.group(1).split()
    if not tokens:
        continue
    city_name = tokens[0].upper().rstrip('.,;:')
    if len(city_name) < 2:
        continue
    adoszam = str(row['Adószám'])
    if city_name not in city_szekhely_data:
        city_szekhely_data[city_name] = {'adoszamok': []}
    city_szekhely_data[city_name]['adoszamok'].append(adoszam)

# Add lat/lon for székhely cities from radius data or compute average
for city_name, cdata in city_szekhely_data.items():
    if city_name in city_radius_data:
        cdata['lat'] = city_radius_data[city_name]['lat']
        cdata['lon'] = city_radius_data[city_name]['lon']
    else:
        # Average coords of orgs in this city
        lats = [coord_data.get(a, (None, None))[0] for a in cdata['adoszamok']]
        lons = [coord_data.get(a, (None, None))[1] for a in cdata['adoszamok']]
        lats = [x for x in lats if x is not None]
        lons = [x for x in lons if x is not None]
        if lats and lons:
            cdata['lat'] = sum(lats) / len(lats)
            cdata['lon'] = sum(lons) / len(lons)
        else:
            cdata['lat'] = None
            cdata['lon'] = None
    cdata['org_count'] = len(cdata['adoszamok'])

print(f"  Székhely-based city data: {len(city_szekhely_data)} cities")

# Dropdown options: combine all cities from both sources
all_city_names = sorted(set(list(city_radius_data.keys()) + list(city_szekhely_data.keys())))
city_dropdown_options = []
for city in all_city_names:
    sz_count = city_szekhely_data.get(city, {}).get('org_count', 0)
    city_dropdown_options.append({'label': f"{city} ({sz_count} szervezet)", 'value': city})

# Color palette
COLORS_20 = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
    '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
    '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5'
]

PARENT_COLORS = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00',
                 '#ccaa00', '#a65628', '#f781bf', '#999999', '#66c2a5']

# ============================================================================
# FIGURE BUILDERS
# ============================================================================

def build_sunburst_figure():
    """Build sunburst chart with 3 color modes"""
    print("  Building sunburst...")
    total_összeg = df_merged['összeg'].sum()
    total_db = df_merged['db'].sum()
    total_aggregated_hist = original.aggregate_historical_data(df_merged)

    # Sort and split top N vs rest
    df_sorted = df_merged.sort_values('összeg', ascending=False).reset_index(drop=True)
    TOP_N = 1000
    top_orgs = df_sorted.head(TOP_N).copy()
    remaining_orgs = df_sorted.iloc[TOP_N:].copy()

    # Build tree nodes
    nodes = []
    id_map = {}
    current_id = 0

    # Root
    all_hist_chart = format_historical_table(total_aggregated_hist)
    all_yoy_growth = original.calculate_yoy_growth(total_aggregated_hist)
    root_purpose = (
        "Ez az összesítés a legtöbb 1%-os SZJA felajánlást kapó<br>"
        f"top {len(df_merged):,} szervezetet tartalmazza, mely az összes<br>"
        "felajánlás kb. 89%-át teszi ki.<br>"
        "Az összes felajánlás országosan ~20,3 milliárd Ft volt.<br>"
        "A fennmaradó ~27 000 kisebb szervezet adatai<br>"
        "nincsenek benne az elemzésben."
    )
    nodes.append({
        'id': str(current_id), 'label': 'Összes', 'parent': '',
        'összeg': total_összeg, 'db': total_db,
        'szekhely': f"{len(df_merged):,} szervezet összesítve",
        'formatted_purpose': root_purpose, 'historical_chart': all_hist_chart,
        'org_name': 'Összes szervezet', 'yoy_growth': all_yoy_growth, 'depth': 0
    })
    id_map['__root__'] = str(current_id)
    current_id += 1

    # Parent categories
    for parent_cat in df_merged['parent_category'].unique():
        if pd.notna(parent_cat):
            subset = df_merged[df_merged['parent_category'] == parent_cat]
            aggregated_hist = original.aggregate_historical_data(subset)
            hist_chart = format_historical_table_with_pct(aggregated_hist, total_aggregated_hist)
            yoy_growth = original.calculate_yoy_growth(aggregated_hist)
            top5 = subset.nlargest(5, 'összeg')
            top5_lines = [f"  {row['Szervezet neve'][:50]}: {row['összeg']:,.0f} Ft"
                          for _, row in top5.iterrows()]
            purpose_text = (f"{len(subset)} szervezet ebben a kategóriában<br>"
                           f"Top 5:<br>" + "<br>".join(top5_lines))
            nodes.append({
                'id': str(current_id), 'label': parent_cat, 'parent': id_map['__root__'],
                'összeg': subset['összeg'].sum(), 'db': subset['db'].sum(),
                'szekhely': f"{len(subset)} szervezet",
                'formatted_purpose': purpose_text, 'historical_chart': hist_chart,
                'org_name': parent_cat, 'yoy_growth': yoy_growth, 'depth': 1
            })
            id_map[parent_cat] = str(current_id)
            current_id += 1

    # Leaf categories
    for parent_cat in df_merged['parent_category'].unique():
        if pd.notna(parent_cat):
            for leaf_cat in df_merged[df_merged['parent_category'] == parent_cat]['leaf_category'].unique():
                if pd.notna(leaf_cat):
                    subset = df_merged[(df_merged['parent_category'] == parent_cat) &
                                      (df_merged['leaf_category'] == leaf_cat)]
                    aggregated_hist = original.aggregate_historical_data(subset)
                    hist_chart = format_historical_table_with_pct(aggregated_hist, total_aggregated_hist)
                    yoy_growth = original.calculate_yoy_growth(aggregated_hist)
                    cat_key = f"{parent_cat}|{leaf_cat}"
                    top5 = subset.nlargest(5, 'összeg')
                    top5_lines = [f"  {row['Szervezet neve'][:50]}: {row['összeg']:,.0f} Ft"
                                  for _, row in top5.iterrows()]
                    purpose_text = (f"{len(subset)} szervezet ebben az alkategóriában<br>"
                                   f"Top 5:<br>" + "<br>".join(top5_lines))
                    nodes.append({
                        'id': str(current_id), 'label': leaf_cat,
                        'parent': id_map.get(parent_cat, '0'),
                        'összeg': subset['összeg'].sum(), 'db': subset['db'].sum(),
                        'szekhely': f"{len(subset)} szervezet",
                        'formatted_purpose': purpose_text, 'historical_chart': hist_chart,
                        'org_name': leaf_cat, 'yoy_growth': yoy_growth, 'depth': 2
                    })
                    id_map[cat_key] = str(current_id)
                    current_id += 1

    # Top N individual orgs (grouped by leaf category, so "további" can go last per group)
    remaining_nodes = []  # collect "további" nodes separately to append last

    for _, row in top_orgs.iterrows():
        parent_key = f"{row['parent_category']}|{row['leaf_category']}"
        nodes.append({
            'id': str(current_id), 'label': row['short_name'],
            'parent': id_map.get(parent_key, '0'),
            'összeg': row['összeg'], 'db': row['db'], 'szekhely': row['szekhely'],
            'formatted_purpose': str(row['formatted_purpose']),
            'historical_chart': row['historical_table'],
            'org_name': row['Szervezet neve'], 'yoy_growth': row['yoy_growth'], 'depth': 3
        })
        current_id += 1

    # Aggregated remaining orgs — collected separately, appended last
    for parent_cat in remaining_orgs['parent_category'].unique():
        if pd.notna(parent_cat):
            for leaf_cat in remaining_orgs[remaining_orgs['parent_category'] == parent_cat]['leaf_category'].unique():
                if pd.notna(leaf_cat):
                    subset = remaining_orgs[(remaining_orgs['parent_category'] == parent_cat) &
                                            (remaining_orgs['leaf_category'] == leaf_cat)]
                    if len(subset) > 0:
                        aggregated_hist = original.aggregate_historical_data(subset)
                        hist_chart = format_historical_table(aggregated_hist)
                        yoy_growth = original.calculate_yoy_growth(aggregated_hist)
                        parent_key = f"{parent_cat}|{leaf_cat}"
                        # Build top 10 list for hover
                        top10 = subset.nlargest(10, 'összeg')
                        top10_lines = [f"  {row['Szervezet neve'][:45]}: {row['összeg']:,.0f} Ft"
                                       for _, row in top10.iterrows()]
                        top10_text = (
                            "Legnagyobb szervezetek a továbbiak közül:<br>" +
                            "<br>".join(top10_lines) +
                            "<br><br>Ezek a szervezetek az átláthatóság miatt lettek<br>"
                            "összesítve, de a többi oldalon egyenként is<br>"
                            "kereshetők (Térkép, Évenkénti adatok, Település)."
                        )
                        remaining_nodes.append({
                            'id': str(current_id), 'label': f"további kisebb {leaf_cat}",
                            'parent': id_map.get(parent_key, '0'),
                            'összeg': subset['összeg'].sum(), 'db': subset['db'].sum(),
                            'szekhely': f"{len(subset)} szervezet összesítve",
                            'formatted_purpose': top10_text,
                            'historical_chart': hist_chart,
                            'org_name': f"További {len(subset)} kisebb szervezet",
                            'yoy_growth': yoy_growth, 'depth': 3
                        })
                        current_id += 1

    # Append "további" nodes last so they appear at the end in the chart
    nodes.extend(remaining_nodes)

    # Calculate statistics for nodes
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
            if parent_node:
                node['parent_label'] = parent_node['label']
                node['pct_of_parent'] = (node['összeg'] / parent_node['összeg'] * 100) if parent_node['összeg'] > 0 else 0
            else:
                node['parent_label'] = ''
                node['pct_of_parent'] = 0
        else:
            node['parent_label'] = ''
            node['pct_of_parent'] = 100

    # Build figure data
    ids = [n['id'] for n in nodes]
    labels = [n['label'] for n in nodes]
    parents = [n['parent'] for n in nodes]
    values = [n['összeg'] for n in nodes]

    customdata = [[
        n['org_name'], n['szekhely'], n['összeg'], n['db'],
        n['átlag'], n['monthly_gross'], n['pct_of_parent'], n['pct_of_total'],
        n['parent_label'], n['formatted_purpose'], n['historical_chart'],
        n['yoy_growth'], f"{n['yoy_growth']:+.1f}"
    ] for n in nodes]

    hover_tpl = (
        '<b>%{label}</b><br>%{customdata[1]}<br>'
        '<br><b>Összeg:</b> %{value:,.0f} Ft<br>'
        '<b>Felajánlók:</b> %{customdata[3]:,} fő<br>'
        '<b>Átlag/fő:</b> %{customdata[4]:,.0f} Ft<br>'
        '<b>Átlagos havi bruttó jövedelem:</b> %{customdata[5]:,.0f} Ft<br>'
        '<b>Részarány (%{customdata[8]}):</b> %{customdata[6]:.2f}%<br>'
        '<b>Részarány (teljes):</b> %{customdata[7]:.3f}%<br>'
        '<b>Előző évhez képest:</b> %{customdata[12]}%<br>'
        '<br><b>Cél:</b><br>%{customdata[9]}<br>'
        '<br><b>Éves történet:</b><br>%{customdata[10]}'
        '<extra></extra>'
    )

    colors_salary = [n['monthly_gross'] for n in nodes]
    salary_series = pd.Series([n['monthly_gross'] for n in nodes if n['db'] > 0])
    min_salary = salary_series.quantile(0.05)
    max_salary = salary_series.quantile(0.85)

    colors_growth = [n['yoy_growth'] for n in nodes]

    fig = go.Figure()

    # Default trace
    fig.add_trace(go.Sunburst(
        ids=ids, labels=labels, parents=parents, values=values,
        branchvalues='total', customdata=customdata, name='Default',
        visible=True, hovertemplate=hover_tpl, textfont=dict(size=15),
        maxdepth=3, sort=False
    ))

    # Salary trace
    fig.add_trace(go.Sunburst(
        ids=ids, labels=labels, parents=parents, values=values,
        branchvalues='total', customdata=customdata, name='Salary',
        visible=False, maxdepth=3, sort=False, marker=dict(
            colorscale='RdYlGn', cmid=(min_salary + max_salary) / 2,
            cmin=min_salary, cmax=max_salary,
            showscale=True, colorbar=dict(
                title=dict(text='Havi bruttó (Ft)', side='right'),
                x=1.02, len=0.6, thickness=15
            ),
            line=dict(width=2)
        ), marker_colors=colors_salary,
        hovertemplate=hover_tpl, textfont=dict(size=15)
    ))

    # Growth trace
    fig.add_trace(go.Sunburst(
        ids=ids, labels=labels, parents=parents, values=values,
        branchvalues='total', customdata=customdata, name='Growth',
        visible=False, maxdepth=3, sort=False, marker=dict(
            colorscale='RdYlGn', cmid=0, cmin=-50.0, cmax=50.0,
            showscale=True, colorbar=dict(
                title=dict(text='Változás (%)', side='right'),
                x=1.02, len=0.6, thickness=15
            ),
            line=dict(width=2)
        ), marker_colors=colors_growth,
        hovertemplate=hover_tpl, textfont=dict(size=15)
    ))

    fig.update_layout(
        annotations=[dict(
            text="Színezés:", showarrow=False,
            x=0.35, y=1.02, xref="paper", yref="paper",
            font=dict(size=13, color="#333")
        )],
        updatemenus=[dict(
            type="buttons", direction="right",
            buttons=[
                dict(args=[{"visible": [True, False, False]}], label="Kategória", method="update"),
                dict(args=[{"visible": [False, True, False]}], label="Átlagos jövedelem", method="update"),
                dict(args=[{"visible": [False, False, True]}], label="Tavalyhoz képesti változás", method="update"),
            ],
            pad={"r": 10, "t": 10}, showactive=True,
            x=0.45, xanchor="left", y=1.02, yanchor="middle"
        )],
        margin=dict(t=50, l=0, r=0, b=100),
        height=1100
    )

    return fig


def build_map_figure():
    """Build map visualization"""
    print("  Building map...")
    df_map = df_merged.dropna(subset=['lat', 'lon']).copy()
    df_map['átlag'] = (df_map['összeg'] / df_map['db']).fillna(0).round()

    parent_categories = sorted(df_map['parent_category'].dropna().unique())
    color_map = {}
    for i, cat in enumerate(parent_categories):
        color_map[cat] = PARENT_COLORS[i % len(PARENT_COLORS)]

    traces = []
    trace_info = []

    for parent_cat in parent_categories:
        leaf_cats = sorted(df_map[df_map['parent_category'] == parent_cat]['leaf_category'].unique())
        for leaf_cat in leaf_cats:
            df_sub = df_map[(df_map['parent_category'] == parent_cat) &
                            (df_map['leaf_category'] == leaf_cat)]

            trace = go.Scattermapbox(
                lat=df_sub['lat'], lon=df_sub['lon'], mode='markers',
                marker=dict(
                    size=df_sub['összeg'].apply(lambda x: min(max((x ** 0.5) / 200, 5), 25)),
                    color=color_map[parent_cat], opacity=0.8, sizemode='diameter'
                ),
                text=df_sub['Szervezet neve'],
                name=f"{parent_cat} / {leaf_cat}",
                customdata=list(zip(
                    df_sub['Szervezet neve'], df_sub['szekhely'], df_sub['összeg'],
                    df_sub['db'], df_sub['átlag'], df_sub['monthly_gross'],
                    df_sub['parent_category'], df_sub['leaf_category'],
                    df_sub['formatted_purpose'],
                    df_sub['yoy_growth'].apply(lambda x: f"{x:+.1f}"),
                    df_sub['historical_table'],
                    df_sub['formatted_purpose_short'],
                    df_sub['historical_table_short']
                )),
                hovertemplate=(
                    '<b>%{customdata[0]}</b><br>%{customdata[1]}<br>'
                    '<b>Kategória:</b> %{customdata[6]} → %{customdata[7]}<br><br>'
                    '<b>Összeg:</b> %{customdata[2]:,.0f} Ft<br>'
                    '<b>Felajánlók:</b> %{customdata[3]:,} fő<br>'
                    '<b>Átlag/fő:</b> %{customdata[4]:,.0f} Ft<br>'
                    '<b>Havi bruttó:</b> %{customdata[5]:,.0f} Ft<br>'
                    '<b>Előző évhez képest:</b> %{customdata[9]}%<br>'
                    '<br><b>Cél:</b> %{customdata[8]}<br>'
                    '<br>%{customdata[10]}'
                    '<extra></extra>'
                ),
                visible=True
            )
            traces.append(trace)
            trace_info.append({'parent': parent_cat, 'leaf': leaf_cat, 'trace_idx': len(traces) - 1})

    fig = go.Figure(data=traces)

    # Build dropdown buttons
    buttons = [dict(label="▼ Összes kategória", method="update",
                    args=[{"visible": [True] * len(traces)}])]
    for parent_cat in parent_categories:
        visible_parent = [info['parent'] == parent_cat for info in trace_info]
        buttons.append(dict(label=f"▼ {parent_cat}", method="update",
                            args=[{"visible": visible_parent}]))
        for info in trace_info:
            if info['parent'] == parent_cat:
                visible_leaf = [False] * len(traces)
                visible_leaf[info['trace_idx']] = True
                buttons.append(dict(label=f"    • {info['leaf']}", method="update",
                                    args=[{"visible": visible_leaf}]))

    fig.update_layout(
        mapbox=dict(style="carto-positron", center=dict(lat=47.2, lon=19.5), zoom=6.5),
        dragmode='pan', hovermode='closest',
        updatemenus=[dict(
            type="dropdown", direction="down", x=0.01, y=0.99,
            xanchor="left", yanchor="top", buttons=buttons,
            bgcolor="white", bordercolor="gray", borderwidth=1, font=dict(size=11)
        )],
        height=800, margin=dict(l=0, r=0, t=10, b=0), showlegend=False
    )

    return fig


def build_scatter_figure():
    """Build scatter plot"""
    print("  Building scatter...")
    df_plot = df_merged[df_merged['összeg'] > 0].copy()
    parent_cats = sorted(df_plot['parent_category'].unique())

    parent_color_map = {}
    default_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                      '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    for i, cat in enumerate(parent_cats):
        parent_color_map[cat] = default_colors[i % len(default_colors)]

    leaf_colors = {}
    for parent_cat in parent_cats:
        base_color = parent_color_map[parent_cat]
        leaf_cats = sorted(df_plot[df_plot['parent_category'] == parent_cat]['leaf_category'].unique())
        for idx, leaf_cat in enumerate(leaf_cats):
            if len(leaf_cats) == 1:
                leaf_colors[leaf_cat] = base_color
            else:
                factor = idx / (len(leaf_cats) - 1) * 0.5
                leaf_colors[leaf_cat] = lighten_color(base_color, factor)

    fig = go.Figure()

    for parent_cat in parent_cats:
        df_parent = df_plot[df_plot['parent_category'] == parent_cat]
        leaf_cats = sorted(df_parent['leaf_category'].unique())

        for idx, leaf_cat in enumerate(leaf_cats):
            df_leaf = df_parent[df_parent['leaf_category'] == leaf_cat]

            customdata = []
            for _, row in df_leaf.iterrows():
                customdata.append([
                    row['Szervezet neve'], row['szekhely'], row['összeg'], row['db'],
                    row['átlag_per_donor'], row['monthly_gross'],
                    parent_cat, row['formatted_purpose'],
                    f"{row['yoy_growth']:+.1f}"
                ])

            fig.add_trace(go.Scatter(
                x=df_leaf['összeg'], y=df_leaf['monthly_gross'], mode='markers',
                name=leaf_cat, legendgroup=parent_cat,
                legendgrouptitle_text=parent_cat if idx == 0 else None,
                marker=dict(size=8, color=leaf_colors.get(leaf_cat, '#999'),
                            opacity=0.7, line=dict(width=0.5, color='white')),
                customdata=customdata,
                hovertemplate=(
                    '<b>%{customdata[0]}</b><br>%{customdata[1]}<br>'
                    '<br><b>Összeg:</b> %{customdata[2]:,.0f} Ft<br>'
                    '<b>Felajánlók:</b> %{customdata[3]:,} fő<br>'
                    '<b>Átlag/fő:</b> %{customdata[4]:,.0f} Ft<br>'
                    '<b>Havi bruttó:</b> %{customdata[5]:,.0f} Ft<br>'
                    '<b>Előző évhez képest:</b> %{customdata[8]}%<br>'
                    '<br><b>Kategória:</b> %{customdata[6]} → ' + leaf_cat + '<br>'
                    '<br><b>Cél:</b> %{customdata[7]}...'
                    '<extra></extra>'
                )
            ))

    fig.update_layout(
        xaxis=dict(title='Felajánlott összeg (Ft)', type='log',
                   gridcolor='lightgray', showline=True, linewidth=1, linecolor='black', mirror=True),
        yaxis=dict(title='Átlagos bruttó havi jövedelem (Ft)', type='log',
                   gridcolor='lightgray', showline=True, linewidth=1, linecolor='black', mirror=True),
        plot_bgcolor='white', hovermode='closest', height=800,
        legend=dict(title=dict(text='Kategóriák', font=dict(size=13)),
                    font=dict(size=10), groupclick="toggleitem",
                    bgcolor='rgba(255,255,255,0.8)', bordercolor='lightgray', borderwidth=1),
        margin=dict(l=80, r=20, t=20, b=80)
    )

    return fig


# ============================================================================
# PRE-BUILD STATIC FIGURES
# ============================================================================

print("\nBuilding figures...")
sunburst_fig = build_sunburst_figure()
map_fig = build_map_figure()
scatter_fig = build_scatter_figure()
print("All figures ready!\n")

# Build org search options for map (name → lat/lon lookup)
df_map_search = df_merged.dropna(subset=['lat', 'lon']).copy()
df_map_search = df_map_search.sort_values('összeg', ascending=False)
map_org_options = [
    {'label': f"{row['Szervezet neve']} ({row['szekhely']})", 'value': idx}
    for idx, row in df_map_search.iterrows()
]
# Store lat/lon/name lookup
map_org_lookup = {
    idx: {'lat': row['lat'], 'lon': row['lon'], 'name': row['Szervezet neve']}
    for idx, row in df_map_search.iterrows()
}

# ============================================================================
# DASH APP
# ============================================================================

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server  # Expose Flask server for gunicorn

IMGS_DIR = os.path.join(BASE_DIR, 'imgs')

@server.route('/imgs/<path:filename>')
def serve_image(filename):
    return send_from_directory(IMGS_DIR, filename)

# Custom CSS
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Civil Szervezetek Adó 1% Elemzése</title>
        {%favicon%}
        {%css%}
        <style>
            body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }

            .sidebar {
                position: fixed;
                top: 0;
                left: 0;
                bottom: 0;
                width: 260px;
                background: #1a1a2e;
                color: #e0e0e0;
                padding: 0;
                overflow-y: auto;
                z-index: 1000;
                box-shadow: 2px 0 10px rgba(0,0,0,0.3);
            }

            .sidebar-header {
                padding: 24px 20px 16px;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }

            .sidebar-header h3 {
                font-size: 18px;
                font-weight: 700;
                color: #ffffff;
                margin: 0 0 4px 0;
            }

            .sidebar-header p {
                font-size: 12px;
                color: #8888aa;
                margin: 0;
            }

            .nav-section { padding: 8px 0; }

            .nav-group-label {
                display: flex;
                align-items: center;
                padding: 10px 20px 6px;
                color: #8888bb;
                font-size: 11px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 1.2px;
                margin-top: 6px;
            }

            .nav-group-label .nav-icon {
                font-size: 13px;
                opacity: 0.7;
            }

            .nav-link {
                display: flex;
                align-items: center;
                padding: 9px 20px 9px 36px;
                color: #b0b0cc !important;
                text-decoration: none !important;
                font-size: 13px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s;
                border-left: 3px solid transparent;
            }

            .nav-link:hover {
                background: rgba(255,255,255,0.05);
                color: #ffffff !important;
            }

            .nav-link.active {
                background: rgba(255,255,255,0.08);
                color: #ffffff !important;
                border-left-color: #4a9eff;
            }

            .nav-icon {
                width: 18px;
                margin-right: 10px;
                text-align: center;
                font-size: 14px;
            }

            .content-area {
                margin-left: 260px;
                padding: 20px 30px;
                min-height: 100vh;
                background: #f8f9fa;
            }

            .page-title {
                font-size: 22px;
                font-weight: 600;
                color: #1a1a2e;
                margin-bottom: 16px;
                padding-bottom: 12px;
                border-bottom: 2px solid #e0e0e0;
            }

            .about-page h2 {
                font-size: 20px;
                font-weight: 600;
                color: #1a1a2e;
                margin-top: 28px;
                margin-bottom: 10px;
                padding-bottom: 6px;
                border-bottom: 1px solid #e0e0e0;
            }

            .about-page h3 {
                font-size: 17px;
                font-weight: 600;
                color: #333;
                margin-top: 18px;
                margin-bottom: 8px;
            }

            .sidebar-footer {
                position: absolute;
                bottom: 0;
                left: 0;
                right: 0;
                padding: 16px 20px;
                border-top: 1px solid rgba(255,255,255,0.1);
                font-size: 11px;
                color: #666688;
            }

            /* Dropdown menu height */
            .Select-menu-outer, .VirtualizedSelectMenu { max-height: 400px !important; }
            .dash-dropdown .Select-menu-outer { max-height: 400px !important; }

            /* Slider tooltip formatting */
            .rc-slider-tooltip { font-size: 14px !important; font-weight: bold !important; }

            .top-banner {
                background: linear-gradient(135deg, #1a1a2e 0%, #2d2d5e 100%);
                border-radius: 8px;
                padding: 14px 22px;
                margin-bottom: 16px;
                box-shadow: 0 2px 8px rgba(26,26,46,0.15);
            }
            /* Loading spinner overlay */
            #_loading-overlay {
                position: fixed;
                top: 0; left: 0; right: 0; bottom: 0;
                background: #f8f9fa;
                z-index: 9999;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            }
            #_loading-overlay .spinner {
                width: 48px; height: 48px;
                border: 4px solid #e0e0e0;
                border-top-color: #4a9eff;
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
            }
            @keyframes spin { to { transform: rotate(360deg); } }
            #_loading-overlay .brand {
                margin-top: 20px;
                font-size: 18px;
                font-weight: 600;
                color: #1a1a2e;
            }
            #_loading-overlay .sub {
                margin-top: 6px;
                font-size: 13px;
                color: #888;
            }

            .about-page img {
                max-width: 100%;
                margin: 16px 0;
                border-radius: 6px;
            }
            .about-page table {
                border-collapse: collapse;
                margin: 12px 0;
            }
            .about-page th, .about-page td {
                border: 1px solid #ccc;
                padding: 6px 12px;
                font-size: 14px;
            }
            .about-page th {
                background: #f0f0f0;
                font-weight: 600;
            }
            .about-page tr:nth-child(even) {
                background: #fafafa;
            }

            .page-info-box {
                background: #f0f6ff;
                border: 1px solid #d0e0f0;
                border-radius: 6px;
                padding: 10px 16px;
                margin-bottom: 16px;
                font-size: 13px;
                color: #444;
                line-height: 1.5;
            }

            /* Hamburger button - hidden on desktop */
            .hamburger-btn {
                display: none;
                position: fixed;
                top: 10px;
                left: 10px;
                z-index: 1100;
                background: #1a1a2e;
                color: #fff;
                border: none;
                border-radius: 6px;
                width: 40px;
                height: 40px;
                font-size: 22px;
                cursor: pointer;
                box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                line-height: 1;
            }

            /* Overlay behind sidebar on mobile */
            .sidebar-overlay {
                display: none;
                position: fixed;
                top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(0,0,0,0.5);
                z-index: 999;
            }

            /* Mobile styles */
            @media (max-width: 768px) {
                .hamburger-btn {
                    display: block;
                }

                .sidebar {
                    transform: translateX(-100%);
                    transition: transform 0.3s ease;
                }

                .sidebar.open {
                    transform: translateX(0);
                }

                .sidebar-overlay.open {
                    display: block;
                }

                .content-area {
                    margin-left: 0 !important;
                    padding: 60px 12px 20px 12px !important;
                }

                .top-banner {
                    margin-top: 0;
                }

                .top-banner > div {
                    flex-direction: column !important;
                    align-items: flex-start !important;
                    gap: 6px !important;
                }

                .page-title {
                    font-size: 18px !important;
                }

                .about-page {
                    padding: 0 !important;
                }

                .about-page img {
                    max-width: 100% !important;
                }

                /* Fix Dash dropdowns on mobile */
                .Select-menu-outer, .dash-dropdown .Select-menu-outer {
                    position: relative !important;
                    z-index: 9999 !important;
                }

                .dash-dropdown {
                    z-index: 100;
                }

                .VirtualizedSelectOption {
                    cursor: pointer !important;
                    -webkit-tap-highlight-color: rgba(0,0,0,0.1);
                }

                /* Ensure dropdown menu is not clipped */
                .Select.is-open {
                    z-index: 9999 !important;
                    position: relative;
                }

                /* Map and chart heights on mobile */
                .js-plotly-plot, .plot-container {
                    max-width: 100vw !important;
                }

                /* Constrain hover labels on mobile */
                .hoverlayer .hovertext text {
                    font-size: 10px !important;
                }
                .hoverlayer .hovertext {
                    max-width: 280px !important;
                }
                .hoverlayer .hovertext rect {
                    max-width: 280px !important;
                }
            }

            /* Global dropdown touch fix */
            .VirtualizedSelectOption {
                touch-action: manipulation;
            }
        </style>
        <script>
            function formatSliderValue(value) {
                if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
                else if (value >= 1000) return (value / 1000).toFixed(0) + 'K';
                return value.toString();
            }
            document.addEventListener('DOMContentLoaded', function() {
                const observer = new MutationObserver(function() {
                    document.querySelectorAll('.rc-slider-tooltip-inner').forEach(function(el) {
                        const num = parseInt((el.textContent || '').replace(/[^0-9]/g, ''));
                        if (!isNaN(num) && num > 1000) el.textContent = formatSliderValue(num);
                    });
                });
                observer.observe(document.body, { childList: true, subtree: true, characterData: true });
            });
        </script>
    </head>
    <body>
        <div id="_loading-overlay">
            <div class="spinner"></div>
            <div class="brand">Civil Szervezetek Adó 1% Elemzése</div>
            <div class="sub">Az adatok betöltése folyamatban...</div>
        </div>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
        <script>
            // Hide loading overlay once Dash has rendered
            (function() {
                var overlay = document.getElementById('_loading-overlay');
                if (!overlay) return;
                var check = setInterval(function() {
                    var app = document.getElementById('react-entry-point');
                    if (app && app.children.length > 0) {
                        overlay.style.transition = 'opacity 0.3s';
                        overlay.style.opacity = '0';
                        setTimeout(function() { overlay.remove(); }, 300);
                        clearInterval(check);
                    }
                }, 100);
            })();
        </script>
        <script>
            // Mobile sidebar toggle
            document.addEventListener('click', function(e) {
                var btn = e.target.closest('#hamburger-btn');
                var overlay = document.getElementById('sidebar-overlay');
                var sidebar = document.querySelector('.sidebar');
                if (!sidebar || !overlay) return;

                if (btn) {
                    sidebar.classList.toggle('open');
                    overlay.classList.toggle('open');
                    return;
                }

                // Close sidebar when clicking overlay or a nav link on mobile
                if (e.target.closest('.sidebar-overlay') || e.target.closest('.nav-link')) {
                    sidebar.classList.remove('open');
                    overlay.classList.remove('open');
                }
            });
        </script>
        <script>
            // External links open in new tab, internal links stay in same tab
            document.addEventListener('click', function(e) {
                var a = e.target.closest('a');
                if (!a) return;
                var href = a.getAttribute('href');
                if (!href) return;
                if (href.startsWith('http://') || href.startsWith('https://')) {
                    a.setAttribute('target', '_blank');
                    a.setAttribute('rel', 'noopener noreferrer');
                }
            });
        </script>
        <script>
            // Mobile: swap map hover to short versions
            (function() {
                if (window.innerWidth > 768) return;
                var MOBILE_HOVER =
                    '<b>%{customdata[0]}</b><br>%{customdata[1]}<br>' +
                    '<b>Összeg:</b> %{customdata[2]:,.0f} Ft<br>' +
                    '<b>Felajánlók:</b> %{customdata[3]:,} fő<br>' +
                    '<b>Cél:</b> %{customdata[11]}<br>' +
                    '<br>%{customdata[12]}<extra></extra>';
                var observer = new MutationObserver(function() {
                    var mapEl = document.getElementById('map-graph');
                    if (!mapEl) return;
                    var fig = mapEl._fullData;
                    if (!fig) return;
                    var needsUpdate = false;
                    for (var i = 0; i < fig.length; i++) {
                        if (fig[i].type === 'scattermapbox' && fig[i].hovertemplate &&
                            fig[i].hovertemplate.indexOf('customdata[10]') !== -1) {
                            needsUpdate = true;
                            break;
                        }
                    }
                    if (needsUpdate) {
                        var update = {};
                        var traceIndices = [];
                        for (var i = 0; i < fig.length; i++) {
                            if (fig[i].type === 'scattermapbox' && fig[i].hovertemplate) {
                                traceIndices.push(i);
                            }
                        }
                        if (traceIndices.length > 0 && window.Plotly) {
                            Plotly.restyle(mapEl, {hovertemplate: MOBILE_HOVER}, traceIndices);
                            observer.disconnect();
                        }
                    }
                });
                observer.observe(document.body, {childList: true, subtree: true});
            })();
        </script>
    </body>
</html>
'''

# Sidebar
sidebar = html.Div([
    html.Div([
        html.H3("ADÓ 1%"),
        html.P("Civil Szervezetek Elemzése")
    ], className="sidebar-header"),

    html.Div([
        # --- Vizualizációk section ---
        html.Div([
            html.Span("📊", className="nav-icon"),
            "Vizualizációk"
        ], className="nav-group-label"),

        dcc.Link([
            html.Span("◎", className="nav-icon"),
            "Térkép"
        ], href="/", className="nav-link", id="nav-map"),

        dcc.Link([
            html.Span("◉", className="nav-icon"),
            "Kategóriák"
        ], href="/kategoriak", className="nav-link", id="nav-sunburst"),

        dcc.Link([
            html.Span("◈", className="nav-icon"),
            "Éves adatok — szervezetek"
        ], href="/idosor", className="nav-link", id="nav-timeseries"),

        dcc.Link([
            html.Span("◆", className="nav-icon"),
            "Éves adatok — kategóriák"
        ], href="/idosor-kat", className="nav-link", id="nav-ts-category"),

        dcc.Link([
            html.Span("◇", className="nav-icon"),
            "Összeg vs Jövedelem"
        ], href="/scatter", className="nav-link", id="nav-scatter"),

        dcc.Link([
            html.Span("⊕", className="nav-icon"),
            "Település keresés"
        ], href="/telepules", className="nav-link", id="nav-city"),

        # --- Információk section ---
        html.Div([
            html.Span("📖", className="nav-icon"),
            "Információk"
        ], className="nav-group-label"),

        dcc.Link([
            html.Span("·", className="nav-icon"),
            "Bevezetés"
        ], href="/bevezetes", className="nav-link", id="nav-intro"),

        dcc.Link([
            html.Span("·", className="nav-icon"),
            "A projekt leírása"
        ], href="/projekt", className="nav-link", id="nav-project"),

        dcc.Link([
            html.Span("·", className="nav-icon"),
            "Érdekességek"
        ], href="/erdekessegek", className="nav-link", id="nav-funfacts"),

        dcc.Link([
            html.Span("·", className="nav-icon"),
            "Saját gondolatok"
        ], href="/gondolatok", className="nav-link", id="nav-thoughts"),

        dcc.Link([
            html.Span("·", className="nav-icon"),
            "A használt promptok"
        ], href="/promptok", className="nav-link", id="nav-prompts"),

        dcc.Link([
            html.Span("·", className="nav-icon"),
            "További tervek"
        ], href="/tervek", className="nav-link", id="nav-plans"),

    ], className="nav-section"),

    html.Div([
        html.P(f"{len(df_merged):,} szervezet"),
    ], className="sidebar-footer")
], className="sidebar")

# Page layouts
def sunburst_page():
    return wrap_page('sunburst', "Kategóriák - Hierarchikus megoszlás", [
        dcc.Loading(
            dcc.Graph(id='sunburst-graph', style={'height': '1100px'},
                      config={'displayModeBar': True, 'displaylogo': False}),
            type='circle', color='#4a9eff'
        )
    ])

def map_page():
    return wrap_page('map', "Térkép - Szervezetek elhelyezkedése", [
        html.Div([
            html.Label("Szervezet keresése:", className="fw-bold", style={'marginRight': '10px'}),
            dcc.Dropdown(
                id='map-org-search',
                options=[],
                value=None,
                placeholder="Írjon be legalább 2 karaktert...",
                searchable=True,
                clearable=True,
                style={'flex': '1'},
                maxHeight=300,
            ),
        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px',
                  'flexWrap': 'wrap', 'gap': '6px', 'position': 'relative', 'zIndex': 10}),
        dcc.Loading(
            dcc.Graph(id='map-graph', style={'height': '800px'},
                      config={'scrollZoom': True, 'displayModeBar': True, 'displaylogo': False}),
            type='circle', color='#4a9eff'
        )
    ])

def timeseries_page():
    # Build grouped dropdown options by parent category
    ts_dropdown_options = []
    parent_to_leaves = {}
    for _, row in df_ts[['parent_category', 'leaf_category']].drop_duplicates().iterrows():
        pc = row['parent_category']
        lc = row['leaf_category']
        if pc not in parent_to_leaves:
            parent_to_leaves[pc] = []
        if lc not in parent_to_leaves[pc]:
            parent_to_leaves[pc].append(lc)
    for parent_cat in sorted(parent_to_leaves.keys()):
        ts_dropdown_options.append({
            'label': f"── {parent_cat.upper()} ──",
            'value': f"__parent__{parent_cat}",
            'disabled': True
        })
        for leaf_cat in sorted(parent_to_leaves[parent_cat]):
            ts_dropdown_options.append({
                'label': f"    {leaf_cat}",
                'value': leaf_cat
            })

    return wrap_page('timeseries', "Évenkénti adatok szervezetenként", [
        dbc.Row([
            dbc.Col([
                html.Label("Kategória:", className="fw-bold"),
                dcc.Dropdown(
                    id='ts-category-dropdown',
                    options=ts_dropdown_options,
                    value=leaf_categories[0], clearable=False,
                    style={'width': '100%'},
                    maxHeight=400
                ),
                html.Div([
                    html.Label("Megjelenítés:", className="fw-bold mt-3"),
                    dbc.ButtonGroup([
                        dbc.Button("Összeg", id="ts-mode-abs", color="primary", outline=True,
                                   size="sm", className="me-1"),
                        dbc.Button("Kat. %", id="ts-mode-pct", color="primary", outline=False,
                                   size="sm", className="me-1"),
                        dbc.Button("Eloszlás", id="ts-mode-dist", color="primary", outline=True,
                                   size="sm"),
                    ], className="mt-1 d-flex"),
                ]),
                dcc.Store(id='ts-chart-mode', data='percentage'),
            ], width=3),
            dbc.Col(width=1),
            dbc.Col([
                dcc.Graph(id='ts-histogram', style={'height': '70px'},
                          config={'displayModeBar': False}),
                html.Label("Összeg szűrő:", className="fw-bold",
                           style={'fontSize': '12px'}),
                dcc.RangeSlider(
                    id='ts-slider', min=0, max=100, value=[0, 100], marks={},
                    step=100000, tooltip={"placement": "bottom", "always_visible": False},
                    allowCross=False, className="mb-2"
                )
            ], width=8)
        ], className="mb-2"),
        dbc.Row([dbc.Col([dcc.Graph(id='ts-graph', style={'height': '700px'})])]),
        dbc.Row([
            dbc.Col(width=3),
            dbc.Col([
                html.Label("Szervezet keresése:", className="fw-bold mt-2",
                           style={'fontSize': '13px'}),
                dcc.Dropdown(
                    id='ts-org-search',
                    options=[],
                    value=None,
                    placeholder="Kezdje el gépelni a szervezet nevét...",
                    searchable=True,
                    clearable=True,
                    maxHeight=300,
                ),
            ], width=9)
        ], className="mt-1")
    ])

def category_timeseries_page():
    parent_cats = sorted(df_ts['parent_category'].dropna().unique())
    cat_options = [
        {'label': '── ÖSSZES (fő kategóriák) ──', 'value': '__all_parents__'},
        {'label': '── ÖSSZES (alkategóriák) ──', 'value': '__all__'},
    ]
    cat_options += [{'label': cat, 'value': cat} for cat in parent_cats]

    return wrap_page('category_timeseries', "Évenkénti adatok kategóriánként", [
        dbc.Row([
            dbc.Col([
                html.Label("Kategória:", className="fw-bold"),
                dcc.Dropdown(
                    id='cat-ts-parent-dropdown',
                    options=cat_options,
                    value='__all_parents__',
                    clearable=False,
                    style={'width': '100%'},
                    maxHeight=400
                ),
                html.Div([
                    html.Label("Megjelenítés:", className="fw-bold mt-3"),
                    dbc.ButtonGroup([
                        dbc.Button("Összeg", id="cat-ts-mode-abs", color="primary",
                                   outline=True, size="sm", className="me-1"),
                        dbc.Button("Arány (%)", id="cat-ts-mode-pct", color="primary",
                                   outline=False, size="sm", className="me-1"),
                        dbc.Button("Eloszlás", id="cat-ts-mode-dist", color="primary",
                                   outline=True, size="sm"),
                    ], className="mt-1 d-flex"),
                ]),
                dcc.Store(id='cat-ts-chart-mode', data='percentage'),
            ], width=3),
            dbc.Col([
                dcc.Graph(id='cat-ts-graph', style={'height': '700px'})
            ], width=9)
        ])
    ])


def scatter_page():
    return wrap_page('scatter', "Összeg vs Átlagos Havi Jövedelem", [
        dcc.Loading(
            dcc.Graph(id='scatter-graph', style={'height': '800px'},
                      config={'displayModeBar': True, 'displaylogo': False}),
            type='circle', color='#4a9eff'
        )
    ])

def city_page():
    return wrap_page('city', "Település keresés", [
        # Search mode + city dropdown at top
        dbc.Row([
            dbc.Col([
                html.Label("Keresés:", className="fw-bold"),
                dbc.ButtonGroup([
                    dbc.Button("Székhely szerint", id="city-search-mode-szekhely", color="primary",
                               outline=False, size="sm", className="me-1"),
                    dbc.Button("10 km-es környezet", id="city-search-mode-radius", color="primary",
                               outline=True, size="sm"),
                ], className="ms-2"),
                dcc.Store(id='city-search-mode', data='szekhely'),
            ], xs=12, md=4, className="mb-2 mb-md-0"),
            dbc.Col([
                html.Label("Település:", className="fw-bold"),
                dcc.Dropdown(
                    id='city-dropdown',
                    options=city_dropdown_options,
                    value=None,
                    placeholder="Válasszon települést...",
                    searchable=True,
                    clearable=True,
                    maxHeight=400,
                    style={'width': '100%'}
                ),
            ], xs=12, md=5),
        ], className="mb-3"),

        # Two-column layout: map left, timeseries right (stacks on <1200px)
        dbc.Row([
            # LEFT: Map
            dbc.Col([
                dcc.Graph(id='city-map-graph', style={'height': '600px'},
                          config={'scrollZoom': True, 'displayModeBar': True,
                                  'displaylogo': False})
            ], xs=12, lg=6, className="mb-3 mb-lg-0"),

            # RIGHT: Timeseries
            dbc.Col([
                html.Div([
                    html.Label("Megjelenítés:", className="fw-bold"),
                    dbc.ButtonGroup([
                        dbc.Button("Összeg", id="city-ts-mode-abs", color="primary",
                                   outline=False, size="sm", className="me-1"),
                        dbc.Button("Arány (%)", id="city-ts-mode-pct", color="primary",
                                   outline=True, size="sm", className="me-1"),
                        dbc.Button("Eloszlás", id="city-ts-mode-dist", color="primary",
                                   outline=True, size="sm"),
                    ], className="ms-2"),
                ], className="d-flex align-items-center mb-2"),
                dcc.Store(id='city-ts-chart-mode', data='absolute'),
                dcc.Graph(id='city-ts-graph', style={'height': '560px'},
                          config={'displayModeBar': True, 'displaylogo': False})
            ], xs=12, lg=6),
        ]),

        # Summary text below
        html.Div(id='city-summary', className="mt-2",
                 style={'fontSize': '14px', 'color': '#666'}),

        # Table below (shown in székhely mode)
        html.Div(id='city-table-container', children=[
            html.H4(id='city-table-title', className="mt-3 mb-2"),
            dash_table.DataTable(
                id='city-table',
                columns=[
                    {'name': 'Szervezet neve', 'id': 'Szervezet neve'},
                    {'name': 'Összeg (Ft)', 'id': 'összeg', 'type': 'numeric',
                     'format': dash_table.FormatTemplate.money(0).symbol_suffix(' Ft')},
                    {'name': 'Szülő kategória', 'id': 'parent_category'},
                    {'name': 'Alkategória', 'id': 'leaf_category'},
                    {'name': 'Székhely', 'id': 'szekhely'},
                ],
                data=[],
                sort_action='native',
                sort_by=[{'column_id': 'összeg', 'direction': 'desc'}],
                filter_action='native',
                page_size=20,
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '8px', 'fontSize': '13px',
                            'maxWidth': '300px', 'overflow': 'hidden', 'textOverflow': 'ellipsis'},
                style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold',
                              'borderBottom': '2px solid #dee2e6'},
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}
                ],
            )
        ], style={'display': 'none'})
    ])


PAGES_DIR = os.path.join(BASE_DIR, 'pages')
_MD_STYLE = {'maxWidth': '800px', 'lineHeight': '1.7', 'fontSize': '15px'}

def _read_page_md(filename):
    """Read a markdown file from the pages/ directory."""
    md_path = os.path.join(PAGES_DIR, filename)
    if os.path.exists(md_path):
        with open(md_path, 'r', encoding='utf-8') as f:
            return f.read()
    return f"*A(z) `{filename}` fájl nem található.*"

def _info_page(title, filename):
    """Generic info page builder: reads pages/<filename> and wraps it."""
    return html.Div([
        make_banner(),
        html.H2(title, className="page-title"),
        dcc.Markdown(_read_page_md(filename), style=_MD_STYLE,
                     dangerously_allow_html=True, id='page-markdown'),
    ], className="about-page")

def intro_page():
    return _info_page("Bevezetés", "bevezetes.md")

def project_page():
    return _info_page("A projekt leírása", "projekt.md")

def thoughts_page():
    return _info_page("Saját gondolatok", "gondolatok.md")

def prompts_page():
    return _info_page("A használt promptok", "promptok.md")

def plans_page():
    return _info_page("További tervek", "tervek.md")

def funfacts_page():
    return _info_page("Érdekességek", "fun_facts.md")

# App layout
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Button("☰", id="hamburger-btn", className="hamburger-btn"),
    html.Div(id="sidebar-overlay", className="sidebar-overlay"),
    sidebar,
    html.Div(id='page-content', className="content-area")
])


# ============================================================================
# CALLBACKS
# ============================================================================

# Page routing
# Nav IDs in order for the routing callback outputs
_NAV_IDS = [
    'nav-sunburst', 'nav-map', 'nav-timeseries', 'nav-ts-category',
    'nav-scatter', 'nav-city', 'nav-intro', 'nav-project',
    'nav-thoughts', 'nav-prompts', 'nav-plans', 'nav-funfacts',
]

@app.callback(
    [Output('page-content', 'children')] + [Output(nid, 'className') for nid in _NAV_IDS],
    [Input('url', 'pathname')]
)
def display_page(pathname):
    base = "nav-link"
    n = len(_NAV_IDS)

    def _result(page, active_id):
        classes = [base] * n
        if active_id in _NAV_IDS:
            classes[_NAV_IDS.index(active_id)] = "nav-link active"
        return (page, *classes)

    routes = {
        '/kategoriak': (sunburst_page, 'nav-sunburst'),
        '/idosor': (timeseries_page, 'nav-timeseries'),
        '/idosor-kat': (category_timeseries_page, 'nav-ts-category'),
        '/scatter': (scatter_page, 'nav-scatter'),
        '/telepules': (city_page, 'nav-city'),
        '/bevezetes': (intro_page, 'nav-intro'),
        '/projekt': (project_page, 'nav-project'),
        '/gondolatok': (thoughts_page, 'nav-thoughts'),
        '/promptok': (prompts_page, 'nav-prompts'),
        '/tervek': (plans_page, 'nav-plans'),
        '/erdekessegek': (funfacts_page, 'nav-funfacts'),
    }

    if pathname in routes:
        page_fn, nav_id = routes[pathname]
        return _result(page_fn(), nav_id)
    else:
        return _result(map_page(), 'nav-map')


# Lazy-load: populate sunburst figure when page appears
@app.callback(
    Output('sunburst-graph', 'figure'),
    [Input('sunburst-graph', 'id')]
)
def load_sunburst(_):
    return sunburst_fig


# Lazy-load: populate scatter figure when page appears
@app.callback(
    Output('scatter-graph', 'figure'),
    [Input('scatter-graph', 'id')]
)
def load_scatter(_):
    return scatter_fig


# Map: filter search options (min 2 chars, top 5)
@app.callback(
    Output('map-org-search', 'options'),
    [Input('map-org-search', 'search_value')]
)
def map_filter_search(search_value):
    if not search_value or len(search_value) < 2:
        return []
    search_lower = search_value.lower()
    matches = [opt for opt in map_org_options if search_lower in opt['label'].lower()]
    return matches[:5]


# Map: search and highlight org
@app.callback(
    Output('map-graph', 'figure'),
    [Input('map-org-search', 'value')]
)
def map_search_org(selected_org_idx):
    if selected_org_idx is None:
        return map_fig

    info = map_org_lookup.get(selected_org_idx)
    if info is None:
        return map_fig

    fig = copy.deepcopy(map_fig)

    # Add a highlight marker for the selected org
    fig.add_trace(go.Scattermapbox(
        lat=[info['lat']], lon=[info['lon']], mode='markers+text',
        marker=dict(size=22, color='red', opacity=0.9,
                    symbol='circle'),
        text=[info['name']],
        textposition='top center',
        textfont=dict(size=13, color='red', family='Arial Black'),
        name='Keresett szervezet',
        hoverinfo='text',
        showlegend=False
    ))

    # Zoom to the selected org
    fig.update_layout(
        mapbox=dict(center=dict(lat=info['lat'], lon=info['lon']), zoom=12)
    )

    return fig


# Time series: update slider
@app.callback(
    [Output('ts-slider', 'min'), Output('ts-slider', 'max'),
     Output('ts-slider', 'value'), Output('ts-slider', 'marks'),
     Output('ts-slider', 'step')],
    [Input('ts-category-dropdown', 'value')]
)
def ts_update_slider(selected_category):
    df_cat = df_ts[df_ts['leaf_category'] == selected_category]
    if len(df_cat) == 0:
        return 0, 100, [0, 100], {}, 1

    min_val = int(df_cat['összeg'].min())
    max_val = int(df_cat['összeg'].max())
    step = 100000

    min_r = (min_val // step) * step
    max_r = ((max_val // step) + 1) * step

    value_range = max_r - min_r

    # Target ~4-5 marks maximum for readability
    target_marks = 4
    raw_interval = value_range / target_marks
    # Round up to a nice interval
    nice_intervals = [100000, 200000, 500000, 1000000, 2000000, 5000000, 10000000, 20000000, 50000000]
    mark_interval = nice_intervals[0]
    for ni in nice_intervals:
        if ni >= raw_interval:
            mark_interval = ni
            break

    def fmt_mark(v):
        if v >= 1e9:
            return f'{v/1e9:.1f}B'
        if v >= 1e6:
            return f'{v/1e6:.1f}M'
        if v >= 1e3:
            return f'{v/1e3:.0f}K'
        return str(v)

    marks = {}
    current = (min_r // mark_interval) * mark_interval
    if current < min_r:
        current += mark_interval
    while current <= max_r:
        marks[current] = fmt_mark(current)
        current += mark_interval

    for v in [min_r, max_r]:
        if v not in marks:
            marks[v] = fmt_mark(v)

    return min_r, max_r, [min_r, max_r], marks, step


# Time series: update histogram
@app.callback(
    Output('ts-histogram', 'figure'),
    [Input('ts-category-dropdown', 'value'), Input('ts-slider', 'value')]
)
def ts_update_histogram(selected_category, amount_range):
    df_cat = df_ts[df_ts['leaf_category'] == selected_category]
    if len(df_cat) == 0:
        return go.Figure()

    fig = go.Figure()
    fig.add_trace(go.Histogram(x=df_cat['összeg'], nbinsx=30,
        marker=dict(color='lightblue', line=dict(color='white', width=1)), showlegend=False))

    df_filtered = df_cat[(df_cat['összeg'] >= amount_range[0]) & (df_cat['összeg'] <= amount_range[1])]
    fig.add_trace(go.Histogram(x=df_filtered['összeg'], nbinsx=30,
        marker=dict(color='steelblue', line=dict(color='white', width=1)), showlegend=False))

    fig.update_layout(
        xaxis=dict(title='', showticklabels=False, showgrid=False),
        yaxis=dict(title='', showgrid=False, fixedrange=True, showticklabels=False),
        plot_bgcolor='white', margin=dict(l=20, r=20, t=10, b=10),
        height=120, barmode='overlay', hovermode='x'
    )
    fig.add_annotation(text=f'{len(df_filtered)} / {len(df_cat)} szervezet',
        x=0.95, y=0.95, xref='paper', yref='paper', showarrow=False,
        bgcolor='rgba(255,255,255,0.8)', bordercolor='lightgray', borderwidth=1)
    return fig


# Time series: mode toggle
@app.callback(
    [Output('ts-chart-mode', 'data'),
     Output('ts-mode-abs', 'outline'),
     Output('ts-mode-pct', 'outline'),
     Output('ts-mode-dist', 'outline')],
    [Input('ts-mode-abs', 'n_clicks'), Input('ts-mode-pct', 'n_clicks'),
     Input('ts-mode-dist', 'n_clicks')],
    prevent_initial_call=True
)
def ts_toggle_mode(abs_clicks, pct_clicks, dist_clicks):
    from dash import ctx
    if ctx.triggered_id == 'ts-mode-pct':
        return 'percentage', True, False, True
    elif ctx.triggered_id == 'ts-mode-dist':
        return 'distribution', True, True, False
    return 'absolute', False, True, True


# Time series: update graph
@app.callback(
    Output('ts-graph', 'figure'),
    [Input('ts-category-dropdown', 'value'), Input('ts-slider', 'value'),
     Input('ts-chart-mode', 'data'), Input('ts-org-search', 'value')]
)
def ts_update_graph(selected_category, amount_range, chart_mode, selected_org):
    if chart_mode is None:
        chart_mode = 'distribution'

    df_all_category = df_ts[df_ts['leaf_category'] == selected_category].copy()

    # Category totals from ALL orgs (before filtering)
    category_totals_by_year = {}
    for year in all_years:
        year_total = sum(row['historical_dict'].get(year, 0) for _, row in df_all_category.iterrows())
        category_totals_by_year[year] = year_total if year_total > 0 else 1

    # Filter by slider
    df_cat = df_all_category[
        (df_all_category['összeg'] >= amount_range[0]) &
        (df_all_category['összeg'] <= amount_range[1])
    ].sort_values('összeg', ascending=False)

    cat_idx = leaf_categories.index(selected_category) if selected_category in leaf_categories else 0
    is_pct = chart_mode == 'percentage'
    is_dist = chart_mode == 'distribution'

    fig = go.Figure()

    if is_dist:
        # Stacked 100% bar chart showing proportional distribution per year
        # Collect data per org per year
        org_year_data = []
        for _, row in df_cat.iterrows():
            org_name = row['Szervezet neve']
            hist_dict = row['historical_dict']
            for year in all_years:
                amount = hist_dict.get(year, 0)
                if amount > 0:
                    org_year_data.append({
                        'org': org_name, 'year': year, 'amount': amount
                    })

        if org_year_data:
            df_dist = pd.DataFrame(org_year_data)
            # Get years that have data
            active_years = sorted(df_dist['year'].unique())
            # Year totals for percentage
            year_totals = df_dist.groupby('year')['amount'].sum()

            # Top orgs by total + "Egyéb"
            org_totals = df_dist.groupby('org')['amount'].sum().sort_values(ascending=False)
            MAX_ORGS = 15
            top_orgs = org_totals.head(MAX_ORGS).index.tolist()
            has_other = len(org_totals) > MAX_ORGS

            # Distinct colors for each org
            dist_colors = [
                '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
                '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#fabed4',
                '#469990', '#dcbeff', '#9A6324', '#800000', '#aaffc3',
                '#808000'
            ]

            for i, org_name in enumerate(top_orgs):
                df_org = df_dist[df_dist['org'] == org_name]
                pcts = []
                for year in active_years:
                    row_data = df_org[df_org['year'] == year]
                    if len(row_data) > 0:
                        pcts.append(row_data['amount'].values[0] / year_totals[year] * 100)
                    else:
                        pcts.append(0)

                short_name = org_name[:40]
                fig.add_trace(go.Bar(
                    x=[str(y) for y in active_years], y=pcts,
                    name=short_name,
                    marker_color=dist_colors[i % len(dist_colors)],
                    text=[f"{p:.1f}%" if p >= 3 else "" for p in pcts],
                    textposition='inside', textfont=dict(size=10, color='white'),
                    hovertemplate=f"<b>{short_name}</b><br>" +
                                  "Év: %{x}<br>Arány: %{y:.1f}%<extra></extra>"
                ))

            if has_other:
                other_orgs = org_totals.iloc[MAX_ORGS:].index.tolist()
                other_pcts = []
                for year in active_years:
                    df_year_other = df_dist[(df_dist['year'] == year) &
                                            (df_dist['org'].isin(other_orgs))]
                    total_other = df_year_other['amount'].sum()
                    other_pcts.append(total_other / year_totals[year] * 100)

                fig.add_trace(go.Bar(
                    x=[str(y) for y in active_years], y=other_pcts,
                    name=f"Egyéb ({len(other_orgs)} szervezet)",
                    marker_color='#cccccc',
                    text=[f"{p:.1f}%" if p >= 3 else "" for p in other_pcts],
                    textposition='inside', textfont=dict(size=10, color='#333'),
                    hovertemplate=f"<b>Egyéb ({len(other_orgs)} szervezet)</b><br>" +
                                  "Év: %{x}<br>Arány: %{y:.1f}%<extra></extra>"
                ))

        fig.update_layout(
            barmode='stack', barnorm='percent',
            xaxis=dict(title='Év', type='category'),
            yaxis=dict(title='Eloszlás (%)', range=[0, 100]),
            plot_bgcolor='white', hovermode='x unified', showlegend=True,
            legend=dict(title=dict(text='Szervezetek', font=dict(size=12)), font=dict(size=9),
                        bgcolor='rgba(255,255,255,0.8)', bordercolor='lightgray', borderwidth=1,
                        traceorder='normal'),
            margin=dict(l=80, r=20, t=20, b=80)
        )

        # Highlight selected org in distribution mode
        if selected_org:
            for trace in fig.data:
                if hasattr(trace, 'name') and trace.name:
                    if selected_org.startswith(trace.name) or trace.name in selected_org:
                        trace.opacity = 1.0
                    else:
                        trace.opacity = 0.15

        return fig

    # --- Line chart modes (absolute / percentage) ---
    for org_idx, (_, row) in enumerate(df_cat.iterrows()):
        color = COLORS_20[org_idx % len(COLORS_20)]
        org_name = row['Szervezet neve']
        hist_dict = row['historical_dict']
        hist_data = row['historical_data']

        years = []
        amounts = []
        pct_values = []
        for year in all_years:
            amount = hist_dict.get(year, 0)
            if amount > 0:
                years.append(year)
                amounts.append(amount)
                pct_values.append(amount / category_totals_by_year.get(year, 1) * 100)

        if not years:
            continue

        # Build hover table
        table_rows = ['<br><br><b>Éves adatok:</b>']
        table_rows.append("<br><span style='font-family: monospace;'>")
        table_rows.append("───────────────────────────────────────────────────────────<br>")
        table_rows.append(f"{'Év':<4}  {'Összeg':>10}  {'Fő':>6}  {'Havi br.':>10}  {'Kat %':>7}<br>")
        table_rows.append("───────────────────────────────────────────────────────────<br>")

        for year in sorted(hist_dict.keys()):
            amount = hist_dict[year]
            if amount > 0:
                donors = get_donor_count(hist_data, year)
                if donors > 0:
                    avg_per_donor = amount / donors
                    monthly_gross = int(avg_per_donor * 100 * (100/15) / 12)
                else:
                    monthly_gross = 0

                category_pct = (amount / category_totals_by_year.get(year, 1) * 100)
                amount_str = f"{amount/1e6:>9.1f}M" if amount >= 1e6 else f"{amount/1e3:>9.0f}K"
                monthly_str = f"{monthly_gross/1e6:>9.1f}M" if monthly_gross >= 1e6 else (
                    f"{monthly_gross/1e3:>9.0f}K" if monthly_gross >= 1e3 else f"{monthly_gross:>9}")

                table_rows.append(f"{year:<4}  {amount_str:>10}  {donors:>6}  {monthly_str:>10}  {category_pct:>6.1f}%<br>")

        table_rows.append("</span>")
        parent_cat = row.get('parent_category', '')
        table_rows.append(f"<br><b>Kategória:</b> {parent_cat} → {selected_category}")
        hover_text = f"<b>{org_name}</b><br>{row.get('szekhely', '')}{''.join(table_rows)}"

        y_data = pct_values if is_pct else amounts

        fig.add_trace(go.Scatter(
            x=years, y=y_data, mode='lines+markers',
            name=org_name[:50], line=dict(color=color, width=2),
            marker=dict(size=6, color=color),
            hovertemplate=hover_text + '<extra></extra>',
            hoverlabel=dict(bgcolor='white', font_size=11)
        ))

    y_title = 'Kategórián belüli arány (%)' if is_pct else 'Felajánlott összeg (Ft)'

    fig.update_layout(
        xaxis=dict(title='Év', gridcolor='lightgray', showline=True, linewidth=1,
                   linecolor='black', mirror=True, dtick=1),
        yaxis=dict(title=y_title, gridcolor='lightgray', showline=True,
                   linewidth=1, linecolor='black', mirror=True),
        plot_bgcolor='white', hovermode='closest', showlegend=True,
        legend=dict(title=dict(text='Szervezetek', font=dict(size=12)), font=dict(size=9),
                    bgcolor='rgba(255,255,255,0.8)', bordercolor='lightgray', borderwidth=1),
        margin=dict(l=80, r=20, t=20, b=80)
    )

    # Highlight selected org in line chart mode
    if selected_org:
        for trace in fig.data:
            if hasattr(trace, 'name') and trace.name:
                if selected_org.startswith(trace.name) or trace.name in selected_org:
                    trace.line = dict(color=trace.line.color if trace.line else 'red', width=4)
                    trace.marker = dict(size=10, color=trace.marker.color if trace.marker else 'red')
                    trace.opacity = 1.0
                else:
                    trace.opacity = 0.1

    return fig


# Time series: update org search options when category changes
@app.callback(
    [Output('ts-org-search', 'options'),
     Output('ts-org-search', 'value')],
    [Input('ts-category-dropdown', 'value')]
)
def ts_update_org_search(selected_category):
    df_cat = df_ts[df_ts['leaf_category'] == selected_category].sort_values('összeg', ascending=False)
    options = [
        {'label': row['Szervezet neve'], 'value': row['Szervezet neve']}
        for _, row in df_cat.iterrows()
    ]
    return options, None


# Category time series: mode toggle
@app.callback(
    [Output('cat-ts-chart-mode', 'data'),
     Output('cat-ts-mode-abs', 'outline'),
     Output('cat-ts-mode-pct', 'outline'),
     Output('cat-ts-mode-dist', 'outline')],
    [Input('cat-ts-mode-abs', 'n_clicks'), Input('cat-ts-mode-pct', 'n_clicks'),
     Input('cat-ts-mode-dist', 'n_clicks')],
    prevent_initial_call=True
)
def cat_ts_toggle_mode(abs_clicks, pct_clicks, dist_clicks):
    from dash import ctx
    if ctx.triggered_id == 'cat-ts-mode-pct':
        return 'percentage', True, False, True
    elif ctx.triggered_id == 'cat-ts-mode-dist':
        return 'distribution', True, True, False
    return 'absolute', False, True, True


# Category time series: update graph
@app.callback(
    Output('cat-ts-graph', 'figure'),
    [Input('cat-ts-parent-dropdown', 'value'),
     Input('cat-ts-chart-mode', 'data')]
)
def cat_ts_update_graph(selected_parent, chart_mode):
    if chart_mode is None:
        chart_mode = 'distribution'
    if not selected_parent:
        return go.Figure()

    # Get all orgs — either for one parent or all
    is_all = selected_parent == '__all__'
    is_all_parents = selected_parent == '__all_parents__'

    # Determine grouping level and categories
    if is_all_parents:
        group_col = 'parent_category'
        key_prefix = 'parent'
    else:
        group_col = 'leaf_category'
        key_prefix = 'leaf'

    if is_all or is_all_parents:
        group_cats = sorted(df_ts[group_col].dropna().unique())
    else:
        group_cats = sorted(df_ts[df_ts['parent_category'] == selected_parent][group_col].dropna().unique())

    # Use pre-computed aggregations instead of iterating over rows
    leaf_year_data = {}  # {cat_name: {year: total_amount}}
    for cat in group_cats:
        year_totals = {}
        for year in all_years:
            total = cat_year_totals.get((key_prefix, cat, year), 0)
            if total > 0:
                year_totals[year] = total
        if year_totals:
            leaf_year_data[cat] = year_totals

    if not leaf_year_data:
        return go.Figure()

    # Lookup: cat → parent_cat (for hover labels)
    leaf_to_parent = {}
    if not is_all_parents:
        for cat in group_cats:
            if cat in leaf_to_parent_map:
                leaf_to_parent[cat] = leaf_to_parent_map[cat]

    # Parent totals per year (for percentage calc)
    parent_totals_by_year = {}
    for year in all_years:
        total = sum(yd.get(year, 0) for yd in leaf_year_data.values())
        parent_totals_by_year[year] = total if total > 0 else 1

    is_pct = chart_mode == 'percentage'
    is_dist = chart_mode == 'distribution'

    fig = go.Figure()

    # Color palette for leaf categories
    dist_colors = [
        '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
        '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#fabed4',
        '#469990', '#dcbeff', '#9A6324', '#800000', '#aaffc3',
        '#808000', '#e6beff', '#aa6e28', '#fffac8', '#800080'
    ]

    if is_dist:
        # Stacked 100% bar chart by leaf category
        active_years = sorted(set(y for yd in leaf_year_data.values() for y in yd.keys()))

        for i, leaf_cat in enumerate(sorted(leaf_year_data.keys())):
            year_amounts = leaf_year_data[leaf_cat]
            pcts = []
            for year in active_years:
                amount = year_amounts.get(year, 0)
                pcts.append(amount / parent_totals_by_year.get(year, 1) * 100)

            fig.add_trace(go.Bar(
                x=[str(y) for y in active_years], y=pcts,
                name=leaf_cat,
                marker_color=dist_colors[i % len(dist_colors)],
                text=[f"{p:.1f}%" if p >= 3 else "" for p in pcts],
                textposition='inside', textfont=dict(size=10, color='white'),
                hovertemplate=(
                    f"<b>{leaf_cat}</b><br>"
                    "Év: %{x}<br>"
                    "Arány: %{y:.1f}%<br>"
                    + (f"<b>Kategória:</b> {leaf_cat}" if is_all_parents else
                       f"<b>Kategória:</b> {leaf_to_parent.get(leaf_cat, '')} → {leaf_cat}")
                    + "<extra></extra>"
                )
            ))

        fig.update_layout(
            barmode='stack', barnorm='percent',
            xaxis=dict(title='Év', type='category'),
            yaxis=dict(title='Eloszlás (%)', range=[0, 100]),
            plot_bgcolor='white', hovermode='x unified', showlegend=True,
            legend=dict(title=dict(text='Kategóriák' if is_all_parents else 'Alkategóriák', font=dict(size=12)), font=dict(size=9),
                        bgcolor='rgba(255,255,255,0.8)', bordercolor='lightgray', borderwidth=1,
                        traceorder='normal'),
            margin=dict(l=80, r=20, t=20, b=80)
        )

    else:
        # Line chart modes (absolute / percentage)
        for i, leaf_cat in enumerate(sorted(leaf_year_data.keys())):
            year_amounts = leaf_year_data[leaf_cat]
            years = sorted(year_amounts.keys())
            amounts = [year_amounts[y] for y in years]
            pct_values = [year_amounts[y] / parent_totals_by_year.get(y, 1) * 100 for y in years]

            y_data = pct_values if is_pct else amounts
            color = COLORS_20[i % len(COLORS_20)]

            # Build hover with yearly data
            hover_lines = [f"<b>{leaf_cat}</b><br><br>"]
            hover_lines.append("<span style='font-family: monospace;'>")
            hover_lines.append("─────────────────────────────<br>")
            hover_lines.append(f"{'Év':<4}  {'Összeg':>10}  {'Arány':>7}<br>")
            hover_lines.append("─────────────────────────────<br>")
            for y in years:
                amt = year_amounts[y]
                pct = amt / parent_totals_by_year.get(y, 1) * 100
                amt_str = f"{amt/1e6:>9.1f}M" if amt >= 1e6 else f"{amt/1e3:>9.0f}K"
                hover_lines.append(f"{y:<4}  {amt_str:>10}  {pct:>6.1f}%<br>")
            hover_lines.append("</span>")
            if is_all_parents:
                hover_lines.append(f"<br><b>Kategória:</b> {leaf_cat}")
            else:
                hover_lines.append(f"<br><b>Kategória:</b> {leaf_to_parent.get(leaf_cat, '')} → {leaf_cat}")
            hover_text = ''.join(hover_lines)

            fig.add_trace(go.Scatter(
                x=years, y=y_data, mode='lines+markers',
                name=leaf_cat, line=dict(color=color, width=2),
                marker=dict(size=6, color=color),
                hovertemplate=hover_text + '<extra></extra>',
                hoverlabel=dict(bgcolor='white', font_size=11)
            ))

        y_title = 'Szülő kategórián belüli arány (%)' if is_pct else 'Felajánlott összeg (Ft)'

        fig.update_layout(
            xaxis=dict(title='Év', gridcolor='lightgray', showline=True, linewidth=1,
                       linecolor='black', mirror=True, dtick=1),
            yaxis=dict(title=y_title, gridcolor='lightgray', showline=True,
                       linewidth=1, linecolor='black', mirror=True),
            plot_bgcolor='white', hovermode='closest', showlegend=True,
            legend=dict(title=dict(text='Kategóriák' if is_all_parents else 'Alkategóriák', font=dict(size=12)), font=dict(size=9),
                        bgcolor='rgba(255,255,255,0.8)', bordercolor='lightgray', borderwidth=1),
            margin=dict(l=80, r=20, t=20, b=80)
        )

    return fig


# ============================================================================
# CITY PAGE CALLBACKS
# ============================================================================

# City: search mode toggle (székhely vs 10km radius)
@app.callback(
    [Output('city-search-mode', 'data'),
     Output('city-search-mode-szekhely', 'outline'),
     Output('city-search-mode-radius', 'outline')],
    [Input('city-search-mode-szekhely', 'n_clicks'),
     Input('city-search-mode-radius', 'n_clicks')],
    prevent_initial_call=True
)
def city_toggle_search_mode(szekhely_clicks, radius_clicks):
    from dash import ctx
    if ctx.triggered_id == 'city-search-mode-radius':
        return 'radius', True, False
    return 'szekhely', False, True


# City: mode toggle
@app.callback(
    [Output('city-ts-chart-mode', 'data'),
     Output('city-ts-mode-abs', 'outline'),
     Output('city-ts-mode-pct', 'outline'),
     Output('city-ts-mode-dist', 'outline')],
    [Input('city-ts-mode-abs', 'n_clicks'),
     Input('city-ts-mode-pct', 'n_clicks'),
     Input('city-ts-mode-dist', 'n_clicks')],
    prevent_initial_call=True
)
def city_ts_toggle_mode(abs_clicks, pct_clicks, dist_clicks):
    from dash import ctx
    if ctx.triggered_id == 'city-ts-mode-pct':
        return 'percentage', True, False, True
    elif ctx.triggered_id == 'city-ts-mode-dist':
        return 'distribution', True, True, False
    return 'absolute', False, True, True


# City: map update
@app.callback(
    Output('city-map-graph', 'figure'),
    [Input('city-dropdown', 'value'),
     Input('city-search-mode', 'data')]
)
def city_update_map(selected_city, search_mode):
    import math

    if search_mode is None:
        search_mode = 'szekhely'

    fig = go.Figure()

    # Determine data source based on search mode
    if search_mode == 'szekhely':
        data_source = city_szekhely_data
    else:
        data_source = city_radius_data

    if not selected_city or selected_city not in data_source:
        # Empty map centered on Hungary
        fig.update_layout(
            mapbox=dict(style="carto-positron",
                        center=dict(lat=47.2, lon=19.5), zoom=6.5),
            height=600, margin=dict(l=0, r=0, t=10, b=0), showlegend=False
        )
        return fig

    city_info = data_source[selected_city]
    city_lat = city_info.get('lat')
    city_lon = city_info.get('lon')
    if city_lat is None or city_lon is None:
        fig.update_layout(
            mapbox=dict(style="carto-positron",
                        center=dict(lat=47.2, lon=19.5), zoom=6.5),
            height=600, margin=dict(l=0, r=0, t=10, b=0), showlegend=False
        )
        return fig
    adoszamok = set(str(a) for a in city_info['adoszamok'])

    # Filter orgs within this city's radius
    df_city_map = df_merged[df_merged['Adószám'].isin(adoszamok)].copy()
    df_city_map = df_city_map.dropna(subset=['lat', 'lon'])

    # Draw 10km circle overlay (only in radius mode)
    if search_mode == 'radius':
        circle_lats = []
        circle_lons = []
        n_points = 72
        radius_km = 10
        for i in range(n_points + 1):
            angle = math.radians(i * 360 / n_points)
            dlat = radius_km / 111.32 * math.cos(angle)
            dlon = radius_km / (111.32 * math.cos(math.radians(city_lat))) * math.sin(angle)
            circle_lats.append(city_lat + dlat)
            circle_lons.append(city_lon + dlon)

        fig.add_trace(go.Scattermapbox(
            lat=circle_lats, lon=circle_lons, mode='lines',
            line=dict(width=2, color='rgba(0, 100, 255, 0.6)'),
            fill='toself', fillcolor='rgba(0, 100, 255, 0.08)',
            name='10 km körzet', hoverinfo='skip', showlegend=False
        ))

    # Build color map using global parent categories for consistent colors
    all_parents = sorted(df_merged['parent_category'].dropna().unique())
    color_map = {cat: PARENT_COLORS[i % len(PARENT_COLORS)]
                 for i, cat in enumerate(all_parents)}

    # Add org markers by parent category
    for parent_cat in sorted(df_city_map['parent_category'].dropna().unique()):
        df_sub = df_city_map[df_city_map['parent_category'] == parent_cat]
        sizes = df_sub['összeg'].apply(lambda x: min(max((x ** 0.5) / 200, 5), 25))

        customdata = list(zip(
            df_sub['Szervezet neve'], df_sub['szekhely'],
            df_sub['összeg'], df_sub['db'],
            df_sub['átlag_per_donor'], df_sub['monthly_gross'],
            df_sub['parent_category'], df_sub['leaf_category']
        ))

        fig.add_trace(go.Scattermapbox(
            lat=df_sub['lat'], lon=df_sub['lon'], mode='markers',
            marker=dict(size=sizes, color=color_map.get(parent_cat, '#999'), opacity=0.8),
            name=parent_cat,
            customdata=customdata,
            hovertemplate=(
                '<b>%{customdata[0]}</b><br>%{customdata[1]}<br>'
                '<b>Kategória:</b> %{customdata[6]} → %{customdata[7]}<br><br>'
                '<b>Összeg:</b> %{customdata[2]:,.0f} Ft<br>'
                '<b>Felajánlók:</b> %{customdata[3]:,} fő<br>'
                '<b>Átlag/fő:</b> %{customdata[4]:,.0f} Ft<br>'
                '<b>Havi bruttó:</b> %{customdata[5]:,.0f} Ft<br>'
                '<extra></extra>'
            ),
            showlegend=True
        ))

    # City center marker
    fig.add_trace(go.Scattermapbox(
        lat=[city_lat], lon=[city_lon], mode='markers',
        marker=dict(size=12, color='red', symbol='circle'),
        name=selected_city, hoverinfo='text',
        text=[f"{selected_city} középpontja"], showlegend=False
    ))

    fig.update_layout(
        mapbox=dict(style="carto-positron",
                    center=dict(lat=city_lat, lon=city_lon), zoom=11),
        height=600, margin=dict(l=0, r=0, t=10, b=0),
        showlegend=False,
    )

    return fig


# City: timeseries update
@app.callback(
    [Output('city-ts-graph', 'figure'),
     Output('city-summary', 'children')],
    [Input('city-dropdown', 'value'),
     Input('city-ts-chart-mode', 'data'),
     Input('city-search-mode', 'data')]
)
def city_ts_update_graph(selected_city, chart_mode, search_mode):
    fig = go.Figure()

    if search_mode is None:
        search_mode = 'szekhely'
    data_source = city_szekhely_data if search_mode == 'szekhely' else city_radius_data

    if not selected_city or selected_city not in data_source:
        fig.update_layout(
            xaxis=dict(title='Év'), yaxis=dict(title=''),
            plot_bgcolor='white', margin=dict(l=80, r=20, t=20, b=80),
            annotations=[dict(text="Válasszon települést a listából", showarrow=False,
                              xref="paper", yref="paper", x=0.5, y=0.5,
                              font=dict(size=16, color='#999'))]
        )
        return fig, ""

    if chart_mode is None:
        chart_mode = 'absolute'

    city_info = data_source[selected_city]
    adoszamok = set(str(a) for a in city_info['adoszamok'])

    # Get orgs that have historical data
    df_city_ts = df_ts[df_ts['Adószám'].isin(adoszamok)].copy()
    df_city_ts = df_city_ts.sort_values('összeg', ascending=False)

    total_amount = df_city_ts['összeg'].sum()
    total_orgs = len(df_city_ts)
    mode_label = "székhely szerint" if search_mode == 'szekhely' else "a 10 km-es körzetben"
    summary = (f"{selected_city}: {total_orgs} szervezet {mode_label}, "
               f"összes felajánlás: {total_amount:,.0f} Ft")

    if len(df_city_ts) == 0:
        fig.update_layout(
            plot_bgcolor='white', margin=dict(l=80, r=20, t=20, b=80),
            annotations=[dict(text="Nincs szervezet történeti adattal ebben a körzetben",
                              showarrow=False, xref="paper", yref="paper", x=0.5, y=0.5,
                              font=dict(size=14, color='#999'))]
        )
        return fig, summary

    is_pct = chart_mode == 'percentage'
    is_dist = chart_mode == 'distribution'

    # City totals by year (for percentage mode)
    city_totals_by_year = {}
    for year in all_years:
        year_total = sum(row['historical_dict'].get(year, 0) for _, row in df_city_ts.iterrows())
        city_totals_by_year[year] = year_total if year_total > 0 else 1

    if is_dist:
        # Stacked 100% bar chart
        org_year_data = []
        for _, row in df_city_ts.iterrows():
            org_name = row['Szervezet neve']
            hist_dict = row['historical_dict']
            for year in all_years:
                amount = hist_dict.get(year, 0)
                if amount > 0:
                    org_year_data.append({'org': org_name, 'year': year, 'amount': amount})

        if org_year_data:
            df_dist = pd.DataFrame(org_year_data)
            active_years = sorted(df_dist['year'].unique())
            year_totals = df_dist.groupby('year')['amount'].sum()

            org_totals = df_dist.groupby('org')['amount'].sum().sort_values(ascending=False)
            MAX_ORGS = 15
            top_orgs = org_totals.head(MAX_ORGS).index.tolist()
            has_other = len(org_totals) > MAX_ORGS

            dist_colors = [
                '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
                '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#fabed4',
                '#469990', '#dcbeff', '#9A6324', '#800000', '#aaffc3',
                '#808000'
            ]

            for i, org_name in enumerate(top_orgs):
                df_org = df_dist[df_dist['org'] == org_name]
                pcts = []
                for year in active_years:
                    row_data = df_org[df_org['year'] == year]
                    if len(row_data) > 0:
                        pcts.append(row_data['amount'].values[0] / year_totals[year] * 100)
                    else:
                        pcts.append(0)

                legend_name = (org_name[:20] + '…') if len(org_name) > 20 else org_name
                fig.add_trace(go.Bar(
                    x=[str(y) for y in active_years], y=pcts,
                    name=legend_name,
                    marker_color=dist_colors[i % len(dist_colors)],
                    text=[f"{p:.1f}%" if p >= 3 else "" for p in pcts],
                    textposition='inside', textfont=dict(size=10, color='white'),
                    hovertemplate=f"<b>{org_name}</b><br>" +
                                  "Év: %{x}<br>Arány: %{y:.1f}%<extra></extra>"
                ))

            if has_other:
                other_orgs = org_totals.iloc[MAX_ORGS:].index.tolist()
                other_pcts = []
                for year in active_years:
                    df_year_other = df_dist[(df_dist['year'] == year) &
                                            (df_dist['org'].isin(other_orgs))]
                    total_other = df_year_other['amount'].sum()
                    other_pcts.append(total_other / year_totals[year] * 100 if year_totals[year] > 0 else 0)

                fig.add_trace(go.Bar(
                    x=[str(y) for y in active_years], y=other_pcts,
                    name=f"Egyéb ({len(other_orgs)})",
                    marker_color='#cccccc',
                    text=[f"{p:.1f}%" if p >= 3 else "" for p in other_pcts],
                    textposition='inside', textfont=dict(size=10, color='#333'),
                    hovertemplate=f"<b>Egyéb ({len(other_orgs)} szervezet)</b><br>" +
                                  "Év: %{x}<br>Arány: %{y:.1f}%<extra></extra>"
                ))

        fig.update_layout(
            barmode='stack', barnorm='percent',
            xaxis=dict(title='Év', type='category'),
            yaxis=dict(title='Eloszlás (%)', range=[0, 100]),
            plot_bgcolor='white', hovermode='x unified', showlegend=True,
            legend=dict(title=dict(text='Szervezetek', font=dict(size=11)),
                        font=dict(size=9), itemwidth=30,
                        bgcolor='rgba(255,255,255,0.8)', bordercolor='lightgray', borderwidth=1),
            margin=dict(l=60, r=10, t=20, b=60)
        )
        return fig, summary

    # --- Line chart modes (absolute / percentage) ---
    for _, row in df_city_ts.iterrows():
        org_name = row['Szervezet neve']
        hist_dict = row['historical_dict']
        hist_data = row['historical_data']

        years = []
        amounts = []
        pct_values = []
        for year in all_years:
            amount = hist_dict.get(year, 0)
            if amount > 0:
                years.append(year)
                amounts.append(amount)
                pct_values.append(amount / city_totals_by_year.get(year, 1) * 100)

        if not years:
            continue

        # Build hover table
        table_rows = ['<br><br><b>Éves adatok:</b>']
        table_rows.append("<br><span style='font-family: monospace;'>")
        table_rows.append("───────────────────────────────────────────────────────────<br>")
        table_rows.append(f"{'Év':<4}  {'Összeg':>10}  {'Fő':>6}  {'Havi br.':>10}  {'Város %':>7}<br>")
        table_rows.append("───────────────────────────────────────────────────────────<br>")

        for year in sorted(hist_dict.keys()):
            amount = hist_dict[year]
            if amount > 0:
                donors = get_donor_count(hist_data, year)
                if donors > 0:
                    avg_per_donor = amount / donors
                    monthly_gross = int(avg_per_donor * 100 * (100 / 15) / 12)
                else:
                    monthly_gross = 0

                city_pct = (amount / city_totals_by_year.get(year, 1) * 100)
                amount_str = f"{amount / 1e6:>9.1f}M" if amount >= 1e6 else f"{amount / 1e3:>9.0f}K"
                monthly_str = f"{monthly_gross / 1e6:>9.1f}M" if monthly_gross >= 1e6 else (
                    f"{monthly_gross / 1e3:>9.0f}K" if monthly_gross >= 1e3 else f"{monthly_gross:>9}")

                table_rows.append(
                    f"{year:<4}  {amount_str:>10}  {donors:>6}  {monthly_str:>10}  {city_pct:>6.1f}%<br>")

        table_rows.append("</span>")
        parent_cat = row.get('parent_category', '')
        leaf_cat = row.get('leaf_category', '')
        table_rows.append(f"<br><b>Kategória:</b> {parent_cat} → {leaf_cat}")
        hover_text = f"<b>{org_name}</b><br>{row.get('szekhely', '')}{''.join(table_rows)}"

        y_data = pct_values if is_pct else amounts
        color = COLORS_20[hash(org_name) % len(COLORS_20)]

        legend_name = (org_name[:20] + '…') if len(org_name) > 20 else org_name
        fig.add_trace(go.Scatter(
            x=years, y=y_data, mode='lines+markers',
            name=legend_name, line=dict(color=color, width=2),
            marker=dict(size=6, color=color),
            hovertemplate=hover_text + '<extra></extra>',
            hoverlabel=dict(bgcolor='white', font_size=11)
        ))

    y_title = 'Városon belüli arány (%)' if is_pct else 'Felajánlott összeg (Ft)'

    fig.update_layout(
        xaxis=dict(title='Év', gridcolor='lightgray', showline=True, linewidth=1,
                   linecolor='black', mirror=True, dtick=1),
        yaxis=dict(title=y_title, gridcolor='lightgray', showline=True,
                   linewidth=1, linecolor='black', mirror=True),
        plot_bgcolor='white', hovermode='closest', showlegend=True,
        legend=dict(title=dict(text='Szervezetek', font=dict(size=11)),
                    font=dict(size=9), itemwidth=30,
                    bgcolor='rgba(255,255,255,0.8)', bordercolor='lightgray', borderwidth=1),
        margin=dict(l=60, r=10, t=20, b=60)
    )

    return fig, summary


# City: table update (székhely mode only)
@app.callback(
    [Output('city-table', 'data'),
     Output('city-table-title', 'children'),
     Output('city-table-container', 'style')],
    [Input('city-dropdown', 'value'),
     Input('city-search-mode', 'data')]
)
def city_update_table(selected_city, search_mode):
    if search_mode is None:
        search_mode = 'szekhely'

    if search_mode != 'szekhely' or not selected_city or selected_city not in city_szekhely_data:
        return [], "", {'display': 'none'}

    adoszamok = set(str(a) for a in city_szekhely_data[selected_city]['adoszamok'])
    df_city = df_merged[df_merged['Adószám'].isin(adoszamok)].copy()
    df_city = df_city.sort_values('összeg', ascending=False)

    table_data = df_city[['Szervezet neve', 'összeg', 'parent_category', 'leaf_category', 'szekhely']].to_dict('records')

    title = f"{selected_city} — {len(table_data)} szervezet"
    return table_data, title, {'display': 'block'}


# ============================================================================
# RUN
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("Dashboard running at: http://127.0.0.1:8092/")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    app.run(debug=False, port=8092)
