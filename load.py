import pandas as pd
import json

# Load config file
# :: Takes: path to central config JSON that specifies locations of assignments, assignment info, etc.
def config(PATH="config.json"):
    with open(PATH, 'r') as f:
        info = json.load(f)
    return info

# Prompt for (valid) assignment name:
def promptSelectAssignment(info=None):
    if info is None:
        info = config()
    name = None
    while name is None:
        print("Enter name of assignment you wish to operate on. Available assignments are:")
        print(" | " + "\n | ".join(info["assignments"].keys()))
        name = input(" > ")
        if name not in info["assignments"]:
            print("Could not find that assignment.")
            name = None
    return name, info["assignments"][name]

# Wrapper class for students
class Student:
    def __init__(self, email, sid, name):
        self.email = email
        self.sid = sid
        self.name = name
        self.grades = dict()
        self.missing_submissions = dict()
        self.late_submissions = dict()

    # Return the students' grade for the given assignment.
    # :: If the grade's missing, count as a zero.
    def grade_for(self, assn):
        return self.grades[assn] if assn in self.grades else 0

    def set_grade(self, assn, score):
        self.grades[assn] = score

    def add_grade(self, assn, score):
        if assn in self.grades:
            self.grades[assn] += score
        else:
            self.grades[assn] = score

    def flag_missing_submission(self, assn, lateness):
        self.missing_submissions[assn] = lateness

    def flag_late_submission(self, assn, lateness):
        self.late_submissions[assn] = lateness

# Load Canvas roster. Outputs dict of Student objects indexed by SID.
def roster(PATH_TO_CANVAS_ROSTER):
    roster = dict()
    df = pd.read_csv(PATH_TO_CANVAS_ROSTER)
    df.drop(index=[1, 2, len(df)-1], inplace=True)
    df.dropna(subset=['SIS User ID'], inplace=True)
    def read_student(row):
        sid = int(row['SIS User ID'])
        email = row['SIS Login ID']+"@cornell.edu"
        name = row['Student']
        roster[sid] = Student(email, sid, name)
    df.apply(read_student, axis=1)
    return roster
