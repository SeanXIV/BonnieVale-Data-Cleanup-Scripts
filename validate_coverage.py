from collections import Counter
from clean_and_split import read_csv_with_multiline
import csv

input_path = "2024 JGT Cohort - 2024 Cohort.csv"
headers, super_headers, rows = read_csv_with_multiline(input_path)

print("Input rows:", len(rows))
print("Header count:", len(headers))
print("First 12 headers:", headers[:12])

# Load outputs
import os
out_dir = "outputs"
files = [
    ("personal_parent", os.path.join(out_dir, "table_personal_parent.csv")),
    ("study_support", os.path.join(out_dir, "table_study_support.csv")),
    ("engagement_progress", os.path.join(out_dir, "table_engagement_progress.csv")),
]

out_headers = {}
for key, path in files:
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        out_headers[key] = next(r)

print("Output headers:")
for k,h in out_headers.items():
    print("-", k, "=>", h)

# Which input headers are used directly by outputs
used_input_headers = set()
# Direct usage from clean_and_split mapping
direct_fields = [
    # Core fields
    "Photo","Name","Surname","Address","Contact #","Parent Details","Comments",
    "Career Options","Academic Grouping","YearBeyond Recommendation","Pathways Recommendation",
    "Absent from School","Absentee rating","School WR rating","School WR rating roundup",
    "Intro Session attended","Info Form received","Info Form returned","Mentor session attended",
    "ID Number",
    # Newly mapped fields across tables
    "Applicant Details","Family Details","ID","Bank Account","SARS Number","Learners / Licence",
    "CV","Study Application","W4AL course","Skills",
    "Visits to Office","Communication WhatsApp","Communication Facebook","#responses","Info session attended",
    # Admin/placeholder and unlabeled academic columns now mapped
    "ro","Datapoints","Unnamed","Unnamed_2",
]
for h in headers:
    for df in direct_fields:
        if h.lower() == df.lower():
            used_input_headers.add(h)
            break

unused_headers = [h for h in headers if h not in used_input_headers and h not in ("R1","R2","R3")]

# Count non-empty cells in each unused header
counts = []
for h in unused_headers:
    non_empty = sum(1 for d in rows if str(d.get(h, "")).strip())
    counts.append((h, non_empty))
counts.sort(key=lambda x: -x[1])

print("\nColumns with data that are NOT currently represented in outputs (header => non-empty rows):")
for h, c in counts:
    if c>0:
        print(f"- {h} => {c}")

print("\nSummary:")
print("Total input columns:", len(headers))
print("Unused columns with some data:", sum(1 for _,c in counts if c>0))

