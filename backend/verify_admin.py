import os
import requests
from io import BytesIO

API_URL = "http://127.0.0.1:8000/admin"

print("--- Starting Admin Dashboard API Verification ---")

# 1. Login
data = {"username": "admin", "password": "admin123"}
r = requests.post(f"{API_URL}/token", data=data)
if not r.ok:
    print("Login failed:", r.text)
    exit(1)
token = r.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}
print("Login successful, token retrieved.")

# 2. Create Syllabus Structure
folders = ["Semester 2 Test", "Chemistry Test", "Module 1 Test"]
current = ""
for folder in folders:
    req = {"name": folder, "parent_path": current}
    res = requests.post(f"{API_URL}/folder", json=req, headers=headers)
    if res.ok:
        print(f"Created folder: '{folder}' inside '{current or 'Root'}'")
    else:
        print(f"Failed to create folder: {res.text}")
    current = f"{current}/{folder}" if current else folder

# 3. Upload File
print(f"Uploading mock PDF to target path: {current}...")
file_content = b"%PDF-1.4 mock pdf content for testing admin panel"
files = {"file": ("mock_notes.pdf", file_content, "application/pdf")}
data = {"path": current}
res = requests.post(f"{API_URL}/upload", files=files, data=data, headers=headers)
if res.ok:
    print("Uploaded mock PDF successfully!")
else:
    print("Upload failed:", res.text)

# 4. Fetch Syllabus
print("Retrieving Syllabus Tree from server...")
res = requests.get(f"{API_URL}/syllabus", headers=headers)
if res.ok:
    syllabus = res.json()
    print("Fetched Syllabus Structure Elements:", len(syllabus))
else:
    print("Failed to fetch syllabus:", res.text)

print("--- Admin Dashboard API Verification Complete ---")
