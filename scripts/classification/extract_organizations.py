import json
import os
from pathlib import Path

def main():
    """Extract organization names and goals from JSON files"""
    org_dir = Path(r"c:\Users\juhib\home_projects\ado1\organizations")
    org_files = list(org_dir.glob("*.json"))

    print(f"Found {len(org_files)} organization files")

    organizations_data = []

    # Read all organizations
    for org_file in org_files:
        try:
            with open(org_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

                # Skip if error
                if data.get('error'):
                    continue

                # Extract relevant information
                name = data.get('search_name', 'Ismeretlen')
                goal = ""

                if 'alapadatok' in data and 'fonadatok' in data['alapadatok']:
                    fonadatok = data['alapadatok']['fonadatok']
                    if fonadatok:
                        goal = fonadatok.get('céljának_leírása', '')

                if goal:  # Only include organizations with goals
                    organizations_data.append({
                        'name': name,
                        'goal': goal,
                        'file': org_file.name
                    })
        except Exception as e:
            print(f"Error reading {org_file.name}: {e}")

    print(f"Successfully loaded {len(organizations_data)} organizations with goals")

    # Save to JSON for processing
    output_file = Path(r"c:\Users\juhib\home_projects\ado1\organizations_to_categorize.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(organizations_data, f, ensure_ascii=False, indent=2)

    print(f"Saved to {output_file}")

    # Print some statistics
    total_orgs = len(organizations_data)
    avg_goal_length = sum(len(org['goal']) for org in organizations_data) / total_orgs if total_orgs > 0 else 0

    print(f"\nStatistics:")
    print(f"  Total organizations with goals: {total_orgs}")
    print(f"  Average goal length: {avg_goal_length:.0f} characters")

    # Show first few examples
    print(f"\nFirst 5 examples:")
    for i, org in enumerate(organizations_data[:5]):
        print(f"\n{i+1}. {org['name']}")
        print(f"   Goal (first 200 chars): {org['goal'][:200]}...")

if __name__ == "__main__":
    main()
