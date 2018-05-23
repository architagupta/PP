import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def sendEmail(to,subject,body):
  try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login("perfectpicture905@gmail.com", "minion00")

    msg = MIMEMultipart()
    msg['From'] = 'perfectpicture905@gmail.com'
    msg['To'] = to
    msg['Subject'] = subject
    msgbody = body
    msg.attach(MIMEText(msgbody, 'plain'))
    server.sendmail("perfectpicture905@gmail.com", to, msg.as_string())
    server.quit()
    return True
  except Exception as e:
    print(e)
    return False

print(sendEmail("nairshreya2205@xyz.com","test","test"))
