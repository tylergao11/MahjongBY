# -*- coding: utf-8 -*-
from train.wincheck import can_ron, can_win, is_pengpeng, is_qidui


def test_basic_win():
    # 123万 456万 789万 123条 东东 — 一条 in 123条 is wild and also 1条
    hand = [1, 2, 3, 4, 5, 6, 7, 8, 9, 17, 18, 19, 49, 49]
    assert can_win(hand)


def test_not_win():
    hand = [1, 2, 3, 4, 5, 6, 7, 8, 9, 17, 18, 19, 49, 50]
    assert not can_win(hand)


def test_ron_with_open_meld():
    concealed = [1, 2, 3, 4, 5, 6, 7, 8, 9, 49]
    assert can_win(concealed, extra=49, n_melds=1)


def test_laizi_fills_one_tiao():
    hand = [1, 2, 3, 4, 5, 6, 7, 8, 9, 18, 19, 49, 49, 17]
    assert can_win(hand)


def test_laizi_makes_honor_pair():
    hand = [1, 2, 3, 4, 5, 6, 7, 8, 9, 18, 19, 20, 49, 17]
    assert can_win(hand)


def test_laizi_fills_chow_gap():
    hand = [1, 2, 3, 4, 5, 6, 7, 8, 9, 33, 35, 49, 49, 17]
    assert can_win(hand)


def test_qidui_with_laizi():
    hand = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 17]
    assert can_win(hand)


def test_qidui_two_wilds():
    hand = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 7, 8, 17, 17]
    assert can_win(hand)


def test_discarded_chicken_ron_is_one_tiao():
    # extra 17 is 1条, not a wild filling 8万
    dead = [1, 2, 3, 4, 5, 6, 7, 9, 18, 19, 20, 49, 49]
    assert not can_win(dead, extra=17)
    chow = [1, 2, 3, 4, 5, 6, 7, 8, 9, 18, 19, 49, 49]
    assert can_win(chow, extra=17)


def test_pinghu_cannot_ron():
    hand = [1, 2, 3, 4, 5, 6, 7, 8, 9, 33, 17, 49, 49]
    assert can_win(hand, extra=35)
    assert not can_ron(hand, extra=35)


def test_qidui_can_ron():
    hand = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 8]
    assert is_qidui(hand, extra=8)
    assert can_ron(hand, extra=8)


def test_pengpeng_can_ron():
    hand = [1, 1, 1, 4, 4, 4, 7, 7, 7, 33, 33, 33, 49]
    assert is_pengpeng(hand, extra=49)
    assert can_ron(hand, extra=49)


if __name__ == "__main__":
    test_basic_win()
    test_not_win()
    test_ron_with_open_meld()
    test_laizi_fills_one_tiao()
    test_laizi_makes_honor_pair()
    test_laizi_fills_chow_gap()
    test_qidui_with_laizi()
    test_qidui_two_wilds()
    test_discarded_chicken_ron_is_one_tiao()
    test_pinghu_cannot_ron()
    test_qidui_can_ron()
    test_pengpeng_can_ron()
    print("wincheck tests ok")
