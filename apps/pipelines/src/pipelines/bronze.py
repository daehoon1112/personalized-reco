"""Bronze(events_raw) 리더 — payload를 타입드 Event로 역직렬화해서 읽는다.

silver 라벨링(#14)·gold 집계(#10)의 입력 경로. 쓰기(consumer)와 대칭:
consumer가 원본을 그대로 payload에 보존하고, 읽을 때 py_common.Event 계약으로 검증한다.

스킵 정책도 함수로 주입한다(on_skip) — 기본은 경고 로그. 카운트가 필요한 배치는
클로저를 꽂는다: `iter_events(conn, on_skip=lambda row_id, exc: skipped.append(row_id))`.
깨진 행이 배치 전체를 죽이지 않는 것이 원칙이다(bronze는 append-only라 과거 불량 데이터 가능).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterator

import psycopg

from py_common import Event, parse_event

logger = logging.getLogger(__name__)

_SELECT_SQL = """
SELECT id, payload
FROM events_raw
WHERE id > %(after_id)s
ORDER BY id
LIMIT %(batch_size)s
"""

# 계약 위반 행을 만났을 때 호출된다 — (row_id, 원인)
OnSkip = Callable[[int, Exception], None]


def _log_skip(row_id: int, exc: Exception) -> None:
    logger.warning("skip bad bronze row id=%d: %s", row_id, exc)


def iter_events(
    conn: psycopg.Connection,
    after_id: int = 0,
    batch_size: int = 1000,
    on_skip: OnSkip = _log_skip,
) -> Iterator[tuple[int, Event]]:
    """events_raw를 id 오름차순(keyset 페이지네이션)으로 순회하며 (id, Event)를 낸다.

    after_id로 증분 읽기 가능(예: 지난 배치의 마지막 id 이후부터).
    """
    while True:
        with conn.cursor() as cur:
            cur.execute(_SELECT_SQL, {"after_id": after_id, "batch_size": batch_size})
            rows = cur.fetchall()
        if not rows:
            return
        for row_id, payload in rows:
            after_id = row_id
            # psycopg는 jsonb를 dict로 돌려주지만, 드라이버/컬럼 설정에 따라 str일 수 있다
            try:
                raw = json.loads(payload) if isinstance(payload, str) else payload
                event = parse_event(raw)
            except (ValueError, TypeError) as exc:
                on_skip(row_id, exc)
                continue
            yield row_id, event
