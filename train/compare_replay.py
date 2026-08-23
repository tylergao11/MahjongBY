# -*- coding: utf-8 -*-
"""Print human vs model on a few real games so progress is visible."""
import json
from pathlib import Path

import joblib
import numpy as np

from train.replay import extract_samples
from train.score import discard_blob_proba, legal_rank
from train.tiles import CALL_NAMES, IDX_TO_TILE, TILE_NAMES

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "fxj.jsonl"
OUT = ROOT / "models" / "replay_compare.txt"


def _tile(idx):
    return TILE_NAMES.get(IDX_TO_TILE[int(idx)], str(idx))


def _call(idx):
    return CALL_NAMES[int(idx)]


def main(n_games=8):
    discard_blob = joblib.load(ROOT / "models" / "discard_mlp.joblib")
    call_blob = joblib.load(ROOT / "models" / "call_mlp.joblib")
    c_model = call_blob["model"]
    lines = []
    games = []
    with DATA.open("r", encoding="utf-8") as handle:
        for i, line in enumerate(handle):
            if i >= n_games:
                break
            games.append(json.loads(line))

    d_hit = d_n = c_hit = c_n = 0
    for g in games:
        discards, calls = extract_samples(g)
        lines.append(f"gamb={g.get('gamb_id')} room={g.get('room_level')} discard={len(discards)} call={len(calls)}")
        shown = 0
        for row in discards:
            x = np.asarray(row.get("x_compact", row["x"]), dtype=np.float32).reshape(1, -1)
            proba = discard_blob_proba(discard_blob, x)
            pred = int(legal_rank(proba, np.asarray(row["mask"]).reshape(1, -1))[0, 0])
            ok = pred == row["y"]
            d_hit += int(ok)
            d_n += 1
            if shown < 4:
                lines.append(f"  出牌 人={_tile(row['y'])} 模型={_tile(pred)} {'对' if ok else '错'}")
                shown += 1
        shown = 0
        for row in calls:
            x = np.asarray(row["x"], dtype=np.float32).reshape(1, -1)
            mask = np.asarray(row["mask"], dtype=np.int8).reshape(1, -1)
            if hasattr(c_model, "predict_scores"):
                scores = c_model.predict_scores(x, mask)
            else:
                continue
            pred = int(legal_rank(scores, mask)[0, 0])
            ok = pred == row["y"]
            c_hit += int(ok)
            c_n += 1
            if shown < 6:
                lines.append(f"  鸣牌 人={_call(row['y'])} 模型={_call(pred)} {'对' if ok else '错'}")
                shown += 1
        lines.append("")

    lines.append(f"这{n_games}局出牌 {d_hit}/{d_n} 鸣牌 {c_hit}/{c_n}")
    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text)
    print(f"wrote={OUT}")


if __name__ == "__main__":
    main()
