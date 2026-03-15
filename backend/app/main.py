import os
import shutil
import nltk
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from jose import JWTError, jwt

# Download required NLTK data for sentence tokenization
try:
    nltk.download('punkt')
    nltk.download('punkt_tab')
except Exception as e:
    print(f"NLTK Download Warning: {e}")

from .database import engine, get_db
from .models import models
from .schemas import schemas
from .utils import auth
from .services.pdf_service import PDFService
from .config import settings

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hearix AI Academic Assistant")

# CORS configuration for Netlify/Localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# --- AUTHENTICATION HELPER ---
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

# --- AUTH ROUTES ---
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

# --- FILE ROUTES ---
@app.post("/files/upload")
async def upload(
    dept: str = Form(...), 
    sem: int = Form(...), 
    sub: str = Form(...), 
    module: int = Form(...), 
    category: str = Form("note"),
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
            category=category,
            file_path=path, 
            owner_id=current_user.id
        )
        db.add(new_file)
        db.commit()
        db.refresh(new_file)
        return {"message": "Upload successful", "file_id": new_file.id}
    except Exception as e:
        db.rollback() 
        raise HTTPException(status_code=500, detail=str(e))

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
    if os.path.exists(file_to_delete.file_path):
        os.remove(file_to_delete.file_path)
    db.delete(file_to_delete)
    db.commit()
    return {"message": "Deleted successfully"}

# --- VOICE ASSISTANT ROUTES (FIXED FOR 404 ISSUES) ---
@app.get("/assistant/fetch-and-read")
def fetch_and_read(
    dept: str, sem: int, sub: str, module: Optional[int] = None, category: str = "note", 
    db: Session = Depends(get_db) 
):
    # Fuzzy search using .ilike to handle speech-to-text variations
    query = db.query(models.File).filter(
        models.File.dept == dept, 
        models.File.semester == sem,
        models.File.subject.ilike(f"%{sub}%"),
        models.File.category == category
    )
    
    if module and category == "note":
        query = query.filter(models.File.module == module)
        
    target_file = query.first()
    
    if not target_file:
        # Debug print for Render logs
        print(f"SEARCH FAILED: Dept:{dept}, Sem:{sem}, Sub:{sub}, Cat:{category}")
        raise HTTPException(status_code=404, detail="Document not found in database.")

    if not os.path.exists(target_file.file_path):
        raise HTTPException(status_code=404, detail="Physical PDF file missing from server storage.")

    raw_text = PDFService.extract_text(target_file.file_path)
    summary = PDFService.chunk_and_summarize(raw_text, target_file.subject)
    return {"voice_response": summary}

@app.get("/assistant/read-topic")
def read_specific_topic(
    dept: str, sem: int, sub: str, topic: str, module: Optional[int] = None, category: str = "note", 
    db: Session = Depends(get_db) 
):
    query = db.query(models.File).filter(
        models.File.dept == dept, 
        models.File.semester == sem,
        models.File.subject.ilike(f"%{sub}%"),
        models.File.category == category
    )
    
    if module and category == "note":
        query = query.filter(models.File.module == module)
        
    target_file = query.first()
    
    if not target_file:
        raise HTTPException(status_code=404, detail="Topic notes not found.")

    raw_text = PDFService.extract_text(target_file.file_path)
    topic_content = PDFService.extract_specific_topic(raw_text, topic)
    return {"voice_response": topic_content}