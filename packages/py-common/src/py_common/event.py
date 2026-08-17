"""이벤트 계약 — Kotlin `me.imweb.reco.serving.event.Event`와 거울상인 타입드 모델.

bronze **저장**은 payload에 원본 JSON을 그대로 보존하지만(받은 그대로 원칙),
**코드에서 읽을 때**는 dict가 아니라 이 클래스를 통한다 — 구조가 코드에 드러나고,
계약 위반(모르는 eventType, ts 누락)을 조용히 통과시키지 않기 위해서다.

와이어 포맷은 camelCase(JSON), 이 모델은 snake_case. 파싱은 둘 다 받는다.
TODO(#4): protobuf+buf 코드젠(packages/schema-py)이 단일 소스가 되면 이 수동 정의를 대체한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class EventType(StrEnum):
    IMPRESSION = "impression"
    CLICK = "click"
    CART = "cart"
    PURCHASE = "purchase"


@dataclass(frozen=True, slots=True)
class EventContext:
    """impression 시점 스냅샷 + 행동별 부가 정보 (전 필드 optional).

    quantity=cart/purchase, order_id 이하=purchase에서만 채워진다.
    모르는 키는 무시한다(전방 호환) — 원본은 어차피 bronze payload에 있다.
    """

    device: str | None = None
    page: str | None = None
    request_id: str | None = None      # 노출 배치 키 — silver 라벨링의 impression↔결과 조인 키
    model_version: str | None = None   # 노출을 만든 서빙 모델 버전
    quantity: int | None = None
    order_id: str | None = None
    unit_price: int | None = None      # KRW 정수
    amount: int | None = None          # KRW 정수
    currency: str | None = None


@dataclass(frozen=True, slots=True)
class Event:
    """소비(consume) 측 타입드 이벤트 — Kafka `events` / bronze `events_raw.payload` 역직렬화용.

    event_id/ts는 수집 API가 항상 채우므로 required — 없으면 파싱 실패가 맞다.
    """

    event_id: str
    event_type: EventType
    ts: datetime
    user_id: str | None = None         # 비회원 None
    item_id: str | None = None
    session_id: str | None = None
    position: int | None = None        # impression/click만, 1-base
    consent: bool | None = None
    context: EventContext | None = None

    @property
    def is_impression(self) -> bool:
        return self.event_type is EventType.IMPRESSION

    @property
    def attribution_key(self) -> tuple[str | None, str | None, str | None]:
        """silver 라벨링에서 결과(click/cart/purchase)를 impression에 귀속할 때 쓰는 조인 키."""
        request_id = self.context.request_id if self.context else None
        return (self.session_id, request_id, self.item_id)


def _get(raw: dict[str, Any], camel: str, snake: str) -> Any:
    """camelCase(와이어)와 snake_case 둘 다 허용."""
    return raw.get(camel) if camel in raw else raw.get(snake)


def parse_context(raw: dict[str, Any]) -> EventContext:
    return EventContext(
        device=raw.get("device"),
        page=raw.get("page"),
        request_id=_get(raw, "requestId", "request_id"),
        model_version=_get(raw, "modelVersion", "model_version"),
        quantity=raw.get("quantity"),
        order_id=_get(raw, "orderId", "order_id"),
        unit_price=_get(raw, "unitPrice", "unit_price"),
        amount=raw.get("amount"),
        currency=raw.get("currency"),
    )


def parse_event(raw: dict[str, Any]) -> Event:
    """이벤트 JSON(dict) → Event. 계약 위반이면 ValueError.

    모르는 최상위/컨텍스트 필드는 무시한다(전방 호환). 모르는 eventType은 실패한다.
    """
    event_id = _get(raw, "eventId", "event_id")
    if not event_id:
        raise ValueError("eventId 누락")

    type_code = _get(raw, "eventType", "event_type")
    try:
        event_type = EventType(type_code)
    except ValueError:
        raise ValueError(f"알 수 없는 eventType: {type_code!r}") from None

    ts_raw = _get(raw, "ts", "event_ts")
    if not isinstance(ts_raw, str) or not ts_raw:
        raise ValueError("ts 누락")
    ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
    if ts.tzinfo is None:
        # naive datetime은 tz-aware와 비교 시 TypeError라, 한 건이 배치 전체를 죽인다.
        # UTC로 임의 가정하면 귀속 윈도(24h)가 조용히 틀어지므로 계약 위반으로 처리한다
        # → 호출자(bronze.iter_events)가 ValueError를 잡아 그 행만 스킵한다.
        raise ValueError(f"ts에 타임존이 없음: {ts_raw!r}")

    context = raw.get("context")
    return Event(
        event_id=str(event_id),
        event_type=event_type,
        ts=ts,
        user_id=_get(raw, "userId", "user_id"),
        item_id=_get(raw, "itemId", "item_id"),
        session_id=_get(raw, "sessionId", "session_id"),
        position=raw.get("position"),
        consent=raw.get("consent"),
        context=parse_context(context) if isinstance(context, dict) else None,
    )
