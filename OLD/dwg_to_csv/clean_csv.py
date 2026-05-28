import csv
from collections import Counter

path = r'C:\Users\HOME\Desktop\אלי ספרא\data\961-MGR-332-1-140426.csv'
with open(path, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    headers = reader.fieldnames
    rows = list(reader)

total = len(rows)
print("=== BEFORE ===")
print(f"Rows: {total}, Cols: {len(headers)}")
print()

# Classify columns
numeric_cols = {'VertexIndex','VertexCount','X','Y','Z','Length_m','Area_sqm','Radius','Bulge','Rotation'}

# Count missing per column
missing = {}
for h in headers:
    count = sum(1 for r in rows if r[h].strip() == '')
    pct = count / total * 100
    ctype = "numeric" if h in numeric_cols else "categorical"
    missing[h] = (count, pct)
    print(f"  {h:20s} | missing: {count:5d} ({pct:5.1f}%) | type: {ctype}")

# Columns to delete (>50% missing)
to_delete = [h for h in headers if missing[h][1] > 50]
print(f"\n--- Columns DELETED (>50% missing): {to_delete}")

# Columns to keep
kept = [h for h in headers if h not in to_delete]

# Fill missing values
print("\n--- FILLING missing values:")
for h in kept:
    if missing[h][0] == 0:
        continue
    if h in numeric_cols:
        vals = [float(r[h]) for r in rows if r[h].strip() != '']
        if vals:
            mean_val = round(sum(vals)/len(vals), 3)
            filled = missing[h][0]
            for r in rows:
                if r[h].strip() == '':
                    r[h] = str(mean_val)
            print(f"  {h:20s} | filled {filled} with mean={mean_val}")
    else:
        vals = [r[h] for r in rows if r[h].strip() != '']
        if vals:
            mode_val = Counter(vals).most_common(1)[0][0]
            filled = missing[h][0]
            for r in rows:
                if r[h].strip() == '':
                    r[h] = mode_val
            print(f"  {h:20s} | filled {filled} with mode='{mode_val}'")

# After cleaning - verify
print(f"\n=== AFTER ===")
print(f"Rows: {len(rows)}, Cols: {len(kept)}")
for h in kept:
    count = sum(1 for r in rows if r[h].strip() == '')
    print(f"  {h:20s} | missing: {count}")

# Save cleaned CSV
out_path = r'C:\Users\HOME\Desktop\אלי ספרא\data\961-MGR-332-1-140426_cleaned.csv'
with open(out_path, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=kept, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)
print(f"\nSAVED: {out_path}")
