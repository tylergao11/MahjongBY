# -*- coding: utf-8 -*-
from harvest.tiles import CALL_AN_GANG, CALL_CHI_LOW, CALL_HU, CALL_PASS, CALL_PENG
from giveaway.bot import GiveawayBots, pick_call, pick_discard


def test_never_hu():
    mask = [1, 0, 0, 0, 0, 0, 0, 1]
    assert pick_call([1], None, True, 0, mask, 80) == CALL_PASS
    assert pick_call([1], 1, False, 0, mask, 80) == CALL_PASS


def test_peng_when_able():
    mask = [1, 0, 0, 0, 1, 0, 0, 1]
    hand = [49, 49, 1, 2, 3, 4, 5, 6, 7, 8, 9, 17, 18]
    assert pick_call(hand, 49, False, 0, mask, 80) == CALL_PENG


def test_chi_when_no_peng():
    mask = [1, 0, 0, 1, 0, 0, 0, 0]
    hand = [2, 3, 5, 6, 7, 8, 8, 8, 33, 34, 35, 49, 50]
    assert pick_call(hand, 1, False, 0, mask, 80) == CALL_CHI_LOW


def test_an_gang_on_own_turn():
    mask = [1, 0, 0, 0, 0, 0, 1, 1]
    assert pick_call([1, 1, 1, 1], None, True, 0, mask, 80) == CALL_AN_GANG


def test_dump_laizi_first():
    hand = [17, 1, 9, 49, 33, 41, 2, 8, 18, 24, 34, 40, 50]
    assert pick_discard(hand) == 17


def test_break_pair_before_honor():
    hand = [5, 5, 1, 9, 33, 41, 2, 8, 18, 24, 34, 40, 49]
    assert pick_discard(hand) == 5


def test_bu_gang_feeds_qiang():
    bots = GiveawayBots()
    assert bots.want_bu_gang([49, 1, 2], [49, 49, 49], ["peng"]) == 49


def test_interface():
    bots = GiveawayBots()
    hands = {1: [1, 2, 3, 4, 5, 6, 7, 8, 9, 17, 18, 49, 67], 2: [], 3: [], 4: []}
    rivers = {1: [], 2: [], 3: [], 4: []}
    melds = {1: [], 2: [], 3: [], 4: []}
    n_melds = {1: 0, 2: 0, 3: 0, 4: 0}
    tile = bots.pick_discard(1, 1, hands, rivers, melds, n_melds, 1)
    assert tile in hands[1]
    action = bots.pick_call(1, 1, hands, rivers, melds, n_melds, 49, 2, False, 0, 80)
    assert action != CALL_HU
    assert action in (CALL_PASS, CALL_PENG, CALL_CHI_LOW)


if __name__ == "__main__":
    test_never_hu()
    test_peng_when_able()
    test_chi_when_no_peng()
    test_an_gang_on_own_turn()
    test_dump_laizi_first()
    test_break_pair_before_honor()
    test_bu_gang_feeds_qiang()
    test_interface()
    print("giveaway tests ok")
