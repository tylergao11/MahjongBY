# -*- coding: utf-8 -*-
from train.tiles import CALL_CHI_LOW, CALL_HU, CALL_PASS, CALL_PENG
from train.win_bot import HarvestBots, WinBots, pick_win_call, pick_win_discard


def test_dump_lonely_honor_when_rest_is_set():
    hand = [1, 2, 3, 4, 5, 6, 7, 8, 9, 17, 18, 19, 49]
    rivers = {1: [], 2: [], 3: [], 4: []}
    melds = {1: [], 2: [], 3: [], 4: []}
    tile = pick_win_discard(hand, rivers, melds, 0)
    assert tile == 49


def test_keep_laizi_dump_honor():
    hand = [1, 2, 3, 4, 5, 6, 7, 8, 9, 18, 19, 20, 17, 49]
    rivers = {1: [], 2: [], 3: [], 4: []}
    melds = {1: [], 2: [], 3: [], 4: []}
    assert pick_win_discard(hand, rivers, melds, 0) == 49


def test_always_hu():
    mask = [1, 0, 0, 0, 0, 0, 0, 1]
    assert pick_win_call([1], None, True, 0, mask, 80) == CALL_HU


def test_pass_when_only_pass():
    mask = [1, 0, 0, 0, 0, 0, 0, 0]
    assert pick_win_call([1, 2, 3], 9, False, 0, mask, 80) == CALL_PASS


def test_qidui_skip_peng():
    mask = [1, 0, 0, 0, 1, 0, 0, 0]
    hand = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 8, 8, 9]
    assert pick_win_call(hand, 9, False, 0, mask, 80) == CALL_PASS


def test_chi_when_shanten_drops():
    mask = [1, 0, 0, 1, 0, 0, 0, 0]
    hand = [2, 3, 5, 6, 7, 8, 8, 8, 33, 34, 35, 49, 50]
    assert pick_win_call(hand, 1, False, 0, mask, 80) == CALL_CHI_LOW


def test_peng_honor_pair():
    mask = [1, 0, 0, 0, 1, 0, 0, 0]
    hand = [49, 49, 1, 2, 3, 4, 5, 6, 7, 8, 9, 17, 18]
    action = pick_win_call(hand, 49, False, 0, mask, 80)
    assert action in (CALL_PENG, CALL_PASS)


def test_prefer_wuji_ron_over_zimo_only():
    hand = [1, 2, 4, 5, 6, 7, 8, 9, 33, 33, 34, 35, 36, 17]
    rivers = {1: [], 2: [], 3: [], 4: []}
    melds = {1: [], 2: [], 3: [], 4: []}
    assert pick_win_discard(hand, rivers, melds, 0) == 17


def test_win_bot_interface():
    bots = HarvestBots()
    assert isinstance(bots, WinBots)
    hands = {1: [1, 2, 3, 4, 5, 6, 7, 8, 9, 17, 18, 49, 67], 2: [], 3: [], 4: []}
    rivers = {1: [], 2: [], 3: [], 4: []}
    melds = {1: [], 2: [], 3: [], 4: []}
    n_melds = {1: 0, 2: 0, 3: 0, 4: 0}
    tile = bots.pick_discard(1, 1, hands, rivers, melds, n_melds, 1)
    assert tile in hands[1]


if __name__ == "__main__":
    test_dump_lonely_honor_when_rest_is_set()
    test_keep_laizi_dump_honor()
    test_always_hu()
    test_pass_when_only_pass()
    test_qidui_skip_peng()
    test_chi_when_shanten_drops()
    test_peng_honor_pair()
    test_prefer_wuji_ron_over_zimo_only()
    test_win_bot_interface()
    print("win bot tests ok")
