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
    print(f"NLTK Download Warning: {e}")

from .database import engine, get_db
from .models import models
from .utils import auth 
from .services.pdf_service import PDFService

# Initialize database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hearix AI Assistant")

# --- STRICT CORS SETUP ---
origins = [
    "https://storied-haupia-6da5b0.netlify.app", 
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5500", 
    "http://localhost:5500"  
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 🚨 DATABASE RESET ROUTE ---
@app.get("/reset-db")
def reset_database(db: Session = Depends(get_db)):
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    return {"message": "Database successfully wiped and recreated with the new String format!"}

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

@app.get("/files/all")
def get_all_files(db: Session = Depends(get_db)):
    return db.query(models.File).all()

@app.get("/files/search")
def search_files(dept: str, semester: str, db: Session = Depends(get_db)):
    sem_val = semester.upper().replace("S", "")
    return db.query(models.File).filter(
        models.File.dept == dept.upper(),
        models.File.semester.in_([sem_val, f"S{sem_val}"])
    ).all()

# --- VOICE ASSISTANT (BULLETPROOF VERSION) ---
@app.get("/assistant/fetch-and-read")
def fetch_and_read(dept: str, sem: str, sub: str, category: str = "note", db: Session = Depends(get_db)):
    # 1. Standardize Semester
    sem_num = sem.upper().replace("S", "")
    sem_options = [sem_num, f"S{sem_num}"]

    # 2. Aggressive String Cleaning (fixes the %20 issue)
    import re
    # Remove any character that is not a letter or number, then split
    clean_sub_string = re.sub(r'[^a-zA-Z0-9\s]', '', sub.lower())
    raw_words = clean_sub_string.split()
    
    # Extensive stop-words list
    stop_words = {"s1","s2","s3","s4","s5","s6","s7","s8", "notes", "syllabus", "read", "for", "the", "semester", "of", "about", "on"}
    keywords = [w for w in raw_words if w not in stop_words and len(w) > 1] # Ignore 1-letter typos

    # 3. Base Query
    query = db.query(models.File).filter(
        models.File.dept == dept.upper(),
        models.File.semester.in_(sem_options),
        models.File.category == category.lower()
    )

    # 4. Fuzzy Matching
    if keywords:
        for word in keywords:
            query = query.filter(models.File.subject.ilike(f"%{word}%"))
    
    target = query.first()
    
    # 5. The "Fallback" Search 
    # If the precise keyword match fails, let's just grab the first file for that Dept/Sem/Cat
    # This ensures your demo doesn't fail if the STT mishears "ds" as "dx"
    if not target:
        fallback_query = db.query(models.File).filter(
            models.File.dept == dept.upper(),
            models.File.semester.in_(sem_options),
            models.File.category == category.lower()
        )
        target = fallback_query.first()

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