# Hearix

Hearix is a local-only AI voice assistant designed to help visually impaired engineering students read their PDF notes. It provides an accessible, screen-reader-friendly interface that allows users to interact with their study materials using voice commands or simple interactions.

---

## 👥 Team Members

This is a group mini project developed by a team of 5 members as part of our college mini project:

* **Namratha Krishna B M**   [GitHub](https://github.com/namrathakrishnabm)
* **Navami Jyothsna**   [GitHub](https://github.com/navamijyothsna)
* **Saranya A**   [GitHub](https://github.com/Saranya53430)
* **Vishnu S**   [GitHub](https://github.com/viishh0)
* **Ajil R**   [GitHub](https://github.com/github-username)

---

## 🚀 Features

* **Voice Interaction**: Designed to be used with voice commands and screen readers (**TalkBack** / **VoiceOver** compatible).
* **Local PDF Processing**: Reads and extracts information from local PDF files without relying on external cloud services for document storage.
* **Admin Dashboard**: A secure, file-system-based dashboard to manage a hierarchical syllabus structure (**Semester > Subject > Module**) and upload PDF notes.
* **Accessible UI**: A high-contrast, easy-to-use frontend with a **"Tap anywhere to speak"** interface.

---

## 🛠️ Technology Stack

* **Backend**: FastAPI (Python)
* **Frontend**: Vanilla HTML, CSS, JavaScript
* **PDF Processing**: PyMuPDF (`fitz`)

---

## 📦 Setup Instructions

### Prerequisites

* Python 3.8+
* Node.js *(optional, for alternative frontend serving)*

### Backend Setup

1. Navigate to the `backend` directory:

   ```bash
   cd backend
   ```

2. Create and activate a virtual environment (recommended):

   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/Mac:
   source .venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Start the backend server:

   ```bash
   uvicorn main:app --reload --port 8000
   ```

   The API will be available at `http://localhost:8000`.

### Frontend Setup

1. Open a new terminal and navigate to the `frontend` directory:

   ```bash
   cd frontend
   ```

2. Serve the static files. You can use Python's built-in HTTP server:

   ```bash
   python -m http.server 8080
   ```

3. Access the application in your browser at `http://localhost:8080`.

---

## 🔐 Admin Dashboard

The Admin Dashboard allows you to manage the syllabus structure and upload PDF files.

1. Navigate to `http://localhost:8080/admin/index.html` in your browser.
2. Log in using the default credentials:
   * Username: `admin`
   * Password: `admin123`
3. Use the interface to create folders (Semester > Subject > Module) and upload PDFs to the corresponding modules.

---

## 📂 Architecture

* `backend/`: Contains the FastAPI application, PDF processing logic, and the `local_pdfs/` directory where uploaded files are stored.
* `frontend/`: Contains the static assets (HTML, CSS, JS) for the main voice assistant UI.
* `frontend/admin/`: Contains the Admin Dashboard interface for managing syllabus and files.

---

## ♿ Accessibility Notes

Hearix is built with accessibility in mind. The main interface is designed to be easily navigable by screen readers. Ensure that your device's accessibility features (like TalkBack on Android or VoiceOver on iOS) are enabled for the best experience.
