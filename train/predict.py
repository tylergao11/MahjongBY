# -*- coding: utf-8 -*-
"""Load trained heads and pick a legal action."""
import joblib
import numpy as np

from train.score import legal_rank
from train.tiles import CALL_NAMES, N_CALL, N_TILES, TILE_NAMES, IDX_TO_TILE


def _load(path):
    return joblib.load(path)["model"]


def pick_discard(model, x, hand_mask):
    proba = np.zeros((1, N_TILES), dtype=np.float64)
    raw = model.predict_proba(np.asarray(x, dtype=np.float32).reshape(1, -1))[0]
    for cls, p in zip(model.classes_, raw):
        proba[0, int(cls)] = p
    mask = np.asarray(hand_mask, dtype=np.int8).reshape(1, -1)
    idx = int(legal_rank(proba, mask)[0, 0])
    return idx, TILE_NAMES.get(IDX_TO_TILE[idx], str(idx)), float(proba[0, idx])


def pick_call(model, x, call_mask):
    x = np.asarray(x, dtype=np.float32).reshape(1, -1)
    mask = np.asarray(call_mask, dtype=np.int8).reshape(1, -1)
    if hasattr(model, "predict_scores"):
        proba = model.predict_scores(x, mask)
    else:
        proba = np.zeros((1, N_CALL), dtype=np.float64)
        raw = model.predict_proba(x)[0]
        for cls, p in zip(model.classes_, raw):
            proba[0, int(cls)] = p
    idx = int(legal_rank(proba, mask)[0, 0])
    return idx, CALL_NAMES[idx], float(proba[0, idx])
