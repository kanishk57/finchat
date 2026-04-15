from core.initialization import initialize_system, build_prompt
from embeddings.embedder import embed_query, rerank_results
from llm.generator import generate_answer
from config import INITIAL_K, FINAL_TOP_K

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.live import Live
from rich.text import Text
from rich.rule import Rule

console = Console()

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
