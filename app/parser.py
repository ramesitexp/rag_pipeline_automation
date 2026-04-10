import fitz  # PyMuPDF

def parse_pdf(filepath: str) -> str:
    """
    Extracts raw text from a PDF file.
    """
    doc = fitz.open(filepath)
    text = ""
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text += page.get_text()
    
    doc.close()
    return text
