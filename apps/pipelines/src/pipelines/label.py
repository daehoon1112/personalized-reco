"""Silver 라벨링(#14) — bronze(events_raw)를 읽어 impression_label을 채운다.

attribution v1 규칙(docs/data-model.md "Attribution v1", V3 마이그레이션 주석과 동일):
  click    = 같은 (session_id, request_id, item_id)에서 impression 이후 가장 이른 click 귀속
  cart     = 같은 키에서 impression 이후 가장 이른 cart 귀속 (click과 대칭 규칙)
  purchase = anchor(click_date, 없으면 cart_date)로부터 24h 이내 가장 이른 purchase 귀속.
             anchor가 없으면(click도 cart도 없으면) 귀속하지 않는다.
규칙 버전은 LABEL_VERSION 하나로 관리한다 — 윈도/규칙이 바뀌면 이 문자열을 올리고 전량 재라벨링.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

import psycopg

from pipelines.bronze import OnSkip, iter_events, log_skip
from py_common import Event, EventType

logger = logging.getLogger(__name__)

LABEL_VERSION = "v1:click=session+request,purchase=24h"
_PURCHASE_WINDOW = timedelta(hours=24)
_UPSERT_CHUNK = 500

AttributionKey = tuple[str | None, str | None, str | None]  # (session_id, request_id, item_id)

# 조인 불가능한 impression(예: item_id 누락)을 만났을 때 호출된다 — (row_id, 사유)
LabelSkip = Callable[[int, str], None]


def _log_label_skip(row_id: int, reason: str) -> None:
    logger.warning("skip impression row_id=%d: %s", row_id, reason)


@dataclass(frozen=True, slots=True)
class ImpressionLabelRow:
    """impression_label 1행 — V3 마이그레이션 컬럼과 1:1 대응."""

    impression_id: str
    event_date: datetime
    user_id: str | None
    item_id: str
    session_id: str | None
    request_id: str | None
    position: int | None
    device: str | None
    page: str | None
    model_version: str | None
    is_click: bool
    click_date: datetime | None
    is_cart: bool
    cart_date: datetime | None
    is_purchase: bool
    purchase_date: datetime | None
    purchase_amount: int | None
    label: int
    label_version: str = LABEL_VERSION


def _earliest_after(events: list[Event], after_ts: datetime) -> Event | None:
    """after_ts보다 엄격히 나중인 이벤트 중 가장 이른 것 (같은 ts는 후행으로 보지 않음)."""
    candidates = [e for e in events if e.ts > after_ts]
    return min(candidates, key=lambda e: e.ts) if candidates else None


def _earliest_in_window(events: list[Event], anchor: datetime, window: timedelta) -> Event | None:
    """[anchor, anchor+window] 구간의 이벤트 중 가장 이른 것."""
    candidates = [e for e in events if anchor <= e.ts <= anchor + window]
    return min(candidates, key=lambda e: e.ts) if candidates else None


def build_label_rows(
    events: Iterable[tuple[int, Event]],
    on_skip: LabelSkip | None = None,
) -> list[ImpressionLabelRow]:
    """(row_id, Event) 스트림 → ImpressionLabelRow 목록. DB 없는 순수 함수.

    click/cart/purchase가 impression보다 나중 bronze 페이지에 있을 수 있어 전량을 먼저
    귀속 키별로 버킷에 담은 뒤 impression마다 조회하는 2-패스 방식이다.

    TODO(#10): 이 방식은 bronze 전량을 메모리에 올린다(`batch_size`는 DB 페이징 크기일 뿐
    스트리밍이 아니다). 볼륨이 커지면 (a) `iter_events(after_id=...)` 증분 + (b) 세션/시간
    윈도 단위 분할 처리로 바꿔야 한다 — impression이 가장 볼륨이 큰 이벤트라 OOM 1순위다.
    """
    skip = on_skip if on_skip is not None else _log_label_skip

    buckets: dict[AttributionKey, dict[EventType, list[Event]]] = defaultdict(lambda: defaultdict(list))
    impressions: list[Event] = []

    for row_id, event in events:
        if event.is_impression:
            if event.item_id is None:
                skip(row_id, "impression missing item_id")
                continue
            if None in event.attribution_key:
                skip(row_id, f"impression missing attribution key: {event.attribution_key}")
                continue
            impressions.append(event)
        buckets[event.attribution_key][event.event_type].append(event)

    rows: list[ImpressionLabelRow] = []
    for imp in impressions:
        assert imp.item_id is not None  # 위에서 None인 impression은 이미 스킵됨
        key = imp.attribution_key
        by_type = buckets[key]

        click = _earliest_after(by_type.get(EventType.CLICK, []), imp.ts)
        cart = _earliest_after(by_type.get(EventType.CART, []), imp.ts)

        anchor = click.ts if click else (cart.ts if cart else None)
        purchase = (
            _earliest_in_window(by_type.get(EventType.PURCHASE, []), anchor, _PURCHASE_WINDOW)
            if anchor is not None
            else None
        )

        rows.append(
            ImpressionLabelRow(
                impression_id=imp.event_id,
                event_date=imp.ts,
                user_id=imp.user_id,
                item_id=imp.item_id,
                session_id=imp.session_id,
                request_id=key[1],
                position=imp.position,
                device=imp.context.device if imp.context else None,
                page=imp.context.page if imp.context else None,
                model_version=imp.context.model_version if imp.context else None,
                is_click=click is not None,
                click_date=click.ts if click else None,
                is_cart=cart is not None,
                cart_date=cart.ts if cart else None,
                is_purchase=purchase is not None,
                purchase_date=purchase.ts if purchase else None,
                purchase_amount=(purchase.context.amount if purchase and purchase.context else None),
                label=3 if purchase else 2 if cart else 1 if click else 0,
            )
        )
    return rows


_UPSERT_SQL = """
INSERT INTO impression_label (
    impression_id, event_date, user_id, item_id, session_id, request_id,
    position, device, page, model_version,
    is_click, click_date, is_cart, cart_date,
    is_purchase, purchase_date, purchase_amount,
    label, label_version
) VALUES (
    %(impression_id)s, %(event_date)s, %(user_id)s, %(item_id)s, %(session_id)s, %(request_id)s,
    %(position)s, %(device)s, %(page)s, %(model_version)s,
    %(is_click)s, %(click_date)s, %(is_cart)s, %(cart_date)s,
    %(is_purchase)s, %(purchase_date)s, %(purchase_amount)s,
    %(label)s, %(label_version)s
)
ON CONFLICT (impression_id) DO UPDATE SET
    event_date      = EXCLUDED.event_date,
    user_id         = EXCLUDED.user_id,
    item_id         = EXCLUDED.item_id,
    session_id      = EXCLUDED.session_id,
    request_id      = EXCLUDED.request_id,
    position        = EXCLUDED.position,
    device          = EXCLUDED.device,
    page            = EXCLUDED.page,
    model_version   = EXCLUDED.model_version,
    is_click        = EXCLUDED.is_click,
    click_date      = EXCLUDED.click_date,
    is_cart         = EXCLUDED.is_cart,
    cart_date       = EXCLUDED.cart_date,
    is_purchase     = EXCLUDED.is_purchase,
    purchase_date   = EXCLUDED.purchase_date,
    purchase_amount = EXCLUDED.purchase_amount,
    label           = EXCLUDED.label,
    label_version   = EXCLUDED.label_version
"""


@dataclass(frozen=True, slots=True)
class LabelReport:
    """배치 1회 결과. 손실(스킵·실패)을 호출자에게 숫자로 돌려준다 —
    라벨 수가 조용히 줄어드는 것이 학습 데이터 편향으로 이어지기 때문이다."""

    labeled: int = 0
    skipped_bronze: int = 0       # payload 계약 위반 (깨진 JSON·tz 없는 ts 등)
    skipped_impression: int = 0   # 조인 키(session/request/item) 누락으로 귀속 불가
    failed: int = 0               # impression_label 적재 실패 (길이 초과·타입 불일치 등)

    @property
    def has_losses(self) -> bool:
        return bool(self.skipped_bronze or self.skipped_impression or self.failed)


def _upsert_rows(
    conn: psycopg.Connection,
    rows: list[ImpressionLabelRow],
    chunk_size: int = _UPSERT_CHUNK,
) -> tuple[int, int]:
    """청크 단위로 커밋한다. 청크가 깨지면 행 단위로 재시도해 불량 행만 버린다.

    bronze는 TEXT(무제한)인데 impression_label은 varchar(36)/(50)이고 amount/position은
    타입 검증이 없다 — 계약 밖 값 1건이 전체를 롤백시키면, bronze는 append-only라
    그 행을 지우기 전까지 배치가 영구히 실패한다.

    @return (성공 행 수, 실패 행 수)
    """
    ok = failed = 0
    for start in range(0, len(rows), chunk_size):
        chunk = rows[start : start + chunk_size]
        params = [asdict(row) for row in chunk]
        try:
            with conn.cursor() as cur:
                cur.executemany(_UPSERT_SQL, params)
            conn.commit()
            ok += len(chunk)
            continue
        except psycopg.Error as exc:
            conn.rollback()
            logger.warning("chunk upsert 실패 → 행 단위 폴백 (offset=%d): %s", start, exc)

        for row, param in zip(chunk, params, strict=True):
            try:
                with conn.cursor() as cur:
                    cur.execute(_UPSERT_SQL, param)
                conn.commit()
                ok += 1
            except psycopg.Error as exc:
                conn.rollback()
                failed += 1
                logger.warning(
                    "skip bad label row impression_id=%s: %s", row.impression_id, exc
                )
    return ok, failed


def run_label(
    conn: psycopg.Connection,
    batch_size: int = 1000,
    on_skip: OnSkip | None = None,
    label_skip: LabelSkip | None = None,
) -> LabelReport:
    """bronze 전량을 읽어 라벨링하고 impression_label에 upsert.

    on_skip/label_skip 미지정 시 기본 로거로 위임하되, 스킵 건수는 항상 센다.
    """
    counts = {"bronze": 0, "impression": 0}

    def count_bronze_skip(row_id: int, exc: Exception) -> None:
        counts["bronze"] += 1
        (on_skip or log_skip)(row_id, exc)

    def count_label_skip(row_id: int, reason: str) -> None:
        counts["impression"] += 1
        (label_skip or _log_label_skip)(row_id, reason)

    events = iter_events(conn, batch_size=batch_size, on_skip=count_bronze_skip)
    rows = build_label_rows(events, on_skip=count_label_skip)
    labeled, failed = _upsert_rows(conn, rows)
    return LabelReport(
        labeled=labeled,
        skipped_bronze=counts["bronze"],
        skipped_impression=counts["impression"],
        failed=failed,
    )
