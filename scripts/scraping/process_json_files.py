"""
Helper script to read and process scraped JSON files with correct UTF-8 encoding
"""

import json
import os
from typing import List, Dict, Any


def read_json_file(filepath: str) -> Dict[str, Any]:
    """
    Read a JSON file with UTF-8 encoding

    Args:
        filepath: Path to JSON file

    Returns:
        Dictionary with JSON data
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def read_all_organizations(folder: str = 'organizations') -> List[Dict[str, Any]]:
    """
    Read all organization JSON files from a folder

    Args:
        folder: Path to folder containing JSON files (default: 'organizations')

    Returns:
        List of organization data dictionaries
    """
    organizations = []

    if not os.path.exists(folder):
        print(f"Folder '{folder}' does not exist")
        return organizations

    json_files = [f for f in os.listdir(folder) if f.endswith('.json')]
    print(f"Found {len(json_files)} JSON files in '{folder}'")

    for filename in json_files:
        filepath = os.path.join(folder, filename)
        try:
            org_data = read_json_file(filepath)
            organizations.append(org_data)
        except Exception as e:
            print(f"Error reading {filename}: {str(e)}")

    print(f"Successfully loaded {len(organizations)} organizations")
    return organizations


def extract_basic_info(organizations: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Extract basic information from organizations

    Args:
        organizations: List of organization data dictionaries

    Returns:
        List of dictionaries with basic info (name, tax number, address, etc.)
    """
    basic_info = []

    for org in organizations:
        try:
            azonosito = org.get('alapadatok', {}).get('azonosito_adatok', {})
            fonadatok = org.get('alapadatok', {}).get('fonadatok', {})
            nav_data = org.get('nav_1_percent', {}).get('kedvezmenyezett_adatok', [])

            # Get latest NAV 1% data if available
            nav_1_percent = None
            if nav_data and len(nav_data) > 0:
                latest_year = nav_data[0]
                nav_1_percent = latest_year.get('Az érvényes civil kedvezményezettet megillető szja 1% összege', 'N/A')

            info = {
                'name': azonosito.get('teljes_név', 'N/A'),
                'tax_number': azonosito.get('adószám', 'N/A'),
                'address': azonosito.get('székhely_címe', 'N/A'),
                'organization_type': fonadatok.get('szervezet_típusa', 'N/A'),
                'public_benefit': fonadatok.get('közhasznú_fokozata', 'N/A'),
                'status': fonadatok.get('állapot', 'N/A'),
                'employees': fonadatok.get('alkalmazottak_száma', 'N/A'),
                'nav_1_percent': nav_1_percent or 'N/A',
                'organization_id': org.get('organization_id', 'N/A')
            }

            basic_info.append(info)
        except Exception as e:
            print(f"Error extracting info for {org.get('search_name', 'Unknown')}: {str(e)}")

    return basic_info


def save_to_csv(basic_info: List[Dict[str, str]], output_file: str = 'organizations_summary.csv'):
    """
    Save basic organization info to CSV file

    Args:
        basic_info: List of dictionaries with basic organization info
        output_file: Output CSV filename (default: 'organizations_summary.csv')
    """
    import csv

    if not basic_info:
        print("No data to save")
        return

    # Get all possible keys
    fieldnames = list(basic_info[0].keys())

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(basic_info)

    print(f"Saved {len(basic_info)} organizations to {output_file}")


def main():
    """Example usage"""

    print("="*60)
    print("Processing scraped organization data")
    print("="*60)

    # Read all organization files
    organizations = read_all_organizations('organizations')

    if not organizations:
        print("No organizations found. Make sure to run the scraper first.")
        return

    # Extract basic information
    print("\nExtracting basic information...")
    basic_info = extract_basic_info(organizations)

    # Display first few organizations
    print("\nFirst 5 organizations:")
    for i, info in enumerate(basic_info[:5], 1):
        print(f"\n{i}. {info['name']}")
        print(f"   Tax Number: {info['tax_number']}")
        print(f"   Address: {info['address']}")
        print(f"   Type: {info['organization_type']}")
        print(f"   Public Benefit: {info['public_benefit']}")
        print(f"   NAV 1%: {info['nav_1_percent']}")

    # Save to CSV
    print("\n" + "="*60)
    save_to_csv(basic_info)
    print("="*60)

    # Summary statistics
    print("\nSummary:")
    print(f"  Total organizations: {len(organizations)}")
    print(f"  Organizations with NAV 1% data: {sum(1 for info in basic_info if info['nav_1_percent'] != 'N/A')}")

    # Count by public benefit status
    benefit_counts = {}
    for info in basic_info:
        status = info['public_benefit']
        benefit_counts[status] = benefit_counts.get(status, 0) + 1

    print("\n  By public benefit status:")
    for status, count in sorted(benefit_counts.items()):
        print(f"    {status}: {count}")


if __name__ == '__main__':
    main()
