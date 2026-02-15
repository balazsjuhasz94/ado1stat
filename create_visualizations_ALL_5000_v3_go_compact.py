"""
Create hierarchical visualizations with COMPACT initial view
Uses all 5000 organizations but starts with categories collapsed
User can click to expand and drill down
"""

import pandas as pd
import plotly.graph_objects as go
import json
import os
import sys

# Set UTF-8 encoding for console output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Import helper functions
import create_visualizations_ALL_5000_v3_go as original

def main():
    print("=" * 80)
    print("COMPACT VISUALIZATION - All 5000 orgs with smart initial view")
    print("Starts collapsed, expands on click for better performance")
    print("=" * 80)

    # Load and process data (same as original, keeping ALL data)
    print("\n1-6. Loading and processing data...")

    df_categories = pd.read_csv('organization_categories_ALL_5000.csv', encoding='utf-8-sig')

    excel_file = 'Szja 1-os felajanlasban reszesult civil kedvezmenyezettek_2025.xlsx'
    df_excel = pd.read_excel(excel_file, sheet_name='Munka1', header=1)
    df_excel['összeg'] = pd.to_numeric(df_excel['Felajánlott összeg (Ft)'], errors='coerce').fillna(0).astype(int)
    df_excel['db'] = pd.to_numeric(df_excel['Felajánlók száma (fő)'], errors='coerce').fillna(0).astype(int)
    df_amounts = df_excel[['Adószám', 'Név', 'összeg', 'db']].copy()

    organizations_folder = 'organizations_by_adoszam'
    org_data_list = []

    if os.path.exists(organizations_folder):
        json_files = [f for f in os.listdir(organizations_folder) if f.endswith('.json')]
        for filename in json_files:
            filepath = os.path.join(organizations_folder, filename)
            try:
                json_data = original.read_json_file(filepath)
                org_info = original.extract_org_data(json_data)
                if org_info:
                    org_data_list.append(org_info)
            except:
                pass
    else:
        print(f"   Folder '{organizations_folder}' not found!")
        return

    df_orgs = pd.DataFrame(org_data_list)

    # Convert and merge
    df_categories['Adószám'] = df_categories['Adószám'].astype(str)
    df_orgs['adoszam'] = df_orgs['adoszam'].astype(str)
    df_amounts['Adószám'] = df_amounts['Adószám'].astype(str)

    df_merged = df_categories.merge(df_orgs, left_on='Adószám', right_on='adoszam', how='left')
    df_merged = df_merged.merge(df_amounts, left_on='Adószám', right_on='Adószám', how='left')
    df_merged = df_merged.dropna(subset=['összeg'])
    df_merged['összeg'] = df_merged['összeg'].astype(int)
    df_merged['db'] = df_merged['db'].astype(int)
    df_merged['purpose'] = df_merged['purpose'].fillna(df_merged['Cél (első 200 karakter)'])

    print(f"   Loaded {len(df_merged)} organizations")
    print(f"   Total: {df_merged['összeg'].sum():,.0f} Ft")

    # Format data
    df_merged['átlag_per_donor'] = (df_merged['összeg'] / df_merged['db']).round(0)
    df_merged['monthly_gross'] = (df_merged['átlag_per_donor'] * 100 * (100/15) / 12).round(0).astype(int)
    df_merged['short_name'] = df_merged['Szervezet neve'].str[:50]
    df_merged['formatted_purpose'] = df_merged['purpose'].apply(original.format_purpose_multiline)
    df_merged['historical_chart'] = df_merged['historical_data'].apply(original.safe_format_historical)
    df_merged['yoy_growth'] = df_merged['historical_data'].apply(original.calculate_yoy_growth)
    df_merged['szekhely'] = df_merged['szekhely'].fillna(df_merged['Székhely']).fillna('Nincs adat')
    df_merged['parent_category'] = df_merged['Szülő kategória']
    df_merged['leaf_category'] = df_merged['Új kategória (legalsó szint)']
    df_merged = df_merged.dropna(subset=['parent_category', 'leaf_category'])

    print("\n7. Building tree structure (ALL organizations)...")

    total_összeg = df_merged['összeg'].sum()
    total_db = df_merged['db'].sum()
    total_aggregated_hist = original.aggregate_historical_data(df_merged)

    # Build nodes (SAME AS ORIGINAL - keeps all orgs)
    nodes = []
    id_map = {}
    current_id = 0

    # Root
    all_hist_chart = original.format_historical_data_visual(total_aggregated_hist)
    all_yoy_growth = original.calculate_yoy_growth(total_aggregated_hist)

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
        'yoy_growth': all_yoy_growth,
        'depth': 0  # Track depth
    })
    id_map['__root__'] = str(current_id)
    current_id += 1

    # Parent categories
    for parent_cat in df_merged['parent_category'].unique():
        if pd.notna(parent_cat):
            subset = df_merged[df_merged['parent_category'] == parent_cat]
            összeg = subset['összeg'].sum()
            db = subset['db'].sum()

            aggregated_hist = original.aggregate_historical_data(subset)
            hist_chart = original.format_historical_data_with_percentage(aggregated_hist, total_aggregated_hist)
            yoy_growth = original.calculate_yoy_growth(aggregated_hist)

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
                'yoy_growth': yoy_growth,
                'depth': 1
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
                    összeg = subset['összeg'].sum()
                    db = subset['db'].sum()

                    aggregated_hist = original.aggregate_historical_data(subset)
                    hist_chart = original.format_historical_data_with_percentage(aggregated_hist, total_aggregated_hist)
                    yoy_growth = original.calculate_yoy_growth(aggregated_hist)

                    cat_key = f"{parent_cat}|{leaf_cat}"

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
                        'yoy_growth': yoy_growth,
                        'depth': 2
                    })
                    id_map[cat_key] = str(current_id)
                    current_id += 1

    # Organizations (ALL of them)
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
            'yoy_growth': row['yoy_growth'],
            'depth': 3  # Orgs are level 3
        })
        current_id += 1

    print(f"   Built tree with {len(nodes)} nodes (all orgs included)")

    # Calculate statistics
    print("\n8. Calculating statistics...")

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

    # Create graph objects lists
    ids = [n['id'] for n in nodes]
    labels = [n['label'] for n in nodes]
    parents = [n['parent'] for n in nodes]
    values = [n['összeg'] for n in nodes]

    customdata = [[
        n['org_name'],
        n['szekhely'],
        n['összeg'],
        n['db'],
        n['átlag'],
        n['monthly_gross'],
        n['pct_of_parent'],
        n['pct_of_total'],
        n['parent_label'],
        n['formatted_purpose'],
        n['historical_chart'],
        n['yoy_growth'],
        f"{n['yoy_growth']:+.1f}"
    ] for n in nodes]

    # Create chart
    print("\n9. Creating COMPACT Sunburst chart...")

    colors_salary = [n['monthly_gross'] for n in nodes]
    min_color_salary = pd.Series([n['monthly_gross'] for n in nodes if n['db'] > 0]).quantile(0.05)
    max_color_salary = pd.Series([n['monthly_gross'] for n in nodes if n['db'] > 0]).quantile(0.85)

    colors_growth = [n['yoy_growth'] for n in nodes]
    min_color_growth = -50.0
    max_color_growth = 50.0

    fig = go.Figure()

    # Add traces with smaller initial textfont for compact view
    fig.add_trace(go.Sunburst(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        branchvalues='total',
        customdata=customdata,
        name='Default',
        visible=True,
        level='',  # Start at root level (most collapsed)
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
        textfont=dict(size=8)  # Smaller font for compact view
    ))

    fig.add_trace(go.Sunburst(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        branchvalues='total',
        customdata=customdata,
        name='Salary',
        visible=False,
        level='',
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
        textfont=dict(size=8)
    ))

    fig.add_trace(go.Sunburst(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        branchvalues='total',
        customdata=customdata,
        name='Growth',
        visible=False,
        level='',
        marker=dict(
            colorscale='RdYlGn',
            cmid=0,
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
        textfont=dict(size=8)
    ))

    fig.update_layout(
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
            'text': 'Civil Szervezetek - Sunburst (Compact View)<br><sub>Kattints a kategóriákra a kibontáshoz - Összes ({:,}) szervezet</sub>'.format(len(df_merged)),
            'x': 0.5,
            'xanchor': 'center'
        }
    )

    output_file = 'sunburst_chart_ALL_5000_go_interactive.html'
    fig.write_html(output_file)
    print(f"   ✓ Saved to {output_file}")

    print("\n" + "=" * 80)
    print("DONE! Compact sunburst visualization created")
    print(f"  Organizations: {len(df_merged)} (ALL included)")
    print(f"  Total nodes: {len(nodes)}")
    print(f"  Initial view: Collapsed at category level")
    print(f"  Click categories to drill down and see individual organizations")
    print("=" * 80)


if __name__ == '__main__':
    main()
