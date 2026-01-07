import os
import csv
import io
import threading
import urllib.parse
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, jsonify, render_template, make_response, request, session, redirect, url_for, render_template_string
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import pytz 
import traceback 

app = Flask(__name__)
app.secret_key = 'cst_secure_key_2026' 

# --- DATABASE CONFIG ---
base_dir = os.path.abspath(os.path.dirname(__file__))
data_dir = os.path.join(base_dir, 'data')
if not os.path.exists(data_dir): os.makedirs(data_dir)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(data_dir, 'attendance.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ================= LOGIN CONFIG =================
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Cst@11210143" 

# ================= CREDENTIALS =================
SMS_API_KEY = "sb6DpbNkzTrZmn6M4OOs9Zuu4sVWvv0owEBMrgjEuRo%3D"
SMS_ENTITY_ID = "1701164059159702167"
SMS_SENDER = "CSTINI"

# ✅ NEW APPROVED ENTRY TEMPLATE ID
ENTRY_TEMPLATE_ID = "1707176777667925464"

# Exit Template ID (Keep the working one)
EXIT_TEMPLATE_ID  = "1707176745232982829"  

INSTITUTE_PHONE = "7083021167"

# EMAIL CONFIG
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "cst.institute@gmail.com"     
SENDER_PASSWORD = "fafp tmkc ghsd sawe"   

# WHATSAPP CONFIG
WHATSAPP_TOKEN = ""       
WHATSAPP_PHONE_ID = ""    

# ================= MODELS =================
class Student(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(100))
    parent_mobile = db.Column(db.String(15))
    parent_email = db.Column(db.String(100))

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20))
    date = db.Column(db.String(15))
    entry_time = db.Column(db.String(15))
    exit_time = db.Column(db.String(15))
    parent_mobile = db.Column(db.String(15))

# ================= HELPERS =================
def get_ist_time():
    utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)
    return utc_now.astimezone(pytz.timezone('Asia/Kolkata'))

def send_sms(phone, msg, template_id):
    if not phone: return
    if len(phone) == 10: phone = "91" + phone
    encoded_msg = urllib.parse.quote(msg)
    url = f"http://servermsg.com/api/SmsApi/SendSingleApi?apikey={SMS_API_KEY}&SenderID={SMS_SENDER}&Phno={phone}&Msg={encoded_msg}&EntityID={SMS_ENTITY_ID}&TemplateID={template_id}"
    try: 
        # Debug print to help check status in logs
        response = requests.get(url, timeout=10)
        print(f"SMS SENT TO {phone} | TEMPLATE: {template_id} | STATUS: {response.text}")
    except Exception as e: 
        print(f"SMS FAILED TO {phone}: {str(e)}")

def send_email(to_email, subject, body):
    if not to_email or "@" not in to_email: return
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        server.quit()
    except Exception as e: print(f"Email Error: {e}")

def send_whatsapp(phone, msg_body):
    if not WHATSAPP_TOKEN: return
    if len(phone) == 10: phone = "91" + phone
    url = f"https://graph.facebook.com/v17.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": phone, "type": "text", "text": {"body": msg_body}}
    try: requests.post(url, headers=headers, json=data, timeout=10)
    except: pass

def notify_parents(student, status, time_now):
    if status == "ENTRY":
        # ✅ NEW APPROVED MESSAGE FORMAT
        # "Dear {Name}, entered the class at {Time}. CST Education India 7083021167"
        sms_msg = f"Dear {student.name}, entered the class at {time_now}. CST Education India 7083021167"
        
        email_sub = f"Entry Alert: {student.name}"
        email_body = f"Dear Parent,\n\n{student.name} has reached the institute at {time_now}.\n\n- CST Institute"
        wa_body = f"✅ *Entry Alert*\nStudent: {student.name}\nTime: {time_now}\nStatus: Present"
        tid = ENTRY_TEMPLATE_ID
    else:
        # Exit Message (Unchanged)
        sms_msg = f"Dear {student.name}, has successfully completed todays class and has now left CST Education India"
        email_sub = f"Exit Alert: {student.name}"
        email_body = f"Dear Parent,\n\n{student.name} has left the institute at {time_now}.\n\n- CST Education India"
        wa_body = f"👋 *Exit Alert*\nStudent: {student.name}\nTime: {time_now}\nStatus: Left"
        tid = EXIT_TEMPLATE_ID

    threading.Thread(target=send_sms, args=(student.parent_mobile, sms_msg, tid)).start()
    threading.Thread(target=send_email, args=(student.parent_email, email_sub, email_body)).start()
    threading.Thread(target=send_whatsapp, args=(student.parent_mobile, wa_body)).start()

# ================= ROUTES =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ""
    if request.method == 'POST':
        user = request.form.get('username')
        pw = request.form.get('password')
        if user == ADMIN_USERNAME and pw == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('teacher_scanner'))
        else:
            msg = "❌ Wrong Password"
    return render_template_string("""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>CST Login</title>
    <style>body{font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;background:#f0f2f5;margin:0}
    .box{background:white;padding:30px;border-radius:10px;box-shadow:0 4px 10px rgba(0,0,0,0.1);text-align:center;width:300px}
    input{width:90%;padding:10px;margin:10px 0;border:1px solid #ccc;border-radius:5px}
    button{width:100%;padding:10px;background:#007bff;color:white;border:none;border-radius:5px;cursor:pointer}
    </style></head><body><div class="box"><h2>🔐 Teacher Login</h2><form method="post">
    <input type="text" name="username" placeholder="Username" required><input type="password" name="password" placeholder="Password" required>
    <button type="submit">Login</button></form><p style="color:red">{{ msg }}</p></div></body></html>""", msg=msg)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/scan/<string:student_id>')
def scan(student_id):
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized. Please Login."}), 401

    try:
        now = get_ist_time()
        today_str = now.strftime('%d-%m-%Y') 
        
        # ✅ TIME FORMAT: "08.00 AM" (Matches your Alphanumeric DLT settings)
        # Using a DOT (.) instead of a colon to match your sample "8.00 am"
        display_time = now.strftime('%I.%M %p') 

        student = Student.query.get(student_id)
        if not student: return jsonify({"error": "Student not registered"}), 404
        
        record = Attendance.query.filter_by(student_id=student_id, date=today_str).first()
        mobile = student.parent_mobile if student.parent_mobile else ""

        if not record:
            new = Attendance(student_id=student_id, date=today_str, entry_time=display_time, parent_mobile=mobile)
            db.session.add(new)
            db.session.commit()
            notify_parents(student, "ENTRY", display_time)
            return jsonify({"status": "ENTRY_MARKED", "time": display_time})

        try:
            # Parse the time back (handling the dot format)
            # Try dot format first, then fallback to colon
            try:
                entry_time_obj = datetime.strptime(record.entry_time, '%I.%M %p').time()
            except:
                entry_time_obj = datetime.strptime(record.entry_time, '%I:%M %p').time()
                
            entry_dt = now.replace(hour=entry_time_obj.hour, minute=entry_time_obj.minute, second=0, microsecond=0)
            duration = now - entry_dt
        except: duration = timedelta(minutes=0)

        if duration >= timedelta(minutes=45):
            if record.exit_time:
                return jsonify({"status": "ALREADY_EXITED", "message": "Already scanned out."})
            record.exit_time = display_time
            db.session.commit()
            notify_parents(student, "EXIT", display_time)
            return jsonify({"status": "EXIT_MARKED", "time": display_time})
        else:
            minutes_left = 60 - int(duration.total_seconds() / 60)
            return jsonify({"status": "WAIT", "message": f"Class in progress. {minutes_left} mins remaining."})
    
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/teacher')
def teacher_scanner():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('scanner.html')

@app.route('/download_report')
def download_report():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    records = Attendance.query.all()
    si = io.StringIO(); cw = csv.writer(si)
    cw.writerow(['Student ID', 'Name', 'Date', 'Entry Time', 'Exit Time', 'Phone Number'])
    for r in records:
        student = Student.query.get(r.student_id)
        name = student.name if student else "Unknown"
        mobile = student.parent_mobile if student else r.parent_mobile
        mobile_str = f"'{mobile}" 
        cw.writerow([r.student_id, name, r.date, r.entry_time, r.exit_time, mobile_str])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=monthly_attendance_report.csv"
    output.headers["Content-type"] = "text/csv"
    return output

if __name__ == "__main__":
    with app.app_context(): db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)