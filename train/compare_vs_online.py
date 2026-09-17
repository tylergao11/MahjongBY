# -*- coding: utf-8 -*-
"""Harvest and companion each play official online robots."""
import json
from collections import Counter
from pathlib import Path

from companion import CompanionBots
from giveaway import GiveawayBots
from harvest import HarvestBots
from train.online_bot import OnlineBots
from train.play import play_game

OUT = Path(__file__).resolve().parent.parent / "models" / "vs_online.json"


class Mix:
    def __init__(self, kinds, ours):
        self.ours = ours
        self.online = OnlineBots()
        self.kinds = kinds

    def _bot(self, seat):
        return self.ours if self.kinds[seat] == "ours" else self.online

    def pick_discard(self, *args, **kwargs):
        return self._bot(args[0]).pick_discard(*args, **kwargs)

    def pick_call(self, *args, **kwargs):
        return self._bot(args[0]).pick_call(*args, **kwargs)

    def want_bu_gang(self, hand, melds, kinds, wall_n=80, seat=None, **kwargs):
        return self._bot(seat).want_bu_gang(hand, melds, kinds, wall_n=wall_n, seat=seat, **kwargs)


def run_batch(name, n, kinds, make_ours, seed0):
    ours_seats = {seat for seat, kind in kinds.items() if kind == "ours"}
    stats = {
        "n": 0, "hu": 0, "zimo": 0, "dianpao": 0, "draw": 0,
        "discards": 0, "ours_wins": 0, "online_wins": 0,
        "by_result": Counter(),
    }
    for i in range(n):
        game = play_game(seed=seed0 + i, bots=Mix(kinds, make_ours()))
        stats["n"] += 1
        how = game.get("result")
        if how == "自摸":
            stats["hu"] += 1
            stats["zimo"] += 1
        elif how in ("点炮", "抢杠"):
            stats["hu"] += 1
            stats["dianpao"] += 1
        elif how in ("十风", "十三幺"):
            stats["hu"] += 1
            stats["zimo"] += 1
        else:
            stats["draw"] += 1
        stats["discards"] += game.get("n_discard") or 0
        stats["by_result"][how] += 1
        winners = game.get("winners") or []
        if not winners and game.get("winner"):
            winners = [game.get("winner")]
        for seat in winners:
            if seat in ours_seats:
                stats["ours_wins"] += 1
            else:
                stats["online_wins"] += 1
        print(
            "%s %s/%s result=%s winner=%s nd=%s"
            % (name, i + 1, n, game.get("result"), game.get("winner"), game.get("n_discard")),
            flush=True,
        )
    n = max(stats["n"], 1)
    return {
        "n": stats["n"],
        "ours_wins": stats["ours_wins"],
        "online_wins": stats["online_wins"],
        "draw": stats["draw"],
        "ours_rate": stats["ours_wins"] / n,
        "online_rate": stats["online_wins"] / n,
        "draw_rate": stats["draw"] / n,
        "avg_discard": stats["discards"] / n,
        "by_result": dict(stats["by_result"]),
        "note": "ours=%s online=%s seeds=%s-%s"
        % (sorted(ours_seats), sorted(set(kinds) - ours_seats), seed0, seed0 + stats["n"] - 1),
    }


def main():
    one = {1: "ours", 2: "online", 3: "online", 4: "online"}
    report = {
        "harvest_1v3": run_batch("h1o3", 30, one, HarvestBots, 13200),
        "companion_1v3": run_batch("c1o3", 30, one, CompanionBots, 13200),
        "giveaway_1v3": run_batch("g1o3", 30, one, GiveawayBots, 13200),
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote=%s" % OUT, flush=True)
    print(
        json.dumps(
            {
                key: {
                    "ours": row["ours_wins"],
                    "online": row["online_wins"],
                    "draw": row["draw"],
                    "ours_rate": row["ours_rate"],
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
