import fitz

def parse_document(file_path) -> fitz.Document:
    return fitz.open(file_path)