import csv
import re
from clean_and_split import read_csv_with_multiline

INPUT = "2024 JGT Cohort - 2024 Cohort.csv"

# Helper to normalize multi-line/space differences
ws_re = re.compile(r"\s+")
def norm(s: str) -> str:
    return ws_re.sub(" ", (s or "").strip())

# Load input as dicts (two headers handled by helper)
headers, super_headers, in_rows = read_csv_with_multiline(INPUT)

# Load outputs (preserve row order)
with open("outputs/table_personal_parent.csv", newline="", encoding="utf-8") as f1:
    r1 = list(csv.DictReader(f1))
with open("outputs/table_study_support.csv", newline="", encoding="utf-8") as f2:
    r2 = list(csv.DictReader(f2))
with open("outputs/table_engagement_progress.csv", newline="", encoding="utf-8") as f3:
    r3 = list(csv.DictReader(f3))

assert len(r1)==len(in_rows)==len(r2)==len(r3), "Row count mismatch"

# Define fields that should be direct copies (no transformation) and their target table/field names
checks = [
    ("personal_parent", "Name", "Name"),
    ("personal_parent", "Surname", "Surname"),
    ("personal_parent", "Address", "Address"),
    ("personal_parent", "Photo", "Photo"),
    ("personal_parent", "Applicant Details", "Applicant Details"),
    ("personal_parent", "Family Details", "Family Details"),
    ("personal_parent", "ID", "ID Document"),
    ("personal_parent", "Bank Account", "Bank Account"),
    ("personal_parent", "SARS Number", "SARS Number"),
    ("personal_parent", "Learners / Licence", "Learners / Licence"),
    ("study_support", "Career Options", "Career Options/Study Details"),  # may fallback to Study Details; allow contains
    ("study_support", "Academic Grouping", "Academic Grouping"),
    ("study_support", "CV", "CV"),
    ("study_support", "Study Application", "Study Application"),
    ("study_support", "W4AL course", "W4AL course"),
    ("study_support", "Skills", "Skills"),
    ("study_support", "Absent from School", "Absent from School"),
    ("study_support", "Absentee rating", "Absentee rating"),
    ("study_support", "School WR rating", "School WR rating"),
    ("study_support", "School WR rating roundup", "School WR rating roundup"),
    ("study_support", "Unnamed", "Academic Details 1"),
    ("study_support", "Unnamed_2", "Academic Details 2"),
    ("engagement_progress", "Intro Session attended", "Intro Session attended"),
    ("engagement_progress", "Info session attended", "Info session attended"),
    ("engagement_progress", "Info Form received", "Info Form received"),
    ("engagement_progress", "Info Form returned", "Info Form returned"),
    ("engagement_progress", "Mentor session attended", "Mentor session attended"),
    ("engagement_progress", "Visits to Office", "Visits to Office"),
    ("engagement_progress", "Communication WhatsApp", "Communication WhatsApp"),
    ("engagement_progress", "Communication Facebook", "Communication Facebook"),
    ("engagement_progress", "#responses", "#responses"),
    ("engagement_progress", "ro", "ro"),
    ("engagement_progress", "Datapoints", "Datapoints"),
]

mismatches = []
for i in range(len(in_rows)):
    d = in_rows[i]
    o1 = r1[i]
    o2 = r2[i]
    o3 = r3[i]
    for tbl, src, dst in checks:
        src_val = norm(d.get(src, ""))
        if tbl=="personal_parent":
            out_val = norm(o1.get(dst, ""))
            # Career Options/Study Details is a special case, skip here
        elif tbl=="study_support":
            out_val = norm(o2.get(dst, ""))
            # For Career Options/Study Details: allow output to contain source
            if dst=="Career Options/Study Details":
                # If source exists, it must be contained in output (output may include fallback)
                if src_val and src_val not in out_val:
                    mismatches.append((i, tbl, src, dst, src_val, out_val))
                    continue
                else:
                    continue
        else:
            out_val = norm(o3.get(dst, ""))
        if src_val != out_val:
            mismatches.append((i, tbl, src, dst, src_val, out_val))

print("Rows:", len(in_rows))
print("Direct-field mismatches:", len(mismatches))
if mismatches:
    # Show up to 10 examples
    for m in mismatches[:10]:
        i, tbl, src, dst, a, b = m
        print(f"Row {i+1}: {tbl} {src} -> {dst}\n  input='{a}'\n  output='{b}'")
else:
    print("All direct copy fields match between input and outputs (allowing whitespace normalization).")

