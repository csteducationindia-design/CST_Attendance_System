import csv
from app import Student, db, app

with app.app_context():
    with open('students.csv', newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        print("Detected CSV Columns:", reader.fieldnames)

        for row in reader:
            sid = row['id'].strip()

            # 🔥 Check if student already exists
            existing = Student.query.get(sid)
            if existing:
                print("Already exists, skipping:", sid)
                continue

            s = Student(
                id=sid,
                name=row['name'].strip(),
                parent_mobile=row['parent_mobile'].strip()
            )
            db.session.add(s)

        db.session.commit()

print("Students import finished")
