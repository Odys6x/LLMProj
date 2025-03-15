import asyncio
from langchain_openai.chat_models import ChatOpenAI
from app.config import Config

# Initialize the LLM
general_llm = ChatOpenAI(openai_api_key=Config.OPENAI_API_KEY, model="gpt-4o")

# Store chat history per user
user_chat_history = {}

# Follow-up questions in sequence
FOLLOW_UP_QUESTIONS = [
    "Are you experiencing this issue on all devices or just one?",
    "Is it slow all the time or only at specific hours?",
    "Have you tried rebooting your router?",
    "Does the issue happen on both WiFi and wired connections?",
    "Do you notice speed drops in a specific location at home?"
]

async def general_llm_response(question, user_name):
    """Handles general queries and asks follow-up questions before sending to RAG."""

    if user_name not in user_chat_history:
        user_chat_history[user_name] = []

    # Append user query to history
    user_chat_history[user_name].append({"user": question})

    # If enough questions were asked, escalate to RAG
    if len(user_chat_history[user_name]) >= len(FOLLOW_UP_QUESTIONS):
        print(f"Collected enough details from {user_name}, forwarding to RAG...")
        return await escalate_to_rag(user_name)
    
    # Get the next follow-up question
    next_question_index = len(user_chat_history[user_name]) - 1
    next_question = FOLLOW_UP_QUESTIONS[next_question_index]

    # Strictly enforce that the LLM only asks a single follow-up question
    return next_question  # This prevents LLM from over-explaining

async def escalate_to_rag(user_name):
    """Sends the collected chat history to RAG with a structured troubleshooting prompt."""
    from app.chat import custom_chain as rag_response  # Import inside to avoid circular dependency

    # Retrieve full chat history
    history_text = "\n".join(
        f"User: {entry.get('user', '[System]')}\nBot: {entry.get('bot', '')}" 
        for entry in user_chat_history[user_name]
    )

    # Create a structured troubleshooting prompt for RAG
    troubleshooting_prompt = f"""
    The user {user_name} has been experiencing an issue with their WiFi. Below is the conversation history:
    
    {history_text}
    
    Based on this troubleshooting information, analyze the issue and provide a helpful solution.
    DO NOT rephrase the conversation or summarize it. Instead, diagnose the issue and suggest concrete troubleshooting steps.
    """

    # Send the structured troubleshooting prompt to RAG
    final_response = await rag_response(troubleshooting_prompt, user_name)

    # Clear history after escalation
    del user_chat_history[user_name]

    return final_response

