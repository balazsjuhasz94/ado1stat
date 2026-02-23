"""
Fill missing x,y coordinates for orgs that have székhely but no coordinates.
Geocodes via Nominatim using the full address string.
Updates the JSON files in organizations_by_adoszam/.

Usage: python scripts/visualization/fill_missing_coordinates.py
"""

import json
import os
import sys
import time

from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
ORGS_DIR = os.path.join(PROJECT_ROOT, 'organizations_by_adoszam')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
CACHE_FILE = os.path.join(DATA_DIR, 'address_geocode_cache.json')


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def main():
    print("=" * 60)
    print("HIÁNYZÓ KOORDINÁTÁK KITÖLTÉSE SZÉKHELY ALAPJÁN")
    print("=" * 60)

    # Step 1: Find orgs missing coordinates
    print("\n1. Szervezetek keresése koordináta nélkül...")
    missing = []  # list of (filepath, data, szekhely)
    json_files = [f for f in os.listdir(ORGS_DIR) if f.endswith('.json')]

    for filename in json_files:
        filepath = os.path.join(ORGS_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if data.get('error'):
                continue

            azonosito = data.get('alapadatok', {}).get('azonosito_adatok', {})
            x_str = azonosito.get('x_koordináta', '')
            y_str = azonosito.get('y_koordináta', '')
            szekhely = azonosito.get('székhely_címe', '')

            has_coords = bool(x_str and y_str)
            has_szekhely = bool(szekhely and szekhely != 'Nincs adat')

            if not has_coords and has_szekhely:
                missing.append((filepath, data, szekhely))
        except Exception:
            pass

    print(f"   {len(missing)} szervezet koordináta nélkül, de székhellyel")

    if not missing:
        print("   Nincs teendő!")
        return

    # Step 2: Geocode addresses
    print("\n2. Címek geokódolása (Nominatim)...")
    cache = load_cache()
    to_geocode = [(fp, data, sz) for fp, data, sz in missing if sz not in cache]
    already_cached = len(missing) - len(to_geocode)
    print(f"   {already_cached} már a cache-ben, {len(to_geocode)} geokódolandó")

    if to_geocode:
        geolocator = Nominatim(user_agent="ado1_civil_fill_coords")
        geocode_fn = RateLimiter(geolocator.geocode, min_delay_seconds=1.1)

        for i, (fp, data, szekhely) in enumerate(to_geocode):
            if (i + 1) % 50 == 0 or i == 0:
                print(f"   Geokódolás: {i + 1}/{len(to_geocode)} ({szekhely[:40]})...")

            try:
                # Try full address first
                query = f"{szekhely}, Magyarország"
                location = geocode_fn(query, language='hu')

                if not location:
                    # Fallback: try just ZIP + city (first two tokens)
                    tokens = szekhely.strip().split()
                    if len(tokens) >= 2:
                        short_query = f"{tokens[0]} {tokens[1]}, Magyarország"
                        location = geocode_fn(short_query, language='hu')

                if location:
                    cache[szekhely] = {'lat': location.latitude, 'lon': location.longitude}
                else:
                    cache[szekhely] = None
            except Exception as e:
                print(f"   HIBA: {szekhely[:40]} - {e}")
                cache[szekhely] = None

            # Save cache every 100
            if (i + 1) % 100 == 0:
                save_cache(cache)

        save_cache(cache)

    success = sum(1 for sz in [m[2] for m in missing] if cache.get(sz) is not None)
    failed = sum(1 for sz in [m[2] for m in missing] if cache.get(sz) is None)
    print(f"   Sikeres: {success}, Sikertelen: {failed}")

    # Step 3: Update JSON files
    print("\n3. JSON fájlok frissítése...")
    updated = 0
    for filepath, data, szekhely in missing:
        coords = cache.get(szekhely)
        if coords is None:
            continue

        azonosito = data['alapadatok']['azonosito_adatok']
        azonosito['x_koordináta'] = str(coords['lat'])
        azonosito['y_koordináta'] = str(coords['lon'])

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        updated += 1

    print(f"   {updated} fájl frissítve koordinátákkal")

    # Show some failed examples
    failed_examples = [sz for sz in [m[2] for m in missing] if cache.get(sz) is None][:10]
    if failed_examples:
        print(f"\n   Sikertelen példák:")
        for sz in failed_examples:
            print(f"     - {sz}")

    print("\nKÉSZ!")


if __name__ == '__main__':
    main()
