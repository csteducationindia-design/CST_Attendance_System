import qrcode
from app import Student, app

# ---------------- CONFIGURATION ----------------
# ✅ This is your NEW Live Domain
BASE_URL = "https://scan.cstai.in" 

with app.app_context():
    # 1. Get all students from the database
    students = Student.query.all()
    print(f"Found {len(students)} students.")

    for s in students:
        # 2. Create the proper Online Link
        # Example: https://scan.cstai.in/scan/cst101
        url = f"{BASE_URL}/scan/{s.id}"
        
        # 3. Generate the QR Image
        img = qrcode.make(url)
        file_name = f"qr_{s.id}.png"
        img.save(file_name)
        
        print(f"✅ Generated: {file_name} -> points to {url}")

    print("\nAll QR codes generated successfully!")