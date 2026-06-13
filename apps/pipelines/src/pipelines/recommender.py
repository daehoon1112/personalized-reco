"""베이스라인 추천 로직 (스캐폴딩).

- rank_by_popularity: 이벤트 → 인기순 점수 (결정적). TODO(#10): gold item_popularity로 이전.
- recommend: top-k 계약(≤k, 중복 없음, seen 제외).
- score_by_genre_affinity / recommend_for_user: 콘텐츠 친화도 + 콜드스타트 폴백(방향성·행동 테스트용).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

# 행동 가중치: 강한 신호일수록 높게.
EVENT_WEIGHTS: dict[str, float] = {
    "impression": 0.0,
    "click": 1.0,
    "cart": 3.0,
    "purchase": 5.0,
}


def _item_of(event: Mapping[str, object]) -> str | None:
    item = event.get("item_id") or event.get("itemId")
    return str(item) if item is not None else None


def _type_of(event: Mapping[str, object]) -> str:
    return str(event.get("event_type") or event.get("eventType") or "")


def rank_by_popularity(events: Sequence[Mapping[str, object]]) -> list[tuple[str, float]]:
    """이벤트 → (item_id, score) 인기순 내림차순. 동점은 item_id 오름차순(결정적)."""
    scores: dict[str, float] = {}
    for event in events:
        item = _item_of(event)
        if item is None:
            continue
        scores[item] = scores.get(item, 0.0) + EVENT_WEIGHTS.get(_type_of(event), 0.0)
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))


def recommend(
    scored_items: Sequence[tuple[str, float]],
    k: int,
    seen: set[str] | None = None,
) -> list[str]:
    """top-k 추천 — ≤k개, 중복 없음, seen 제외 (계약)."""
    seen = seen or set()
    out: list[str] = []
    for item, _score in scored_items:
        if item in seen or item in out:
            continue
        out.append(item)
        if len(out) >= k:
            break
    return out


def score_by_genre_affinity(
    user_genre_history: Mapping[str, int],
    items: Sequence[tuple[str, str]],
) -> list[tuple[str, float]]:
    """items=[(item_id, genre)] → (item_id, score) 내림차순. score=유저의 해당 장르 비율(0~1)."""
    total = sum(user_genre_history.values()) or 1
    scored = [(item, user_genre_history.get(genre, 0) / total) for item, genre in items]
    return sorted(scored, key=lambda kv: (-kv[1], kv[0]))


def recommend_for_user(
    user_genre_history: Mapping[str, int],
    items: Sequence[tuple[str, str]],
    k: int,
    seen: set[str] | None = None,
    popularity_fallback: Sequence[tuple[str, float]] | None = None,
) -> list[str]:
    """히스토리 있으면 친화도, 없으면(콜드스타트) 인기순 폴백."""
    if user_genre_history:
        base = score_by_genre_affinity(user_genre_history, items)
    else:
        base = list(popularity_fallback or [])
    return recommend(base, k, seen)
