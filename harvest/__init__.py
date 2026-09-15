# -*- coding: utf-8 -*-
"""曲靖飞小鸡可吃场纯收割。发给服务端只需要这个目录。"""
from harvest.bot import HarvestBots, WinBots, pick_call, pick_discard, pick_win_call, pick_win_discard
from harvest.fxj_rules import can_ron, can_win, judge, ron_fan
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
    CALL_NAMES,
    LAIZI_ID,
    TILE_IDS,
    tile_name,
)
