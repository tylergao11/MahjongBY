# -*- coding: utf-8 -*-
"""曲靖飞小鸡可吃场送钱。策略只在这个目录，规则共用 harvest/。"""
from giveaway.bot import GiveawayBots, pick_call, pick_discard
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
