from __future__ import annotations

from collections import defaultdict

import torch

from .models import BehaviorEvent
from .segment import segment_from_counts


PAD = "<pad>"
UNK = "<unk>"


def _item_token(item_type: str, item_id: int | None) -> str:
    if not item_type or item_id is None:
        return "none"
    return f"{item_type}:{int(item_id)}"


def build_vocabs(events: list[BehaviorEvent]) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    token_set = {PAD, UNK, "none"}
    event_set = {PAD, UNK}

    for e in events:
        token_set.add(_item_token(e.item_type, e.item_id))
        event_set.add(e.event_type or "unknown")

    segment_set = {
        "returning_buyer",
        "new_buyer",
        "high_intent_browser",
        "researcher",
        "browser",
        "new_or_unknown",
    }

    token_to_id = {t: i for i, t in enumerate(sorted(token_set))}
    event_to_id = {t: i for i, t in enumerate(sorted(event_set))}
    segment_to_id = {t: i for i, t in enumerate(sorted(segment_set))}
    return token_to_id, event_to_id, segment_to_id


def _encode(seq: list[str], vocab: dict[str, int], max_len: int) -> tuple[list[int], int]:
    ids = [vocab.get(s, vocab.get(UNK, 1)) for s in seq[-max_len:]]
    length = len(ids)
    pad_id = vocab.get(PAD, 0)
    if length < max_len:
        ids = [pad_id] * (max_len - length) + ids
    return ids, length


def make_training_examples(
    max_len: int = 30,
    min_seq: int = 3,
    per_customer_max_examples: int = 200,
) -> dict:
    """
    Builds training samples from BehaviorEvent table.
    Labels:
      - next_event_id (intent/action)
      - next_item_token_id (generalized item token)
      - segment_id (heuristic label for cold-start supervision)
    """
    qs = BehaviorEvent.objects.exclude(customer_id__isnull=True).order_by("customer_id", "created_at")
    events = list(qs)
    if not events:
        return {"error": "no_events"}

    token_to_id, event_to_id, segment_to_id = build_vocabs(events)

    by_customer: dict[int, list[BehaviorEvent]] = defaultdict(list)
    for e in events:
        if e.customer_id is not None:
            by_customer[int(e.customer_id)].append(e)

    xs_token: list[list[int]] = []
    xs_event: list[list[int]] = []
    xs_len: list[int] = []
    ys_next_event: list[int] = []
    ys_next_item: list[int] = []
    ys_segment: list[int] = []

    for cid, seq in by_customer.items():
        if len(seq) < min_seq:
            continue

        # segment label based on counts in this customer's full history
        counts: dict[str, int] = defaultdict(int)
        for e in seq:
            counts[e.event_type] += 1
        segment = segment_from_counts(dict(counts))
        seg_id = segment_to_id.get(segment, 0)

        examples = 0
        # Next-step prediction: use prefix up to t-1 to predict t
        for t in range(1, len(seq)):
            prefix = seq[:t]
            target = seq[t]
            tok_seq = [_item_token(e.item_type, e.item_id) for e in prefix]
            ev_seq = [e.event_type or "unknown" for e in prefix]

            x_tok, L = _encode(tok_seq, token_to_id, max_len=max_len)
            x_ev, _ = _encode(ev_seq, event_to_id, max_len=max_len)

            ys_next_event.append(event_to_id.get(target.event_type or "unknown", event_to_id.get(UNK, 1)))
            ys_next_item.append(token_to_id.get(_item_token(target.item_type, target.item_id), token_to_id.get(UNK, 1)))
            ys_segment.append(seg_id)

            xs_token.append(x_tok)
            xs_event.append(x_ev)
            xs_len.append(max(1, L))

            examples += 1
            if examples >= per_customer_max_examples:
                break

    return {
        "token_to_id": token_to_id,
        "event_to_id": event_to_id,
        "segment_to_id": segment_to_id,
        "x_token": torch.tensor(xs_token, dtype=torch.long),
        "x_event": torch.tensor(xs_event, dtype=torch.long),
        "x_len": torch.tensor(xs_len, dtype=torch.long),
        "y_next_event": torch.tensor(ys_next_event, dtype=torch.long),
        "y_next_item": torch.tensor(ys_next_item, dtype=torch.long),
        "y_segment": torch.tensor(ys_segment, dtype=torch.long),
    }

