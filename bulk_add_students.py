import csv
import os
from app import Student, db, app

with app.app_context():
    # Check if DB exists
    db_path = os.path.join(app.root_path, 'data', 'attendance.db')
    if not os.path.exists(db_path):
        db.create_all()
        print("Database created (it didn't exist).")
    else:
        print("Database found. Keeping existing data...")

    # Read CSV and Add New Students
    if os.path.exists('students.csv'):
        with open('students.csv', newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            added_count = 0
            
            for row in reader:
                sid = row['id'].strip()
                
                # Check if student already exists
                existing_student = Student.query.get(sid)
                if existing_student:
                    # Optional: Update email/phone if changed
                    existing_student.parent_mobile = row['parent_mobile'].strip()
                    existing_student.parent_email = row.get('parent_email', '').strip()
                    print(f"Updated info for: {sid}")
                else:
                    # Create New Student
                    s = Student(
                        id=sid,
                        name=row['name'].strip(),
                        parent_mobile=row['parent_mobile'].strip(),
                        parent_email=row.get('parent_email', '').strip()
                    )
                    db.session.add(s)
                    added_count += 1
                    print(f"Added NEW student: {sid}")

            db.session.commit()
            print(f"✅ Process Complete. Added {added_count} new students.")
    else:
        print("❌ students.csv not found!")