import yaml
import sys
import json

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

with open('categories.yaml', 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

print(f"Type: {type(data)}")
print(f"Length: {len(data)}")
print(f"\nFirst 3 items:")
for i, item in enumerate(data[:3]):
    print(f"\n{i}. Type: {type(item)}")
    if isinstance(item, dict):
        for key, value in item.items():
            print(f"   Key: {key}")
            print(f"   Value type: {type(value)}")
            if isinstance(value, list):
                print(f"   Value length: {len(value)}")
                print(f"   First few children: {value[:3]}")
    else:
        print(f"   Value: {item}")
