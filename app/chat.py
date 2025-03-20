import asyncio
import re
from langchain.schema import HumanMessage
from app.prompt import create_detailed_context, prompt_template
from app.retriever import EnhancedRetriever
from app.vectorstore import load_faiss, save_faiss
from app.config import Config
from langchain_openai.chat_models import ChatOpenAI
from langchain_openai.embeddings import OpenAIEmbeddings
import time

# Initialize model and embeddings
model = ChatOpenAI(openai_api_key=Config.OPENAI_API_KEY, model=Config.MODEL)
embeddings = OpenAIEmbeddings()

# Load FAISS vector store
vectorstore = load_faiss(Config.INDEX_FILE, Config.DOC_FILE, embeddings)

# Ensure FAISS is loaded only once and use a global cache
if "retriever" not in globals():
    retriever = EnhancedRetriever([vectorstore])

# Global cache for previous queries
if "query_cache" not in globals():
    query_cache = {}  # This will persist across function calls

# Store chat history per user
if "user_conversation_history" not in globals():
    user_conversation_history = {}

# Limit response length while keeping key details
# def shorten_response(text, max_length=350):
#     sentences = text.split(". ")
#     summary = []
#     char_count = 0

#     for sentence in sentences:
#         if char_count + len(sentence) > max_length:
#             break
#         summary.append(sentence)
#         char_count += len(sentence) + 2  # Account for ". "

#     return ". ".join(summary) + "." # Ensures strict token limit

def shorten_response(text, max_length=400):
    words = text.split()
    if len(words) <= max_length:
        return text  # If already within the limit, return as is

    shortened_text = " ".join(words[:max_length])
    
    # Ensure we end on a complete sentence
    last_period = shortened_text.rfind(".")
    if last_period != -1:
        return shortened_text[:last_period + 1]  # Cut off at the last full sentence

    return shortened_text  # If no period is found, return as is

def clean_response(text):
    """Cleans AI response to remove Markdown and improve readability."""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Remove bold markdown
    text = text.replace("\n", " ")  # Remove new lines
    text = re.sub(r"\d+\.\s*", "", text)  # Remove numbered steps
    text = text.replace("•", "")  # Remove bullet points
    text = text.replace(" - ", ", ").replace(":", ", ")  # Smooth transitions
    return text.strip()

async def custom_chain(question, user_name):
    """Combines RAG-based retrieval and structured troubleshooting for a more natural response."""
    print(f"[DEBUG] Received question: {question} from user: {user_name}")
    print("[DEBUG] User conversation history:", user_conversation_history)

    normalized_question = question.strip().lower()

    if normalized_question in {"what's next", "continue", "next step", "go on", "whats next"}:
        if user_name in user_conversation_history and user_conversation_history[user_name]:
            # Retrieve the last AI response
            last_response = user_conversation_history[user_name][-1]
            
            # Format the prompt to continue from last response
            continuation_prompt = f"""
            The user previously received this response:
            
            {last_response}

            Now, they are asking: "{question}"
            
            Your task:
            - Continue from the last response, ensuring you do NOT repeat previous steps.
            - Provide exactly 2-3 next steps in a logical sequence.
            - Summarize the next steps concisely in simple and natural language.
            - Keep responses under 400 tokens while answering the question.
            - Be helpful and conversational in your tone.
            """

            # Generate next part of the response, ensuring it remains short and conversational
            next_response = await model.ainvoke([HumanMessage(content=continuation_prompt)], max_tokens=300)

            # Clean and store the response
            cleaned_response = clean_response(shorten_response(next_response.content))
            user_conversation_history[user_name].append({"user": question, "ai": cleaned_response})
            return cleaned_response  # Return the new, continued response

    # Check cache before querying FAISS
    if normalized_question in query_cache:
        print("[DEBUG] Using cached response for:", normalized_question)
        context_documents = query_cache[normalized_question]
    else:
        print("[DEBUG] Querying FAISS for:", normalized_question)
        start_time = time.time()
        context_documents = await retriever.get_relevant_documents(question)
        end_time = time.time()
        print(f"[DEBUG] FAISS retrieval took {end_time - start_time:.2f} seconds")
        query_cache[normalized_question] = context_documents  # Store result in cache

    # Ensure user has a conversation history
    if user_name not in user_conversation_history:
        user_conversation_history[user_name] = []

    # Add the new question to history
    user_conversation_history[user_name].append({"user": question})

    # Retrieve previous conversation history
    previous_context = "\n".join([
    f"User: {entry['user']}\nAI: {entry.get('ai', '')}" 
    if isinstance(entry, dict) else f"AI: {entry}"
    for entry in user_conversation_history[user_name][-3:]
    ])
    print("[DEBUG] Previous context:", previous_context)

    # Extract and clean context from documents
    context = "\n".join([doc.page_content for doc in context_documents])
    detailed_context = create_detailed_context(context, question)

    # Modify prompt to include chat history
    prompt = f"""
    You are a helpful assistant. Below is the conversation history so far:
    {previous_context}
    Now, the user has asked:
    {question}
    Additional relevant information:
    {detailed_context}
    Your task:
    - Fully answer the user’s question while keeping responses short (2-3 key points only).
    - Avoid generic responses. Ensure that every response is actionable and informative.
    - If the user is asking for the next step, summarize only the next 2-3 actions without repeating previous steps.
    - Respond naturally in a conversational tone, ensuring readability for a voice assistant.
    - If it’s a new topic, reset the context accordingly but provide a direct and structured answer.
    """
    print("[DEBUG] Sending prompt to LLM")

    start_time = time.time()
    response = await model.ainvoke([HumanMessage(content=prompt)], max_tokens=400)
    end_time = time.time()
    print(f"[DEBUG] LLM response time: {end_time - start_time:.2f} seconds")
    clean_answer = clean_response(shorten_response(response.content))
    formatted_answer = f"{clean_answer} Let me know if you need any extra help."
    # Store AI response in history
    user_conversation_history[user_name].append(formatted_answer)
    return formatted_answer
