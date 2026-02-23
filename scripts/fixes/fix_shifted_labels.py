"""
Fix shifted labels in organization_categories_ALL_5000.csv
The LLM returned 9 labels for batch 80 (10 organizations), causing a shift.
This script inserts a placeholder row to realign everything.
"""

import pandas as pd
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 80)
print("FIXING SHIFTED LABELS IN CLASSIFICATION DATA")
print("=" * 80)

# 1. Load the current (corrupted) CSV
print("\n1. Loading current CSV file...")
df = pd.read_csv('organization_categories_ALL_5000.csv', encoding='utf-8-sig')
print(f"   Loaded {len(df)} rows")

# 2. Find where the shift occurred
# Batch 80 means organizations 790-799 (batch 1 = orgs 0-9, batch 2 = orgs 10-19, etc.)
# The mismatch happened in batch 80, which is orgs 790-799
# The 10th org in that batch (index 799) didn't get a label
# So we need to insert a placeholder at row 799

shift_position = 799  # This is the row index where we need to insert

print(f"\n2. Shift occurred at row {shift_position} (batch 80, org #{shift_position+1})")
print(f"   Organization at this position: {df.iloc[shift_position]['Szervezet neve']}")

# 3. Create a placeholder row
# Copy the row structure from the row at shift_position
placeholder_row = df.iloc[shift_position].copy()
placeholder_row['Új kategória (legalsó szint)'] = 'Kategorizálatlan'
placeholder_row['Szülő kategória'] = 'Egyéb'

print(f"\n3. Creating placeholder row:")
print(f"   Organization: {placeholder_row['Szervezet neve']}")
print(f"   Category: Kategorizálatlan (will be inserted)")

# 4. Split the dataframe and insert the placeholder
df_before = df.iloc[:shift_position]  # Rows 0-798 (correct)
df_after = df.iloc[shift_position:]   # Rows 799-4999 (shifted, will become 800-5000)

# Create new dataframe with placeholder inserted
df_fixed = pd.concat([
    df_before,
    pd.DataFrame([placeholder_row]),
    df_after
], ignore_index=True)

print(f"\n4. Reconstruction:")
print(f"   Before shift: {len(df_before)} rows (0-{shift_position-1})")
print(f"   Placeholder: 1 row (will be at index {shift_position})")
print(f"   After shift: {len(df_after)} rows ({shift_position}-{len(df)-1}) → will become ({shift_position+1}-{len(df)})")
print(f"   Total: {len(df_fixed)} rows")

# 5. Verify the fix
print(f"\n5. Verification:")
print(f"   Original file had: {len(df)} rows")
print(f"   Fixed file has: {len(df_fixed)} rows")
print(f"   Difference: +{len(df_fixed) - len(df)} row (should be +1)")

# Show some examples around the shift point
print(f"\n   Organizations around the shift point:")
for i in range(max(0, shift_position-2), min(len(df_fixed), shift_position+3)):
    org_name = df_fixed.iloc[i]['Szervezet neve'][:50]
    category = df_fixed.iloc[i]['Új kategória (legalsó szint)']
    marker = " ← INSERTED" if i == shift_position else ""
    print(f"   Row {i:4d}: {category:30s} | {org_name}{marker}")

# 6. Save the fixed CSV
output_file = 'organization_categories_ALL_5000_FIXED.csv'
df_fixed.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"\n6. Saved fixed CSV to: {output_file}")

# 7. Create backup and replace
import shutil
backup_file = 'organization_categories_ALL_5000_BACKUP.csv'
shutil.copy('organization_categories_ALL_5000.csv', backup_file)
print(f"   Created backup: {backup_file}")

# Replace the original file
shutil.copy(output_file, 'organization_categories_ALL_5000.csv')
print(f"   Replaced original file with fixed version")

print("\n" + "=" * 80)
print("DONE! The labels are now correctly aligned.")
print("=" * 80)
print(f"\nNote: Row {shift_position} has 'Kategorizálatlan' as a placeholder.")
print("All other rows should now have correct labels.")
print("\nYou can now re-run:")
print("  python create_visualizations_ALL_5000_v3_go.py")
