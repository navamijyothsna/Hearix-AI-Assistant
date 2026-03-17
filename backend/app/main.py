import os
import shutil
import nltk
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import engine, get_db
from .models import models
from .utils import auth 
from .services.pdf_service import PDFService

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

origins = [
    "https://storied-haupia-6da5b0.netlify.app",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5500"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/reset-db")
def reset_database(db: Session = Depends(get_db)):
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    return {"message": "Database reset successfully!"}

@app.post("/auth/register")
def register(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    hashed = auth.get_password_hash(password)
    new_user = models.User(username=username, hashed_password=hashed)
    db.add(new_user)
    db.commit()
    return {"message": "Success"}

@app.post("/auth/login")
def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == username).first()
    if not db_user or not auth.verify_password(password, db_user.hashed_password):
        raise HTTPException(status_code=401)
    token = auth.create_access_token(data={"sub": db_user.username})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/files/upload")
async def upload_file(
    dept: str = Form(...), 
    sem: str = Form(...), 
    sub: str = Form(...), 
    category: str = Form(...), 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    new_file = models.File(
        filename=file.filename, 
        dept=dept.upper().strip(), 
        semester=str(sem).upper().replace("S", "").strip(), 
        subject=sub.lower().strip(), 
        category=category.lower().strip(), 
        file_path=file_path
    )
    db.add(new_file)
    db.commit()
    return {"message": "Uploaded"}

@app.get("/files/all")
def get_all(db: Session = Depends(get_db)):
    return db.query(models.File).all()

@app.get("/assistant/fetch-and-read")
def fetch_and_read(dept: str, sem: str, sub: str, category: str = "note", topic: str = "", db: Session = Depends(get_db)):
    clean_sem = str(sem).upper().replace("S", "").strip()
    clean_sub = sub.lower().strip()
    
    # 1. Fetch ALL matching records for this Dept/Sem/Cat
    targets = db.query(models.File).filter(
        models.File.dept == dept.upper(),
        models.File.semester == clean_sem,
        models.File.category == category.lower()
    ).all()

    valid_target = None

    # 2. SELF-HEALING LOOP: Check if the file ACTUALLY exists on the server!
    for t in targets:
        if not os.path.exists(t.file_path):
            # 🚨 GHOST FILE DETECTED! Automatically delete it from the DB
            db.delete(t)
            db.commit()
            continue
        
        # If it physically exists, see if it matches the subject you spoke
        if clean_sub in t.subject.lower():
            valid_target = t
            break
    
    # 3. Fallback: If no exact subject match, just pick the first VALID physical file
    if not valid_target:
        fallback_targets = db.query(models.File).filter(
            models.File.dept == dept.upper(),
            models.File.semester == clean_sem,
            models.File.category == category.lower()
        ).all()
        
        for ft in fallback_targets:
            if os.path.exists(ft.file_path):
                valid_target = ft
                break

    # If everything fails, it means you need to upload a fresh file
    if not valid_target:
        raise HTTPException(status_code=404, detail="File deleted by server sleep. Please re-upload.")

    raw_text = PDFService.extract_text(valid_target.file_path)
    summary = PDFService.chunk_and_summarize(raw_text, valid_target.subject, topic)
    return {"voice_response": summary}

@app.delete("/files/{file_id}")
def delete_file(file_id: int, db: Session = Depends(get_db)):
    file = db.query(models.File).filter(models.File.id == file_id).first()
    if file:
        db.delete(file)
        db.commit()
    return {"message": "Deleted"}