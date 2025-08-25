import csv
import os
import re
import logging
import argparse
import unicodedata
from typing import Dict, List, Tuple, Optional

# Defaults; can be overridden via CLI
INPUT_PATH = "2024 JGT Cohort - 2024 Cohort.csv"
OUTPUT_DIR = "outputs"
DEFAULT_ENCODING = "utf-8-sig"

# Regex patterns
RE_PHONE = re.compile(r"\+?\d[\d\s\-]{7,}\d")
RE_WHATS = re.compile(r"whats\s*app|whatsapp", re.IGNORECASE)
RE_ALT = re.compile(r"altern|alt", re.IGNORECASE)
RE_PRIMARY_HINT = re.compile(r"kontak|bel|call|primary", re.IGNORECASE)
# Times like 0515, 0717
RE_HHMM = re.compile(r"(?<!\d)(\d{4})(?!\d)")
# Dates like 15/08 or 15/08/2024 -> capture first two parts
RE_DDMM = re.compile(r"\b(\d{1,2})/(\d{2})(?:/(\d{2,4}))?\b")

# Afrikaans keys in parent details
RE_PARENT_NAME = re.compile(r"Ouer/Voog\s*se\s*volle\s*naam\s*(.*)", re.IGNORECASE)
RE_PARENT_SURNAME_OF = re.compile(r"Ouer/Voog\s*van\s*(.*)", re.IGNORECASE)
RE_PARENT_CONTACT = re.compile(r"Kontak\s*nr\s*([\+\d][\d\s\-]+)", re.IGNORECASE)


def read_csv_with_multiline(path: str, encoding: str = DEFAULT_ENCODING) -> Tuple[List[str], List[str], List[Dict[str, str]]]:
    """Read CSV that may contain multiline fields. Returns (headers, super_headers, rows_as_dicts).
    - Uses the first row (super header) to name blank header cells (e.g., Comments, Support groups).
    - Renames the last three columns to R1, R2, R3.
    """
    with open(path, "r", encoding=encoding, newline="") as f:
        reader = csv.reader(f)
        try:
            super_header_raw = next(reader)
        except StopIteration:
            return [], [], []
        header_raw = next(reader)  # actual header, may include embedded newlines inside quotes
        # Clean both header rows: strip whitespace/newlines, collapse spaces
        cleaned_super: List[str] = []
        for h in super_header_raw:
            if h is None:
                cleaned_super.append("")
                continue
            h2 = " ".join(str(h).replace("\r", " ").replace("\n", " ").strip().split())
            cleaned_super.append(h2)
        cleaned_header: List[str] = []
        for i, h in enumerate(header_raw):
            val = ""
            if h is not None:
                val = " ".join(str(h).replace("\r", " ").replace("\n", " ").strip().split())
            # If the header cell is blank, fall back to the super header label
            if not val and i < len(cleaned_super):
                val = cleaned_super[i]
            cleaned_header.append(val)
        # Make header names unique (preserve last 3 which will be R1/R2/R3)
        n = len(cleaned_header)
        if n:
            seen = {}
            for i in range(max(0, n - 3)):
                val = cleaned_header[i] or "Unnamed"
                count = seen.get(val, 0)
                if count:
                    val = f"{val}_{count+1}"
                seen[cleaned_header[i] or "Unnamed"] = count + 1
                cleaned_header[i] = val
        # Ensure last three columns are named R1, R2, R3 (placeholders)
        if len(cleaned_header) >= 3:
            cleaned_header[-3:] = ["R1", "R2", "R3"]
        # Build rows
        rows: List[Dict[str, str]] = []
        for row in reader:
            # Pad/truncate to header length
            if len(row) < len(cleaned_header):
                row = row + [""] * (len(cleaned_header) - len(row))
            elif len(row) > len(cleaned_header):
                row = row[: len(cleaned_header)]
            d = {cleaned_header[i]: (row[i] if row[i] is not None else "") for i in range(len(cleaned_header))}
            rows.append(d)
        return cleaned_header, cleaned_super, rows


def normalize_phone(raw: str) -> str:
    s = re.sub(r"[\s\-]", "", raw)
    # Keep only leading + and digits
    s = re.sub(r"[^\d\+]", "", s)
    return s


def parse_contact_field(text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if not text:
        return None, None, None
    # Split into lines to look for hints
    lines = [ln.strip() for ln in str(text).splitlines() if ln.strip()]
    prim = None
    wa = None
    alt = None
    # First pass: labeled lines
    for ln in lines:
        phones = RE_PHONE.findall(ln)
        if not phones:
            continue
        num = normalize_phone(phones[0])
        if RE_WHATS.search(ln):
            if not wa:
                wa = num
            continue
        if RE_ALT.search(ln):
            if not alt:
                alt = num
            continue
        if RE_PRIMARY_HINT.search(ln):
            if not prim:
                prim = num
            continue
        # Unlabeled will be assigned later
    # Second pass: assign remaining by order of appearance
    remaining = []
    for ln in lines:
        for ph in RE_PHONE.findall(ln):
            n = normalize_phone(ph)
            if n not in {x for x in [prim, wa, alt] if x}:
                remaining.append(n)
    for n in remaining:
        if not prim:
            prim = n
        elif not wa:
            wa = n
        elif not alt:
            alt = n
    return prim, wa, alt


def parse_parent_details(text: str) -> Tuple[Optional[str], Optional[str]]:
    if not text:
        return None, None
    t = str(text)
    name = None
    contact = None
    # Try explicit fields
    m = RE_PARENT_NAME.search(t)
    if m:
        val = m.group(1).strip()
        if val and val.upper() != "NA":
            name = val
    m2 = RE_PARENT_SURNAME_OF.search(t)
    if m2:
        val = m2.group(1).strip()
        if val and val.upper() != "NA":
            # Combine if complementary
            if name and val and val not in name:
                name = f"{name} {val}"
            elif not name:
                name = val
    m3 = RE_PARENT_CONTACT.search(t)
    if m3:
        contact = normalize_phone(m3.group(1))
    # Fallback: any phone
    if not contact:
        phones = RE_PHONE.findall(t)
        if phones:
            contact = normalize_phone(phones[0])
    # Clean up
    if name:
        name = " ".join(name.split())
    return name, contact


def split_comments(text: str) -> Tuple[str, str]:
    if not text:
        return "", ""
    t = str(text)
    # Normalize cases like 15/08/ -> 15/08
    t = re.sub(r"\b(\d{1,2}/\d{2})/\b", r"\1", t)
    times: List[str] = []
    # Dates first
    for m in RE_DDMM.finditer(t):
        token = f"{m.group(1)}/{m.group(2)}"
        if token not in times:
            times.append(token)
    # HHMM times
    for m in RE_HHMM.finditer(t):
        token = m.group(1)
        if token not in times:
            times.append(token)
    # Remove tokens from text for clean comment text
    cleaned = t
    for token in times:
        cleaned = re.sub(rf"\b{re.escape(token)}\b", " ", cleaned)
    # Also remove isolated labels like 'Rudi' author lines? Keep them as part of comment text.
    cleaned = re.sub(r"[\r\n]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return " ".join(times), cleaned


def _luhn_sa_id_ok(digits: str) -> bool:
    """Validate SA ID with Luhn-like algorithm on 13 digits."""
    if len(digits) != 13 or not digits.isdigit():
        return False
    # Positions are 1-indexed in the spec; implement accordingly
    # A = sum of digits in odd positions 1,3,5,7,9,11
    a = sum(int(digits[i]) for i in [0, 2, 4, 6, 8, 10])
    # B = concat even positions 2,4,6,8,10,12 -> as number *2, then sum digits
    even_concat = digits[1] + digits[3] + digits[5] + digits[7] + digits[9] + digits[11]
    b_num = int(even_concat) * 2
    b = sum(int(ch) for ch in str(b_num))
    c = a + b
    d = (10 - (c % 10)) % 10
    return d == int(digits[12])


def parse_sa_id_fields(id_value: str) -> Tuple[str, str, str, bool, str]:
    """Parse and validate South African ID.
    Returns (dob_iso, age_str, gender, valid, reason_if_invalid).
    Validation includes:
    - 13 numeric digits
    - Valid date of birth (YYMMDD) with century chosen to make plausible age [0..120]
    - Check digit per SA Luhn algorithm
    Gender is derived from sequence digits (7-10): >=5000 -> Male, else Female.
    """
    if not id_value:
        return "", "", "", False, "empty"
    digits = re.sub(r"[^0-9]", "", str(id_value))
    if len(digits) != 13:
        return "", "", "", False, "length"
    yy = digits[0:2]
    mm = digits[2:4]
    dd = digits[4:6]
    ssss = digits[6:10]
    from datetime import date
    today = date.today()

    def try_century(century: int):
        try:
            dob = date(century + int(yy), int(mm), int(dd))
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if 0 <= age <= 120:
                return dob, age
        except Exception:
            return None
        return None

    dob_age_1900 = try_century(1900)
    dob_age_2000 = try_century(2000)
    if not dob_age_1900 and not dob_age_2000:
        return "", "", "", False, "invalid_date"
    # Prefer the century with age <= 100; if 1900 yields age > 100 and 2000 is valid, choose 2000
    if dob_age_2000 and (not dob_age_1900 or dob_age_1900[1] > 100):
        dob, age = dob_age_2000
    else:
        dob, age = dob_age_1900

    if not _luhn_sa_id_ok(digits):
        return "", "", "", False, "checksum"

    # Gender from SSSS
    gender = ""
    try:
        gender_num = int(ssss)
        gender = "Male" if gender_num >= 5000 else "Female"
    except Exception:
        gender = ""

    return dob.isoformat(), str(age), gender, True, ""


def ensure_outputs_dir(path: str):
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def extract_year_from_filename(path: str, fallback: Optional[int] = None) -> int:
    base = os.path.basename(path)
    m = re.search(r"\b(20\d{2})\b", base)
    if m:
        return int(m.group(1))
    if fallback is not None:
        return fallback
    from datetime import date
    y = date.today().year
    logging.warning(f"Cohort year not found in filename; defaulting to current year {y}.")
    return y


def slug_letters_two(s: str) -> str:
    if not s:
        return ""
    # Normalize and remove accents
    s_norm = unicodedata.normalize('NFKD', s)
    s_ascii = ''.join(ch for ch in s_norm if not unicodedata.combining(ch))
    # Keep only letters
    letters = re.sub(r"[^A-Za-z]", "", s_ascii)
    return letters[:2].lower()


def build_student_id(name: str, surname: str, year: int, unique_counts: Dict[str, int], row_index: int) -> str:
    n2 = slug_letters_two(name)
    s2 = slug_letters_two(surname)
    base = f"{n2}{s2}{year}"
    if not n2 and not s2:
        base = f"unk{year}r{row_index+1}"
    # Ensure uniqueness
    cnt = unique_counts.get(base, 0)
    unique_counts[base] = cnt + 1
    if cnt == 0:
        return base
    else:
        return f"{base}{cnt+1}"


def main(input_path: str = INPUT_PATH, output_dir: str = OUTPUT_DIR, encoding: str = DEFAULT_ENCODING, cohort_year: Optional[int] = None):
    logging.info(f"Starting clean & split | input='{input_path}' | output_dir='{output_dir}'")
    try:
        headers, super_headers, rows = read_csv_with_multiline(input_path, encoding=encoding)
    except FileNotFoundError:
        logging.error(f"Input file not found: {input_path}")
        return 2
    except UnicodeDecodeError as e:
        logging.error(f"Encoding error reading '{input_path}': {e}")
        return 3
    except Exception as e:
        logging.exception(f"Unexpected error reading '{input_path}': {e}")
        return 4
    # Determine cohort year
    year = cohort_year if cohort_year else extract_year_from_filename(input_path)
    logging.info(f"Cohort year: {year}")

    if not rows:
        logging.warning("No data rows found.")
        return 0
    # Map required columns (best-effort; handle missing gracefully)
    col = {h.lower(): h for h in headers}
    def get_col(name: str) -> Optional[str]:
        # return actual header matching case-insensitively
        key = name.lower()
        if key in col:
            return col[key]
        # try fuzzy contains
        for h in headers:
            if h and key in h.lower():
                return h
        return None

    id_col = get_col("ID Number") or get_col("ID_Number") or get_col("ID No")
    if not id_col:
        print("WARNING: Could not find an 'ID Number' column; keying will be empty.")
    name_col = get_col("Name")
    surname_col = get_col("Surname")
    address_col = get_col("Address")
    photo_col = get_col("Photo")

    contact_col = get_col("Contact #") or get_col("Contact#") or get_col("Contact")
    parent_details_col = get_col("Parent Details")
    # If 'Comments' header was blank, it should now be picked up via superheader-based fallback
    comments_col = get_col("Comments")

    # Additional columns to map as requested
    applicant_details_col = get_col("Applicant Details")
    family_details_col = get_col("Family Details")
    id_doc_col = get_col("ID")  # distinct from ID Number
    bank_account_col = get_col("Bank Account")
    sars_number_col = get_col("SARS Number")
    learners_licence_col = get_col("Learners / Licence")

    visits_office_col = get_col("Visits to Office")
    comm_whatsapp_col = get_col("Communication WhatsApp")
    comm_facebook_col = get_col("Communication Facebook")
    cv_col = get_col("CV")
    study_app_col = get_col("Study Application")
    w4al_course_col = get_col("W4AL course")
    skills_col = get_col("Skills")
    responses_col = get_col("#responses")
    info_session_attended_col = get_col("Info session attended")

    career_col = get_col("Career Options")
    academic_group_col = get_col("Academic Grouping")
    # Capture the two unlabeled academic columns made unique by read_csv_with_multiline
    academic_details_1_col = get_col("Unnamed") or get_col("Unnamed_2")
    academic_details_2_col = get_col("Unnamed_2") if academic_details_1_col == get_col("Unnamed") else get_col("Unnamed")
    pathways_col = get_col("Pathways Recommendation")
    yearbeyond_col = get_col("YearBeyond Recommendation")

    wr_rating_col = get_col("School WR rating")
    wr_roundup_col = get_col("School WR rating roundup")
    absent_col = get_col("Absent from School")
    absentee_rating_col = get_col("Absentee rating")

    intro_session_col = get_col("Intro Session attended")
    info_form_received_col = get_col("Info Form received")
    info_form_returned_col = get_col("Info Form returned")
    mentor_session_col = get_col("Mentor session attended")

    # Last three: R1, R2, R3 are headers already
    r1_col = "R1" if "R1" in headers else None
    r2_col = "R2" if "R2" in headers else None
    r3_col = "R3" if "R3" in headers else None

    # Prepare outputs
    ensure_outputs_dir(output_dir)

    # Identify columns belonging to groups based on super headers
    group_indices: Dict[str, List[int]] = {}
    for i, sh in enumerate(super_headers):
        if not sh:
            continue
        group_indices.setdefault(sh, []).append(i)

    def group_slice_text(d: Dict[str, str], group_name: str) -> str:
        idxs = group_indices.get(group_name, [])
        vals: List[str] = []
        for i in idxs:
            if i < len(headers):
                key = headers[i]
                if key in ("R1", "R2", "R3"):
                    continue
                vals.append(str(d.get(key, "")))
        # Join non-empty with newlines to preserve info
        vals = [v for v in vals if v and v.upper() != "NA" and v != "-"]
        return "\n".join(vals)

    # Table 1: Personal & Parent Info
    t1_fields = [
        "Student_ID",
        "ID_Number",
        "Name",
        "Surname",
        "DOB (from SA ID)",
        "Age (from SA ID)",
        "Gender (from SA ID)",
        "Address",
        "Primary Contact",
        "WhatsApp",
        "Alternative",
        "Parent/Guardian Name",
        "Parent/Guardian Contact",
        "Applicant Details",
        "Family Details",
        "ID Document",
        "Bank Account",
        "SARS Number",
        "Learners / Licence",
        "Comment_Text",
        "Photo",
    ]
    t1_rows: List[Dict[str, str]] = []

    # Table 2: Study & Support Info
    t2_fields = [
        "Student_ID",
        "ID_Number",
        "Career Options/Study Details",
        "Academic Grouping",
        "Academic Details 1",
        "Academic Details 2",
        "Support",
        "Additional Support",
        "CV",
        "Study Application",
        "W4AL course",
        "Skills",
        "Work Readiness Criteria",
        "Pathways Recommendation",
        "YearBeyond Recommendation",
        # Preserve granular WR fields, if present
        "Absent from School",
        "Absentee rating",
        "School WR rating",
        "School WR rating roundup",
    ]
    t2_rows: List[Dict[str, str]] = []

    # Table 3: Engagement & Progress Tracking
    t3_fields = [
        "Student_ID",
        "ID_Number",
        "Intro Session attended",
        "Info session attended",
        "Info Form received",
        "Info Form returned",
        "Mentor session attended",
        "Visits to Office",
        "Communication WhatsApp",
        "Communication Facebook",
        "#responses",
        "ro",
        "Datapoints",
        "R1",
        "R2",
        "R3",
    ]
    t3_rows: List[Dict[str, str]] = []

    missing_id_count = 0
    # Track uniqueness for Student_ID
    id_counts: Dict[str, int] = {}

    for idx, d in enumerate(rows):
        # ID key
        id_val = (d.get(id_col, "") if id_col else "").strip()
        if not id_val:
            missing_id_count += 1
        # Build Student_ID (first 2 letters of name + first 2 of surname + year; unique suffix if needed)
        student_id = build_student_id(d.get(name_col, "") if name_col else "",
                                      d.get(surname_col, "") if surname_col else "",
                                      year,
                                      id_counts,
                                      idx)
        # Contacts (learner)
        prim, wa, alt = parse_contact_field(d.get(contact_col, "") if contact_col else "")
        # Parent details
        p_name, p_contact = parse_parent_details(d.get(parent_details_col, "") if parent_details_col else "")
        # Comments
        c_time, c_text = split_comments(d.get(comments_col, "") if comments_col else group_slice_text(d, "Comments"))

        # Table 1 row
        dob_iso, age_str, gender, valid_id, invalid_reason = parse_sa_id_fields(id_val)
        if id_val and not valid_id:
            norm_id = re.sub(r"[^0-9]", "", id_val)
            logging.warning(f"Invalid SA ID for row: id='{norm_id}' reason='{invalid_reason}' name='{d.get(name_col, '') if name_col else ''} {d.get(surname_col, '') if surname_col else ''}'")
        t1_rows.append({
            "Student_ID": student_id,
            "ID_Number": id_val,
            "Name": d.get(name_col, "") if name_col else "",
            "Surname": d.get(surname_col, "") if surname_col else "",
            "DOB (from SA ID)": dob_iso,
            "Age (from SA ID)": age_str,
            "Gender (from SA ID)": gender,
            "Address": d.get(address_col, "") if address_col else "",
            "Primary Contact": prim or "",
            "WhatsApp": wa or "",
            "Alternative": alt or "",
            "Parent/Guardian Name": p_name or "",
            "Parent/Guardian Contact": p_contact or "",
            "Applicant Details": d.get(applicant_details_col, "") if applicant_details_col else "",
            "Family Details": d.get(family_details_col, "") if family_details_col else "",
            "ID Document": d.get(id_doc_col, "") if id_doc_col else "",
            "Bank Account": d.get(bank_account_col, "") if bank_account_col else "",
            "SARS Number": (d.get(sars_number_col, "") if sars_number_col else "").replace("-","None") if (d.get(sars_number_col, "") if sars_number_col else "") == "-" else (d.get(sars_number_col, "") if sars_number_col else ""),
            "Learners / Licence": (d.get(learners_licence_col, "") if learners_licence_col else "").replace("-","None") if (d.get(learners_licence_col, "") if learners_licence_col else "") == "-" else (d.get(learners_licence_col, "") if learners_licence_col else ""),
            "Comment_Text": c_text,
            "Photo": d.get(photo_col, "") if photo_col else "",
        })

        # Work Readiness Criteria (summary): prefer roundup, else rating
        wr_summary = (d.get(wr_roundup_col, "") if wr_roundup_col else "") or (d.get(wr_rating_col, "") if wr_rating_col else "")
        # If both empty, use grouped text under Work Readiness Criteria
        if not wr_summary:
            wr_summary = group_slice_text(d, "Work Readiness Criteria")

        t2_rows.append({
            "Student_ID": student_id,
            "ID_Number": id_val,
            "Career Options/Study Details": (d.get(career_col, "") if career_col else "") or group_slice_text(d, "Study Details") or group_slice_text(d, "Career Options"),
            "Academic Grouping": d.get(academic_group_col, "") if academic_group_col else "",
            "Academic Details 1": d.get(academic_details_1_col, "") if academic_details_1_col else "",
            "Academic Details 2": d.get(academic_details_2_col, "") if academic_details_2_col else "",
            "Support": group_slice_text(d, "Support"),
            "Additional Support": group_slice_text(d, "Additional Support"),
            "CV": d.get(cv_col, "") if cv_col else "",
            "Study Application": d.get(study_app_col, "") if study_app_col else "",
            "W4AL course": d.get(w4al_course_col, "") if w4al_course_col else "",
            "Skills": d.get(skills_col, "") if skills_col else "",
            "Work Readiness Criteria": wr_summary,
            "Pathways Recommendation": d.get(pathways_col, "") if pathways_col else "",
            "YearBeyond Recommendation": d.get(yearbeyond_col, "") if yearbeyond_col else "",
            "Absent from School": d.get(absent_col, "") if absent_col else "",
            "Absentee rating": d.get(absentee_rating_col, "") if absentee_rating_col else "",
            "School WR rating": d.get(wr_rating_col, "") if wr_rating_col else "",
            "School WR rating roundup": d.get(wr_roundup_col, "") if wr_roundup_col else "",
        })

        # Normalize 'ro' stars to numeric rating
        def stars_to_number(val: str) -> str:
            if not val:
                return ""
            s = str(val)
            # If digits already present, return digits
            m = re.search(r"\d+", s)
            if m:
                return m.group(0)
            # Count star characters
            count = s.count("★")
            if count > 0:
                return str(count)
            # Handle common NA markers
            if s.strip().upper() in {"N/A", "#N/A", "NA"}:
                return ""
            return ""

        t3_rows.append({
            "Student_ID": student_id,
            "ID_Number": id_val,
            "Intro Session attended": d.get(intro_session_col, "") if intro_session_col else "",
            "Info session attended": d.get(info_session_attended_col, "") if info_session_attended_col else "",
            "Info Form received": d.get(info_form_received_col, "") if info_form_received_col else "",
            "Info Form returned": d.get(info_form_returned_col, "") if info_form_returned_col else "",
            "Mentor session attended": d.get(mentor_session_col, "") if mentor_session_col else "",
            "Visits to Office": d.get(visits_office_col, "") if visits_office_col else "",
            "Communication WhatsApp": d.get(comm_whatsapp_col, "") if comm_whatsapp_col else "",
            "Communication Facebook": d.get(comm_facebook_col, "") if comm_facebook_col else "",
            "#responses": d.get(responses_col, "") if responses_col else "",
            "ro": stars_to_number(d.get('ro', "")),
            "Datapoints": d.get('Datapoints', ""),
            "R1": d.get(r1_col, "") if r1_col else "",
            "R2": d.get(r2_col, "") if r2_col else "",
            "R3": d.get(r3_col, "") if r3_col else "",
        })

    # Write outputs
    def write_csv(path: str, fieldnames: List[str], data: List[Dict[str, str]]):
        with open(path, "w", encoding=encoding, newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            for r in data:
                w.writerow(r)
        logging.info(f"Wrote {len(data)} rows -> {path}")

    # Write outputs with user-provided output_dir
    p1 = os.path.join(output_dir, "table_personal_parent.csv")
    p2 = os.path.join(output_dir, "table_study_support.csv")
    p3 = os.path.join(output_dir, "table_engagement_progress.csv")
    write_csv(p1, t1_fields, t1_rows)
    write_csv(p2, t2_fields, t2_rows)
    write_csv(p3, t3_fields, t3_rows)

    # Summary log
    logging.info("Summary: rows per table")
    logging.info(f"- Personal & Parent: {len(t1_rows)}")
    logging.info(f"- Study & Support:  {len(t2_rows)}")
    logging.info(f"- Engagement:       {len(t3_rows)}")
    if missing_id_count:
        logging.warning(f"NOTE: {missing_id_count} row(s) missing ID Number; included with empty ID.")

    # Student_ID uniqueness check
    unique_ids = {r["Student_ID"] for r in t1_rows}
    if len(unique_ids) != len(t1_rows):
        logging.error("Student_IDs are not unique in Table 1; please inspect generation logic.")

    return 0


def parse_args():
    parser = argparse.ArgumentParser(description="Clean and split cohort CSV into three linked tables.")
    parser.add_argument("input", nargs="?", default=INPUT_PATH, help="Path to input CSV (default: %(default)s)")
    parser.add_argument("--output-dir", "-o", default=OUTPUT_DIR, help="Directory to write outputs (default: %(default)s)")
    parser.add_argument("--encoding", default=DEFAULT_ENCODING, help="File encoding (default: %(default)s)")
    parser.add_argument("--cohort-year", type=int, default=None, help="Override cohort year in Student_IDs (e.g., 2024)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    setup_logging(verbose=args.verbose)
    exit_code = main(args.input, args.output_dir, args.encoding, args.cohort_year)
    if exit_code:
        logging.error(f"Exited with code {exit_code}")

