from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import models
from ..schemas import schemas
from ..services.pdf_service import PDFService
from .deps import get_current_user

router = APIRouter(prefix="/assistant", tags=["AI Assistant"])

@router.get("/summarize/{file_id}", response_model=schemas.SummaryResponse)
def get_pdf_summary(
    file_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Retrieves a PDF, extracts text, and returns an AI-generated summary.
    Available to both Admins and Blind Users.
    """
    # 1. Fetch file record
    db_file = db.query(models.FileMetadata).filter(models.FileMetadata.id == file_id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="File record not found in database.")

    # 2. Extract Text from PDF
    full_text = PDFService.extract_text(db_file.file_path)

    # 3. Generate Summary
    summary = PDFService.chunk_and_summarize(full_text)

    return {
        "filename": db_file.filename,
        "summary": summary,
        "chunk_count": 1 # Representing the processed section
    }