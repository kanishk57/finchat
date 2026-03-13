import os
import sys
import time
import glob
from ingestion.pdf_parser import extract_pdf_pages
from embeddings.embedder import embed_passages, embed_query, rerank_results, load_models
from vector_store.faiss_index import VectorStore
from llm.context_builder import build_context
from llm.generator import generate_answer

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.live import Live
from rich.text import Text
from rich.rule import Rule

console = Console()

# ----------------------------
# CONFIG
# ----------------------------
PDF_DIR = "data/pdfs/"
INITIAL_K = 10
FINAL_TOP_K = 3
THRESHOLD = 0.3
INDEX_PATH = "faiss.index"
METADATA_PATH = "metadata.pkl"

def build_prompt(query, retrieved_results):
    context = build_context(retrieved_results)
    return f"""
### INSTRUCTIONS
You are a highly precise Financial Analysis Assistant. 
Your goal is to provide a structured, factual answer based ONLY on the provided context.

### CONSTRAINTS
- Cite every claim using [Source X] format at the end of the sentence.
- If multiple documents provide conflicting data, highlight the discrepancy.
- If the information is not present, respond: "The provided documents do not contain information regarding [X]."
- Keep the tone professional and editorial.

### CONTEXT
{context}

### USER QUERY
{query}

### ANALYSIS AND RESPONSE
"""

def initialize_system():
    # Use a single status context for the whole startup to prevent flickering
    with console.status("[bold green]Starting FinChat Engine...", spinner="aesthetic") as status:
        
        # 1. Weights Loading
        status.update("[bold green]Loading AI models & weights (BGE-Base)...")
        load_models()
        
        # 2. Document Discovery
        status.update("[bold blue]Scanning data directory...")
        pdf_files = glob.glob(os.path.join(PDF_DIR, "*.pdf"))
        if not pdf_files:
            console.print(f"[bold red]Error:[/bold red] No PDFs found in {PDF_DIR}")
            sys.exit(1)

        # 3. Indexing Logic
        vector_store = None
        FORCE_REBUILD = False
        pages = []
        num_chunks = 0

        if os.path.exists(INDEX_PATH) and os.path.exists(METADATA_PATH):
            vector_store = VectorStore(768) 
            if vector_store.load(INDEX_PATH, METADATA_PATH):
                indexed_docs = {m["doc_name"] for m in vector_store.metadata}
                current_docs = {os.path.basename(f) for f in pdf_files}
                if indexed_docs != current_docs:
                    status.update("[bold yellow]Change detected. Rebuilding index...")
                    FORCE_REBUILD = True
                else:
                    status.update("[bold green]Found existing index. Skipping rebuild...")
                    num_chunks = len(vector_store.metadata)
            else:
                FORCE_REBUILD = True
        else:
            FORCE_REBUILD = True

        if FORCE_REBUILD:
            status.update(f"[bold blue]Analyzing {len(pdf_files)} documents...")
            pages = extract_pdf_pages(pdf_files, chunk_size=1000, overlap=200)
            num_chunks = len(pages)
            
            status.update("[bold cyan]Generating embeddings (this may take a minute)...")
            texts = [page["text"] for page in pages]
            
            # Use batching logic configured in embedder.py
            embeddings = embed_passages(texts)
            
            vector_store = VectorStore(len(embeddings[0]))
            vector_store.add(embeddings, pages)
            vector_store.save(INDEX_PATH, METADATA_PATH)
            
    return vector_store, len(pdf_files), num_chunks

def main():
    # Show initial banner briefly
    console.print(Rule(style="bold blue"))
    console.print("[bold cyan]FinChat System Initialization[/bold cyan]", justify="center")
    console.print(Rule(style="bold blue"))

    vector_store, num_files, num_chunks = initialize_system()
    
    # Final clear before starting chat
    console.clear()
    
    console.print(Panel.fit(
        f"Welcome to [bold cyan]FinChat[/bold cyan]\n"
        f"[dim]Engine Ready | {num_files} files | {num_chunks} chunks[/dim]\n"
        f"Type [bold red]'exit'[/bold red] to quit.", 
        border_style="blue",
        title="[bold]System Status[/bold]"
    ))

    # 2. RAG Loop
    while True:
        try:
            query = console.input("\n[bold yellow]Query[/bold yellow] > ").strip()
        except EOFError:
            break
            
        if not query:
            continue
        if query.lower() == "exit":
            break

        with console.status("[cyan]Retrieving information...", spinner="bouncingBall"):
            query_embedding = embed_query(query)
            initial_results = vector_store.search_hybrid(query, query_embedding, k=INITIAL_K)
            
            if not initial_results:
                console.print("[bold red]No relevant information found in documents.[/bold red]")
                continue

            final_results = rerank_results(query, initial_results, top_n=FINAL_TOP_K)
        
        # Display Sources Table
        table = Table(title="Top Referenced Sources", title_style="bold magenta", border_style="dim")
        table.add_column("Ref", justify="center", style="cyan")
        table.add_column("Document Source", style="white")
        table.add_column("Page", justify="center", style="yellow")
        table.add_column("Relevance", justify="right", style="green")

        for i, res in enumerate(final_results, 1):
            table.add_row(
                str(i), 
                res['doc_name'], 
                str(res['page_number']), 
                f"{res.get('rerank_score', 0):.4f}"
            )
        
        console.print(table)

        prompt = build_prompt(query, final_results)

        console.print(f"\n[bold green]FinChat Assistant:[/bold green]")
        
        # Streaming Output
        full_response = ""
        with Live(Text(""), refresh_per_second=10) as live:
            for chunk in generate_answer(prompt):
                full_response += chunk
                live.update(Text(full_response, style="italic white"))
        
        console.print(Rule(style="dim"))

if __name__ == "__main__":
    main()
