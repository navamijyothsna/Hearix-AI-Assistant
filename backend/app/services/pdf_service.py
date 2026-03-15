import PyPDF2
from google import genai

# --- Configure the AI Model ---
# ⚠️ REPLACE THIS WITH YOUR ACTUAL API KEY FROM GOOGLE AI STUDIO
GEMINI_API_KEY = "AIzaSyAldSEqtgsT-h3XfAbGpp7enbojqJ1hdgY"

# Initialize the new GenAI client
try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"Failed to initialize GenAI Client: {e}")
    client = None

class PDFService:
    @staticmethod
    def extract_text(file_path: str) -> str:
        """Extracts all text from a PDF file."""
        try:
            with open(file_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                # Limiting to the first 10 pages for speed and API limits during development
                max_pages = min(len(reader.pages), 10) 
                for i in range(max_pages):
                    extracted = reader.pages[i].extract_text()
                    if extracted:
                        text += extracted + " "
                
                print(f"DEBUG: Successfully extracted {len(text)} characters from {file_path}")
                return text.strip()
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""

    @staticmethod
    def chunk_and_summarize(text: str, subject: str) -> str:
        """Uses True AI to generate a contextual summary for a blind student."""
        if not text:
            return "The document appears to be empty or unreadable."
            
        if not client:
             return "The AI client failed to initialize. Please check your API key."
        
        prompt = f"""
        You are an academic voice assistant designed to help visually impaired students. 
        The student has asked for a summary of their notes for the subject '{subject}'.
        
        Read the following extracted text from their PDF notes and provide a clear, 
        easy-to-listen-to summary. 
        Keep it under 4 sentences. Speak naturally, without using formatting like asterisks or bullet points.
        
        Extracted Text:
        {text[:5000]} 
        """
        
        try:
            print("DEBUG: Sending request to the new Gemini API for Summary...")
            # Use the new syntax for generating content
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            print("DEBUG: Successfully received response from Gemini API.")
            return response.text.replace("*", "") 
        except Exception as e:
            print(f"CRITICAL API ERROR (Summary): {str(e)}")
            return f"I found the notes for {subject}, but the AI service is currently unavailable."

    @staticmethod
    def extract_specific_topic(text: str, topic: str) -> str:
        """Uses True AI to find the answer to a specific topic within the notes."""
        if not text:
            return "The document appears to be empty."
            
        if not client:
             return "The AI client failed to initialize. Please check your API key."

        prompt = f"""
        You are an academic voice assistant for a visually impaired student.
        The student has asked you to explain or find information about a specific topic: '{topic}'.
        
        Search through the provided text below. If you find information about the topic, 
        explain it clearly and concisely in 2 or 3 sentences. 
        If the topic is NOT mentioned anywhere in the text, simply reply: 
        "I could not find any information about {topic} in these notes."
        Do not use formatting like bolding or bullet points, as this will be read by a Text-to-Speech engine.
        
        Extracted Text:
        {text[:10000]}
        """
        
        try:
            print(f"DEBUG: Sending request to the new Gemini API for Topic: {topic}...")
            # Use the new syntax for generating content
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            print("DEBUG: Successfully received response from Gemini API.")
            return response.text.replace("*", "")
        except Exception as e:
            print(f"CRITICAL API ERROR (Topic): {str(e)}")
            return f"I am having trouble analyzing the notes for {topic} right now."