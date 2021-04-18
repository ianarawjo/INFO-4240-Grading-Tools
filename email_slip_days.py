# Import smtplib for the actual sending function
import smtplib, ssl
import time

# Import slip days data
import pandas as pd
df_slips = pd.read_csv("slip_days.csv")

# DONT RUN THIS SCRIPT UNLESS YOU'RE READY!
exit(0)

port = 465  # For SSL
smtp_server = "smtp.gmail.com"
sender_email = "iaa32@cornell.edu"  # Enter your address
password = input("Type your password and press enter: ")

# Create a secure SSL context
context = ssl.create_default_context()

# Login and send email
with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
    server.login(sender_email, password)

    # Loop through all slip days entries
    for _, row in df_slips.iterrows():
        name = row['Name']
        receiver_email = row['Email'].strip().lower()
        slips = row['Slip Days Remaining']

        if int(slips) < 0:
            message = """\
Subject: INFO 4240 Slip Days Remaining

Hi {},\n
You have {} slip days remaining for use in assignments in INFO 4240. This calculation includes all major assignments prior to MiniProject 3.
-> If you have negative slip days, you are out of slip days and have handed in at least one assignment late with a deduction.\n
This message was sent from Python. Do not reply. If you want to report a discrepency, report on EdDiscussion or contact one of your section TAs.""".format(name, slips)
        else:
            message = """\
Subject: INFO 4240 Slip Days Remaining

Hi {},\n
You have {} slip days remaining for use in assignments in INFO 4240. This calculation includes all major assignments prior to MiniProject 3.\n
This message was sent from Python. Do not reply. If you want to report a discrepency, report on EdDiscussion, attend office hours, or contact one of your section TAs.""".format(name, slips)

        # print(name, receiver_email, slips, message)

        # Send email
        print("Sending to", name, receiver_email)
        server.sendmail(sender_email, receiver_email, message)

        # Wait 1 seconds so gmail doesn't get angry at us
        time.sleep(1)
