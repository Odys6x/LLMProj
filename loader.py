import re
import fitz  # PyMuPDF
import pandas as pd
from docx import Document as DocxDocument

class BaseLoader:
    def __init__(self, file_path):
        self.file_path = file_path

    def clean_and_trim(self, text):
        return re.sub(r"\s+", " ", text).strip()

class TextFileLoader(BaseLoader):
    def load_and_split(self):
        with open(self.file_path, "r", encoding="utf-8") as file:
            return self.clean_and_trim(file.read()).split("\n")

class DocxFileLoader(BaseLoader):
    def load_and_split(self):
        doc = DocxDocument(self.file_path)
        return self.clean_and_trim(" ".join([p.text for p in doc.paragraphs])).split("\n")

class XlsxFileLoader(BaseLoader):
    def load_and_split(self):
        df = pd.read_excel(self.file_path, sheet_name=None)
        return self.clean_and_trim(" ".join([sheet.to_string(index=False) for sheet in df.values()])).split("\n")

class PyMuPDFLoader(BaseLoader):
    def load_and_split(self):
        doc = fitz.open(self.file_path)
        return self.clean_and_trim(" ".join([page.get_text() for page in doc])).split("\n")
