from app import Attendance, db, app
from datetime import datetime

today = datetime.now().strftime('%Y-%m-%d')

with app.app_context():
    Attendance.query.filter_by(date=today).delete()
    db.session.commit()
    print("Today's attendance cleared")
