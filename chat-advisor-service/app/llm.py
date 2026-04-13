import os
import requests


def chat_completion(messages: list[dict], temperature: float = 0.2) -> dict:
    """
    OpenAI-compatible chat.completions call.
    Env:
      - LLM_BASE_URL
      - LLM_API_KEY
      - CHAT_MODEL
    """
    base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    api_key = os.environ.get("LLM_API_KEY", "")
    model = os.environ.get("CHAT_MODEL", "gpt-4.1-mini")
    if not api_key:
        raise RuntimeError("Missing LLM_API_KEY for chat")

    url = f"{base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "temperature": temperature}
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()

