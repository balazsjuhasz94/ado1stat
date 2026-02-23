"""
Pre-compute city radius data for the dashboard city search page.
Parses cities from szekhely, geocodes them via Nominatim, finds orgs within 10km.
Output: data/city_radius_data.json

Usage: python scripts/visualization/precompute_city_data.py
"""

import json
import os
import re
import sys
import time
from math import radians, cos, sin, asin, sqrt

from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
ORGS_DIR = os.path.join(PROJECT_ROOT, 'organizations_by_adoszam')
CACHE_FILE = os.path.join(DATA_DIR, 'city_geocode_cache.json')
OUTPUT_FILE = os.path.join(DATA_DIR, 'city_radius_data.json')


def parse_city_from_szekhely(szekhely):
    """Extract city name from szekhely string.
    Format: '{4-digit ZIP} {CITY} {STREET_NAME} {STREET_TYPE} {NUMBER}'
    Hungarian cities are typically a single word after the ZIP code.
    The next words are usually the street name, not part of the city.
    """
    if not szekhely or szekhely == 'Nincs adat':
        return None

    szekhely = szekhely.strip()

    # Match 4-digit ZIP at start
    m = re.match(r'^(\d{4})\s+(.+)$', szekhely)
    if not m:
        return None

    rest = m.group(2).strip()
    tokens = rest.split()
    if not tokens:
        return None

    # The city is the first word after the ZIP code.
    # Exception: some cities have a Roman numeral district suffix (e.g., "BUDAPEST XI.")
    # or a compound name with a hyphen (e.g., "HAJDÚ-BIHAR" - but that's a county, not a city)
    city = tokens[0].upper().rstrip('.,;:')

    # Skip Roman numeral district indicators that follow Budapest
    # (they are not separate cities)

    return city if city and len(city) >= 2 else None


def haversine_km(lat1, lon1, lat2, lon2):
    """Haversine distance in kilometers."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))


def load_geocode_cache():
    """Load cached geocoding results."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_geocode_cache(cache):
    """Save geocoding cache."""
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def main():
    print("=" * 60)
    print("TELEPÜLÉS ADATOK ELŐSZÁMÍTÁSA")
    print("=" * 60)

    # Step 1: Load all org data
    print("\n1. Szervezetek betöltése...")
    orgs = []  # list of {adoszam, city, lat, lon}
    json_files = [f for f in os.listdir(ORGS_DIR) if f.endswith('.json')]
    print(f"   {len(json_files)} JSON fájl")

    for i, filename in enumerate(json_files):
        if (i + 1) % 2000 == 0:
            print(f"   Feldolgozás: {i + 1}/{len(json_files)}...")

        filepath = os.path.join(ORGS_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if data.get('error'):
                continue

            azonosito = data.get('alapadatok', {}).get('azonosito_adatok', {})
            adoszam = data.get('search_adoszam', '')
            szekhely = azonosito.get('székhely_címe', '')
            x_str = azonosito.get('x_koordináta', '')
            y_str = azonosito.get('y_koordináta', '')

            lat = float(x_str) if x_str else None
            lon = float(y_str) if y_str else None
            city = parse_city_from_szekhely(szekhely)

            orgs.append({
                'adoszam': adoszam,
                'city': city,
                'lat': lat,
                'lon': lon,
            })
        except Exception as e:
            pass

    print(f"   {len(orgs)} szervezet betöltve")
    with_coords = [o for o in orgs if o['lat'] is not None and o['lon'] is not None]
    print(f"   {len(with_coords)} koordinátával rendelkezik")

    # Step 2: Extract unique cities
    print("\n2. Települések kinyerése...")
    city_counts = {}
    for o in orgs:
        if o['city']:
            city_counts[o['city']] = city_counts.get(o['city'], 0) + 1

    print(f"   {len(city_counts)} egyedi település")
    # Show top 15
    top_cities = sorted(city_counts.items(), key=lambda x: -x[1])[:15]
    for city, count in top_cities:
        print(f"     {city}: {count}")

    # Step 3: Geocode cities
    print("\n3. Települések geokódolása (Nominatim)...")
    cache = load_geocode_cache()
    cities_to_geocode = [c for c in city_counts if c not in cache]
    print(f"   {len(cache)} már a cache-ben, {len(cities_to_geocode)} geokódolandó")

    if cities_to_geocode:
        geolocator = Nominatim(user_agent="ado1_civil_dashboard_precompute")
        geocode_fn = RateLimiter(geolocator.geocode, min_delay_seconds=1.1)

        for i, city in enumerate(cities_to_geocode):
            if (i + 1) % 50 == 0 or i == 0:
                print(f"   Geokódolás: {i + 1}/{len(cities_to_geocode)} ({city})...")

            try:
                location = geocode_fn(f"{city}, Magyarország", language='hu')
                if location:
                    cache[city] = {'lat': location.latitude, 'lon': location.longitude}
                else:
                    cache[city] = None  # Mark as failed
            except Exception as e:
                print(f"   HIBA {city}: {e}")
                cache[city] = None

            # Save cache every 100 cities
            if (i + 1) % 100 == 0:
                save_geocode_cache(cache)

        save_geocode_cache(cache)
        print(f"   Geokódolás kész, cache mentve")

    geocoded = {city: coords for city, coords in cache.items() if coords is not None}
    failed = [city for city, coords in cache.items() if coords is None]
    print(f"   Sikeres: {len(geocoded)}, Sikertelen: {len(failed)}")
    if failed[:10]:
        print(f"   Sikertelen példák: {', '.join(failed[:10])}")

    # Step 4: Compute 10km radius membership
    print("\n4. 10 km-es körzet számítása...")
    city_radius_data = {}

    for ci, (city, coords) in enumerate(geocoded.items()):
        if (ci + 1) % 100 == 0:
            print(f"   Település: {ci + 1}/{len(geocoded)}...")

        city_lat = coords['lat']
        city_lon = coords['lon']
        nearby_adoszamok = []

        for o in with_coords:
            dist = haversine_km(city_lat, city_lon, o['lat'], o['lon'])
            if dist <= 10.0:
                nearby_adoszamok.append(o['adoszam'])

        if nearby_adoszamok:
            city_radius_data[city] = {
                'lat': city_lat,
                'lon': city_lon,
                'org_count': len(nearby_adoszamok),
                'adoszamok': nearby_adoszamok,
            }

    print(f"   {len(city_radius_data)} település legalább 1 szervezettel a körzetben")

    # Stats
    org_counts = [d['org_count'] for d in city_radius_data.values()]
    if org_counts:
        print(f"   Min/Max/Medián szervezetszám: {min(org_counts)}/{max(org_counts)}/{sorted(org_counts)[len(org_counts)//2]}")

    # Step 5: Save
    print(f"\n5. Mentés: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(city_radius_data, f, ensure_ascii=False, indent=2)

    print("\nKÉSZ!")
    print(f"  Települések: {len(city_radius_data)}")
    print(f"  Fájl: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
