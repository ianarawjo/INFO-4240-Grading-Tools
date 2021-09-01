from grades import load_grades
import os
import pandas as pd
from datetime import datetime
from load_roster import load_roster

# The expected format is columns=["Name", "Email", "Extra Slip Days", "Excluding"]
# where name and email are the student's, and extra slip days is an int.
# 'Excluding' marks certain assignments to exclude from the calculation for that particular student
# (e.g., they had a sudden emergency). Normally this should be blank.
# If you need to add to excluding, you put the key of the rubric_data_map (below)
# corresponding to the assignment you wish to exclude. Multiple can be comma-separated (no spaces).
PATH_TO_EXTRA_SLIP_DAYS_CSV = None #'data/extra_slip_days.csv' # Set to None if you don't have this

# Path to the Canvas roster (download Gradebook csv) for this class.
# :: This is used to determine who is still in the class.
PATH_TO_CANVAS_ROSTER = "data/roster/roster-sp21.csv"

# Where to save the slip days calculation.
SAVE_TO = 'data/slip_days.csv'

# Map rubric files to directories containing all assignment eval sheets from GS.
# This assumes the json rubrics are in /rubrics and the assignment folders are in the /data folder.
# **Assumes you have SCORE SHEETS in each assignment directory! These are required for Lateness calculation!!**
rubric_data_map = {
    'dw3': 'dw3-sp21'
    # 'mp1': 'mp1',
    # 'mp2': 'mp2',
    # 'dw1': 'dw1',
    # 'dw2': 'dw2',
    # 'dw3': 'dw3',
    # 'mp3_indiv': 'mp3/indiv',
    # 'mp3_group': 'mp3/group',
    # 'mp4': 'mp4',
    # 'dw4': 'dw4',
    # 'dw5': 'dw5'
}
duedates = {
    'checkin': 'Sep 5 2021 10:00PM',
    'dw3': 'Apr 7 2021 10:00PM'
}
INITIAL_SLIPS = 7 # the number of slip days every student starts with

# Read extra slip days sheet
excluding_assns = {}
if PATH_TO_EXTRA_SLIP_DAYS_CSV:
    df = pd.read_csv(PATH_TO_EXTRA_SLIP_DAYS_CSV)
    excluding_df = df.dropna(subset=['Excluding'])
    for index, row in excluding_df.iterrows():
        excluding_assns[row['Email'].strip().lower()] = row['Excluding'].split(',')

# Read roster. This lets us double-check who's missing a submission for each assignment.
roster = load_roster(PATH_TO_CANVAS_ROSTER)

# For each assignment, extract grades, and sum num of late days across assignments
# special_check = {}
slip_days = {}
emails_to_names = {}
mp3_slips_used = {}
missing_submissions = {}
for rubric_name, dir_name in rubric_data_map.items():
    grades, rubric, questions = load_grades(os.path.join('rubrics', rubric_name+'.json'), \
                                            os.path.join('data', dir_name), \
                                            only_submitted=True)
    seen_sids = {}
    for g in grades:
        email = g['email'].strip()
        if email not in emails_to_names:
            emails_to_names[email] = g['name']
        if email not in seen_sids:
            if email in excluding_assns and dir_name in excluding_assns[email]:
                num_slips_used = 0 # override lateness for exclusions
                print("Excluding", dir_name, "from student", email, "slip days")
            elif g['late'] > 0:
                # Calculate *how* late (in days, 24hr periods=1440 min)
                num_slips_used = int(g['late'] / 1440)+1
            else:
                num_slips_used = 0

            if 'mp3' in rubric_name:
                if email in mp3_slips_used: # special case for mp3
                    # when seeing the second mp3, now add the max to slip days count
                    slip_days[email] += max(mp3_slips_used[email], num_slips_used)
                    print('Added mp3 slips for', email,  max(mp3_slips_used[email], num_slips_used))
                else:
                    # don't add the first mp3 assignment to slip days count yet
                    mp3_slips_used[email] = num_slips_used
            else:
                if email in slip_days:
                    slip_days[email] += num_slips_used
                else:
                    slip_days[email] = num_slips_used
            seen_sids[email] = True

    duedate = datetime.strptime(duedates[rubric_name], '%b %d %Y %I:%M%p')
    for sid, student in roster.items():
        if student.email in seen_sids: continue
        # Missing a student submission for this assignment. Calculate how long:
        lateness = datetime.now() - duedate
        student.flag_missing_submission(rubric_name, lateness)

# Read extra slip days sheet, and subtract from the total used:
if PATH_TO_EXTRA_SLIP_DAYS_CSV:
    for index, row in df.iterrows():
        email = row['Email'].strip().lower()
        if email in slip_days:
            slip_days[email] = slip_days[email]-int(row['Extra Slip Days'])
        else:
            slip_days[email] = -int(row['Extra Slip Days'])

# Collect remaining slip days into a spreadsheet
rem_slips = []
for email, used_slips in slip_days.items():
    slips = INITIAL_SLIPS-used_slips
    rem_slips.append( [emails_to_names[email], email, slips] )
rem_slips.sort(key=lambda x: x[2])
df_slips = pd.DataFrame(rem_slips, columns=["Name", "Email", "Slip Days Remaining"])
df_slips.to_csv(SAVE_TO, index=False)
print("Saved remaining slip days to spreadsheet", SAVE_TO)

# Print 'struggling students' to console:
print("\n== Students with low remaining slip days (according to *submitted* assignments) ==")
for name, email, slips in rem_slips:
    if slips <= 2:
        print(name, email, slips)

print("\n== Students missing assignment submissions ==")
missing_assns = dict()
for assn, _ in rubric_data_map.items():
    missing_assns[assn] = []
for sid, student in roster.items():
    printed_missing_header = False
    if student.email in slip_days:
        slips = INITIAL_SLIPS-slip_days[student.email]
    else:
        slips = INITIAL_SLIPS
    for assn, lateness in student.missing_submissions.items():
        if not printed_missing_header:
            print("{} ({}) is missing:".format(student.name, student.email))
            printed_missing_header = True
        days_missing = int(lateness.total_seconds() / (1440*60)) + 1
        print("   {} by {} days, {} secs. This is -= {} slip days. If they submit, they will have {} slip days remaining.".format(assn, lateness.days, lateness.seconds, days_missing, slips-days_missing))
        missing_assns[assn].append(student.email)

print("\n== All emails of students missing each assignment ==")
for assn, emails in missing_assns.items():
    print(assn, ":", ', '.join(emails))
