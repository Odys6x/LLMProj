import asyncio
from app.intent_classifier import IntentClassifier
from app.llm_agent import general_llm_response
from app.billing_agent import handle_billing_query
from app.chat import custom_chain as rag_response

# Initialize classifier
intent_classifier = IntentClassifier()

async def handle_query(question, user_name):
    """Routes queries based on intent detection."""

    intent = intent_classifier.classify(question)

    if intent == "technical":
        print("Detected a WiFi issue. Initiating troubleshooting...")
        response = await general_llm_response(question, user_name)  # Follow-up questions first

    elif intent == "installation":
        print("Detected an installation or user guide request. Routing to RAG...")
        response = await rag_response(question, user_name)  # DIRECT RAG for installation queries

    elif intent == "billing":
        print("Routing to Billing Support...")
        response = await handle_billing_query(question, user_name)

    else:  # General queries, including router recommendations
        print("General question detected. Routing to general chatbot.")
        response = await general_llm_response(question, user_name)

    return response