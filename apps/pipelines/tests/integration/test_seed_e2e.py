"""E2E 통합 테스트 (#9) — 시뮬레이터 → POST /events → Kafka → bronze-sink → events_raw.

로컬 스택(`make dev`: serving + Kafka + bronze-sink + Postgres)이 떠 있어야 한다.
스택이 없으면 skip — CI에서 인프라 없이 돌아도 깨지지 않는다.
`make test-integration`(pytest -m integration)으로 실행.
"""

import time
import uuid
from datetime import datetime, timezone

import httpx
import psycopg
import pytest

from py_common.config import load_settings
from py_common.event import parse_event
from pipelines.ingest_client import post_events
from pipelines.simulator import SimConfig, generate_events

pytestmark = pytest.mark.integration

SETTINGS = load_settings()
N_EVENTS = 100
POLL_TIMEOUT_S = 30.0


def _stack_up() -> bool:
    try:
        return httpx.get(f"{SETTINGS.serving_url}/health", timeout=2.0).status_code == 200
    except httpx.HTTPError:
        return False


if not _stack_up():
    pytest.skip(
        "로컬 스택(:8080)이 떠 있지 않음 — make dev 후 실행", allow_module_level=True
    )


@pytest.fixture(scope="module")
def batch() -> list[dict]:
    """고정 seed 이벤트 100건 — 단, eventId는 실행마다 새로 발급해 이전 실행 잔여와 격리."""
    events = generate_events(
        SimConfig(n_events=N_EVENTS, end_ts=datetime.now(timezone.utc))
    )
    return [{**e, "eventId": str(uuid.uuid4())} for e in events]


def _count_loaded(conn: psycopg.Connection, event_ids: list[str]) -> int:
    row = conn.execute(
        "SELECT count(*) FROM events_raw WHERE event_id = ANY(%s)", (event_ids,)
    ).fetchone()
    assert row is not None
    return row[0]


def test_seed_events_land_in_bronze(batch: list[dict]) -> None:
    report = post_events(batch, SETTINGS.serving_url, batch_size=40)
    assert report.sent == N_EVENTS

    event_ids = [e["eventId"] for e in batch]
    with psycopg.connect(SETTINGS.database_url) as conn:
        deadline = time.monotonic() + POLL_TIMEOUT_S
        loaded = 0
        while time.monotonic() < deadline:
            loaded = _count_loaded(conn, event_ids)
            if loaded == N_EVENTS:
                break
            time.sleep(1.0)
        assert loaded == N_EVENTS, f"{POLL_TIMEOUT_S}s 내 {loaded}/{N_EVENTS}건만 적재됨"

        # 적재된 payload가 계약을 그대로 보존하는지 — 타입 분포까지 전송분과 일치
        rows = conn.execute(
            "SELECT payload FROM events_raw WHERE event_id = ANY(%s)", (event_ids,)
        ).fetchall()
        loaded_types = sorted(parse_event(payload).event_type for (payload,) in rows)
        sent_types = sorted(e["eventType"] for e in batch)
        assert loaded_types == sent_types


def test_resend_is_idempotent(batch: list[dict]) -> None:
    """같은 배치 재전송 → event_id 유니크로 행 수 불변 (bronze 멱등성)."""
    event_ids = [e["eventId"] for e in batch]
    post_events(batch, SETTINGS.serving_url, batch_size=40)

    time.sleep(3.0)  # 재전송분이 컨슈머를 통과할 시간
    with psycopg.connect(SETTINGS.database_url) as conn:
        assert _count_loaded(conn, event_ids) == N_EVENTS
