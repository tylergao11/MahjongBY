# -*- coding: utf-8 -*-
from harvest.tiles import CALL_HU, CALL_PASS, CALL_PENG
from companion.bot import CompanionBots, pick_call, pick_discard, should_peng


def test_dump_lonely_honor():
    hand = [1, 2, 3, 4, 5, 6, 7, 8, 9, 17, 18, 19, 49]
    rivers = {1: [], 2: [], 3: [], 4: []}
    melds = {1: [], 2: [], 3: [], 4: []}
    assert pick_discard(hand, rivers, melds) == 49


def test_always_hu():
    mask = [1, 0, 0, 0, 0, 0, 0, 1]
    assert pick_call([1], None, True, 0, mask, 80) == CALL_HU


def test_peng_honor():
    assert should_peng([49, 49, 1, 2, 3], 49)
    mask = [1, 0, 0, 0, 1, 0, 0, 0]
    assert pick_call([49, 49, 1, 2, 3, 4, 5, 6, 7, 8, 9, 17, 18], 49, False, 0, mask, 80) == CALL_PENG


def test_interface():
    bots = CompanionBots()
    hands = {1: [1, 2, 3, 4, 5, 6, 7, 8, 9, 17, 18, 49, 67], 2: [], 3: [], 4: []}
    rivers = {1: [], 2: [], 3: [], 4: []}
    melds = {1: [], 2: [], 3: [], 4: []}
    n_melds = {1: 0, 2: 0, 3: 0, 4: 0}
    tile = bots.pick_discard(1, 1, hands, rivers, melds, n_melds, 1)
    assert tile in hands[1]
    assert bots.pick_call(1, 1, hands, rivers, melds, n_melds, None, None, True, 0, 80) in (CALL_PASS, CALL_HU)


if __name__ == "__main__":
    test_dump_lonely_honor()
    test_always_hu()
    test_peng_honor()
    test_interface()
    print("companion tests ok")
