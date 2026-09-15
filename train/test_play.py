# -*- coding: utf-8 -*-
from train.play import play_game, result_text
from train.view import public_payload


def test_play_seed_has_four_robots_and_discards():
    game = play_game(seed=7)
    assert game["events"][0]["op"] == "deal"
    hands = game["events"][0]["hands"]
    dealer = game["events"][0]["dealer"]
    assert len(hands[dealer]) == 14
    for seat in (1, 2, 3, 4):
        assert seat == dealer or len(hands[seat]) == 13
        assert game["events"][0]["names"][seat].startswith("机器人")
    assert any(e.get("op") == "discard" for e in events_of(game))
    assert game["events"][-1]["op"] == "end"
    assert game["result"] in ("流局", "自摸", "点炮")
    assert game["n_discard"] >= 1


def events_of(game):
    return game["events"]


def test_same_seed_same_opening():
    a = play_game(seed=11)
    b = play_game(seed=11)
    assert a["events"][0]["dealer"] == b["events"][0]["dealer"]
    assert a["events"][0]["hands"] == b["events"][0]["hands"]
    first_a = next(e for e in a["events"] if e.get("op") == "discard")
    first_b = next(e for e in b["events"] if e.get("op") == "discard")
    assert first_a["tile"] == first_b["tile"]
    assert first_a["seat"] == first_b["seat"]


def test_payload_has_frames():
    game = play_game(seed=7)
    payload = public_payload(game["events"])
    assert payload["frames"]
    assert payload["frames"][0]["line"] == "开局"
    assert len(payload["frames"][0]["seats"]) == 4
    names = [s["name"] for s in payload["frames"][0]["seats"]]
    assert "机器人1" in names
    assert payload["log"]
    assert result_text(game)


if __name__ == "__main__":
    test_play_seed_has_four_robots_and_discards()
    test_same_seed_same_opening()
    test_payload_has_frames()
    print("play tests ok")
