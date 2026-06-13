"""컨슈머 통합 테스트 (Testcontainers) — Kafka+Postgres 실제 기동.

produce → run_consumer → Bronze 적재 + 멱등성(중복 메시지가 한 행) 확인.
Docker 필요. `pytest -m integration` 으로만 실행된다.
"""

import json

import pytest

pytestmark = pytest.mark.integration

BRONZE_DDL = """
CREATE TABLE IF NOT EXISTS events_raw (
    id          BIGSERIAL PRIMARY KEY,
    event_id    TEXT NOT NULL UNIQUE,
    event_type  TEXT NOT NULL,
    user_id     TEXT,
    item_id     TEXT,
    session_id  TEXT,
    position    INTEGER,
    consent     BOOLEAN,
    event_ts    TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload     JSONB NOT NULL
);
"""


def test_consumer_lands_events_to_bronze_idempotently(monkeypatch: pytest.MonkeyPatch) -> None:
    import psycopg
    from confluent_kafka import Producer
    from testcontainers.kafka import KafkaContainer
    from testcontainers.postgres import PostgresContainer

    from pipelines.consumer import run_consumer

    with PostgresContainer("postgres:16") as pg, KafkaContainer() as kafka:
        db_url = pg.get_connection_url().replace("postgresql+psycopg2://", "postgresql://")
        bootstrap = kafka.get_bootstrap_server()
        monkeypatch.setenv("DATABASE_URL", db_url)
        monkeypatch.setenv("KAFKA_BOOTSTRAP", bootstrap)

        with psycopg.connect(db_url) as conn:
            conn.execute(BRONZE_DDL)
            conn.commit()

        producer = Producer({"bootstrap.servers": bootstrap})
        evt = {
            "eventId": "evt-1",
            "eventType": "click",
            "userId": "u1",
            "itemId": "i1",
            "ts": "2026-06-13T00:00:00Z",
        }
        # 같은 event_id를 두 번 produce → 멱등성 확인
        producer.produce("events", json.dumps(evt).encode())
        producer.produce("events", json.dumps(evt).encode())
        producer.flush(10)

        processed = run_consumer(idle_timeout=8)
        assert processed >= 1

        with psycopg.connect(db_url) as conn:
            row = conn.execute(
                "SELECT count(*) FROM events_raw WHERE event_id = 'evt-1'"
            ).fetchone()
        assert row is not None
        assert row[0] == 1  # 중복 메시지여도 Bronze에는 한 행 (ON CONFLICT DO NOTHING)
