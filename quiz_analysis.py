from grades import load_grades
import os
import json
import pandas as pd
import dateutil.parser
import numpy as np

''' === SETUP === '''
# Path to the Canvas roster (download Gradebook csv) for this class.
# :: This is used to determine who is still in the class.
PATH_TO_CANVAS_ROSTER = "data/roster/roster.csv"

# Where the quizzes (exported GS analysis csv's) are stored.
# Quizzes must be in format: [month]-[day].csv
PATH_TO_QUIZ_DIR = 'data/quizzes'
PATH_TO_QUIZ_EXCEPTIONS_JSON = "data/quiz_exceptions.json" # could be None

''' === HELPER CODE === '''
# Wrapper class for students
class Student:
    def __init__(self, email, sid, name):
        self.email = email
        self.sid = sid
        self.name = name
        self.grades = dict()

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
''' === END HELPER CODE === '''

''' === LOAD STUDENT ROSTER === '''
# The full list of students in the class, a dict of Student objs indexed by sid
roster = dict()
df = pd.read_csv(PATH_TO_CANVAS_ROSTER)
df.drop(index=[1, 2, len(df)-1], inplace=True)
df.dropna(subset=['SIS User ID'], inplace=True)
def read_student(row):
    sid = int(row['SIS User ID'])
    email = row['SIS Login ID']+"@cornell.edu"
    name = row['Student']
    roster[sid] = Student(email, sid, name)
    roster[sid].set_grade('extra_credit_1', float(row['Active Learning Initiative Survey (221004)']))
df.apply(read_student, axis=1)

''' === LOAD QUIZ GRADES === '''
# :: Quiz names should be in format: [Month#]-[Day#]
quiz_exceptions = {}
if PATH_TO_QUIZ_EXCEPTIONS_JSON:
    with open(PATH_TO_QUIZ_EXCEPTIONS_JSON) as f:
      quiz_exceptions = json.load(f)
quizzes = []
for entry in os.scandir(PATH_TO_QUIZ_DIR):
    if not entry.path.endswith(".csv"): continue

    # Extract file name
    filename = os.path.splitext(os.path.basename(entry.path))[0]
    assn_name = 'quiz-'+filename
    quizzes.append(assn_name)

    # Calculate the proper submission time for this quiz,
    # assuming csv files are named with the dates quizzes were due...
    month, day = filename.split('-')
    if len(day) == 1:
        day = '0'+day
    # Note that it SHOULD be 16:20 UTC to correspond to 12:20 EST, HOWEVER
    # for some reason Canvas is off by 1 hour (maybe daylight savings...?)
    # :: I give 1 minute grace period for quizzes
    if int(month) < 4 or (int(month) == 3 and int(day) < 14):
        proper_submission_time = dateutil.parser.parse('2021-0{}-{} 17:21:00 UTC'.format(month, day))
    else:
        proper_submission_time = dateutil.parser.parse('2021-0{}-{} 16:21:00 UTC'.format(month, day))

    # Special exception quizzes
    if int(month) == 3 and int(day) == 25:
        proper_submission_time = dateutil.parser.parse('2021-0{}-{} 03:59:00 UTC'.format(month, int(day)+1))

    def calc_quiz_grade(row):
        sid = row['sis_id']
        if sid not in roster: return # if person dropped the class, skip
        if filename in quiz_exceptions and \
            sid in quiz_exceptions[filename]: return # people exempt from specific quizzes
        datestring = row['submitted']
        time_submitted = dateutil.parser.parse(datestring)
        is_late = time_submitted > proper_submission_time # if it's late
        score = 0.5 if is_late else 1
        roster[sid].set_grade(assn_name, score)

    # Read quiz data
    df = pd.read_csv(entry.path)

    # Keep only the very *first* attempt (we only care about lateness, not score)
    # :: https://stackoverflow.com/questions/15705630/get-the-rows-which-have-the-max-value-in-groups-using-groupby
    df.sort_values('attempt', ascending=True).drop_duplicates(['sis_id'], inplace=True)

    # For each student's attempt, calculate lateness + final score:
    df.apply(calc_quiz_grade, axis=1)

for sid, student in roster.items():
    quiz_total_perc = sum([student.grade_for(q) for q in quizzes]) / len(quizzes)
    print("{} ({:.2f}%):".format(student.name, quiz_total_perc*100))
    for q in quizzes:
        grade = student.grade_for(q)
        if grade < 1.0:
            print("\t{}:\t{:.2f}".format(q, grade*100))
