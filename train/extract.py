# -*- coding: utf-8 -*-
"""Build discard + call samples from fxj.jsonl."""
import json
from collections import Counter
from pathlib import Path

import numpy as np

from train.replay import extract_samples
from train.tiles import CALL_NAMES

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "fxj.jsonl"
OUT_DIR = ROOT / "data"
DISCARD_PATH = OUT_DIR / "discard_samples.npz"
CALL_PATH = OUT_DIR / "call_samples.npz"


def _dump(path, rows):
    if not rows:
        np.savez_compressed(
            path,
            x=np.zeros((0, 1), dtype=np.float32),
            y=np.zeros((0,), dtype=np.int64),
            mask=np.zeros((0, 1), dtype=np.int8),
            gamb_id=np.zeros((0,), dtype=np.int64),
            room_level=np.zeros((0,), dtype=np.int64),
        )
        return 0
    payload = {
        "x": np.asarray([r["x"] for r in rows], dtype=np.float32),
        "y": np.asarray([r["y"] for r in rows], dtype=np.int64),
        "mask": np.asarray([r["mask"] for r in rows], dtype=np.int8),
        "gamb_id": np.asarray([r["gamb_id"] if r["gamb_id"] is not None else -1 for r in rows], dtype=np.int64),
        "room_level": np.asarray([r["room_level"] if r["room_level"] is not None else -1 for r in rows], dtype=np.int64),
    }
    if rows and "x_compact" in rows[0]:
        payload["x_compact"] = np.asarray([r["x_compact"] for r in rows], dtype=np.float32)
    np.savez_compressed(path, **payload)
    return len(rows)


def main():
    games = []
    with DATA.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                games.append(json.loads(line))

    discards = []
    calls = []
    skipped = 0
    for game in games:
        d_rows, c_rows = extract_samples(game)
        if not d_rows and not c_rows:
            skipped += 1
            continue
        discards.extend(d_rows)
        calls.extend(c_rows)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    n_d = _dump(DISCARD_PATH, discards)
    n_c = _dump(CALL_PATH, calls)
    print(f"games={len(games)} skipped={skipped} discards={n_d} calls={n_c}")
    if discards:
        print(f"discard_dim={len(discards[0]['x'])} discard_y={Counter(r['y'] for r in discards).most_common(8)}")
    if calls:
        print(f"call_dim={len(calls[0]['x'])} call_y={[(CALL_NAMES[k], v) for k, v in Counter(r['y'] for r in calls).most_common()]}")
    print(f"wrote={DISCARD_PATH}")
    print(f"wrote={CALL_PATH}")


if __name__ == "__main__":
    main()
