import pandas as pd
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

df = pd.read_excel('Szja 1-os felajanlasban reszesult civil kedvezmenyezettek_2025.xlsx', sheet_name='Munka1')
print("Column names:")
for col in df.columns[:15]:
    print(f"  '{col}'")