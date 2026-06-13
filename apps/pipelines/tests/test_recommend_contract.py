"""② 계약(contract) 테스트 — 출력값이 아니라 '형식/불변식'을 검증."""

import pytest

from pipelines.recommender import recommend, score_by_genre_affinity

SCORED = [("a", 9.0), ("b", 5.0), ("c", 3.0), ("d", 1.0)]


@pytest.mark.parametrize("k", [1, 2, 3, 10])
def test_returns_at_most_k(k: int) -> None:
    assert len(recommend(SCORED, k)) <= k


def test_no_duplicates() -> None:
    out = recommend(SCORED + SCORED, 4)
    assert len(out) == len(set(out))


def test_excludes_seen_items() -> None:
    out = recommend(SCORED, 4, seen={"a", "c"})
    assert "a" not in out
    assert "c" not in out


def test_result_is_subset_of_candidates() -> None:
    candidates = {item for item, _ in SCORED}
    assert set(recommend(SCORED, 3)).issubset(candidates)


def test_affinity_scores_in_unit_range() -> None:
    scored = score_by_genre_affinity(
        {"action": 3, "comedy": 1},
        [("x", "action"), ("y", "comedy"), ("z", "drama")],
    )
    assert all(0.0 <= score <= 1.0 for _, score in scored)
