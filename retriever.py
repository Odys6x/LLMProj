import numpy as np
from rank_bm25 import BM25Okapi
import asyncio

class EnhancedRetriever:
    def __init__(self, vectorstores, top_k=5):
        self.vectorstores = vectorstores
        self.top_k = top_k

    async def get_relevant_documents(self, query):
        results = []
        for vectorstore in self.vectorstores:
            retriever = vectorstore.as_retriever()
            results.extend(await asyncio.to_thread(retriever.invoke, query))

        return self.filter_and_rank_bm25(results, query)[:self.top_k]

    def filter_and_rank_bm25(self, documents, query):
        tokenized_texts = [doc.page_content.split() for doc in documents]
        bm25 = BM25Okapi(tokenized_texts)
        scores = bm25.get_scores(query.split())
        ranked_indices = np.argsort(scores)[::-1]
        return [documents[idx] for idx in ranked_indices]
