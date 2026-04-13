from __future__ import annotations

import time

import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from .ml_artifacts import Vocab, save_model, save_vocab
from .ml_dataset import make_training_examples
from .model_behavior import ModelBehavior


def train_model_behavior(
    max_len: int = 30,
    batch_size: int = 64,
    epochs: int = 3,
    lr: float = 2e-3,
    d_model: int = 64,
    hidden: int = 128,
    num_layers: int = 1,
    dropout: float = 0.1,
    device: str = "cpu",
) -> dict:
    data = make_training_examples(max_len=max_len)
    if "error" in data:
        return data

    token_to_id = data["token_to_id"]
    event_to_id = data["event_to_id"]
    segment_to_id = data["segment_to_id"]

    v = Vocab(token_to_id=token_to_id, event_to_id=event_to_id, segment_to_id=segment_to_id)

    x_tok = data["x_token"]
    x_ev = data["x_event"]
    x_len = data["x_len"]
    y_ev = data["y_next_event"]
    y_item = data["y_next_item"]
    y_seg = data["y_segment"]

    ds = TensorDataset(x_tok, x_ev, x_len, y_ev, y_item, y_seg)
    dl = DataLoader(ds, batch_size=batch_size, shuffle=True)

    model = ModelBehavior(
        token_vocab_size=len(token_to_id),
        event_vocab_size=len(event_to_id),
        segment_vocab_size=len(segment_to_id),
        d_model=d_model,
        hidden=hidden,
        num_layers=num_layers,
        dropout=dropout,
    ).to(device)

    ce = nn.CrossEntropyLoss()
    opt = torch.optim.AdamW(model.parameters(), lr=lr)

    t0 = time.time()
    model.train()
    for _ in range(epochs):
        for btok, bev, blen, y1, y2, y3 in dl:
            btok = btok.to(device)
            bev = bev.to(device)
            blen = blen.to(device)
            y1 = y1.to(device)
            y2 = y2.to(device)
            y3 = y3.to(device)

            out = model(btok, bev, blen)
            loss = ce(out.next_event_logits, y1) + ce(out.next_item_logits, y2) + 0.5 * ce(out.segment_logits, y3)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()

    cfg = {
        "token_vocab_size": len(token_to_id),
        "event_vocab_size": len(event_to_id),
        "segment_vocab_size": len(segment_to_id),
        "d_model": d_model,
        "hidden": hidden,
        "num_layers": num_layers,
        "dropout": dropout,
        "max_len": max_len,
    }
    save_vocab(v)
    save_model(model, cfg)

    return {
        "status": "trained",
        "examples": int(x_tok.shape[0]),
        "token_vocab": len(token_to_id),
        "event_vocab": len(event_to_id),
        "segment_vocab": len(segment_to_id),
        "elapsed_s": round(time.time() - t0, 3),
        "config": cfg,
    }

