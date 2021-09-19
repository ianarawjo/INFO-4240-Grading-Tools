import pandas as pd
import os
import sys
import json
import datetime
import statistics as stat
import numpy as np
from difflib import get_close_matches

# == PART YOU CAN EDIT ==
# NOTE: This file uses "config.json" to load rubric and grade csvs.
# It needs a filepath of rubric to use for an assignment. Rubric is JSON file.
# It also needs where you're storing all CSVs for a specific assignment.
# :: Generate CSVs from clicking "Export Evaluations" in GradeScope.
# :: You can also include the 'scores' csv by clicking "Download Grades." Drop that
# :: into the dir (don't rename it!) if you want more info on graded/ungraded and lateness.
additional_scores_sheet = None
# Whether to keep persistent timestamps on when a particular error was first seen
# (Note: if the error is no longer present, it just won't appear.)
ERROR_CHECK_PERSISTENCE = False
# Whether to show TA grade distribution plot
SHOW_TA_GRADE_DIST = True
SHOW_TA_GRADE_DIST_ONLY_TA = None # None # Default: None. Change to EXACT full name (string) to mask in only that TA
# ===========================

# == COMMAND LINE ==
if len(sys.argv) == 3:
    csv_dir = sys.argv[1]
    rubric_path = sys.argv[2]
# ===========================

# Loads rubric JSON file
def load_rubric(rubric_path):
    with open(rubric_path) as f:
        rubric = json.load(f)
    return rubric

# Converts a list of dictionaries, where each dict
# has the exact same keys, into a pandas DataFrame where
# columns=keys and rows=values, with one exception:
# It expands the 'grade' item (which is a dict)
# into separate columns.
def to_pandas(grades):
    if len(grades) == 0: return None
    entries = []
    cols = list(grades[0].keys())
    for d in grades:
        entry = []
        for c in cols:
            if c != 'grade':
                entry.append(d[c])
            else:
                entry.extend([score for _, score in d[c].items()])
        entries.append(entry)
    rubric_items = list(grades[0]['grade'].keys())
    grade_col_idx = cols.index('grade')
    cols = cols[0:grade_col_idx] + rubric_items + cols[grade_col_idx+1:]
    return pd.DataFrame(entries, columns=cols)

# Read in all the grades for all the csvs specified in questions,
# using the given rubric (a JSON object).
# :: Returns grades as a list of dicts. See end of calc_grade for format.
# :: Alternatively, you can set to_pandas_df to get an equivalent DataFrame format.
def load_grades(rubric_path, csv_dir, to_pandas_df=False, only_submitted=True):
    global additional_scores_sheet

    print("\n== Loading grades for assignment '{}' ==".format(rubric_path))

    # Load rubric
    rubric = load_rubric(rubric_path)

    # Verify there's an assignment ID so we can generate URLs
    if 'gsAssignmentID' not in rubric:
        print("Error: Gradescope assignment ID (check in URL text) is not present for this rubric. Please include it.")
        exit(0)

    # Load csv files as 'questions'
    # :: Recurses into subdirectories at csv_path.
    questions = dict()
    def load_dir(dir_path, recurse=1):
        global additional_scores_sheet
        for entry in os.scandir(dir_path):
            if os.path.isdir(entry.path) and recurse > 0:
                load_dir(entry.path, recurse=0)
            elif entry.path.endswith(".csv"):
                filename = os.path.splitext(os.path.basename(entry.path))[0]
                if "_scores" in filename:
                    additional_scores_sheet = entry.path
                elif filename[-13:] == "Please_ignore":
                    continue # skip the correction sheet
                else:
                    simplified_key = filename[:20]
                    questions[simplified_key] = entry.path
    load_dir(csv_dir)

    # Remove any questions rubric wants us to skip:
    if "skipQuestions" in rubric:
        for q in rubric["skipQuestions"]:
            if q in questions:
                del questions[q]

    # Load grades for each question
    grades = []
    for name, csv in questions.items():
        print(" - Loaded question:", name, csv)
        num = int(os.path.basename(csv).split("_")[0])
        gs = load_gradesheet(rubric, name, csv, num, only_submitted=only_submitted)
        grades.extend(gs)

    # (Optional) Load lateness markers from score sheet
    # :: If there's an additional score sheet identified, add "graded/ungraded" and "lateness" info:
    if additional_scores_sheet is not None:
        df = pd.read_csv(additional_scores_sheet)
        num_graded = len(df[df['Status']=="Graded"])
        num_ungraded = len(df[df['Status']=="Ungraded"])
        num_ontime = len(df[df['Lateness (H:M:S)']=="00:00:00"])
        num_graded_ontime = len(df[(df['Status']=="Graded") & (df['Lateness (H:M:S)']=="00:00:00")])
        num_ungraded_ontime = len(df[(df['Status']=="Ungraded") & (df['Lateness (H:M:S)']=="00:00:00")])
        num_graded_late = len(df[(df['Status']=="Graded") & (df['Lateness (H:M:S)']!="00:00:00")])
        num_ungraded_late = len(df[(df['Status']=="Ungraded") & (df['Lateness (H:M:S)']!="00:00:00")])

        df_scores_sheet = df
        def hms_to_min(hms_str):
            t = hms_str.split(':')
            return int(t[0])*60+int(t[1])+int(t[2])/60
        def lateness(sid):
            student = df_scores_sheet[df_scores_sheet['SID']==str(sid)]
            if len(student) == 0:
                pass #print("Error: Could not find student with SID", sid)
            elif len(student) > 1:
                print("Error: Found more than one student with SID", sid)
            else:
                return hms_to_min(student['Lateness (H:M:S)'].tolist()[0])
            return 0

        print("Total submissions: {} fully graded, {} left to grade ({:.2f}% done)".format(num_graded, num_ungraded, 100*num_graded/(num_graded+num_ungraded)))
        print(" > Ontime submissions: {} fully graded, {} left to grade ({:.2f}% done)".format(num_graded_ontime, num_ungraded_ontime, 100*num_graded_ontime/(num_graded_ontime+num_ungraded_ontime)))
        if num_graded_late + num_ungraded_late > 0:
            print(" > Late submissions: {} fully graded, {} left to grade ({:.2f}% done)".format(num_graded_late, num_ungraded_late, 100*num_graded_late/(num_graded_late+num_ungraded_late)))
        else:
            print(" > Late submissions: 0")

        # Mark lateness in grades
        for g in grades:
            if g['sid'] == -1:
                pass #print('Warning: Student', g['email'], 'has no SID.')
            g['late'] = lateness(g['sid'])

    if to_pandas_df:
        return to_pandas(grades), rubric, questions
    else:
        return grades, rubric, questions

# Read in all the grades for a single GS eval sheet
# :: Returns grades as a list of dicts. See end of calc_grade for format.
def load_gradesheet(rubric, question_name, csv, question_num, only_submitted=True):
    df = pd.read_csv(csv)
    df.drop(index=[len(df)-1, len(df)-2, len(df)-3], inplace=True)
    df.dropna(subset=['SID'], inplace=True)

    grades = df.apply(lambda row: calc_grade(row, rubric, question_name, df.columns, question_num), axis=1)

    if only_submitted:
        grades = [g for g in grades if g['was_submitted'] is True] # cull the Nones

    return grades

# Calculate the grade for a specific row of a GS eval sheet
def calc_grade(row, rubric, question_name, col_names, question_num):
    scores = dict()
    no_score = pd.isna(row['Score']) or row['Score'] == 0
    gs_score = 0 if no_score else row['Score']
    incomplete_score = False
    errors = []
    gsAssignmentID = rubric['gsAssignmentID']
    aggr_method = rubric['aggr_method']
    shortnames = rubric['shortnames']
    was_submitted = True
    was_submitted_check = None
    if 'wasSubmittedItem' in rubric:
        was_submitted_item = rubric['wasSubmittedItem']
        was_submitted_check = "+"
    elif 'wasNotSubmittedItem' in rubric:
        was_submitted_item = rubric['wasNotSubmittedItem']
        was_submitted_check = "-"
    rubric = rubric['rubric']

    # Detects which column name matches a given rubric item.
    # Has to be done on a case-by-case basis because of small variations in strings.
    def col_inc_term(term):
        if term in col_names:
            return term
        else:
            # Easy checks for single trailing spaces either on ends or near colon
            if (term+' ') in col_names:
                return term+" "
            elif (' '+term in col_names):
                return " "+term
            elif ":" in term:
                lr = term.split(":")
                if len(lr) > 2:
                    pass
                elif (lr[0] + ' :' + lr[1]) in col_names:
                    return (lr[0] + ' :' + lr[1])
                elif (lr[0] + ': ' + lr[1]) in col_names:
                    return (lr[0] + ': ' + lr[1])
            # Compute edit distance (this is intensive) and return the closest match.
            # This is because sometimes graders edit the rubric and say, add an extra letter,
            # screwing up the column names for specific questions. We want to ignore these errors.
            # print(term, col_names)
            closest = get_close_matches(term, col_names, 1)[0]
            return closest

    # Calculate score (pts) for each rubric item
    for key, val in rubric.items():
        score = 0

        # Is single rubric item w/ no subitems
        if isinstance(val, int):
            col = col_inc_term(key)
            if was_submitted_check != None and key == was_submitted_item:
                # This is a special rubric item to mark if the current question had a submission.
                was_submitted = row[col] == "true" or row[col] == True or row[col] == "TRUE"
                if was_submitted_check == '-': was_submitted = not was_submitted
                scores[shortnames[key]] = val if was_submitted else 0 # for consistency
            else:
                score = val if row[col] == "true" else 0
                scores[shortnames[key]] = score
            continue

        # Is rubric item w/ subitems (dict)
        subscores = []
        for subkey, subval in val.items():
            col = col_inc_term(key + ": " + subkey) # the name of the column referring to this subitem of the rubric
            # if subkey == 'The discussion of the ideas the design raises is nuanced':
            #     print(col, row[col], type(row[col]))
            if col not in row:
                print("Error: Column", col, "is not in row for question", question_name)
            if row[col] == "true" or row[col] is True or row[col] == "TRUE":
                # Different loading/saving schemes have different 'true' representations.
                subscores.append(subval)

        # Aggregate scores using appropriate method for this rubric item=
        if aggr_method[key] == "max":
            if len(subscores) == 0:
                incomplete_score = True
                if gs_score > 0:
                    errors.append("No score entered for rubric item: " + str(key))
                score = 0
            else:
                score = max(subscores)
                if len(subscores) > 1:
                    errors.append("More than one score entered for single-select rubric item: " + str(key))
        elif aggr_method[key] == "sum":
            score = sum(subscores)

        # Save total score
        scores[shortnames[key]] = score

    # Sanity check that our extracted scores sum to GradeScope's total score
    agg = 0.0
    for key, val in scores.items():
        agg += val
    if row['Adjustment'] != "" and not pd.isna(row['Adjustment']):
        agg += row['Adjustment']
    if agg != gs_score:
        errors.append("Calc grade doesn't match GradeScope." + str(float(row['Adjustment'])))

    # Check for errors in grading
    # Check whether comments are blank
    if not isinstance(row['Comments'], str) or len(row['Comments'].strip()) == 0:
        if gs_score > 0:
            if incomplete_score:
                errors.append("Comment is blank, and not all rubric items are completed.")
            else:
                errors.append("Comment is blank after all rubric items were completed.")
    elif any(s in row['Comments'] for s in ('you', 'You')):
        errors.append("Comment contains the word 'you.'")
    if was_submitted == False and gs_score > 0:
        # Someone marked the "not/submitted" rubric item when they shouldn't have...
        errors.append("'Was submitted' rubric item mismatched; this question has a score.")
        was_submitted = True

    # Compatibility issues
    # :: GS seems to have changed their eval sheets from "First/Last Name" cols to just a "Name" col.
    name = row['Name'] if 'Name' in row else (row["First Name"] + " " + row["Last Name"])

    # Return the grade details
    return {
        "name" : name,
        "sid" : int(row["SID"]) if not pd.isna(row["SID"]) and (isinstance(row["SID"], float) or row["SID"].isdigit()) else -1,
        "aid" : row["Assignment Submission ID"],
        "qid" : row["Question Submission ID"],
        "email" : row["Email"],
        "comments" : row["Comments"],
        "question" : question_name,
        "grader" : row["Grader"],
        "grade" : scores,
        "adjustment": 0 if pd.isna(row['Adjustment']) else row['Adjustment'],
        "total_score" : gs_score,
        "was_submitted" : was_submitted,
        "inc_score" : incomplete_score,
        "errors" : errors,
        "url": "https://www.gradescope.com/courses/288777/assignments/" + \
                gsAssignmentID + "/submissions/" + \
                row["Assignment Submission ID"] + "#" + "Question_" + str(question_num)
    }

# Check for outliers *within* students' question grades (for the same assignment)
# :: grades must be the same assignment, where every question is worth the same # of points
# :: pt_diff is how many points difference between question grades before we flag the grades
def outlier_check(grades, pt_diff=5):
    outliers = dict()

    # Bucket grades by student
    student_submissions = dict()
    for g in grades:
        # Skip unsubmitted or incomplete score grades
        if g['was_submitted'] == False or g['inc_score'] == True: continue
        elif g['sid'] in student_submissions:
            student_submissions[g['sid']].append(g)
        else:
            student_submissions[g['sid']] = [ g ]

    # For each student, check for outlier pattern:
    print('Wide variations between grades for specific students')
    print('-----------------------------------------------------')
    for (sid, question_grades) in student_submissions.items():
        init_score = -1
        for g in question_grades:
            if init_score == -1:
                init_score = g['total_score']
            elif abs(g['total_score'] - init_score) >= pt_diff:
                # Flag this students' grades as inconsistent
                print('Wide variation for student {} {} ({} pt difference)'.format(g['name'], g['email'], abs(g['total_score'] - init_score)))
                for g in question_grades:
                    print(' > Question: {}\tScore: {}\tGrader: {:>16s}\tURL: {}'.format(g['question'], g['total_score'], g['grader'][:16], g['url']))
                outliers[sid] = question_grades
                print()
                break

    return outliers

# Is a TA consistently grading higher or lower than others (for the given grades)?
def ta_stats(grades):
    # Bucket grades by grader
    graders = dict()
    for g in grades:
        # Skip unsubmitted or incomplete score grades
        if g['was_submitted'] == False or g['inc_score'] == True: continue
        elif g['grader'] in graders:
            graders[g['grader']].append(g)
        else:
            graders[g['grader']] = [ g ]
    # Calculate mean+st.dev per grader
    graders_scores = dict()
    for (gname, qs) in graders.items():
        graders_scores[gname] = [(g['total_score'], g['name'], g['email'], g['url']) for g in qs]
    return graders_scores

def ta_consistency_check(grades):
    print('{:<20s}\t{}\t{}'.format('TA Name', 'Num graded', 'Mean, St. Dev'))
    print('-----------------------------------------------------')
    graders_scores = ta_stats(grades)
    graders_stats = []
    all_scores = []
    outliers = []

    # Detect total mean + st dev
    for gname, data in graders_scores.items():
        scores = [d[0] for d in data]
        if not isinstance(gname, str): continue
        if len(scores) == 0: continue
        all_scores.extend(scores)

    if len(all_scores) == 0:
        print("No scores detected.")
        return

    total_stdev = stat.stdev(all_scores)
    total_med = stat.median(all_scores)

    for gname, data in graders_scores.items():
        if not isinstance(gname, str): continue
        scores = [d[0] for d in data]
        if len(scores) == 0: continue
        elif len(scores) == 1:
            graders_stats.append((gname, 1, scores[0], 0))
        else:
            for d in data:
                score = d[0]
                if abs(score-total_med) > total_stdev*2.5: # flag outliers
                    outliers.append((gname, score, d[1:]))
            graders_stats.append((gname, len(scores), stat.mean(scores), stat.stdev(scores)))

    graders_stats.sort(key=lambda x: x[2])
    for (gname, n, m, sd) in graders_stats:
        print('{:<20s}\t{:<10s}\t{:.2f}\t{:.2f}'.format(gname[:20], str(n), m, sd))

    if len(outliers) > 0:
        print('\nDetected outliers (grader scores that are 2.5 st. deviations away from total median score):')
        for o in outliers:
            print(o[0], o[1], o[2])

# Command-line loading.
if __name__ == "__main__":
    import load

    # Ask for which assignment to load:
    assn_name, assn_info = load.promptSelectAssignment()
    rubric_path = assn_info["rubric"]
    csv_dir = assn_info["data"]

    # Calculate grades
    grades, rubric, questions = load_grades(rubric_path, csv_dir, only_submitted=False)
    qkeys = sorted(list(questions.keys()))
    num_questions = len(questions)

    if num_questions > 1:
        print('\n')
        outlier_check(grades)
    print('\n')
    ta_consistency_check(grades)

    # Special check --unassigned questions:
    total_unassigned = []
    unassigned = dict()
    unassigned_urls = dict()
    unscored = [g for g in grades if g['was_submitted'] is False and g['total_score'] == 0]
    for g in unscored:
        email = g['email']
        if email not in unassigned_urls: unassigned_urls[email] = g['url'].split("#")[0]
        if email not in unassigned: unassigned[email] = 1
        else: unassigned[email] += 1
    for key, num_unassigned in unassigned.items():
        if num_unassigned == num_questions:
            print("\nUnassigned detected for", key, unassigned_urls[key])
            total_unassigned.append(["", "*Unassigned*", unassigned_urls[key]])
    print("Total unassigned: ", len(total_unassigned))
    df_unassigned = pd.DataFrame(total_unassigned, columns=["Grader", "Question", "URL"])
    df_unassigned.to_csv("unassigned_to_question.csv", index=False)

    # If there's more than one question, count the grading progress of each:
    is_late_submitter = additional_scores_sheet is not None
    graded_but_score_zero = []
    if num_questions > 1:
        print("\nPer question completion rates (assumes you've included a 'was submitted' rubric item per question and filled this out for all submissions):")
        completion_rates = []
        for q in qkeys:
            submitted = [g for g in grades if g['was_submitted'] is True and g['question'] is q]
            submitted_ungraded = [g for g in submitted if g['total_score'] == 0 or g['inc_score'] is True]

            # print("For question", q)
            # for g in submitted:
            #     print(g['grader'], g['name'], g['total_score'])

            # print("For question", q)
            # ta_consistency_check(submitted)

            if is_late_submitter: # if we have late submission information from the Download Grades sheet...
                submitted_ontime = [g for g in submitted if g['late'] == 0]
                submitted_ungraded_ontime = [g for g in submitted if g['late'] == 0 and (g['total_score'] == 0 or g['inc_score'] is True)]
                completion_rates.append( (q, len(submitted)-len(submitted_ungraded), len(submitted_ungraded), \
                                              len(submitted_ontime)-len(submitted_ungraded_ontime), len(submitted_ungraded_ontime)))
            else:
                completion_rates.append( (q, len(submitted)-len(submitted_ungraded), len(submitted_ungraded)) )

        if is_late_submitter:
            for (q, num_graded, num_ungraded, num_graded_ontime, num_ungraded_ontime) in completion_rates:
                total_submitted = num_graded + num_ungraded
                total_ontime = num_graded_ontime + num_ungraded_ontime
                print(" > {}:\t{} / {} total graded ({:.0f}%),\t{} / {} ontime graded ({:.0f}%)".format(q, num_graded, total_submitted, 100 if total_submitted==0 else 100*num_graded/total_submitted, num_graded_ontime, total_ontime, 100 if total_ontime==0 else 100*num_graded_ontime/total_ontime))
        else:
            for (q, num_graded, num_ungraded) in completion_rates:
                total_submitted = num_graded + num_ungraded
                print(" > {}:\t{} / {} graded ({:.0f}%)".format(q, num_graded, total_submitted, 100 if total_submitted==0 else 100*num_graded/(num_graded+num_ungraded)))

    # We need to remove all non-submissions to each question before doing useful operations
    grades = [g for g in grades if g['was_submitted'] is True]

    student_submissions = dict()
    for g in grades:
        if g['sid'] in student_submissions:
            student_submissions[g['sid']].append(g)
        else:
            student_submissions[g['sid']] = [ g ]

    # Export all grades, sorted by student and question:
    export_cols = ["Name", "Email", "Question", "Grader", "Comments", "Adjustment", "Total Score"]
    item_names = rubric['shortnames'].keys()
    export_cols.extend(item_names)
    export_cols.extend(["URL", "SID", "Assignment Submission ID", "Question Submission ID"])
    export_grades = []
    for g in grades:
        if g['inc_score'] == True: continue
        row = [ g['name'], g['email'], g['question'], g['grader'], g['comments'], g['adjustment'], g['total_score'] ]
        row.extend([score for _, score in g['grade'].items()])
        row.extend([g['url'], g['sid'], g['aid'], g['qid']])
        export_grades.append(row)
    export_grades.sort(key=lambda r: (r[0], r[2]))
    df_grades = pd.DataFrame(export_grades, columns=export_cols)
    df_grades.to_csv("all_grades.csv", index=False)

    # Export only what is left to grade:
    export_cols = ["Grader", "Question", "URL"]
    export_grades = []
    for g in grades:
        if g['inc_score'] == False:
            if g['total_score'] == 0: # check for weird graded-but-zero assignments:
                export_grades.append([ g['grader'], "Warning: Grade is 0 but marked as fully graded.", g['url'] ])
            continue
        export_grades.append([ g['grader'], g['question'], g['url'] ])
    export_grades += total_unassigned
    export_grades.sort(key=lambda r: r[1])
    df_leftgrades = pd.DataFrame(export_grades, columns=export_cols)
    df_leftgrades.to_csv("left_to_grade.csv", index=False)

    # Collect grading errors into a spreadsheet
    aggr_errs = []
    for sid, gs in student_submissions.items():
        for g in gs:
            for e in g['errors']:
                aggr_errs.append( [str(datetime.datetime.now()), e, g['grader'], g['comments'], g['question'], g['url'] ] )
    aggr_errs.sort(key=lambda r: (r[0], r[1], r[2], r[4])) # sort on time first, then error type, then grader, then question #
    df_errs = pd.DataFrame(aggr_errs, columns=["First seen", "Issue", "Grader", "Comments", "Question", "URL"])

    if ERROR_CHECK_PERSISTENCE and os.path.exists("grading_errors.csv"):
        # Load the prior error list, if it exists
        df_prev = pd.read_csv("grading_errors.csv")
        df_prev['Question'] = df_prev['Question'].astype(str) # a fix since single-question csvs have the name "1" which confuses pandas
        # Find which rows are *shared* between the prior error check and the current one (excluding timestamp column)
        df_shared_rows = df_prev.merge(df_errs.drop(columns=['First seen'], inplace=False), how='inner', indicator=False)
        # Find rows in the current errors which are new (not in prev list)
        df_new_errs = df_errs.merge(df_prev.drop(columns=['First seen'], inplace=False), \
                            how ='outer', indicator=True).loc[lambda x:x['_merge']=='left_only']
        # Merge the new with the old, which keeps the timestamps:
        df_merged_errs = pd.concat([df_new_errs, df_shared_rows], ignore_index=True, sort=False)
        df_merged_errs.drop(columns=['_merge'], inplace=False).to_csv("grading_errors.csv", index=False)
    else:
        df_errs.to_csv("grading_errors.csv", index=False)

    # Collect student 'missed questions' into a spreadsheet
    if num_questions > 1:
        if 'expectedQuestionsAnswered' not in rubric:
            print("Error: Cannot export which students are missing questions. Set expectedQuestionsAnswered in rubric.")
        else:
            # Loop through students
            students_missing_qs = []
            for sid, gs in student_submissions.items():
                if len(gs) != rubric['expectedQuestionsAnswered']:
                    students_missing_qs.append( [sid, gs[0]['name'], gs[0]['email'], rubric['expectedQuestionsAnswered']-len(gs)] )
            df_miss = pd.DataFrame(students_missing_qs, columns=["SID", "Name", "Email", "Number Missing"])
            df_miss.to_csv("missing_questions.csv", index=False)

    # Show TA grade distribution
    if SHOW_TA_GRADE_DIST:
        import matplotlib
        matplotlib.use('TkAgg')
        import matplotlib.pyplot as plt

        def set_axis_style(ax, labels):
            ax.xaxis.set_tick_params(direction='out')
            ax.xaxis.set_ticks_position('bottom')
            ax.set_xticks(np.arange(1, len(labels) + 1))
            ax.set_xticklabels(labels)
            ax.set_xlim(0.25, len(labels) + 0.75)
            ax.set_xlabel('Grader Name')

        complete_grades = [g for g in grades if g['inc_score'] == False]
        graders_scores = [(g, d) for g, d in ta_stats(complete_grades).items()]
        graders_scores.sort(key=lambda x: stat.mean([d[0] for d in x[1]]))
        data = [np.array(sorted([d[0] for d in data])) for (_, data) in graders_scores] #, dtype=object)
        total_mean = np.median(np.hstack(data))

        fig, ax1 = plt.subplots(nrows=1, ncols=1, figsize=(16, 6), sharey=True)

        ax1.set_title('TA Score Distribution')
        ax1.set_ylabel('Scores')
        plt.xticks(rotation = 90) # Rotates X-Axis Ticks by 45-degrees
        ax1.violinplot(data)

        plt.axhline(y=total_mean, color='k', linestyle='dashed', linewidth=1)

        # set style for the axes
        if SHOW_TA_GRADE_DIST_ONLY_TA is not None:
            labels = [(g if g == SHOW_TA_GRADE_DIST_ONLY_TA else ".") for (g, _) in graders_scores]
        else:
            labels = [(g + " ({})".format(len(_))) for (g, _) in graders_scores]
        for ax in [ax1]:
            set_axis_style(ax, labels)

        plt.subplots_adjust(bottom=0.4, wspace=0.05)
        plt.show()

    # Calculate grading distributions per rubric item
    # item_scores = [[] for i in range(len(rubric['shortnames']))]
    # for g in grades:
    #     for i, key in enumerate(g['grade']):
    #         item_scores[i].append(g['grade'][key])
    #
    # for i, name in enumerate(rubric['shortnames']):
    #     print(name)
    #     dist = item_scores[i]
    #     print(stat.median(dist))
    #     print(stat.mean(dist))
    #     print(stat.stdev(dist))
