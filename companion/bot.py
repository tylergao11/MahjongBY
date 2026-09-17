# -*- coding: utf-8 -*-
"""陪玩：线上普通人打法。能胡就胡。不抠点炮、不算向听效率。"""
from collections import Counter

from harvest.legal import legal_call_mask
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
    is_laizi,
)

FACE_VALUE = {1: 0, 9: 0, 2: 1, 8: 1, 3: 2, 7: 2, 4: 3, 5: 3, 6: 4}
REMAIN_VALUE = {n: n for n in range(13)}


def to_byte(tid):
    tid = int(tid)
    if 1 <= tid <= 9:
        return tid
    if 17 <= tid <= 25:
        return 0x20 + (tid - 16)
    if 33 <= tid <= 41:
        return 0x10 + (tid - 32)
    return {49: 0x31, 50: 0x32, 51: 0x33, 52: 0x34, 65: 0x41, 66: 0x42, 67: 0x43}[tid]


def from_byte(byte):
    row, col = byte >> 4, byte & 0x0F
    if row == 0:
        return col
    if row == 1:
        return 32 + col
    if row == 2:
        return 16 + col
    if row == 3:
        return {1: 49, 2: 50, 3: 51, 4: 52}[col]
    return {1: 65, 2: 66, 3: 67}[col]


def _row_col(byte):
    return byte >> 4, byte & 0x0F


def _sorted_bytes(hand):
    return sorted(to_byte(t) for t in hand)


def _matrix(hand):
    grid = [[0] * 10 for _ in range(6)]
    for tid in hand:
        row, col = _row_col(to_byte(tid))
        grid[row][col] += 1
    for row in range(6):
        grid[row][0] = sum(grid[row][1:])
    return grid


def _remain_bytes(hand, rivers, melds):
    seen = Counter(hand)
    rivers = rivers or {}
    melds = melds or {}
    for seat in (1, 2, 3, 4):
        seen.update(rivers.get(seat, []))
        seen.update(melds.get(seat, []))
    out = {}
    for tid in TILE_IDS:
        out[to_byte(tid)] = max(0, 4 - seen[tid])
    return out


def _groups(bytes_sorted):
    used = [False] * len(bytes_sorted)
    incomplete = {i: [] for i in range(1, 7)}

    def unused_from(start):
        for i in range(start, len(bytes_sorted)):
            if not used[i]:
                return i
        return None

    def ended():
        return all(used)

    def kezi(idx):
        card = bytes_sorted[idx]
        group = [card]
        for i in range(idx + 1, len(bytes_sorted)):
            if bytes_sorted[i] > card:
                break
            if not used[i] and bytes_sorted[i] == card:
                group.append(card)
                used[i] = True
                if len(group) == 3:
                    used[idx] = True
                    incomplete[6].append(card)
                    return True
        if len(group) == 2:
            used[idx] = True
            incomplete[3].append(card)
            return True
        return False

    def shunzi(idx):
        card = bytes_sorted[idx]
        if card > 0x30:
            return False
        plus1 = plus2 = False
        for i in range(idx + 1, len(bytes_sorted)):
            nxt = bytes_sorted[i]
            if nxt > card + 2:
                break
            if used[i]:
                continue
            if nxt == card + 1:
                used[i] = True
                plus1 = True
            elif nxt == card + 2:
                used[i] = True
                plus2 = True
                used[idx] = True
                if plus1:
                    incomplete[2].extend([card, card + 1, card + 2])
                else:
                    incomplete[4].extend([card, card + 2])
                return True
        if plus1:
            used[idx] = True
            incomplete[5].extend([card, card + 1])
            return True
        return False

    def walk(idx):
        if not kezi(idx) and not shunzi(idx):
            used[idx] = True
            incomplete[1].append(bytes_sorted[idx])
        if ended():
            return
        nxt = unused_from(idx + 1)
        if nxt is not None:
            walk(nxt)

    first = unused_from(0)
    if first is not None:
        walk(first)
    return incomplete


def _suit_values(matrix):
    rows = [(matrix[i][0], i) for i in range(3)]
    rows.sort(key=lambda item: item[0])
    values = {3: 0, 4: 0, 5: 0}
    for score, (_, row) in enumerate(rows):
        values[row] = score
    return values


def _is_isolated(matrix, row, col):
    if matrix[row][col] != 1:
        return False
    left1 = col <= 1 or not matrix[row][col - 1]
    left2 = col <= 2 or not matrix[row][col - 2]
    right1 = col + 1 > 9 or not matrix[row][col + 1]
    right2 = col + 2 > 9 or not matrix[row][col + 2]
    return left1 and left2 and right1 and right2


def _card_value(byte, remain, suit_values, matrix):
    row, col = _row_col(byte)
    if row >= 6 or col <= 0 or col >= 10:
        return 0
    need = [byte - 1, byte + 1]
    kezi = REMAIN_VALUE.get(remain.get(byte, 0), 12)
    shun = 0
    for need_b in need:
        shun += REMAIN_VALUE.get(remain.get(need_b, 0), 12)
    return kezi + shun + suit_values.get(row, 0) + FACE_VALUE.get(col, 0)


def _min_card(cards, remain, suit_values, matrix, blocked):
    ranked = []
    for byte in cards:
        if byte in blocked:
            continue
        ranked.append((_card_value(byte, remain, suit_values, matrix), byte))
    if not ranked:
        return 0
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return ranked[-1][1]


def _min_from_pairs(cards, remain, suit_values, matrix, blocked, gap=False):
    ranked = []
    for i in range(0, len(cards) - 1, 2):
        a, b = cards[i], cards[i + 1]
        if a in blocked or b in blocked:
            continue
        need = [a + 1] if gap else [a - 1, b + 1]
        value = 0
        for byte in (a, b):
            row, col = _row_col(byte)
            kezi = REMAIN_VALUE.get(remain.get(byte, 0), 12)
            shun = sum(REMAIN_VALUE.get(remain.get(n, 0), 12) for n in need)
            value += kezi + shun + suit_values.get(row, 0) + FACE_VALUE.get(col, 0)
        ranked.append((value, [a, b]))
    if not ranked:
        return 0
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return _min_card(ranked[-1][1], remain, suit_values, matrix, blocked)


def _honor_discard(hand, remain):
    matrix = _matrix(hand)
    best = None
    best_left = 99
    for tid in hand:
        byte = to_byte(tid)
        row, col = _row_col(byte)
        if row not in (3, 4) or matrix[row][col] != 1:
            continue
        left = remain.get(byte, 0)
        if left < best_left:
            best_left = left
            best = tid
    return best


def pick_discard(hand, rivers=None, melds=None, n_melds=0, forbid=None, **kwargs):
    if not hand:
        return 0
    legal = [t for t, ok in zip(TILE_IDS, discard_legal_vec(hand, forbid=forbid)) if ok and t in hand]
    if not legal:
        return hand[0]
    remain = _remain_bytes(hand, rivers, melds)
    honor = _honor_discard(hand, remain)
    if honor in legal:
        return honor
    matrix = _matrix(hand)
    suit_values = _suit_values(matrix)
    groups = _groups(_sorted_bytes(hand))
    allowed = {to_byte(t) for t in legal}
    singles = list(groups[1])
    isolated = []
    leftover = []
    for byte in reversed(singles):
        if byte not in allowed:
            leftover.insert(0, byte)
            continue
        row, col = _row_col(byte)
        if matrix[row][0] == 1:
            return from_byte(byte)
        if _is_isolated(matrix, row, col):
            isolated.append(byte)
        else:
            leftover.insert(0, byte)
    for bucket in (isolated, leftover):
        chosen = _min_card(bucket, remain, suit_values, matrix, set())
        if chosen and chosen in allowed:
            return from_byte(chosen)
    edge = _min_from_pairs(groups[5], remain, suit_values, matrix, set())
    if edge and edge in allowed:
        return from_byte(edge)
    gap = _min_from_pairs(groups[4], remain, suit_values, matrix, set(), gap=True)
    if gap and gap in allowed:
        return from_byte(gap)
    pairs = groups[2]
    seqs = groups[3]
    if len(pairs) <= 1:
        seq = _min_from_pairs(seqs, remain, suit_values, matrix, set())
        if seq and seq in allowed:
            return from_byte(seq)
        pair = _min_from_pairs(pairs, remain, suit_values, matrix, set())
        if pair and pair in allowed:
            return from_byte(pair)
    else:
        pair = _min_from_pairs(pairs, remain, suit_values, matrix, set())
        if pair and pair in allowed:
            return from_byte(pair)
    return legal[0]


def _group_score(incomplete):
    return (
        len(incomplete[5])
        + len(incomplete[4])
        + len(incomplete[3])
        + len(incomplete[2])
        + len(incomplete[1]) * 2
    )


def chi_improves(hand, take):
    before = _groups(_sorted_bytes(hand))
    after_hand = list(hand)
    for tile in take:
        after_hand.remove(tile)
    after = _groups(_sorted_bytes(after_hand))
    for key in (1, 2, 3, 4):
        if after[key]:
            after[key].pop()
            break
    return _group_score(after) < _group_score(before)


def should_peng(hand, offer):
    byte = to_byte(offer)
    row, col = _row_col(byte)
    if row in (3, 4):
        return True
    matrix = _matrix(hand)
    left_open = col - 1 < 1 or matrix[row][col - 1] == 0
    right_open = col + 1 > 9 or matrix[row][col + 1] == 0
    return left_open or right_open


def _chi_takes(offer, action):
    if action == CALL_CHI_HIGH:
        return [offer - 2, offer - 1]
    if action == CALL_CHI_MID:
        return [offer - 1, offer + 1]
    return [offer + 1, offer + 2]


def pick_call(hand, offer, own_turn, n_melds, mask, wall_n, **kwargs):
    if mask[CALL_HU]:
        return CALL_HU
    if own_turn:
        if mask[CALL_AN_GANG] and wall_n > 0:
            for tile, n in Counter(hand).items():
                if n >= 4 and not is_laizi(tile):
                    return CALL_AN_GANG
        return CALL_PASS
    if mask[CALL_MING_GANG] and wall_n > 0 and not is_laizi(offer):
        return CALL_MING_GANG
    if mask[CALL_PENG] and should_peng(hand, offer):
        return CALL_PENG
    rank = offer - 16 if 17 <= offer <= 25 else offer - 32 if 33 <= offer <= 41 else offer
    order = (CALL_CHI_LOW, CALL_CHI_MID, CALL_CHI_HIGH) if rank in (7, 8) else (
        CALL_CHI_HIGH, CALL_CHI_MID, CALL_CHI_LOW
    )
    for action in order:
        if not mask[action]:
            continue
        take = _chi_takes(offer, action)
        if all(t in hand for t in take) and chi_improves(hand, take):
            return action
    return CALL_PASS


class CompanionBots:
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
        return pick_call(hands[seat], offer, own_turn, n_melds[seat], mask, wall_n)

    def want_bu_gang(self, hand, melds, kinds, wall_n=80, **kwargs):
        i = 0
        for kind in kinds:
            n = 4 if kind in ("gang", "an_gang", "ming_gang") else 3
            group = melds[i:i + n]
            i += n
            if kind == "peng" and group and group[0] in hand:
                return group[0]
        return None
