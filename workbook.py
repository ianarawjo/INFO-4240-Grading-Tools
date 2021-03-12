import pandas as pd
import os
import json
import statistics as stat
from difflib import get_close_matches

# == PART YOU SHOULD EDIT ==
# Put filename of rubric to use. Rubric file should be in the "rubrics" folder.
rubric_filename = 'workbook1.json'
# Put filenames of CSVs, and corresponding shorthand names. CSVs should be in "data" folder.
questions = {
    'Nissembaum': '1_Nissenbaum_How_Computer_Systems_Embody_.csv',
    'Papanek': '2_Papanek_Do-it-Yourself_Murder.csv',
    'Flanagan': '3_Flanagan_et_al_Embodying_Values_in_Tech.csv',
    'Gaver': '4_Gaver_Making_spaces_How_design_workbook.csv',
    'Gaver and Martin': '5_Gaver_and_Martin_Alternatives_exploring.csv',
    'Gaver and Dunne': '6_Gaver_and_Dunne_Projected_realities.csv',
    'Gaver and Bowers': '7_Gaver_and_Bowers_Annotated_Portfolios.csv',
    'Bleeker': '8_Bleecker_Part_1_Design_Fiction_pp_3-8_o.csv',
    'Pierce': '9_Pierce_and_Paulos_Some_variations_on_a_.csv',
    'Edgerton': '10_Edgerton_Significance.csv',
    'Scott': '11_Scott_High-Modernist_City.csv',
    'Refrigerator': '12_How_the_Refrigerator_gets_its_Hum.csv',
    'Infrastructure': '13_Infrastructural_Speculations.csv'
}
# ===========================

# Read in all the grades for a single GS eval sheet
# :: Returns grades as a list of dicts. See end of calc_grade for format.
def read_grades(rubric, question_name, csv):
    df = pd.read_csv(os.path.join("data", csv))
    df.drop(index=[len(df)-1, len(df)-2, len(df)-3, len(df)-4], inplace=True)

    grades = df.apply(lambda row: calc_grade(row, rubric, question_name, df.columns), axis=1)
    grades = [g for g in grades if g is not None] # cull the Nones

    return grades

# Calculate the grade for a specific row of a GS eval sheet
def calc_grade(row, rubric, question_name, col_names):
    scores = dict()
    errors = []
    gsAssignmentID = rubric['gsAssignmentID']
    aggr_method = rubric['aggr_method']
    shortnames = rubric['shortnames']
    rubric = rubric['rubric']
    if pd.isna(row['Score']) or row['Score'] == 0: return None

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
            closest = get_close_matches(term, col_names, 1)[0]
            return closest

    # Calculate score (pts) for each rubric item
    for key, val in rubric.items():
        score = 0

        # Is single rubric item w/ no subitems
        if isinstance(val, int):
            col = col_inc_term(key)
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
    if agg != row['Score']:
        errors.append("Calc grade doesn't match GradeScope." + str(float(row['Adjustment'])))

    # Check for errors in grading
    # Check whether comments are blank
    if not isinstance(row['Comments'], str) or len(row['Comments'].strip()) == 0:
        errors.append("Comment is blank.")
    elif any(s in row['Comments'] for s in ('you', 'You')):
        errors.append("Comment contains the word 'you.'")

    # Return the grade details
    return {
        "name" : row["First Name"] + " " + row["Last Name"],
        "sid" : row["SID"],
        "aid" : row["Assignment Submission ID"],
        "qid" : row["Question Submission ID"],
        "email" : row["Email"],
        "comments" : row["Comments"],
        "question" : question_name,
        "grader" : row["Grader"],
        "grade" : scores,
        "adjustment": 0 if pd.isna(row['Adjustment']) else row['Adjustment'],
        "total_score" : row['Score'],
        "errors" : errors,
        "url": "https://www.gradescope.com/courses/228839/assignments/" + \
                gsAssignmentID + "/submissions/" + \
                row["Assignment Submission ID"] + "#"
    }

# Command-line loading.
if __name__ == "__main__":

    # Load rubric
    with open(os.path.join("rubrics", rubric_filename)) as f:
        rubric = json.load(f)

    # Verify there's an assignment ID so we can generate URLs
    if 'gsAssignmentID' not in rubric:
        print("Error: Gradescope assignment ID (check in URL text) is not present for this rubric. Please include it.")
        exit(0)

    grades = []
    for name, csv in questions.items():
        print("Question:", name, csv)
        gs = read_grades(rubric, name, csv)
        grades.extend(gs)

    student_submissions = dict()
    for g in grades:
        if g['sid'] in student_submissions:
            student_submissions[g['sid']].append(g)
        else:
            student_submissions[g['sid']] = [ g ]

    # Collect grading errors into a spreadsheet
    aggr_errs = []
    for sid, gs in student_submissions.items():
        for g in gs:
            for e in g['errors']:
                aggr_errs.append( [e, g['grader'], g['question'], g['url'] ] )
    aggr_errs.sort(key=lambda r: (r[0], r[1], r[2]))
    for e in aggr_errs:
        print(e)

    df_errs = pd.DataFrame(aggr_errs, columns=["Error", "Grader", "Question", "URL"])
    df_errs.to_csv("grading_errors.csv")

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
