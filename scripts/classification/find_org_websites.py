"""
Find official websites for the top 1000 civil organizations using Claude Haiku with web search.
Results are saved to data/org_websites_top1000.csv.
Resumable: can be stopped and restarted without re-processing already completed orgs.

Usage:
    python scripts/classification/find_org_websites.py

Estimated cost: ~$13 for 1000 organizations
Estimated time: ~35 minutes
"""

import json
import os
import re
import sys
import time
import pandas as pd
from anthropic import Anthropic

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(BASE_DIR, 'data')
ORGS_DIR = os.path.join(BASE_DIR, 'organizations_by_adoszam')
CSV_PATH = os.path.join(DATA_DIR, 'organization_categories_ALL_10000.csv')
EXCEL_PATH = os.path.join(DATA_DIR, 'Szja 1-os felajanlasban reszesult civil kedvezmenyezettek_2025.xlsx')
API_KEY_PATH = os.path.join(DATA_DIR, 'api.txt')
LOG_PATH = os.path.join(DATA_DIR, 'org_websites_log.jsonl')
RESULTS_PATH = os.path.join(DATA_DIR, 'org_websites_top1000.csv')

# Domains to reject (not actual org websites)
BLOCKED_DOMAINS = [
    'facebook.com', 'instagram.com', 'twitter.com', 'x.com',
    'youtube.com', 'tiktok.com', 'linkedin.com',
    'civil.info.hu', 'nav.gov.hu', 'birosag.hu',
    'nonprofit.hu', 'magyarorszag.hu', 'kormany.hu',
    'wikipedia.org', 'google.com',
]

TOP_N = 1000


def load_api_key():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and os.path.exists(API_KEY_PATH):
        with open(API_KEY_PATH, 'r') as f:
            api_key = f.read().strip()
    if not api_key:
        raise ValueError("No ANTHROPIC_API_KEY found (set env var or put it in data/api.txt)")
    return api_key


def get_top_orgs(n):
    """Load top N organizations by donation amount."""
    df_cats = pd.read_csv(CSV_PATH)

    df_excel = pd.read_excel(EXCEL_PATH, sheet_name='Munka1', header=1)
    df_excel['összeg'] = pd.to_numeric(df_excel['Felajánlott összeg (Ft)'], errors='coerce').fillna(0).astype(int)
    df_amounts = df_excel[['Adószám', 'összeg']].copy()

    df = df_cats.merge(df_amounts, on='Adószám', how='left')
    df['összeg'] = df['összeg'].fillna(0).astype(int)

    df = df.sort_values('összeg', ascending=False).head(n)

    print(f"Top {n} orgs: {df['összeg'].iloc[0]:,} Ft (max) → {df['összeg'].iloc[-1]:,} Ft (min)")

    return df


def get_org_purpose(adoszam):
    """Try to load purpose from JSON file."""
    for fn in os.listdir(ORGS_DIR):
        if fn.startswith(f'org_{adoszam}') and fn.endswith('.json'):
            path = os.path.join(ORGS_DIR, fn)
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            fonadatok = data.get('alapadatok', {}).get('fonadatok', {})
            return fonadatok.get('céljának_leírása', '')
    return ''


def is_blocked_url(url):
    """Check if URL is from a blocked domain."""
    url_lower = url.lower()
    for domain in BLOCKED_DOMAINS:
        if domain in url_lower:
            return True
    return False


def extract_url(text):
    """Extract the first valid URL from response text."""
    urls = re.findall(r'https?://[^\s<>"\')\]]+', text)
    for url in urls:
        url = url.rstrip('.,;:!?)')
        if not is_blocked_url(url):
            return url
    return None


def find_website(client, org_name, city, purpose):
    """
    Use Claude Haiku with web search to find an organization's website.
    Returns (url or None, searched_bool).
    """
    system_prompt = """Te egy magyar civil szervezet weboldal kereső vagy.
A feladatod: megtalálni a szervezet SAJÁT HIVATALOS weboldalát.

SZABÁLYOK:
1. Keress rá a szervezet nevére a weben.
2. Csak a szervezet SAJÁT weboldalát add vissza (pl. https://szervezet.hu).
3. NE adj vissza Facebook, Instagram, YouTube, vagy más közösségi média oldalt.
4. NE adj vissza kormányzati nyilvántartó oldalakat (civil.info.hu, nav.gov.hu, birosag.hu).
5. NE adj vissza Wikipedia vagy híroldal cikkeket.
6. Ha a szervezetnek NINCS saját weboldala, válaszolj: NINCS

VÁLASZ FORMÁTUM:
URL: [a weboldal címe, pl. https://example.hu]
vagy
URL: NINCS"""

    purpose_text = f"\nCél: {purpose[:200]}" if purpose else ""
    user_msg = f"Keresd meg ennek a szervezetnek a weboldalát:\n\nNév: {org_name}\nSzékhely: {city}{purpose_text}"

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            temperature=0,
            system=system_prompt,
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 2
            }],
            messages=[{"role": "user", "content": user_msg}]
        )

        searched = False
        result_text = ""
        for block in response.content:
            if block.type == "text":
                result_text += block.text
            elif block.type == "web_search_tool_use":
                searched = True

        # Check for NINCS
        if "NINCS" in result_text.upper():
            return None, searched

        # Extract URL
        url = extract_url(result_text)
        return url, searched

    except Exception as e:
        print(f"   HIBA: {e}")
        return None, False


def load_processed():
    """Load already-processed adoszams from log file."""
    processed = {}
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    processed[str(entry['adoszam'])] = entry
                except json.JSONDecodeError:
                    continue
    return processed


def save_results(df_top, processed):
    """Save results CSV from processed data."""
    print("\n" + "=" * 70)
    print("ÖSSZEFOGLALÓ")
    print("=" * 70)

    results = []
    for _, row in df_top.iterrows():
        adoszam = str(row['Adószám'])
        entry = processed.get(adoszam, {})
        results.append({
            'Adószám': adoszam,
            'Szervezet neve': row['Szervezet neve'],
            'Összeg': row['összeg'],
            'URL': entry.get('url', ''),
        })

    df_results = pd.DataFrame(results)
    df_results.to_csv(RESULTS_PATH, index=False, encoding='utf-8-sig')

    found = sum(1 for r in results if r['URL'])
    not_found = sum(1 for r in results if not r['URL'])
    processed_count = sum(1 for r in results if str(r['Adószám']) in processed)

    print(f"Feldolgozva: {processed_count}/{len(results)}")
    print(f"Weboldal talált: {found}")
    print(f"Nincs weboldal: {not_found}")

    if found > 0:
        print(f"\nPélda találatok:")
        shown = 0
        for r in results:
            if r['URL']:
                print(f"  {r['Szervezet neve'][:50]} → {r['URL']}")
                shown += 1
                if shown >= 5:
                    break

    print(f"\nEredmények mentve: {RESULTS_PATH}")
    print(f"Részletes log: {LOG_PATH}")


def main():
    print("=" * 70)
    print("CIVIL SZERVEZETEK WEBOLDAL KERESÉS")
    print(f"Top {TOP_N} szervezet — Claude Haiku + Web Search")
    print("=" * 70)

    api_key = load_api_key()
    print(f"API kulcs betöltve (...{api_key[-8:]})")
    client = Anthropic(api_key=api_key)

    print(f"\nTop {TOP_N} szervezet betöltése...")
    df_top = get_top_orgs(TOP_N)
    print(f"{len(df_top)} szervezet betöltve")

    processed = load_processed()
    if processed:
        print(f"{len(processed)} szervezet már feldolgozva (folytatás)")

    remaining = df_top[~df_top['Adószám'].astype(str).isin(processed.keys())]
    total_remaining = len(remaining)
    total_all = len(df_top)
    print(f"{total_remaining} szervezet feldolgozandó")

    if total_remaining == 0:
        print("\nMinden szervezet már feldolgozva!")
        save_results(df_top, processed)
        return

    found_count = sum(1 for p in processed.values() if p.get('url'))
    not_found_count = sum(1 for p in processed.values() if not p.get('url'))
    search_count = sum(1 for p in processed.values() if p.get('searched'))

    log_file = open(LOG_PATH, 'a', encoding='utf-8')

    try:
        for idx, (_, row) in enumerate(remaining.iterrows()):
            adoszam = str(row['Adószám'])
            name = row['Szervezet neve']
            city = str(row.get('Székhely', ''))
            amount = row['összeg']
            progress_num = len(processed) + 1

            purpose = get_org_purpose(adoszam)

            print(f"\n[{progress_num}/{total_all}] {name[:60]}")
            print(f"   Székhely: {city[:60]}  |  Összeg: {amount:,} Ft")

            url, searched = find_website(client, name, city, purpose)

            if url:
                found_count += 1
                print(f"   ✓ {url}")
            else:
                not_found_count += 1
                print(f"   ✗ Nincs weboldal")

            if searched:
                search_count += 1

            entry = {
                'adoszam': adoszam,
                'name': name,
                'city': city,
                'amount': amount,
                'url': url or '',
                'searched': searched,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            log_file.write(json.dumps(entry, ensure_ascii=False) + '\n')
            log_file.flush()
            processed[adoszam] = entry

            if progress_num % 50 == 0:
                print(f"\n   --- Összesítés: {progress_num}/{total_all} | "
                      f"Talált: {found_count} | Nem talált: {not_found_count} | "
                      f"Web keresés: {search_count} ---")

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n\n⚠️  Megszakítva! Az eddigi eredmények elmentve.")
        print(f"   Folytatáshoz futtasd újra: python {__file__}")
    finally:
        log_file.close()

    save_results(df_top, processed)


if __name__ == '__main__':
    main()
