# 送钱

发给服务端拷 `giveaway/`，规则仍用 `harvest/`。不要带模仿模型和网页。

桌上只用 `GiveawayBots`。不胡，能碰就碰，能吃就吃，癞子和对子先扔，有碰就补杠给人抢。

```python
from giveaway import GiveawayBots

bots = GiveawayBots()
tile = bots.pick_discard(seat, dealer, hands, rivers, melds, n_melds, just_drew, forbid=None)
action = bots.pick_call(seat, dealer, hands, rivers, melds, n_melds, offer, offer_seat, own_turn, just_drew, wall_n)
bu = bots.want_bu_gang(hand, melds, kinds, wall_n=80)
```

座位和牌 id 跟 `harvest/` 一样。动作：0过 1吃高 2吃中 3吃低 4碰 5明杠 6暗杠 7胡。这套策略不会选胡。
