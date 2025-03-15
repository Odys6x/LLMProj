import asyncio
import re
from langchain.schema import HumanMessage
from app.prompts import create_detailed_context, prompt_template
from app.retriever import EnhancedRetriever
from app.vectorstore import load_faiss, save_faiss
from app.config import Config
from langchain_openai.chat_models import ChatOpenAI
from langchain_openai.embeddings import OpenAIEmbeddings

# Initialize model and embeddings
model = ChatOpenAI(openai_api_key=Config.OPENAI_API_KEY, model=Config.MODEL)
embeddings = OpenAIEmbeddings()

# Load FAISS vector store
vectorstore = load_faiss(Config.INDEX_FILE, Config.DOC_FILE, embeddings)

async def custom_chain(question, user_name):
    retriever = EnhancedRetriever([vectorstore])
    context_documents = await retriever.get_relevant_documents(question)
    
    context = "\n".join([doc.page_content for doc in context_documents])
    detailed_context = create_detailed_context(context, question)
    
    prompt = prompt_template.format(context=detailed_context, question=question)
    message = HumanMessage(content=f"{user_name}, {prompt}")

    response = await asyncio.to_thread(model.invoke, [message])
    
    clean_answer = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', response.content).replace('\n', '<br>')
    return f"<b>{user_name}</b>, here are the details:<br><ul>{clean_answer}</ul>"
