"""이벤트 계약 테스트 — Kotlin EventDeserializationTest와 동일 케이스(양쪽 계약 동기화 검증).

픽스처는 data/samples/events.sample.jsonl 실제 라인과 동일한 형태.
"""

from datetime import datetime, timezone

import pytest

from py_common import Event, EventType, parse_event


IMPRESSION = {
    "eventId": "8c932752-7ddf-4be3-87d9-23d443f6a23c",
    "eventType": "impression",
    "userId": "u-000116",
    "itemId": "p-0120",
    "sessionId": "5bbf563c-1555-4083-befb-11c44edeee63",
    "position": 1,
    "consent": True,
    "ts": "2026-06-27T00:15:00.000Z",
    "context": {
        "device": "pc",
        "page": "category",
        "requestId": "3729ac5a-41c0-4c60-ac07-2a9a065869e1",
        "modelVersion": "pop-v0",
    },
}


def test_impression_parses_to_typed_event() -> None:
    event = parse_event(IMPRESSION)

    assert isinstance(event, Event)
    assert event.event_type is EventType.IMPRESSION
    assert event.is_impression
    assert event.user_id == "u-000116"
    assert event.position == 1
    assert event.ts == datetime(2026, 6, 27, 0, 15, tzinfo=timezone.utc)
    assert event.context is not None
    assert event.context.request_id == "3729ac5a-41c0-4c60-ac07-2a9a065869e1"
    assert event.attribution_key == (
        "5bbf563c-1555-4083-befb-11c44edeee63",
        "3729ac5a-41c0-4c60-ac07-2a9a065869e1",
        "p-0120",
    )


def test_purchase_parses_order_context() -> None:
    event = parse_event(
        {
            "eventId": "e-1",
            "eventType": "purchase",
            "userId": "u-1",
            "itemId": "p-1",
            "sessionId": "s-1",
            "position": None,
            "consent": True,
            "ts": "2026-06-27T01:00:00Z",
            "context": {
                "device": "mobile",
                "page": "home",
                "requestId": "r-1",
                "modelVersion": "pop-v0",
                "orderId": "o-abc",
                "quantity": 2,
                "unitPrice": 12900,
                "amount": 25800,
                "currency": "KRW",
            },
        }
    )

    assert event.event_type is EventType.PURCHASE
    assert event.context is not None
    assert event.context.order_id == "o-abc"
    assert event.context.quantity == 2
    assert event.context.amount == 25_800
    assert event.context.currency == "KRW"


def test_unknown_fields_are_tolerated() -> None:
    event = parse_event(
        {
            "eventId": "e-2",
            "eventType": "click",
            "itemId": "p-2",
            "ts": "2026-06-27T02:00:00Z",
            "futureField": "x",
            "context": {"device": "pc", "newContextKey": 123},
        }
    )

    assert event.event_type is EventType.CLICK
    assert event.user_id is None
    assert event.context is not None
    assert event.context.device == "pc"


def test_snake_case_keys_are_accepted() -> None:
    event = parse_event(
        {
            "event_id": "e-4",
            "event_type": "cart",
            "user_id": "u-4",
            "item_id": "p-4",
            "event_ts": "2026-06-27T04:00:00Z",
            "context": {"request_id": "r-4", "quantity": 1},
        }
    )

    assert event.event_type is EventType.CART
    assert event.context is not None
    assert event.context.request_id == "r-4"


@pytest.mark.parametrize(
    "bad",
    [
        {"eventId": "e-3", "eventType": "wishlist", "ts": "2026-06-27T03:00:00Z"},  # 모르는 타입
        {"eventType": "click", "ts": "2026-06-27T03:00:00Z"},  # eventId 누락
        {"eventId": "e-5", "eventType": "click"},  # ts 누락
    ],
)
def test_contract_violations_fail_loudly(bad: dict) -> None:
    with pytest.raises(ValueError):
        parse_event(bad)
