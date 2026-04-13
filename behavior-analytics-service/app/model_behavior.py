from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn


@dataclass
class BehaviorModelOutput:
    embedding: torch.Tensor  # [B, D]
    next_event_logits: torch.Tensor  # [B, E]
    next_item_logits: torch.Tensor  # [B, I]
    segment_logits: torch.Tensor  # [B, S]


class ModelBehavior(nn.Module):
    """
    Minimal sequence model for:
    - next_event_type (intent/action)
    - next_item (generalized item token)
    - segment (supervised from heuristic label during cold start; replace later)
    - customer/session embedding (last hidden state)
    """

    def __init__(
        self,
        token_vocab_size: int,
        event_vocab_size: int,
        segment_vocab_size: int,
        d_model: int = 64,
        hidden: int = 128,
        num_layers: int = 1,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.token_emb = nn.Embedding(token_vocab_size, d_model)
        self.event_emb = nn.Embedding(event_vocab_size, d_model)
        self.rnn = nn.GRU(
            input_size=d_model * 2,
            hidden_size=hidden,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.proj = nn.Sequential(
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        self.next_event_head = nn.Linear(hidden, event_vocab_size)
        self.next_item_head = nn.Linear(hidden, token_vocab_size)
        self.segment_head = nn.Linear(hidden, segment_vocab_size)

    def forward(
        self,
        token_ids: torch.Tensor,  # [B, T]
        event_ids: torch.Tensor,  # [B, T]
        lengths: torch.Tensor,  # [B]
    ) -> BehaviorModelOutput:
        tok = self.token_emb(token_ids)
        ev = self.event_emb(event_ids)
        x = torch.cat([tok, ev], dim=-1)

        # Pack for variable lengths.
        packed = nn.utils.rnn.pack_padded_sequence(
            x, lengths.cpu(), batch_first=True, enforce_sorted=False
        )
        _, h = self.rnn(packed)  # h: [L, B, H]
        h_last = h[-1]  # [B, H]

        z = self.proj(h_last)
        return BehaviorModelOutput(
            embedding=z,
            next_event_logits=self.next_event_head(z),
            next_item_logits=self.next_item_head(z),
            segment_logits=self.segment_head(z),
        )

