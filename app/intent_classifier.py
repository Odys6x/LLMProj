import openai
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from langchain.memory import ConversationBufferMemory
import os

# Load API key from environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")

# Store chat memory per user (shared between intent classifier & follow-up handler)
user_chat_memory = {}

class IntentClassifier:
    def __init__(self, model_name="gpt-4"):
        self.llm = ChatOpenAI(model_name=model_name)

    def classify(self, query, user_name):
        """Classifies user intent dynamically using LLM and stores it in shared memory."""

        if user_name not in user_chat_memory:
            user_chat_memory[user_name] = {
                "memory": ConversationBufferMemory(memory_key="chat_history"),
                "intent": None,  
                "follow_up_count": 0,
                "escalated": False  
            }

        memory = user_chat_memory[user_name]["memory"]

        # **Check if the issue was already escalated**
        if user_chat_memory[user_name]["escalated"]:
            print(f"[DEBUG] Issue for {user_name} has already been escalated.")
            return "escalation"

        # **Manually Detect Escalation Phrases**
        escalation_triggers = [
            "it still doesn’t work", "issue persists", "not fixed", 
            "not working", "call IT", "contact support", "need more help", "escalate this"
        ]
        if any(trigger in query.lower() for trigger in escalation_triggers):
            print(f"[DEBUG] Escalation triggered by user input: {query}")
            user_chat_memory[user_name]["escalated"] = True
            return "escalation"

        # **Use LLM for Intent Classification**
        system_prompt = (
            "You are an intelligent intent classifier for a chatbot handling WiFi, "
            "network, and billing inquiries. Classify the user's query into one of "
            "the following intents:\n"
            "1. 'technical' - If the user is troubleshooting WiFi or network issues.\n"
            "2. 'installation' - If the user is asking for setup or configuration steps.\n"
            "3. 'general' - If the user has a general query about WiFi or ISPs.\n"
            "4. 'billing' - If the user is asking about bills, invoices, or subscriptions.\n"
            "5. 'escalation' - If the user says 'it still doesn’t work', 'issue persists', "
            "or requests IT support, escalate the issue.\n"
            "Return only the intent as output."
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"User Query: {query}")
        ]

        response = self.llm.invoke(messages).content.strip().lower()

        # **Ensure "escalation" intent is prioritized**
        if response == "escalation":
            user_chat_memory[user_name]["escalated"] = True
            return "escalation"

        # Store classified intent in shared memory
        user_chat_memory[user_name]["intent"] = response
        print(f"Detected intent for {user_name}: {response}")

        # Save query in memory so follow-ups have full context
        memory.save_context({"user": query}, {"bot": f"[Intent: {response}]"})

        
        return response
    
    def reset_escalation(self, user_name):
        """Resets the escalation flag so future queries are handled normally."""
        if user_name in user_chat_memory:
            user_chat_memory[user_name]["escalated"] = False
            print(f"[DEBUG] Escalation flag reset for {user_name}.")

