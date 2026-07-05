"""수집 API 클라이언트 — 시뮬레이터 이벤트를 serving으로 전송 (#9).

Kafka에 직접 붙지 않고 `POST /events`(202)를 쓴다 — 수집 API → Kafka → bronze-sink
전체 경로를 그대로 태우는 것이 목적이라서다(실트래픽과 같은 길).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestReport:
    sent: int
    batches: int
    retried: int


class IngestError(RuntimeError):
    """재시도 후에도 배치 전송이 실패했을 때."""


def post_events(
    events: list[dict[str, Any]],
    serving_url: str,
    batch_size: int = 200,
    client: httpx.Client | None = None,
) -> IngestReport:
    """이벤트를 batch_size 단위로 POST /events 전송. 실패 배치는 1회 재시도.

    client 주입은 테스트용(httpx.MockTransport). 반환값은 전송 요약.
    """
    own_client = client is None
    client = client or httpx.Client(base_url=serving_url, timeout=10.0)
    sent = batches = retried = 0
    try:
        for start in range(0, len(events), batch_size):
            batch = events[start : start + batch_size]
            try:
                resp = client.post("/events", json=batch)
                resp.raise_for_status()
            except httpx.HTTPError as first_error:
                logger.warning("배치 전송 실패(재시도 1회): %s", first_error)
                retried += 1
                try:
                    resp = client.post("/events", json=batch)
                    resp.raise_for_status()
                except httpx.HTTPError as retry_error:
                    raise IngestError(
                        f"배치 전송 실패({start}~{start + len(batch)}): {retry_error}"
                    ) from retry_error
            sent += len(batch)
            batches += 1
        return IngestReport(sent=sent, batches=batches, retried=retried)
    finally:
        if own_client:
            client.close()


def fetch_recommended_items(
    serving_url: str,
    user_id: str,
    client: httpx.Client | None = None,
) -> list[str]:
    """--from-api 모드: 추천 API가 준 노출 아이템 목록.

    현재 serving은 스텁(고정 3개)이지만, #8이 완성되면 이 경로가 진짜 피드백 루프가 된다.
    """
    own_client = client is None
    client = client or httpx.Client(base_url=serving_url, timeout=10.0)
    try:
        resp = client.get("/api/recommendations", params={"userId": user_id})
        resp.raise_for_status()
        return [item["itemId"] for item in resp.json()["items"]]
    finally:
        if own_client:
            client.close()
