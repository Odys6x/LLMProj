import asyncio
from app.intent_classifier import IntentClassifier
from app.llm_agent import dynamic_llm_response as general_llm_response
from app.billing_agent import handle_billing_query
from app.chat import custom_chain as rag_response

# Initialize classifier
intent_classifier = IntentClassifier()

async def handle_query(question, user_name):
    """Routes queries based on intent detection."""

    intent = intent_classifier.classify(question, user_name)

    if intent == "technical":
        print("Detected a WiFi issue. Initiating troubleshooting...")
        response = await general_llm_response(question, user_name)  

    elif intent == "installation":
        print("Detected an installation or user guide request. Routing to RAG...")
        response = await rag_response(question, user_name)  

    elif intent == "billing":
        print("Routing to Billing Support...")
        response = await handle_billing_query(question, user_name)

    elif intent == "escalation":
        print("Escalating issue for User to IT support....")
        response = escalate_to_it(user_name)  # **NOW CALLING ESCALATION FUNCTION**

        # **Fix: Reset escalation after response**
        intent_classifier.reset_escalation(user_name)

    else:  # General queries
        print("General question detected. Routing to general chatbot.")
        response = await general_llm_response(question, user_name)

    return response

def escalate_to_it(user_name):
    """Handles escalation to IT support."""
    print(f"[DEBUG] Escalating issue for {user_name} to IT support.")
    return "This will be escalated to the IT side or an officer will speak with you."
