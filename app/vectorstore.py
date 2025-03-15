import pickle
import os
import time
from langchain_community.vectorstores import FAISS

def save_faiss(vectorstore, index_file, doc_file):
    vectorstore.save_local(index_file)
    with open(doc_file, "wb") as f:
        pickle.dump(vectorstore.docstore, f)

def load_faiss(index_file, doc_file, embeddings):
    if os.path.exists(index_file) and os.path.exists(doc_file):
        vectorstore = FAISS.load_local(index_file, embeddings, allow_dangerous_deserialization=True)
        with open(doc_file, "rb") as f:
            vectorstore.docstore = pickle.load(f)
        return vectorstore
    return None
