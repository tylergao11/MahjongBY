# -*- coding: utf-8 -*-
"""Try several local heads and keep the best imitate score."""
import json
from pathlib import Path

import joblib
from sklearn.neural_network import MLPClassifier

from train.score import (
    CALL_PATH,
    DISCARD_PATH,
    METRICS_PATH,
    MODEL_DIR,
    N_CALL,
    N_TILES,
    assemble_report,
    expand_proba,
    load_pack,
    write_report,
)
from train.tiles import CALL_PASS

DISCARD_MODEL = MODEL_DIR / "discard_mlp.joblib"
CALL_MODEL = MODEL_DIR / "call_mlp.joblib"
SWEEP_PATH = MODEL_DIR / "sweep.json"

DISCARD_GRID = [
    {"name": "d_128_64_i40", "hidden": (128, 64), "max_iter": 40, "alpha": 1e-4},
    {"name": "d_128_64_i80_reg", "hidden": (128, 64), "max_iter": 80, "alpha": 5e-4},
    {"name": "d_256_128_i40_reg", "hidden": (256, 128), "max_iter": 40, "alpha": 5e-4},
]
CALL_GRID = [
    {"name": "c_128_64_i80", "hidden": (128, 64), "max_iter": 80, "alpha": 1e-4, "balance": False},
    {"name": "c_128_64_i80_bal", "hidden": (128, 64), "max_iter": 80, "alpha": 1e-4, "balance": True},
]


def _fit(x, y, spec, name):
    print(f"fit {name} {spec}", flush=True)
    model = MLPClassifier(
        hidden_layer_sizes=spec["hidden"],
        activation="relu",
        solver="adam",
        alpha=spec["alpha"],
        batch_size=256,
        learning_rate_init=1e-3,
        max_iter=spec["max_iter"],
        random_state=7,
        verbose=False,
    )
    model.fit(x, y)
    return model


def _balance_calls(x, y):
    idx_pass = np_where_equal(y, CALL_PASS)
    idx_act = np_where_not_equal(y, CALL_PASS)
    if len(idx_act) == 0:
        return x, y
    # keep all actions, downsample pass to the same count
    n = min(len(idx_pass), len(idx_act) * 2)
    rng = __import__("numpy").random.RandomState(7)
    if n < len(idx_pass):
        idx_pass = rng.choice(idx_pass, size=n, replace=False)
    keep = __import__("numpy").concatenate([idx_pass, idx_act])
    rng.shuffle(keep)
    return x[keep], y[keep]


def np_where_equal(y, v):
    import numpy as np
    return np.flatnonzero(y == v)


def np_where_not_equal(y, v):
    import numpy as np
    return np.flatnonzero(y != v)


def main():
    discard = load_pack(DISCARD_PATH)
    call = load_pack(CALL_PATH)
    d_models = {}
    c_models = {}
    for spec in DISCARD_GRID:
        d_models[spec["name"]] = _fit(discard["x_train"], discard["y_train"], spec, spec["name"])
    for spec in CALL_GRID:
        x, y = call["x_train"], call["y_train"]
        if spec.get("balance"):
            x, y = _balance_calls(x, y)
        c_models[spec["name"]] = _fit(x, y, spec, spec["name"])

    rows = []
    best = None
    best_pair = None
    for d_name, d_model in d_models.items():
        d_scores = expand_proba(d_model.predict_proba(discard["x_val"]), d_model.classes_, N_TILES)
        for c_name, c_model in c_models.items():
            c_scores = expand_proba(c_model.predict_proba(call["x_val"]), c_model.classes_, N_CALL)
            report = assemble_report(discard, call, d_scores, c_scores)
            imitate = report["imitate"]["score"]
            row = {
                "discard": d_name,
                "call": c_name,
                "imitate": imitate,
                "discard_top1": report["discard"]["model"]["top1"],
                "discard_follow": report["discard"]["model"]["follow"],
                "call_acc": report["call"]["model"]["accuracy"],
                "call_nonpass": report["call"]["model"]["nonpass_acc"],
                "call_score": report["call"]["model"]["call_score"],
            }
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
            if best is None or imitate > best["imitate"]["score"]:
                best = report
                best_pair = (d_name, c_name, d_model, c_model)

    best["device"] = "cpu"
    best["backend"] = "sklearn.neural_network.MLPClassifier"
    best["chosen"] = {"discard": best_pair[0], "call": best_pair[1]}
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": best_pair[2], "classes": best_pair[2].classes_.tolist()}, DISCARD_MODEL)
    joblib.dump({"model": best_pair[3], "classes": best_pair[3].classes_.tolist()}, CALL_MODEL)
    write_report(best, METRICS_PATH)
    SWEEP_PATH.write_text(json.dumps({"rows": rows, "chosen": best["chosen"]}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(best["imitate"], ensure_ascii=False, indent=2))
    print(f"chose={best['chosen']}")
    print(f"sweep={SWEEP_PATH}")
    print(f"metrics={METRICS_PATH}")


if __name__ == "__main__":
    main()
