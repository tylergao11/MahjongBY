# -*- coding: utf-8 -*-
"""Harvest vs companion, real table games."""
import json
from collections import Counter
from pathlib import Path

from companion import CompanionBots
from harvest import HarvestBots
from train.play import play_game

OUT = Path(__file__).resolve().parent.parent / "models" / "harvest_vs_companion.json"


class Mix:
    def __init__(self, kinds):
        self.harvest = HarvestBots()
        self.companion = CompanionBots()
        self.kinds = kinds

    def _bot(self, seat):
        return self.harvest if self.kinds[seat] == "harvest" else self.companion

    def pick_discard(self, *args, **kwargs):
        return self._bot(args[0]).pick_discard(*args, **kwargs)

    def pick_call(self, *args, **kwargs):
        return self._bot(args[0]).pick_call(*args, **kwargs)

    def want_bu_gang(self, hand, melds, kinds, wall_n=80, seat=None, **kwargs):
        return self._bot(seat).want_bu_gang(hand, melds, kinds, wall_n=wall_n, seat=seat, **kwargs)


def _add(stats, game, harvest_seats):
    stats["n"] += 1
    how = game.get("result")
    if how == "自摸":
        stats["zimo"] += 1
        stats["hu"] += 1
    elif how in ("点炮", "抢杠"):
        stats["dianpao"] += 1
        stats["hu"] += 1
    elif how in ("十风", "十三幺"):
        stats["zimo"] += 1
        stats["hu"] += 1
    else:
        stats["draw"] += 1
    stats["discards"] += game.get("n_discard") or 0
    winners = game.get("winners") or []
    if not winners and game.get("winner"):
        winners = [game.get("winner")]
    h = c = 0
    for seat in winners:
        if seat in harvest_seats:
            h += 1
        else:
            c += 1
    stats["harvest_wins"] += h
    stats["companion_wins"] += c
    extra = game.get("result")
    stats["by_result"][extra] += 1


def run_batch(name, n, kinds, seed0):
    harvest_seats = {seat for seat, kind in kinds.items() if kind == "harvest"}
    stats = {
        "n": 0, "hu": 0, "zimo": 0, "dianpao": 0, "draw": 0,
        "discards": 0, "harvest_wins": 0, "companion_wins": 0,
        "by_result": Counter(),
    }
    for i in range(n):
        game = play_game(seed=seed0 + i, bots=Mix(kinds))
        _add(stats, game, harvest_seats)
        print(
            "%s %s/%s result=%s winner=%s nd=%s"
            % (name, i + 1, n, game.get("result"), game.get("winner"), game.get("n_discard")),
            flush=True,
        )
    n = max(stats["n"], 1)
    return {
        "n": stats["n"],
        "harvest_wins": stats["harvest_wins"],
        "companion_wins": stats["companion_wins"],
        "draw": stats["draw"],
        "harvest_rate": stats["harvest_wins"] / n,
        "companion_rate": stats["companion_wins"] / n,
        "draw_rate": stats["draw"] / n,
        "hu_rate": stats["hu"] / n,
        "avg_discard": stats["discards"] / n,
        "by_result": dict(stats["by_result"]),
        "note": "harvest=%s companion=%s seeds=%s-%s"
        % (sorted(harvest_seats), sorted(set(kinds) - harvest_seats), seed0, seed0 + stats["n"] - 1),
    }


def main():
    report = {
        "h2c2": run_batch("h2c2", 24, {1: "harvest", 2: "companion", 3: "harvest", 4: "companion"}, 12000),
        "h1c3": run_batch("h1c3", 20, {1: "harvest", 2: "companion", 3: "companion", 4: "companion"}, 12100),
        "c1h3": run_batch("c1h3", 20, {1: "companion", 2: "harvest", 3: "harvest", 4: "harvest"}, 12200),
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote=%s" % OUT, flush=True)
    print(
        json.dumps(
            {
                key: {
                    "harvest": row["harvest_wins"],
                    "companion": row["companion_wins"],
                    "draw": row["draw"],
                    "h_rate": row["harvest_rate"],
                    "c_rate": row["companion_rate"],
                    "avg_nd": row["avg_discard"],
                }
                for key, row in report.items()
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
