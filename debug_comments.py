from clean_and_split import read_csv_with_multiline, split_comments, parse_contact_field

headers, rows = read_csv_with_multiline("2024 JGT Cohort - 2024 Cohort.csv")
print("Headers count:", len(headers))
print("First 10 headers:", headers[:10])
comments_key = None
for h in headers:
    if h and 'comments' in h.lower():
        comments_key = h
        break
print("Comments column:", comments_key)
for i, d in enumerate(rows[:3]):
    c = d.get(comments_key, "") if comments_key else ""
    t, txt = split_comments(c)
    print("Row", i+1, "raw_len", len(str(c)), "time=", t, "text_preview=", txt[:80])
    print("Contact field sample:", d.get('Contact #','')[:80])
    prim, wa, alt = parse_contact_field(d.get('Contact #',''))
    print("contacts:", prim, wa, alt)

