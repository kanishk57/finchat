def build_context(results):
    context_blocks = []

    for i, item in enumerate(results, 1):
        block = (
            f"[Source {i}] "
            f"Document: {item['doc_name']}, "
            f"Page: {item['page_number']}\n"
            f"{item['text']}\n"
        )
        context_blocks.append(block)

    return "\n\n".join(context_blocks)