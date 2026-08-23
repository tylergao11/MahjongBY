# -*- coding: utf-8 -*-
"""Bag several HGB discard models; keep bag if follow rises."""
import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from train.score import (
    DISCARD_PATH,
    MODEL_DIR,
    N_TILES,
    discard_blob_proba,
    expand_proba,
    score_scores,
    split_by_game,
)

DISCARD_MODEL = MODEL_DIR / "discard_mlp.joblib"


def _hgb(seed, max_iter=320, depth=8):
    return HistGradientBoostingClassifier(
        max_depth=depth,
        max_iter=max_iter,
        learning_rate=0.07,
        l2_regularization=0.12,
        min_samples_leaf=20,
        random_state=seed,
    )


def main():
    pack = np.load(DISCARD_PATH)
    train_idx, val_idx = split_by_game(pack["gamb_id"])
    x_train, y_train = pack["x_compact"][train_idx], pack["y"][train_idx]
    x_val, y_val = pack["x_compact"][val_idx], pack["y"][val_idx]
    mask_val = pack["mask"][val_idx]
    print(f"discard train={len(y_train)} dim={x_train.shape[1]}", flush=True)

    models = []
    best_i = 0
    best_f = -1.0
    for i, (seed, depth, iters) in enumerate((
        (7, 8, 320),
        (17, 7, 280),
        (27, 9, 240),
        (37, 8, 400),
        (47, 6, 360),
    )):
        print(f"fit HGB seed={seed} depth={depth} iter={iters}", flush=True)
        model = _hgb(seed, iters, depth)
        model.fit(x_train, y_train)
        one = score_scores(expand_proba(model.predict_proba(x_val), model.classes_, N_TILES), y_val, mask_val)
        print(f"  follow={one['follow']:.4f} top1={one['top1']:.4f}", flush=True)
        if one["follow"] > best_f:
            best_f = one["follow"]
            best_i = i
        models.append(model)

    bag = {"model": models, "kind": "bag", "features": "compact_shape_seq"}
    bag_m = score_scores(discard_blob_proba(bag, x_val), y_val, mask_val)
    print(f"bag follow={bag_m['follow']:.4f} top1={bag_m['top1']:.4f}", flush=True)

    if bag_m["follow"] >= best_f:
        payload, name, follow = bag, "bag", bag_m["follow"]
    else:
        payload = {
            "model": models[best_i],
            "kind": "hgb",
            "classes": models[best_i].classes_.tolist(),
            "features": "compact_shape_seq",
        }
        name, follow = f"hgb{best_i}", best_f

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    prev_follow = -1.0
    if DISCARD_MODEL.exists():
        try:
            old = joblib.load(DISCARD_MODEL)
            if old.get("features") == payload.get("features") and (
                (old.get("kind") == "bag" and x_train.shape[1] == x_val.shape[1])
            ):
                prev_follow = score_scores(discard_blob_proba(old, x_val), y_val, mask_val)["follow"]
        except Exception:
            prev_follow = -1.0
    if follow + 1e-6 < prev_follow:
        print(f"skip write {name} follow={follow:.4f} < current {prev_follow:.4f}")
        return
    joblib.dump(payload, DISCARD_MODEL)
    print(f"kept {name} follow={follow:.4f}")


if __name__ == "__main__":
    main()
