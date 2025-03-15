import os

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MODEL = "gpt-4o-mini"
    INDEX_FILE = "faiss_index"
    DOC_FILE = "index.pkl"