from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json
import asyncio
import os

from main import initialize_system, build_prompt, INITIAL_K, FINAL_TOP_K
from embeddings.embedder import embed_query, rerank_results

app = FastAPI(title="FinChat API")

@app.middleware("http")
async def add_no_cache_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Ensure static directory exists
os.makedirs("app/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Mount the PDF directory so they can be viewed in the browser
os.makedirs("data/pdfs", exist_ok=True)
app.mount("/pdfs", StaticFiles(directory="data/pdfs"), name="pdfs")

vector_store = None

@app.on_event("startup")
async def startup_event():
    global vector_store
    print("Initializing system for API...")
    loop = asyncio.get_event_loop()
    # Execute the heavy initialization in a threadpool to not block asyncio
    vector_store, num_files, num_chunks = await loop.run_in_executor(None, initialize_system)
    print(f"System initialized! Loaded {num_files} files with {num_chunks} chunks.")

class ChatRequest(BaseModel):
    query: str

@app.get("/")
async def get_root():
    return FileResponse("app/static/index.html")

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    query = request.query
    
    query_embedding = embed_query(query)
    initial_results = vector_store.search_hybrid(query, query_embedding, k=INITIAL_K)
    
    if not initial_results:
        async def mock_stream():
            yield "data: " + json.dumps({"type": "chunk", "content": "The provided documents do not contain information regarding this query."}) + "\n\n"
        return StreamingResponse(mock_stream(), media_type="text/event-stream")

    final_results = rerank_results(query, initial_results, top_n=FINAL_TOP_K)
    prompt = build_prompt(query, final_results)

    # Format citations for the frontend
    citations = []
    for i, res in enumerate(final_results, 1):
        citations.append({
            "ref": i,
            "doc_name": res['doc_name'],
            "page": res['page_number'],
            "relevance": round(res.get('rerank_score', 0), 4)
        })

    def generate():
        # 1. Send citations immediately
        yield f"data: {json.dumps({'type': 'citations', 'citations': citations})}\n\n"
        
        # 2. Stream generation from generator.py
        from llm.generator import generate_answer
        for chunk in generate_answer(prompt):
            if chunk:
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
        
        # 3. Send done signal
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
