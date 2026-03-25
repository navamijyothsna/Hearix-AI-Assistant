import os
from reportlab.pdfgen import canvas
from fastapi.testclient import TestClient
from main import app, PDF_DIR

client = TestClient(app)

def setup_test_pdf():
    pdf_path = "biology_notes.pdf"
    c = canvas.Canvas(pdf_path)
    c.drawString(100, 750, "The cell is the basic structural and functional unit of life.")
    c.drawString(100, 730, "Mitochondria is the powerhouse of the cell, generating ATP.")
    c.save()
    return pdf_path

def run_tests():
    print("Testing /health...")
    assert client.get("/health").status_code == 200
    
    pdf_path = setup_test_pdf()
    
    print("Testing /upload...")
    with open(pdf_path, "rb") as f:
        response = client.post("/upload", files={"file": ("biology_notes.pdf", f, "application/pdf")})
        assert response.status_code == 200
        
    print("Testing /pdfs...")
    response = client.get("/pdfs")
    assert response.status_code == 200
    assert "biology_notes.pdf" in response.json()["pdfs"]
    
    print("Testing /query (successful match)...")
    response = client.post("/query", json={
        "document_name": "biology",
        "topic": "mitochondria"
    })
    assert response.status_code == 200
    assert "powerhouse" in response.json()["response"]
    
    print("Testing /query (no match)...")
    response = client.post("/query", json={
        "document_name": "biology",
        "topic": "quantum physics"
    })
    assert "couldn't find any information" in response.json()["response"]
    
    print("\n--- All Backend End-to-End Tests Passed! ---")
    
if __name__ == "__main__":
    run_tests()
