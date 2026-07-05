"""전송 계층 테스트 — httpx.MockTransport로 배치 분할·202 처리·재시도 검증 (네트워크 없음)."""

import httpx
import pytest

from pipelines.ingest_client import (
    IngestError,
    fetch_recommended_items,
    post_events,
)

BASE = "http://serving.test"


def _make_events(n: int) -> list[dict]:
    return [{"eventId": f"e-{i}", "eventType": "impression"} for i in range(n)]


def test_batching_and_report() -> None:
    received: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        received.append(len(json.loads(request.content)))
        return httpx.Response(202, json={"accepted": received[-1]})

    client = httpx.Client(base_url=BASE, transport=httpx.MockTransport(handler))
    report = post_events(_make_events(450), BASE, batch_size=200, client=client)

    assert received == [200, 200, 50]
    assert report.sent == 450
    assert report.batches == 3
    assert report.retried == 0


def test_retry_once_then_succeed() -> None:
    calls = {"n": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(500)
        return httpx.Response(202)

    client = httpx.Client(base_url=BASE, transport=httpx.MockTransport(handler))
    report = post_events(_make_events(10), BASE, batch_size=200, client=client)

    assert calls["n"] == 2
    assert report.retried == 1
    assert report.sent == 10


def test_fail_after_retry_raises() -> None:
    client = httpx.Client(
        base_url=BASE,
        transport=httpx.MockTransport(lambda _: httpx.Response(500)),
    )
    with pytest.raises(IngestError):
        post_events(_make_events(10), BASE, batch_size=200, client=client)


def test_fetch_recommended_items_parses_stub_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["userId"] == "u-000116"
        return httpx.Response(200, json={
            "userId": "u-000116",
            "strategy": "popularity-fallback (example)",
            "items": [
                {"itemId": "item-1", "score": 0.92},
                {"itemId": "item-2", "score": 0.81},
            ],
        })

    client = httpx.Client(base_url=BASE, transport=httpx.MockTransport(handler))
    assert fetch_recommended_items(BASE, "u-000116", client=client) == ["item-1", "item-2"]
