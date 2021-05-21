from grades import load_grades
import os
import pandas as pd

# The expected format is columns=["Name", "Email", "Extra Slip Days", "Excluding"]
# where name and email are the student's, and extra slip days is an int.
# 'Excluding' marks certain assignments to exclude from the calculation for that particular student
# (e.g., they had a sudden emergency). Normally this should be blank.
# If you need to add to excluding, you put the key of the rubric_data_map (below)
# corresponding to the assignment you wish to exclude. Multiple can be comma-separated (no spaces).
PATH_TO_EXTRA_SLIP_DAYS_CSV = 'data/extra_slip_days.csv' # Set to None if you don't have this
SAVE_TO = 'data/slip_days.csv'

# Map rubric files to directories containing all assignment eval sheets from GS.
# This assumes the json rubrics are in /rubrics and the assignment folders are in the /data folder.
# **Assumes you have SCORE SHEETS in each assignment directory! These are required for Lateness calculation!!**
rubric_data_map = {
    'mp1': 'mp1',
    'mp2': 'mp2',
    'dw1': 'dw1',
    'dw2': 'dw2',
    'dw3': 'dw3',
    'mp3_indiv': 'mp3/indiv',
    'mp3_group': 'mp3/group',
    'mp4': 'mp4',
    'dw4': 'dw4',
    'dw5': 'dw5'
}
INITIAL_SLIPS = 10 # the number of slip days every student starts with

# Read extra slip days sheet
excluding_assns = {}
if PATH_TO_EXTRA_SLIP_DAYS_CSV:
    df = pd.read_csv(PATH_TO_EXTRA_SLIP_DAYS_CSV)
    excluding_df = df.dropna(subset=['Excluding'])
    for index, row in excluding_df.iterrows():
        excluding_assns[row['Email'].strip().lower()] = row['Excluding'].split(',')

# For each assignment, extract grades, and sum num of late days across assignments
# special_check = {}
slip_days = {}
emails_to_names = {}
mp3_slips_used = {}
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
    print(email, slips)
    rem_slips.append( [emails_to_names[email], email, slips] )
df_slips = pd.DataFrame(rem_slips, columns=["Name", "Email", "Slip Days Remaining"])
df_slips.to_csv(SAVE_TO, index=False)
print("Saved remaining slip days to spreadsheet", SAVE_TO)
