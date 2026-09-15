# -*- coding: utf-8 -*-
"""纯收割：能胡就胡，优先能点炮的牌型。"""
from collections import Counter

from harvest.fxj_rules import judge
from harvest.legal import legal_call_mask
from harvest.shanten import qidui_shanten, shanten
from harvest.tiles import (
    CALL_AN_GANG,
    CALL_CHI_HIGH,
    CALL_CHI_LOW,
    CALL_CHI_MID,
    CALL_HU,
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


def _chi_takes(offer, action):
    if action == CALL_CHI_HIGH:
        return [offer - 2, offer - 1]
    if action == CALL_CHI_MID:
        return [offer - 1, offer + 1]
    return [offer + 1, offer + 2]


def _remove(hand, tiles):
    out = list(hand)
    for tile in tiles:
        out.remove(tile)
    return out


def _empty_rivers():
    return {1: [], 2: [], 3: [], 4: []}


def _remain_ids(hand, rivers, melds):
    seen = Counter(hand)
    rivers = rivers or _empty_rivers()
    melds = melds or _empty_rivers()
    for seat in (1, 2, 3, 4):
        seen.update(rivers.get(seat, []))
        seen.update(melds.get(seat, []))
    return {tid: max(0, 4 - seen[tid]) for tid in TILE_IDS}


def _lonely_honor(hand, remain):
    best = None
    best_left = 99
    for tid in hand:
        if not is_honor(tid) or hand.count(tid) != 1:
            continue
        left = remain.get(tid, 0)
        if left < best_left:
            best_left = left
            best = tid
    return best


def _ukeire(hand, n_melds, remain):
    cur = shanten(hand, n_melds=n_melds)
    if cur < 0:
        return 32
    total = 0
    for tid, left in remain.items():
        if left <= 0:
            continue
        if shanten(hand + [tid], n_melds=n_melds) < cur:
            total += left
    return total


def _ron_wait(hand, n_melds, remain, meld_kinds):
    tiles = 0
    value = 0
    for tid, left in remain.items():
        if left <= 0:
            continue
        info = judge(
            hand, extra=tid, n_melds=n_melds, meld_kinds=meld_kinds,
            zimo=False, hu_tile=tid,
        )
        if info is None:
            continue
        if info["base"] == "平胡" and info["extra_fan"] == 0:
            continue
        tiles += left
        value += left * (1 + int(info["total_fan"]))
    return tiles, value


def _qidui_n(hand, n_melds):
    if int(n_melds) != 0:
        return 8
    return qidui_shanten([int(t) for t in hand])


def _protect_qidui(hand, n_melds):
    if int(n_melds) != 0:
        return False
    qd = _qidui_n(hand, 0)
    std = shanten(hand, n_melds=0, allow_qidui=False)
    return qd <= std and qd <= 2


def _protect_pengpeng(hand, n_melds, meld_kinds):
    kinds = meld_kinds or []
    if any(kind == "chi" for kind in kinds):
        return False
    pairs = sum(1 for n in Counter(hand).values() if n >= 2)
    opened = sum(1 for kind in kinds if kind in ("peng", "gang", "an_gang", "ming_gang"))
    return pairs + opened >= 4


def _threat(n_melds_all, seat, wall_n):
    if not n_melds_all:
        return 0
    other = max((n_melds_all[s] for s in n_melds_all if s != seat), default=0)
    if other >= 3 or wall_n <= 16:
        return 2
    if other >= 2 or wall_n <= 28:
        return 1
    return 0


def _safe_tile(tile, rivers):
    if not rivers:
        return False
    return any(tile in rivers[s] for s in rivers)


def _junk(hand, tile):
    if is_laizi(tile):
        return 9
    n = hand.count(tile)
    if is_honor(tile):
        return 0 if n == 1 else 6
    if n >= 3:
        return 7
    if n == 2:
        return 5
    suit, rank = suit_rank(tile)
    if suit is None:
        return 3
    near = [
        id_from_suit(suit, rank - 2),
        id_from_suit(suit, rank - 1),
        id_from_suit(suit, rank + 1),
        id_from_suit(suit, rank + 2),
    ]
    if not any(x in hand for x in near if x is not None):
        return 1 if rank in (1, 9) else 2
    return 4


def _keep_score(hand, n_melds, remain, meld_kinds):
    sn = shanten(hand, n_melds=n_melds)
    uke = _ukeire(hand, n_melds, remain)
    ron_t = ron_v = 0
    if sn == 0:
        ron_t, ron_v = _ron_wait(hand, n_melds, remain, meld_kinds)
    if sn == 0 and uke >= 30:
        speed = 200 + ron_t
    elif sn == 0:
        speed = min(uke, 24) + 6 * ron_t + 3 * ron_v
    else:
        speed = uke
        if sn == 1 and not any(is_laizi(t) for t in hand):
            speed += 4
    return sn, -speed, -ron_t, -uke


def _discard_score(hand, tile, n_melds, remain, rivers, meld_kinds, threat):
    nxt = _remove(hand, [tile])
    sn, neg_speed, neg_ron, _neg_uke = _keep_score(nxt, n_melds, remain, meld_kinds)
    ron_w = -neg_ron
    danger = 0
    if threat:
        if not _safe_tile(tile, rivers) and remain.get(tile, 0) > 0:
            if sn > 0:
                danger = threat
            elif ron_w == 0:
                danger = 1 if threat >= 2 else 0
    laizi = 1 if is_laizi(tile) else 0
    return (sn, neg_speed, danger, laizi, _junk(hand, tile), remain.get(tile, 0), tile)


def _best_discard(hand, n_melds, remain, rivers, meld_kinds, threat, forbid=None):
    legal = [t for t, ok in zip(TILE_IDS, discard_legal_vec(hand, forbid=forbid)) if ok and t in hand]
    if not legal:
        return hand[0], (8, 0, 0, 0, 0, 0, hand[0] if hand else 0)
    scored = [
        _discard_score(hand, tile, n_melds, remain, rivers, meld_kinds, threat)
        for tile in set(legal)
    ]
    scored.sort()
    honor = _lonely_honor(hand, remain)
    best = scored[0]
    if honor in legal:
        honor_row = _discard_score(hand, honor, n_melds, remain, rivers, meld_kinds, threat)
        if honor_row[0] == best[0] and honor_row[1] <= best[1] + 2:
            return honor, honor_row
    return best[-1], best


def pick_discard(
    hand, rivers, melds, n_melds, forbid=None, meld_kinds=None,
    n_melds_all=None, seat=1, wall_n=80,
):
    if not hand:
        return 0
    remain = _remain_ids(hand, rivers, melds)
    threat = _threat(n_melds_all, seat, wall_n)
    tile, _ = _best_discard(hand, n_melds, remain, rivers, meld_kinds, threat, forbid=forbid)
    return tile


def pick_call(
    hand, offer, own_turn, n_melds, mask, wall_n,
    rivers=None, melds=None, meld_kinds=None, n_melds_all=None, seat=1,
):
    if mask[CALL_HU]:
        return CALL_HU
    remain = _remain_ids(hand, rivers, melds)
    threat = _threat(n_melds_all, seat, wall_n)
    now = _keep_score(hand, n_melds, remain, meld_kinds)
    protect_qd = _protect_qidui(hand, n_melds)
    protect_pp = _protect_pengpeng(hand, n_melds, meld_kinds)

    if own_turn:
        if mask[CALL_AN_GANG] and wall_n > 0 and not protect_qd:
            for tile, n in Counter(hand).items():
                if n >= 4 and not is_laizi(tile):
                    after = shanten(_remove(hand, [tile] * 4), n_melds=n_melds + 1)
                    if after <= now[0]:
                        return CALL_AN_GANG
        return CALL_PASS

    if mask[CALL_MING_GANG] and wall_n > 0 and not is_laizi(offer) and not protect_qd:
        after_hand = _remove(hand, [offer, offer, offer])
        if shanten(after_hand, n_melds=n_melds + 1) <= now[0]:
            return CALL_MING_GANG

    best_action = CALL_PASS
    best = now

    def better(after, action):
        if after[0] < best[0]:
            return True
        if after[0] > best[0]:
            return False
        if after[2] < best[2]:
            return True
        need = 2 if action == CALL_PENG else 4
        return after[1] <= best[1] - need

    def consider(action, after_hand, after_melds, after_kinds, forbid=None):
        nonlocal best_action, best
        tile, _unused = _best_discard(
            after_hand, after_melds, remain, rivers, after_kinds, threat, forbid=forbid,
        )
        keep = _keep_score(_remove(after_hand, [tile]), after_melds, remain, after_kinds)
        if better(keep, action):
            best = keep
            best_action = action

    if mask[CALL_PENG] and not protect_qd:
        after_hand = _remove(hand, [offer, offer])
        after_kinds = list(meld_kinds or []) + ["peng"]
        consider(CALL_PENG, after_hand, n_melds + 1, after_kinds)

    if protect_qd or protect_pp:
        return best_action

    for action in CHI_ACTIONS:
        if not mask[action]:
            continue
        take = _chi_takes(offer, action)
        if not all(t in hand for t in take):
            continue
        after_hand = _remove(hand, take)
        after_kinds = list(meld_kinds or []) + ["chi"]
        consider(action, after_hand, n_melds + 1, after_kinds, forbid=offer)
    return best_action


pick_win_discard = pick_discard
pick_win_call = pick_call


class HarvestBots:
    def pick_discard(self, seat, dealer, hands, rivers, melds, n_melds, just_drew, forbid=None, **kwargs):
        return pick_discard(
            hands[seat], rivers, melds, n_melds[seat], forbid=forbid,
            meld_kinds=kwargs.get("meld_kinds"),
            n_melds_all=n_melds,
            seat=seat,
            wall_n=kwargs.get("wall_n", 80),
        )

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
            rivers=rivers, melds=melds, meld_kinds=kwargs.get("meld_kinds"),
            n_melds_all=n_melds, seat=seat,
        )

    def want_bu_gang(self, hand, melds, kinds, wall_n=80, **kwargs):
        if wall_n < 16 or _protect_qidui(hand, 0):
            return None
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
            before = shanten(hand, n_melds=len(kinds))
            after = shanten(_remove(hand, [tile]), n_melds=len(kinds))
            if after <= before:
                return tile
        return None


WinBots = HarvestBots
