# -*- coding: utf-8 -*-
"""4-meld + pair, or 七对. 一条 (妖姬) is wild in the closed hand only."""
from collections import Counter
from functools import lru_cache

from harvest.tiles import LAIZI_ID, id_from_suit, suit_rank


def _hand_tiles(hand, extra=None):
    tiles = [int(t) for t in hand]
    locked_tiao = 0
    if extra is not None:
        extra = int(extra)
        if extra == LAIZI_ID:
            locked_tiao = 1
        else:
            tiles.append(extra)
    return tiles, locked_tiao


def can_win(hand, extra=None, n_melds=0):
    tiles, locked_tiao = _hand_tiles(hand, extra)
    need = 4 - int(n_melds)
    if need < 0:
        return False
    if len(tiles) + locked_tiao != need * 3 + 2:
        return False
    if need == 4 and _qidui(tiles, locked_tiao):
        return True
    wilds = sum(1 for t in tiles if t == LAIZI_ID)
    rest = [t for t in tiles if t != LAIZI_ID]
    rest.extend([LAIZI_ID] * locked_tiao)
    if _complete(tuple(sorted(rest)), need, 0, wilds):
        return True
    from harvest.fxj_rules import is_lanpai
    return is_lanpai(hand, extra=extra, n_melds=n_melds) or is_lanpai(
        hand, extra=extra, n_melds=n_melds, qixing=True
    )


def is_qidui(hand, extra=None, n_melds=0):
    if int(n_melds) != 0:
        return False
    tiles, locked_tiao = _hand_tiles(hand, extra)
    if len(tiles) + locked_tiao != 14:
        return False
    return _qidui(tiles, locked_tiao)


def is_pengpeng(hand, extra=None, n_melds=0, meld_kinds=None):
    if meld_kinds and any(kind == "chi" for kind in meld_kinds):
        return False
    tiles, locked_tiao = _hand_tiles(hand, extra)
    need = 4 - int(n_melds)
    if need < 0 or len(tiles) + locked_tiao != need * 3 + 2:
        return False
    wilds = sum(1 for t in tiles if t == LAIZI_ID)
    rest = [t for t in tiles if t != LAIZI_ID]
    rest.extend([LAIZI_ID] * locked_tiao)
    return _pungs_only(tuple(sorted(rest)), need, 0, wilds)


def can_ron(hand, extra=None, n_melds=0, meld_kinds=None, **kwargs):
    """点炮按可吃场：平胡且无另加番不能胡。hupai710111"""
    from harvest.fxj_rules import can_ron as _fxj_ron
    return _fxj_ron(hand, extra=extra, n_melds=n_melds, meld_kinds=meld_kinds, **kwargs)


def _qidui(tiles, locked_tiao=0):
    wilds = sum(1 for t in tiles if t == LAIZI_ID)
    rest = [t for t in tiles if t != LAIZI_ID]
    rest.extend([LAIZI_ID] * locked_tiao)
    odd = sum(n % 2 for n in Counter(rest).values())
    return wilds >= odd and (wilds - odd) % 2 == 0


@lru_cache(maxsize=200000)
def _complete(tiles, sets_left, has_pair, wilds):
    if sets_left < 0 or wilds < 0:
        return False
    if not tiles:
        if not has_pair:
            wilds -= 2
            has_pair = 1
        return has_pair and wilds >= 0 and wilds == sets_left * 3

    first = tiles[0]
    n = tiles.count(first)

    for take, w in ((3, 0), (2, 1), (1, 2)):
        if n >= take and wilds >= w:
            if _complete(_remove(tiles, first, take), sets_left - 1, has_pair, wilds - w):
                return True
    if not has_pair:
        for take, w in ((2, 0), (1, 1)):
            if n >= take and wilds >= w:
                if _complete(_remove(tiles, first, take), sets_left, 1, wilds - w):
                    return True

    suit, rank = suit_rank(first)
    if suit:
        for start in (rank, rank - 1, rank - 2):
            if start < 1 or start > 7:
                continue
            ids = (
                id_from_suit(suit, start),
                id_from_suit(suit, start + 1),
                id_from_suit(suit, start + 2),
            )
            if first not in ids:
                continue
            rest = list(tiles)
            wneed = 0
            for tid in ids:
                if tid in rest:
                    rest.remove(tid)
                else:
                    wneed += 1
            if wneed <= wilds and _complete(tuple(rest), sets_left - 1, has_pair, wilds - wneed):
                return True
    return False


def _pungs_only(tiles, sets_left, has_pair, wilds):
    if sets_left < 0 or wilds < 0:
        return False
    if not tiles:
        if not has_pair:
            wilds -= 2
            has_pair = 1
        return has_pair and wilds >= 0 and wilds == sets_left * 3
    first = tiles[0]
    n = tiles.count(first)
    for take, w in ((3, 0), (2, 1), (1, 2)):
        if n >= take and wilds >= w:
            if _pungs_only(_remove(tiles, first, take), sets_left - 1, has_pair, wilds - w):
                return True
    if not has_pair:
        for take, w in ((2, 0), (1, 1)):
            if n >= take and wilds >= w:
                if _pungs_only(_remove(tiles, first, take), sets_left, 1, wilds - w):
                    return True
    return False


def _remove(tiles, tile, k):
    rest = list(tiles)
    for _ in range(k):
        rest.remove(tile)
    return tuple(rest)
