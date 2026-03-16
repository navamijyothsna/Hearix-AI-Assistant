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
                # Safeguard: Only read the first 3 pages to prevent 429 Token limits
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
        # Extra Safeguard: Hard cutoff at 15,000 characters (keeps it safely inside free tier)
        safe_text = text[:15000] 

        if not safe_text.strip():
            return "The document appears to be empty or contains unreadable images instead of text."

        try:
            # Initialize the new Google GenAI client
            # It automatically picks up the GEMINI_API_KEY from your Render environment variables
            client = genai.Client()
            
            prompt = f"""
            You are an accessible academic assistant for a visually impaired student. 
            Based ONLY on the text below, provide a short, clear, 2-to-3 sentence spoken summary about {subject}. 
            Do not use complex formatting, markdown, or bullet points because this will be read aloud by a screen reader.
            
            Text:
            {safe_text}
            """
            
            # Downgrade to 1.5-flash: It has much higher free tier limits than 2.0!
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt,
            )
            
            return response.text

        except Exception as e:
            print(f"Gemini API Error: {e}")
            return "I'm sorry, the document is too large for my current limits. Please upload a shorter document."