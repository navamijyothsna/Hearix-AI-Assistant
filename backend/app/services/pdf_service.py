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
                # Safeguard: Only read the first 3 pages
                num_pages = min(len(reader.pages), 3) 
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
        safe_text = text[:15000] 

        if not safe_text.strip():
            return "The document appears to be empty or contains unreadable images instead of text."

        try:
            # EXPLICITLY grab the key from Render's environment
            api_key = os.getenv("GEMINI_API_KEY")
            
            if not api_key:
                return "Server Error: The GEMINI_API_KEY is missing from Render."

            # Pass the key directly to the client
            client = genai.Client(api_key=api_key)
            
            prompt = f"""
            You are an accessible academic assistant for a visually impaired student. 
            Based ONLY on the text below, provide a short, clear, 2-to-3 sentence spoken summary about {subject}. 
            Do not use complex formatting, markdown, or bullet points because this will be read aloud by a screen reader.
            
            Text:
            {safe_text}
            """
            
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt,
            )
            
            return response.text

        except Exception as e:
            # THIS IS THE FIX: Print the ACTUAL error to the screen so we can see what's wrong!
            error_msg = str(e)
            print(f"Gemini API Error: {error_msg}")
            return f"AI System Error: {error_msg}"