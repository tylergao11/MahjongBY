# 纯收割

发给服务端只拷 `harvest/` 这一份。不要带 `train/online_bot.py`、模仿模型、网页。

## 接口

```python
from harvest import HarvestBots, CALL_PASS, CALL_HU, tile_name

bots = HarvestBots()
tile = bots.pick_discard(seat, dealer, hands, rivers, melds, n_melds, just_drew, forbid=None, meld_kinds=..., wall_n=80)
action = bots.pick_call(seat, dealer, hands, rivers, melds, n_melds, offer, offer_seat, own_turn, just_drew, wall_n, meld_kinds=..., blocked_hu=..., passed_fan=..., passed_peng=..., after_gang=False)
bu = bots.want_bu_gang(hand, melds, kinds, wall_n=80)
```

座位 `1..4`。牌 id：1-9万，17-25条（17=妖姬/癞子），33-41筒，49/50/51/52/65/66/67 字。动作：0过 1吃高 2吃中 3吃低 4碰 5明杠 6暗杠 7胡。

规则是可吃场。没有陪玩、没有送钱。
