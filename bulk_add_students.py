import csv
import os
from app import Student, db, app

# Delete old DB to reset structure (WARNING: Deletes attendance history)
# If you want to keep history, you must use a migration tool, but for now, a reset is easiest.
with app.app_context():
    db_path = os.path.join(app.root_path, 'data', 'attendance.db')
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Old database removed.")
    
    db.create_all()
    print("New Database Created with Email Support.")

    if os.path.exists('students.csv'):
        with open('students.csv', newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                s = Student(
                    id=row['id'].strip(),
                    name=row['name'].strip(),
                    parent_mobile=row['parent_mobile'].strip(),
                    parent_email=row.get('parent_email', '').strip() # Handle missing emails
                )
                db.session.add(s)
            db.session.commit()
            print("✅ Students imported successfully!")
    else:
        print("❌ students.csv not found!")