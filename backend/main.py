import os
import secrets
import fitz  # PyMuPDF
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Hearix API")

# Explicit CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PDF_DIR = os.path.join(os.path.dirname(__file__), "local_pdfs")
os.makedirs(PDF_DIR, exist_ok=True)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="admin/token")
valid_tokens = set()

def verify_token(token: str = Depends(oauth2_scheme)):
    if token not in valid_tokens:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token

@app.post("/admin/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username == "admin" and form_data.password == "admin123":
        token = secrets.token_hex(16)
        valid_tokens.add(token)
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=400, detail="Incorrect username or password")

class QueryRequest(BaseModel):
    document_name: str
    topic: str
    
class FolderRequest(BaseModel):
    name: str
    parent_path: str = ""

@app.get("/admin/syllabus")
def get_syllabus(token: str = Depends(verify_token)):
    syllabus = []
    if not os.path.exists(PDF_DIR):
        return syllabus
    for sem in os.listdir(PDF_DIR):
        sem_path = os.path.join(PDF_DIR, sem)
        if os.path.isdir(sem_path):
            sem_data = {"name": sem, "subjects": []}
            for subj in os.listdir(sem_path):
                subj_path = os.path.join(sem_path, subj)
                if os.path.isdir(subj_path):
                    subj_data = {"name": subj, "modules": []}
                    for mod in os.listdir(subj_path):
                        mod_path = os.path.join(subj_path, mod)
                        if os.path.isdir(mod_path):
                            mod_data = {"name": mod, "files": []}
                            for f in os.listdir(mod_path):
                                if f.lower().endswith(".pdf"):
                                    mod_data["files"].append(f)
                            subj_data["modules"].append(mod_data)
                    sem_data["subjects"].append(subj_data)
            syllabus.append(sem_data)
    return syllabus

@app.post("/admin/folder")
def create_folder(req: FolderRequest, token: str = Depends(verify_token)):
    if ".." in req.parent_path or ".." in req.name:
        raise HTTPException(status_code=400, detail="Invalid path")
    path = os.path.join(PDF_DIR, req.parent_path, req.name) if req.parent_path else os.path.join(PDF_DIR, req.name)
    os.makedirs(path, exist_ok=True)
    return {"message": "Created successfully"}

@app.post("/admin/upload")
async def admin_upload_pdf(file: UploadFile = File(...), path: str = Form(""), token: str = Depends(verify_token)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    if ".." in path:
         raise HTTPException(status_code=400, detail="Invalid path")
    target_dir = os.path.join(PDF_DIR, path)
    os.makedirs(target_dir, exist_ok=True)
    file_path = os.path.join(target_dir, file.filename)
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    return {"message": f"Successfully uploaded {file.filename} to {path}"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    file_path = os.path.join(PDF_DIR, file.filename)
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
        
    return {"message": f"Successfully uploaded {file.filename}"}

@app.get("/pdfs")
def list_pdfs():
    files = []
    for root, _, filenames in os.walk(PDF_DIR):
        for f in filenames:
            if f.lower().endswith('.pdf'):
                files.append(f)
    return {"pdfs": files}

@app.post("/query")
def query_pdf(request: QueryRequest):
    # Find matching PDF by filename (case insensitive partial match) traversing all folders
    target_file_path = None
    target_file = None
    for root, _, files in os.walk(PDF_DIR):
        for f in files:
            if f.lower().endswith('.pdf') and request.document_name.lower() in f.lower():
                target_file_path = os.path.join(root, f)
                target_file = f
                break
        if target_file_path:
            break
            
    if not target_file_path:
        return {"response": f"I couldn't find a document named {request.document_name}."}
        
    extracted_text = ""
    
    try:
        doc = fitz.open(target_file_path)
        for page in doc:
            extracted_text += page.get_text()
        doc.close()
    except Exception as e:
        return {"response": f"Failed to read the document. Error: {str(e)}"}
        
    # Simple parsing: Find sentences containing the topic
    sentences = [s.strip() for s in extracted_text.replace('\n', ' ').split('.') if s.strip()]
    relevant_sentences = [s for s in sentences if request.topic.lower() in s.lower()]
    
    if not relevant_sentences:
        return {"response": f"I couldn't find any information about {request.topic} in {target_file}."}
        
    # Return up to 3 sentences to keep voice output manageable
    response_text = ". ".join(relevant_sentences[:3]) + "."
    return {"response": response_text}
