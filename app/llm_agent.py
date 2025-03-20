import asyncio
import re
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from app.config import Config

# Initialize the LLM agent
llm = ChatOpenAI(openai_api_key=Config.OPENAI_API_KEY, model="gpt-4o-mini")
user_chat_memory = {}
user_language = {}  # Store detected language per user

# Common greetings in multiple languages
GREETINGS = ["hi", "hello", "hey", "hola", "bonjour", "你好", "こんにちは", "안녕하세요", "hallo", "ciao", "வணக்கம்"]

async def detect_language(question):
    """Detects the user's language dynamically."""
    system_prompt = "Detect the language of the following message and reply ONLY with the language code (e.g., en, es, fr, zh, ta)."

    response = await llm.ainvoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ])

    detected_lang = response.content.strip().lower()
    return detected_lang if detected_lang else "en"  # Default to English

async def translate_text(text, target_lang):
    """Translates text dynamically into the detected user language."""
    if target_lang == "en":  # If English, no need to translate
        return text

    system_prompt = f"""
    Translate the following into {target_lang}, but DO NOT add any extra information, disclaimers, or metadata.
    ONLY return the translation of the given text, nothing else.
    
    Text: "{text}"
    """

    response = await llm.ainvoke([
        {"role": "system", "content": system_prompt}
    ])

    return response.content.strip()

async def dynamic_llm_response(question, user_name):
    """Handles queries, detects language, translates responses, and dynamically generates follow-up questions."""

    # **Detect user's language if not already stored OR if they switch languages**
    detected_lang = await detect_language(question)
    previous_lang = user_language.get(user_name, None)
    
    if previous_lang is None or detected_lang != previous_lang:
        user_language[user_name] = detected_lang  # Store language preference

    # **Handle greetings and respond in the detected language**
    if question.lower().strip() in GREETINGS:
        greeting_response = await translate_text("Hello! How can I assist you today?", detected_lang)
        return greeting_response

    # **Ensure user has a memory instance**
    if user_name not in user_chat_memory:
        user_chat_memory[user_name] = {
            "memory": ConversationBufferMemory(memory_key="chat_history"),
            "intent": None,
            "follow_up_count": 0
        }

    memory = user_chat_memory[user_name]["memory"]
    follow_up_count = user_chat_memory[user_name]["follow_up_count"]
    user_intent = user_chat_memory[user_name]["intent"]

    # **Store user query in memory**
    memory.save_context({"user": question}, {"bot": ""})

    # **Check if follow-up question limit is reached**
    if follow_up_count >= 5:
        print(f"[DEBUG] Maximum follow-ups reached for {user_name}. Escalating to RAG...")
        collected_answers = memory.load_memory_variables({})["chat_history"]
        return await escalate_to_rag(user_name, collected_answers)

    # **Construct dynamic troubleshooting prompt**
    prompt = f"""
    You are a helpful AI assistant specializing in WiFi troubleshooting and customer inquiries.
    The user {user_name} is experiencing an issue classified as **{user_intent}**.
    Here is their conversation history:

    {memory.load_memory_variables({})["chat_history"]}

    Based on this, do the following:
    - If more information is needed, ask a **specific follow-up question** to clarify the problem.
    - **You can ask up to 5 questions maximum** before giving a solution.
    - If the limit is reached, respond with: 'escalate_to_rag'
    - If enough details are collected, provide a **direct troubleshooting solution**.
    
    **Translate your response into {detected_lang}.**
    
    ONLY return the next response, **do not summarize** previous messages.
    """

    # **Call LLM to generate a response**
    response = await llm.ainvoke(prompt)
    translated_response = response.content.strip()

    # **Manually check for escalation trigger**
    if "escalate_to_rag" in translated_response.lower():
        print(f"[DEBUG] Escalation trigger detected for {user_name}.")
        collected_answers = memory.load_memory_variables({})["chat_history"]
        return await escalate_to_rag(user_name, collected_answers)

    # **Store AI's response in memory and update follow-up count**
    memory.save_context({"user": question}, {"bot": translated_response})
    user_chat_memory[user_name]["follow_up_count"] += 1  # Increment follow-up count

    return translated_response

async def escalate_to_rag(user_name, collected_answers):
    """Sends the collected chat history to RAG with a structured troubleshooting prompt in the user's language."""
    from app.chat import custom_chain as rag_response  # Avoid circular dependency

    user_lang = user_language.get(user_name, "en")

    # **Retrieve full chat history**
    memory_data = user_chat_memory[user_name]["memory"].load_memory_variables({})
    chat_history = memory_data.get("chat_history", "")

    history_text = "\n".join(chat_history.split("\n"))  # Ensure it's properly formatted


    troubleshooting_prompt = f"""
    The user {user_name} has been experiencing an issue with their WiFi. Below is the conversation history:

    {history_text}

    Based on this troubleshooting information, analyze the issue and provide a helpful solution.
    DO NOT rephrase the conversation or summarize it. Instead, diagnose the issue and suggest concrete troubleshooting steps.
    
    **Translate your response into {user_lang}.**
    """

    # **Send structured prompt to RAG**
    final_response = await rag_response(troubleshooting_prompt, user_name)

    # **Clear memory after escalation**
    del user_chat_memory[user_name]
    del user_language[user_name]

    return final_response
