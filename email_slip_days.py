# Import smtplib for the actual sending function
import smtplib, ssl
import time
import os
import pandas as pd
import load
from getpass import getpass

# Load central config json
config = load.config()

TEMP_STORAGE = "./_temp_passed_emails.txt"
SLIP_DAYS_CSV = config["slipDaysCSVExportPath"]

# Special mode to print output to console
PRINT_TO_CONSOLE = input("If you want to email everyone in {}, type 'e'. Otherwise, type anything else to print to console.".format(SLIP_DAYS_CSV))
if PRINT_TO_CONSOLE == 'e':
    PRINT_TO_CONSOLE = False
    check = input("Are you sure you want to email everyone in {}? If so, type 'y': ".format(SLIP_DAYS_CSV))
    if check != 'y':
        print("Exiting. Come back when you're ready!")
        exit(0)
else:
    PRINT_TO_CONSOLE = True

# Import slip days data
df_slips = pd.read_csv(SLIP_DAYS_CSV).dropna(how='all')

# Generate message data
def gen_messages(df_slips):
    msgs = []
    # Loop through all slip days entries
    for _, row in df_slips.iterrows():
        name = row['Name']
        receiver_email = row['Email'].strip().lower()
        slips = row['Slip Days Remaining']

        low_slip_msg = "" if slips > 2 else " If you have negative slip days, you are out of slip days and have handed in at least one assignment late with a deduction."

        missing_assns_msg = row['Missing Assignments']
        something_missing = False if not isinstance(missing_assns_msg, str) else (len(missing_assns_msg) > 0)
        if something_missing:
            missing_assns_msg = "We have detected that you're missing {} assignment submission(s), including:\n - ".format(len(missing_assns_msg.split("\n"))-1) + \
                                "\n - ".join(row['Missing Assignments'].split("\n"))[:-4]
        else:
            missing_assns_msg = "We have detected that you've submitted all major assignments so far. Great job! :)"

        late_assns_msg = row['Late Assignments']
        something_late = False if not isinstance(late_assns_msg, str) else (len(late_assns_msg) > 0)
        if something_late:
            late_assns_msg = "We have detected {} assignment(s) submitted late, including:\n - ".format(len(late_assns_msg.split("\n"))-1) + \
                                "\n - ".join(row['Late Assignments'].split("\n"))[:-4]
        else:
            late_assns_msg = "*Of the assignments you've submitted,* we've detected that you've submitted them all on-time. Awesome!"

        extra_slips_msg = "" if pd.isna(row['Extra Slips']) else row['Extra Slips']

        reply_option = "Do not reply."
        if something_missing or slips < 0:
            reply_option = "You may reply and grad TA Xiaoyan can respond to any concerns."

        message = """Subject: INFO 4240 Slip Days Remaining

Hi {},

This is an automatically generated email, sent by INFO/STS 4240/5240 robots running Python. Just because we're robots doesn't mean we don't care about your performance in the class.

This email summarizes any remaining slip days and outstanding assignments you may have for the course INFO/STS 4240/5240. At the time this email was sent, you have {} slip days remaining. (If you are confused about what slip days are, see course policy: https://courses.infosci.cornell.edu/info4240/2021fa/policies.html#late-policy.{})

{}

{}

The initial number of slip days are {}. {} Note that slip days are only tallied for *submitted* assignments. If you decide not to submit an assignment, it will not factor into your slip days; however, missing assignments heavily affect your grade and are strongly discouraged.

This message was sent from Python. {} If you want to discuss about a problem/difficulty or report a discrepancy, you can ask a question on EdDiscussion, attend office hours, or talk to your section instructor or the professor.
See office hours here: https://courses.infosci.cornell.edu/info4240/2021fa/policies.html""".format(name, slips, low_slip_msg, missing_assns_msg, late_assns_msg, 7, extra_slips_msg, reply_option)

        # Append to messages list
        msgs.append((name, receiver_email, message))

    return msgs

# == GENERATE MESSAGE DATA ==
msgs = gen_messages(df_slips)

# == PRINT EMAILS TO CONSOLE TO CHECK ==
if PRINT_TO_CONSOLE:
    for name, receiver_email, message in msgs:
        print("==========================================")
        print(name, receiver_email, ":\n", message, "\n\n")
    exit(0)

# == SEND EMAILS ==
print("Opening email port...\n(If you're using GMail, please ensure 'Less secure app access' is ON in GMail settings: https://support.google.com/accounts/answer/6010255?hl=en )")
port = 465  # For SSL
smtp_server = "smtp.gmail.com"
sender_email = input("Type your gmail address: ") # Enter your address
password = getpass("Type your password and press enter: ")

# Create a secure SSL context
context = ssl.create_default_context()

# Check if there's already a list of names. This helps us
# keep state as the GMail server might kick us out at random moments.
emails_sent = []
if os.path.isfile(TEMP_STORAGE):
    with open(TEMP_STORAGE) as f:
        txt = f.read()
        emails_sent = txt.split(",")

# Login and send email
excepted = False
with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
    server.login(sender_email, password)
    # Loop through messages to each student
    for name, receiver_email, message in msgs:
        # Skip anyone who has already been messaged:
        if receiver_email in emails_sent: continue

        # Try to send email to student
        print("Sending to", name, receiver_email)
        try:
            server.sendmail(sender_email, receiver_email, message)
        except Exception as e:
            # Server failed us. Print error + break out of loop.
            print("Server error: {0}".format(err))
            excepted = True
            break

        # Keep track of what was sent
        emails_sent.append(receiver_email)

        # Wait 3 seconds so gmail doesn't get angry at us
        time.sleep(3)

# If there was an exception, save which emails were sent.
# Otherwise, delete the "sent emails" file, since everyone's been sent an email.
if excepted:
    print("Terminated prematurely. Saving which emails were successfully sent...")
    txt = ",".join(emails_sent)
    with open(TEMP_STORAGE, 'w') as f:
        f.write(txt)
else:
    if os.path.isfile(TEMP_STORAGE):
        os.remove(TEMP_STORAGE)

print("Done!")
