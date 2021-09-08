# Import smtplib for the actual sending function
import smtplib, ssl
import time

# Special mode to print output to console
PRINT_TO_CONSOLE = True

# DON'T RUN THIS SCRIPT UNLESS YOU'RE READY!
if not PRINT_TO_CONSOLE:
    exit(0) # if ready, change this to "pass"

# Import slip days data
import pandas as pd
df_slips = pd.read_csv("data/slip_days.csv")

# Generate message data
def gen_messages(df_slips):
    msgs = []
    # Loop through all slip days entries
    for _, row in df_slips.iterrows():
        name = row['Name']
        receiver_email = row['Email'].strip().lower()
        slips = row['Slip Days Remaining']

        low_slip_msg = "" if slips > 1 else " If you have negative slip days, you are out of slip days and have handed in at least one assignment late with a deduction."

        missing_assns_msg = row['Missing Assignments']
        something_missing = False if not isinstance(missing_assns_msg, str) else (len(missing_assns_msg) > 0)
        if something_missing:
            missing_assns_msg = "We have detected that you haven't submitted {} assignments, including:\n - ".format(len(missing_assns_msg.split("\n"))-1) + \
                                "\n - ".join(row['Missing Assignments'].split("\n"))[:-4]
        else:
            missing_assns_msg = "We have detected that you have submitted all major assignments so far. Great job! :)"

        reply_option = "Do not reply."
        if something_missing or slips < 0:
            "You may reply and grad TA Xiaoyan can respond to any concerns."

        message = """Subject: INFO 4240 Slip Days Remaining

Hi {},

This is an automatically generated email, sent by INFO/STS 4240/5240 robots running Python. Just because we're robots doesn't mean we don't care about your performance in the class.

This email summarizes any remaining slip days and outstanding assignments you may have for the course INFO/STS 4240/5240. At the time this email was sent, you have {} slip days remaining. (If you are confused about what slip days are, see course policy: https://courses.infosci.cornell.edu/info4240/2021fa/policies.html#late-policy.{})

{}

Note that slip days are only tallied for *submitted* assignments. If you decide not to submit an assignment, it will not factor into your slip days; however, missing assignments heavily affect your grade and are strongly discouraged.

This message was sent from Python. {} If you want to discuss about a problem/difficulty or report a discrepancy, you can ask a question on EdDiscussion, attend office hours, or talk to your section instructor or the professor.
See office hours here: https://courses.infosci.cornell.edu/info4240/2021fa/policies.html""".format(name, slips, low_slip_msg, missing_assns_msg, reply_option)

        # Append to messages list
        msgs.append((name, receiver_email, message))

    return msgs

# == GENERATE MESSAGE DATA ==
msgs = gen_messages(df_slips)

# == PRINT EMAILS TO CONSOLE TO CHECK ==
if PRINT_TO_CONSOLE:
    for name, receiver_email, message in msgs:
        print(name, receiver_email, ":\n", message, "\n\n")
    exit(0)

# == SEND EMAILS ==
port = 465  # For SSL
smtp_server = "smtp.gmail.com"
sender_email = "xl656@cornell.edu"  # Enter your address
password = input("Type your password and press enter: ")

# Create a secure SSL context
context = ssl.create_default_context()

# Login and send email
with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
    server.login(sender_email, password)
    # Loop through messages to each student
    for name, receiver_email, message in msgs:
        # Send email to student
        print("Sending to", name, receiver_email)
        server.sendmail(sender_email, receiver_email, message)

        # Wait 3 seconds so gmail doesn't get angry at us
        time.sleep(3)
