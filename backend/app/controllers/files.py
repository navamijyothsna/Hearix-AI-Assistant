import os
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import models
from ..schemas import schemas
from .deps import get_admin_user, get_current_user
from ..config import settings

router = APIRouter(prefix="/files", tags=["Files"])

@router.post("/upload", response_model=schemas.FileResponse)
def upload_pdf(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_admin_user)
):
    """
    Endpoint for Admins to upload academic PDFs.
    """
    # 1. Validate File Type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Only PDF files are allowed"
        )

    # 2. Generate Unique Filename
    # Using UUID prevents issues if two admins upload files with the same name.
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

    # 3. Save File to Physical Storage
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Could not save file to disk: {str(e)}"
        )

    # 4. Save Metadata to Database
    db_file = models.FileMetadata(
        filename=file.filename,
        file_path=file_path,
        owner_id=admin_user.id
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    
    return db_file

@router.get("/", response_model=List[schemas.FileResponse])
def list_files(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Endpoint for all authenticated users to see available documents.
    """
    return db.query(models.FileMetadata).all()

@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: int, 
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_admin_user)
):
    """
    Endpoint for Admins to delete a file from the system.
    """
    db_file = db.query(models.FileMetadata).filter(models.FileMetadata.id == file_id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="File record not found")

    # Delete physical file from 'uploads/' folder
    if os.path.exists(db_file.file_path):
        os.remove(db_file.file_path)

    # Delete record from database
    db.delete(db_file)
    db.commit()
    return None