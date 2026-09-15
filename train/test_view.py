# -*- coding: utf-8 -*-
from pathlib import Path

from train.table import apply_event, format_tiles, fxj_to_events, play_events
from train.view import build_text, demo_events, public_payload, render_game
from train.web import TableServer

ROOT = Path(__file__).resolve().parent.parent


def test_format_tiles():
    assert format_tiles([65, 17, 1, 1]) == "1万 1万 妖姬 中"


def test_peng_updates_hand_and_river():
    events = [
        {
            "op": "deal",
            "dealer": 1,
            "hands": {
                1: ["1万", "2万", "3万", "4万", "5万", "6万", "7万", "8万", "9万", "东", "东", "东", "中", "白"],
                2: ["1条", "2条", "3条", "4条", "5条", "6条", "7条", "8条", "9条", "南", "南", "南", "发"],
                3: ["1筒", "2筒", "3筒", "4筒", "5筒", "6筒", "7筒", "8筒", "9筒", "西", "西", "西", "北"],
                4: ["2万", "3万", "4万", "5万", "6万", "7万", "8万", "1筒", "2筒", "3筒", "发", "发", "白"],
            },
        },
        {"op": "discard", "seat": 1, "tile": "中"},
        {"op": "draw", "seat": 2, "tile": "9万"},
        {"op": "discard", "seat": 2, "tile": "发"},
        {"op": "peng", "seat": 4, "tile": "发"},
        {"op": "discard", "seat": 4, "tile": "白"},
    ]
    steps = play_events(events)
    board = steps[-1]["board"]
    assert "发" not in [str(x) for x in board.hands[4]] or board.hands[4].count(66) == 0
    assert board.hands[4].count(66) == 0
    assert board.melds[4][0]["kind"] == "碰"
    assert 0 in board.river_called[2] or (len(board.rivers[2]) - 1) in board.river_called[2]
    assert board.rivers[1][0] == 65
    assert board.rivers[4][-1] == 67


def test_pass_marked_when_chi_available():
    events = [
        {
            "op": "deal",
            "dealer": 1,
            "names": {1: "座1", 2: "座2", 3: "座3", 4: "座4"},
            "hands": {
                1: ["3万", "9万", "9万", "9万", "东", "东", "东", "南", "南", "南", "西", "西", "西", "中"],
                2: ["1万", "2万", "1条", "2条", "3条", "4条", "5条", "6条", "7条", "8条", "9条", "北", "北"],
                3: ["1筒", "2筒", "3筒", "4筒", "5筒", "6筒", "7筒", "8筒", "9筒", "白", "白", "发", "发"],
                4: ["1条", "1条", "1筒", "2筒", "3筒", "4筒", "5筒", "6筒", "7筒", "8筒", "9筒", "白", "发"],
            },
        },
        {"op": "discard", "seat": 1, "tile": "3万"},
        {"op": "draw", "seat": 2, "tile": "9筒"},
        {"op": "discard", "seat": 2, "tile": "北"},
    ]
    text = render_game(play_events(events))
    assert "打 3万" in text
    assert "可吃" in text
    assert "过" in text


def test_demo_has_four_hands_and_order():
    text = render_game(play_events(demo_events()))
    assert "机器人1" in text and "机器人4" in text
    assert "手牌" in text and "打牌" in text
    assert "打 中" in text
    assert "碰 发" in text
    assert "【顺序】" in text
    assert "【终局】" in text
    north = text.index("打 北")
    assert "机器人2 摸 2条" in text[north:]


def test_fxj_real_game():
    text = build_text("0", every=False)
    assert "手牌" in text
    assert "打牌" in text
    assert "座1" in text
    assert "打 " in text
    assert "【顺序】" in text


def test_events_json_roundtrip(tmp_path):
    path = tmp_path / "bot.json"
    path.write_text(
        '{"names":{"1":"机器人1","2":"机器人2","3":"机器人3","4":"机器人4"},'
        '"events":[{"op":"deal","dealer":1,"hands":{"1":["1万","2万","3万","4万","5万","6万","7万","8万","9万","东","东","东","中","白"],'
        '"2":["1条"],"3":["1筒"],"4":["发"]}},{"op":"discard","seat":1,"tile":"中"},{"op":"end"}]}',
        encoding="utf-8",
    )
    text = build_text(events_path=str(path))
    assert "机器人1" in text
    assert "打 中" in text


def test_utf8_output_no_bom():
    out = ROOT / "models" / "view_demo.txt"
    text = build_text("demo")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    raw = out.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    decoded = raw.decode("utf-8")
    assert "\ufffd" not in decoded
    assert "手牌" in decoded
    assert "机器人1" in decoded


def test_apply_unknown_is_safe():
    from train.table import Table

    table = Table()
    extra = apply_event(table, {"op": "noop"})
    assert extra.get("unknown") == "noop"


def test_index_has_step_and_center_river():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "上一步" in html
    assert "下一步" in html
    assert "data-river" in html
    assert "立刻看完" in html
    assert "碰杠" in html
    assert "seat-body" in html
    assert "刚抓" in html
    assert "drawn-wrap" in html
    assert "laizi" in html


def test_payload_rivers_and_last_discard():
    payload = public_payload(demo_events())
    assert payload["frames"][0]["line"] == "开局"
    assert payload["frames"][0]["last_discard_seat"] is None
    found = None
    for frame in payload["frames"]:
        if frame.get("last_discard_seat") == 1:
            found = frame
            break
    assert found is not None
    seat1 = [s for s in found["seats"] if s["seat"] == 1][0]
    assert seat1["river"]
    assert seat1["river"][0]["name"] == "中"


def test_payload_peng_on_side():
    payload = public_payload(demo_events())
    last = payload["frames"][-1]
    seat4 = [s for s in last["seats"] if s["seat"] == 4][0]
    assert seat4["opens"]
    assert seat4["opens"][0]["family"] == "peng"
    assert seat4["opens"][0]["kind"] == "碰"
    assert len(seat4["opens"][0]["tiles"]) == 3
    assert seat4["opens"][0]["tiles"][0]["name"] == "发"
    assert len(seat4["hand"]) == 10


def test_payload_drawn_in_hand():
    payload = public_payload(demo_events())
    opening = payload["frames"][0]
    seat1 = [s for s in opening["seats"] if s["seat"] == 1][0]
    assert seat1["drawn"]["name"] == "北"
    assert seat1["hand"][-1]["drawn"] is True
    assert seat1["hand"][-1]["name"] == "北"
    assert len(seat1["hand"]) == 14
    seat2 = [s for s in opening["seats"] if s["seat"] == 2][0]
    assert seat2["drawn"] is None
    assert len(seat2["hand"]) == 13
    draw = None
    for frame in payload["frames"]:
        if "摸 9万" in frame["line"]:
            draw = frame
            break
    assert draw is not None
    assert "打" not in draw["line"]
    seat2 = [s for s in draw["seats"] if s["seat"] == 2][0]
    assert seat2["drawn"]["name"] == "9万"
    assert seat2["hand"][-1]["name"] == "9万"
    assert seat2["hand"][-1]["drawn"] is True
    assert len(seat2["hand"]) == 14
    after = None
    for frame in payload["frames"]:
        if "打 发" in frame["line"]:
            after = frame
            break
    assert after is not None
    seat2 = [s for s in after["seats"] if s["seat"] == 2][0]
    assert seat2["drawn"] is None
    assert len(seat2["hand"]) == 13


def test_web_server_does_not_reuse_port():
    assert TableServer.allow_reuse_address is False


def test_fxj_events_not_empty():
    import json

    line = (ROOT / "fxj.jsonl").open("r", encoding="utf-8").readline()
    game = json.loads(line)
    events = fxj_to_events(game)
    ops = [e["op"] for e in events]
    assert events[0]["op"] == "deal"
    assert "discard" in ops
    assert len(events[0]["hands"][1]) == 14


if __name__ == "__main__":
    test_format_tiles()
    test_peng_updates_hand_and_river()
    test_pass_marked_when_chi_available()
    test_demo_has_four_hands_and_order()
    test_fxj_real_game()
    from pathlib import Path as _P
    import tempfile
    import shutil

    tmp = _P(tempfile.mkdtemp())
    try:
        test_events_json_roundtrip(tmp)
    finally:
        shutil.rmtree(tmp)
    test_utf8_output_no_bom()
    test_apply_unknown_is_safe()
    test_index_has_step_and_center_river()
    test_payload_rivers_and_last_discard()
    test_payload_peng_on_side()
    test_payload_drawn_in_hand()
    test_web_server_does_not_reuse_port()
    test_fxj_events_not_empty()
    print("view tests ok")
