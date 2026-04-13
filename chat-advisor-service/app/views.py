import os
import requests

from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .llm import chat_completion


def _safe_json(r):
    try:
        return r.json()
    except Exception:
        return None


class Health(APIView):
    def get(self, request):
        return Response({"status": "ok"})


class AdvisorChat(APIView):
    """
    POST /advisor/chat/
    Body:
      {
        "customer_id": 1,
        "message": "..."
      }
    Returns:
      {
        "answer": "...",
        "citations": [{doc_path,title,heading,chunk_id,score}],
        "profile": {...}
      }
    """

    def post(self, request):
        customer_id = (request.data or {}).get("customer_id")
        message = ((request.data or {}).get("message") or "").strip()
        if not message:
            return Response({"error": "message is required"}, status=status.HTTP_400_BAD_REQUEST)

        behavior_url = os.environ.get(
            "BEHAVIOR_SERVICE_URL", getattr(settings, "BEHAVIOR_SERVICE_URL", "http://behavior-analytics-service:8000")
        ).rstrip("/")
        kb_url = os.environ.get(
            "KB_RAG_SERVICE_URL", getattr(settings, "KB_RAG_SERVICE_URL", "http://kb-rag-service:8000")
        ).rstrip("/")

        profile = None
        if customer_id is not None:
            try:
                r = requests.get(f"{behavior_url}/profiles/{int(customer_id)}/?days=30", timeout=5)
                if r.status_code == 200:
                    profile = _safe_json(r)
            except Exception:
                profile = None

        kb_results = []
        try:
            r = requests.post(f"{kb_url}/kb/retrieve/", json={"query": message, "top_k": 6}, timeout=30)
            if r.status_code == 200:
                kb_results = (_safe_json(r) or {}).get("results", []) or []
        except Exception:
            kb_results = []

        citations = [
            {
                "doc_path": k.get("doc_path", ""),
                "title": k.get("title", ""),
                "heading": k.get("heading", ""),
                "chunk_id": k.get("chunk_id", ""),
                "score": k.get("score", 0),
            }
            for k in kb_results[:6]
        ]

        context_blocks = []
        for i, k in enumerate(kb_results[:6], start=1):
            context_blocks.append(
                f"[{i}] title={k.get('title','')}\npath={k.get('doc_path','')}\nheading={k.get('heading','')}\ncontent:\n{k.get('text','')}"
            )
        kb_context = "\n\n".join(context_blocks)

        system = (
            "You are a customer advisor for an online bookstore & clothes shop. "
            "Use the provided Knowledge Base context as the primary source of truth for policies and FAQs. "
            "If the KB does not contain the answer, say what is missing and ask a clarifying question. "
            "When referencing KB facts, cite them with bracket numbers like [1], [2]. "
            "Be concise, action-oriented, and avoid requesting sensitive data."
        )

        profile_text = ""
        if profile:
            profile_text = (
                f"CustomerProfile:\nsegment={profile.get('segment')}\n"
                f"event_counts={profile.get('event_counts')}\n"
                f"top_items={profile.get('top_items')}\n"
            )

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"{profile_text}\n\nKnowledgeBase:\n{kb_context}\n\nUserMessage:\n{message}"},
        ]

        try:
            out = chat_completion(messages)
            answer = out["choices"][0]["message"]["content"]
        except Exception as e:
            return Response({"error": f"LLM error: {str(e)}", "citations": citations, "profile": profile}, status=500)

        return Response({"answer": answer, "citations": citations, "profile": profile})

