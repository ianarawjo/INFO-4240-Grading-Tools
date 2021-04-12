from grades import load_grades

# == PART YOU SHOULD EDIT ==
# Put filepath of rubric to use for this assignment. Rubric is JSON file.
group_rubric_path = 'rubrics/workbook2.json'
indiv_rubric_path = 'rubrics/...json'
# Put directory where you're storing all the CSVs for this specific assignment.
# :: Generate CSVs from clicking "Export Evaluations" in GradeScope.
group_csv_dir = "data/dw2"
indiv_csv_dir = "" # needs to be a different folder
# ===========================

rubric_path = ''
group_grades, _, _ = load_grades(group_rubric_path, group_csv_dir, only_submitted=False)
indiv_grades, _, _ = load_grades(indiv_rubric_path, indiv_csv_dir, only_submitted=False)

# Identify and bucket groups (the lazy way)
assnIds = set([g['aid'] for g in group_grades])
groups = []
for aid in assnIds:
    members = [g for g in group_grades if g['aid'] == assnIds]
    indivs = []
    for m in members:
        indiv = [g for g in indiv_grades if g['sid'] == m['sid']]
        if len(indiv) == 0:
            print("No individual submission for student", m['name'], m['sid'])
        elif len(indiv) > 1:
            print("Somehow, individual student", m['name'], m['sid'], 'submitted twice! O___O')
        else:
            indivs.append(indiv[0])
    groups.append((aid, members, indivs))

# Print connected submissions to csv
export_cols = ["Group #", "Group Submission", "Member 1", "Member 1 Submission", "Member 2", "Member 2 Submission"]
export_grades = []
for (aid, members, indivs) in groups:
    row = [ aid, members[0]['url'], indivs[0]['name'], indivs[0]['url'] ]
    if len(indivs) > 1:
        row.extend([indivs[1]['name'], indivs[1]['url']])
    else:
        row.extend(['N/A', 'N/A'])
    export_grades.append(row)

export_grades.sort(key=lambda r: r[0])
df_grades = pd.DataFrame(export_grades, columns=export_cols)
df_grades.to_csv("conn_group_indiv.csv", index=False)
