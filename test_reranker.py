from models.model_manager import get_reranker_model
import numpy as np

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

reranker = get_reranker_model()
query = "what are the documents about"
passages = [
    "This is a 10-K report for NVIDIA Corporation for the fiscal year ended January 28, 2024.",
    "The 2023 Annual Report provides a comprehensive overview of our financial performance.",
    "This sample document contains some random text about financial analysis.",
    "Apples are red and bananas are yellow."
]

pairs = [[query, p] for p in passages]
scores = reranker.predict(pairs)

print(f"Query: {query}")
for i, score in enumerate(scores):
    print(f"Passage: {passages[i][:50]}...")
    print(f"  Raw Score: {score:.4f}")
    print(f"  Sigmoid Score: {sigmoid(score):.4f}")
