import os
import PyPDF2
from google import genai

class PDFService:
    @staticmethod
    def extract_text(file_path: str) -> str:
        text = ""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                # Only read the first 2 pages for the demo to stay safe
                num_pages = min(len(reader.pages), 2) 
                for i in range(num_pages):
                    page_text = reader.pages[i].extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return "Could not extract text from the PDF."

    @staticmethod
    def chunk_and_summarize(text: str, subject: str) -> str:
        # Keep it very short for the free tier
        safe_text = text[:5000] 

        if not safe_text.strip():
            return "The document appears to be empty."

        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                return "AI Error: GEMINI_API_KEY is missing from Render environment."

            client = genai.Client(api_key=api_key)
            
            prompt = f"Summarize this academic note about {subject} in two simple sentences for a student: {safe_text}"
            
            # FIXED: Using the most stable model name string
            response = client.models.generate_content(
                model='gemini-1.5-flash', 
                contents=prompt
            )
            
            return response.text

        except Exception as e:
            # ULTIMATE FALLBACK: If the AI fails, just give the student the first 20 words
            # This ensures the "Blind Student" always hears SOMETHING.
            print(f"Gemini Error: {e}")
            words = safe_text.split()[:20]
            fallback_text = " ".join(words)
            return f"I had trouble connecting to the AI, but here is the start of your note: {fallback_text}..."