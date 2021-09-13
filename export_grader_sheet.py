import pandas as pd

df = pd.read_csv('left_to_grade.csv')[['Question', 'URL']]
df.sort_values(by=['Question'], inplace=True)
df["Grader"] = "" # Empty grader column
df["Graded?"] = 0
df["Notes"] = ""
grader_col = df.pop('Grader')
graded_col = df.pop('Graded?')
df.insert(0, 'Graded?', graded_col)
df.insert(0, 'Grader', grader_col)
df.to_csv("grader_sheet_example.csv", index=False)
