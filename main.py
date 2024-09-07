from flask import Flask, abort, request, Response
import sqlite3, os, datetime
from datetime import datetime as dt
from dotenv import load_dotenv
import gmailconnector as gc

load_dotenv()

reader = gc.ReadEmail(folder=gc.Folder.inbox)
filter1 = gc.Condition.since(since=datetime.date(year=dt.now().year, month=dt.now().month, day=dt.now().day))
filter2 = gc.Condition.subject(subject="New text message")
filter3 = gc.Condition.text(reader.env.gmail_user)
filter4 = gc.Category.not_deleted


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

conn = sqlite3.connect("data.db")
conn.row_factory = dict_factory

c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS addrs (id TEXT PRIMARY KEY, addr TEXT)")
conn.commit()
c.close()

app = Flask(__name__)

@app.get('/findNumber/<number>')
def findNum(number):
    response = reader.instantiate(filters=(filter1, filter2, filter3, filter4))

    try:
        for each_mail in reader.read_mail(messages=response.body, humanize_datetime=False):
            receivedNumber = each_mail.sender_email.split(".")[1][1:]
            domain = each_mail.sender_email.split("@")[1]
            if domain != "txt.voice.google.com": continue
            if number == receivedNumber:
                conn = sqlite3.connect("data.db")
                conn.row_factory = dict_factory
                c = conn.cursor()
                c.execute("SELECT * FROM addrs WHERE id = ?", (number,))
                if c.fetchone() == None:
                    c.execute("INSERT INTO addrs (id, addr) VALUES (?, ?)", (number, each_mail.sender_email))
                    conn.commit()
                c.close()
                return each_mail.sender_email
    except Exception as e:
        return Response(str(e), status=500)
        
@app.post('/text/<number>')
def sendText(number):
    conn = sqlite3.connect("data.db")
    conn.row_factory = dict_factory
    c = conn.cursor()
    c.execute("SELECT * FROM addrs WHERE id = ?", (number,))
    row = c.fetchone()
    c.close()
    if row == None:
        return abort(404)
    addr = row["addr"]
    text = request.json['msg']
    mail_object = gc.SendEmail()
    auth = mail_object.authenticate
    mail_object.send_email(recipient=addr, subject="Text Service", body=text)
    return "Text sent to " + number

app.run(host='0.0.0.0', port=2340, debug=True)
