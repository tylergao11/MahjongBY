# -*- coding: utf-8 -*-
"""Replay fxj ops and snapshot discard + chi/peng/gang/pass."""
from collections import Counter

from train.tiles import (
    CALL_AN_GANG,
    CALL_CHI_HIGH,
    CALL_CHI_LOW,
    CALL_CHI_MID,
    CALL_HU,
    CALL_MING_GANG,
    CALL_PASS,
    CALL_PENG,
    CODE_TO_CALL,
    LAIZI_IDX,
    N_CALL,
    counts_from_list,
    discard_legal_vec,
    is_honor,
    is_laizi,
    next_seat,
    one_hot_tile,
    suit_rank,
    tile_idx,
)
from train.shanten import discard_shanten_vec, locked_shanten, qidui_shanten, shanten
from harvest.legal import can_chi_high, can_chi_low, can_chi_mid, legal_call_mask
from train.wincheck import can_ron, can_win

HONORS = (49, 50, 51, 52, 65, 66, 67)
WINDS = (49, 50, 51, 52)


def parse_tiles(text):
    text = (text or "").strip().strip(",")
    if not text:
        return []
    out = []
    for part in text.split(","):
        part = part.strip()
        if part.isdigit():
            out.append(int(part))
    return out


def parse_ops(ops):
    items = []
    for raw in (ops or "").split("|"):
        raw = raw.strip()
        if not raw:
            continue
        if "-" not in raw:
            items.append({"code": raw, "seat": None, "tiles": [], "payload": ""})
            continue
        code, rest = raw.split("-", 1)
        seat = None
        tiles = []
        payload = rest
        if code in ("111", "115", "200"):
            payload = rest
        elif code == "201":
            payload = rest
            if rest and rest[0].isdigit():
                seat = int(rest[0])
        elif rest:
            if ":" in rest:
                left, right = rest.split(":", 1)
                if left.isdigit():
                    seat = int(left)
                    tiles = parse_tiles(right)
                    payload = right
            elif rest.isdigit():
                seat = int(rest)
            else:
                tiles = parse_tiles(rest)
        items.append({"code": code, "seat": seat, "tiles": tiles, "payload": payload})
    return items


def _modal_tile(tiles):
    if not tiles:
        return None
    return Counter(tiles).most_common(1)[0][0]


def _take(hand, tiles):
    for tile in tiles:
        if tile in hand:
            hand.remove(tile)


def _count(hand, tile):
    return sum(1 for x in hand if x == tile)


def _hand_shape(hand):
    counts = Counter(hand)
    isolated = sum(1 for n in counts.values() if n == 1)
    pairs = sum(1 for n in counts.values() if n >= 2)
    honors = sum(1 for t in hand if is_honor(t))
    wan = sum(1 for t in hand if 1 <= t <= 9)
    tiao = sum(1 for t in hand if 17 <= t <= 25)
    tong = sum(1 for t in hand if 33 <= t <= 41)
    missing = int(wan == 0) + int(tiao == 0) + int(tong == 0)
    return [
        isolated / 14.0,
        pairs / 7.0,
        honors / 14.0,
        wan / 14.0,
        tiao / 14.0,
        tong / 14.0,
        missing / 3.0,
    ]


def seat_wind_tile(seat, dealer):
    return WINDS[(int(seat) - int(dealer)) % 4]


def _visible_tiles(rivers, melds):
    out = []
    for s in range(1, 5):
        out.extend(rivers[s])
        out.extend(melds[s])
    return out


def call_extra_features(hand, offer, offer_seat, seat, mask, rivers=None, n_melds=0, melds=None):
    """Chi neighbors, offer count, legal bits — so 吃/明杠不再被过和碰淹没。"""
    extra = list(mask)
    extra.append(1.0 if offer_seat is not None and seat == next_seat(offer_seat) else 0.0)
    n = _count(hand, offer) if offer is not None else 0
    extra.extend([n / 4.0, 1.0 if n >= 2 else 0.0, 1.0 if n >= 3 else 0.0, 1.0 if n >= 4 else 0.0])
    suit_oh = [0.0, 0.0, 0.0, 0.0]
    neigh = [0.0, 0.0, 0.0, 0.0]
    rank_n = 0.0
    chi_flags = [0.0, 0.0, 0.0]
    if offer is not None:
        suit, rank = suit_rank(offer)
        if suit == "wan":
            suit_oh[0] = 1.0
        elif suit == "tiao":
            suit_oh[1] = 1.0
        elif suit == "tong":
            suit_oh[2] = 1.0
        else:
            suit_oh[3] = 1.0
        if rank is not None:
            rank_n = rank / 9.0
        if suit is not None and rank is not None:
            for i, delta in enumerate((-2, -1, 1, 2)):
                rr = rank + delta
                if 1 <= rr <= 9:
                    neigh[i] = _count(hand, offer + delta) / 4.0
        chi_flags = [
            1.0 if can_chi_high(hand, offer) else 0.0,
            1.0 if can_chi_mid(hand, offer) else 0.0,
            1.0 if can_chi_low(hand, offer) else 0.0,
        ]
    extra.extend(suit_oh)
    extra.append(rank_n)
    extra.extend(neigh)
    extra.extend(chi_flags)
    extra.extend(_chi_cost(hand, offer))
    extra.extend(_chi_shanten(hand, offer, n_melds, rivers, melds))
    return extra


def _chi_needed(offer, kind):
    if kind == "high":
        return [offer - 2, offer - 1]
    if kind == "mid":
        return [offer - 1, offer + 1]
    return [offer + 1, offer + 2]


def _chi_cost(hand, offer):
    """Each legal chi: pair-break count and leftover isolates after taking it."""
    out = []
    for kind, ok in (
        ("high", offer is not None and can_chi_high(hand, offer)),
        ("mid", offer is not None and can_chi_mid(hand, offer)),
        ("low", offer is not None and can_chi_low(hand, offer)),
    ):
        if not ok:
            out.extend([0.0, 0.0])
            continue
        need = _chi_needed(offer, kind)
        pair_break = sum(1.0 for t in need if _count(hand, t) == 2) / 2.0
        remain = list(hand)
        for t in need:
            if t in remain:
                remain.remove(t)
        isolated = sum(1 for n in Counter(remain).values() if n == 1) / 14.0
        out.extend([pair_break, isolated])
    return out


def _chi_shanten(hand, offer, n_melds, rivers, melds=None):
    rivers = rivers or {s: [] for s in range(1, 5)}
    melds = melds or {s: [] for s in range(1, 5)}
    vis = Counter(_visible_tiles(rivers, melds))
    before = shanten(hand, n_melds=n_melds)
    out = [
        (before + 1) / 9.0,
        n_melds / 4.0,
        1.0 if n_melds else 0.0,
        sum(len(rivers[s]) for s in range(1, 5)) / 80.0,
    ]
    if offer is None:
        out.extend([0.0, 0.0, 0.0])
    else:
        rank = suit_rank(offer)[1]
        out.extend([
            vis[offer] / 4.0,
            max(0.0, (4 - _count(hand, offer) - vis[offer]) / 4.0),
            1.0 if rank in (1, 9) else 0.0,
        ])
    best_help = 0.0
    for kind, ok in (
        ("high", offer is not None and can_chi_high(hand, offer)),
        ("mid", offer is not None and can_chi_mid(hand, offer)),
        ("low", offer is not None and can_chi_low(hand, offer)),
    ):
        if not ok:
            out.extend([0.0, 0.0, 0.0])
            continue
        remain = list(hand)
        need = _chi_needed(offer, kind)
        for tile in need:
            if tile in remain:
                remain.remove(tile)
        after = shanten(remain, n_melds=n_melds + 1)
        help_n = max(0.0, (before - after) / 3.0)
        best_help = max(best_help, help_n)
        need_left = sum(max(0, 4 - _count(hand, tile) - vis[tile]) for tile in need) / 8.0
        out.extend([(after + 1) / 9.0, help_n, need_left])
    out.append(best_help)
    out.append(1.0 if best_help > 0 else 0.0)
    return out


def build_call_features(seat, dealer, hands, rivers, melds, mask, offer=None, offer_seat=None, just_drew=0, n_melds=0):
    base = build_features(seat, dealer, hands, rivers, melds, offer, offer_seat, just_drew)
    return base + call_extra_features(
        hands[seat], offer, offer_seat, seat, mask, rivers=rivers, n_melds=n_melds, melds=melds,
    )


def build_features(seat, dealer, hands, rivers, melds, offer=None, offer_seat=None, just_drew=0):
    others_meld = []
    for s in range(1, 5):
        if s != seat:
            others_meld.extend(melds[s])
    seat_oh = [0, 0, 0, 0]
    seat_oh[seat - 1] = 1
    offerer_oh = [0, 0, 0, 0]
    if offer_seat in (1, 2, 3, 4):
        offerer_oh[offer_seat - 1] = 1
    return (
        counts_from_list(hands[seat])
        + counts_from_list(melds[seat])
        + counts_from_list(others_meld)
        + counts_from_list(rivers[1])
        + counts_from_list(rivers[2])
        + counts_from_list(rivers[3])
        + counts_from_list(rivers[4])
        + one_hot_tile(offer)
        + seat_oh
        + offerer_oh
        + [1 if seat == dealer else 0]
        + [len(hands[seat]) / 14.0]
        + [1 if just_drew else 0]
        + _hand_shape(hands[seat])
    )


def _honor_detail(hand, visible, seat, dealer):
    vis = Counter(visible)
    hand_c = Counter(hand)
    wind = seat_wind_tile(seat, dealer)
    block = []
    isolated = []
    for tile in HONORS:
        n = hand_c[tile]
        seen = vis[tile]
        left = max(0, 4 - n - seen)
        block.extend([
            n / 4.0,
            seen / 4.0,
            left / 4.0,
            1.0 if n == 1 else 0.0,
            1.0 if n >= 2 else 0.0,
            1.0 if tile == wind else 0.0,
        ])
        if n == 1:
            isolated.append((seen, left, tile))
    safest = [0.0] * 7
    margin = 0.0
    if isolated:
        isolated.sort(key=lambda row: (row[0], -row[1]), reverse=True)
        safest[HONORS.index(isolated[0][2])] = 1.0
        if len(isolated) > 1:
            margin = (isolated[0][0] - isolated[1][0]) / 4.0
    n_iso = len(isolated) / 7.0
    n_pairs = sum(1.0 for tile in HONORS if hand_c[tile] >= 2) / 7.0
    return block + safest + [margin, n_iso, n_pairs]


def _compact_features(seat, dealer, hands, rivers, melds, just_drew=0, n_melds=0):
    visible = _visible_tiles(rivers, melds)
    others_meld = []
    for s in range(1, 5):
        if s != seat:
            others_meld.extend(melds[s])
    seat_oh = [0, 0, 0, 0]
    seat_oh[seat - 1] = 1
    hand_c = counts_from_list(hands[seat])
    vis_c = counts_from_list(visible)
    isolated = [1.0 if n == 1 else 0.0 for n in hand_c]
    isolated[LAIZI_IDX] = 0.0
    remain = [max(0.0, (4 - h - v) / 4.0) for h, v in zip(hand_c, vis_c)]
    laizi_n = sum(1 for t in hands[seat] if is_laizi(t))
    locked = locked_shanten(hands[seat], n_melds=n_melds)
    best = shanten(hands[seat], n_melds=n_melds)
    help_n = max(0.0, (locked - best) / 6.0) if laizi_n else 0.0
    qidui = qidui_shanten(hands[seat]) if n_melds == 0 else 8
    return (
        hand_c
        + counts_from_list(melds[seat])
        + counts_from_list(others_meld)
        + vis_c
        + seat_oh
        + [1 if seat == dealer else 0]
        + [len(hands[seat]) / 14.0]
        + [1 if just_drew else 0]
        + _honor_detail(hands[seat], visible, seat, dealer)
        + _hand_shape(hands[seat])
        + isolated
        + remain
        + discard_shanten_vec(hands[seat], n_melds=n_melds)
        + [(best + 1) / 9.0]
        + [n_melds / 4.0]
        + [sum(len(rivers[s]) for s in range(1, 5)) / 80.0]
        + [len(melds[seat]) / 16.0]
        + one_hot_tile(rivers[seat][-1] if rivers[seat] else None)
        + [laizi_n / 4.0, 1.0 if laizi_n else 0.0, help_n, (qidui + 1) / 8.0]
    )


def _meta(game, seat, kind, label, mask, features, extra=None):
    row = {
        "x": features,
        "y": label,
        "mask": mask,
        "gamb_id": game.get("gamb_id"),
        "room_level": game.get("room_level"),
        "seat": seat,
        "kind": kind,
    }
    if extra:
        row.update(extra)
    return row


def _emit_response_calls(game, dealer, hands, rivers, melds, n_melds, offer, offer_seat, actor, action):
    rows = []
    for seat in range(1, 5):
        if seat == offer_seat:
            continue
        mask = legal_call_mask(
            hands[seat], offer, offer_seat, seat, own_turn=False, n_melds=n_melds[seat],
        )
        if actor == seat and action is not None:
            mask[action] = 1
        if sum(mask[1:]) == 0:
            continue
        label = action if actor == seat else CALL_PASS
        if mask[label] == 0:
            continue
        rows.append(_meta(
            game,
            seat,
            "call",
            label,
            mask,
            build_call_features(
                seat, dealer, hands, rivers, melds, mask, offer, offer_seat,
                n_melds=n_melds[seat],
            ),
        ))
    return rows


def extract_samples(game):
    ops = parse_ops(game.get("ops") or "")
    deal = next((op for op in ops if op["code"] == "115"), None)
    if deal is None or ":" not in deal["payload"]:
        return [], []

    parts = deal["payload"].split(":")
    if len(parts) < 4:
        return [], []

    hands = {seat: parse_tiles(parts[seat - 1]) for seat in range(1, 5)}
    rivers = {seat: [] for seat in range(1, 5)}
    melds = {seat: [] for seat in range(1, 5)}
    n_melds = {1: 0, 2: 0, 3: 0, 4: 0}
    dealer = next((op["seat"] for op in ops if op["code"] == "112" and op["seat"]), 1)
    last_discard = None
    last_discard_seat = None
    pending = False
    last_drew = {1: 0, 2: 0, 3: 0, 4: 0}
    discards = []
    calls = []

    def resolve_pass():
        nonlocal pending
        if not pending or last_discard is None:
            pending = False
            return
        calls.extend(_emit_response_calls(
            game, dealer, hands, rivers, melds, n_melds,
            last_discard, last_discard_seat, actor=None, action=None,
        ))
        pending = False

    def emit_own_turn(seat, action):
        mask = legal_call_mask(
            hands[seat], None, None, seat, own_turn=True, n_melds=n_melds[seat],
        )
        mask[action] = 1
        if sum(mask[1:]) == 0:
            return
        calls.append(_meta(
            game, seat, "call", action, mask,
            build_call_features(
                seat, dealer, hands, rivers, melds, mask, just_drew=last_drew[seat],
                n_melds=n_melds[seat],
            ),
        ))

    for op in ops:
        code = op["code"]
        seat = op["seat"]
        tiles = op["tiles"]

        if code == "100" and seat in hands and tiles:
            resolve_pass()
            hands[seat].append(tiles[0])
            last_drew[seat] = 1
        elif code == "10001" and seat in hands and tiles:
            resolve_pass()
            if can_win(hands[seat], n_melds=n_melds[seat]):
                emit_own_turn(seat, CALL_PASS)
            discard = tiles[0]
            label = tile_idx(discard)
            if label is not None and discard in hands[seat]:
                mask = discard_legal_vec(hands[seat])
                discards.append(_meta(
                    game, seat, "discard", label, mask,
                    build_features(
                        seat, dealer, hands, rivers, melds,
                        just_drew=last_drew[seat],
                    ),
                    extra={
                        "discard": discard,
                        "x_compact": _compact_features(
                            seat, dealer, hands, rivers, melds,
                            just_drew=last_drew[seat],
                            n_melds=n_melds[seat],
                        ),
                    },
                ))
                hands[seat].remove(discard)
                rivers[seat].append(discard)
                last_discard = discard
                last_discard_seat = seat
                pending = True
                last_drew[seat] = 0
        elif code == "4004" and seat in hands:
            resolve_pass()
            emit_own_turn(seat, CALL_HU)
            pending = False
        elif code == "4001" and seat in hands:
            if pending and last_discard is not None:
                calls.extend(_emit_response_calls(
                    game, dealer, hands, rivers, melds, n_melds,
                    last_discard, last_discard_seat, actor=seat, action=CALL_HU,
                ))
            pending = False
        elif code in CODE_TO_CALL and seat in hands:
            action = CODE_TO_CALL[code]
            if code == "3003":
                resolve_pass()
                emit_own_turn(seat, CALL_AN_GANG)
                tile = _modal_tile(tiles)
                if tile is not None:
                    _take(hands[seat], [tile] * 4)
                    melds[seat].extend([tile] * 4)
                    n_melds[seat] += 1
                last_drew[seat] = 0
            else:
                if pending and last_discard is not None:
                    calls.extend(_emit_response_calls(
                        game, dealer, hands, rivers, melds, n_melds,
                        last_discard, last_discard_seat, actor=seat, action=action,
                    ))
                    pending = False
                if code in ("1001", "1002", "1003"):
                    payload = tiles[:]
                    from_hand = payload[:]
                    if last_discard in from_hand:
                        from_hand.remove(last_discard)
                    _take(hands[seat], from_hand[:2])
                    melds[seat].extend(payload)
                    n_melds[seat] += 1
                elif code == "2001":
                    tile = _modal_tile(tiles) or last_discard
                    if tile is not None:
                        _take(hands[seat], [tile, tile])
                        melds[seat].extend([tile, tile, tile])
                        n_melds[seat] += 1
                elif code == "3001":
                    tile = _modal_tile(tiles) or last_discard
                    if tile is not None:
                        need = 3 if last_discard == tile else 4
                        _take(hands[seat], [tile] * need)
                        melds[seat].extend([tile] * 4)
                        n_melds[seat] += 1
                last_discard = None
                last_drew[seat] = 0
        elif code == "10002":
            resolve_pass()
        elif code in ("199", "200", "201", "3004"):
            pending = False

    return discards, calls


def extract_discard_samples(game):
    discards, _calls = extract_samples(game)
    return discards
