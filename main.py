from flask import Flask, render_template, request, jsonify
import os
import re
from dotenv import load_dotenv
import pandas as pd
from docx import Document as DocxDocument
import fitz  # PyMuPDF
from langchain_community.document_loaders import PyPDFLoader
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain_community.llms import Ollama
from langchain_openai.chat_models import ChatOpenAI
from langchain_community.embeddings import OllamaEmbeddings
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI
from langchain.schema import HumanMessage
from typing import List
import numpy as np
from rank_bm25 import BM25Okapi
import asyncio
import pickle
import time
import subprocess

app = Flask(__name__)

# Apply the nest_asyncio patch to allow nested event loops in Jupyter
# nest_asyncio.apply()

# Load environment variables from a .env file with API key
load_dotenv()

# Get the OpenAI API key from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Model configuration
MODEL = "gpt-4o-mini"  # Change this to your preferred model gpt-4o-mini has 200,000 tpm, gpt-4o has 30,000 tpm

# Initialize the model and embeddings based on the chosen MODEL
if MODEL.startswith("gpt"):
    model = ChatOpenAI(openai_api_key=OPENAI_API_KEY, model=MODEL)
    embeddings = OpenAIEmbeddings()
else:
    model = Ollama(model=MODEL)
    embeddings = OllamaEmbeddings(model=MODEL)

# Test the model with a simple invocation
try:
    model.invoke("Tell me a joke")
except Exception as e:
    print(f"Model invocation error: {e}")


# Define a custom loader for text files
class TextFileLoader:
    """Simple loader for text files to match the interface of PyPDFLoader"""

    def __init__(self, file_path):
        self.file_path = file_path

    def load_and_split(self):
        with open(self.file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        # Clean and trim the content
        cleaned_content = self.clean_and_trim(content)
        if len(cleaned_content) > 300:
            # Assuming each line in the text file represents a split page
            pages = cleaned_content.splitlines()
            return pages
        return []

    def clean_and_trim(self, text):
        # Remove extra spaces, newlines, and other unwanted characters
        text = re.sub(r'\s+', ' ', text).strip()
        return text


# Define a custom loader for DOCX files
class DocxFileLoader:
    """Loader for DOCX files to match the interface of PyPDFLoader"""

    def __init__(self, file_path):
        self.file_path = file_path

    def load_and_split(self):
        doc = DocxDocument(self.file_path)
        content = [p.text for p in doc.paragraphs]
        # Clean and trim the content
        cleaned_content = self.clean_and_trim(" ".join(content))
        if len(cleaned_content) > 300:
            return cleaned_content.split('\n')
        return []

    def clean_and_trim(self, text):
        # Remove extra spaces, newlines, and other unwanted characters
        text = re.sub(r'\s+', ' ', text).strip()
        return text


# Define a custom loader for XLSX files
class XlsxFileLoader:
    """Loader for XLSX files to match the interface of PyPDFLoader"""

    def __init__(self, file_path):
        self.file_path = file_path

    def load_and_split(self):
        content = []
        xlsx = pd.ExcelFile(self.file_path)
        for sheet_name in xlsx.sheet_names:
            df = pd.read_excel(xlsx, sheet_name=sheet_name)
            content.append(df.to_string(index=False))
        # Clean and trim the content
        cleaned_content = self.clean_and_trim(" ".join(content))
        if len(cleaned_content) > 300:
            return cleaned_content.split('\n')
        return []

    def clean_and_trim(self, text):
        # Remove extra spaces, newlines, and other unwanted characters
        text = re.sub(r'\s+', ' ', text).strip()
        return text


# Define a custom loader for PDFs using PyMuPDF
class PyMuPDFLoader:
    """Loader for PDFs using PyMuPDF (fitz)"""

    def __init__(self, file_path):
        self.file_path = file_path

    def load_and_split(self):
        content = []
        doc = fitz.open(self.file_path)
        for page in doc:
            content.append(page.get_text())
        # Clean and trim the content
        cleaned_content = self.clean_and_trim(" ".join(content))
        if len(cleaned_content) > 300:
            return cleaned_content.split('\n')
        return []

    def clean_and_trim(self, text):
        # Remove extra spaces, newlines, and other unwanted characters
        text = re.sub(r'\s+', ' ', text).strip()
        return text


# Function to load documents from a directory and its subdirectories
def load_documents(directory):
    all_pages = []
    accepted_documents = 0
    rejected_documents = 0

    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                if file.endswith('.pdf'):
                    loader = PyMuPDFLoader(file_path)
                elif file.endswith('.txt'):
                    loader = TextFileLoader(file_path)
                elif file.endswith('.docx'):
                    loader = DocxFileLoader(file_path)
                elif file.endswith('.xlsx'):
                    loader = XlsxFileLoader(file_path)
                else:
                    continue
                pages = loader.load_and_split()
                if pages:
                    all_pages.extend([Document(page_content=page) for page in pages])
                    accepted_documents += 1
                else:
                    rejected_documents += 1
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
                rejected_documents += 1

    print(f"Accepted documents: {accepted_documents}")
    print(f"Rejected documents: {rejected_documents}")
    return all_pages


# Function to batch documents into manageable sizes
def batch_documents(documents, batch_size):
    for i in range(0, len(documents), batch_size): #splits the document list into segments of size batch_size
        yield documents[i:i + batch_size]


# Save FAISS vector store to file
def save_faiss(vectorstore, index_file, doc_file): #vectorstore, which is the FAISS vector store object; index_file, the filename where the index should be saved; and doc_file, the filename where the document store should be saved
    vectorstore.save_local(index_file)
    with open(doc_file, 'wb') as f:
        pickle.dump(vectorstore.docstore, f) #Uses the pickle module to serialize and save the document store part of the vectorstore (stored in vectorstore.docstore) to the file


# Load FAISS vector store from file
def load_faiss(index_file, doc_file, embeddings):
    vectorstore = FAISS.load_local(index_file, embeddings, allow_dangerous_deserialization=True)
    with open(doc_file, 'rb') as f:
        vectorstore.docstore = pickle.load(f)
    return vectorstore


# Function to integrate chat history into the vector database
def integrate_chat_history(vectorstore, chat_history, embeddings):
    chat_documents = [Document(page_content=message) for message in chat_history] #Each chat message is stored as the page_content of a Document.
    # Create a temporary FAISS vector store for the chat history
    chat_vectorstore = FAISS.from_documents(chat_documents, embedding=embeddings) #Creates a temporary FAISS vector store from the list of chat documents using the specified embeddings.
    # Combine the chat vector store with the main vector store
    vectorstore.merge_from(chat_vectorstore)


# Example usage
directory = '/Users/nithiyapriyaramesh/Desktop/LLM_RAG/RAG_sourcecode/static/www.burpple.com'
pages = load_documents(directory)

# Check if any pages were loaded
if not pages:
    print("No documents found. Please check the directory path and file formats.")
else:
    # Define batch size to keep under token limit (adjust based on your use case)
    batch_size = 10
    vectorstores = []

    # Load existing FAISS vector store if available
    index_file = 'faiss_index'
    doc_file = 'index.pkl'
    if os.path.exists(index_file) and os.path.exists(doc_file):
        vectorstore = load_faiss(index_file, doc_file, embeddings)
        vectorstores.append(vectorstore)
        print("Loaded existing FAISS vector store.")
    else:
        print("No existing FAISS vector store found, creating a new one.")

    # Create FAISS vector stores for new batches of documents
    new_documents = []
    for batch in batch_documents(pages, batch_size):
        retry_attempts = 3
        while retry_attempts > 0:
            try:
                vectorstore = FAISS.from_documents(batch, embedding=embeddings)
                vectorstores.append(vectorstore)
                new_documents.extend(batch)
                break
            except Exception as e:
                print(f"Error creating vector store for batch: {e}")
                retry_attempts -= 1
                time.sleep(2)

                # Save the updated FAISS vector store
    if new_documents:
        vectorstore = FAISS.from_documents(new_documents, embedding=embeddings)
        save_faiss(vectorstore, index_file, doc_file)
        print("Updated FAISS vector store saved.")
    else:
        print("No new documents to update.")

    # Chat history integration
    chat_history = ["Hi, how are you?", "What is the latest update on AI research?"]  # Example chat history
    integrate_chat_history(vectorstore, chat_history, embeddings)
    print("Integrated chat history into the vector store.")


# Asynchronous querying of vector stores

async def query_vectorstore(vectorstore, query):
    retriever = vectorstore.as_retriever()
    response = await asyncio.to_thread(retriever.invoke, query)
    return response


async def query_vectorstores(vectorstores, query):
    tasks = [query_vectorstore(vectorstore, query) for vectorstore in vectorstores]
    responses = await asyncio.gather(*tasks)
    return responses


# Example query to the vector stores
async def main():
    query = "tell me about SIT"
    responses = await query_vectorstores(vectorstores, query)
    for response in responses:
        print(response)


# Define a function to generate rephrased versions of the input question
def generate_rephrased_questions(question):
    rephrased_templates = [
        "Can you explain about {}?",
        "What can you tell me about {}?",
        "Please provide details on {}.",
        "I'd like to know more about {}.",
        "Could you give an overview of {}?"
    ]
    rephrased_questions = [template.format(question) for template in rephrased_templates]
    return rephrased_questions


# Define a function to create a detailed context with rephrased questions
def create_detailed_context(context, question):
    rephrased_questions = generate_rephrased_questions(question)
    additional_context = f"Additional context about {question}."
    full_context = context + "\n" + additional_context + "\n" + "\n".join(rephrased_questions)
    return full_context


# Enhanced Retriever Class with BM25
class EnhancedRetriever:
    def __init__(self, vectorstores, top_k=5):
        self.vectorstores = vectorstores
        self.top_k = top_k

    async def get_relevant_documents(self, query):
        combined_results = []
        for vectorstore in self.vectorstores:
            retriever = vectorstore.as_retriever()
            results = await asyncio.to_thread(retriever.invoke, query)
            combined_results.extend(results)

        # Filter and rank the results using BM25
        combined_results = self.filter_and_rank_bm25(combined_results, query)
        return combined_results[:self.top_k]

    def filter_and_rank_bm25(self, documents, query):
        # Extract text from documents
        texts = [doc.page_content for doc in documents]
        if not texts:
            return []

        # Use BM25 to rank documents
        tokenized_texts = [text.split() for text in texts]
        bm25 = BM25Okapi(tokenized_texts)
        tokenized_query = query.split()
        scores = bm25.get_scores(tokenized_query)
        ranked_indices = np.argsort(scores)[::-1]

        # Rank documents
        ranked_documents = [documents[idx] for idx in ranked_indices]
        return ranked_documents


# Define a few-shot learning example
few_shot_examples = """
Example 1:
Context: The Singapore Institute of Technology (SIT) is Singapore’s fifth autonomous university and offers applied degree programmes focused on science and technology.
Question: What is the focus of SIT's degree programmes?
Answer: The Singapore Institute of Technology (SIT) focuses on applied degree programmes in science and technology.

Example 2:
Context: Fintech companies in Singapore are subject to regulations set by the Monetary Authority of Singapore (MAS), which oversees the financial sector and ensures its stability.
Question: What authority oversees fintech regulations in Singapore?
Answer: The Monetary Authority of Singapore (MAS) oversees fintech regulations in Singapore.
"""

# Define a prompt template with few-shot examples
prompt_template = PromptTemplate(
    input_variables=["context", "question"],
    template=few_shot_examples + "\n\nContext: {context}\n\nQuestion: {question}\nAnswer:"
)

# Custom function to chain the components

async def custom_chain(question, user_name):
    # Retrieve context documents dynamically using EnhancedRetriever
    retriever = EnhancedRetriever(vectorstores)
    context_documents = await retriever.get_relevant_documents(question)

    # Combine content of retrieved documents
    context = "\n".join([doc.page_content for doc in context_documents])

    # Create a detailed context with rephrased questions
    detailed_context = create_detailed_context(context, question)

    # Format the prompt with the detailed context and include user's name
    prompt = prompt_template.format(context=detailed_context, question=question)

    # Wrap the prompt in a HumanMessage object
    message = HumanMessage(content=f"{user_name}, {prompt}")

    # Get the answer from the model
    response = await asyncio.to_thread(model.invoke, [message])

    # Extract the content from the response
    clean_answer = response.content

    # Replace markdown bold syntax with HTML bold tags
    formatted_answer = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', clean_answer)

    # Replace newlines with <br> for HTML formatting
    formatted_answer = formatted_answer.replace('\n', '<br>')

    # Format response in HTML
    html_response = f"<b>{user_name}</b>, here are the details you asked for:<br><ul>{formatted_answer}</ul>"

    return html_response


# Route to serve the chat interface
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle chat messages
@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    user_name = request.json.get('name')
    if user_message and user_name:
        response = asyncio.run(custom_chain(user_message, user_name))
        return jsonify({'response': response})
    return jsonify({'response': 'No message provided.'})

# Route to install packages from requirements.txt
@app.route('/install_packages', methods=['POST'])
def install_packages():
    try:
        result = subprocess.run(['pip', 'install', '-r', 'requirements.txt'], capture_output=True, text=True)
        if result.returncode == 0:
            return jsonify({'response': 'Packages installed successfully.'})
        else:
            return jsonify({'response': f"Error installing packages: {result.stderr}"})
    except Exception as e:
        return jsonify({'response': f"Exception occurred: {str(e)}"})

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)

# Example questions and their responses using the enhanced custom chain
async def main_chain():
    questions = [
        "Tell me about clusters of SIT",
    ]

    for question in questions:
        answer = await custom_chain(question)
        print(f"Question: {question}")
        print(f"Answer: {answer}")
        print()


# Run the main_chain function to execute queries with the custom chain
asyncio.run(main_chain())
