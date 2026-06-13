"""① 결정적 단위 테스트 — 같은 입력이면 같은 출력 (후보/인기순 집계)."""

from pipelines.recommender import rank_by_popularity

EVENTS = [
    {"event_type": "impression", "item_id": "a"},
    {"event_type": "click", "item_id": "a"},
    {"event_type": "purchase", "item_id": "b"},
    {"event_type": "click", "item_id": "b"},
    {"event_type": "click", "item_id": "c"},
]


def test_popularity_is_deterministic() -> None:
    assert rank_by_popularity(EVENTS) == rank_by_popularity(list(reversed(EVENTS)))


def test_popularity_scores_and_tie_break() -> None:
    ranked = rank_by_popularity(EVENTS)
    # b: purchase(5)+click(1)=6 ; a: click(1) ; c: click(1)
    assert ranked[0] == ("b", 6.0)
    # 동점(a,c=1.0)은 item_id 오름차순으로 결정적 정렬
    assert ranked[1:] == [("a", 1.0), ("c", 1.0)]


def test_impression_only_has_zero_weight() -> None:
    assert rank_by_popularity([{"event_type": "impression", "item_id": "x"}]) == [("x", 0.0)]
