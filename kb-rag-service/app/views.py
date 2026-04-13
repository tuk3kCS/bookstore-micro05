import os

from django.conf import settings
from qdrant_client import QdrantClient
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .embeddings import embed_texts
from .ingest import ingest_kb_dir
from .models import KBChunk
from .qdrant_index import search


class Health(APIView):
    def get(self, request):
        return Response({"status": "ok"})


class IngestKB(APIView):
    """
    POST /kb/ingest/
    Ingests markdown files from KB_SOURCE_DIR (mounted volume).
    Requires LLM_API_KEY to compute embeddings.
    """

    def post(self, request):
        source_dir = os.environ.get("KB_SOURCE_DIR", getattr(settings, "KB_SOURCE_DIR", "/kb"))
        qdrant_url = os.environ.get("QDRANT_URL", getattr(settings, "QDRANT_URL", "http://qdrant:6333"))
        collection = os.environ.get("QDRANT_COLLECTION", getattr(settings, "QDRANT_COLLECTION", "kb_chunks"))
        try:
            summary = ingest_kb_dir(source_dir, qdrant_url=qdrant_url, collection=collection)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(summary)


class RetrieveKB(APIView):
    """
    POST /kb/retrieve/
    Body: { "query": "...", "top_k": 5 }
    Returns: [{chunk_id, score, doc_path, title, heading, text, tags, updated_at}]
    """

    def post(self, request):
        query = (request.data or {}).get("query", "") or ""
        top_k = int((request.data or {}).get("top_k", 5) or 5)
        top_k = max(1, min(top_k, 20))

        if not query.strip():
            return Response({"error": "query is required"}, status=status.HTTP_400_BAD_REQUEST)

        qdrant_url = os.environ.get("QDRANT_URL", getattr(settings, "QDRANT_URL", "http://qdrant:6333"))
        collection = os.environ.get("QDRANT_COLLECTION", getattr(settings, "QDRANT_COLLECTION", "kb_chunks"))

        try:
            qvec = embed_texts([query])[0]
            client = QdrantClient(url=qdrant_url)
            resp = search(client, collection, qvec, limit=top_k)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # qdrant-client query_points returns an object with `.points`
        hits = getattr(resp, "points", resp) or []

        chunk_ids = []
        scored = []
        for h in hits:
            payload = h.payload or {}
            cid = payload.get("chunk_id") or str(h.id)
            chunk_ids.append(cid)
            scored.append((cid, float(h.score), payload))

        chunks = {str(c.id): c for c in KBChunk.objects.filter(id__in=chunk_ids)}

        results = []
        for cid, score, payload in scored:
            ch = chunks.get(cid)
            if not ch:
                continue
            results.append(
                {
                    "chunk_id": cid,
                    "score": score,
                    "doc_path": payload.get("doc_path", ""),
                    "title": payload.get("title", ""),
                    "heading": payload.get("heading", ""),
                    "tags": payload.get("tags", []),
                    "updated_at": payload.get("updated_at", ""),
                    "text": ch.text,
                }
            )

        return Response({"results": results})

