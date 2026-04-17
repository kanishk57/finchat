import requests
import json
import logging
import re
import os
from typing import Generator, Optional
from config import LLAMA_SERVER_URL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a precise financial analyst.
Answer directly and concisely using the retrieved context as evidence.
Do not output a source list, citation table, repeated document names, or meta commentary.
The app renders citations separately.
If the context is insufficient, say what is missing."""


def generate_answer(prompt: str, max_tokens: int = 1000, temperature: float = 0.1, history: list = None) -> Generator[str, None, None]:
    """
    Yields chunks of the generated answer in real-time.
    Ensures strict alternation of messages for Llama-3/Gemma-style templates.
    Avoids 'system' role which often causes parity issues in Jinja templates.
    """
    raw_messages = []
    
    # 1. Collect and clean history
    if history:
        for msg in history:
            content = msg.get('content', '').strip()
            if not content:
                continue
            # Strip HTML tags
            content = re.sub(r'<[^>]+>', '', content)
            role = 'user' if msg.get('role') == 'user' else 'assistant'
            raw_messages.append({"role": role, "content": content})
            
    # 2. Add current prompt
    raw_messages.append({"role": "user", "content": prompt})
    
    # 3. Consolidate and Alternate
    # Merges consecutive roles and ensures the first message is 'user'
    messages = []
    for msg in raw_messages:
        if not messages:
            if msg["role"] == "assistant":
                # Cannot start with assistant, skip or convert
                continue
            messages.append(msg)
        else:
            if messages[-1]["role"] == msg["role"]:
                messages[-1]["content"] += "\n\n" + msg["content"]
            else:
                messages.append(msg)
                
    # 4. Prepend System Prompt to the first message
    if messages:
        messages[0]["content"] = f"{SYSTEM_PROMPT}\n\n{messages[0]['content']}"
    
    payload: dict = {
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": 0.95,
        "top_k": 40,
        "stream": True
    }

    if os.getenv("FINCHAT_LLM_OFFLINE") == "1":
        yield "FinChat is running in offline mode because the LLM server is not available. Start llama-server on port 8080 to enable chat generation."
        return

    try:
        logger.info(f"Sending request to LLAMA_SERVER_URL: {LLAMA_SERVER_URL}")
        response = requests.post(LLAMA_SERVER_URL, json=payload, timeout=300, stream=True)

        if response.status_code != 200:
            error_body = response.text[:1000]
            logger.warning(f"V1 API failed with status {response.status_code}. Response: {error_body}")
            
            # Fallback to non-streaming completion if v1 fails
            OLD_URL: str = "http://127.0.0.1:8080/completion"
            logger.info(f"Trying fallback to OLD_URL: {OLD_URL}")
            
            # For fallback, construct a single string prompt
            full_prompt = ""
            for m in messages:
                role_label = "user" if m["role"] == "user" else "model"
                full_prompt += f"<start_of_turn>{role_label}\n{m['content']}<end_of_turn>\n"
            full_prompt += "<start_of_turn>model\n"
            
            payload_old: dict = {
                "prompt": full_prompt,
                "n_predict": max_tokens,
                "temperature": temperature,
                "stream": True
            }
            response_old = requests.post(OLD_URL, json=payload_old, timeout=300, stream=True)

            if response_old.status_code != 200:
                logger.error(f"Both API versions failed. Fallback status: {response_old.status_code}")
                yield f"Error: LLM server (v1) returned {response.status_code}.\n"
                yield f"Message: {error_body}\n\n"
                yield "Advice: The model server is rejecting the message sequence. Prepending the system prompt to the user message usually fixes this."
                return

            for line in response_old.iter_lines():
                if line:
                    decoded_line: str = line.decode('utf-8')
                    if decoded_line.startswith("data: "):
                        try:
                            data: dict = json.loads(decoded_line[6:])
                            yield data.get("content", "")
                        except:
                            continue
            return

        for line in response.iter_lines():
            if line:
                decoded_line: str = line.decode('utf-8')
                if decoded_line.startswith("data: "):
                    data_str: str = decoded_line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data: dict = json.loads(data_str)
                        chunk: str = data['choices'][0]['delta'].get('content', '')
                        if chunk:
                            yield chunk
                    except Exception as e:
                        logger.error(f"Error parsing streaming JSON: {e}")
                        continue
    except requests.exceptions.ConnectionError:
        msg = f"Error: Could not connect to LLM server at {LLAMA_SERVER_URL}. Is it running?"
        logger.error(msg)
        yield msg
    except Exception as e:
        logger.exception(f"Exception in generate_answer: {e}")
        yield f"Error: {str(e)}"
