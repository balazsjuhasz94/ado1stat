"""
Main execution script for civil.info.hu web scraper
Loads organization names from 200.txt and scrapes data
"""

import argparse
from civil_scraper import CivilScraper, load_organization_names, save_results, log_errors, safe_print


def main():
    """Main execution function"""

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Scrape civil.info.hu organization data')
    parser.add_argument('--input', type=str, default='200.txt',
                        help='Input file with organization names (default: 200.txt)')
    parser.add_argument('--output', type=str, default='civil_organizations_data.json',
                        help='Output JSON file (default: civil_organizations_data.json)')
    parser.add_argument('--log', type=str, default='scraping_errors.log',
                        help='Error log file (default: scraping_errors.log)')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit number of organizations to scrape (for testing)')
    parser.add_argument('--delay', type=float, default=1.5,
                        help='Delay between requests in seconds (default: 1.5)')
    parser.add_argument('--folder', type=str, default='organizations',
                        help='Folder to save individual organization JSON files (default: organizations)')

    args = parser.parse_args()

    # Load organization names
    safe_print(f"Loading organization names from: {args.input}")
    try:
        org_names = load_organization_names(args.input)
        safe_print(f"Loaded {len(org_names)} organization names")
    except FileNotFoundError:
        safe_print(f"Error: File '{args.input}' not found")
        return
    except Exception as e:
        safe_print(f"Error loading file: {str(e)}")
        return

    # Apply limit if specified
    if args.limit:
        org_names = org_names[:args.limit]
        safe_print(f"Limiting to first {args.limit} organizations")

    # Initialize scraper
    scraper = CivilScraper()

    # Run scraping
    results = scraper.scrape_all(org_names, delay=args.delay, output_folder=args.folder)

    # Save results
    save_results(results, args.output)

    # Save error log
    log_errors(results, args.log)

    safe_print("\nDone!")


if __name__ == '__main__':
    main()
