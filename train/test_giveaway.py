# -*- coding: utf-8 -*-
from harvest.tiles import CALL_HU, CALL_PASS, CALL_PENG
from giveaway.bot import GiveawayBots, pick_call, pick_discard


def test_pass_pinghu():
    mask = [1, 0, 0, 0, 0, 0, 0, 1]
    hand = [1, 2, 3, 4, 5, 6, 7, 8, 9, 33, 34, 35, 49, 49]
    assert pick_call(hand, None, True, 0, mask, 80) == CALL_PASS


def test_take_qidui():
    mask = [1, 0, 0, 0, 0, 0, 0, 1]
    hand = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 9, 9]
    assert pick_call(hand, None, True, 0, mask, 80) == CALL_HU


def test_take_dadui():
    mask = [1, 0, 0, 0, 0, 0, 0, 1]
    hand = [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 49, 49]
    assert pick_call(hand, None, True, 0, mask, 80) == CALL_HU


def test_do_not_chi():
    chi = [1, 0, 0, 1, 0, 0, 0, 0]
    hand = [2, 3, 5, 6, 7, 8, 8, 8, 33, 34, 35, 49, 50]
    assert pick_call(hand, 1, False, 0, chi, 80) == CALL_PASS


def test_peng_for_dadui_not_qidui():
    mask = [1, 0, 0, 0, 1, 0, 0, 0]
    dadui = [49, 49, 1, 1, 1, 2, 2, 2, 3, 4, 5, 6, 7]
    assert pick_call(dadui, 49, False, 0, mask, 80) == CALL_PENG
    qidui = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 8, 8, 9]
    assert pick_call(qidui, 9, False, 0, mask, 80) == CALL_PASS


def test_do_not_peek_to_deal_qidui():
    hand = [9, 9, 1, 2, 3, 4, 5, 6, 7, 8, 33, 34, 49]
    other = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 9]
    rivers = {1: [], 2: [], 3: [], 4: []}
    melds = {1: [], 2: [], 3: [], 4: []}
    n_melds = {1: 0, 2: 0, 3: 0, 4: 0}
    kinds = {1: [], 2: [], 3: [], 4: []}
    hands = {1: hand, 2: other, 3: [], 4: []}
    tile = pick_discard(hand, rivers, melds, n_melds, seat=1, meld_kinds=kinds, hands=hands)
    assert tile != 9


def test_feed_open_wan_when_it_is_junk():
    hand = [5, 49, 49, 50, 50, 51, 51, 65, 65, 33, 33, 18, 18]
    rivers = {1: [], 2: [49], 3: [], 4: []}
    melds = {1: [], 2: [1, 2, 3, 4, 6, 7], 3: [], 4: []}
    kinds = {1: [], 2: ["chi", "chi"], 3: [], 4: []}
    n_melds = {1: 0, 2: 2, 3: 0, 4: 0}
    assert pick_discard(hand, rivers, melds, n_melds, seat=1, meld_kinds=kinds) == 5


def test_no_bu_gang():
    bots = GiveawayBots()
    assert bots.want_bu_gang([49, 1, 2], [49, 49, 49], ["peng"]) is None


def test_interface():
    bots = GiveawayBots()
    hands = {1: [1, 2, 3, 4, 5, 6, 7, 8, 9, 17, 18, 49, 67], 2: [], 3: [], 4: []}
    rivers = {1: [], 2: [], 3: [], 4: []}
    melds = {1: [], 2: [], 3: [], 4: []}
    n_melds = {1: 0, 2: 0, 3: 0, 4: 0}
    tile = bots.pick_discard(1, 1, hands, rivers, melds, n_melds, 1)
    assert tile in hands[1]
    assert bots.pick_call(1, 1, hands, rivers, melds, n_melds, 49, 2, False, 0, 80) != CALL_HU


if __name__ == "__main__":
    test_pass_pinghu()
    test_take_qidui()
    test_take_dadui()
    test_do_not_chi()
    test_peng_for_dadui_not_qidui()
    test_do_not_peek_to_deal_qidui()
    test_feed_open_wan_when_it_is_junk()
    test_no_bu_gang()
    test_interface()
    print("giveaway tests ok")
