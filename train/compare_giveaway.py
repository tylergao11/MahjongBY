# -*- coding: utf-8 -*-
"""1 giveaway vs 3 official online robots."""
import json
from collections import Counter
from pathlib import Path

from giveaway import GiveawayBots
from train.compare_win import _finish
from train.online_bot import OnlineBots
from train.play import play_game

OUT = Path(__file__).resolve().parent.parent / "models" / "giveaway_vs_online.json"


class MixGive1v3:
    def __init__(self, give_seat=1):
        self.give = GiveawayBots()
        self.online = OnlineBots()
        self.give_seat = give_seat
        self.kinds = {seat: "give" if seat == give_seat else "online" for seat in (1, 2, 3, 4)}

    def _bot(self, seat):
        return self.give if self.kinds[seat] == "give" else self.online

    def pick_discard(self, *args, **kwargs):
        return self._bot(args[0]).pick_discard(*args, **kwargs)

    def pick_call(self, *args, **kwargs):
        return self._bot(args[0]).pick_call(*args, **kwargs)

    def want_bu_gang(self, hand, melds, kinds, wall_n=80, seat=None, **kwargs):
        kind = self.kinds.get(seat, "online")
        bot = self.give if kind == "give" else self.online
        return bot.want_bu_gang(hand, melds, kinds, wall_n=wall_n, seat=seat, **kwargs)


def main():
    n = 30
    seed0 = 9200
    stats = {
        "n": 0,
        "hu": 0,
        "zimo": 0,
        "dianpao": 0,
        "draw": 0,
        "avg_discard": 0.0,
        "seat_wins": {1: 0, 2: 0, 3: 0, 4: 0},
    }
    extra = Counter()
    give_fans = []
    for i in range(n):
        game = play_game(seed=seed0 + i, bots=MixGive1v3())
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
        stats["avg_discard"] += game.get("n_discard") or 0
        winners = game.get("winners") or []
        if not winners and game.get("winner"):
            winners = [game.get("winner")]
        for winner in winners:
            if winner in stats["seat_wins"]:
                stats["seat_wins"][winner] += 1
        extra[game.get("result")] += 1
        winners = game.get("winners") or []
        if 1 in winners:
            fans = game.get("fans") or {}
            give_fans.append(fans.get("1") or fans.get(1))
        print(
            "g1o3 %s/%s result=%s winner=%s nd=%s"
            % (i + 1, n, game.get("result"), game.get("winner"), game.get("n_discard")),
            flush=True,
        )
    out = _finish(stats)
    give_n = stats["seat_wins"][1]
    online_n = stats["seat_wins"][2] + stats["seat_wins"][3] + stats["seat_wins"][4]
    out["by_result"] = dict(extra)
    out["give_seat"] = 1
    out["give_wins"] = give_n
    out["online_wins"] = online_n
    out["give_rate"] = give_n / n
    out["online_rate"] = online_n / n
    out["give_fans"] = give_fans
    out["note"] = "seat 1 giveaway, seats 2+3+4 online, seeds %s-%s" % (seed0, seed0 + n - 1)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote=%s" % OUT, flush=True)
    print(
        json.dumps(
            {
                "n": n,
                "give_wins": give_n,
                "online_wins": online_n,
                "draw": stats["draw"],
                "give_rate": out["give_rate"],
                "online_rate": out["online_rate"],
                "draw_rate": out["draw_rate"],
                "avg_discard": out["avg_discard"],
                "by_result": out["by_result"],
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
