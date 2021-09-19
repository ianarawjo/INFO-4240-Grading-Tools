# Nice command-line interface for accessing common scripts
import subprocess
OPS = ["analyze_grades", "download_grades", "calc_slips", "email_slips", "mark_reading_not_selected", "open_config"]

# Safely ask for an operation from a constrained list 'ops'.
# If the user doesn't answer correctly, ask again.
def input_op(ops, prompt, error_msg):
    op = None
    while op is None:
        print(prompt)
        print(" | " + "\n | ".join(OPS))
        op = input(" > ")
        if op not in OPS:
            print(error_msg)
            op = None
    return op

op = input_op(OPS, "Which operation do you wish to perform?", "Sorry, I don't recognize that input. Try again.")

if op == "analyze_grades":
    subprocess.call("python grades.py", shell=True)
elif op == "download_grades":
    subprocess.call("python scrapers/watch_grading_sheets.py", shell=True)
elif op == "calc_slips":
    subprocess.call("python slip_days.py", shell=True)
elif op == "email_slips":
    yn = input("Do you want to recalculate slip days first? (y/n): ")
    if yn == "y":
        subprocess.call("python slip_days.py", shell=True)
    print("=== END SLIP DAYS CALCULATION ==\n")
    print("=== BEGIN EMAIL SLIP DAYS SCRIPT ==")
    subprocess.call("python email_slip_days.py", shell=True)
elif op == "mark_reading_not_selected":
    subprocess.call("python scrapers/mark_not_question.py", shell=True)
elif op == "open_config":
    # Only works on MacOS rn
    subprocess.call("open config.json", shell=True)
