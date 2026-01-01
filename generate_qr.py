import qrcode
from app import Student, app

with app.app_context():
    students = Student.query.all()
    for s in students:
        url = f"https://scan.cstai.in/scan/{s.id}"
        img = qrcode.make(url)
        img.save(f"qr_{s.id}.png")
        print("QR generated:", s.id)
