# -*- coding: utf-8 -*-
"""Four-seat table state. Replay fxj ops or robot event lists into the same log."""
from train.replay import (
    _chi_needed,
    _modal_tile,
    _take,
    legal_call_mask,
    parse_ops,
    parse_tiles,
)
from train.shanten import shanten
from train.tiles import (
    CALL_NAMES,
    CODE_TO_CALL,
    TILE_IDS,
    TILE_NAMES,
    TILE_NAME_ALIASES,
    tile_name,
)

SEATS = (1, 2, 3, 4)
NAME_TO_TILE = {name: tid for tid, name in TILE_NAMES.items()}
NAME_TO_TILE.update(TILE_NAME_ALIASES)
_TILE_ORDER = {tid: i for i, tid in enumerate(TILE_IDS)}
CHI_KIND = {
    "吃高": "high",
    "吃中": "mid",
    "吃低": "low",
    "high": "high",
    "mid": "mid",
    "low": "low",
}
KIND_LABEL = {
    "chi": "吃",
    "peng": "碰",
    "gang": "明杠",
    "ming_gang": "明杠",
    "an_gang": "暗杠",
    "吃": "吃",
    "吃高": "吃高",
    "吃中": "吃中",
    "吃低": "吃低",
    "碰": "碰",
    "明杠": "明杠",
    "暗杠": "暗杠",
}


def parse_tile(val):
    if val is None or val == "":
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        return int(val)
    text = str(val).strip()
    if text.isdigit():
        return int(text)
    return NAME_TO_TILE.get(text)


def parse_tile_list(vals):
    if vals is None:
        return []
    if isinstance(vals, str):
        if "," in vals:
            vals = vals.split(",")
        else:
            vals = vals.split()
    out = []
    for item in vals:
        tile = parse_tile(item)
        if tile is not None:
            out.append(tile)
    return out


def sort_tiles(tiles):
    return sorted(list(tiles), key=lambda t: _TILE_ORDER.get(int(t), 100))


def format_tiles(tiles):
    if not tiles:
        return "(空)"
    return " ".join(tile_name(t) for t in sort_tiles(tiles))


def format_melds(melds):
    if not melds:
        return "(空)"
    parts = []
    for meld in melds:
        kind = KIND_LABEL.get(meld.get("kind"), meld.get("kind") or "副露")
        tiles = meld.get("tiles") or []
        if tiles and len(set(tiles)) == 1:
            parts.append(kind + tile_name(tiles[0]))
        else:
            parts.append(kind + format_tiles(tiles).replace(" ", ""))
    return " ".join(parts)


def format_river(tiles, called=None):
    if not tiles:
        return "(空)"
    called = called or set()
    parts = []
    for i, tile in enumerate(tiles):
        name = tile_name(tile)
        parts.append(name + "*" if i in called else name)
    return " ".join(parts)


def shanten_label(hand, n_melds=0):
    value = shanten(hand, n_melds=n_melds)
    if value < 0:
        return "和"
    if value == 0:
        return "听"
    return "向听%s" % value


class Table:
    def __init__(self):
        self.reset()

    def reset(self):
        self.hands = {seat: [] for seat in SEATS}
        self.rivers = {seat: [] for seat in SEATS}
        self.river_called = {seat: set() for seat in SEATS}
        self.melds = {seat: [] for seat in SEATS}
        self.n_melds = {seat: 0 for seat in SEATS}
        self.dealer = 1
        self.names = {seat: "座%s" % seat for seat in SEATS}
        self.last_discard = None
        self.last_discard_seat = None
        self.last_draw_seat = None
        self.last_draw_tile = None
        self.wall_left = None
        self.gamb_id = None
        self.room_level = None
        self.dice = None
        self.winner = None
        self.winners = []
        self.hu_tile = None
        self.zimo = False
        self.from_seat = None
        self.ended = False
        self.last_fan = None

    def copy(self):
        other = Table()
        other.hands = {seat: list(self.hands[seat]) for seat in SEATS}
        other.rivers = {seat: list(self.rivers[seat]) for seat in SEATS}
        other.river_called = {seat: set(self.river_called[seat]) for seat in SEATS}
        other.melds = {
            seat: [{"kind": m["kind"], "tiles": list(m.get("tiles") or [])} for m in self.melds[seat]]
            for seat in SEATS
        }
        other.n_melds = dict(self.n_melds)
        other.dealer = self.dealer
        other.names = dict(self.names)
        other.last_discard = self.last_discard
        other.last_discard_seat = self.last_discard_seat
        other.last_draw_seat = self.last_draw_seat
        other.last_draw_tile = self.last_draw_tile
        other.wall_left = self.wall_left
        other.gamb_id = self.gamb_id
        other.room_level = self.room_level
        other.dice = self.dice
        other.winner = self.winner
        other.winners = list(self.winners)
        other.hu_tile = self.hu_tile
        other.zimo = self.zimo
        other.from_seat = self.from_seat
        other.ended = self.ended
        other.last_fan = self.last_fan
        return other

    def seat_name(self, seat):
        return self.names.get(int(seat), "座%s" % seat)

    def legal_calls(self, offer, offer_seat):
        out = {}
        for seat in SEATS:
            if seat == offer_seat:
                continue
            mask = legal_call_mask(
                self.hands[seat], offer, offer_seat, seat, own_turn=False, n_melds=self.n_melds[seat],
            )
            names = [CALL_NAMES[i] for i in range(1, len(mask)) if mask[i]]
            if names:
                out[seat] = names
        return out

    def mark_called(self):
        seat = self.last_discard_seat
        tile = self.last_discard
        if seat not in self.rivers or tile is None:
            return
        river = self.rivers[seat]
        for i in range(len(river) - 1, -1, -1):
            if river[i] == tile:
                self.river_called[seat].add(i)
                break


def _norm_names(raw):
    if not raw:
        return {}
    out = {}
    for key, val in dict(raw).items():
        try:
            out[int(key)] = str(val)
        except (TypeError, ValueError):
            continue
    return out


def _norm_hands(raw):
    out = {}
    for key, val in dict(raw or {}).items():
        try:
            seat = int(key)
        except (TypeError, ValueError):
            continue
        out[seat] = parse_tile_list(val)
    return out


def apply_event(table, event):
    extra = {}
    op = str(event.get("op") or "").strip()
    seat = event.get("seat")
    if seat is not None and seat != "":
        seat = int(seat)
    tile = parse_tile(event.get("tile"))
    tiles = parse_tile_list(event.get("tiles"))

    if op == "deal":
        table.reset()
        names = _norm_names(event.get("names"))
        if names:
            table.names.update(names)
        hands = _norm_hands(event.get("hands"))
        for s in SEATS:
            table.hands[s] = list(hands.get(s) or [])
        dealer = event.get("dealer")
        table.dealer = int(dealer) if dealer else 1
        if event.get("gamb_id") is not None:
            table.gamb_id = event.get("gamb_id")
        if event.get("room_level") is not None:
            table.room_level = event.get("room_level")
        if event.get("dice") is not None:
            table.dice = event.get("dice")
        if event.get("wall_left") is not None:
            table.wall_left = int(event.get("wall_left"))
        dealer_hand = table.hands.get(table.dealer) or []
        if len(dealer_hand) >= 14:
            table.last_draw_seat = table.dealer
            table.last_draw_tile = dealer_hand[-1]
        else:
            table.last_draw_seat = None
            table.last_draw_tile = None
        return extra

    if op in ("draw", "摸"):
        if seat in table.hands and tile is not None:
            table.hands[seat].append(tile)
            if table.wall_left is not None:
                table.wall_left = max(0, table.wall_left - 1)
            table.last_draw_seat = seat
            table.last_draw_tile = tile
            extra["tile"] = tile
        return extra

    if op in ("discard", "打", "出牌"):
        if seat in table.hands and tile is not None:
            if tile in table.hands[seat]:
                table.hands[seat].remove(tile)
            else:
                extra["missing"] = 1
            table.rivers[seat].append(tile)
            table.last_discard = tile
            table.last_discard_seat = seat
            table.last_draw_seat = None
            table.last_draw_tile = None
            extra["tile"] = tile
            extra["legal"] = table.legal_calls(tile, seat)
        return extra

    if op in ("chi", "吃", "吃高", "吃中", "吃低"):
        kind = event.get("kind") or (op if op in CHI_KIND else "吃")
        chi_key = CHI_KIND.get(kind)
        offer = table.last_discard
        if not tiles and chi_key and offer is not None:
            tiles = _chi_needed(offer, chi_key) + [offer]
        from_hand = list(tiles)
        if offer in from_hand:
            from_hand.remove(offer)
        if seat in table.hands:
            _take(table.hands[seat], from_hand[:2])
            table.melds[seat].append({"kind": KIND_LABEL.get(kind, "吃"), "tiles": tiles or from_hand})
            table.n_melds[seat] += 1
            table.mark_called()
        table.last_discard = None
        table.last_discard_seat = None
        table.last_draw_seat = None
        table.last_draw_tile = None
        extra["kind"] = KIND_LABEL.get(kind, "吃")
        extra["tiles"] = tiles
        return extra

    if op in ("peng", "碰"):
        use = tile or _modal_tile(tiles) or table.last_discard
        if seat in table.hands and use is not None:
            _take(table.hands[seat], [use, use])
            table.melds[seat].append({"kind": "碰", "tiles": [use, use, use]})
            table.n_melds[seat] += 1
            table.mark_called()
        table.last_discard = None
        table.last_discard_seat = None
        table.last_draw_seat = None
        table.last_draw_tile = None
        extra["tile"] = use
        return extra

    if op in ("gang", "ming_gang", "明杠"):
        use = tile or _modal_tile(tiles) or table.last_discard
        if seat in table.hands and use is not None:
            need = 3 if table.last_discard == use else 4
            _take(table.hands[seat], [use] * need)
            table.melds[seat].append({"kind": "明杠", "tiles": [use, use, use, use]})
            table.n_melds[seat] += 1
            table.mark_called()
        table.last_discard = None
        table.last_discard_seat = None
        table.last_draw_seat = None
        table.last_draw_tile = None
        extra["tile"] = use
        return extra

    if op in ("an_gang", "暗杠"):
        use = tile or _modal_tile(tiles)
        if seat in table.hands and use is not None:
            _take(table.hands[seat], [use] * 4)
            table.melds[seat].append({"kind": "暗杠", "tiles": [use, use, use, use]})
            table.n_melds[seat] += 1
        table.last_draw_seat = None
        table.last_draw_tile = None
        extra["tile"] = use
        return extra

    if op in ("hu", "胡", "自摸"):
        zimo = bool(event.get("zimo") or op == "自摸")
        from_seat = event.get("from_seat")
        if from_seat is not None and from_seat != "":
            from_seat = int(from_seat)
        else:
            from_seat = None if zimo else table.last_discard_seat
        use = tile
        if use is None:
            use = table.last_discard if not zimo else None
        if seat in table.hands and use is not None and not zimo:
            table.hands[seat].append(use)
            table.mark_called()
        if zimo and seat in table.hands:
            keep = use if use is not None else (table.hands[seat][-1] if table.hands[seat] else None)
            if keep is not None:
                table.last_draw_seat = seat
                table.last_draw_tile = keep
        table.winner = seat
        table.winners = list(getattr(table, "winners", None) or [])
        if seat not in table.winners:
            table.winners.append(seat)
        table.hu_tile = use
        table.zimo = zimo
        table.from_seat = from_seat
        table.ended = True
        table.last_fan = event.get("fan")
        extra["tile"] = use
        extra["zimo"] = zimo
        extra["from_seat"] = from_seat
        return extra

    if op in ("end", "终局"):
        table.ended = True
        return extra
    extra["unknown"] = op
    return extra


def play_events(events):
    table = Table()
    steps = []
    for raw in events or []:
        event = dict(raw)
        extra = apply_event(table, event)
        step = dict(event)
        step.update(extra)
        step["board"] = table.copy()
        steps.append(step)
    return steps


def fxj_to_events(game):
    ops = parse_ops(game.get("ops") or "")
    dealer = 1
    names = {}
    dice = None
    hands = {}
    wall_left = None
    events = []
    dealt = False

    def ensure_deal():
        nonlocal dealt
        if dealt:
            return
        events.append({
            "op": "deal",
            "dealer": dealer,
            "hands": {seat: list(hands.get(seat) or []) for seat in SEATS},
            "names": names,
            "dice": dice,
            "gamb_id": game.get("gamb_id"),
            "room_level": game.get("room_level"),
            "wall_left": wall_left,
        })
        dealt = True

    for op in ops:
        code = op["code"]
        seat = op["seat"]
        tiles = op["tiles"]
        if code == "111" and ":" in (op["payload"] or ""):
            users = (op["payload"].split(":", 1)[1] or "").split(",")
            for i, uid in enumerate(users[:4]):
                uid = uid.strip()
                if uid:
                    names[i + 1] = "座%s %s" % (i + 1, uid)
        elif code == "112" and op["seat"]:
            dealer = int(op["seat"])
        elif code == "113":
            dice = op["payload"]
        elif code == "115" and ":" in (op["payload"] or ""):
            parts = op["payload"].split(":")
            if len(parts) >= 4:
                hands = {s: parse_tiles(parts[s - 1]) for s in SEATS}
            if len(parts) >= 5:
                wall_left = len(parse_tiles(parts[4]))
        elif code == "119":
            ensure_deal()
        elif code == "100" and seat and tiles:
            ensure_deal()
            events.append({"op": "draw", "seat": seat, "tile": tiles[0]})
        elif code == "10001" and seat and tiles:
            ensure_deal()
            events.append({"op": "discard", "seat": seat, "tile": tiles[0]})
        elif code in ("1001", "1002", "1003") and seat:
            ensure_deal()
            events.append({
                "op": "chi",
                "seat": seat,
                "tiles": tiles,
                "kind": CALL_NAMES[CODE_TO_CALL[code]],
            })
        elif code == "2001" and seat:
            ensure_deal()
            events.append({"op": "peng", "seat": seat, "tiles": tiles, "tile": _modal_tile(tiles)})
        elif code == "3001" and seat:
            ensure_deal()
            events.append({"op": "gang", "seat": seat, "tiles": tiles, "tile": _modal_tile(tiles)})
        elif code == "3003" and seat:
            ensure_deal()
            events.append({"op": "an_gang", "seat": seat, "tiles": tiles, "tile": _modal_tile(tiles)})
        elif code == "4004" and seat:
            ensure_deal()
            events.append({"op": "hu", "seat": seat, "tile": tiles[0] if tiles else None, "zimo": True})
        elif code == "4001" and seat:
            ensure_deal()
            events.append({
                "op": "hu",
                "seat": seat,
                "tile": tiles[0] if tiles else None,
                "zimo": False,
            })
        elif code == "199":
            ensure_deal()
            events.append({"op": "end"})
    if not dealt:
        ensure_deal()
    return events
