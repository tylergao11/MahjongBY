# -*- coding: utf-8 -*-
"""整局模仿评分：出牌跟牌分 + 鸣牌分，合成模仿分。"""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from train.tiles import CALL_NAMES, CALL_PASS, IDX_TO_TILE, N_CALL, N_TILES, TILE_NAMES  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent
DISCARD_PATH = ROOT / "data" / "discard_samples.npz"
CALL_PATH = ROOT / "data" / "call_samples.npz"
DATA_PATH = DISCARD_PATH
MODEL_DIR = ROOT / "models"
METRICS_PATH = MODEL_DIR / "metrics.json"


def split_by_game(gamb_id, seed=7, val_ratio=0.15):
    rng = np.random.RandomState(seed)
    unique = np.unique(gamb_id)
    rng.shuffle(unique)
    n_val = max(1, int(len(unique) * val_ratio))
    val_ids = set(unique[:n_val].tolist())
    val = np.array([gid in val_ids for gid in gamb_id], dtype=bool)
    return ~val, val


def legal_rank(scores, mask):
    masked = np.where(mask > 0, scores, -1.0)
    return np.argsort(-masked, axis=1)


def topk_hit(rank, y, k):
    return (rank[:, :k] == y[:, None]).any(axis=1)


def summarize_hits(rank, y, mask=None):
    n = len(y)
    top1 = topk_hit(rank, y, 1)
    top3 = topk_hit(rank, y, 3)
    out = {
        "n": int(n),
        "top1": float(top1.mean()) if n else 0.0,
        "top3": float(top3.mean()) if n else 0.0,
    }
    out["follow"] = 0.5 * out["top1"] + 0.5 * out["top3"]
    if mask is not None and n:
        legal_n = np.clip(mask.sum(axis=1).astype(np.float64), 1.0, None)
        out["avg_legal"] = float(legal_n.mean())
        out["random_expect_top1"] = float((1.0 / legal_n).mean())
    return out


def score_scores(scores, y, mask):
    return summarize_hits(legal_rank(scores, mask), y, mask)


def expand_proba(proba, classes, n_class):
    full = np.zeros((proba.shape[0], n_class), dtype=np.float64)
    for col, cls in enumerate(classes):
        full[:, int(cls)] = proba[:, col]
    return full


def discard_blob_proba(blob, x):
    kind = blob.get("kind")
    if kind == "mix":
        hgb = blob["model"]["hgb"]
        mlp = blob["model"]["mlp"]
        return (
            expand_proba(hgb.predict_proba(x), hgb.classes_, N_TILES)
            + expand_proba(mlp.predict_proba(x), mlp.classes_, N_TILES)
        ) / 2.0
    if kind == "bag":
        parts = []
        for model in blob["model"]:
            parts.append(expand_proba(model.predict_proba(x), model.classes_, N_TILES))
        return sum(parts) / len(parts)
    model = blob["model"]
    return expand_proba(model.predict_proba(x), model.classes_, N_TILES)


def random_legal_scores(mask, seed=7):
    rng = np.random.RandomState(seed)
    return np.where(mask > 0, rng.random(mask.shape), 0.0)


def majority_legal_scores(y_train, n_class):
    freq = np.bincount(y_train, minlength=n_class).astype(np.float64)
    if freq.max() <= 0:
        freq[:] = 1.0
    return freq


def confusion_names(y_true, y_pred, names, topn=8):
    pairs = defaultdict(int)
    for a, b in zip(y_true.tolist(), y_pred.tolist()):
        if a != b:
            pairs[(a, b)] += 1
    rows = []
    for (a, b), n in sorted(pairs.items(), key=lambda kv: -kv[1])[:topn]:
        rows.append({"true": names[a], "pred": names[b], "n": int(n)})
    return rows


def _names_discard():
    return {i: TILE_NAMES.get(IDX_TO_TILE[i], str(i)) for i in range(N_TILES)}


def score_discard(y_val, mask_val, room_val, y_train, model_scores=None):
    report = {
        "n_val": int(len(y_val)),
        "n_train_labels": int(len(y_train)),
        "baselines": {
            "random_legal": score_scores(random_legal_scores(mask_val), y_val, mask_val),
            "majority_legal": score_scores(
                np.broadcast_to(majority_legal_scores(y_train, N_TILES), mask_val.shape).copy(),
                y_val,
                mask_val,
            ),
        },
    }
    if model_scores is not None:
        model = score_scores(model_scores, y_val, mask_val)
        report["model"] = model
        report["lift_top1_vs_random"] = model["top1"] - report["baselines"]["random_legal"]["top1"]
        pred = legal_rank(model_scores, mask_val)[:, 0]
        report["top_confusions"] = confusion_names(y_val, pred, _names_discard())
        per_room = {}
        for room in sorted(set(room_val.tolist())):
            idx = room_val == room
            if idx.any():
                per_room[str(int(room))] = score_scores(model_scores[idx], y_val[idx], mask_val[idx])
        report["per_room"] = per_room
    return report


def score_call(y_val, mask_val, y_train, model_scores=None):
    always_pass = np.zeros((len(y_val), N_CALL), dtype=np.float64)
    always_pass[:, CALL_PASS] = 1.0
    majority = np.broadcast_to(majority_legal_scores(y_train, N_CALL), (len(y_val), N_CALL)).copy()
    report = {
        "n_val": int(len(y_val)),
        "n_train_labels": int(len(y_train)),
        "baselines": {
            "always_pass": _call_detail(always_pass, y_val, mask_val),
            "majority_legal": _call_detail(majority, y_val, mask_val),
            "random_legal": _call_detail(random_legal_scores(mask_val), y_val, mask_val),
        },
    }
    if model_scores is not None:
        report["model"] = _call_detail(model_scores, y_val, mask_val)
        pred = legal_rank(model_scores, mask_val)[:, 0]
        report["top_confusions"] = confusion_names(y_val, pred, CALL_NAMES)
        report["per_class"] = _per_class(y_val, pred)
    return report


def _call_detail(scores, y, mask):
    base = score_scores(scores, y, mask)
    pred = legal_rank(scores, mask)[:, 0]
    acc = pred == y
    nonpass = y != CALL_PASS
    acted = (y != CALL_PASS)
    base["accuracy"] = float(acc.mean()) if len(y) else 0.0
    base["pass_acc"] = float(acc[~nonpass].mean()) if (~nonpass).any() else 0.0
    base["nonpass_acc"] = float(acc[nonpass].mean()) if nonpass.any() else 0.0
    base["n_pass"] = int((~nonpass).sum())
    base["n_nonpass"] = int(nonpass.sum())
    # 鸣牌分：总体准确 + 真鸣了时有没有跟上，避免「一律过」刷高分
    base["call_score"] = 0.5 * base["accuracy"] + 0.5 * base["nonpass_acc"]
    if acted.any():
        base["acted_recall"] = base["nonpass_acc"]
    return base


def _per_class(y_true, y_pred):
    out = {}
    for i, name in enumerate(CALL_NAMES):
        idx = y_true == i
        if not idx.any():
            continue
        out[name] = {
            "n": int(idx.sum()),
            "acc": float((y_pred[idx] == i).mean()),
        }
    return out


def imitate_score(discard_follow, call_score):
    return 0.5 * discard_follow + 0.5 * call_score


def load_pack(path):
    pack = np.load(path)
    if pack["y"].shape[0] == 0:
        return None
    train_idx, val_idx = split_by_game(pack["gamb_id"])
    return {
        "x_train": pack["x"][train_idx],
        "y_train": pack["y"][train_idx],
        "mask_train": pack["mask"][train_idx],
        "x_val": pack["x"][val_idx],
        "y_val": pack["y"][val_idx],
        "mask_val": pack["mask"][val_idx],
        "room_val": pack["room_level"][val_idx],
        "n_train": int(train_idx.sum()),
        "n_val": int(val_idx.sum()),
        "n_games_train": int(len(set(pack["gamb_id"][train_idx].tolist()))),
        "n_games_val": int(len(set(pack["gamb_id"][val_idx].tolist()))),
    }


def load_split(path=DISCARD_PATH):
    return load_pack(path)


def write_report(report, path=METRICS_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main(argv=None):
    import argparse
    import joblib

    parser = argparse.ArgumentParser(description="Score full human imitation")
    parser.add_argument("--discard-model", default="")
    parser.add_argument("--call-model", default="")
    args = parser.parse_args(argv)

    discard = load_pack(DISCARD_PATH)
    call = load_pack(CALL_PATH)
    d_scores = None
    c_scores = None
    if args.discard_model and discard is not None:
        blob = joblib.load(args.discard_model)
        d_scores = expand_proba(blob["model"].predict_proba(discard["x_val"]), blob["model"].classes_, N_TILES)
    if args.call_model and call is not None:
        blob = joblib.load(args.call_model)
        c_scores = expand_proba(blob["model"].predict_proba(call["x_val"]), blob["model"].classes_, N_CALL)

    report = assemble_report(discard, call, d_scores, c_scores)
    out = write_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"wrote={out}")


def assemble_report(discard, call, d_scores=None, c_scores=None):
    report = {}
    if discard is not None:
        report["discard"] = score_discard(
            discard["y_val"], discard["mask_val"], discard["room_val"],
            discard["y_train"], d_scores,
        )
        report["discard"]["split"] = {
            "n_train": discard["n_train"],
            "n_val": discard["n_val"],
            "n_games_train": discard["n_games_train"],
            "n_games_val": discard["n_games_val"],
        }
    if call is not None:
        report["call"] = score_call(call["y_val"], call["mask_val"], call["y_train"], c_scores)
        report["call"]["split"] = {
            "n_train": call["n_train"],
            "n_val": call["n_val"],
            "n_games_train": call["n_games_train"],
            "n_games_val": call["n_games_val"],
        }
    d_follow = report.get("discard", {}).get("model", {}).get("follow")
    if d_follow is None:
        d_follow = report.get("discard", {}).get("baselines", {}).get("majority_legal", {}).get("follow", 0.0)
    c_score = report.get("call", {}).get("model", {}).get("call_score")
    if c_score is None:
        c_score = report.get("call", {}).get("baselines", {}).get("always_pass", {}).get("call_score", 0.0)
    report["imitate"] = {
        "score": imitate_score(d_follow, c_score),
        "discard_follow": d_follow,
        "call_score": c_score,
        "formula": "0.5*discard_follow + 0.5*call_score",
        "call_score_formula": "0.5*accuracy + 0.5*nonpass_acc",
    }
    return report


if __name__ == "__main__":
    main()
