## BonnieVale Data Cleanup – Scripts Guide

### Overview
This repository contains scripts to clean and restructure the cohort spreadsheet into three linked tables without altering the original data. The processing is non-destructive: the original CSV remains unchanged and outputs are written to the outputs/ folder.

- Input: 2024 JGT Cohort - 2024 Cohort.csv (CSV with multi-line cells and a two-row header)
- Outputs:
  - outputs/table_personal_parent.csv
  - outputs/table_study_support.csv
  - outputs/table_engagement_progress.csv
- Linking key across tables: ID_Number (rows without an ID are kept with an empty key so no data is lost)

### Files
- clean_and_split.py
  - Main script that reads the CSV, parses and cleans fields (contacts, comments), uses the first super-header row to resolve blank headers, renames the last three columns to R1/R2/R3 in-memory, and writes the three output tables.
  - Now includes a CLI with options for input path, output directory, encoding, and verbose logging; non-destructive (original CSV is never modified).
- debug_comments.py
  - Small helper to preview how Comments and Contact parsing worked for the first few rows.
- validate_coverage.py
  - Verifies that every input column (including grouped/unlabeled) is represented across the output tables.
- validate_correctness.py
  - Verifies that direct-copy fields match between input and outputs, and that row counts are preserved.

### Requirements
- Python 3.8+ (standard library only; no external packages required)
- Windows PowerShell or any terminal

### Quick Start (cross‑platform)
1) Prerequisite: Python 3.8+
   - Check your version:
     - Windows/PowerShell: python --version
     - macOS/Linux (sometimes python3): python3 --version

2) Open a terminal and change to this project folder:
   - Windows/PowerShell: cd "path\\to\\project"
   - macOS/Linux: cd path/to/project

3) Run the cleaner (it creates the output folder if missing):
   - Basic run (writes to outputs/ in this folder):
     - Windows: python clean_and_split.py "path\\to\\input.csv"
     - macOS/Linux: python3 clean_and_split.py "path/to/input.csv"
   - Verbose logs + custom output folder (recommended):
     - Windows: python clean_and_split.py -v -o outputs_run1 "path\\to\\input.csv"
     - macOS/Linux: python3 clean_and_split.py -v -o outputs_run1 "path/to/input.csv"
   - If the file uses a specific encoding (e.g., utf-8):
     - python[3] clean_and_split.py -v --encoding utf-8 -o outputs_utf8 "path/to/input.csv"

4) Check the outputs in the chosen output folder (e.g., outputs_run1/):
   - table_personal_parent.csv
   - table_study_support.csv
   - table_engagement_progress.csv

5) Re-run/refresh outputs
   - Reuse the same folder (files get overwritten), or choose a new folder name to keep runs side‑by‑side.
   - Timestamped folder examples:
     - Windows/PowerShell:
       - $ts = Get-Date -Format "yyyyMMdd_HHmmss"
       - python clean_and_split.py -v -o "outputs_$ts" "path\\to\\input.csv"
     - macOS/Linux (bash/zsh):
       - ts=$(date +%Y%m%d_%H%M%S)
       - python3 clean_and_split.py -v -o "outputs_$ts" "path/to/input.csv"

6) Batch process multiple CSVs (optional)
   - Windows/PowerShell:
     - Get-ChildItem .\data -Filter *.csv | ForEach-Object { $name = $_.BaseName; python clean_and_split.py -v -o "outputs_$name" $_.FullName }
   - macOS/Linux (bash/zsh):
     - for f in data/*.csv; do name=$(basename "$f" .csv); python3 clean_and_split.py -v -o "outputs_$name" "$f"; done

### What the cleaner does

#### Header handling and column naming
- The CSV has a two-row header:
  - Row 1: super header labels (e.g., Comments, Study Details, Support, Additional Support, Work Readiness Criteria)
  - Row 2: column-level headers (some cells are blank)
- The script fills blank header cells using the corresponding label from the super header row. This allows locating grouped data (e.g., all columns under “Support”).
- The last three columns are renamed in-memory to R1, R2, and R3 as placeholders.
- The original file is never modified.

#### Contact parsing (learner contacts)
- Source column: Contact # (multi-line text)
- Recognizes Afrikaans and English labels:
  - Primary: lines containing Kontak, Bel, Call, Primary
  - WhatsApp: lines containing WhatsApp/Whats App
  - Alternative: lines containing Alternatiewe/Altern/Alt
- If labels are missing, the first three phone-like numbers are assigned in order: Primary, WhatsApp, Alternative.
- Phone normalization: spaces and dashes removed, digits preserved (leading + allowed).

#### Parent/Guardian parsing
- Source block: Parent Details (multi-line text)
- Extracts:
  - Parent/Guardian Name: looks for patterns like “Ouer/Voog se volle naam …” and “Ouer/Voog van …” and combines if they complement each other (e.g., name + surname-of)
  - Parent/Guardian Contact: “Kontak nr …”; if not present, falls back to the first phone-like number found in the block

#### Comments parsing
- Source group: Comments (resolved via the super header if the column header cell is blank)
- Splits into two fields:
  - Comment_Time: tokens such as DD/MM (e.g., 15/08) and HHMM (e.g., 0515, 0717)
  - Comment_Text: actual comment with timestamps removed; newlines collapsed; names like “Rudi” retained as part of the text

#### Grouped fields (Study/Support/Work Readiness)
- Using the super header row, the script finds all columns belonging to these groups and concatenates their non-empty values per row, preserving content in a single text field:
  - Support
  - Additional Support
  - Work Readiness Criteria
  - Study Details (fallback if Career Options is empty)
- Work Readiness Criteria (summary) preference:
  - Uses “School WR rating roundup” if available, else “School WR rating”, else concatenated group text

### Output tables and columns

1) outputs/table_personal_parent.csv
- ID_Number
- Name
- Surname
- Address
- Primary Contact
- WhatsApp
- Alternative
- Parent/Guardian Name
- Parent/Guardian Contact
- Comment_Time
- Comment_Text
- Photo

2) outputs/table_study_support.csv
- ID_Number
- Career Options/Study Details (Career Options; falls back to Study Details group text)
- Academic Grouping
- Support (concatenated group text)
- Additional Support (concatenated group text)
- Work Readiness Criteria (summary per preference above)
- Pathways Recommendation
- YearBeyond Recommendation
- Absent from School
- Absentee rating
- School WR rating
- School WR rating roundup

3) outputs/table_engagement_progress.csv
- ID_Number
- Intro Session attended
- Info Form received
- Info Form returned
- Mentor session attended
- R1
- R2
- R3

### Customization
- Input/output paths: change INPUT_PATH and OUTPUT_DIR at the top of clean_and_split.py
- Contact labeling rules: extend the keyword lists in clean_and_split.py (e.g., add more Afrikaans/English synonyms)
- Timestamp patterns: adjust the regexes if new date/time formats appear
- Group selection: modify group_slice_text() to pick specific columns within a group rather than concatenating all
- Work Readiness summary logic: change the preference order or include additional fields

### Troubleshooting
- No data rows found: verify the input file path and that the CSV has at least two header rows
- Comments not splitting: ensure the first header row contains the “Comments” label aligned with the comments column(s)
- Missing ID_Number values: rows are preserved with an empty key; if you prefer temporary IDs, let’s agree on a scheme (e.g., TEMP-001) and update the script
- Unexpected contact assignments: labels may be missing; extend keywords, or provide a specific pattern seen in the data so we can refine the parser

### Validating results
- Open the outputs/*.csv files and spot-check several rows against the original
- Join tables by ID_Number in your analysis tool to confirm linkage
- Run debug_comments.py to preview how the first few rows’ Comments and Contacts were parsed

### Non-destructive guarantee
- The original CSV is never edited; all transformations happen in-memory and outputs are written to outputs/



