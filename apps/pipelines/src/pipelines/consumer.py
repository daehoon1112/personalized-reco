"""Kafka 컨슈머 → Bronze(events_raw) 적재 (#13).

`events` 토픽을 구독해 Postgres bronze 테이블에 **멱등** 적재한다.
역직렬화는 현재 JSON(proto-over-JSON 임시) — TODO(#4): proto 생성 타입으로 대체.

at-least-once + ON CONFLICT(event_id) DO NOTHING 조합으로 Bronze에는 사실상 정확히 한 번 적재된다.
"""

from __future__ import annotations

import argparse
import json
import signal
import time
from datetime import datetime, timezone
from typing import Any

import psycopg
from confluent_kafka import Consumer, KafkaException

from py_common import load_settings

EVENTS_TOPIC = "events"
CONSUMER_GROUP = "bronze-sink"

INSERT_SQL = """
INSERT INTO events_raw
    (event_id, event_type, user_id, item_id, session_id, position, consent, event_ts, payload)
VALUES
    (%(event_id)s, %(event_type)s, %(user_id)s, %(item_id)s, %(session_id)s,
     %(position)s, %(consent)s, %(event_ts)s, %(payload)s)
ON CONFLICT (event_id) DO NOTHING
"""


def parse_ts(value: Any) -> datetime:
    """ISO-8601(끝의 Z 허용) → tz-aware datetime. 없거나 깨지면 현재 UTC."""
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def to_row(evt: dict[str, Any]) -> dict[str, Any]:
    """이벤트 JSON → events_raw 행."""
    return {
        "event_id": evt.get("eventId") or evt.get("event_id"),
        "event_type": evt.get("eventType") or evt.get("event_type"),
        "user_id": evt.get("userId") or evt.get("user_id"),
        "item_id": evt.get("itemId") or evt.get("item_id"),
        "session_id": evt.get("sessionId") or evt.get("session_id"),
        "position": evt.get("position"),
        "consent": evt.get("consent"),
        "event_ts": parse_ts(evt.get("ts") or evt.get("event_ts")),
        "payload": json.dumps(evt, ensure_ascii=False),
    }


def run_consumer(idle_timeout: float = 0.0) -> int:
    """컨슈머 루프. idle_timeout>0이면 그 시간(초) 동안 메시지가 없을 때 종료(검증/배치용)."""
    settings = load_settings()
    consumer = Consumer(
        {
            "bootstrap.servers": settings.kafka_bootstrap,
            "group.id": CONSUMER_GROUP,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    consumer.subscribe([EVENTS_TOPIC])

    inserted = 0
    last_seen = time.monotonic()
    running = True

    def _stop(*_: Any) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    try:
        with psycopg.connect(settings.database_url) as conn:
            while running:
                msg = consumer.poll(1.0)
                if msg is None:
                    if idle_timeout and (time.monotonic() - last_seen) >= idle_timeout:
                        break
                    continue
                if msg.error():
                    raise KafkaException(msg.error())

                last_seen = time.monotonic()
                try:
                    evt = json.loads(msg.value())
                    row = to_row(evt)
                except (ValueError, TypeError) as exc:
                    print(f"skip bad message: {exc}")
                    consumer.commit(msg)
                    continue

                with conn.cursor() as cur:
                    cur.execute(INSERT_SQL, row)
                conn.commit()
                consumer.commit(msg)  # DB 커밋 후 오프셋 커밋
                inserted += 1
    finally:
        consumer.close()

    print(f"bronze 적재 완료: {inserted} 건")
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(prog="reco-consumer", description="Kafka → Bronze 컨슈머 (#13)")
    parser.add_argument(
        "--idle-timeout",
        type=float,
        default=0.0,
        help="이 시간(초) 동안 메시지가 없으면 종료 (0=무한 실행)",
    )
    args = parser.parse_args()
    run_consumer(idle_timeout=args.idle_timeout)


if __name__ == "__main__":
    main()
