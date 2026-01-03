import requests
import urllib.parse

# ---------------- CONFIGURATION ----------------
# double check these match your account exactly
API_KEY = "sb6DpbNkzTrZmn6M4OOs9Zuu4sVWvv0owEBMrgjEuRo%3D"
ENTITY_ID = "1701164059159702167"
TEMPLATE_ID = "1707176698851172545"  # Entry Template
SENDER_ID = "CSTINI"

# The number to test (Use YOUR personal mobile number here to check)
TEST_MOBILE = "919822826307"  # <--- PUT YOUR NUMBER HERE (with 91)

# The Name to test
STUDENT_NAME = "TestStudent"

# Time to test
TIME_NOW = "08:00 AM"

# ---------------- PREPARE MESSAGE ----------------
# IMPORTANT: This must match your DLT template EXACTLY.
# Based on your previous chats, your template likely ends with the institute number.
INSTITUTE_PHONE = "7083021167"

msg = f"Dear {STUDENT_NAME}, {STUDENT_NAME} entered the class at {TIME_NOW}. CST Institute {INSTITUTE_PHONE} www.cste.in"

print(f"--- PREVIEW ---")
print(f"To: {TEST_MOBILE}")
print(f"Message: {msg}")
print(f"Len: {len(msg)}")

# URL Encode
msg_encoded = urllib.parse.quote(msg)

# ---------------- SEND ----------------
url = f"http://servermsg.com/api/SmsApi/SendSingleApi?apikey={API_KEY}&SenderID={SENDER_ID}&Phno={TEST_MOBILE}&Msg={msg_encoded}&EntityID={ENTITY_ID}&TemplateID={TEMPLATE_ID}"

print("\n--- SENDING... ---")
try:
    response = requests.get(url, timeout=15)
    print("Response Status Code:", response.status_code)
    print("Response Body:", response.text)
except Exception as e:
    print("Error:", e)

9373969296 - shashik