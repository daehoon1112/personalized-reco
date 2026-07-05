"""② 계약 테스트 — 생성 이벤트가 와이어 계약과 퍼널 불변식을 지키는지.

`py_common.event.parse_event()`가 그대로 검증기 역할을 한다 — Kotlin EventEnvelope의
거울상 계약을 통과하지 못하면 bronze-sink/파이프라인이 못 읽는 데이터라는 뜻이다.
"""

from datetime import datetime, timezone

import pytest

from py_common.event import EventType, parse_event
from pipelines.simulator import SimConfig, generate_events

FIXED_END = datetime(2026, 7, 4, 0, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def events() -> list[dict]:
    return generate_events(SimConfig(n_events=1000, end_ts=FIXED_END))


def test_every_event_round_trips_through_contract(events: list[dict]) -> None:
    for raw in events:
        parsed = parse_event(raw)  # 계약 위반이면 ValueError로 실패
        assert parsed.event_id == raw["eventId"]
        assert parsed.context is not None
        assert parsed.context.request_id


def test_position_only_on_impression_and_click(events: list[dict]) -> None:
    for raw in events:
        if raw["eventType"] in ("impression", "click"):
            assert raw["position"] >= 1
        else:
            assert raw["position"] is None


def test_purchase_context_complete(events: list[dict]) -> None:
    purchases = [e for e in events if e["eventType"] == "purchase"]
    assert purchases, "1000건이면 purchase가 존재해야 한다"
    for raw in purchases:
        ctx = raw["context"]
        assert ctx["orderId"].startswith("o-")
        assert ctx["amount"] == ctx["unitPrice"] * ctx["quantity"]
        assert ctx["currency"] == "KRW"


def test_funnel_ordering_within_session(events: list[dict]) -> None:
    """click은 같은 세션·requestId·아이템의 impression 뒤에, ts 단조 증가로 나온다."""
    seen_impressions: set[tuple] = set()
    for raw in events:  # 리스트가 ts 오름차순임을 전제 (아래 test_sorted가 보증)
        key = (raw["sessionId"], raw["context"]["requestId"], raw["itemId"])
        event_type = EventType(raw["eventType"])
        if event_type is EventType.IMPRESSION:
            seen_impressions.add(key)
        else:
            assert key in seen_impressions, f"{event_type}이 impression보다 먼저: {key}"


def test_sorted_by_ts(events: list[dict]) -> None:
    timestamps = [e["ts"] for e in events]
    assert timestamps == sorted(timestamps)
