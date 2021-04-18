from grades import load_grades
import pandas as pd

# == PART YOU SHOULD EDIT ==
# Put filepath of rubric to use for this assignment. Rubric is JSON file.
group_rubric_path = 'rubrics/mp3_group.json'
indiv_rubric_path = 'rubrics/mp3_indiv.json'
# Put directory where you're storing all the CSVs for this specific assignment.
# :: Generate CSVs from clicking "Export Evaluations" in GradeScope.
group_csv_dir = "data/mp3/group"
indiv_csv_dir = "data/mp3/indiv" # needs to be a different folder
# ===========================

group_grades, _, _ = load_grades(group_rubric_path, group_csv_dir, only_submitted=False)
indiv_grades, _, _ = load_grades(indiv_rubric_path, indiv_csv_dir, only_submitted=False)

# Identify and bucket groups (the lazy way)
assnIds = set([g['aid'] for g in group_grades])
groups = []
for aid in assnIds:
    members = [g for g in group_grades if g['aid'] == aid]
    indivs = []
    for m in members:
        indiv = [g for g in indiv_grades if g['sid'] == m['sid']]
        if len(indiv) == 0:
            print("No individual submission for student", m['name'], m['sid'])
        elif len(indiv) > 1:
            print("Somehow, individual student", m['name'], m['sid'], 'submitted twice! O___O')
        else:
            indivs.append(indiv[0])
    print(aid, len(members), len(indivs))
    groups.append((aid, members, indivs))

# Print connected submissions to csv
export_cols = ["Group #", "Group Submission", "Member 1", "Member 1 Submission", "Member 2", "Member 2 Submission"]
export_grades = []
for (aid, members, indivs) in groups:
    gsub = members[0]['url']
    m1 = members[0]['name']
    m2 = members[1]['name'] if len(members) > 1 else "N/A"
    m1sub = "No submission"
    m2sub = "No submission"
    row = [ aid, gsub, m1 ]
    if len(indivs) > 0:
        m1sub = indivs[0]['url']
    if len(indivs) > 1:
        m2sub = indivs[1]['url']
    row.extend( [m1sub, m2, m2sub] )
    export_grades.append(row)

export_grades.sort(key=lambda r: r[0])
df_grades = pd.DataFrame(export_grades, columns=export_cols)
df_grades.to_csv("conn_group_indiv.csv", index=False)
