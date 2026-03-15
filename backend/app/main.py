from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from jose import JWTError, jwt
import os
import shutil

from .database import engine, get_db
from .models import models
from .schemas import schemas
from .utils import auth
from .services.pdf_service import PDFService
from .config import settings

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Voice Academic Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

@app.post("/auth/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed = auth.get_password_hash(user.password)
    new_user = models.User(username=user.username, hashed_password=hashed, role=user.role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not db_user or not auth.verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = auth.create_access_token(data={"sub": db_user.username})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/files/upload")
async def upload(
    dept: str = Form(...), 
    sem: int = Form(...), 
    sub: str = Form(...), 
    module: int = Form(...), 
    category: str = Form("note"), # NEW FIELD
    file: UploadFile = File(...), 
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    os.makedirs("uploads", exist_ok=True)
    path = os.path.join("uploads", file.filename)
    
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    try:
        new_file = models.File(
            filename=file.filename, 
            dept=dept, 
            semester=sem, 
            subject=sub, 
            module=module, 
            category=category, # NEW FIELD
            file_path=path, 
            owner_id=current_user.id
        )
        db.add(new_file)
        db.commit()
        db.refresh(new_file)
        return {"message": "Upload successful", "file_id": new_file.id}
    except Exception as e:
        db.rollback() 
        print(f"CRITICAL DATABASE ERROR DURING UPLOAD: {e}")
        raise HTTPException(status_code=500, detail=f"Database error during upload: {str(e)}")

@app.get("/files/search", response_model=List[schemas.FileOut])
def search_files(
    dept: str, semester: int, subject: Optional[str] = None, 
    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    query = db.query(models.File).filter(models.File.dept == dept, models.File.semester == semester)
    if subject:
        query = query.filter(models.File.subject.ilike(f"%{subject}%"))
    
    results = query.all()
    if not results:
        raise HTTPException(status_code=404, detail="No notes found.")
    return results

@app.delete("/files/{file_id}")
def delete_file(file_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    file_to_delete = db.query(models.File).filter(models.File.id == file_id).first()
    if not file_to_delete:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        if os.path.exists(file_to_delete.file_path):
            os.remove(file_to_delete.file_path)
    except Exception as e:
        print(f"Warning: Could not delete physical file: {e}")
    db.delete(file_to_delete)
    db.commit()
    return {"message": f"Successfully deleted {file_to_delete.subject}"}

# --- UPDATED: VOICE ROUTES NOW SUPPORT SYLLABUS ---
@app.get("/assistant/fetch-and-read")
def fetch_and_read(
    dept: str, sem: int, sub: str, module: Optional[int] = None, category: str = "note", # NEW FIELD
    db: Session = Depends(get_db) 
):
    query = db.query(models.File).filter(
        models.File.dept == dept, 
        models.File.semester == sem,
        models.File.subject.ilike(f"%{sub}%"),
        models.File.category == category # Filter by Syllabus or Note
    )
    
    # If it's a syllabus, ignore the module number
    if module and category == "note":
        query = query.filter(models.File.module == module)
        
    target_file = query.first()
    
    if not target_file:
        raise HTTPException(status_code=404, detail="Notes not found.")

    raw_text = PDFService.extract_text(target_file.file_path)
    summary = PDFService.chunk_and_summarize(raw_text, target_file.subject)
    return {"voice_response": summary}

@app.get("/assistant/read-topic")
def read_specific_topic(
    dept: str, sem: int, sub: str, topic: str, module: Optional[int] = None, category: str = "note", # NEW FIELD
    db: Session = Depends(get_db) 
):
    query = db.query(models.File).filter(
        models.File.dept == dept, 
        models.File.semester == sem,
        models.File.subject.ilike(f"%{sub}%"),
        models.File.category == category # Filter by Syllabus or Note
    )
    
    if module and category == "note":
        query = query.filter(models.File.module == module)
        
    target_file = query.first()
    
    if not target_file:
        raise HTTPException(status_code=404, detail="Notes not found.")

    raw_text = PDFService.extract_text(target_file.file_path)
    topic_content = PDFService.extract_specific_topic(raw_text, topic)
    return {"voice_response": topic_content}