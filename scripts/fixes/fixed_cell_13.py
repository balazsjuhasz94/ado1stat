# Fixed version of cell 13 - Build hierarchical path for visualization

def build_category_path(row):
    """Build hierarchical path for sunburst/treemap - ensures consistent structure"""
    path = []

    # Get category values
    parent1 = row['Szülő kategória 1']
    parent2 = row['Szülő kategória 2']
    leaf = row['Új kategória (legalsó szint)']
    org_name = row['short_name']

    # Build path based on what's available
    # Strategy: Always include all levels, use leaf as placeholder for missing parents

    if pd.notna(parent1) and parent1 != '':
        # Has parent1
        path.append(parent1)

        if pd.notna(parent2) and parent2 != '':
            # Has both parent1 and parent2
            path.append(parent2)
            path.append(leaf)
        else:
            # Has parent1 but no parent2
            path.append(leaf)
    else:
        # No parents - top level category
        path.append(leaf)

    # Always add organization name at the end
    path.append(org_name)

    return path

# Build paths for all organizations
df_merged['category_path'] = df_merged.apply(build_category_path, axis=1)

# Check path structure
print("Sample category paths:")
for i, path in enumerate(df_merged['category_path'].head(10)):
    print(f"{i+1}. ({len(path)} levels) {' > '.join(path)}")

# Check path lengths distribution
path_lengths = df_merged['category_path'].apply(len)
print(f"\nPath length distribution:")
print(path_lengths.value_counts().sort_index())
