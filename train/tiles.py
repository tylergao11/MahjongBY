# -*- coding: utf-8 -*-
"""Standard 136-tile encoding used by fxj.jsonl."""

TILE_IDS = (
    list(range(1, 10))
    + list(range(17, 26))
    + list(range(33, 42))
    + [49, 50, 51, 52, 65, 66, 67]
)

TILE_TO_IDX = {tid: i for i, tid in enumerate(TILE_IDS)}
IDX_TO_TILE = {i: tid for tid, i in TILE_TO_IDX.items()}
N_TILES = 34

TILE_NAMES = {}
for i in range(1, 10):
    TILE_NAMES[i] = f"{i}万"
    TILE_NAMES[16 + i] = f"{i}条"
    TILE_NAMES[32 + i] = f"{i}筒"
TILE_NAMES.update({49: "东", 50: "南", 51: "西", 52: "北", 65: "中", 66: "发", 67: "白"})


def tile_idx(tile_id):
    return TILE_TO_IDX.get(int(tile_id))


def tile_name(tile_id):
    return TILE_NAMES.get(int(tile_id), f"?{tile_id}")


def counts_from_list(tiles):
    vec = [0] * N_TILES
    for t in tiles:
        idx = tile_idx(t)
        if idx is not None:
            vec[idx] += 1
    return vec


def one_hot_tile(tile_id):
    vec = [0] * N_TILES
    idx = tile_idx(tile_id) if tile_id is not None else None
    if idx is not None:
        vec[idx] = 1
    return vec


def suit_rank(tile_id):
    tid = int(tile_id)
    if 1 <= tid <= 9:
        return "wan", tid
    if 17 <= tid <= 25:
        return "tiao", tid - 16
    if 33 <= tid <= 41:
        return "tong", tid - 32
    return None, None


def is_honor(tile_id):
    return suit_rank(tile_id)[0] is None


def next_seat(seat):
    return 1 if seat == 4 else seat + 1


CALL_PASS = 0
CALL_CHI_HIGH = 1
CALL_CHI_MID = 2
CALL_CHI_LOW = 3
CALL_PENG = 4
CALL_MING_GANG = 5
CALL_AN_GANG = 6
CALL_HU = 7
N_CALL = 8
CALL_NAMES = ("过", "吃高", "吃中", "吃低", "碰", "明杠", "暗杠", "胡")
CODE_TO_CALL = {
    "1001": CALL_CHI_HIGH,
    "1002": CALL_CHI_MID,
    "1003": CALL_CHI_LOW,
    "2001": CALL_PENG,
    "3001": CALL_MING_GANG,
    "3003": CALL_AN_GANG,
    "4001": CALL_HU,
    "4004": CALL_HU,
}
