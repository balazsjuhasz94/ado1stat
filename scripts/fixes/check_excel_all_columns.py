import pandas as pd
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Read with row 1 as header
df = pd.read_excel('Szja 1-os felajanlasban reszesult civil kedvezmenyezettek_2025.xlsx', sheet_name='Munka1', header=1)
print(f"Total columns: {len(df.columns)}")
print("\nAll column names:")
for i, col in enumerate(df.columns):
    print(f"  {i}: '{col}'")
