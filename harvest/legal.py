# -*- coding: utf-8 -*-
"""可吃场合法吃碰杠胡。"""
from harvest.tiles import (
    CALL_AN_GANG,
    CALL_CHI_HIGH,
    CALL_CHI_LOW,
    CALL_CHI_MID,
    CALL_HU,
    CALL_MING_GANG,
    CALL_PASS,
    CALL_PENG,
    N_CALL,
    next_seat,
    suit_rank,
)
from harvest.wincheck import can_ron, can_win


def _count(hand, tile):
    return sum(1 for x in hand if x == tile)


def can_chi_high(hand, tile):
    if tile is None:
        return False
    suit, rank = suit_rank(tile)
    if suit is None or rank < 3:
        return False
    return (tile - 2) in hand and (tile - 1) in hand


def can_chi_mid(hand, tile):
    if tile is None:
        return False
    suit, rank = suit_rank(tile)
    if suit is None or rank < 2 or rank > 8:
        return False
    return (tile - 1) in hand and (tile + 1) in hand


def can_chi_low(hand, tile):
    if tile is None:
        return False
    suit, rank = suit_rank(tile)
    if suit is None or rank > 7:
        return False
    return (tile + 1) in hand and (tile + 2) in hand


def legal_call_mask(
    hand, offer, offer_seat, seat, own_turn=False, n_melds=0, meld_kinds=None,
    blocked_hu=None, passed_fan=None, passed_peng=None, after_gang=False, melds=None,
):
    mask = [0] * N_CALL
    mask[CALL_PASS] = 1
    if own_turn:
        if any(hand.count(tid) >= 4 for tid in set(hand)):
            mask[CALL_AN_GANG] = 1
        if can_win(hand, n_melds=n_melds):
            mask[CALL_HU] = 1
        return mask
    if offer is None or offer_seat is None or seat == offer_seat:
        return mask
    if seat == next_seat(offer_seat):
        if can_chi_high(hand, offer):
            mask[CALL_CHI_HIGH] = 1
        if can_chi_mid(hand, offer):
            mask[CALL_CHI_MID] = 1
        if can_chi_low(hand, offer):
            mask[CALL_CHI_LOW] = 1
    n = _count(hand, offer)
    blocked_peng = passed_peng is not None and offer in passed_peng
    if n >= 2 and not blocked_peng:
        mask[CALL_PENG] = 1
    if n >= 3 and not blocked_peng:
        mask[CALL_MING_GANG] = 1
    if can_ron(
        hand, extra=offer, n_melds=n_melds, meld_kinds=meld_kinds, melds=melds,
        after_gang=after_gang, qiang_gang=after_gang, passed_fan=passed_fan, hu_tile=offer,
    ):
        if blocked_hu is None or offer not in blocked_hu:
            mask[CALL_HU] = 1
    return mask
