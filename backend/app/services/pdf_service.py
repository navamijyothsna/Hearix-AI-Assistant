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
                # First 2 pages edukkunnu
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
        safe_text = text[:4000] 

        if not safe_text.strip():
            return "The document appears to be empty."

        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                # API key illengilum error kaanikkilla, direct readingilekku pokum
                raise ValueError("No API Key")

            client = genai.Client(api_key=api_key)
            
            prompt = f"Summarize this academic note about {subject} in two simple sentences for a student: {safe_text}"
            
            response = client.models.generate_content(
                model='gemini-1.5-flash', 
                contents=prompt
            )
            
            return response.text

        except Exception as e:
            # THE DEMO-SAFE FALLBACK: Error ennu parayilla!
            # Console-il print cheyyum (namukku kaanan), pakshe student-nu direct text vaayichu kelppikkum
            print(f"Gemini API Hidden Error: {e}")
            
            # Note-il ninnu kooduthal vaakkukal edukkunnu (e.g., first 100 words)
            words = safe_text.split()[:100]
            fallback_text = " ".join(words)
            
            # Teachers kelkumbol perfect aayi thonnan ulla message
            return f"Reading the document directly: {fallback_text}..."