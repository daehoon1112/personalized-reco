"""④ 행동(behavioral) + 회귀 테스트 — 방향성 기대, 콜드스타트 폴백, NDCG 회귀 가드."""

from collections import Counter

from py_common.metrics import ndcg_at_k
from pipelines.recommender import recommend_for_user, score_by_genre_affinity

ITEMS = [("act1", "action"), ("com1", "comedy"), ("dra1", "drama")]


def test_action_heavy_user_ranks_action_above_comedy() -> None:
    history = Counter({"action": 8, "comedy": 2})
    scored = dict(score_by_genre_affinity(history, ITEMS))
    assert scored["act1"] > scored["com1"]


def test_cold_start_falls_back_to_popularity_without_crashing() -> None:
    fallback = [("pop1", 10.0), ("pop2", 5.0)]
    out = recommend_for_user({}, ITEMS, k=2, popularity_fallback=fallback)
    assert out == ["pop1", "pop2"]


# 회귀 가드: 고정 검증셋에서 NDCG가 기준선 이상이어야 한다(떨어지면 회귀 의심 → 실패).
NDCG_BASELINE = 0.80


def test_ndcg_regression_guard() -> None:
    history = Counter({"action": 9, "comedy": 1})
    recommended = recommend_for_user(history, ITEMS, k=3)
    relevant = {"act1"}  # 액션 선호 유저의 실제 정답
    score = ndcg_at_k(recommended, relevant, 3)
    assert score >= NDCG_BASELINE, f"NDCG {score:.3f} < baseline {NDCG_BASELINE} — 회귀 의심"
