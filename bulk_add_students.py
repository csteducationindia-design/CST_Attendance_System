import csv
import os
from app import Student, db, app

# ---------------- CONFIGURATION ----------------
# This script SAFELY adds new students without deleting old data.

with app.app_context():
    # 1. Check if DB exists (Create if missing, but DON'T delete)
    db_path = os.path.join(app.root_path, 'data', 'attendance.db')
    if not os.path.exists(db_path):
        db.create_all()
        print("✅ Database created (it was missing).")
    else:
        print("ℹ️  Database found. Keeping existing data...")

    # 2. READ CSV & UPDATE/ADD
    if os.path.exists('students.csv'):
        with open('students.csv', newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            added_count = 0
            updated_count = 0
            
            for row in reader:
                student_id = row['id'].strip()
                
                # Check if student exists
                student = Student.query.get(student_id)
                
                if student:
                    # UPDATE existing student (in case email/phone changed)
                    student.name = row['name'].strip()
                    student.parent_mobile = row['parent_mobile'].strip()
                    student.parent_email = row.get('parent_email', '').strip()
                    updated_count += 1
                else:
                    # ADD new student
                    new_student = Student(
                        id=student_id,
                        name=row['name'].strip(),
                        parent_mobile=row['parent_mobile'].strip(),
                        parent_email=row.get('parent_email', '').strip()
                    )
                    db.session.add(new_student)
                    added_count += 1

            db.session.commit()
            print(f"✅ Process Complete.")
            print(f"   - Added: {added_count} new students")
            print(f"   - Updated: {updated_count} existing students")
    else:
        print("❌ Error: students.csv file not found.")