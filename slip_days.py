from grades import load_grades
import os
import pandas as pd
from datetime import datetime
import load

# Load central config json
config = load.config()
assignments = config["assignments"]

# The expected format is columns=["Name", "Email", "Extra Slip Days", "Excluding"]
# where name and email are the student's, and extra slip days is an int.
# 'Excluding' marks certain assignments to exclude from the calculation for that particular student
# (e.g., they had a sudden emergency). Normally this should be blank.
# If you need to add to excluding, you put the key of the rubric_data_map (below)
# corresponding to the assignment you wish to exclude. Multiple can be comma-separated (no spaces).
PATH_TO_EXTRA_SLIP_DAYS_CSV = config["extraSlipsCSV"] # Set to None if you don't have this

# Path to the Canvas roster (download Gradebook csv) for this class.
# :: This is used to determine who is still in the class.
PATH_TO_CANVAS_ROSTER = config["rosterCSV"]

# Where to save the slip days calculation.
SAVE_TO = config["slipDaysCSVExportPath"]

# The number of slip days every student starts with
INITIAL_SLIPS = 7

def calculate_slip_days():
    # Read extra slip days sheet
    excluding_assns = {}
    if PATH_TO_EXTRA_SLIP_DAYS_CSV:
        df = pd.read_csv(PATH_TO_EXTRA_SLIP_DAYS_CSV).dropna(subset=['Email'])
        excluding_df = df.dropna(subset=['Excluding'])
        for index, row in excluding_df.iterrows():
            excluding_assns[row['Email'].strip().lower()] = row['Excluding'].split(',')

    # Read roster. This lets us double-check who's missing a submission for each assignment.
    roster = load.roster(PATH_TO_CANVAS_ROSTER)

    # For each assignment, extract grades, and sum num of late days across assignments
    # special_check = {}
    slip_days = {}
    flagged_email_domains = {}
    emails_to_names = {}
    emails_to_sids = {}
    mp3_slips_used = {}
    missing_submissions = {}
    for assn_name, info in assignments.items():

        # Exclude any assignments that are not due yet:
        duedate = datetime.strptime(info["duedate"], '%b %d %Y %I:%M%p')
        if (datetime.now() - duedate).total_seconds() < 0:
            print("\n==================\nSkipping assignment", assn_name, "which is not yet due!\n==================\n")
            continue

        grades, rubric, questions = load_grades(info["rubric"], \
                                                info["data"], \
                                                only_submitted=False)
        seen_sids = {}
        for g in grades:
            email = g['email'].strip()

            # Special check that email is @cornell.edu. Note that emails on Canvas roster will be @cornell,
            # but on GS may not be. Was not aware this was possible, but had a student w/ an NYU email on GS.
            if email.split('@')[-1] != "cornell.edu" and email not in flagged_email_domains:
                flagged_email_domains[email] = True
                print("Student {} has email {} that is not a Cornell address. This may cause errors, as the Canvas roster uses @cornell emails.".format(g['name'], g['email']))
                input("Press any key to continue and ignore this warning...")

            if email not in emails_to_names:
                emails_to_names[email] = g['name']
                emails_to_sids[email] = g['sid']
            if email not in seen_sids:
                if email in excluding_assns and assn_name in excluding_assns[email]:
                    num_slips_used = 0 # override lateness for exclusions
                    print("Excluding", assn_name, "from student", email, "slip days")
                elif g['late'] > 0 and g['late'] > 20: # Grace period of 20 minutes.
                    # Calculate *how* late (in days, 24hr periods=1440 min)
                    num_slips_used = int(g['late'] / 1440)+1
                    if g['sid'] in roster:
                        roster[g['sid']].flag_late_submission(assn_name, (g['late'], num_slips_used))
                else:
                    num_slips_used = 0

                if 'mp3' in assn_name:
                    if email in mp3_slips_used: # special case for mp3
                        # when seeing the second mp3, now add the max to slip days count
                        slip_days[email] += max(mp3_slips_used[email], num_slips_used)
                        print('Added mp3 slips for', email, max(mp3_slips_used[email], num_slips_used))
                    else:
                        # don't add the first mp3 assignment to slip days count yet
                        mp3_slips_used[email] = num_slips_used
                else:
                    if email in slip_days:
                        slip_days[email] += num_slips_used
                    else:
                        slip_days[email] = num_slips_used
                seen_sids[email] = True

        # Detect students that haven't submitted at all yet (whether late or on-time.)
        for sid, student in roster.items():
            if student.email in seen_sids: continue
            # Missing a student submission for this assignment. Calculate how long:
            lateness = datetime.now() - duedate
            student.flag_missing_submission(assn_name, lateness)
            print("Student {} is missing assignment {}.".format(student.name, assn_name))
            # If student isn't in the slip days tally, add them:
            if student.email not in slip_days:
                slip_days[student.email] = 0 # Note: this marks the slip days used, not remaining
                emails_to_names[student.email] = student.name
                emails_to_sids[student.email] = sid

    # Read extra slip days sheet, and subtract from the total used:
    extra_slips = dict()
    if PATH_TO_EXTRA_SLIP_DAYS_CSV:
        for index, row in df.iterrows():
            email = row['Email'].strip().lower()
            if email in slip_days:
                slip_days[email] = slip_days[email]-int(row['Extra Slip Days'])
            else:
                slip_days[email] = -int(row['Extra Slip Days'])
            print("Detected extra slip days for", email, "=", row['Extra Slip Days'])
            if email in extra_slips:
                extra_slips[email] += int(row['Extra Slip Days'])
            else:
                extra_slips[email] = int(row['Extra Slip Days'])

    # Collect remaining slip days
    rem_slips = []
    for email, used_slips in slip_days.items():
        slips = INITIAL_SLIPS-used_slips
        sid = emails_to_sids[email]
        if sid not in roster:
            print("Skipping student {} not in roster...".format(emails_to_names[email]))
            continue
        student = roster[sid]
        name = student.name.split(", ")[1] + " " + student.name.split(", ")[0]
        missing_info = ""
        late_info = ""

        # Find any late submissions + gen info
        for assn, (lateness, slips_off) in student.late_submissions.items(): # here, lateness is an integer in minutes
            fullname = assignments[assn]["fullname"]
            late_info += "{} by {} days, {} hrs, {} mins. This cost {} slip days.\n".format(fullname, int(lateness/1440), int((lateness%1440)/60), int(lateness%60), slips_off)

        # Find any missing assignments + gen info
        for assn, lateness in student.missing_submissions.items():
            fullname = assignments[assn]["fullname"]
            days_missing = int(lateness.total_seconds() / (1440*60)) + 1
            missing_info += "{} by {} days, {} hrs, {} secs. This is {} slip days. If you were to submit at the time this email was sent, you would have {} slip days remaining.\n".format(fullname, lateness.days, int(lateness.seconds/(60*60)), lateness.seconds%60, days_missing, slips-days_missing)

        # Find any extra slips
        extra_slip_info = ""
        if email in extra_slips:
            extra_slip_info = "During the course, you were granted {} additional slip days at the discretion of staff. (This could've been due to a late add, a late resubmission of an assignment that you submitted on-time, a personal issue, or other matters. Assignments can still be listed as technically 'late' in the report, but the deducted slips are offset by the extra ones.)".format(extra_slips[email])

        rem_slips.append( [name, email, slips, late_info, missing_info, extra_slip_info] )
    rem_slips.sort(key=lambda x: x[2])

    # Print 'struggling students' to console:
    print("\n== Students with low remaining slip days (according to *submitted* assignments) ==")
    for name, email, slips, _, _, _ in rem_slips:
        if slips <= 2:
            print(name, email, slips)

    print("\n== Students missing assignment submissions ==")
    missing_assns = dict()
    for assn_name, _ in assignments.items():
        missing_assns[assn_name] = []
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
            print("   {} by {} days, {} hrs, {} secs. This is -= {} slip days. If they submit, they will have {} slip days remaining.".format(assn, lateness.days, int(lateness.seconds/(60*60)), lateness.seconds%60, days_missing, slips-days_missing))
            missing_assns[assn].append(student.email)

    print("\n== All emails of students missing each assignment ==")
    for assn, emails in missing_assns.items():
        print(assn, ":", ', '.join(emails))

    # Save info to a spreadsheet
    df_slips = pd.DataFrame(rem_slips, columns=["Name", "Email", "Slip Days Remaining", "Late Assignments", "Missing Assignments", "Extra Slips"])
    df_slips.to_csv(SAVE_TO, index=False)
    print("Saved remaining slip days to spreadsheet", SAVE_TO)

# Command-line loading.
if __name__ == "__main__":
    calculate_slip_days()
