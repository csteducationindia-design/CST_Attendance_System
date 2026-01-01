import os
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import requests
import urllib.parse
import threading  # For sending SMS in background without freezing

app = Flask(__name__)

# --- DATABASE CONFIG FOR COOLIFY ---
# This ensures the DB is saved in a 'data' folder we can protect
base_dir = os.path.abspath(os.path.dirname(__file__))
data_dir = os.path.join(base_dir, 'data')

# Create the data folder if it doesn't exist
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(data_dir, 'attendance.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# ---------------- DATABASE ----------------
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

# ---------------- SMS CONFIG ----------------
SMS_API_KEY = "sb6DpbNkzTrZmn6M4OOs9Zuu4sVWvv0owEBMrgjEuRo%3D"
SMS_ENTITY_ID = "1701164059159702167"
SMS_SENDER = "CSTINI"
ENTRY_TEMPLATE_ID = "1707176698851172545"
EXIT_TEMPLATE_ID  = "1707176698785611900"

# 🔥 FIX: Your Institute Number (Hardcoded for DLT Compliance)
INSTITUTE_PHONE = "7083021167"

def send_sms_entry(phone, name, time_now):
    # DLT Template: Dear {name}, {name} entered the class at {time}. CST Institute {InstituteNumber} www.cste.in
    msg = f"Dear {name}, {name} entered the class at {time_now}. CST Institute {INSTITUTE_PHONE} www.cste.in"
    
    # URL Encode the message
    msg = urllib.parse.quote(msg)
    
    # Ensure phone number has country code if needed (optional but recommended)
    # if len(phone) == 10: phone = "91" + phone

    url = f"http://servermsg.com/api/SmsApi/SendSingleApi?apikey={SMS_API_KEY}&SenderID={SMS_SENDER}&Phno={phone}&Msg={msg}&EntityID={SMS_ENTITY_ID}&TemplateID={ENTRY_TEMPLATE_ID}"
    
    try:
        r = requests.get(url, timeout=10)
        print(f"ENTRY SMS SENT to {phone}: {r.text}")
    except Exception as e:
        print(f"ENTRY SMS FAILED: {e}")

def send_sms_exit(phone, name, time_now):
    # DLT Template: Dear {name}, {name} left the class at {time}. CST Institute {InstituteNumber} www.cste.in
    msg = f"Dear {name}, {name} left the class at {time_now}. CST Institute {INSTITUTE_PHONE} www.cste.in"
    
    msg = urllib.parse.quote(msg)

    url = f"http://servermsg.com/api/SmsApi/SendSingleApi?apikey={SMS_API_KEY}&SenderID={SMS_SENDER}&Phno={phone}&Msg={msg}&EntityID={SMS_ENTITY_ID}&TemplateID={EXIT_TEMPLATE_ID}"

    try:
        r = requests.get(url, timeout=10)
        print(f"EXIT SMS SENT to {phone}: {r.text}")
    except Exception as e:
        print(f"EXIT SMS FAILED: {e}")

# ---------------- QR SCAN LOGIC ----------------
@app.route('/scan/<string:student_id>')
def scan(student_id):
    # Get current time
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    
    # User-Friendly Time (e.g., "08:00 AM" or "08.00 am")
    # Using standard AM/PM format. If DLT is strict about dots (8.00), change ':' to '.' below.
    display_time = now.strftime('%I:%M %p') 

    student = Student.query.get(student_id)
    if not student:
        return jsonify({"error": "Student not registered"}), 404

    record = Attendance.query.filter_by(student_id=student_id, date=today_str).first()

    # --- SCENARIO 1: ENTRY ---
    if not record:
        new = Attendance(student_id=student_id, date=today_str,
                         entry_time=display_time, parent_mobile=student.parent_mobile)
        db.session.add(new)
        db.session.commit()

        # Run SMS in background thread (Prevent freezing)
        threading.Thread(target=send_sms_entry, args=(student.parent_mobile, student.name, display_time)).start()

        return jsonify({"status": "ENTRY_MARKED", "time": display_time})

    # --- SCENARIO 2: EXIT (After 1 Hour) ---
    
    # Robust Time Parsing (Handles both 24hr and AM/PM formats in DB)
    try:
        entry_time_obj = datetime.strptime(record.entry_time, '%I:%M %p').time()
    except ValueError:
        try:
            entry_time_obj = datetime.strptime(record.entry_time, '%H:%M:%S').time()
        except ValueError:
             # Fallback if format is completely different
             return jsonify({"error": "Time format error in DB"}), 500

    entry_dt = datetime.combine(now.date(), entry_time_obj)
    duration = now - entry_dt

    # Check 1 Hour Condition
    if duration >= timedelta(hours=1):
        if record.exit_time:
            return jsonify({"status": "ALREADY_EXITED", "message": "Already scanned out."})

        record.exit_time = display_time
        db.session.commit()

        threading.Thread(target=send_sms_exit, args=(student.parent_mobile, student.name, display_time)).start()

        return jsonify({"status": "EXIT_MARKED", "time": display_time})

    else:
        minutes_left = 60 - int(duration.total_seconds() / 60)
        return jsonify({
            "status": "WAIT", 
            "message": f"Class in progress. {minutes_left} mins remaining."
        })

# ---------------- RUN ----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    # Host 0.0.0.0 allows access from other devices (Mobile)
    app.run(host="0.0.0.0", port=5000, debug=True)