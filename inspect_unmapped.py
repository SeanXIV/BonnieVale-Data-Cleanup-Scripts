from clean_and_split import read_csv_with_multiline
from collections import defaultdict

headers, super_headers, rows = read_csv_with_multiline("2024 JGT Cohort - 2024 Cohort.csv")

# Identify unmapped based on latest mapping
mapped = set([
    # Table 1
    'Photo','Name','Surname','Address','Contact #','Parent Details','Comments',
    'Applicant Details','Family Details','ID','Bank Account','SARS Number','Learners / Licence',
    # Table 2
    'Career Options','Academic Grouping','YearBeyond Recommendation','Pathways Recommendation',
    'Absent from School','Absentee rating','School WR rating','School WR rating roundup',
    'CV','Study Application','W4AL course','Skills',
    # Table 3
    'Intro Session attended','Info Form received','Info Form returned','Mentor session attended',
    'Visits to Office','Communication WhatsApp','Communication Facebook','#responses','Info session attended',
    # Key
    'ID Number',
    # Placeholders handled separately
    'R1','R2','R3',
])

unmapped = []
for i,h in enumerate(headers):
    if h not in mapped and h not in ('R1','R2','R3'):
        unmapped.append((i,h))

print("Unmapped columns and sample values:")
for i,h in unmapped:
    # collect up to 5 distinct non-empty samples
    seen = []
    for d in rows:
        v = str(d.get(h, '')).strip()
        if v and v not in seen:
            seen.append(v)
        if len(seen)>=5:
            break
    print(f"[{i}] header='{h or '<EMPTY>'}' samples={seen}")

print("\nSuper headers aligned:")
for i,h in unmapped:
    sh = super_headers[i] if i < len(super_headers) else ''
    print(f"[{i}] super='{sh}'")

