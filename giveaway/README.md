# 送钱

发给服务端拷 `giveaway/`，规则仍用 `harvest/`。

看不上小胡，大胡才要。平胡、无鸡平胡都过；七对、大对、清一色、混一色、字一色这些才胡。这把有人胡就结束，所以小的让出去，大的到手就收。

出牌按自己往大牌走，不偷看对面手牌，不专门打能点炮的牌。吃不做。碰只在能推进大对、且不是七对快成的时候。不补杠。

```python
from giveaway import GiveawayBots

bots = GiveawayBots()
tile = bots.pick_discard(seat, dealer, hands, rivers, melds, n_melds, just_drew, forbid=None, meld_kinds=...)
action = bots.pick_call(seat, dealer, hands, rivers, melds, n_melds, offer, offer_seat, own_turn, just_drew, wall_n)
bu = bots.want_bu_gang(hand, melds, kinds, wall_n=80)
```

座位和牌 id 跟 `harvest/` 一样。动作：0过 1吃高 2吃中 3吃低 4碰 5明杠 6暗杠 7胡。
