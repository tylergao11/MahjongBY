# -*- coding: utf-8 -*-
"""Standard 4-meld + pair win check. No scoring, only shape."""


def can_win(hand, extra=None, n_melds=0):
    tiles = list(hand)
    if extra is not None:
        tiles.append(extra)
    need = 4 - int(n_melds)
    if need < 0:
        return False
    if len(tiles) != need * 3 + 2:
        return False
    tiles.sort()
    return _complete(tuple(tiles), need, False)


def _complete(tiles, sets_left, has_pair):
    if not tiles:
        return sets_left == 0 and has_pair
    first = tiles[0]
    n = tiles.count(first)

    if n >= 3 and _complete(_remove(tiles, first, 3), sets_left - 1, has_pair):
        return True
    if n >= 2 and not has_pair and _complete(_remove(tiles, first, 2), sets_left, True):
        return True
    if first <= 41 and first % 16 <= 7:
        a, b = first + 1, first + 2
        if a in tiles and b in tiles:
            rest = list(tiles)
            rest.remove(first)
            rest.remove(a)
            rest.remove(b)
            if _complete(tuple(rest), sets_left - 1, has_pair):
                return True
    return False


def _remove(tiles, tile, k):
    rest = list(tiles)
    for _ in range(k):
        rest.remove(tile)
    return tuple(rest)
