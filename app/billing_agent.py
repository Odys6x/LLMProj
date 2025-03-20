import asyncio
from langchain_openai.chat_models import ChatOpenAI
from app.config import Config

# Billing support model
billing_agent = ChatOpenAI(openai_api_key=Config.OPENAI_API_KEY, model="gpt-4o-mini")

async def handle_billing_query(question, user_name):
    """Handles user queries related to billing and account management."""
    
    billing_faq = """
    - To check your bill, visit your account dashboard.
    - To upgrade/downgrade your plan, call customer support or go online.
    - Refunds can take up to 5-7 business days.
    """

    response_prompt = f"{user_name}, here’s what I found regarding billing: {billing_faq} \n\nYour question: {question}"
    response = await asyncio.to_thread(billing_agent.invoke, response_prompt)
    # response = await billing_agent.invoke(response_prompt)

    return response.content