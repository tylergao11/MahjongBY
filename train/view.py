# -*- coding: utf-8 -*-
"""Text table for reviewing four-seat play order, hands, and discards.

Usage:
  python -m train.view            first fxj game
  python -m train.view 0          same
  python -m train.view 274373     one gamb_id
  python -m train.view demo        four-robot sample
  python -m train.view --every 274373
  python -m train.view --events path.json

Robot later: dump the same event list the table already understands.
{"events":[
  {"op":"deal","dealer":1,"names":{"1":"机器人1","2":"机器人2","3":"机器人3","4":"机器人4"},
   "hands":{"1":["1万",...],"2":[...],"3":[...],"4":[...]}},
  {"op":"discard","seat":1,"tile":"中"},
  {"op":"draw","seat":2,"tile":"9万"},
  {"op":"discard","seat":2,"tile":"发"},
  {"op":"peng","seat":4,"tile":"发"},
  {"op":"discard","seat":4,"tile":"白"}
]}
"""
import argparse
import json
import sys
from pathlib import Path

from train.table import (
    SEATS,
    format_melds,
    format_river,
    format_tiles,
    fxj_to_events,
    parse_tile,
    parse_tile_list,
    play_events,
    shanten_label,
    sort_tiles,
)
from train.tiles import tile_name

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "fxj.jsonl"
DEFAULT_OUT = ROOT / "models" / "view_last.txt"


def _stdio_utf8():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


def demo_events():
    return [
        {
            "op": "deal",
            "dealer": 1,
            "gamb_id": "demo",
            "room_level": "bot",
            "names": {1: "机器人1", 2: "机器人2", 3: "机器人3", 4: "机器人4"},
            "hands": {
                1: ["1万", "2万", "3万", "4万", "5万", "6万", "7万", "8万", "9万", "东", "东", "东", "中", "北"],
                2: ["1条", "2条", "3条", "4条", "5条", "6条", "7条", "8条", "9条", "南", "南", "南", "发"],
                3: ["1筒", "2筒", "3筒", "4筒", "5筒", "6筒", "7筒", "8筒", "9筒", "西", "西", "西", "7条"],
                4: ["2万", "3万", "4万", "5万", "6万", "7万", "8万", "1筒", "2筒", "3筒", "发", "发", "白"],
            },
        },
        {"op": "discard", "seat": 1, "tile": "中"},
        {"op": "draw", "seat": 2, "tile": "9万"},
        {"op": "discard", "seat": 2, "tile": "发"},
        {"op": "peng", "seat": 4, "tile": "发"},
        {"op": "discard", "seat": 4, "tile": "白"},
        {"op": "draw", "seat": 1, "tile": "1条"},
        {"op": "discard", "seat": 1, "tile": "北"},
        {"op": "draw", "seat": 2, "tile": "2条"},
        {"op": "discard", "seat": 2, "tile": "南"},
        {"op": "draw", "seat": 3, "tile": "8万"},
        {"op": "discard", "seat": 3, "tile": "西"},
        {"op": "end"},
    ]


def render_board(table, compact=False):
    lines = []
    for seat in SEATS:
        dealer = "庄" if seat == table.dealer else "  "
        label = shanten_label(table.hands[seat], table.n_melds[seat])
        name = table.seat_name(seat)
        hand_tiles = list(table.hands[seat])
        drawn_txt = ""
        if getattr(table, "last_draw_seat", None) == seat and table.last_draw_tile in hand_tiles:
            hand_tiles.remove(table.last_draw_tile)
            drawn_txt = "  刚抓  %s" % tile_name(table.last_draw_tile)
        hand = format_tiles(hand_tiles)
        meld = format_melds(table.melds[seat])
        river = format_river(table.rivers[seat], table.river_called[seat])
        if compact:
            lines.append(
                "%s %s %s  手:%s%s  副:%s  河:%s" % (name, dealer, label, hand, drawn_txt, meld, river)
            )
        else:
            lines.append("%s %s %s" % (name, dealer, label))
            lines.append("  手牌  %s%s" % (hand, drawn_txt))
            lines.append("  副露  %s" % meld)
            lines.append("  打牌  %s" % river)
    return "\n".join(lines)


def _header(table):
    bits = ["局"]
    if table.gamb_id is not None:
        bits.append("gamb=%s" % table.gamb_id)
    if table.room_level is not None:
        bits.append("房间%s" % table.room_level)
    bits.append("庄%s" % table.seat_name(table.dealer))
    if table.dice:
        bits.append("骰%s" % table.dice)
    if table.wall_left is not None:
        bits.append("牌墙%s" % table.wall_left)
    return " ".join(bits)


def _legal_text(step, table):
    legal = step.get("legal") or {}
    if not legal:
        return ""
    parts = []
    for seat in SEATS:
        names = legal.get(seat) or legal.get(str(seat))
        if names:
            parts.append("%s可%s" % (table.seat_name(seat), "/".join(names)))
    if not parts:
        return ""
    return "[" + " ".join(parts) + "]"


def _is_call(op):
    return op in ("chi", "吃", "吃高", "吃中", "吃低", "peng", "碰", "gang", "ming_gang", "明杠", "an_gang", "暗杠", "hu", "胡", "自摸")


def _tile_of(step):
    tile = parse_tile(step.get("tile"))
    if tile is not None:
        return tile_name(tile)
    tiles = parse_tile_list(step.get("tiles"))
    if tiles:
        return format_tiles(tiles).replace(" ", "")
    return ""


def _merged_actions(steps):
    rows = []
    i = 0
    seq = 1
    n = len(steps)
    while i < n:
        step = steps[i]
        op = str(step.get("op") or "")
        if op in ("deal", "end", "终局"):
            i += 1
            continue
        board = step.get("board")
        nxt = steps[i + 1] if i + 1 < n else None
        nxt_op = str((nxt or {}).get("op") or "")
        name = board.seat_name(step["seat"]) if step.get("seat") is not None else ""

        if op in ("draw", "摸"):
            line = "%3d %s 摸 %s" % (seq, name, _tile_of(step))
            rows.append((line, step))
            i += 1
            seq += 1
            continue

        if op in ("discard", "打", "出牌"):
            line = "%3d %s 打 %s" % (seq, name, _tile_of(step))
            line = _with_legal(line, step, steps, i)
            rows.append((line, step))
            i += 1
            seq += 1
            continue

        if op in ("chi", "吃", "吃高", "吃中", "吃低", "peng", "碰", "gang", "ming_gang", "明杠", "an_gang", "暗杠"):
            verb = {
                "chi": "吃",
                "peng": "碰",
                "gang": "明杠",
                "ming_gang": "明杠",
                "an_gang": "暗杠",
            }.get(op, op)
            if step.get("kind"):
                verb = step["kind"]
            body = _tile_of(step)
            line = "%3d %s %s %s" % (seq, name, verb, body)
            if nxt and nxt_op in ("discard", "打", "出牌") and nxt.get("seat") == step.get("seat"):
                line += " 打 %s" % _tile_of(nxt)
                line = _with_legal(line, nxt, steps, i + 1)
                rows.append((line, nxt))
                i += 2
            else:
                rows.append((line, step))
                i += 1
            seq += 1
            continue

        if op in ("hu", "胡", "自摸"):
            if step.get("zimo") or op == "自摸":
                line = "%3d %s 自摸 %s" % (seq, name, _tile_of(step))
            else:
                from_seat = step.get("from_seat")
                from_name = board.seat_name(from_seat) if from_seat else "?"
                line = "%3d %s 胡 %s （%s点炮）" % (seq, name, _tile_of(step), from_name)
            rows.append((line, step))
            i += 1
            seq += 1
            continue

        i += 1
    return rows


def _with_legal(line, discard_step, steps, idx):
    board = discard_step.get("board")
    text = _legal_text(discard_step, board)
    nxt = steps[idx + 1] if idx + 1 < len(steps) else None
    nxt_op = str((nxt or {}).get("op") or "")
    if text:
        line += "  " + text
        if not _is_call(nxt_op):
            line += "  过"
    if discard_step.get("missing"):
        line += "  !手牌缺这张"
    return line


def render_game(steps, every=False):
    if not steps:
        return "(空对局)"
    first = steps[0].get("board") or steps[-1]["board"]
    last = steps[-1]["board"]
    lines = [
        "================================================",
        _header(first),
        "河中 * 表示这张被吃碰杠拿走",
        "================================================",
        "",
        "【开局】",
        render_board(first),
        "",
        "【顺序】",
    ]
    for line, step in _merged_actions(steps):
        lines.append(line)
        if every:
            lines.append(render_board(step["board"], compact=True))
            lines.append("")
    lines.extend(["", "【终局】"])
    if last.winner:
        if last.zimo:
            lines.append("胡牌 %s 自摸 %s" % (last.seat_name(last.winner), tile_name(last.hu_tile) if last.hu_tile else ""))
        else:
            src = last.seat_name(last.from_seat) if last.from_seat else "?"
            lines.append(
                "胡牌 %s 胡 %s （%s点炮）"
                % (last.seat_name(last.winner), tile_name(last.hu_tile) if last.hu_tile else "", src)
            )
    lines.append(render_board(last))
    return "\n".join(lines) + "\n"


def _tile_kind(name):
    if name == "妖姬":
        return "laizi"
    if name.endswith("万"):
        return "wan"
    if name.endswith("条"):
        return "tiao"
    if name.endswith("筒"):
        return "tong"
    return "honor"


def serialize_opens(melds):
    out = []
    for meld in melds or []:
        kind = str(meld.get("kind") or "副露")
        if "杠" in kind:
            family = "gang"
        elif "碰" in kind:
            family = "peng"
        else:
            family = "chi"
        tiles = []
        for tile in meld.get("tiles") or []:
            name = tile_name(tile)
            tiles.append({"name": name, "kind": _tile_kind(name)})
        out.append({"kind": kind, "family": family, "tiles": tiles})
    return out


def serialize_seat(table, seat):
    river = []
    for i, tile in enumerate(table.rivers[seat]):
        name = tile_name(tile)
        river.append({"name": name, "called": i in table.river_called[seat], "kind": _tile_kind(name)})
    tiles = list(table.hands[seat])
    drawn = None
    if getattr(table, "last_draw_seat", None) == seat and table.last_draw_tile in tiles:
        tiles.remove(table.last_draw_tile)
        name = tile_name(table.last_draw_tile)
        drawn = {"name": name, "kind": _tile_kind(name), "drawn": True}
    hand = []
    for tile in sort_tiles(tiles):
        name = tile_name(tile)
        hand.append({"name": name, "kind": _tile_kind(name)})
    if drawn:
        hand.append(drawn)
    return {
        "seat": seat,
        "name": table.seat_name(seat),
        "dealer": seat == table.dealer,
        "shanten": shanten_label(table.hands[seat], table.n_melds[seat]),
        "hand": hand,
        "drawn": drawn,
        "melds": format_melds(table.melds[seat]),
        "opens": serialize_opens(table.melds[seat]),
        "river": river,
    }


def public_payload(events):
    steps = play_events(events)
    if not steps:
        return {"header": "", "frames": [], "log": []}
    first = steps[0]["board"]
    frames = [{
        "line": "开局",
        "seats": [serialize_seat(first, seat) for seat in SEATS],
        "wall": first.wall_left,
        "last_discard_seat": None,
        "last_draw_seat": first.last_draw_seat,
    }]
    log = []
    for line, step in _merged_actions(steps):
        board = step["board"]
        text = line.strip()
        log.append(text)
        frames.append({
            "line": text,
            "seats": [serialize_seat(board, seat) for seat in SEATS],
            "wall": board.wall_left,
            "last_discard_seat": board.last_discard_seat,
            "last_draw_seat": board.last_draw_seat,
        })
    last = steps[-1]["board"]
    return {
        "header": _header(first),
        "frames": frames,
        "log": log,
        "end_seats": [serialize_seat(last, seat) for seat in SEATS],
        "winner": last.winner,
        "zimo": last.zimo,
        "wall_left": last.wall_left,
    }


def load_fxj_game(pick="0"):
    if not DATA.exists():
        raise FileNotFoundError("missing %s" % DATA)
    want_id = None
    want_index = 0
    text = str(pick)
    if text.isdigit():
        num = int(text)
        if num >= 10000:
            want_id = num
        else:
            want_index = num
    elif text:
        want_id = text
    with DATA.open("r", encoding="utf-8") as handle:
        for i, line in enumerate(handle):
            if not line.strip():
                continue
            game = json.loads(line)
            if want_id is not None:
                if str(game.get("gamb_id")) == str(want_id):
                    return game
            elif i == want_index:
                return game
    raise ValueError("game not found: %s" % pick)


def load_events_file(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    events = list(data.get("events") or [])
    names = data.get("names")
    if names and events and events[0].get("op") == "deal":
        merged = dict(events[0])
        merged.setdefault("names", names)
        events[0] = merged
    return events


def build_text(pick="0", every=False, events_path=""):
    if events_path:
        steps = play_events(load_events_file(events_path))
    elif str(pick) == "demo":
        steps = play_events(demo_events())
    else:
        steps = play_events(fxj_to_events(load_fxj_game(pick)))
    return render_game(steps, every=every)


def main(argv=None):
    _stdio_utf8()
    parser = argparse.ArgumentParser(description="Four-seat mahjong text view")
    parser.add_argument("pick", nargs="?", default="0", help="demo | index | gamb_id")
    parser.add_argument("--every", action="store_true", help="print board after each action")
    parser.add_argument("--events", default="", help="robot/event json path")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="utf-8 output file")
    parser.add_argument("--no-save", action="store_true")
    args = parser.parse_args(argv)
    text = build_text(pick=args.pick, every=args.every, events_path=args.events)
    if not args.no_save:
        out = Path(args.out)
        if not out.is_absolute():
            out = ROOT / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    if not args.no_save:
        sys.stdout.write("wrote=%s\n" % (Path(args.out) if Path(args.out).is_absolute() else ROOT / args.out))


if __name__ == "__main__":
    main()
