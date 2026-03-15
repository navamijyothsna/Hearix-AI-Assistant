import PyPDF2
from google import genai
from app.config import settings
from fastapi import HTTPException

class PDFService:
    @staticmethod
    def get_client():
        if not settings.GEMINI_API_KEY:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY not found in server environment.")
        try:
            return genai.Client(api_key=settings.GEMINI_API_KEY)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI Init Error: {str(e)}")

    @staticmethod
    def extract_text(file_path):
        text = ""
        try:
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() or ""
            return text
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PDF Error: {str(e)}")

    @staticmethod
    def chunk_and_summarize(text, subject):
        client = PDFService.get_client()
        prompt = f"You are a helpful academic assistant. Summarize these {subject} notes for a student: {text[:10000]}"
        try:
            response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            return response.text
        except Exception as e:
            return f"Error generating summary: {str(e)}"

    @staticmethod
    def extract_specific_topic(text, topic):
        client = PDFService.get_client()
        prompt = f"Based on the following notes, explain the topic '{topic}' in simple terms: {text[:10000]}"
        try:
            response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            return response.text
        except Exception as e:
            return f"Error explaining topic: {str(e)}"