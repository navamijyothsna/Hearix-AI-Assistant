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

# --- VOICE ASSISTANT (BULLETPROOF VERSION 2.0) ---
@app.get("/assistant/fetch-and-read")
def fetch_and_read(dept: str, sem: str, sub: str, category: str = "note", db: Session = Depends(get_db)):
    
    # 1. Clean the incoming Subject String extremely aggressively
    # This prevents weird URL encoded characters like "%20" or "0" from ruining the search
    import urllib.parse
    import re
    
    decoded_sub = urllib.parse.unquote(sub) # Decode URL artifacts
    clean_sub = re.sub(r'[^a-zA-Z\s]', '', decoded_sub.lower()) # KEEP ONLY LETTERS AND SPACES. Drops numbers like '0'.
    
    raw_words = clean_sub.split()
    stop_words = {"s", "notes", "syllabus", "read", "for", "the", "semester", "of", "about", "on"}
    keywords = [w for w in raw_words if w not in stop_words and len(w) > 1] 

    # 2. Standardize Semester
    sem_num = str(sem).upper().replace("S", "")
    sem_options = [sem_num, f"S{sem_num}"]

    # 3. Build Base Query
    query = db.query(models.File).filter(
        models.File.dept == dept.upper(),
        models.File.semester.in_(sem_options),
        models.File.category == category.lower()
    )

    # 4. Search with cleaned keywords
    if keywords:
        for word in keywords:
            query = query.filter(models.File.subject.ilike(f"%{word}%"))
    
    target = query.first()

    # 5. Fallback: If specific search fails, just grab ANY file matching Dept, Sem, and Cat
    if not target:
        fallback_query = db.query(models.File).filter(
            models.File.dept == dept.upper(),
            models.File.semester.in_(sem_options),
            models.File.category == category.lower()
        )
        target = fallback_query.first()

    # 6. Final Check: Does it exist in DB?
    if not target:
        raise HTTPException(status_code=404, detail="Document not found in Database")

    # 7. CRASH PREVENTION: Did Render delete the physical file while sleeping?
    if not os.path.exists(target.file_path):
        # Delete the ghost record from the database so it stops causing errors
        db.delete(target)
        db.commit()
        raise HTTPException(status_code=404, detail="File deleted by server sleep. Please re-upload.")

    # 8. Process PDF
    try:
        raw_text = PDFService.extract_text(target.file_path)
        summary = PDFService.chunk_and_summarize(raw_text, target.subject)
        return {"voice_response": summary}
    except Exception as e:
        print(f"AI/PDF Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to read or summarize the PDF.")

@app.delete("/files/{file_id}")
def delete_file(file_id: int, db: Session = Depends(get_db)):
    file = db.query(models.File).filter(models.File.id == file_id).first()
    if file:
        if os.path.exists(file.file_path):
            os.remove(file.file_path)
        db.delete(file)
        db.commit()
    return {"message": "Deleted"}