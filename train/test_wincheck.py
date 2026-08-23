# -*- coding: utf-8 -*-
from train.wincheck import can_win


def test_basic_win():
    # 123万 456万 789万 123条 东东
    hand = [1, 2, 3, 4, 5, 6, 7, 8, 9, 17, 18, 19, 49, 49]
    assert can_win(hand)


def test_not_win():
    hand = [1, 2, 3, 4, 5, 6, 7, 8, 9, 17, 18, 19, 49, 50]
    assert not can_win(hand)


def test_ron_with_open_meld():
    # 已碰一门，手牌 123万 456万 东东 + 摸/点 7万?  need 1 set + pair from 5 tiles
    # 123 456 东东 = 8 tiles, n_melds=2 would need 2 sets + pair = 8. wait
    # n_melds=1 need 3 sets + pair = 11 tiles
    concealed = [1, 2, 3, 4, 5, 6, 7, 8, 9, 49]
    assert can_win(concealed, extra=49, n_melds=1)


if __name__ == "__main__":
    test_basic_win()
    test_not_win()
    test_ron_with_open_meld()
    print("wincheck tests ok")
