"""bronze 리더 단위 테스트 — 커넥션 스텁으로 페이지네이션/역직렬화/불량행 스킵 검증."""

from typing import Any

from pipelines.bronze import iter_events
from py_common import EventType


def _event_payload(event_id: str, event_type: str = "impression") -> dict[str, Any]:
    return {
        "eventId": event_id,
        "eventType": event_type,
        "userId": "u-1",
        "itemId": "p-1",
        "ts": "2026-06-27T00:00:00Z",
        "context": {"requestId": "r-1"},
    }


class _StubCursor:
    """execute의 after_id/batch_size 파라미터를 존중하는 events_raw 스텁."""

    def __init__(self, rows: list[tuple[int, dict]]) -> None:
        self._all = rows
        self._page: list[tuple[int, dict]] = []

    def execute(self, _sql: str, params: dict) -> None:
        after = params["after_id"]
        self._page = [r for r in self._all if r[0] > after][: params["batch_size"]]

    def fetchall(self) -> list[tuple[int, dict]]:
        return self._page

    def __enter__(self) -> "_StubCursor":
        return self

    def __exit__(self, *_: object) -> None:
        pass


class _StubConn:
    def __init__(self, rows: list[tuple[int, dict]]) -> None:
        self._rows = rows

    def cursor(self) -> _StubCursor:
        return _StubCursor(self._rows)


def test_reads_all_rows_across_pages_in_order() -> None:
    rows = [(i, _event_payload(f"e-{i}")) for i in range(1, 6)]
    conn: Any = _StubConn(rows)

    result = list(iter_events(conn, batch_size=2))  # 5행을 2행 페이지로

    assert [row_id for row_id, _ in result] == [1, 2, 3, 4, 5]
    assert all(e.event_type is EventType.IMPRESSION for _, e in result)
    assert result[0][1].event_id == "e-1"


def test_after_id_resumes_incrementally() -> None:
    rows = [(i, _event_payload(f"e-{i}")) for i in range(1, 6)]
    conn: Any = _StubConn(rows)

    result = list(iter_events(conn, after_id=3))

    assert [row_id for row_id, _ in result] == [4, 5]


def test_bad_rows_are_skipped_via_on_skip_callback() -> None:
    rows = [
        (1, _event_payload("e-1")),
        (2, {"eventId": "e-2", "eventType": "wishlist", "ts": "2026-06-27T00:00:00Z"}),  # 모르는 타입
        (3, _event_payload("e-3", "purchase")),
    ]
    conn: Any = _StubConn(rows)
    skipped: list[int] = []

    result = list(iter_events(conn, on_skip=lambda row_id, _exc: skipped.append(row_id)))

    assert [e.event_id for _, e in result] == ["e-1", "e-3"]
    assert skipped == [2]
