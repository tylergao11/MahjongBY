# -*- coding: utf-8 -*-
"""Hierarchical call policy: family first, then chi direction / peng-vs-gang."""
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from train.tiles import (
    CALL_AN_GANG,
    CALL_CHI_HIGH,
    CALL_CHI_LOW,
    CALL_CHI_MID,
    CALL_HU,
    CALL_MING_GANG,
    CALL_PASS,
    CALL_PENG,
    N_CALL,
)

FAM_PASS, FAM_CHI, FAM_PENG, FAM_MING, FAM_AN, FAM_HU = 0, 1, 2, 3, 4, 5
N_FAM = 6
Y_TO_FAM = {
    CALL_PASS: FAM_PASS,
    CALL_CHI_HIGH: FAM_CHI,
    CALL_CHI_MID: FAM_CHI,
    CALL_CHI_LOW: FAM_CHI,
    CALL_PENG: FAM_PENG,
    CALL_MING_GANG: FAM_MING,
    CALL_AN_GANG: FAM_AN,
    CALL_HU: FAM_HU,
}


def family_of(y):
    return np.array([Y_TO_FAM[int(v)] for v in np.asarray(y).tolist()], dtype=np.int64)


def family_mask(call_mask):
    fm = np.zeros((call_mask.shape[0], N_FAM), dtype=np.int8)
    fm[:, FAM_PASS] = call_mask[:, CALL_PASS]
    fm[:, FAM_CHI] = (call_mask[:, CALL_CHI_HIGH:CALL_CHI_LOW + 1].sum(axis=1) > 0).astype(np.int8)
    fm[:, FAM_PENG] = call_mask[:, CALL_PENG]
    fm[:, FAM_MING] = call_mask[:, CALL_MING_GANG]
    fm[:, FAM_AN] = call_mask[:, CALL_AN_GANG]
    fm[:, FAM_HU] = call_mask[:, CALL_HU]
    return fm


def _hgb(max_iter=200, depth=6, balanced=False, seed=7):
    kwargs = dict(
        max_depth=depth,
        max_iter=max_iter,
        learning_rate=0.08,
        l2_regularization=0.1,
        min_samples_leaf=20,
        random_state=seed,
    )
    try:
        if balanced:
            kwargs["class_weight"] = "balanced"
        return HistGradientBoostingClassifier(**kwargs)
    except TypeError:
        kwargs.pop("class_weight", None)
        return HistGradientBoostingClassifier(**kwargs)


def _expand_one(model, x, n_class):
    full = np.zeros((len(x), n_class), dtype=np.float64)
    if model is None or len(x) == 0:
        return full
    raw = model.predict_proba(x)
    for col, cls in enumerate(model.classes_):
        full[:, int(cls)] = raw[:, col]
    return full


def _expand(model, x, n_class):
    if model is None or (isinstance(model, list) and not model):
        return np.zeros((len(x), n_class), dtype=np.float64)
    if isinstance(model, list):
        parts = [_expand_one(m, x, n_class) for m in model]
        return sum(parts) / len(parts)
    return _expand_one(model, x, n_class)


def _oversample(x, y, boost):
    """Duplicate minority families. boost: family_id -> extra copies."""
    xs = [x]
    ys = [y]
    for fam, copies in boost.items():
        idx = np.flatnonzero(y == fam)
        if idx.size == 0 or copies <= 0:
            continue
        take = np.tile(idx, copies)
        xs.append(x[take])
        ys.append(y[take])
    return np.concatenate(xs), np.concatenate(ys)


class HierarchicalCall:
    def __init__(self):
        self.family = None
        self.chi = None
        self.peng_gang = None
        self.chi_vs_pass = None
        self.chi_scale = 1.0

    def fit(self, x, y, mask):
        fam_y = family_of(y)
        fam_x, fam_lab = _oversample(x, fam_y, {FAM_CHI: 2, FAM_MING: 4, FAM_AN: 2, FAM_HU: 3})
        self.family = []
        print(f"fit family n={len(fam_lab)} bag=3", flush=True)
        for seed in (7, 17, 27):
            model = _hgb(260, 7, balanced=True, seed=seed)
            model.fit(fam_x, fam_lab)
            self.family.append(model)

        chi_idx = np.flatnonzero(np.isin(y, (CALL_CHI_HIGH, CALL_CHI_MID, CALL_CHI_LOW)))
        if chi_idx.size:
            chi_y = y[chi_idx] - CALL_CHI_HIGH
            self.chi = []
            print(f"fit chi-dir n={chi_idx.size} bag=2", flush=True)
            for seed in (7, 19):
                model = _hgb(200, 6, balanced=True, seed=seed)
                model.fit(x[chi_idx], chi_y)
                self.chi.append(model)

        only_chi = (
            (mask[:, CALL_CHI_HIGH:CALL_CHI_LOW + 1].sum(axis=1) > 0)
            & (mask[:, CALL_PENG] == 0)
            & (mask[:, CALL_MING_GANG] == 0)
            & (mask[:, CALL_HU] == 0)
            & np.isin(y, (CALL_PASS, CALL_CHI_HIGH, CALL_CHI_MID, CALL_CHI_LOW))
        )
        cvp_idx = np.flatnonzero(only_chi)
        if cvp_idx.size:
            cvp_y = (y[cvp_idx] != CALL_PASS).astype(np.int64)
            cvp_x, cvp_lab = _oversample(x[cvp_idx], cvp_y, {1: 3})
            self.chi_vs_pass = []
            print(f"fit chi-vs-pass n={len(cvp_lab)} chi={int((cvp_lab == 1).sum())} bag=2", flush=True)
            for seed in (7, 23):
                model = _hgb(220, 6, balanced=True, seed=seed)
                model.fit(cvp_x, cvp_lab)
                self.chi_vs_pass.append(model)

        both = np.flatnonzero((mask[:, CALL_PENG] > 0) & (mask[:, CALL_MING_GANG] > 0) & np.isin(y, (CALL_PENG, CALL_MING_GANG)))
        if both.size:
            pg_y = (y[both] == CALL_MING_GANG).astype(np.int64)
            # 明杠少，复制到接近碰的数量
            peng_n = int((pg_y == 0).sum())
            gang_n = int((pg_y == 1).sum())
            pg_x, pg_lab = x[both], pg_y
            if gang_n and peng_n and gang_n < peng_n:
                copies = max(1, peng_n // max(gang_n, 1) - 1)
                gang_i = np.flatnonzero(pg_y == 1)
                pg_x = np.concatenate([pg_x, np.tile(x[both][gang_i], (copies, 1))])
                pg_lab = np.concatenate([pg_lab, np.tile(pg_y[gang_i], copies)])
            self.peng_gang = _hgb(160, 5, balanced=True)
            print(f"fit peng-vs-gang n={len(pg_lab)} gang={int((pg_lab == 1).sum())}", flush=True)
            self.peng_gang.fit(pg_x, pg_lab)
        return self

    def predict_scores(self, x, mask):
        n = len(x)
        scores = np.zeros((n, N_CALL), dtype=np.float64)
        fam = _expand(self.family, x, N_FAM)
        fam = np.where(family_mask(mask) > 0, fam, 0.0)
        denom = fam.sum(axis=1, keepdims=True)
        denom = np.where(denom <= 0, 1.0, denom)
        fam = fam / denom

        chi_raw = _expand(self.chi, x, 3)
        chi_legal = mask[:, CALL_CHI_HIGH:CALL_CHI_LOW + 1]
        chi_raw = np.where(chi_legal > 0, chi_raw, 0.0)
        chi_sum = chi_raw.sum(axis=1, keepdims=True)
        chi_sum = np.where(chi_sum <= 0, 1.0, chi_sum)
        chi_p = chi_raw / chi_sum

        pg = np.zeros((n, 2), dtype=np.float64)
        pg[:, 0] = 1.0
        if self.peng_gang is not None:
            raw = _expand(self.peng_gang, x, 2)
            both = (mask[:, CALL_PENG] > 0) & (mask[:, CALL_MING_GANG] > 0)
            pg[both] = raw[both]
            # 只有一边合法时，合法那边为 1
        only_peng = (mask[:, CALL_PENG] > 0) & (mask[:, CALL_MING_GANG] == 0)
        only_gang = (mask[:, CALL_PENG] == 0) & (mask[:, CALL_MING_GANG] > 0)
        pg[only_peng, 0] = 1.0
        pg[only_peng, 1] = 0.0
        pg[only_gang, 0] = 0.0
        pg[only_gang, 1] = 1.0

        scores[:, CALL_PASS] = fam[:, FAM_PASS]
        scores[:, CALL_CHI_HIGH] = fam[:, FAM_CHI] * chi_p[:, 0]
        scores[:, CALL_CHI_MID] = fam[:, FAM_CHI] * chi_p[:, 1]
        scores[:, CALL_CHI_LOW] = fam[:, FAM_CHI] * chi_p[:, 2]
        scores[:, CALL_PENG] = fam[:, FAM_PENG] * pg[:, 0]
        scores[:, CALL_MING_GANG] = fam[:, FAM_MING] * pg[:, 1]
        scores[:, CALL_AN_GANG] = fam[:, FAM_AN]
        scores[:, CALL_HU] = fam[:, FAM_HU]

        only_chi = (
            (mask[:, CALL_CHI_HIGH:CALL_CHI_LOW + 1].sum(axis=1) > 0)
            & (mask[:, CALL_PENG] == 0)
            & (mask[:, CALL_MING_GANG] == 0)
            & (mask[:, CALL_HU] == 0)
        )
        if self.chi_vs_pass is not None and only_chi.any():
            cvp = _expand(self.chi_vs_pass, x, 2)
            pick = cvp[only_chi]
            scores[only_chi, CALL_PASS] = pick[:, 0]
            scores[only_chi, CALL_CHI_HIGH] = pick[:, 1] * self.chi_scale * chi_p[only_chi, 0]
            scores[only_chi, CALL_CHI_MID] = pick[:, 1] * self.chi_scale * chi_p[only_chi, 1]
            scores[only_chi, CALL_CHI_LOW] = pick[:, 1] * self.chi_scale * chi_p[only_chi, 2]

        scores = np.where(mask > 0, scores, 0.0)
        return scores
