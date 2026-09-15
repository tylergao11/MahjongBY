# -*- coding: utf-8 -*-
"""曲靖飞小鸡可吃场：只按 vendor/qjfxj RulesConfig_kechichang + AllRules。"""
from collections import Counter

from harvest.tiles import LAIZI_ID, TILE_IDS, is_honor, suit_rank
from harvest.wincheck import can_win as _std_win, is_pengpeng, is_qidui

BASE_STAKE = 1
WUMEIHUA = 37
HONORS = (49, 50, 51, 52, 65, 66, 67)
YAO_SHISAN = frozenset([1, 9, 17, 25, 33, 41] + list(HONORS))
GANG_KINDS = ("gang", "an_gang", "ming_gang")
OPEN_KINDS = ("chi", "peng", "gang", "ming_gang")

BASE_ORDER = (
    (3, "四小鸡"),
    (3, "龙抓背"),
    (3, "十三幺"),
    (3, "十风"),
    (2, "小七对"),
    (2, "七星烂牌"),
    (1, "大对"),
    (1, "烂牌"),
    (0, "平胡"),
)


def _tiles(hand, extra=None):
    tiles = [int(t) for t in hand]
    if extra is not None:
        tiles.append(int(extra))
    return tiles


def _n_laizi(hand, extra=None):
    n = sum(1 for t in hand if int(t) == LAIZI_ID)
    if extra is not None and int(extra) == LAIZI_ID:
        n += 1
    return n


def _gang_n(meld_kinds):
    return sum(1 for k in (meld_kinds or []) if k in GANG_KINDS)


def _open_n(meld_kinds):
    return sum(1 for k in (meld_kinds or []) if k in OPEN_KINDS)


def is_lanpai(hand, extra=None, n_melds=0, qixing=False):
    if int(n_melds) != 0:
        return False
    tiles = _tiles(hand, extra)
    if len(tiles) != 14 or len(set(tiles)) != 14:
        return False
    honors = [t for t in tiles if is_honor(t)]
    if len(honors) != len(set(honors)):
        return False
    by_suit = {"wan": [], "tiao": [], "tong": []}
    for t in tiles:
        if is_honor(t):
            continue
        suit, rank = suit_rank(t)
        if suit is None:
            return False
        by_suit[suit].append(rank)
    for ranks in by_suit.values():
        ranks.sort()
        if len(ranks) > 3:
            return False
        if len(ranks) == 2 and ranks[1] - ranks[0] not in (3, 6):
            return False
        if len(ranks) == 3 and not (ranks[1] == ranks[0] + 3 and ranks[2] == ranks[0] + 6):
            return False
    if qixing:
        return set(honors) == set(HONORS)
    return True


def is_long_qidui(hand, extra=None, n_melds=0):
    if not is_qidui(hand, extra=extra, n_melds=n_melds):
        return False
    tiles = [int(t) for t in hand if int(t) != LAIZI_ID]
    if extra is not None and int(extra) != LAIZI_ID:
        tiles.append(int(extra))
    elif extra is not None and int(extra) == LAIZI_ID:
        tiles.append(LAIZI_ID)
    return any(n >= 4 for n in Counter(tiles).values())


def can_win(hand, extra=None, n_melds=0):
    if _std_win(hand, extra=extra, n_melds=n_melds):
        return True
    return is_lanpai(hand, extra=extra, n_melds=n_melds) or is_lanpai(
        hand, extra=extra, n_melds=n_melds, qixing=True
    )


def _pure_self_laizi(hand, extra=None, n_melds=0, meld_kinds=None):
    """癞子只当一条本身。paixing501301"""
    from harvest.wincheck import _complete

    tiles = [int(t) for t in hand]
    if extra is not None:
        tiles.append(int(extra))
    if LAIZI_ID not in tiles:
        return False
    need = 4 - int(n_melds)
    if len(tiles) != need * 3 + 2:
        return False
    if all(n % 2 == 0 for n in Counter(tiles).values()) and need == 4:
        return True
    return _complete(tuple(sorted(tiles)), need, 0, 0)


def _qingyise(tiles):
    suits = set()
    for t in tiles:
        if is_honor(t):
            return False
        suit, _ = suit_rank(t)
        if suit:
            suits.add(suit)
    return len(suits) == 1


def _hunyise(tiles):
    suits = set()
    has_honor = False
    for t in tiles:
        if is_honor(t):
            has_honor = True
            continue
        suit, _ = suit_rank(t)
        if suit:
            suits.add(suit)
    return has_honor and len(suits) == 1


def _ziyise(tiles):
    return bool(tiles) and all(is_honor(t) for t in tiles)


def _pung_set(hand, extra, meld_kinds, melds):
    found = set()
    kinds = meld_kinds or []
    flat = list(melds or [])
    i = 0
    for kind in kinds:
        n = 4 if kind in GANG_KINDS else 3
        group = flat[i:i + n]
        i += n
        if group:
            found.add(int(group[0]))
    tiles = _tiles(hand, extra)
    for tid, n in Counter(tiles).items():
        if n >= 3:
            found.add(int(tid))
    return found


def _base_name(hand, extra, n_melds, meld_kinds, special=None):
    if special in ("十风", "十三幺"):
        return special
    if _n_laizi(hand, extra) >= 4 and int(n_melds) == 0:
        return "四小鸡"
    if is_long_qidui(hand, extra=extra, n_melds=n_melds):
        return "龙抓背"
    if is_qidui(hand, extra=extra, n_melds=n_melds):
        return "小七对"
    if is_lanpai(hand, extra=extra, n_melds=n_melds, qixing=True):
        return "七星烂牌"
    if is_lanpai(hand, extra=extra, n_melds=n_melds):
        return "烂牌"
    if is_pengpeng(hand, extra=extra, n_melds=n_melds, meld_kinds=meld_kinds):
        return "大对"
    if _std_win(hand, extra=extra, n_melds=n_melds):
        return "平胡"
    return None


def extra_fans(
    hand, extra=None, n_melds=0, meld_kinds=None, melds=None,
    zimo=False, after_gang=False, qiang_gang=False, hu_tile=None,
):
    extras = []
    kinds = meld_kinds or []
    tiles = _tiles(hand, extra)
    gangs = _gang_n(kinds)
    opens = _open_n(kinds)
    an_only = kinds and all(k == "an_gang" for k in kinds)
    closed = opens == 0

    if zimo and (closed or (after_gang and an_only)):
        extras.append(("门前清", 1))
    if "an_gang" not in kinds and opens >= 4:
        extras.append(("全求人", 1))
    if after_gang and zimo:
        extras.append(("杠上花", 1))
        if gangs:
            extras.append(("杠加番", gangs))
        if hu_tile in (WUMEIHUA, LAIZI_ID):
            extras.append(("杠上五梅花", 2))
    elif qiang_gang:
        extras.append(("杠上炮", 1))
    elif gangs >= 2:
        extras.append(("杠加番", gangs // 2))
    if after_gang and not zimo:
        extras.append(("杠上炮", 1))
    if _n_laizi(hand, extra) == 0:
        extras.append(("无鸡", 1))
    elif _pure_self_laizi(hand, extra=extra, n_melds=n_melds, meld_kinds=kinds):
        extras.append(("小鸡归位", 1))
    if _qingyise(tiles):
        extras.append(("清一色", 2))
    elif _hunyise(tiles):
        extras.append(("混一色", 1))
    if _ziyise(tiles):
        extras.append(("字一色", 2))
    pungs = _pung_set(hand, extra, kinds, melds)
    if {65, 66, 67} <= pungs:
        extras.append(("大三元", 3))
    if {49, 50, 51, 52} <= pungs:
        extras.append(("大四喜", 3))
    merged = {}
    for name, fan in extras:
        merged[name] = max(merged.get(name, 0), fan)
    return [(name, fan) for name, fan in merged.items()]


def judge(
    hand, extra=None, n_melds=0, meld_kinds=None, melds=None,
    zimo=False, after_gang=False, qiang_gang=False, hu_tile=None, special=None,
):
    if special not in ("十风", "十三幺") and not can_win(hand, extra=extra, n_melds=n_melds):
        return None
    base = _base_name(hand, extra, n_melds, meld_kinds, special=special)
    if base is None:
        return None
    base_fan = next(fan for fan, name in BASE_ORDER if name == base)
    extras = extra_fans(
        hand, extra=extra, n_melds=n_melds, meld_kinds=meld_kinds, melds=melds,
        zimo=zimo, after_gang=after_gang, qiang_gang=qiang_gang, hu_tile=hu_tile,
    )
    if base in ("小七对", "龙抓背", "烂牌", "七星烂牌", "十风", "十三幺", "四小鸡"):
        extras = [(n, f) for n, f in extras if n not in ("门前清",)]
    extra_fan = sum(f for _, f in extras)
    total = base_fan + extra_fan
    return {
        "ok": True,
        "base": base,
        "base_fan": base_fan,
        "extras": extras,
        "extra_fan": extra_fan,
        "total_fan": total,
        "money": BASE_STAKE * (2 ** total),
    }


def _any_wait_laizi(hand, n_melds, meld_kinds):
    if sum(1 for t in hand if int(t) == LAIZI_ID) == 0:
        return False
    hits = 0
    for tid in TILE_IDS:
        if _std_win(hand, extra=tid, n_melds=n_melds):
            hits += 1
    return hits >= 30


def can_ron(
    hand, extra=None, n_melds=0, meld_kinds=None, melds=None,
    after_gang=False, qiang_gang=False, passed_fan=None, hu_tile=None,
    skip_any_wait=False,
):
    """hupai710111 / hupai400004 / hupai725105。抢杠不受平胡点炮限制。"""
    info = judge(
        hand, extra=extra, n_melds=n_melds, meld_kinds=meld_kinds, melds=melds,
        zimo=False, after_gang=after_gang, qiang_gang=qiang_gang or after_gang,
        hu_tile=hu_tile if hu_tile is not None else extra,
    )
    if info is None:
        return False
    if (not skip_any_wait) and _any_wait_laizi(hand, n_melds, meld_kinds):
        if extra != LAIZI_ID and not _pure_self_laizi(hand, extra=extra, n_melds=n_melds):
            return False
    if not (qiang_gang or after_gang):
        if info["base"] == "平胡" and info["extra_fan"] == 0:
            return False
    if passed_fan is not None and info["total_fan"] <= int(passed_fan):
        return False
    return True


def ron_fan(hand, extra=None, n_melds=0, meld_kinds=None, melds=None, after_gang=False):
    info = judge(
        hand, extra=extra, n_melds=n_melds, meld_kinds=meld_kinds, melds=melds,
        zimo=False, after_gang=after_gang, qiang_gang=after_gang, hu_tile=extra,
    )
    return info["total_fan"] if info else -1


def liuju_left(gang_count):
    """liuju200002"""
    rem = int(gang_count) % 3
    if rem == 0:
        return 20
    if rem == 1:
        return 14
    return 16


def is_shifeng_tile(tile):
    return is_honor(tile)


def is_shisan_tile(tile):
    return int(tile) in YAO_SHISAN


def underground_hu(river, meld_n):
    if meld_n:
        return None
    if not river:
        return None
    if len(river) == 10 and all(is_shifeng_tile(t) for t in river):
        return "十风"
    if len(river) == 13 and all(is_shisan_tile(t) for t in river):
        return "十三幺"
    return None


def settle(winners, from_seat, zimo, qiang_gang, judgments):
    """jiesuan101111/101211/101221/101234/101321/101402。底注*2^N。"""
    scores = {1: 0, 2: 0, 3: 0, 4: 0}
    details = []
    others = [s for s in (1, 2, 3, 4) if s not in winners]
    for seat in winners:
        info = judgments[seat]
        pay = info["money"]
        names = [info["base"]] + [n for n, _ in info["extras"]]
        if qiang_gang and from_seat:
            scores[from_seat] -= pay * 3
            scores[seat] += pay * 3
            payers = [from_seat, from_seat, from_seat]
        elif zimo:
            for o in others:
                scores[o] -= pay
                scores[seat] += pay
            payers = list(others)
        else:
            shooter = from_seat
            scores[shooter] -= pay
            scores[seat] += pay
            payers = [shooter]
        details.append({
            "seat": seat,
            "base": info["base"],
            "fan": info["total_fan"],
            "names": names,
            "pay": pay,
            "payers": payers,
        })
    return {"scores": scores, "details": details, "stake": BASE_STAKE}


def pick_gang_tile(hand, n_melds, pool):
    if not pool:
        return None
    from harvest.shanten import shanten
    best = pool[0]
    best_sn = 99
    for tile in pool:
        sn = shanten(list(hand) + [tile], n_melds=n_melds)
        if sn < best_sn:
            best_sn = sn
            best = tile
    return best
