from langchain.prompts import PromptTemplate

few_shot_examples = """
Example 1:
Context: SIT is Singapore’s fifth autonomous university.
Question: What is SIT?
Answer: SIT is Singapore’s fifth autonomous university.
"""

prompt_template = PromptTemplate(
    input_variables=["context", "question"],
    template=few_shot_examples + "\n\nContext: {context}\n\nQuestion: {question}\nAnswer:"
)

def create_detailed_context(context, question):
    return f"{context}\nAdditional context about {question}."
