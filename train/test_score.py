# -*- coding: utf-8 -*-
import numpy as np

from train.call_heads import FAM_CHI, FAM_MING, FAM_PENG, family_mask, family_of
from train.score import imitate_score, legal_rank, score_scores
from train.tiles import CALL_CHI_HIGH, CALL_MING_GANG, CALL_PASS, CALL_PENG, N_CALL


def test_perfect_model_is_one():
    y = np.array([3, 10, 0])
    mask = np.zeros((3, 34), dtype=np.int8)
    scores = np.zeros((3, 34), dtype=np.float64)
    for i, label in enumerate(y):
        mask[i, label] = 1
        mask[i, (label + 1) % 34] = 1
        scores[i, label] = 9.0
        scores[i, (label + 1) % 34] = 1.0
    out = score_scores(scores, y, mask)
    assert out["top1"] == 1.0
    assert out["follow"] == 1.0


def test_mask_blocks_illegal_high_score():
    y = np.array([2])
    mask = np.zeros((1, 34), dtype=np.int8)
    mask[0, 2] = 1
    scores = np.zeros((1, 34), dtype=np.float64)
    scores[0, 7] = 100.0
    scores[0, 2] = 0.1
    assert legal_rank(scores, mask)[0, 0] == 2


def test_always_pass_misses_real_calls():
    y = np.array([CALL_PASS, 4, 1])
    mask = np.ones((3, N_CALL), dtype=np.int8)
    scores = np.zeros((3, N_CALL), dtype=np.float64)
    scores[:, CALL_PASS] = 1.0
    out = score_scores(scores, y, mask)
    assert out["top1"] < 1.0


def test_imitate_formula():
    assert abs(imitate_score(0.6, 0.4) - 0.5) < 1e-9


def test_family_groups_chi_and_splits_peng_gang():
    y = np.array([CALL_PASS, CALL_CHI_HIGH, CALL_PENG, CALL_MING_GANG])
    assert family_of(y).tolist() == [0, FAM_CHI, FAM_PENG, FAM_MING]
    mask = np.zeros((1, N_CALL), dtype=np.int8)
    mask[0, [CALL_PASS, CALL_CHI_HIGH, CALL_PENG]] = 1  # 胡位保持 0
    fm = family_mask(mask)
    assert fm[0, FAM_CHI] == 1
    assert fm[0, FAM_MING] == 0


if __name__ == "__main__":
    test_perfect_model_is_one()
    test_mask_blocks_illegal_high_score()
    test_always_pass_misses_real_calls()
    test_imitate_formula()
    test_family_groups_chi_and_splits_peng_gang()
    print("score tests ok")
