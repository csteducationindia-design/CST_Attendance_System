import os
import csv
import io
import zipfile
import threading
import urllib.parse
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, jsonify, render_template, make_response, request, session, redirect, url_for, render_template_string, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import pytz 
import traceback 
import qrcode  # ✅ Make sure 'qrcode' is in your requirements.txt

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
DOMAIN_URL = "https://scan.cstai.in" # ✅ Used for generating QR Links

# ================= CREDENTIALS =================
SMS_API_KEY = "sb6DpbNkzTrZmn6M4OOs9Zuu4sVWvv0owEBMrgjEuRo%3D"
SMS_ENTITY_ID = "1701164059159702167"
SMS_SENDER = "CSTINI"

# ✅ NEW APPROVED ENTRY TEMPLATE ID
ENTRY_TEMPLATE_ID = "1707176777667925464"
# Exit Template ID 
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
        # Dear {Name}, entered the class at {Time}. CST Education India 7083021167
        sms_msg = f"Dear {student.name}, entered the class at {time_now}. CST Education India 7083021167"
        email_sub = f"Entry Alert: {student.name}"
        email_body = f"Dear Parent,\n\n{student.name} has reached the institute at {time_now}.\n\n- CST Institute"
        wa_body = f"✅ *Entry Alert*\nStudent: {student.name}\nTime: {time_now}\nStatus: Present"
        tid = ENTRY_TEMPLATE_ID
    else:
        sms_msg = f"Dear {student.name}, has successfully completed today’s class and has now left CST Education India"
        email_sub = f"Exit Alert: {student.name}"
        email_body = f"Dear Parent,\n\n{student.name} has left the institute at {time_now}.\n\n- CST Education India"
        wa_body = f"👋 *Exit Alert*\nStudent: {student.name}\nTime: {time_now}\nStatus: Left"
        tid = EXIT_TEMPLATE_ID

    threading.Thread(target=send_sms, args=(student.parent_mobile, sms_msg, tid)).start()
    threading.Thread(target=send_email, args=(student.parent_email, email_sub, email_body)).start()
    threading.Thread(target=send_whatsapp, args=(student.parent_mobile, wa_body)).start()

# ================= DASHBOARD & ADMIN ROUTES =================
@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    # HTML Dashboard UI
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Teacher Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f4f7f6; margin: 0; padding: 20px; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
            h1 { color: #333; text-align: center; margin-bottom: 30px; }
            .card { background: #f9f9f9; border: 1px solid #ddd; padding: 20px; border-radius: 8px; margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between; }
            .card h3 { margin: 0 0 10px 0; color: #555; }
            .card p { margin: 0; color: #777; font-size: 14px; }
            .btn { text-decoration: none; padding: 10px 20px; border-radius: 5px; color: white; font-weight: bold; cursor: pointer; border: none; display: inline-block; }
            .btn-blue { background: #007bff; } .btn-blue:hover { background: #0056b3; }
            .btn-green { background: #28a745; } .btn-green:hover { background: #218838; }
            .btn-orange { background: #fd7e14; } .btn-orange:hover { background: #e36d0a; }
            .btn-red { background: #dc3545; } .btn-red:hover { background: #c82333; }
            input[type=file] { padding: 5px; }
            .header-buttons { display: flex; justify-content: space-between; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header-buttons">
                <a href="{{ url_for('teacher_scanner') }}" class="btn btn-green">📷 Go to Scanner</a>
                <a href="{{ url_for('logout') }}" class="btn btn-red">Log Out</a>
            </div>
            <h1>🏫 Teacher Admin Dashboard</h1>
            
            {% with messages = get_flashed_messages() %}
              {% if messages %}
                <div style="padding: 10px; background: #d4edda; color: #155724; border-radius: 5px; margin-bottom: 20px;">
                    {{ messages[0] }}
                </div>
              {% endif %}
            {% endwith %}

            <div class="card">
                <div>
                    <h3>📂 1. Add/Update Students</h3>
                    <p>Upload your <b>students.csv</b> file here.</p>
                </div>
                <form action="{{ url_for('upload_students') }}" method="post" enctype="multipart/form-data" style="display:flex; align-items:center;">
                    <input type="file" name="file" required accept=".csv">
                    <button type="submit" class="btn btn-blue">Upload CSV</button>
                </form>
            </div>

            <div class="card">
                <div>
                    <h3>🏁 2. Get QR Codes</h3>
                    <p>Download a ZIP file of all student QR codes.</p>
                </div>
                <a href="{{ url_for('download_all_qrs') }}" class="btn btn-orange">Download QRs</a>
            </div>

            <div class="card">
                <div>
                    <h3>📊 3. Attendance Report</h3>
                    <p>Download monthly attendance in Excel/CSV.</p>
                </div>
                <a href="{{ url_for('download_report') }}" class="btn btn-blue">Download Report</a>
            </div>
        </div>
    </body>
    </html>
    """)

@app.route('/upload_students', methods=['POST'])
def upload_students():
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    if 'file' not in request.files:
        return "No file uploaded", 400
    
    file = request.files['file']
    if file.filename == '':
        return "No file selected", 400

    try:
        # Read CSV file from upload
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        reader = csv.DictReader(stream)
        
        count = 0
        updated = 0
        
        for row in reader:
            s_id = row['id'].strip()
            name = row['name'].strip()
            mobile = row['parent_mobile'].strip()
            email = row.get('parent_email', '').strip()

            student = Student.query.get(s_id)
            if student:
                student.name = name
                student.parent_mobile = mobile
                student.parent_email = email
                updated += 1
            else:
                new_s = Student(id=s_id, name=name, parent_mobile=mobile, parent_email=email)
                db.session.add(new_s)
                count += 1
        
        db.session.commit()
        from flask import flash
        app.secret_key = 'cst_secure_key_2026' # Ensure key is set
        # Using a simple URL param for success message in this basic example if flash setup is complex,
        # but let's try to inject a success message into the dashboard render.
        return render_template_string("""<script>alert('✅ Success! Added: {{c}} New, Updated: {{u}}'); window.location.href='/dashboard';</script>""", c=count, u=updated)

    except Exception as e:
        return f"Error processing CSV: {str(e)}"

@app.route('/download_all_qrs')
def download_all_qrs():
    if not session.get('logged_in'): return redirect(url_for('login'))

    try:
        students = Student.query.all()
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            for s in students:
                # Generate QR Link
                url = f"{DOMAIN_URL}/scan/{s.id}"
                
                # Create QR Image
                qr = qrcode.QRCode(box_size=10, border=4)
                qr.add_data(url)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                
                # Save to Zip
                img_buffer = io.BytesIO()
                img.save(img_buffer, format="PNG")
                zf.writestr(f"qr_{s.id}.png", img_buffer.getvalue())

        zip_buffer.seek(0)
        
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name='all_student_qrs.zip'
        )
    except Exception as e:
        return f"Error generating QRs: {str(e)}"

# ================= EXISTING ROUTES =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ""
    if request.method == 'POST':
        user = request.form.get('username')
        pw = request.form.get('password')
        if user == ADMIN_USERNAME and pw == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('dashboard')) # 👈 Changed redirect to Dashboard
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
        # Time format matching DLT 08.00 AM
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