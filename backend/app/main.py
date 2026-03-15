import os
import shutil
import nltk
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional

# Download required NLTK data for text processing
try:
    nltk.download('punkt')
    nltk.download('punkt_tab')
except Exception as e:
    print(f"NLTK Download Warning: {e}")

from .database import engine, get_db
from .models import models
from .utils import auth 
from .services.pdf_service import PDFService

# Initialize database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- AUTHENTICATION ---
@app.post("/auth/register")
def register(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    hashed = auth.get_password_hash(password)
    new_user = models.User(username=username, hashed_password=hashed)
    db.add(new_user)
    db.commit()
    return {"message": "User registered successfully"}

@app.post("/auth/login")
def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == username).first()
    if not db_user or not auth.verify_password(password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = auth.create_access_token(data={"sub": db_user.username})
    return {"access_token": token, "token_type": "bearer"}

# --- FILE OPERATIONS ---
@app.post("/files/upload")
async def upload_file(
    dept: str = Form(...), sem: str = Form(...), sub: str = Form(...), 
    category: str = Form("note"), file: UploadFile = File(...), db: Session = Depends(get_db)
):
    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    new_file = models.File(
        filename=file.filename, dept=dept.upper(), semester=str(sem).upper(),
        subject=sub.lower().strip(), category=category.lower(), file_path=file_path
    )
    db.add(new_file)
    db.commit()
    return {"message": "Success"}

@app.get("/files/search")
def search_files(dept: str, semester: str, db: Session = Depends(get_db)):
    # Handles both '6' and 'S6'
    sem_val = semester.upper().replace("S", "")
    return db.query(models.File).filter(
        models.File.dept == dept.upper(),
        models.File.semester.in_([sem_val, f"S{sem_val}"])
    ).all()

# --- VOICE ASSISTANT ---
@app.get("/assistant/fetch-and-read")
def fetch_and_read(dept: str, sem: str, sub: str, category: str = "note", db: Session = Depends(get_db)):
    sem_num = sem.upper().replace("S", "")
    sem_options = [sem_num, f"S{sem_num}"]

    raw_words = sub.lower().split()
    stop_words = {"s1","s2","s3","s4","s5","s6","s7","s8", "notes", "syllabus", "read", "for", "the"}
    keywords = [w for w in raw_words if w not in stop_words]

    query = db.query(models.File).filter(
        models.File.dept == dept.upper(),
        models.File.semester.in_(sem_options),
        models.File.category == category.lower()
    )

    if keywords:
        for word in keywords:
            query = query.filter(models.File.subject.ilike(f"%{word}%"))
    
    target = query.first()
    if not target:
        raise HTTPException(status_code=404, detail="Document not found")

    raw_text = PDFService.extract_text(target.file_path)
    summary = PDFService.chunk_and_summarize(raw_text, target.subject)
    return {"voice_response": summary}

@app.delete("/files/{file_id}")
def delete_file(file_id: int, db: Session = Depends(get_db)):
    file = db.query(models.File).filter(models.File.id == file_id).first()
    if file:
        if os.path.exists(file.file_path):
            os.remove(file.file_path)
        db.delete(file)
        db.commit()
    return {"message": "Deleted"}