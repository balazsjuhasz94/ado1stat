"""
Fix shifted labels in organization_categories_ALL_5000.csv (PROPER VERSION)
The LLM returned 9 labels for batch 80, causing labels to shift.
This script re-assigns labels without duplicating organizations.
"""

import pandas as pd
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 80)
print("FIXING SHIFTED LABELS - PROPER VERSION")
print("=" * 80)

# 1. Load the CSV
print("\n1. Loading CSV file...")
df = pd.read_csv('organization_categories_ALL_5000_BACKUP.csv', encoding='utf-8-sig')  # Use backup
print(f"   Loaded {len(df)} rows")

# 2. The issue: batch 80 (rows 790-799) got 9 labels instead of 10
# This means:
# - Rows 0-798: correct labels
# - Row 799: has label meant for row 800
# - Row 800: has label meant for row 801
# - ...
# - Row 4998: has label meant for row 4999
# - Row 4999: has "Kategorizálatlan" (no label available)

shift_start = 799  # Where the shift begins

print(f"\n2. Issue: Labels shifted starting at row {shift_start}")
print(f"   Rows 0-{shift_start-1}: Correct labels ✓")
print(f"   Rows {shift_start}-4999: Each has label meant for next row ✗")

# 3. Fix: Shift labels back
print(f"\n3. Fixing labels...")

# Store the current labels
labels = df['Új kategória (legalsó szint)'].tolist()
parent_cats = df['Szülő kategória'].tolist()

# Create new label arrays
fixed_labels = labels[:shift_start]  # Keep first 799 labels
fixed_parents = parent_cats[:shift_start]  # Keep first 799 parent cats

# Insert placeholder at position 799
fixed_labels.append('Kategorizálatlan')
fixed_parents.append('Egyéb')

# Add the remaining labels (shifted back)
fixed_labels.extend(labels[shift_start:-1])  # Skip the last one (which was "Kategorizálatlan")
fixed_parents.extend(parent_cats[shift_start:-1])

# Verify lengths match
assert len(fixed_labels) == len(df), f"Label count mismatch: {len(fixed_labels)} vs {len(df)}"
assert len(fixed_parents) == len(df), f"Parent count mismatch: {len(fixed_parents)} vs {len(df)}"

# Update the dataframe
df['Új kategória (legalsó szint)'] = fixed_labels
df['Szülő kategória'] = fixed_parents

print(f"   ✓ Labels realigned")

# 4. Show examples around the fix
print(f"\n4. Verification - Organizations around row {shift_start}:")
for i in range(max(0, shift_start-2), min(len(df), shift_start+5)):
    org_name = df.iloc[i]['Szervezet neve'][:45]
    category = df.iloc[i]['Új kategória (legalsó szint)']
    marker = " ← FIXED" if i == shift_start else ""
    print(f"   Row {i:4d}: {category:30s} | {org_name}{marker}")

# 5. Check for duplicates
print(f"\n5. Checking for duplicate organizations...")
duplicates = df[df.duplicated(subset=['Adószám'], keep=False)]
if len(duplicates) > 0:
    print(f"   ⚠️ WARNING: Found {len(duplicates)} duplicate tax numbers")
    for idx, row in duplicates.head(10).iterrows():
        print(f"      Row {idx}: {row['Adószám']} - {row['Szervezet neve'][:50]}")
else:
    print(f"   ✓ No duplicates found - all {len(df)} organizations are unique")

# 6. Count categories
print(f"\n6. Category distribution:")
category_counts = df['Új kategória (legalsó szint)'].value_counts()
print(f"   'Kategorizálatlan': {category_counts.get('Kategorizálatlan', 0)} organizations")
print(f"   Other categories: {len(category_counts) - 1} different categories")

# 7. Save
output_file = 'organization_categories_ALL_5000.csv'
df.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"\n7. Saved fixed CSV to: {output_file}")
print(f"   Total rows: {len(df)}")

print("\n" + "=" * 80)
print("DONE! Labels are now correctly aligned.")
print("=" * 80)
print(f"\nNote: Row {shift_start} now has 'Kategorizálatlan'")
print("This is the organization that didn't get classified in batch 80.")
print("All other organizations have their correct labels.")
print("\nYou can now re-run:")
print("  python create_visualizations_ALL_5000_v3_go.py")
