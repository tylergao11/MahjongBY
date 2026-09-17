# -*- coding: utf-8 -*-
"""Check harvest and giveaway only take legal kechichang moves."""
import json
from pathlib import Path

from giveaway.bot import GiveawayBots, _is_big
from harvest import HarvestBots
from harvest.fxj_rules import can_ron, can_win, judge
from harvest.legal import legal_call_mask
from harvest.tiles import (
    CALL_AN_GANG,
    CALL_HU,
    CALL_MING_GANG,
    CALL_PASS,
    discard_legal_vec,
    tile_idx,
)
from train.online_bot import OnlineBots
from train.play import play_game

OUT = Path(__file__).resolve().parent.parent / "models" / "rules_verify.json"


class CheckBots:
    def __init__(self, inner, label, give_seats=()):
        self.inner = inner
        self.label = label
        self.give_seats = set(give_seats)
        self.bad = []
        self.n_discard = 0
        self.n_call = 0
        self.n_hu = 0

    def _fail(self, kind, detail):
        self.bad.append({"bot": self.label, "kind": kind, "detail": detail})

    def pick_discard(self, seat, dealer, hands, rivers, melds, n_melds, just_drew, forbid=None, **kwargs):
        tile = self.inner.pick_discard(
            seat, dealer, hands, rivers, melds, n_melds, just_drew, forbid=forbid, **kwargs,
        )
        self.n_discard += 1
        hand = hands[seat]
        legal = discard_legal_vec(hand, forbid=forbid)
        idx = tile_idx(tile)
        if tile not in hand or idx is None or not legal[idx]:
            self._fail("discard", "seat=%s tile=%s forbid=%s hand=%s" % (seat, tile, forbid, hand))
        return tile

    def pick_call(self, seat, dealer, hands, rivers, melds, n_melds, offer, offer_seat, own_turn, just_drew, wall_n, **kwargs):
        action = self.inner.pick_call(
            seat, dealer, hands, rivers, melds, n_melds, offer, offer_seat, own_turn, just_drew, wall_n, **kwargs,
        )
        self.n_call += 1
        own_kinds = kwargs.get("meld_kinds")
        if isinstance(own_kinds, dict):
            own_kinds = own_kinds.get(seat, [])
        own_melds = melds[seat] if isinstance(melds, dict) and seat in melds else None
        mask = legal_call_mask(
            hands[seat], offer, offer_seat, seat, own_turn=own_turn, n_melds=n_melds[seat],
            meld_kinds=own_kinds, blocked_hu=kwargs.get("blocked_hu"),
            passed_fan=kwargs.get("passed_fan"), passed_peng=kwargs.get("passed_peng"),
            after_gang=kwargs.get("after_gang", False), melds=own_melds,
        )
        if wall_n <= 0:
            mask[CALL_AN_GANG] = 0
            mask[CALL_MING_GANG] = 0
        if action < 0 or action >= len(mask) or not mask[action]:
            self._fail(
                "call",
                "seat=%s action=%s mask=%s offer=%s own=%s"
                % (seat, action, mask, offer, own_turn),
            )
            return action
        if action == CALL_HU:
            self.n_hu += 1
            hand = hands[seat]
            after_gang = kwargs.get("after_gang", False)
            if own_turn:
                ok = can_win(hand, n_melds=n_melds[seat])
                info = judge(
                    hand, extra=None, n_melds=n_melds[seat], meld_kinds=own_kinds,
                    melds=own_melds, zimo=True, after_gang=after_gang,
                    hu_tile=hand[-1] if hand else None,
                )
            else:
                ok = can_ron(
                    hand, extra=offer, n_melds=n_melds[seat], meld_kinds=own_kinds,
                    melds=own_melds, after_gang=after_gang, qiang_gang=after_gang,
                    passed_fan=kwargs.get("passed_fan"), hu_tile=offer,
                )
                info = judge(
                    hand, extra=offer, n_melds=n_melds[seat], meld_kinds=own_kinds,
                    melds=own_melds, zimo=False, after_gang=after_gang,
                    qiang_gang=after_gang, hu_tile=offer,
                )
            if not ok or info is None:
                self._fail("hu_rule", "seat=%s own=%s offer=%s info=%s" % (seat, own_turn, offer, info))
            if seat in self.give_seats and info is not None and not _is_big(info):
                self._fail("giveaway_small_hu", "seat=%s base=%s extras=%s" % (
                    seat, info.get("base"), info.get("extras"),
                ))
        return action

    def want_bu_gang(self, hand, melds, kinds, wall_n=80, **kwargs):
        tile = self.inner.want_bu_gang(hand, melds, kinds, wall_n=wall_n, **kwargs)
        if tile is None:
            return None
        if tile not in hand:
            self._fail("bu_gang", "tile=%s not in hand" % tile)
            return None
        i = 0
        ok = False
        for kind in kinds:
            n = 4 if kind in ("gang", "an_gang", "ming_gang") else 3
            group = melds[i:i + n]
            i += n
            if kind == "peng" and group and group[0] == tile:
                ok = True
                break
        if not ok:
            self._fail("bu_gang", "tile=%s not an open peng" % tile)
        return tile


class Mix1v3:
    def __init__(self, ours, our_name="ours"):
        self.ours = ours
        self.online = OnlineBots()
        self.kinds = {1: "ours", 2: "online", 3: "online", 4: "online"}

    def _bot(self, seat):
        return self.ours if self.kinds.get(seat) == "ours" else self.online

    def pick_discard(self, *args, **kwargs):
        return self._bot(args[0]).pick_discard(*args, **kwargs)

    def pick_call(self, *args, **kwargs):
        return self._bot(args[0]).pick_call(*args, **kwargs)

    def want_bu_gang(self, hand, melds, kinds, wall_n=80, seat=None, **kwargs):
        return self._bot(seat).want_bu_gang(hand, melds, kinds, wall_n=wall_n, seat=seat, **kwargs)


def _unit_cases():
    bad = []
    ping = [1, 2, 3, 4, 5, 6, 7, 8, 9, 33, 17, 49, 49]
    if can_ron(ping, extra=35):
        bad.append("pinghu_ron_should_fail")
    if not can_win(ping, extra=35):
        bad.append("pinghu_zimo_shape_should_win")
    if not can_ron(ping, extra=35, qiang_gang=True):
        bad.append("qiang_gang_pinghu_should_ron")
    qidui = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 8]
    if not can_ron(qidui, extra=8):
        bad.append("qidui_should_ron")
    info = judge(qidui, extra=8, zimo=False, hu_tile=8)
    if not _is_big(info):
        bad.append("qidui_should_be_big")
    ping14 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 33, 34, 35, 49, 49]
    ping_info = judge(ping14, extra=None, zimo=True, hu_tile=49)
    if _is_big(ping_info):
        bad.append("pinghu_should_not_be_big")
    g = GiveawayBots()
    h = HarvestBots()
    mask = [1, 0, 0, 0, 0, 0, 0, 1]
    if g.pick_call(1, 1, {1: ping14, 2: [], 3: [], 4: []}, {1: [], 2: [], 3: [], 4: []}, {1: [], 2: [], 3: [], 4: []}, {1: 0, 2: 0, 3: 0, 4: 0}, None, None, True, 49, 80) != CALL_PASS:
        # own turn pinghu 14: mask from legal will have HU; giveaway must pass
        pass
    hands = {1: ping14, 2: [], 3: [], 4: []}
    rivers = {1: [], 2: [], 3: [], 4: []}
    melds = {1: [], 2: [], 3: [], 4: []}
    n_melds = {1: 0, 2: 0, 3: 0, 4: 0}
    if g.pick_call(1, 1, hands, rivers, melds, n_melds, None, None, True, 49, 80) != CALL_PASS:
        bad.append("giveaway_took_pinghu")
    qhands = {1: qidui + [8], 2: [], 3: [], 4: []}
    if h.pick_call(1, 1, qhands, rivers, melds, n_melds, None, None, True, 8, 80) != CALL_HU:
        bad.append("harvest_skipped_qidui")
    if g.pick_call(1, 1, qhands, rivers, melds, n_melds, None, None, True, 8, 80) != CALL_HU:
        bad.append("giveaway_skipped_qidui")
    return bad


def run_batch(name, n, make, seed0):
    wrapped = None
    results = []
    for i in range(n):
        inner = make()
        wrapped = CheckBots(inner, name)
        game = play_game(seed=seed0 + i, bots=wrapped)
        results.append({
            "seed": seed0 + i,
            "result": game.get("result"),
            "winner": game.get("winner"),
            "fans": game.get("fans") or {},
        })
        for seat, info in (game.get("fans") or {}).items():
            if info and not info.get("ok"):
                wrapped._fail("settle", "bad fan seat=%s" % seat)
            if name == "giveaway" and str(seat) == "1" and info and not _is_big(info):
                if game.get("winner") == 1 or 1 in (game.get("winners") or []):
                    wrapped._fail("giveaway_won_small", info)
    return {
        "n": n,
        "bad": list(wrapped.bad) if wrapped else [],
        "discards": wrapped.n_discard if wrapped else 0,
        "calls": wrapped.n_call if wrapped else 0,
        "hus": wrapped.n_hu if wrapped else 0,
        "results": results,
    }


def _merge_bad(batch):
    # CheckBots is reused; bad list accumulates only last game if we recreate each loop.
    return batch


def run_batch_fixed(name, n, make, seed0, give_seats=()):
    all_bad = []
    discards = calls = hus = 0
    results = []
    for i in range(n):
        wrapped = CheckBots(make(), name, give_seats=give_seats)
        game = play_game(seed=seed0 + i, bots=wrapped)
        discards += wrapped.n_discard
        calls += wrapped.n_call
        hus += wrapped.n_hu
        all_bad.extend(wrapped.bad)
        winners = game.get("winners") or []
        fans = game.get("fans") or {}
        for seat in winners:
            info = fans.get(str(seat)) or fans.get(seat)
            if info is None:
                all_bad.append({"bot": name, "kind": "hu_missing_judge", "detail": "seat=%s" % seat})
            elif give_seats and int(seat) in give_seats and info and not _is_big(info):
                all_bad.append({"bot": name, "kind": "giveaway_won_small", "detail": info})
        results.append({
            "seed": seed0 + i,
            "result": game.get("result"),
            "winner": game.get("winner"),
            "winners": winners,
            "base": {
                str(s): (fans.get(str(s)) or fans.get(s) or {}).get("base")
                for s in winners
            },
        })
    return {
        "n": n,
        "bad_n": len(all_bad),
        "bad": all_bad[:20],
        "discards": discards,
        "calls": calls,
        "hus": hus,
        "results": results,
    }


def main():
    unit = _unit_cases()
    report = {
        "unit_bad": unit,
        "harvest4": run_batch_fixed("harvest", 12, HarvestBots, 11000),
        "giveaway4": run_batch_fixed("giveaway", 12, GiveawayBots, 11100, give_seats=(1, 2, 3, 4)),
        "harvest_1v3": run_batch_fixed("harvest", 8, lambda: Mix1v3(HarvestBots()), 11200),
        "giveaway_1v3": run_batch_fixed("giveaway", 8, lambda: Mix1v3(GiveawayBots()), 11300, give_seats=(1,)),
    }
    ok = not unit and all(report[k]["bad_n"] == 0 for k in ("harvest4", "giveaway4", "harvest_1v3", "giveaway_1v3"))
    report["ok"] = ok
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("ok=%s unit_bad=%s" % (ok, unit), flush=True)
    for key in ("harvest4", "giveaway4", "harvest_1v3", "giveaway_1v3"):
        row = report[key]
        print(
            "%s n=%s bad=%s discards=%s calls=%s hus=%s"
            % (key, row["n"], row["bad_n"], row["discards"], row["calls"], row["hus"]),
            flush=True,
        )
        if row["bad"]:
            print(row["bad"][:5], flush=True)


if __name__ == "__main__":
    main()
