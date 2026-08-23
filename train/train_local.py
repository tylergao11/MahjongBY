# -*- coding: utf-8 -*-
"""Local CPU training for discard + call heads, then unified score."""
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

DISCARD_MODEL = MODEL_DIR / "discard_mlp.joblib"
CALL_MODEL = MODEL_DIR / "call_mlp.joblib"


def fit_head(x, y, hidden, max_iter, name):
    print(f"train {name} n={len(y)} hidden={hidden} max_iter={max_iter}", flush=True)
    model = MLPClassifier(
        hidden_layer_sizes=hidden,
        activation="relu",
        solver="adam",
        alpha=1e-4,
        batch_size=256,
        learning_rate_init=1e-3,
        max_iter=max_iter,
        random_state=7,
        verbose=True,
    )
    model.fit(x, y)
    return model


def main():
    discard = load_pack(DISCARD_PATH)
    call = load_pack(CALL_PATH)
    if discard is None:
        raise SystemExit("missing discard samples")
    if call is None:
        raise SystemExit("missing call samples")

    d_model = fit_head(discard["x_train"], discard["y_train"], (256, 128), 80, "discard")
    c_model = fit_head(call["x_train"], call["y_train"], (128, 64), 80, "call")

    d_scores = expand_proba(d_model.predict_proba(discard["x_val"]), d_model.classes_, N_TILES)
    c_scores = expand_proba(c_model.predict_proba(call["x_val"]), c_model.classes_, N_CALL)
    report = assemble_report(discard, call, d_scores, c_scores)
    report["device"] = "cpu"
    report["backend"] = "sklearn.neural_network.MLPClassifier"
    report["heads"] = {
        "discard": {"hidden": [256, 128], "max_iter": 80},
        "call": {"hidden": [128, 64], "max_iter": 80},
    }

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": d_model, "classes": d_model.classes_.tolist()}, DISCARD_MODEL)
    joblib.dump({"model": c_model, "classes": c_model.classes_.tolist()}, CALL_MODEL)
    write_report(report, METRICS_PATH)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"discard_model={DISCARD_MODEL}")
    print(f"call_model={CALL_MODEL}")
    print(f"metrics={METRICS_PATH}")


if __name__ == "__main__":
    main()
