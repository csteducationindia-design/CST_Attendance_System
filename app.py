import os
import csv
import io
import threading
import urllib.parse
import requests
from flask import Flask, jsonify, render_template, make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import pytz # Handling Timezones properly

app = Flask(__name__)

# --- DATABASE CONFIG ---
base_dir = os.path.abspath(os.path.dirname(__file__))
data_dir = os.path.join(base_dir, 'data')
if not os.path.exists(data_dir): os.makedirs(data_dir)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(data_dir, 'attendance.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELS ---
class Student(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(100))
    parent_mobile = db.Column(db.String(15))

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20))
    date = db.Column(db.String(15))
    entry_time = db.Column(db.String(15))
    exit_time = db.Column(db.String(15))
    parent_mobile = db.Column(db.String(15))

# --- SMS SETTINGS ---
SMS_API_KEY = "sb6DpbNkzTrZmn6M4OOs9Zuu4sVWvv0owEBMrgjEuRo%3D"
SMS_ENTITY_ID = "1701164059159702167"
SMS_SENDER = "CSTINI"
ENTRY_TEMPLATE_ID = "1707176698851172545"
EXIT_TEMPLATE_ID  = "1707176698785611900"
INSTITUTE_PHONE = "7083021167"

# --- HELPER: GET INDIA TIME ---
def get_ist_time():
    # Returns the current time in India (IST)
    utc_now = datetime.utcnow()
    ist_tz = pytz.timezone('Asia/Kolkata')
    return utc_now.replace(tzinfo=pytz.utc).astimezone(ist_tz)

def send_sms_entry(phone, name, time_now):
    if not phone: return # Safety check
    
    msg = f"Dear {name}, {name} entered the class at {time_now}. CST Institute {INSTITUTE_PHONE} www.cste.in"
    msg = urllib.parse.quote(msg)
    
    # Auto-add 91 if missing
    if len(phone) == 10: phone = "91" + phone

    url = f"http://servermsg.com/api/SmsApi/SendSingleApi?apikey={SMS_API_KEY}&SenderID={SMS_SENDER}&Phno={phone}&Msg={msg}&EntityID={SMS_ENTITY_ID}&TemplateID={ENTRY_TEMPLATE_ID}"
    try:
        requests.get(url, timeout=10)
    except Exception as e:
        print(f"SMS Error: {e}")

def send_sms_exit(phone, name, time_now):
    if not phone: return # Safety check

    msg = f"Dear {name}, {name} left the class at {time_now}. CST Institute {INSTITUTE_PHONE} www.cste.in"
    msg = urllib.parse.quote(msg)

    if len(phone) == 10: phone = "91" + phone

    url = f"http://servermsg.com/api/SmsApi/SendSingleApi?apikey={SMS_API_KEY}&SenderID={SMS_SENDER}&Phno={phone}&Msg={msg}&EntityID={SMS_ENTITY_ID}&TemplateID={EXIT_TEMPLATE_ID}"
    try:
        requests.get(url, timeout=10)
    except Exception as e:
        print(f"SMS Error: {e}")

# --- ROUTES ---
@app.route('/scan/<string:student_id>')
def scan(student_id):
    # Use Indian Time (IST)
    now = get_ist_time()
    today_str = now.strftime('%Y-%m-%d')
    display_time = now.strftime('%I:%M %p') # e.g. 02:30 PM

    student = Student.query.get(student_id)
    if not student:
        return jsonify({"error": "Student not registered"}), 404

    # Ensure phone is not None (Prevents Network Error Crash)
    mobile = student.parent_mobile if student.parent_mobile else ""

    record = Attendance.query.filter_by(student_id=student_id, date=today_str).first()

    # --- ENTRY ---
    if not record:
        new = Attendance(student_id=student_id, date=today_str,
                         entry_time=display_time, parent_mobile=mobile)
        db.session.add(new)
        db.session.commit()

        # Send SMS (Safe Threading)
        if mobile:
            threading.Thread(target=send_sms_entry, args=(mobile, student.name, display_time)).start()

        return jsonify({"status": "ENTRY_MARKED", "time": display_time})

    # --- EXIT (Check 1 Hour Rule) ---
    try:
        # We must parse the time carefully
        entry_time_obj = datetime.strptime(record.entry_time, '%I:%M %p').time()
        # Combine today's date with entry time
        entry_dt = datetime.combine(now.date(), entry_time_obj)
        # Add Timezone info to entry_dt so we can compare it with 'now'
        entry_dt = pytz.timezone('Asia/Kolkata').localize(entry_dt)
        
        duration = now - entry_dt
    except:
        # Fallback if time calculation fails
        duration = timedelta(minutes=0)

    if duration >= timedelta(hours=1):
        if record.exit_time:
            return jsonify({"status": "ALREADY_EXITED", "message": "Already scanned out."})

        record.exit_time = display_time
        db.session.commit()

        if mobile:
            threading.Thread(target=send_sms_exit, args=(mobile, student.name, display_time)).start()

        return jsonify({"status": "EXIT_MARKED", "time": display_time})

    else:
        minutes_left = 60 - int(duration.total_seconds() / 60)
        return jsonify({
            "status": "WAIT", 
            "message": f"Class in progress. {minutes_left} mins remaining."
        })

@app.route('/teacher')
def teacher_scanner():
    return render_template('scanner.html')

@app.route('/download_report')
def download_report():
    records = Attendance.query.all()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Student ID', 'Name', 'Date', 'Entry Time', 'Exit Time', 'Phone Number'])
    
    for r in records:
        student = Student.query.get(r.student_id)
        name = student.name if student else "Unknown"
        mobile = student.parent_mobile if student else r.parent_mobile
        #cw.writerow([r.student_id, name, r.date, r.entry_time, r.exit_time, mobile])
	# Force Excel to read as text by adding '
        mobile_str = f"'{mobile}" 
        cw.writerow([r.student_id, name, r.date, r.entry_time, r.exit_time, mobile_str])

        
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=monthly_attendance_report.csv"
    output.headers["Content-type"] = "text/csv"
    return output

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)