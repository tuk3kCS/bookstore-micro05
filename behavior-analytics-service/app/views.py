from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import BehaviorEvent
from .serializers import BehaviorEventSerializer
from .ml_artifacts import load_model
from .ml_train import train_model_behavior
from .ml_dataset import PAD, UNK
from .segment import segment_from_counts

import torch


class EventIngest(APIView):
    """
    POST /events/
    Body example:
      {
        "customer_id": 1,
        "session_id": "sess_...",
        "correlation_id": "corr_...",
        "event_type": "view_item|search|add_to_cart|checkout_start|checkout_complete|review_submit|login|register",
        "page": "/books/1/",
        "referrer": "/books/",
        "item_type": "book|clothes",
        "item_id": 1,
        "metadata": {"q": "python", "quantity": 2}
      }
    """

    def post(self, request):
        serializer = BehaviorEventSerializer(data=request.data)
        if serializer.is_valid():
            obj = serializer.save()
            return Response({"id": obj.id}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def _segment_from_counts(counts: dict) -> str:
    # Backward compatible wrapper (older code path).
    return segment_from_counts(counts)


class CustomerProfile(APIView):
    """
    GET /profiles/<customer_id>/?days=30
    Returns aggregated stats + lightweight signals for RAG.
    """

    def get(self, request, customer_id: int):
        try:
            customer_id = int(customer_id)
        except Exception:
            return Response({"error": "Invalid customer_id"}, status=status.HTTP_400_BAD_REQUEST)

        days = request.GET.get("days", "30")
        try:
            days_i = int(days)
            days_i = max(1, min(days_i, 365))
        except Exception:
            days_i = 30

        since = timezone.now() - timedelta(days=days_i)
        qs = BehaviorEvent.objects.filter(customer_id=customer_id, created_at__gte=since)

        counts_qs = qs.values("event_type").annotate(c=Count("id")).order_by()
        counts = {row["event_type"]: int(row["c"]) for row in counts_qs}

        last_events = list(
            qs.order_by("-created_at")
            .values("event_type", "page", "item_type", "item_id", "created_at")[:25]
        )

        top_items = (
            qs.exclude(item_id__isnull=True)
            .exclude(item_type="")
            .values("item_type", "item_id")
            .annotate(c=Count("id"))
            .order_by("-c")[:10]
        )
        top_items = [{"item_type": r["item_type"], "item_id": r["item_id"], "count": int(r["c"])} for r in top_items]

        segment = _segment_from_counts(counts)

        profile = {
            "customer_id": customer_id,
            "window_days": days_i,
            "segment": segment,
            "event_counts": counts,
            "top_items": top_items,
            "recent_events": last_events,
        }
        return Response(profile)


class Health(APIView):
    def get(self, request):
        return Response({"status": "ok"})


class ModelTrain(APIView):
    """
    POST /model/train/
    Trains model_behavior from stored BehaviorEvent data and saves artifacts to MODEL_DIR (/models by default).
    """

    def post(self, request):
        try:
            result = train_model_behavior(device="cpu")
            if "error" in result:
                return Response(result, status=400)
            return Response(result)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class ModelInfer(APIView):
    """
    POST /model/infer/
    Body: { "customer_id": 1, "max_len": 30, "top_k": 5 }
    Returns: embedding + predicted next_event + predicted segment + top next_items.
    """

    def post(self, request):
        customer_id = (request.data or {}).get("customer_id")
        if customer_id is None:
            return Response({"error": "customer_id is required"}, status=400)
        try:
            customer_id = int(customer_id)
        except Exception:
            return Response({"error": "Invalid customer_id"}, status=400)

        max_len = int((request.data or {}).get("max_len", 30) or 30)
        max_len = max(5, min(max_len, 100))
        top_k = int((request.data or {}).get("top_k", 5) or 5)
        top_k = max(1, min(top_k, 10))

        # Load latest events
        evs = list(
            BehaviorEvent.objects.filter(customer_id=customer_id)
            .order_by("-created_at")[:max_len]
        )
        evs.reverse()
        if not evs:
            return Response({"error": "no_events_for_customer"}, status=404)

        try:
            model, vocab = load_model(device="cpu")
        except Exception as e:
            return Response({"error": f"model_not_available: {str(e)}"}, status=503)

        pad_tok = vocab.token_to_id.get(PAD, 0)
        unk_tok = vocab.token_to_id.get(UNK, 1)
        pad_ev = vocab.event_to_id.get(PAD, 0)
        unk_ev = vocab.event_to_id.get(UNK, 1)

        def _item_token(item_type, item_id):
            if not item_type or item_id is None:
                return "none"
            return f"{item_type}:{int(item_id)}"

        tok_seq = [_item_token(e.item_type, e.item_id) for e in evs]
        ev_seq = [e.event_type or "unknown" for e in evs]

        tok_ids = [vocab.token_to_id.get(t, unk_tok) for t in tok_seq[-max_len:]]
        ev_ids = [vocab.event_to_id.get(t, unk_ev) for t in ev_seq[-max_len:]]
        length = len(tok_ids)
        if length < max_len:
            tok_ids = [pad_tok] * (max_len - length) + tok_ids
            ev_ids = [pad_ev] * (max_len - length) + ev_ids

        with torch.no_grad():
            out = model(
                torch.tensor([tok_ids], dtype=torch.long),
                torch.tensor([ev_ids], dtype=torch.long),
                torch.tensor([max(1, length)], dtype=torch.long),
            )

            next_event_id = int(torch.argmax(out.next_event_logits, dim=-1).item())
            seg_id = int(torch.argmax(out.segment_logits, dim=-1).item())

            next_event = vocab.id_to_event.get(next_event_id, "unknown")
            segment = vocab.id_to_segment.get(seg_id, "new_or_unknown")

            probs = torch.softmax(out.next_item_logits, dim=-1)[0]
            top = torch.topk(probs, k=min(top_k, probs.shape[0]))
            items = []
            id_to_token = vocab.id_to_token
            for pid, p in zip(top.indices.tolist(), top.values.tolist()):
                token = id_to_token.get(int(pid), "none")
                if token in (PAD, UNK, "none"):
                    continue
                if ":" in token:
                    t, iid = token.split(":", 1)
                    try:
                        iid_i = int(iid)
                    except Exception:
                        iid_i = None
                else:
                    t, iid_i = token, None
                items.append({"item_type": t, "item_id": iid_i, "score": float(p)})

            emb = out.embedding[0].tolist()

        return Response(
            {
                "customer_id": customer_id,
                "predicted": {
                    "segment": segment,
                    "next_event_type": next_event,
                    "next_items": items,
                },
                "embedding": emb,
            }
        )

