import csv
import os
from app import Student, db, app

# ---------------- CONFIGURATION ----------------
# This script deletes the OLD database and creates a NEW one
# with the 'parent_email' column.

with app.app_context():
    db_path = os.path.join(app.root_path, 'data', 'attendance.db')
    
    # 1. DELETE OLD DB (Fixes the Network Error)
    if os.path.exists(db_path):
        os.remove(db_path)
        print("🗑️  Old Database deleted.")

    # 2. CREATE NEW DB (With Email Column)
    db.create_all()
    print("✅ New Database created with Email Support.")

    # 3. RE-IMPORT STUDENTS
    if os.path.exists('students.csv'):
        with open('students.csv', newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                s = Student(
                    id=row['id'].strip(),
                    name=row['name'].strip(),
                    parent_mobile=row['parent_mobile'].strip(),
                    # Safe way to get email, even if column is missing in CSV
                    parent_email=row.get('parent_email', '').strip() 
                )
                db.session.add(s)
                count += 1
            db.session.commit()
            print(f"✅ Imported {count} students successfully!")
    else:
        print("❌ Error: students.csv file not found.")