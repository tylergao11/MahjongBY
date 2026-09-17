# -*- coding: utf-8 -*-
"""送钱：看不上小胡，大胡才要。不偷看对面手牌去点炮。"""
from collections import Counter

from harvest.fxj_rules import judge
from harvest.legal import legal_call_mask
from harvest.shanten import qidui_shanten, shanten
from harvest.tiles import (
    CALL_AN_GANG,
    CALL_HU,
    CALL_MING_GANG,
    CALL_PASS,
    CALL_PENG,
    TILE_IDS,
    discard_legal_vec,
    is_honor,
    is_laizi,
    suit_rank,
)

SEATS = (1, 2, 3, 4)
BIG_BASE = ("大对", "小七对", "龙抓背", "十三幺", "十风", "四小鸡", "烂牌", "七星烂牌")
BIG_EXTRA = ("清一色", "混一色", "字一色", "大三元", "大四喜")


def _empty_map():
    return {1: [], 2: [], 3: [], 4: []}


def _as_map(value):
    if isinstance(value, dict):
        return value
    return _empty_map()


def _own_n(n_melds, seat):
    if isinstance(n_melds, dict):
        return int(n_melds.get(seat, 0))
    return int(n_melds or 0)


def _own_kinds(meld_kinds, seat):
    if isinstance(meld_kinds, dict):
        return list(meld_kinds.get(seat) or [])
    if isinstance(meld_kinds, (list, tuple)):
        return list(meld_kinds)
    return []


def _group(tile):
    if is_laizi(tile):
        return "tiao"
    suit, _rank = suit_rank(tile)
    return suit or "honor"


def _remove(hand, tiles):
    out = list(hand)
    for tile in tiles:
        out.remove(tile)
    return out


def _is_big(info):
    if not info:
        return False
    if info["base"] in BIG_BASE:
        return True
    names = {name for name, _fan in (info.get("extras") or [])}
    return bool(names & set(BIG_EXTRA))


def _hu_info(hand, offer, own_turn, n_melds, meld_kinds, melds, after_gang):
    extra = None if own_turn else offer
    if own_turn:
        hu_tile = hand[-1] if hand else None
    else:
        hu_tile = offer
    return judge(
        hand, extra=extra, n_melds=n_melds, meld_kinds=meld_kinds, melds=melds,
        zimo=own_turn, after_gang=after_gang, hu_tile=hu_tile,
    )


def _iter_melds(melds, kinds):
    tiles = list(melds or [])
    kinds = list(kinds or [])
    i = 0
    if kinds:
        for kind in kinds:
            n = 4 if kind in ("gang", "an_gang", "ming_gang") else 3
            yield kind, tiles[i:i + n]
            i += n
        return
    while i < len(tiles):
        if i + 3 <= len(tiles) and tiles[i] == tiles[i + 1] == tiles[i + 2]:
            if i + 4 <= len(tiles) and tiles[i + 3] == tiles[i]:
                yield "gang", tiles[i:i + 4]
                i += 4
            else:
                yield "peng", tiles[i:i + 3]
                i += 3
        elif i + 3 <= len(tiles):
            yield "chi", tiles[i:i + 3]
            i += 3
        else:
            break


def _need(other, tile, rivers, melds, n_melds, kinds_map):
    river = list(rivers.get(other, []))
    opened = list(melds.get(other, []))
    kinds = kinds_map.get(other, [])
    n_open = _own_n(n_melds, other)
    dumped = river.count(tile)
    group = _group(tile)
    suit_n = Counter()
    has_chi = False
    for kind, group_tiles in _iter_melds(opened, kinds):
        if kind == "chi":
            has_chi = True
        for tid in group_tiles:
            suit_n[_group(tid)] += 1
    river_n = Counter(_group(t) for t in river)
    close = 1 + n_open
    if n_open >= 3:
        close += 3
    score = 0
    if suit_n[group] >= 3:
        score += 8
    elif suit_n[group] > 0:
        score += 4
    if n_open >= 1 and not has_chi and dumped == 0:
        score += 6 if is_honor(tile) else 2
    if opened.count(tile) >= 3:
        score += 3
    if dumped == 0:
        score += 2
    if group != "honor" and len(river) >= 4 and river_n[group] == 0:
        score += 3
    if river_n[group] >= 3:
        score -= 4
    if dumped >= 1:
        score -= 5
    return max(0, score) * close


def _public_feed(tile, seat, rivers, melds, n_melds, kinds_map):
    best = 0
    total = 0
    for other in SEATS:
        if other == seat:
            continue
        value = _need(other, tile, rivers, melds, n_melds, kinds_map)
        best = max(best, value)
        total += value
    live = sum(1 for other in SEATS if other != seat and tile not in rivers.get(other, []))
    return best, total, live


def _dadui_dist(hand, n_melds, kinds):
    if any(kind == "chi" for kind in (kinds or [])):
        return 8
    pairs = sum(1 for n in Counter(hand).values() if n >= 2)
    opened = sum(1 for kind in (kinds or []) if kind in ("peng", "gang", "an_gang", "ming_gang"))
    return max(0, 5 - pairs - opened)


def _big_shape(hand, n_melds, kinds, opened_tiles):
    sn = shanten(hand, n_melds=n_melds)
    qd = qidui_shanten([int(t) for t in hand]) if int(n_melds) == 0 else 8
    dadui = _dadui_dist(hand, n_melds, kinds)
    suits = Counter()
    for tile in list(hand) + list(opened_tiles or []):
        group = _group(tile)
        if group != "honor":
            suits[group] += 1
    main = max(suits.values()) if suits else 0
    wuji = 0 if not any(is_laizi(t) for t in hand) else 1
    return (min(sn, qd), min(qd, dadui), -main, wuji)


def pick_discard(
    hand, rivers=None, melds=None, n_melds=0, forbid=None,
    seat=1, meld_kinds=None, **kwargs,
):
    if not hand:
        return 0
    rivers = _as_map(rivers)
    melds = _as_map(melds)
    kinds_map = meld_kinds if isinstance(meld_kinds, dict) else _empty_map()
    own_kinds = _own_kinds(meld_kinds, seat)
    own_n = _own_n(n_melds, seat)
    own_melds = melds.get(seat, [])
    legal = [t for t, ok in zip(TILE_IDS, discard_legal_vec(hand, forbid=forbid)) if ok and t in hand]
    if not legal:
        return hand[0]

    def score(tile):
        nxt = _remove(hand, [tile])
        shape = _big_shape(nxt, own_n, own_kinds, own_melds)
        feed = _public_feed(tile, seat, rivers, melds, n_melds, kinds_map)
        return shape + tuple(-x for x in feed)

    return min(set(legal), key=score)


def pick_call(hand, offer, own_turn, n_melds, mask, wall_n, **kwargs):
    kinds = kwargs.get("meld_kinds") or []
    if isinstance(kinds, dict):
        kinds = kinds.get(kwargs.get("seat", 1), [])
    melds = kwargs.get("melds")
    after_gang = kwargs.get("after_gang", False)
    if mask[CALL_HU] and _is_big(_hu_info(hand, offer, own_turn, n_melds, kinds, melds, after_gang)):
        return CALL_HU
    if own_turn:
        return CALL_PASS
    if mask[CALL_PENG] and not any(kind == "chi" for kind in kinds):
        qd = qidui_shanten([int(t) for t in hand]) if int(n_melds) == 0 else 8
        std = shanten(hand, n_melds=n_melds, allow_qidui=False)
        if qd <= std and qd <= 2:
            return CALL_PASS
        return CALL_PENG
    return CALL_PASS


class GiveawayBots:
    def pick_discard(self, seat, dealer, hands, rivers, melds, n_melds, just_drew, forbid=None, **kwargs):
        return pick_discard(
            hands[seat], rivers, melds, n_melds, forbid=forbid,
            seat=seat, meld_kinds=kwargs.get("meld_kinds"),
        )

    def pick_call(self, seat, dealer, hands, rivers, melds, n_melds, offer, offer_seat, own_turn, just_drew, wall_n, **kwargs):
        own_melds = melds[seat] if isinstance(melds, dict) and seat in melds else None
        own_kinds = kwargs.get("meld_kinds")
        if isinstance(own_kinds, dict):
            own_kinds = own_kinds.get(seat, [])
        mask = legal_call_mask(
            hands[seat], offer, offer_seat, seat, own_turn=own_turn, n_melds=n_melds[seat],
            meld_kinds=own_kinds, blocked_hu=kwargs.get("blocked_hu"),
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
            meld_kinds=own_kinds, melds=own_melds, after_gang=kwargs.get("after_gang", False),
            seat=seat,
        )

    def want_bu_gang(self, hand, melds, kinds, wall_n=80, **kwargs):
        return None
