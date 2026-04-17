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
    grouped_results: List[Dict[str, Any]] = []
    grouped_by_key: Dict[Any, Dict[str, Any]] = {}

    for item in results:
        key = (item.get('doc_name'), item.get('page_number'))
        text = (item.get('text') or '').strip()
        if key not in grouped_by_key:
            group = {
                'doc_name': item.get('doc_name'),
                'page_number': item.get('page_number'),
                'snippets': []
            }
            grouped_by_key[key] = group
            grouped_results.append(group)

        if text:
            group = grouped_by_key[key]
            if text not in group['snippets']:
                group['snippets'].append(text)

    for i, item in enumerate(grouped_results, 1):
        snippets = item['snippets'] or ['No excerpt available.']
        combined_snippets = "\n".join(f"- {snippet}" for snippet in snippets)
        block: str = (
            f"[Source {i}] "
            f"Document: {item['doc_name']} | "
            f"Page: {item['page_number']}\n"
            f"{combined_snippets}"
        )
        context_blocks.append(block)

    return "\n\n".join(context_blocks)
