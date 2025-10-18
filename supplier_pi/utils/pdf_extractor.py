import fitz  # PyMuPDF
import os

def extract_text_from_pdf(pdf_path):
    """
    Extracts and returns all text from a given PDF file.
    """
    if not os.path.exists(pdf_path):
        return ""

    text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        print(f"❌ Error reading PDF {pdf_path}: {e}")
        return ""

    return text.strip()