"""
Main execution script for civil.info.hu web scraper - Search by Tax Number (Adószám)
Loads tax numbers from adoszam_500.txt or adoszam_5000.txt and scrapes data
"""

import argparse
from civil_scraper_adoszam import CivilScraperAdoszam, load_tax_numbers, save_results, log_errors, safe_print


def main():
    """Main execution function"""

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Scrape civil.info.hu organization data by tax number')
    parser.add_argument('--input', type=str, default='adoszam_500.txt',
                        help='Input file with tax numbers (default: adoszam_500.txt)')
    parser.add_argument('--output', type=str, default='civil_organizations_by_adoszam.json',
                        help='Output JSON file (default: civil_organizations_by_adoszam.json)')
    parser.add_argument('--log', type=str, default='scraping_errors_adoszam.log',
                        help='Error log file (default: scraping_errors_adoszam.log)')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit number of organizations to scrape (for testing)')
    parser.add_argument('--delay', type=float, default=1.5,
                        help='Delay between requests in seconds (default: 1.5)')
    parser.add_argument('--folder', type=str, default='organizations_by_adoszam',
                        help='Folder to save individual organization JSON files (default: organizations_by_adoszam)')

    args = parser.parse_args()

    # Load tax numbers
    safe_print(f"Loading tax numbers from: {args.input}")
    try:
        tax_numbers = load_tax_numbers(args.input)
        safe_print(f"Loaded {len(tax_numbers)} tax numbers")
    except FileNotFoundError:
        safe_print(f"Error: File '{args.input}' not found")
        return
    except Exception as e:
        safe_print(f"Error loading file: {str(e)}")
        return

    # Apply limit if specified
    if args.limit:
        tax_numbers = tax_numbers[:args.limit]
        safe_print(f"Limiting to first {args.limit} organizations")

    # Initialize scraper
    scraper = CivilScraperAdoszam()

    # Run scraping
    results = scraper.scrape_all(tax_numbers, delay=args.delay, output_folder=args.folder)

    # Save results
    save_results(results, args.output)

    # Save error log
    log_errors(results, args.log)

    safe_print("\nDone!")


if __name__ == '__main__':
    main()
