import asyncio
import re
from langchain.schema import HumanMessage
from app.prompt import create_detailed_context, prompt_template
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
    """Combines RAG-based retrieval and structured troubleshooting for a more natural response."""

    # Retrieve relevant RAG documents
    retriever = EnhancedRetriever([vectorstore])
    context_documents = await retriever.get_relevant_documents(question)
    
    # Extract and clean context from documents
    context = "\n".join([doc.page_content for doc in context_documents])
    detailed_context = create_detailed_context(context, question)

    # Format troubleshooting prompt
    prompt = f"""
    You are a WiFi troubleshooting assistant for an ISP company. The user is experiencing the following issue:
    
    {question}

    Additional relevant information:
    {detailed_context}
    
    Your task:
    - Identify the root cause of the issue.
    - Suggest actionable troubleshooting steps.
    - DO NOT summarize or rewrite the conversation. Just diagnose and help fix the issue.
    - Address the user directly as "you" instead of referring to them in the third person
    """

    # Send prompt to the model
    response = await asyncio.to_thread(model.invoke, [HumanMessage(content=prompt)])
    
    # Extract and clean response content
    clean_answer = response.content

    # Replace markdown bold syntax with HTML bold tags
    formatted_answer = re.sub(r'\*\*(.*?)\*\*', r'<b>\g<1></b>', clean_answer)

    # Replace newlines with spaces for a natural flow
    formatted_answer = formatted_answer.replace("\n", " ")

    # Remove numbered points (e.g., "1.", "2.") for a conversational tone
    formatted_answer = re.sub(r"\d+\.\s*", "", formatted_answer)

    # Ensure smooth transitions by replacing rigid separators
    formatted_answer = formatted_answer.replace("•", "").replace(" - ", ", ").replace(":", ", ")

    # Make the response feel more like human speech
    formatted_answer = (
        f"{formatted_answer} Just follow the steps, and you'll be all set! Let me know if you need any extra help."
    )

    return formatted_answer