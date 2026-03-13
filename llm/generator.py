import requests
import json

LLAMA_SERVER_URL = "http://localhost:8080/v1/chat/completions"


def generate_answer(prompt, max_tokens=1000):
    """
    Yields chunks of the generated answer in real-time.
    """
    payload = {
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful financial analysis assistant. Respond based ONLY on the provided context."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": max_tokens,
        "temperature": 0.1,
        "top_p": 0.95,
        "stream": True  # Enable streaming
    }

    try:
        response = requests.post(LLAMA_SERVER_URL, json=payload, timeout=300, stream=True)
        
        if response.status_code != 200:
            # Fallback to non-streaming completion if v1 fails
            OLD_URL = "http://localhost:8080/completion"
            payload_old = {
                "prompt": f"<start_of_turn>user\n{prompt}<end_of_turn>\n<start_of_turn>model\n",
                "n_predict": max_tokens,
                "temperature": 0.1,
                "stream": True
            }
            response = requests.post(OLD_URL, json=payload_old, timeout=300, stream=True)
            
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("data: "):
                        try:
                            data = json.loads(decoded_line[6:])
                            yield data.get("content", "")
                        except:
                            continue
            return

        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data: "):
                    data_str = decoded_line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        chunk = data['choices'][0]['delta'].get('content', '')
                        if chunk:
                            yield chunk
                    except:
                        continue
    except Exception as e:
        yield f"Error: {str(e)}"