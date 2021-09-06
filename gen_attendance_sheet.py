from grades import load_grades
import os
import json
import pandas as pd
import dateutil.parser
import numpy as np

''' === SETUP === '''
# Path to the Canvas roster (download Gradebook csv) for this class.
# :: This is used to determine who is still in the class.
PATH_TO_CANVAS_ROSTER_ORIG = "data/roster/roster_fa21_origin.csv"
PATH_TO_CANVAS_ROSTER_CURR = "data/roster/roster_fa21_curr.csv"

''' === LOAD STUDENT ROSTER === '''
# The full list of students in the class, a dict of Student objs indexed by sid
def read_roster(path):
    roster = []
    df = pd.read_csv(path)
    df.drop(index=[1, 2, len(df)-1], inplace=True)
    df.dropna(subset=['SIS User ID'], inplace=True)
    def read_student(row):
        sid = int(row['SIS User ID'])
        email = row['SIS Login ID']+"@cornell.edu"
        name = row['Student']
        section = row['Section']
        section = section.split('and')[0]
        roster.append((section, name, email))
    df.apply(read_student, axis=1)
    return roster

roster_orig = read_roster(PATH_TO_CANVAS_ROSTER_ORIG)
roster_curr = read_roster(PATH_TO_CANVAS_ROSTER_CURR)

for s in roster_curr:
    section, name, email = s
    for t in roster_orig:
        s2, n2, e2 = t
        if e2 != email: continue
        if s2 != section:
            print("Student", name, "changed sections from", s2, "to", section)

''' === SAVE ATTENDANCE SHEET, SORTED BY SECTION === '''
# df_out = pd.DataFrame(roster, columns=["Section", "Name", "Email"])
# df_out.sort_values(by=["Section"]).to_csv("attendance.csv", index=False)
