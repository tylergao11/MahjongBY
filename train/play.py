# -*- coding: utf-8 -*-
"""Four harvest robots play one official kechichang game."""
import json
import random
import time
from collections import Counter
from pathlib import Path

from harvest import HarvestBots
from harvest.legal import legal_call_mask
from train.replay import (
    _chi_needed,
    _take,
)
from train.fxj_rules import (
    judge,
    liuju_left,
    pick_gang_tile,
    ron_fan,
    settle,
    underground_hu,
)
from train.table import SEATS
from train.tiles import (
    CALL_AN_GANG,
    CALL_CHI_HIGH,
    CALL_CHI_LOW,
    CALL_CHI_MID,
    CALL_HU,
    CALL_MING_GANG,
    CALL_PASS,
    CALL_PENG,
    TILE_IDS,
    discard_legal_vec,
    next_seat,
    tile_idx,
    tile_name,
)

ROOT = Path(__file__).resolve().parent.parent
GAMES_DIR = ROOT / "models" / "games"
INDEX_PATH = GAMES_DIR / "index.json"
BOT_NAMES = {1: "机器人1", 2: "机器人2", 3: "机器人3", 4: "机器人4"}
CHI = {
    CALL_CHI_HIGH: ("high", "吃高"),
    CALL_CHI_MID: ("mid", "吃中"),
    CALL_CHI_LOW: ("low", "吃低"),
}
MAX_DISCARDS = 120
_BOTS = None


def load_bots():
    global _BOTS
    if _BOTS is None:
        _BOTS = HarvestBots()
    return _BOTS


def __getattr__(name):
    if name == "Bots":
        return HarvestBots
    raise AttributeError(name)


def _safe_discard(hand, tile):
    if tile in hand:
        return tile
    return hand[0]


def _an_gang_tile(hand):
    for tile, n in Counter(hand).items():
        if n >= 4:
            return tile
    return None


def _bu_gang_tile(hand, melds, kinds):
    i = 0
    for kind in kinds:
        n = 4 if kind in ("gang", "an_gang", "ming_gang") else 3
        group = melds[i:i + n]
        i += n
        if kind == "peng" and group and group[0] in hand:
            return group[0]
    return None


def _force_legal_discard(hand, tile, forbid=None):
    legal = discard_legal_vec(hand, forbid=forbid)
    tidx = tile_idx(tile)
    if tile in hand and tidx is not None and legal[tidx]:
        return tile
    for cand in hand:
        cidx = tile_idx(cand)
        if cidx is not None and legal[cidx]:
            return cand
    return hand[0]


def _first_after(start, seats):
    seat = start
    for _ in range(4):
        seat = next_seat(seat)
        if seat in seats:
            return seat
    return seats[0]


def _mark_called(rivers, river_called, seat, tile):
    river = rivers[seat]
    for i in range(len(river) - 1, -1, -1):
        if river[i] == tile:
            river_called[seat].add(i)
            break


def play_game(seed=None, bots=None):
    rng = random.Random(seed)
    if bots is None:
        bots = load_bots()
    wall = []
    for tid in TILE_IDS:
        wall.extend([tid] * 4)
    rng.shuffle(wall)
    dealer = rng.choice(list(SEATS))
    hands = {seat: [] for seat in SEATS}
    for _ in range(13):
        for seat in SEATS:
            hands[seat].append(wall.pop(0))
    hands[dealer].append(wall.pop(0))
    rivers = {seat: [] for seat in SEATS}
    river_called = {seat: set() for seat in SEATS}
    melds = {seat: [] for seat in SEATS}
    meld_kinds = {seat: [] for seat in SEATS}
    n_melds = {seat: 0 for seat in SEATS}
    passed_hu = {seat: set() for seat in SEATS}
    passed_fan = {seat: None for seat in SEATS}
    passed_peng = {seat: set() for seat in SEATS}
    gang_n = [0]
    after_gang_turn = [False]
    gid = "bot-%s-%04d" % (time.strftime("%Y%m%d-%H%M%S"), rng.randint(0, 9999))
    events = [{
        "op": "deal",
        "dealer": dealer,
        "hands": {seat: list(hands[seat]) for seat in SEATS},
        "names": dict(BOT_NAMES),
        "gamb_id": gid,
        "room_level": "bot",
        "wall_left": len(wall),
    }]
    discards = [0]
    last_seat = [dealer]
    ended = {
        "how": "流局", "winner": None, "winners": [], "zimo": False,
        "tile": None, "from_seat": None, "settle": None, "fans": {},
    }

    def clear_pass(seat):
        passed_hu[seat].clear()
        passed_fan[seat] = None
        passed_peng[seat].clear()

    def draw(seat, gang=False):
        if gang:
            pool = wall[-2:] if len(wall) >= 2 else list(wall)
            tile = pick_gang_tile(hands[seat], n_melds[seat], pool)
            if tile is None:
                return None
            wall.remove(tile)
        else:
            if len(wall) <= liuju_left(gang_n[0]):
                return None
            tile = wall.pop(0)
        hands[seat].append(tile)
        clear_pass(seat)
        events.append({"op": "draw", "seat": seat, "tile": tile, "gang": gang})
        return tile

    def do_discard(seat, just_drew, forbid=None):
        tile = bots.pick_discard(
            seat, dealer, hands, rivers, melds, n_melds, just_drew, forbid=forbid,
            meld_kinds=meld_kinds[seat], wall_n=len(wall),
        )
        tile = _force_legal_discard(hands[seat], tile, forbid=forbid)
        hands[seat].remove(tile)
        rivers[seat].append(tile)
        events.append({"op": "discard", "seat": seat, "tile": tile})
        discards[0] += 1
        last_seat[0] = seat
        return tile

    def collect_calls(offer, offer_seat, after_gang=False):
        picks = {}
        for seat in SEATS:
            if seat == offer_seat:
                continue
            action = bots.pick_call(
                seat, dealer, hands, rivers, melds, n_melds,
                offer=offer, offer_seat=offer_seat, own_turn=False, just_drew=0, wall_n=len(wall),
                meld_kinds=meld_kinds[seat], blocked_hu=passed_hu[seat],
                passed_fan=passed_fan[seat], passed_peng=passed_peng[seat],
                after_gang=after_gang,
            )
            mask = legal_call_mask(
                hands[seat], offer, offer_seat, seat, own_turn=False, n_melds=n_melds[seat],
                meld_kinds=meld_kinds[seat], blocked_hu=passed_hu[seat],
                passed_fan=passed_fan[seat], passed_peng=passed_peng[seat],
                after_gang=after_gang, melds=melds[seat],
            )
            if mask[CALL_HU] and action == CALL_PASS:
                passed_hu[seat].add(offer)
                fan = ron_fan(
                    hands[seat], extra=offer, n_melds=n_melds[seat],
                    meld_kinds=meld_kinds[seat], melds=melds[seat], after_gang=after_gang,
                )
                if fan >= 0:
                    prev = passed_fan[seat]
                    passed_fan[seat] = fan if prev is None else max(prev, fan)
            if mask[CALL_PENG] or mask[CALL_MING_GANG]:
                if action == CALL_PASS:
                    passed_peng[seat].add(offer)
            if action != CALL_PASS and mask[action]:
                picks[seat] = action
                clear_pass(seat)
        return picks

    def finish_hu(winners, tile, zimo, from_seat, qiang=False, special=None, after_gang=False):
        ordered = []
        if zimo:
            ordered = list(winners)
        else:
            seat = from_seat
            for _ in range(4):
                seat = next_seat(seat)
                if seat in winners:
                    ordered.append(seat)
        judgments = {}
        for seat in ordered:
            extra = None if zimo else tile
            info = judge(
                hands[seat], extra=extra, n_melds=n_melds[seat],
                meld_kinds=meld_kinds[seat], melds=melds[seat],
                zimo=zimo, after_gang=after_gang, qiang_gang=qiang,
                hu_tile=tile, special=special,
            )
            if info is None and special:
                info = {
                    "ok": True, "base": special, "base_fan": 3, "extras": [],
                    "extra_fan": 0, "total_fan": 3, "money": 8,
                }
            if info is None:
                continue
            judgments[seat] = info
            events.append({
                "op": "hu", "seat": seat, "tile": tile, "zimo": zimo,
                "from_seat": from_seat, "fan": info,
            })
        if not judgments:
            return None
        if from_seat and not zimo:
            _mark_called(rivers, river_called, from_seat, tile)
        pay = settle(list(judgments), from_seat, zimo, qiang, judgments)
        how = special or ("自摸" if zimo else ("抢杠" if qiang else "点炮"))
        first = next(iter(judgments))
        ended.update({
            "how": how, "winner": first, "winners": list(judgments),
            "zimo": zimo, "tile": tile, "from_seat": from_seat,
            "settle": pay, "fans": {str(s): judgments[s] for s in judgments},
        })
        return "hu"

    def try_qiang_gang(offer, offer_seat):
        picks = collect_calls(offer, offer_seat, after_gang=True)
        hus = [seat for seat, action in picks.items() if action == CALL_HU]
        if not hus:
            return None
        return finish_hu(hus, offer, False, offer_seat, qiang=True, after_gang=True)

    def own_turn(seat, just_drew, after_gang=False):
        after_gang_turn[0] = after_gang
        action = bots.pick_call(
            seat, dealer, hands, rivers, melds, n_melds,
            offer=None, offer_seat=None, own_turn=True, just_drew=just_drew, wall_n=len(wall),
            meld_kinds=meld_kinds[seat], blocked_hu=passed_hu[seat],
        )
        if action == CALL_HU:
            tile = hands[seat][-1] if hands[seat] else None
            return finish_hu([seat], tile, True, None, after_gang=after_gang)
        if action == CALL_AN_GANG:
            tile = _an_gang_tile(hands[seat])
            if tile is not None:
                _take(hands[seat], [tile] * 4)
                melds[seat].extend([tile] * 4)
                meld_kinds[seat].append("an_gang")
                n_melds[seat] += 1
                gang_n[0] += 1
                clear_pass(seat)
                events.append({"op": "an_gang", "seat": seat, "tile": tile})
                if draw(seat, gang=True) is None:
                    return "wall"
                return own_turn(seat, True, after_gang=True)
        bu = None
        if hasattr(bots, "want_bu_gang"):
            bu = bots.want_bu_gang(
                hands[seat], melds[seat], meld_kinds[seat], wall_n=len(wall), seat=seat,
            )
        if bu is not None and wall:
            hands[seat].remove(bu)
            i = 0
            for ki, kind in enumerate(meld_kinds[seat]):
                n = 4 if kind in ("gang", "an_gang", "ming_gang") else 3
                if kind == "peng" and melds[seat][i] == bu:
                    melds[seat][i:i + 3] = [bu, bu, bu, bu]
                    meld_kinds[seat][ki] = "gang"
                    break
                i += n
            gang_n[0] += 1
            events.append({"op": "bu_gang", "seat": seat, "tile": bu})
            qiang = try_qiang_gang(bu, seat)
            if qiang:
                return qiang
            if draw(seat, gang=True) is None:
                return "wall"
            return own_turn(seat, True, after_gang=True)
        tile = do_discard(seat, just_drew)
        ug = underground_hu(rivers[seat], n_melds[seat])
        if ug:
            return finish_hu([seat], tile, True, None, special=ug)
        return "discard"

    def after_discard(offer, offer_seat):
        picks = collect_calls(offer, offer_seat)
        hus = [seat for seat, action in picks.items() if action == CALL_HU]
        if hus:
            return finish_hu(hus, offer, False, offer_seat)
        gangs = [seat for seat, action in picks.items() if action == CALL_MING_GANG]
        if gangs:
            seat = _first_after(offer_seat, gangs)
            _take(hands[seat], [offer] * 3)
            melds[seat].extend([offer] * 4)
            meld_kinds[seat].append("ming_gang")
            n_melds[seat] += 1
            gang_n[0] += 1
            clear_pass(seat)
            _mark_called(rivers, river_called, offer_seat, offer)
            events.append({"op": "gang", "seat": seat, "tile": offer})
            if draw(seat, gang=True) is None:
                return "wall"
            result = own_turn(seat, True, after_gang=True)
            if result == "hu":
                return "hu"
            if result == "wall":
                return "wall"
            if discards[0] >= MAX_DISCARDS:
                return "wall"
            return after_discard(rivers[seat][-1], seat)
        pengs = [seat for seat, action in picks.items() if action == CALL_PENG]
        if pengs:
            seat = _first_after(offer_seat, pengs)
            _take(hands[seat], [offer, offer])
            melds[seat].extend([offer] * 3)
            meld_kinds[seat].append("peng")
            n_melds[seat] += 1
            clear_pass(seat)
            _mark_called(rivers, river_called, offer_seat, offer)
            events.append({"op": "peng", "seat": seat, "tile": offer})
            do_discard(seat, 0)
            if discards[0] >= MAX_DISCARDS:
                return "wall"
            return after_discard(rivers[seat][-1], seat)
        chis = [seat for seat, action in picks.items() if action in CHI]
        if chis:
            seat = chis[0]
            kind_key, kind_name = CHI[picks[seat]]
            need = _chi_needed(offer, kind_key)
            tiles = need + [offer]
            _take(hands[seat], need)
            melds[seat].extend(tiles)
            meld_kinds[seat].append("chi")
            n_melds[seat] += 1
            clear_pass(seat)
            _mark_called(rivers, river_called, offer_seat, offer)
            events.append({"op": "chi", "seat": seat, "tiles": tiles, "kind": kind_name})
            do_discard(seat, 0, forbid=offer)
            if discards[0] >= MAX_DISCARDS:
                return "wall"
            return after_discard(rivers[seat][-1], seat)
        if len(wall) <= liuju_left(gang_n[0]):
            return "wall"
        return "pass"

    result = own_turn(dealer, 1)
    if result not in ("hu", "wall"):
        while discards[0] < MAX_DISCARDS:
            status = after_discard(rivers[last_seat[0]][-1], last_seat[0])
            if status in ("hu", "wall"):
                break
            nxt = next_seat(last_seat[0])
            if draw(nxt) is None:
                break
            result = own_turn(nxt, 1)
            if result in ("hu", "wall"):
                break
    events.append({"op": "end"})
    return _finish(gid, events, ended, seed)


def _finish(gid, events, ended, seed):
    events[-1] = {"op": "end"}
    return {
        "id": gid,
        "seed": seed,
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "events": events,
        "result": ended["how"],
        "winner": ended["winner"],
        "winners": ended.get("winners") or ([] if ended["winner"] is None else [ended["winner"]]),
        "zimo": ended["zimo"],
        "hu_tile": ended["tile"],
        "from_seat": ended["from_seat"],
        "settle": ended.get("settle"),
        "fans": ended.get("fans") or {},
        "n_discard": sum(1 for e in events if e.get("op") == "discard"),
    }


def result_text(game):
    winners = game.get("winners") or []
    if not winners and game.get("winner"):
        winners = [game.get("winner")]
    names = "、".join(BOT_NAMES.get(s, "") for s in winners)
    tile = tile_name(game.get("hu_tile")) if game.get("hu_tile") else ""
    fans = game.get("fans") or {}
    fan_txt = ""
    if fans:
        bits = []
        for seat in winners:
            info = fans.get(str(seat)) or fans.get(seat) or {}
            labels = [info.get("base") or ""] + [n for n, _ in (info.get("extras") or [])]
            bits.append("%s%s番" % ("".join(labels), info.get("total_fan", "")))
        fan_txt = " " + "，".join(b for b in bits if b)
    if game.get("result") in ("自摸", "十风", "十三幺") and winners:
        prefix = "自摸" if game.get("result") == "自摸" else game.get("result")
        return "%s %s %s%s" % (names, prefix, tile, fan_txt)
    if game.get("result") in ("点炮", "抢杠") and winners:
        src = BOT_NAMES.get(game.get("from_seat"), "")
        verb = "抢杠" if game.get("result") == "抢杠" else "点炮"
        return "%s 胡 %s（%s%s）%s" % (names, tile, src, verb, fan_txt)
    if game.get("result") == "流局":
        return "流局"
    return game.get("result") or "流局"


def save_game(game):
    GAMES_DIR.mkdir(parents=True, exist_ok=True)
    path = GAMES_DIR / ("%s.json" % game["id"])
    path.write_text(json.dumps(game, ensure_ascii=False, indent=2), encoding="utf-8")
    index = list_games()
    index = [row for row in index if row.get("id") != game["id"]]
    index.insert(0, {
        "id": game["id"],
        "created": game.get("created"),
        "result": game.get("result"),
        "winner": game.get("winner"),
        "n_discard": game.get("n_discard"),
        "text": result_text(game),
    })
    INDEX_PATH.write_text(json.dumps(index[:80], ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def list_games():
    if not INDEX_PATH.exists():
        return []
    try:
        data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(data, list):
        return data
    return []


def load_game(gid):
    path = GAMES_DIR / ("%s.json" % gid)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv=None):
    import argparse
    import sys

    from train.view import render_game
    from train.table import play_events

    parser = argparse.ArgumentParser(description="Four robots play one mahjong game")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)
    game = play_game(seed=args.seed)
    save_game(game)
    text = render_game(play_events(game["events"]))
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
    sys.stdout.write(text)
    sys.stdout.write("id=%s result=%s discards=%s\n" % (game["id"], result_text(game), game["n_discard"]))


if __name__ == "__main__":
    main()
