# -*- coding: utf-8 -*-
"""4-meld + pair shanten, plus 七对. 一条 (妖姬) is wild in the closed hand."""
from collections import Counter
from functools import lru_cache

from harvest.tiles import LAIZI_ID, LAIZI_IDX, TILE_TO_IDX, tile_idx
from harvest.wincheck import can_win


def shanten(hand, extra=None, n_melds=0, allow_qidui=True):
    if can_win(hand, extra=extra, n_melds=n_melds):
        return -1
    tiles = [int(t) for t in hand]
    locked = 0
    if extra is not None:
        extra = int(extra)
        if extra == LAIZI_ID:
            locked = 1
        else:
            tiles.append(extra)
    need = 4 - int(n_melds)
    if need < 0:
        return 8
    cnt = [0] * 34
    for tile in tiles:
        idx = tile_idx(tile)
        if idx is not None:
            cnt[idx] += 1
    wilds = cnt[LAIZI_IDX]
    if locked:
        cnt[LAIZI_IDX] += 1
    as_tiao = _from_counts(tuple(cnt), need, 0)
    if wilds == 0:
        best = as_tiao
    else:
        stripped = list(cnt)
        stripped[LAIZI_IDX] = locked
        best = min(as_tiao, _from_counts(tuple(stripped), need, wilds))
    if allow_qidui and need == 4:
        best = min(best, qidui_shanten(tiles, locked_tiao=locked))
    if best < 0:
        return 0
    return best


def locked_shanten(hand, n_melds=0):
    """Treat 一条 as 1-bamboo, not as a wild."""
    tiles = list(hand)
    need = 4 - int(n_melds)
    if need < 0:
        return 8
    cnt = [0] * 34
    for tile in tiles:
        idx = tile_idx(tile)
        if idx is not None:
            cnt[idx] += 1
    return _from_counts(tuple(cnt), need, 0)


def qidui_shanten(tiles, locked_tiao=0):
    wilds = sum(1 for t in tiles if int(t) == LAIZI_ID)
    counts = Counter(int(t) for t in tiles if int(t) != LAIZI_ID)
    if locked_tiao:
        counts[LAIZI_ID] += int(locked_tiao)
    pairs = 0
    odd = 0
    for n in counts.values():
        pairs += n // 2
        odd += n % 2
    use = min(odd, wilds)
    pairs += use
    wilds -= use
    pairs += wilds // 2
    return max(-1, 6 - pairs)


def discard_shanten_vec(hand, n_melds=0):
    """Per-tile shanten after discarding one copy. Missing tiles stay 1.0."""
    out = [1.0] * 34
    uniq = set()
    for tile in hand:
        idx = tile_idx(tile)
        if idx is not None:
            uniq.add((idx, tile))
    if not uniq:
        return out
    for idx, tile in uniq:
        remain = list(hand)
        remain.remove(tile)
        out[idx] = min(1.0, (shanten(remain, n_melds=n_melds) + 1) / 9.0)
    return out


def _from_counts(cnt, need, wilds=0):
    if wilds:
        return _search_w(cnt, 0, 0, 0, 0, need, wilds)
    return _search(cnt, 0, 0, 0, 0, need)


@lru_cache(maxsize=200000)
def _search(cnt, pos, mentsu, tatsu, pair, need):
    while pos < 34 and cnt[pos] == 0:
        pos += 1
    if pos >= 34:
        return _eval(mentsu, tatsu, pair, need)

    best = 8
    n = cnt[pos]
    honor = pos >= 27

    if n >= 3:
        best = min(best, _search(_add(cnt, pos, -3), pos, mentsu + 1, tatsu, pair, need))
    if n >= 2:
        if not pair:
            best = min(best, _search(_add(cnt, pos, -2), pos, mentsu, tatsu, 1, need))
        best = min(best, _search(_add(cnt, pos, -2), pos, mentsu, tatsu + 1, pair, need))
    if not honor and pos % 9 <= 6:
        a, b = pos + 1, pos + 2
        if cnt[a] and cnt[b]:
            nxt = _add(_add(_add(cnt, pos, -1), a, -1), b, -1)
            best = min(best, _search(nxt, pos, mentsu + 1, tatsu, pair, need))
    if not honor and pos % 9 <= 7 and cnt[pos + 1]:
        nxt = _add(_add(cnt, pos, -1), pos + 1, -1)
        best = min(best, _search(nxt, pos, mentsu, tatsu + 1, pair, need))
    if not honor and pos % 9 <= 6 and cnt[pos + 2]:
        nxt = _add(_add(cnt, pos, -1), pos + 2, -1)
        best = min(best, _search(nxt, pos, mentsu, tatsu + 1, pair, need))

    leftover = n
    best = min(best, _search(_add(cnt, pos, -leftover), pos + 1, mentsu, tatsu, pair, need))
    return best


@lru_cache(maxsize=300000)
def _search_w(cnt, pos, mentsu, tatsu, pair, need, wilds):
    while pos < 34 and (cnt[pos] == 0 or pos == LAIZI_IDX):
        pos += 1
    if pos >= 34:
        return _eval_w(mentsu, tatsu, pair, need, wilds)

    best = 8
    n = cnt[pos]
    honor = pos >= 27

    for w in range(0, 3):
        used = 3 - w
        if used <= n and w <= wilds and used >= 1:
            best = min(best, _search_w(_add(cnt, pos, -used), pos, mentsu + 1, tatsu, pair, need, wilds - w))
    if n >= 2:
        if not pair:
            best = min(best, _search_w(_add(cnt, pos, -2), pos, mentsu, tatsu, 1, need, wilds))
        best = min(best, _search_w(_add(cnt, pos, -2), pos, mentsu, tatsu + 1, pair, need, wilds))
    if n >= 1 and wilds >= 1:
        if not pair:
            best = min(best, _search_w(_add(cnt, pos, -1), pos, mentsu, tatsu, 1, need, wilds - 1))
        best = min(best, _search_w(_add(cnt, pos, -1), pos, mentsu, tatsu + 1, pair, need, wilds - 1))
    if not honor:
        best = min(best, _chow_w(cnt, pos, mentsu, tatsu, pair, need, wilds))

    leftover = n
    best = min(best, _search_w(_add(cnt, pos, -leftover), pos + 1, mentsu, tatsu, pair, need, wilds))
    return best


def _chow_w(cnt, pos, mentsu, tatsu, pair, need, wilds):
    best = 8
    rank = pos % 9
    for start in (rank, rank - 1, rank - 2):
        if start < 0 or start > 6:
            continue
        base = pos - rank + start
        ids = (base, base + 1, base + 2)
        if pos not in ids:
            continue
        nxt = cnt
        wneed = 0
        ok = True
        took_pos = False
        for idx in ids:
            if idx == LAIZI_IDX:
                wneed += 1
                continue
            if nxt[idx] > 0:
                nxt = _add(nxt, idx, -1)
                if idx == pos:
                    took_pos = True
            else:
                wneed += 1
        if not took_pos or wneed > wilds:
            continue
        best = min(best, _search_w(nxt, pos, mentsu + 1, tatsu, pair, need, wilds - wneed))
        if wneed == 1:
            best = min(best, _search_w(nxt, pos, mentsu, tatsu + 1, pair, need, wilds - wneed))
    return best


def _eval(mentsu, tatsu, pair, need):
    mentsu = min(mentsu, need)
    room = need - mentsu
    tatsu = min(tatsu, room)
    if pair:
        return max(-1, 2 * room - tatsu - 1)
    return max(0, 2 * room - tatsu)


def _eval_w(mentsu, tatsu, pair, need, wilds):
    mentsu = min(mentsu, need)
    room = need - mentsu
    up = min(room, tatsu, wilds)
    mentsu += up
    tatsu -= up
    wilds -= up
    room = need - mentsu
    more = min(room, wilds // 3)
    mentsu += more
    wilds -= more * 3
    room = need - mentsu
    if room and wilds >= 2:
        tatsu += 1
        wilds -= 2
        room = need - mentsu
        tatsu = min(tatsu, room)
    if not pair:
        if wilds >= 2:
            pair = 1
            wilds -= 2
        elif wilds >= 1:
            pair = 1
            wilds -= 1
    room = need - min(mentsu, need)
    tatsu = min(tatsu, room)
    if pair:
        return max(-1, 2 * room - tatsu - 1)
    return max(0, 2 * room - tatsu)


def _add(cnt, pos, delta):
    lst = list(cnt)
    lst[pos] += delta
    return tuple(lst)


assert TILE_TO_IDX[67] == 33
assert LAIZI_IDX == 9
