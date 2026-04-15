from models.model_manager import get_reranker_model
import numpy as np

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

reranker = get_reranker_model()
query = "NVIDIA inventory trends"
passages = [
    "NVIDIA Corporation inventory increased by 20% in Q3 due to supply chain build-up.",
    "The 2023 Annual Report provides a comprehensive overview of our financial performance.",
    "Apples are red and bananas are yellow."
]

pairs = [[query, p] for p in passages]
scores = reranker.predict(pairs)

print(f"Query: {query}")
for i, score in enumerate(scores):
    print(f"Passage: {passages[i][:50]}...")
    print(f"  Raw Score: {score:.4f}")
    print(f"  Sigmoid Score: {sigmoid(score):.4f}")
