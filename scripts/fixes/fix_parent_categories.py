"""
Fix parent categories in organization_categories_llm.csv
by mapping leaf categories to their parents from categories.yaml
"""

import pandas as pd
import yaml
import sys
from typing import Dict, List, Tuple

# Set UTF-8 encoding for console output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def extract_category_hierarchy(data, parent_path=None):
    """
    Extract mapping of leaf category -> (parent1, parent2)

    Returns:
        Dict mapping leaf category name to tuple of (parent1, parent2)
    """
    if parent_path is None:
        parent_path = []

    category_map = {}

    for item in data:
        if isinstance(item, str):
            # This is a leaf node
            parent1 = parent_path[0] if len(parent_path) > 0 else ''
            parent2 = parent_path[1] if len(parent_path) > 1 else ''
            category_map[item] = (parent1, parent2)
        elif isinstance(item, dict):
            # This has children
            for parent, children in item.items():
                if isinstance(children, list):
                    # Recurse into children
                    child_map = extract_category_hierarchy(children, parent_path + [parent])
                    category_map.update(child_map)

    return category_map


def main():
    print("="*70)
    print("FIXING PARENT CATEGORIES")
    print("="*70)

    # Load category hierarchy
    print("\n1. Loading category hierarchy from categories.yaml...")
    with open('categories.yaml', 'r', encoding='utf-8') as f:
        hierarchy = yaml.safe_load(f)

    # Build category mapping
    category_map = extract_category_hierarchy(hierarchy)
    print(f"   Found {len(category_map)} leaf categories with parent mappings")

    # Show some examples
    print("\n   Sample mappings:")
    for i, (leaf, parents) in enumerate(list(category_map.items())[:5]):
        print(f"     {leaf} -> Parent1: '{parents[0]}', Parent2: '{parents[1]}'")

    # Load LLM categorization CSV
    print("\n2. Loading organization_categories_llm.csv...")
    df = pd.read_csv('organization_categories_llm.csv', encoding='utf-8-sig')
    print(f"   Loaded {len(df)} organizations")

    # Add parent categories
    print("\n3. Adding parent categories...")

    def get_parents(leaf_category):
        """Get parent categories for a leaf category"""
        if leaf_category in category_map:
            return category_map[leaf_category]
        else:
            # Category not found in hierarchy
            return ('', '')

    # Apply mapping
    df[['Szülő kategória 1', 'Szülő kategória 2']] = df['Új kategória (legalsó szint)'].apply(
        lambda x: pd.Series(get_parents(x))
    )

    # Count how many have parents
    has_parent1 = (df['Szülő kategória 1'] != '').sum()
    has_parent2 = (df['Szülő kategória 2'] != '').sum()

    print(f"   Organizations with Parent 1: {has_parent1} ({has_parent1/len(df)*100:.1f}%)")
    print(f"   Organizations with Parent 2: {has_parent2} ({has_parent2/len(df)*100:.1f}%)")

    # Show categories without parents (not in hierarchy)
    no_parent = df[df['Szülő kategória 1'] == '']['Új kategória (legalsó szint)'].unique()
    if len(no_parent) > 0:
        print(f"\n   WARNING: {len(no_parent)} leaf categories not found in hierarchy:")
        for cat in no_parent[:10]:
            print(f"     - {cat}")

    # Save updated CSV
    print("\n4. Saving updated CSV...")
    output_file = 'organization_categories_llm.csv'
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"   Saved to: {output_file}")

    # Show sample of updated data
    print("\n5. Sample of updated data:")
    print(df[['Szervezet neve', 'Új kategória (legalsó szint)', 'Szülő kategória 1', 'Szülő kategória 2']].head(10).to_string())

    print("\n" + "="*70)
    print("DONE!")
    print("="*70)


if __name__ == '__main__':
    main()
