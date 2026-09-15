# -*- coding: utf-8 -*-
from train.play import _safe_discard
from train.replay import legal_call_mask
from train.shanten import discard_shanten_vec, shanten
from train.tiles import (
    CALL_CHI_HIGH,
    CALL_CHI_LOW,
    CALL_CHI_MID,
    CALL_PENG,
    LAIZI_ID,
    LAIZI_IDX,
    discard_legal_vec,
    tile_idx,
)
from train.wincheck import can_win


def test_win_is_minus_one():
    hand = [1, 2, 3, 4, 5, 6, 7, 8, 9, 17, 18, 19, 49, 49]
    assert can_win(hand)
    assert shanten(hand) == -1


def test_tenpai_is_zero():
    hand = [1, 2, 3, 4, 5, 6, 7, 8, 9, 17, 18, 19, 49]
    assert shanten(hand) == 0


def test_thirteen_tiles_not_complete():
    hand = [1, 2, 3, 4, 5, 6, 7, 8, 9, 33, 34, 35, 17]
    assert not can_win(hand)
    assert shanten(hand) == 0


def test_open_meld_win():
    concealed = [1, 2, 3, 4, 5, 6, 7, 8, 9, 49]
    assert shanten(concealed, extra=49, n_melds=1) == -1


def test_discard_vec_marks_hand_tiles():
    hand = [1, 2, 3, 4, 5, 6, 7, 8, 9, 17, 18, 19, 49, 50]
    vec = discard_shanten_vec(hand)
    assert vec[tile_idx(50)] < 1.0
    assert vec[tile_idx(67)] == 1.0


def test_laizi_shanten_is_win():
    hand = [1, 2, 3, 4, 5, 6, 7, 8, 9, 18, 19, 49, 49, 17]
    assert shanten(hand) == -1


def test_wild_shanten_not_worse_than_as_one_tiao():
    hand = [4, 5, 8, 17, 18, 23, 24, 25, 34, 34, 39, 40, 52, 65]
    assert shanten(hand) <= 2


def test_discarded_chicken_is_one_tiao():
    hand = [18, 19, 1, 2, 3, 4, 5, 6, 7, 8, 9, 49, 50]
    mask = legal_call_mask(hand, LAIZI_ID, 1, 2, own_turn=False, n_melds=0)
    assert mask[CALL_CHI_LOW] == 1
    pair = [17, 17, 1, 2, 3, 4, 5, 6, 7, 8, 9, 49, 50]
    peng = legal_call_mask(pair, LAIZI_ID, 1, 3, own_turn=False, n_melds=0)
    assert peng[CALL_PENG] == 1


def test_laizi_chi_only_as_itself():
    hand = [17, 19, 1, 2, 3, 4, 5, 6, 7, 8, 9, 49, 50]
    mask = legal_call_mask(hand, 18, 1, 2, own_turn=False, n_melds=0)
    assert mask[CALL_CHI_MID] == 1
    wild = [17, 3, 8, 9, 18, 19, 20, 33, 34, 35, 49, 50, 51]
    mask_w = legal_call_mask(wild, 2, 1, 2, own_turn=False, n_melds=0)
    assert mask_w[CALL_CHI_HIGH] == 0
    assert mask_w[CALL_CHI_LOW] == 0


def test_discard_legal_allows_laizi():
    mixed = [1, 17, 18]
    vec = discard_legal_vec(mixed)
    assert vec[LAIZI_IDX] == 1
    assert vec[tile_idx(1)] == 1
    only = [17, 17]
    assert discard_legal_vec(only)[LAIZI_IDX] == 1
    assert _safe_discard(mixed, 17) == 17
    assert discard_legal_vec([1, 2, 18], forbid=18)[tile_idx(18)] == 0
    assert discard_legal_vec([18, 18], forbid=18)[tile_idx(18)] == 1


if __name__ == "__main__":
    test_win_is_minus_one()
    test_tenpai_is_zero()
    test_thirteen_tiles_not_complete()
    test_open_meld_win()
    test_discard_vec_marks_hand_tiles()
    test_laizi_shanten_is_win()
    test_wild_shanten_not_worse_than_as_one_tiao()
    test_discarded_chicken_is_one_tiao()
    test_laizi_chi_only_as_itself()
    test_discard_legal_allows_laizi()
    print("shanten tests ok")
