# -*- coding: utf-8 -*-
"""送钱：该胡不胡，能碰就碰，好牌先扔。"""
from harvest.legal import legal_call_mask
from harvest.tiles import (
    CALL_AN_GANG,
    CALL_CHI_HIGH,
    CALL_CHI_LOW,
    CALL_CHI_MID,
    CALL_MING_GANG,
    CALL_PASS,
    CALL_PENG,
    TILE_IDS,
    discard_legal_vec,
    id_from_suit,
    is_honor,
    is_laizi,
    suit_rank,
)

CHI_ACTIONS = (CALL_CHI_HIGH, CALL_CHI_MID, CALL_CHI_LOW)


def _connected(hand, tile):
    suit, rank = suit_rank(tile)
    if suit is None:
        return False
    near = [
        id_from_suit(suit, rank - 2),
        id_from_suit(suit, rank - 1),
        id_from_suit(suit, rank + 1),
        id_from_suit(suit, rank + 2),
    ]
    return any(x in hand for x in near if x is not None)


def _gift_score(hand, tile):
    if is_laizi(tile):
        return (0, 0, tile)
    n = hand.count(tile)
    if n >= 3:
        return (1, -n, tile)
    if n == 2:
        return (2, 0, tile)
    if _connected(hand, tile):
        return (3, 0, tile)
    if is_honor(tile):
        return (6, 0, tile)
    suit, rank = suit_rank(tile)
    if rank in (1, 9):
        return (5, 0, tile)
    return (4, 0, tile)


def pick_discard(hand, rivers=None, melds=None, n_melds=0, forbid=None, **kwargs):
    if not hand:
        return 0
    legal = [t for t, ok in zip(TILE_IDS, discard_legal_vec(hand, forbid=forbid)) if ok and t in hand]
    if not legal:
        return hand[0]
    return min(set(legal), key=lambda tile: _gift_score(hand, tile))


def pick_call(hand, offer, own_turn, n_melds, mask, wall_n, **kwargs):
    if own_turn:
        if mask[CALL_AN_GANG] and wall_n > 0:
            return CALL_AN_GANG
        return CALL_PASS
    if mask[CALL_MING_GANG] and wall_n > 0:
        return CALL_MING_GANG
    if mask[CALL_PENG]:
        return CALL_PENG
    for action in CHI_ACTIONS:
        if mask[action]:
            return action
    return CALL_PASS


class GiveawayBots:
    def pick_discard(self, seat, dealer, hands, rivers, melds, n_melds, just_drew, forbid=None, **kwargs):
        return pick_discard(hands[seat], rivers, melds, n_melds[seat], forbid=forbid)

    def pick_call(self, seat, dealer, hands, rivers, melds, n_melds, offer, offer_seat, own_turn, just_drew, wall_n, **kwargs):
        own_melds = melds[seat] if isinstance(melds, dict) and seat in melds else None
        mask = legal_call_mask(
            hands[seat], offer, offer_seat, seat, own_turn=own_turn, n_melds=n_melds[seat],
            meld_kinds=kwargs.get("meld_kinds"), blocked_hu=kwargs.get("blocked_hu"),
            passed_fan=kwargs.get("passed_fan"), passed_peng=kwargs.get("passed_peng"),
            after_gang=kwargs.get("after_gang", False), melds=own_melds,
        )
        if wall_n <= 0:
            mask[CALL_AN_GANG] = 0
            mask[CALL_MING_GANG] = 0
        if sum(mask[1:]) == 0:
            return CALL_PASS
        return pick_call(
            hands[seat], offer, own_turn, n_melds[seat], mask, wall_n,
        )

    def want_bu_gang(self, hand, melds, kinds, wall_n=80, **kwargs):
        i = 0
        for kind in kinds:
            n = 4 if kind in ("gang", "an_gang", "ming_gang") else 3
            group = melds[i:i + n]
            i += n
            if kind != "peng" or not group or group[0] not in hand:
                continue
            tile = group[0]
            if is_laizi(tile):
                continue
            return tile
        return None
