"""Create JSON files for organizations with scraping errors using Excel data"""
import pandas as pd
import json
import os
from datetime import datetime

# 1. Load error organizations
df_errors = pd.read_csv('scraping_errors_with_names.csv', encoding='utf-8-sig')
df_errors['Adószám'] = df_errors['Adószám'].astype(str)

print(f"Loaded {len(df_errors)} organizations with errors")

# 2. Load Excel data to get 2025 amounts and donor counts
excel_file = 'Szja 1-os felajanlasban reszesult civil kedvezmenyezettek_2025.xlsx'
df_excel = pd.read_excel(excel_file, sheet_name='Munka1', header=1)
df_excel['Adószám'] = df_excel['Adószám'].astype(str)

# 3. Merge to get all data
df_merged = df_errors.merge(
    df_excel[['Adószám', 'Név', 'Székhely', 'Felajánlott összeg (Ft)', 'Felajánlók száma (fő)']],
    on='Adószám',
    how='left'
)

print(f"Merged {len(df_merged)} organizations")

# 4. Create JSON files
output_folder = 'organizations_by_adoszam'
os.makedirs(output_folder, exist_ok=True)

timestamp = datetime.now().isoformat()
created_count = 0

for idx, row in df_merged.iterrows():
    adoszam = row['Adószám']
    org_name = row['Szervezet neve']
    szekhely = row.get('Székhely', '')
    osszeg = row.get('Felajánlott összeg (Ft)', 0)
    db = row.get('Felajánlók száma (fő)', 0)

    # Handle NaN values
    if pd.isna(szekhely):
        szekhely = ''
    if pd.isna(osszeg):
        osszeg = 0
    if pd.isna(db):
        db = 0

    # Format amount as string with " Ft" suffix
    osszeg_str = f"{int(osszeg):,} Ft".replace(',', ' ')

    # Create JSON structure
    json_data = {
        "search_adoszam": adoszam,
        "scraped_at": timestamp,
        "organization_id": None,
        "alapadatok": {
            "azonosito_adatok": {
                "teljes_név": org_name,
                "rövid_név": "",
                "székhely_ország": "Magyarország",
                "székhely_címe": szekhely,
                "x_koordináta": "",
                "y_koordináta": "",
                "adószám": adoszam,
                "adószám_állapota": "",
                "adószám_kiadásának_dátuma": "",
                "statisztikai_számjel": ""
            },
            "fonadatok": {
                "szervezet_típusa": "",
                "szervezet_célja_szerinti_besorolás": "",
                "céljának_leírása": "",  # Blank as requested
                "állapot": "",
                "nyilvantartási_száma": "",
                "régi_nyilvantartási_száma": "",
                "közhasznú_fokozata": "",
                "közhasznúsági_jogállás_jogerőre_emelkedésének_dátuma": "",
                "alapító_okirat_legutóbbi_módosításának_dátuma": "",
                "alkalmazottak_száma": "",
                "a_nyilvántartott_adatok_verziószáma": "",
                "a_verzió_bejegyzésének_dátuma": ""
            },
            "kepviselok": [],
            "eljarasok": [],
            "teaor": []
        },
        "nav_1_percent": {
            "kedvezmenyezett_adatok": [
                {
                    "Év": "2025",
                    "Érvényesen rendelkező magánszemélyek száma": str(int(db)),
                    "Az érvényes civil kedvezményezettet megillető szja 1% összege": osszeg_str
                }
            ],
            "kozlemenyek": [],
            "kizarasok": []
        },
        "error": None
    }

    # Save to file with same naming convention
    filename = f"org_{adoszam}_{adoszam}_None.json"
    filepath = os.path.join(output_folder, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    created_count += 1

    if (created_count) % 10 == 0:
        print(f"  Created {created_count}/{len(df_merged)} files...")

print(f"\n✅ Created {created_count} JSON files in '{output_folder}'")
print(f"\nSample organizations:")
for i in range(min(5, len(df_merged))):
    print(f"  - {df_merged.iloc[i]['Szervezet neve']}")
