import json
import sys
import pprint

if len(sys.argv) < 2:
    print("Please enter the Gradescope rubric by highlighting the text in the \
           browser window, and copy+paste as an argument to this script (surround with quotes).")

txt = sys.argv[1]

rubric = dict()
cur_header = None
cur_item = None
cur_pts = None
last_token = None
lines = txt.split('\n')
for line in lines:
    if len(line) == 0: continue
    if line == "unapplied rubric item" or line == "applied rubric item": continue
    if line[0] == "+":
        cur_pts = float(line.split(" ")[1])
        last_token = "pts"
        continue
    if last_token == "pts":
        cur_item = line
        last_token = "line"
        if cur_header != None:
            rubric[cur_header][cur_item] = cur_pts
        else:
            rubric[cur_item] = cur_pts
    else:
        cur_header = line
        rubric[cur_header] = dict()

aggr_method = dict()
shortnames = dict()
for key, val in rubric.items():
    aggr_method[key] = "max"
    shortnames[key] = key.split(" ")[0]

out_dict = { "gsAssignmentID": "ENTER", "maxScore":"ENTER", \
  "expectedQuestionsAnswered":"ENTER", "wasNotSubmittedItem":"ENTER", \
  "rubric":rubric, "aggr_method":aggr_method, "shortnames":shortnames }
pprint.pprint(out_dict)

with open('out_rubric.json', 'w', encoding='utf-8') as f:
    json.dump(out_dict, f, ensure_ascii=False, indent=4)
