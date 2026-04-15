from typing import List, Dict, Any

def build_context(results: List[Dict[str, Any]]) -> str:
    """
    Build context string from search results for LLM prompt.
    
    Args:
        results: List of search result dictionaries
        
    Returns:
        Formatted context string
    """
    context_blocks: List[str] = []

    for i, item in enumerate(results, 1):
        block: str = (
            f"[Source {i}] "
            f"Document: {item['doc_name']}, "
            f"Page: {item['page_number']}\n"
            f"{item['text']}\n"
        )
        context_blocks.append(block)

    return "\n\n".join(context_blocks)