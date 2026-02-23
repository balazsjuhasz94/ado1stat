"""Diagnose tree structure issues"""
import pandas as pd
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Load data
df_categories = pd.read_csv('organization_categories_adoszam_500.csv', encoding='utf-8-sig')
df_categories['Adószám'] = df_categories['Adószám'].astype(str)

excel_file = 'Szja 1-os felajanlasban reszesult civil kedvezmenyezettek_2025.xlsx'
df_amounts = pd.read_excel(excel_file, sheet_name='Munka1', header=1)
df_amounts['Adószám'] = df_amounts['Adószám'].astype(str)
df_amounts = df_amounts.rename(columns={'Felajánlott összeg (Ft)': 'összeg', 'Felajánlók száma (fő)': 'db'})

df_merged = df_categories.merge(df_amounts[['Adószám', 'összeg', 'db']], on='Adószám', how='inner')
df_merged['parent_category'] = df_merged['Szülő kategória']
df_merged['leaf_category'] = df_merged['Új kategória (legalsó szint)']

total_összeg = df_merged['összeg'].sum()
total_db = df_merged['db'].sum()

# Build tree with same logic as main script
nodes = []
id_map = {}
current_id = 0

# Root
nodes.append({'id': str(current_id), 'label': 'Összes', 'parent': '', 'összeg': total_összeg})
id_map['__root__'] = str(current_id)
current_id += 1

# Parent categories
for parent_cat in df_merged['parent_category'].unique():
    if pd.notna(parent_cat):
        subset = df_merged[df_merged['parent_category'] == parent_cat]
        nodes.append({
            'id': str(current_id),
            'label': parent_cat,
            'parent': id_map['__root__'],
            'összeg': subset['összeg'].sum()
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
                cat_key = f"{parent_cat}|{leaf_cat}"
                nodes.append({
                    'id': str(current_id),
                    'label': leaf_cat,
                    'parent': id_map.get(parent_cat, '0'),
                    'összeg': subset['összeg'].sum()
                })
                id_map[cat_key] = str(current_id)
                current_id += 1

# Organizations
for idx, row in df_merged.iterrows():
    parent_cat = row['parent_category']
    leaf_cat = row['leaf_category']
    parent_key = f"{parent_cat}|{leaf_cat}"

    nodes.append({
        'id': str(current_id),
        'label': row['Szervezet neve'][:30],
        'parent': id_map.get(parent_key, '0'),
        'összeg': row['összeg']
    })
    current_id += 1

print(f"Total nodes: {len(nodes)}")

# Check tree integrity
ids = [n['id'] for n in nodes]
parents = [n['parent'] for n in nodes]
values = [n['összeg'] for n in nodes]

# Find orphaned nodes (parent doesn't exist)
id_set = set(ids)
orphaned = []
for i, parent in enumerate(parents):
    if parent != '' and parent not in id_set:
        orphaned.append((ids[i], nodes[i]['label'], parent))

if orphaned:
    print(f"\n❌ Found {len(orphaned)} orphaned nodes (parent doesn't exist):")
    for node_id, label, parent in orphaned[:10]:
        print(f"   Node {node_id} ({label}) has non-existent parent {parent}")
else:
    print("\n✅ No orphaned nodes")

# Check if all nodes connect to root
def get_root(node_id):
    """Trace back to root"""
    visited = set()
    current = node_id
    while current != '':
        if current in visited:
            return None  # Circular reference
        visited.add(current)
        idx = ids.index(current)
        current = parents[idx]
    return '0' if '0' in visited else None

disconnected = []
for i, node_id in enumerate(ids):
    if node_id != '0':  # Skip root
        root = get_root(node_id)
        if root is None:
            disconnected.append((node_id, nodes[i]['label']))

if disconnected:
    print(f"\n❌ Found {len(disconnected)} disconnected nodes:")
    for node_id, label in disconnected[:10]:
        print(f"   Node {node_id} ({label})")
else:
    print("✅ All nodes connect to root")

# Check value sums
print(f"\nValue checks:")
print(f"  Root value: {nodes[0]['összeg']:,.0f} Ft")
print(f"  Sum of all values: {sum(values):,.0f} Ft")
print(f"  Expected total: {total_összeg:,.0f} Ft")

# Count children per level
children_count = {}
for parent in parents:
    children_count[parent] = children_count.get(parent, 0) + 1

print(f"\nChildren distribution:")
print(f"  Root ('') has {children_count.get('', 0)} children")
for i in range(1, 10):
    if str(i) in children_count:
        print(f"  Node {i} ({nodes[i]['label']}) has {children_count[str(i)]} children")

# Check for missing parent mappings
print(f"\nid_map keys: {len(id_map)}")
print(f"Checking for missing mappings...")
missing = []
for idx, row in df_merged.iterrows():
    parent_cat = row['parent_category']
    leaf_cat = row['leaf_category']
    parent_key = f"{parent_cat}|{leaf_cat}"
    if parent_key not in id_map:
        missing.append(parent_key)

if missing:
    print(f"❌ Found {len(missing)} missing parent_key mappings")
    print(f"   First few: {missing[:5]}")
else:
    print("✅ All parent_key mappings exist")
