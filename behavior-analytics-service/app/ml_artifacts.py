from __future__ import annotations

import json
import os
from dataclasses import dataclass

import torch

from .model_behavior import ModelBehavior


@dataclass
class Vocab:
    token_to_id: dict[str, int]
    event_to_id: dict[str, int]
    segment_to_id: dict[str, int]

    @property
    def id_to_token(self) -> dict[int, str]:
        return {v: k for k, v in self.token_to_id.items()}

    @property
    def id_to_event(self) -> dict[int, str]:
        return {v: k for k, v in self.event_to_id.items()}

    @property
    def id_to_segment(self) -> dict[int, str]:
        return {v: k for k, v in self.segment_to_id.items()}


def artifacts_dir() -> str:
    return os.environ.get("MODEL_DIR", "/models")


def vocab_path() -> str:
    return os.path.join(artifacts_dir(), "model_behavior.vocab.json")


def model_path() -> str:
    return os.path.join(artifacts_dir(), "model_behavior.pt")


def load_vocab() -> Vocab:
    with open(vocab_path(), "r", encoding="utf-8") as f:
        raw = json.load(f)
    return Vocab(
        token_to_id=raw["token_to_id"],
        event_to_id=raw["event_to_id"],
        segment_to_id=raw["segment_to_id"],
    )


def save_vocab(v: Vocab):
    os.makedirs(artifacts_dir(), exist_ok=True)
    raw = {
        "token_to_id": v.token_to_id,
        "event_to_id": v.event_to_id,
        "segment_to_id": v.segment_to_id,
    }
    with open(vocab_path(), "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)


def load_model(device: str = "cpu") -> tuple[ModelBehavior, Vocab]:
    v = load_vocab()
    ckpt = torch.load(model_path(), map_location=device)
    cfg = ckpt["config"]
    m = ModelBehavior(
        token_vocab_size=cfg["token_vocab_size"],
        event_vocab_size=cfg["event_vocab_size"],
        segment_vocab_size=cfg["segment_vocab_size"],
        d_model=cfg["d_model"],
        hidden=cfg["hidden"],
        num_layers=cfg["num_layers"],
        dropout=cfg["dropout"],
    )
    m.load_state_dict(ckpt["state_dict"])
    m.eval()
    return m, v


def save_model(m: ModelBehavior, cfg: dict):
    os.makedirs(artifacts_dir(), exist_ok=True)
    torch.save(
        {"state_dict": m.state_dict(), "config": cfg},
        model_path(),
    )

