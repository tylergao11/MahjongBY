# -*- coding: utf-8 -*-
from train.fxj_rules import (
    can_ron,
    can_win,
    is_lanpai,
    is_long_qidui,
    judge,
    liuju_left,
    settle,
    underground_hu,
)
from train.wincheck import can_ron as win_can_ron, can_win as win_can_win


def test_pinghu_no_fan_cannot_ron():
    hand = [1, 2, 3, 4, 5, 6, 7, 8, 9, 33, 17, 49, 49]
    assert can_win(hand, extra=35)
    assert not can_ron(hand, extra=35)


def test_qingyise_pinghu_can_ron():
    hand = [1, 2, 3, 4, 5, 6, 7, 8, 9, 1, 2, 3, 9]
    assert can_win(hand, extra=9)
    info = judge(hand, extra=9, zimo=False)
    assert info["base"] == "平胡"
    assert any(n == "清一色" for n, _ in info["extras"])
    assert can_ron(hand, extra=9)


def test_menqing_does_not_unlock_ron():
    hand = [1, 2, 3, 4, 5, 6, 7, 8, 9, 33, 17, 49, 49]
    assert not can_ron(hand, extra=35)


def test_qidui_can_ron():
    hand = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 8]
    assert can_ron(hand, extra=8)


def test_lanpai():
    hand = [1, 4, 7, 18, 21, 24, 33, 36, 39, 49, 50, 51, 52]
    assert is_lanpai(hand, extra=65)
    assert can_win(hand, extra=65)
    assert win_can_win(hand, extra=65)


def test_qixing_lanpai():
    hand = [1, 4, 7, 18, 21, 24, 49, 50, 51, 52, 65, 66, 67]
    assert is_lanpai(hand, extra=33, qixing=True)


def test_long_qidui():
    hand = [1, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6]
    assert is_long_qidui(hand, extra=1)
    info = judge(hand, extra=1)
    assert info["base"] == "龙抓背"


def test_passed_fan_blocks_same():
    hand = [1, 1, 1, 4, 4, 4, 7, 7, 7, 33, 33, 33, 49]
    assert can_ron(hand, extra=49)
    info = judge(hand, extra=49, zimo=False)
    assert not can_ron(hand, extra=49, passed_fan=info["total_fan"])


def test_qiang_gang_allows_pinghu():
    hand = [1, 2, 3, 4, 5, 6, 7, 8, 9, 33, 17, 49, 49]
    assert can_ron(hand, extra=35, qiang_gang=True)


def test_liuju_left():
    assert liuju_left(0) == 20
    assert liuju_left(1) == 14
    assert liuju_left(2) == 16
    assert liuju_left(3) == 20


def test_shifeng():
    river = [49, 50, 51, 52, 65, 66, 67, 49, 50, 51]
    assert underground_hu(river, 0) == "十风"
    assert underground_hu(river, 1) is None


def test_settle_zimo():
    info = {"money": 2, "base": "平胡", "extras": [("门前清", 1)], "total_fan": 1}
    pay = settle([1], None, True, False, {1: info})
    assert pay["scores"][1] == 6
    assert pay["scores"][2] == -2


def test_wincheck_delegates():
    hand = [1, 2, 3, 4, 5, 6, 7, 8, 9, 33, 17, 49, 49]
    assert not win_can_ron(hand, extra=35)


if __name__ == "__main__":
    test_pinghu_no_fan_cannot_ron()
    test_qingyise_pinghu_can_ron()
    test_menqing_does_not_unlock_ron()
    test_qidui_can_ron()
    test_lanpai()
    test_qixing_lanpai()
    test_long_qidui()
    test_passed_fan_blocks_same()
    test_qiang_gang_allows_pinghu()
    test_liuju_left()
    test_shifeng()
    test_settle_zimo()
    test_wincheck_delegates()
    print("fxj rules tests ok")
