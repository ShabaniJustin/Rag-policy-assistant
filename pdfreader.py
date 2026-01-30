import os
from pypdf import PdfReader

def read_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"The file {pdf_path} does not exist.")

    reader = PdfReader(pdf_path)
    pages = [page.extract_text() for page in reader.pages]
    return pages

def read_pdf_from_file(file_object):
    """Read PDF from a file-like object (for uploaded files)."""
    reader = PdfReader(file_object)
    pages = [page.extract_text() for page in reader.pages]
    return pages