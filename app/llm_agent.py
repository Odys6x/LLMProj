# import asyncio
# from langchain_openai.chat_models import ChatOpenAI
# from app.config import Config

# # Initialize the LLM
# general_llm = ChatOpenAI(openai_api_key=Config.OPENAI_API_KEY, model="gpt-4o")

# # Store chat history per user
# user_chat_history = {}

# # Follow-up questions in sequence
# FOLLOW_UP_QUESTIONS = [
#     "Are you experiencing this issue on all devices or just one?",
#     "Is it slow all the time or only at specific hours?",
#     "Have you tried rebooting your router?",
#     "Does the issue happen on both WiFi and wired connections?",
#     "Do you notice speed drops in a specific location at home?"
# ]

# async def general_llm_response(question, user_name):
#     """Handles general queries and asks follow-up questions before sending to RAG."""

#     if user_name not in user_chat_history:
#         user_chat_history[user_name] = []

#     # Append user query to history
#     user_chat_history[user_name].append({"user": question})

#     # If enough questions were asked, escalate to RAG
#     if len(user_chat_history[user_name]) >= len(FOLLOW_UP_QUESTIONS):
#         print(f"Collected enough details from {user_name}, forwarding to RAG...")
#         return await escalate_to_rag(user_name)
    
#     # Get the next follow-up question
#     next_question_index = len(user_chat_history[user_name]) - 1
#     next_question = FOLLOW_UP_QUESTIONS[next_question_index]

#     # Strictly enforce that the LLM only asks a single follow-up question
#     return next_question  # This prevents LLM from over-explaining

# async def escalate_to_rag(user_name):
#     """Sends the collected chat history to RAG with a structured troubleshooting prompt."""
#     from app.chat import custom_chain as rag_response  # Import inside to avoid circular dependency

#     # Retrieve full chat history
#     history_text = "\n".join(
#         f"User: {entry.get('user', '[System]')}\nBot: {entry.get('bot', '')}" 
#         for entry in user_chat_history[user_name]
#     )

#     # Create a structured troubleshooting prompt for RAG
#     troubleshooting_prompt = f"""
#     The user {user_name} has been experiencing an issue with their WiFi. Below is the conversation history:
    
#     {history_text}
    
#     Based on this troubleshooting information, analyze the issue and provide a helpful solution.
#     DO NOT rephrase the conversation or summarize it. Instead, diagnose the issue and suggest concrete troubleshooting steps.
#     """

#     # Send the structured troubleshooting prompt to RAG
#     final_response = await rag_response(troubleshooting_prompt, user_name)

#     # Clear history after escalation
#     del user_chat_history[user_name]

#     return final_response

import asyncio
import re
from langchain_openai.chat_models import ChatOpenAI
from app.config import Config

# Initialize the LLM
general_llm = ChatOpenAI(openai_api_key=Config.OPENAI_API_KEY, model="gpt-4o-mini")

# Store chat history per user
user_chat_history = {}
user_language = {}
user_intent_history = {}


# Follow-up questions in sequence
FOLLOW_UP_QUESTIONS = [
    "Are you experiencing this issue on all devices or just one?",
    "Is it slow all the time or only at specific hours?",
    "Have you tried rebooting your router?",
    "Does the issue happen on both WiFi and wired connections?",
    "Do you notice speed drops in a specific location at home?"
]

# Define vague responses that require clarification
UNCLEAR_RESPONSES = {"just", "idk", "maybe", "not sure"}
def is_nonsense(text):
    """Detects gibberish text based on randomness, missing vowels, or excessive consonants."""
    text = text.lower().strip()
    if len(text) < 3 or re.match(r"^[^a-zA-Z]+$", text) or re.match(r"^([a-zA-Z])\1{2,}$", text):
        return True
    if not re.search(r"[aeiouy]", text) or re.search(r"[bcdfghjklmnpqrstvwxyz]{6,}", text, re.I):
        return True
    return False

async def general_llm_response(question, user_name):
    """Handles general queries and ensures all follow-up questions are answered before processing."""

    if user_name not in user_chat_history:
        user_chat_history[user_name] = {"history": [], "follow_up_count": 0}

    # Define common greetings
    GREETINGS = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening", "hola", "yo"}
    if question.lower().strip() in GREETINGS:
        return "Hello! How can I assist you today?"

    # Handle gibberish input
    if is_nonsense(question):
        return "I didn't quite understand that. Could you rephrase your response?"

    # Retrieve follow-up progress
    follow_up_count = user_chat_history[user_name]["follow_up_count"]

    # Ensure follow-up sequence completes before switching
    if follow_up_count < len(FOLLOW_UP_QUESTIONS):
        next_question = FOLLOW_UP_QUESTIONS[follow_up_count]
        user_chat_history[user_name]["history"].append({"user": question, "bot": next_question})
        user_chat_history[user_name]["follow_up_count"] += 1  # Move to next question
        return next_question  # Continue follow-ups

    # **All follow-up questions completed, now escalate to RAG**
    print(f"[DEBUG] All follow-up questions answered by {user_name}. Forwarding to RAG...")

    # Construct full conversation history
    collected_answers = "\n".join(
        f"User: {entry['user']}\nBot: {entry['bot']}" for entry in user_chat_history[user_name]["history"]
    )

    # Call RAG or troubleshooting function with full collected answers
    user_intent_history[user_name] = "installation"  # Set intent for RAG
    return await escalate_to_rag(user_name, collected_answers)

async def escalate_to_rag(user_name, collected_answers):
    """Sends the collected chat history to RAG with a structured troubleshooting prompt."""
    from app.chat import custom_chain as rag_response  # Import inside to avoid circular dependency

    # Create a structured troubleshooting prompt for RAG
    troubleshooting_prompt = f"""
    The user {user_name} has been experiencing an issue with their WiFi. Below is the conversation history:
    
    {collected_answers}
    
    Based on this troubleshooting information, analyze the issue and provide a helpful solution.
    DO NOT rephrase the conversation or summarize it. Instead, diagnose the issue and suggest concrete troubleshooting steps.
    """

    # Send the structured troubleshooting prompt to RAG
    final_response = await rag_response(troubleshooting_prompt, user_name)

    # Clear history after escalation
    user_chat_history[user_name] = {"history": [], "follow_up_count": 0}  # Reset for next query

    return final_response