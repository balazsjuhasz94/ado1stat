"""
Web scraper for civil.info.hu - Search by Adószám (Tax Number)
Modified version that searches organizations by tax number instead of name
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
import traceback
import sys
import os


def safe_print(text: str):
    """Print text with encoding error handling for Windows console"""
    try:
        print(text)
    except UnicodeEncodeError:
        # Fallback to ASCII with errors ignored
        print(text.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding))


class CivilScraperAdoszam:
    """Web scraper for civil.info.hu - searches by tax number (adószám)"""

    def __init__(self):
        """Initialize scraper with session and base configuration"""
        self.session = requests.Session()
        self.base_url = "https://civil.info.hu"
        self.search_url = f"{self.base_url}/civil_szervezet_kereso/be.html"
        self.profile_url = f"{self.base_url}/civil_szervezet_kereso/profil"

        # Set headers to mimic browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest'
        })

    def search_organization_by_adoszam(self, adoszam: str) -> Optional[str]:
        """
        Search for organization by tax number (adószám) and return first result's ID

        Args:
            adoszam: Tax number to search for

        Returns:
            Organization ID (szervezet_id) or None if not found
        """
        try:
            params = {'action': 'getCivilData'}
            data = {
                'nev': '',
                'tipus': '',
                'besorolas': '',
                'cim': '',
                'adoszam': adoszam,  # Search by tax number
                'kozhasznu': '',
                'kozpont': '',
                'torolt': '0',
                'draw': '1',
                'start': '0',
                'length': '10'
            }

            # Make AJAX search request
            response = self.session.post(
                self.search_url,
                params=params,
                data=data,
                timeout=30
            )
            response.raise_for_status()

            # Parse JSON response
            result = response.json()

            # Check if results exist
            if result.get('data') and len(result['data']) > 0:
                first_result = result['data'][0]
                org_id = first_result.get('szervezet_id')
                org_name = first_result.get('neve', 'Unknown')
                safe_print(f"  Found: {org_name} (ID: {org_id})")
                return org_id

            return None

        except Exception as e:
            raise Exception(f"Search failed: {str(e)}")

    def fetch_profile(self, org_id: str) -> str:
        """
        Fetch organization profile page HTML

        Args:
            org_id: Organization ID

        Returns:
            HTML content of profile page
        """
        try:
            # POST request to profile page with organization ID
            data = {'id': org_id}
            response = self.session.post(
                self.profile_url,
                data=data,
                timeout=30
            )
            response.raise_for_status()

            return response.text

        except Exception as e:
            raise Exception(f"Profile fetch failed: {str(e)}")

    def _clean_text(self, text: Optional[str]) -> str:
        """Clean extracted text (remove extra whitespace, decode entities)"""
        if not text:
            return ""
        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _extract_table_rows(self, soup: BeautifulSoup, table_selector: str) -> List[Dict[str, str]]:
        """
        Extract rows from a table as list of dictionaries

        Args:
            soup: BeautifulSoup object
            table_selector: CSS selector for the table

        Returns:
            List of dictionaries with column headers as keys
        """
        rows = []
        table = soup.select_one(table_selector)
        if not table:
            return rows

        # Get headers
        headers = []
        thead = table.select_one('thead')
        if thead:
            header_cells = thead.select('th')
            headers = [self._clean_text(th.get_text()) for th in header_cells]

        # Get data rows
        tbody = table.select_one('tbody')
        if tbody:
            for tr in tbody.select('tr'):
                cells = tr.select('td')
                if cells and headers:
                    row_dict = {}
                    for i, cell in enumerate(cells):
                        if i < len(headers):
                            row_dict[headers[i]] = self._clean_text(cell.get_text())
                    if row_dict:
                        rows.append(row_dict)

        return rows

    def _extract_form_group_data(self, container) -> Dict[str, str]:
        """
        Extract data from form-group rows (publicorgrow class)

        Args:
            container: BeautifulSoup element containing form groups

        Returns:
            Dictionary with label as key and value from strong tag
        """
        data = {}
        if not container:
            return data

        form_groups = container.select('.form-group.publicorgrow')
        for group in form_groups:
            label_elem = group.select_one('label.col-form-label')
            value_elem = group.select_one('.col-sm-9 strong')

            if label_elem and value_elem:
                key = self._clean_text(label_elem.get_text())
                value = self._clean_text(value_elem.get_text())
                # Create safe key name (lowercase, no special chars)
                safe_key = re.sub(r'[^\w\s]', '', key.lower()).replace(' ', '_')
                data[safe_key] = value

        return data

    def parse_alapadatok(self, html: str) -> Dict[str, Any]:
        """
        Parse Alapadatok (Basic Data) tab

        Args:
            html: HTML content of profile page

        Returns:
            Dictionary with all basic data sections
        """
        soup = BeautifulSoup(html, 'html.parser')
        alapadatok = {}

        try:
            # Extract Azonosító adatok (Identifier data) from baseDataContainer
            base_container = soup.select_one('#baseDataContainer')
            if base_container:
                alapadatok['azonosito_adatok'] = self._extract_form_group_data(base_container)

            # Extract Főnadatok (Main data) from details1 tab
            details1 = soup.select_one('#details1')
            if details1:
                # Extract all publicorgrow form groups that are NOT inside fieldsets
                fonadatok = {}
                for group in details1.select('.form-group.publicorgrow'):
                    # Skip if inside a fieldset
                    if group.find_parent('fieldset'):
                        continue

                    label_elem = group.select_one('label.col-form-label')
                    value_elem = group.select_one('.col-sm-9 strong')

                    if label_elem and value_elem:
                        key = self._clean_text(label_elem.get_text())
                        value = self._clean_text(value_elem.get_text())
                        safe_key = re.sub(r'[^\w\s]', '', key.lower()).replace(' ', '_')
                        fonadatok[safe_key] = value

                alapadatok['fonadatok'] = fonadatok

            # Extract Képviselők (Representatives)
            kepviselok_table = soup.select_one('#details1 table#dataTable-kepviselo')
            if kepviselok_table:
                alapadatok['kepviselok'] = self._extract_table_rows(soup, '#details1 table#dataTable-kepviselo')
            else:
                alapadatok['kepviselok'] = []

            # Extract Eljárások (Procedures) - if table exists
            eljarasok_table = soup.select_one('#details1 table[data-groupname="eljaras"]')
            if eljarasok_table:
                alapadatok['eljarasok'] = self._extract_table_rows(soup, '#details1 table[data-groupname="eljaras"]')
            else:
                alapadatok['eljarasok'] = []

            # Extract TEÁOR codes
            teaor_table = soup.select_one('#details1 table#dataTable-teaor')
            if teaor_table:
                alapadatok['teaor'] = self._extract_table_rows(soup, '#details1 table#dataTable-teaor')
            else:
                alapadatok['teaor'] = []

        except Exception as e:
            safe_print(f"Warning: Error parsing alapadatok: {str(e)}")

        return alapadatok

    def parse_nav_1_percent(self, html: str) -> Dict[str, Any]:
        """
        Parse NAV 1% tab

        Args:
            html: HTML content of profile page

        Returns:
            Dictionary with NAV 1% data sections
        """
        soup = BeautifulSoup(html, 'html.parser')
        nav_data = {}

        try:
            # Extract Kedvezményezett adatok (Beneficiary data)
            kedv_table = soup.select_one('#details2 table#navTable1')
            if kedv_table:
                nav_data['kedvezmenyezett_adatok'] = self._extract_table_rows(soup, '#details2 table#navTable1')
            else:
                nav_data['kedvezmenyezett_adatok'] = []

            # Extract Közlemények (Announcements)
            kozl_table = soup.select_one('#details2 table#navTable2')
            if kozl_table:
                nav_data['kozlemenyek'] = self._extract_table_rows(soup, '#details2 table#navTable2')
            else:
                nav_data['kozlemenyek'] = []

            # Extract Kizárások (Exclusions)
            kiz_table = soup.select_one('#details2 table#navTable3')
            if kiz_table:
                nav_data['kizarasok'] = self._extract_table_rows(soup, '#details2 table#navTable3')
            else:
                nav_data['kizarasok'] = []

        except Exception as e:
            safe_print(f"Warning: Error parsing NAV 1%: {str(e)}")

        return nav_data

    def scrape_organization(self, adoszam: str) -> Dict[str, Any]:
        """
        Complete scraping workflow for a single organization (by tax number)

        Args:
            adoszam: Tax number to search and scrape

        Returns:
            Dictionary with all scraped data
        """
        org_data = {
            'search_adoszam': adoszam,
            'scraped_at': datetime.now().isoformat(),
            'organization_id': None,
            'alapadatok': {},
            'nav_1_percent': {},
            'error': None
        }

        try:
            # Step 1: Search for organization by tax number
            org_id = self.search_organization_by_adoszam(adoszam)
            if not org_id:
                raise Exception("Organization not found in search results")

            org_data['organization_id'] = org_id

            # Step 2: Fetch profile page
            html = self.fetch_profile(org_id)

            # Step 3: Parse Alapadatok tab
            org_data['alapadatok'] = self.parse_alapadatok(html)

            # Step 4: Parse NAV 1% tab
            org_data['nav_1_percent'] = self.parse_nav_1_percent(html)

            safe_print(f"[OK] Successfully scraped tax number: {adoszam}")

        except Exception as e:
            error_msg = str(e)
            org_data['error'] = error_msg
            safe_print(f"[FAIL] Failed to scrape tax number: {adoszam} - {error_msg}")

        return org_data

    def _save_individual_file(self, org_data: Dict[str, Any], output_folder: str):
        """
        Save individual organization data to a separate JSON file

        Args:
            org_data: Organization data dictionary
            output_folder: Folder path to save the file
        """
        try:
            # Get organization name from alapadatok
            org_name = org_data.get('alapadatok', {}).get('azonosito_adatok', {}).get('teljes_nev', 'unknown')
            if not org_name or org_name == 'unknown':
                org_name = f"org_{org_data.get('search_adoszam', 'no_tax')}"

            org_id = org_data.get('organization_id', 'no_id')
            adoszam = org_data.get('search_adoszam', 'no_tax')

            # Remove special characters and limit length
            safe_name = re.sub(r'[^\w\s-]', '', org_name)
            safe_name = re.sub(r'[-\s]+', '_', safe_name)
            safe_name = safe_name[:100]  # Limit filename length

            # Create filename with tax number and ID to ensure uniqueness
            filename = f"{safe_name}_{adoszam}_{org_id}.json"
            filepath = os.path.join(output_folder, filename)

            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(org_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            safe_print(f"Warning: Failed to save individual file for {org_data.get('search_adoszam')}: {str(e)}")

    def scrape_all(self, adoszam_list: List[str], delay: float = 1.5, output_folder: Optional[str] = None) -> Dict[str, Any]:
        """
        Scrape multiple organizations with progress tracking

        Args:
            adoszam_list: List of tax numbers
            delay: Delay between requests in seconds (default 1.5)
            output_folder: Optional folder path to save individual JSON files for each organization

        Returns:
            Dictionary with all results and metadata
        """
        # Create output folder if specified
        if output_folder:
            os.makedirs(output_folder, exist_ok=True)
            safe_print(f"Individual files will be saved to: {output_folder}")

        start_time = datetime.now()
        results = {
            'organizations': [],
            'metadata': {
                'total_organizations': len(adoszam_list),
                'successful_scrapes': 0,
                'failed_scrapes': 0,
                'scrape_started': start_time.isoformat(),
                'scrape_completed': None
            }
        }

        safe_print(f"\n{'='*60}")
        safe_print(f"Starting scrape of {len(adoszam_list)} organizations (by tax number)")
        safe_print(f"{'='*60}\n")

        for i, adoszam in enumerate(adoszam_list, 1):
            safe_print(f"[{i}/{len(adoszam_list)}] Processing tax number: {adoszam}")

            # Scrape organization
            org_data = self.scrape_organization(adoszam)
            results['organizations'].append(org_data)

            # Save individual file if output folder specified
            if output_folder:
                self._save_individual_file(org_data, output_folder)

            # Update counters
            if org_data.get('error'):
                results['metadata']['failed_scrapes'] += 1
            else:
                results['metadata']['successful_scrapes'] += 1

            # Rate limiting (except for last item)
            if i < len(adoszam_list):
                time.sleep(delay)

        # Update completion time
        end_time = datetime.now()
        results['metadata']['scrape_completed'] = end_time.isoformat()
        duration = (end_time - start_time).total_seconds()

        safe_print(f"\n{'='*60}")
        safe_print(f"Scraping completed!")
        safe_print(f"Duration: {duration:.1f} seconds")
        safe_print(f"Successful: {results['metadata']['successful_scrapes']}")
        safe_print(f"Failed: {results['metadata']['failed_scrapes']}")
        safe_print(f"{'='*60}\n")

        return results


def load_tax_numbers(filepath: str) -> List[str]:
    """
    Load tax numbers from text file

    Args:
        filepath: Path to text file with tax numbers (one per line)

    Returns:
        List of tax numbers
    """
    tax_numbers = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            tax_num = line.strip()
            # Remove line numbers if present (e.g., "1→12345678" becomes "12345678")
            tax_num = re.sub(r'^\d+→', '', tax_num)
            if tax_num and tax_num.isdigit():
                tax_numbers.append(tax_num)
    return tax_numbers


def save_results(data: Dict[str, Any], output_file: str):
    """
    Save scraped data to JSON file

    Args:
        data: Dictionary with scraped data
        output_file: Path to output JSON file
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    safe_print(f"Results saved to: {output_file}")


def log_errors(results: Dict[str, Any], log_file: str):
    """
    Save error log for failed scrapes

    Args:
        results: Dictionary with all scraping results
        log_file: Path to error log file
    """
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"Scraping Error Log (Tax Number Search)\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"{'='*60}\n\n")

        failed_count = 0
        for org in results['organizations']:
            if org.get('error'):
                failed_count += 1
                f.write(f"Tax Number: {org['search_adoszam']}\n")
                f.write(f"Error: {org['error']}\n")
                f.write(f"Timestamp: {org['scraped_at']}\n")
                f.write(f"{'-'*60}\n\n")

        if failed_count == 0:
            f.write("No errors occurred during scraping.\n")

    safe_print(f"Error log saved to: {log_file}")
