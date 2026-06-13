"""③ 메트릭 코드 검증 — 손으로 답을 아는 작은 픽스처로 구현 정확성을 못 박는다."""

import math

import pytest

from py_common.metrics import dcg_at_k, ndcg_at_k, precision_at_k, recall_at_k

REC = ["A", "B", "C", "D"]
RELEVANT = {"A", "C"}


def test_precision_at_k() -> None:
    assert precision_at_k(REC, RELEVANT, 2) == pytest.approx(0.5)  # top2 [A,B] → 1 hit / 2
    assert precision_at_k(REC, RELEVANT, 4) == pytest.approx(0.5)  # 2 hits / 4


def test_recall_at_k() -> None:
    assert recall_at_k(REC, RELEVANT, 1) == pytest.approx(0.5)  # [A] → 1 / 2
    assert recall_at_k(REC, RELEVANT, 4) == pytest.approx(1.0)


def test_dcg_handcomputed() -> None:
    # A@0 → 1/log2(2)=1.0 ; C@2 → 1/log2(4)=0.5 ; 합 1.5
    assert dcg_at_k(REC, RELEVANT, 4) == pytest.approx(1.5)


def test_ndcg_handcomputed() -> None:
    idcg = 1 / math.log2(2) + 1 / math.log2(3)  # 1 + 0.6309
    assert ndcg_at_k(REC, RELEVANT, 4) == pytest.approx(1.5 / idcg)


def test_perfect_ranking_ndcg_is_one() -> None:
    assert ndcg_at_k(["A", "C", "B", "D"], {"A", "C"}, 4) == pytest.approx(1.0)


def test_empty_relevant_is_zero() -> None:
    assert recall_at_k(REC, set(), 4) == 0.0
    assert ndcg_at_k(REC, set(), 4) == 0.0
