import os
import requests


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    OpenAI-compatible embeddings call.
    Requires env:
      - LLM_BASE_URL (default https://api.openai.com/v1)
      - LLM_API_KEY
      - EMBEDDING_MODEL
    """
    base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    api_key = os.environ.get("LLM_API_KEY", "")
    model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")

    if not api_key:
        raise RuntimeError("Missing LLM_API_KEY for embeddings")

    url = f"{base_url}/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"model": model, "input": texts}
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    return [row["embedding"] for row in data["data"]]

