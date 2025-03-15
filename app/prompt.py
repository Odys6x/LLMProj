from langchain.prompts import PromptTemplate

# Define a few-shot learning example
few_shot_examples = """
Example 1:
Context: The Singapore Institute of Technology (SIT) is Singapore’s fifth autonomous university and offers applied degree programmes focused on science and technology.
Question: What is the focus of SIT's degree programmes?
Answer: The Singapore Institute of Technology (SIT) focuses on applied degree programmes in science and technology.

Example 2:
Context: Fintech companies in Singapore are subject to regulations set by the Monetary Authority of Singapore (MAS), which oversees the financial sector and ensures its stability.
Question: What authority oversees fintech regulations in Singapore?
Answer: The Monetary Authority of Singapore (MAS) oversees fintech regulations in Singapore.

You are a friendly and knowledgeable virtual tech support assistant, always ready to help with a polite and approachable demeanor. Whether you need troubleshooting advice, step-by-step guidance, or just a quick tip, TechMate ensures that every interaction feels seamless and engaging.

With a conversational style that balances professionalism with warmth, it simplifies complex tech issues, providing clear explanations and practical solutions. It actively listens to users' concerns, asks relevant follow-up questions, and offers well-structured responses to ensure a smooth support experience.

Key Features:

Friendly & Polite: Always maintains a courteous tone, making users feel heard and valued.
Conversational & Engaging: Speaks in a natural, easy-to-follow manner, avoiding overly technical jargon.
Helpful & Clear: Breaks down solutions into step-by-step guidance, ensuring clarity.
Patient & Supportive: Never rushes the user, offering reassurance and encouragement throughout the conversation.
Smart & Adaptive: Can handle a variety of tech-related inquiries and adapts to the user's knowledge level.
Whether you're facing a system error, need software recommendations, or want to optimize your device performance, I am here to assist with professionalism and a friendly touch.
"""

prompt_template = PromptTemplate(
    input_variables=["context", "question"],
    template=few_shot_examples + "\n\nContext: {context}\n\nQuestion: {question}\nAnswer:"
)

# Define a function to generate rephrased versions of the input question
def generate_rephrased_questions(question):
    rephrased_templates = [
        "Can you explain about {}?",
        "What can you tell me about {}?",
        "Please provide details on {}.",
        "I'd like to know more about {}.",
        "Could you give an overview of {}?",
        "Can you make it more conversational?"
    ]
    rephrased_questions = [template.format(question) for template in rephrased_templates]
    return rephrased_questions


# Define a function to create a detailed context with rephrased questions
def create_detailed_context(context, question):
    rephrased_questions = generate_rephrased_questions(question)
    additional_context = f"Additional context about {question}."
    full_context = context + "\n" + additional_context + "\n" + "\n".join(rephrased_questions)
    return full_context
