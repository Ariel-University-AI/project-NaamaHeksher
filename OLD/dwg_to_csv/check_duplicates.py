import csv
from collections import Counter

path = r'C:\Users\HOME\Desktop\אלי ספרא\data\961-MGR-332-1-140426_cleaned.csv'
with open(path, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    headers = reader.fieldnames
    rows = list(reader)

total = len(rows)
print(f"Total rows: {total}")
print(f"Columns: {len(headers)}")

# Convert each row to a tuple for hashing
def row_key(r):
    return tuple(r[h] for h in headers)

# Count occurrences of each row
row_counts = Counter(row_key(r) for r in rows)

# Find duplicates (count > 1)
duplicates = {k: v for k, v in row_counts.items() if v > 1}

print(f"\nUnique rows: {len(row_counts)}")
print(f"Duplicate groups: {len(duplicates)}")
total_dup_rows = sum(v - 1 for v in duplicates.values())
print(f"Total duplicate rows (to remove): {total_dup_rows}")

if duplicates:
    print(f"\n{'='*80}")
    print(f"DUPLICATE ROWS DETAILS:")
    print(f"{'='*80}")
    for i, (key, count) in enumerate(sorted(duplicates.items(), key=lambda x: -x[1])):
        row_dict = dict(zip(headers, key))
        print(f"\n--- Duplicate group {i+1} (appears {count} times, removing {count-1}) ---")
        for h in headers:
            val = row_dict[h]
            if val:
                print(f"  {h:20s}: {val}")

# Remove duplicates, keep first
seen = set()
unique_rows = []
for r in rows:
    key = row_key(r)
    if key not in seen:
        seen.add(key)
        unique_rows.append(r)

print(f"\n{'='*80}")
print(f"BEFORE: {total} rows")
print(f"AFTER:  {len(unique_rows)} rows")
print(f"REMOVED: {total - len(unique_rows)} duplicate rows")

# Save
with open(path, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=headers)
    writer.writeheader()
    writer.writerows(unique_rows)
print(f"\nSaved cleaned file (overwritten): {path}")
