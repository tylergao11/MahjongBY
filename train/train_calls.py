# -*- coding: utf-8 -*-
"""Retrain call heads only. Keep the current discard model."""
import json
import sys

import joblib

from train.call_heads import HierarchicalCall
from train.score import (
    CALL_PATH,
    DISCARD_PATH,
    METRICS_PATH,
    MODEL_DIR,
    _call_detail,
    assemble_report,
    discard_blob_proba,
    load_pack,
    split_by_game,
    write_report,
)

CALL_MODEL = MODEL_DIR / "call_mlp.joblib"
DISCARD_MODEL = MODEL_DIR / "discard_mlp.joblib"


def discard_scores(discard):
    blob = joblib.load(DISCARD_MODEL)
    pack = __import__("numpy").load(DISCARD_PATH)
    _train_idx, val_idx = split_by_game(pack["gamb_id"])
    x_val = pack["x_compact"][val_idx] if "x_compact" in pack.files else discard["x_val"]
    return discard_blob_proba(blob, x_val)


def main():
    discard = load_pack(DISCARD_PATH)
    call = load_pack(CALL_PATH)
    if "--score-only" in sys.argv:
        heads = joblib.load(CALL_MODEL)["model"]
        c_scores = heads.predict_scores(call["x_val"], call["mask_val"])
    else:
        heads = HierarchicalCall().fit(call["x_train"], call["y_train"], call["mask_train"])
        best_scale, best_cs = 1.0, -1.0
        for scale in (0.75, 0.9, 1.0, 1.15, 1.35, 1.6, 1.9, 2.3):
            heads.chi_scale = scale
            detail = _call_detail(
                heads.predict_scores(call["x_val"], call["mask_val"]),
                call["y_val"],
                call["mask_val"],
            )
            print(
                f"chi_scale={scale:.2f} call_score={detail['call_score']:.4f} "
                f"acc={detail['accuracy']:.3f} pass={detail['pass_acc']:.3f} "
                f"nonpass={detail['nonpass_acc']:.3f}",
                flush=True,
            )
            if detail["call_score"] > best_cs:
                best_cs, best_scale = detail["call_score"], scale
        heads.chi_scale = best_scale
        print(f"kept chi_scale={best_scale:.2f} call_score={best_cs:.4f}", flush=True)
        c_scores = heads.predict_scores(call["x_val"], call["mask_val"])
    d_scores = discard_scores(discard)
    report = assemble_report(discard, call, d_scores, c_scores)
    report["device"] = "cpu"
    report["call_model"] = "hierarchical_family_chi_penggang"
    prev = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    report["previous_imitate"] = prev.get("imitate")
    report["previous_call"] = {
        "accuracy": prev.get("call", {}).get("model", {}).get("accuracy"),
        "nonpass_acc": prev.get("call", {}).get("model", {}).get("nonpass_acc"),
        "per_class": prev.get("call", {}).get("per_class"),
    }
    prev_score = float((prev.get("imitate") or {}).get("score") or -1)
    new_score = float(report["imitate"]["score"])
    if "--score-only" not in sys.argv:
        if new_score + 1e-6 >= prev_score:
            joblib.dump({"model": heads, "kind": "hierarchical"}, CALL_MODEL)
            write_report(report, METRICS_PATH)
            print(f"kept call imitate={new_score:.4f}", flush=True)
        else:
            print(f"skip call imitate={new_score:.4f} < {prev_score:.4f}", flush=True)
    else:
        write_report(report, METRICS_PATH)
    print(json.dumps({
        "imitate": report["imitate"],
        "call": report["call"]["model"],
        "per_class": report["call"]["per_class"],
        "previous_imitate": report["previous_imitate"],
    }, ensure_ascii=False, indent=2))
    print(f"call_model={CALL_MODEL}")
    print(f"metrics={METRICS_PATH}")


if __name__ == "__main__":
    main()
