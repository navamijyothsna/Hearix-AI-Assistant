import os
import shutil
import nltk
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional

# Pre-download NLTK data required for text processing
try:
    nltk.download('punkt')
    nltk.download('punkt_tab')
except Exception as e:
    print(f"NLTK Download skipped/failed: {e}")

from .database import engine, get_db
from .models import models
from .services.pdf_service import PDFService

# Initialize database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hearix AI Assistant")

# CORS Setup - Allows your Netlify frontend to talk to this Render backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- FILE UPLOAD ---
@app.post("/files/upload")
async def upload_file(
    dept: str = Form(...), 
    sem: str = Form(...), 
    sub: str = Form(...), 
    category: str = Form("note"),
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    # Ensure upload directory exists
    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    new_file = models.File(
        filename=file.filename,
        dept=dept.upper(),
        semester=str(sem).upper(), # Stores as '6' or 'S6'
        subject=sub.lower().strip(),
        category=category.lower(),
        file_path=file_path
    )
    db.add(new_file)
    db.commit()
    return {"message": "Upload successful"}

# --- SEARCH FILES (Admin Panel) ---
@app.get("/files/search")
def search_files(dept: str, semester: str, db: Session = Depends(get_db)):
    # Standardize semester for search
    sem_val = semester.upper().replace("S", "")
    return db.query(models.File).filter(
        models.File.dept == dept.upper(),
        models.File.semester.in_([sem_val, f"S{sem_val}"])
    ).all()

# --- VOICE ASSISTANT: FETCH AND READ ---
@app.get("/assistant/fetch-and-read")
def fetch_and_read(dept: str, sem: str, sub: str, category: str = "note", db: Session = Depends(get_db)):
    # 1. Standardize Semester (matches '6' and 'S6')
    sem_num = sem.upper().replace("S", "")
    sem_options = [sem_num, f"S{sem_num}"]

    # 2. Clean the subject keywords from the voice transcript
    # This prevents "s6", "notes", etc., from breaking the subject match
    raw_words = sub.lower().split()
    stop_words = {"s1","s2","s3","s4","s5","s6","s7","s8", "notes", "syllabus", "read", "for", "the", "semester"}
    keywords = [w for w in raw_words if w not in stop_words]

    # 3. Build Query
    query = db.query(models.File).filter(
        models.File.dept == dept.upper(),
        models.File.semester.in_(sem_options),
        models.File.category == category.lower()
    )

    # 4. Apply Fuzzy Keyword Matching
    if keywords:
        for word in keywords:
            query = query.filter(models.File.subject.ilike(f"%{word}%"))
    
    target_file = query.first()

    if not target_file:
        # LOGGING: Helpful to see in Render Logs if search fails
        print(f"SEARCH FAILED -> Dept: {dept}, Sem: {sem_num}, Keywords: {keywords}, Cat: {category}")
        raise HTTPException(status_code=404, detail="Document not found.")

    # 5. Process PDF and Generate AI Summary
    if not os.path.exists(target_file.file_path):
        raise HTTPException(status_code=404, detail="File lost on server. Please re-upload.")

    try:
        raw_text = PDFService.extract_text(target_file.file_path)
        summary = PDFService.chunk_and_summarize(raw_text, target_file.subject)
        return {"voice_response": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Processing Error: {str(e)}")

# --- DELETE FILE ---
@app.delete("/files/{file_id}")
def delete_file(file_id: int, db: Session = Depends(get_db)):
    file = db.query(models.File).filter(models.File.id == file_id).first()
    if file:
        if os.path.exists(file.file_path):
            os.remove(file.file_path)
        db.delete(file)
        db.commit()
    return {"message": "Deleted"}