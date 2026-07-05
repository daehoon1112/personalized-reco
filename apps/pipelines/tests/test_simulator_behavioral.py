"""④ 행동 테스트 — 방향성 기대: position-decay CTR, zipf 인기 편중, 집계 CTR 범위."""

from collections import Counter
from datetime import datetime, timezone

import pytest

from pipelines.simulator import SimConfig, click_prob, generate_events

FIXED_END = datetime(2026, 7, 4, 0, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def events() -> list[dict]:
    # 통계적 기대는 표본이 커야 안정적 — 시드 고정이라 flaky하지 않다.
    return generate_events(SimConfig(n_events=20_000, end_ts=FIXED_END))


def _ctr_at(events: list[dict], positions: set[int]) -> float:
    impressions = sum(
        1 for e in events if e["eventType"] == "impression" and e["position"] in positions
    )
    clicks = sum(1 for e in events if e["eventType"] == "click" and e["position"] in positions)
    return clicks / impressions


def test_position_decay_ctr(events: list[dict]) -> None:
    """1위 CTR > 5위 이하 CTR — position bias 신호가 데이터에 실제로 실리는지."""
    assert _ctr_at(events, {1}) > _ctr_at(events, {5, 6, 7, 8, 9, 10})


def test_click_prob_monotonic_decreasing() -> None:
    probs = [click_prob(0.28, pos) for pos in range(1, 11)]
    assert probs == sorted(probs, reverse=True)
    assert probs[0] == pytest.approx(0.28)  # 1위 = base


def test_aggregate_ctr_in_realistic_range(events: list[dict]) -> None:
    counts = Counter(e["eventType"] for e in events)
    ctr = counts["click"] / counts["impression"]
    assert 0.10 <= ctr <= 0.25, f"집계 CTR {ctr:.3f}이 현실적 범위를 벗어남"


def test_item_exposure_is_head_heavy(events: list[dict]) -> None:
    """zipf 편중: 노출 상위 10% 아이템이 전체 노출의 30% 이상을 차지."""
    exposure = Counter(
        e["itemId"] for e in events if e["eventType"] == "impression"
    )
    total = sum(exposure.values())
    head = sum(count for _, count in exposure.most_common(max(1, len(exposure) // 10)))
    assert head / total >= 0.30


def test_funnel_rates_direction(events: list[dict]) -> None:
    counts = Counter(e["eventType"] for e in events)
    assert counts["impression"] > counts["click"] > counts["cart"] > counts["purchase"] > 0
