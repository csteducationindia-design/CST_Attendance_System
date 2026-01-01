from app import db, Student, app

with app.app_context():
    s1 = Student(name="Rahul Patil", parent_mobile="9876543210")
    s2 = Student(name="Pooja Sharma", parent_mobile="9123456789")

    db.session.add_all([s1, s2])
    db.session.commit()
    print("Students Added Successfully")
