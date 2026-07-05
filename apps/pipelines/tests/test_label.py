"""silver 라벨링(#14) 단위 테스트 — DB 없이 build_label_rows의 attribution 로직 검증."""

from datetime import datetime, timedelta, timezone
from typing import Any

from pipelines.bronze import iter_events
from pipelines.label import LABEL_VERSION, ImpressionLabelRow, build_label_rows
from py_common import Event, EventContext, EventType

_T0 = datetime(2026, 6, 27, 0, 0, 0, tzinfo=timezone.utc)


def _impression(
    event_id: str = "e-imp",
    ts: datetime = _T0,
    session_id: str = "s-1",
    request_id: str = "r-1",
    item_id: str = "p-1",
    user_id: str | None = "u-1",
    position: int | None = 1,
    device: str | None = "pc",
    page: str | None = "category",
    model_version: str | None = "pop-v0",
) -> Event:
    return Event(
        event_id=event_id,
        event_type=EventType.IMPRESSION,
        ts=ts,
        user_id=user_id,
        item_id=item_id,
        session_id=session_id,
        position=position,
        consent=True,
        context=EventContext(device=device, page=page, request_id=request_id, model_version=model_version),
    )


def _action(
    event_type: EventType,
    event_id: str,
    ts: datetime,
    session_id: str = "s-1",
    request_id: str = "r-1",
    item_id: str = "p-1",
    user_id: str | None = "u-1",
    amount: int | None = None,
) -> Event:
    return Event(
        event_id=event_id,
        event_type=event_type,
        ts=ts,
        user_id=user_id,
        item_id=item_id,
        session_id=session_id,
        consent=True,
        context=EventContext(request_id=request_id, amount=amount),
    )


def _rows_by_impression(events: list[Event]) -> dict[str, ImpressionLabelRow]:
    stream = [(i, e) for i, e in enumerate(events, start=1)]
    rows = build_label_rows(stream)
    return {r.impression_id: r for r in rows}


def test_happy_path_impression_click_cart_purchase_within_24h() -> None:
    imp = _impression()
    click = _action(EventType.CLICK, "e-click", _T0 + timedelta(minutes=1))
    cart = _action(EventType.CART, "e-cart", _T0 + timedelta(minutes=2))
    purchase = _action(EventType.PURCHASE, "e-purchase", _T0 + timedelta(hours=1), amount=10000)

    rows = _rows_by_impression([imp, click, cart, purchase])
    row = rows["e-imp"]

    assert row.label == 3
    assert row.is_click and row.click_date == click.ts
    assert row.is_cart and row.cart_date == cart.ts
    assert row.is_purchase and row.purchase_date == purchase.ts
    assert row.purchase_amount == 10000
    assert row.device == "pc"
    assert row.page == "category"
    assert row.model_version == "pop-v0"
    assert row.label_version == LABEL_VERSION


def test_impression_with_no_click_ever() -> None:
    imp = _impression()
    rows = _rows_by_impression([imp])
    row = rows["e-imp"]

    assert row.label == 0
    assert not row.is_click and row.click_date is None
    assert not row.is_cart and row.cart_date is None
    assert not row.is_purchase and row.purchase_date is None


def test_purchase_anchor_prefers_click_date_over_cart_date() -> None:
    imp = _impression()
    click = _action(EventType.CLICK, "e-click", _T0 + timedelta(minutes=1))
    cart = _action(EventType.CART, "e-cart", _T0 + timedelta(hours=2))
    # click_date와 cart_date 사이에 purchase를 둬서 두 anchor가 다른 결과를 내도록 구성:
    # anchor=click_date면 [click_date, click_date+24h] 안이라 귀속되고,
    # anchor=cart_date면 purchase가 cart_date보다 앞이라(윈도 시작 전) 귀속되지 않는다.
    purchase = _action(EventType.PURCHASE, "e-purchase", _T0 + timedelta(hours=1), amount=5000)

    rows = _rows_by_impression([imp, click, cart, purchase])
    row = rows["e-imp"]

    assert row.is_click and row.is_cart
    assert row.is_purchase
    assert row.purchase_date == purchase.ts
    assert row.label == 3


def test_cart_then_purchase_within_24h_without_click() -> None:
    imp = _impression()
    cart = _action(EventType.CART, "e-cart", _T0 + timedelta(minutes=5))
    purchase = _action(EventType.PURCHASE, "e-purchase", cart.ts + timedelta(hours=2), amount=20000)

    rows = _rows_by_impression([imp, cart, purchase])
    row = rows["e-imp"]

    assert not row.is_click and row.click_date is None
    assert row.is_cart
    assert row.is_purchase and row.purchase_date == purchase.ts
    assert row.label == 3


def test_purchase_more_than_24h_after_click_is_not_attributed() -> None:
    imp = _impression()
    click = _action(EventType.CLICK, "e-click", _T0 + timedelta(minutes=1))
    purchase = _action(
        EventType.PURCHASE, "e-purchase", click.ts + timedelta(hours=24, minutes=1), amount=1000
    )

    rows = _rows_by_impression([imp, click, purchase])
    row = rows["e-imp"]

    assert row.is_click
    assert not row.is_purchase
    assert row.purchase_date is None
    assert row.purchase_amount is None
    assert row.label == 1


def test_purchase_with_no_prior_click_or_cart_is_not_attributed() -> None:
    imp = _impression()
    purchase = _action(EventType.PURCHASE, "e-purchase", _T0 + timedelta(minutes=10), amount=1000)

    rows = _rows_by_impression([imp, purchase])
    row = rows["e-imp"]

    assert not row.is_click and not row.is_cart
    assert not row.is_purchase
    assert row.label == 0


def test_multiple_keys_interleaved_do_not_cross_contaminate() -> None:
    imp_a = _impression(event_id="e-imp-a", session_id="s-1", request_id="r-1", item_id="p-1")
    click_a = _action(
        EventType.CLICK, "e-click-a", _T0 + timedelta(minutes=1), session_id="s-1", request_id="r-1", item_id="p-1"
    )
    imp_b = _impression(event_id="e-imp-b", session_id="s-2", request_id="r-2", item_id="p-2")
    # b와 같은 item_id/세션이 아니므로 a의 click이 b에 붙으면 안 된다.

    rows = _rows_by_impression([imp_a, click_a, imp_b])

    assert rows["e-imp-a"].is_click
    assert not rows["e-imp-b"].is_click


def test_bad_row_is_skipped_via_bronze_on_skip_without_killing_batch() -> None:
    class _StubCursor:
        def __init__(self, rows: list[tuple[int, Any]]) -> None:
            self._rows = rows

        def execute(self, _sql: str, params: dict) -> None:
            after = params["after_id"]
            self._page = [r for r in self._rows if r[0] > after][: params["batch_size"]]

        def fetchall(self) -> list[tuple[int, Any]]:
            return self._page

        def __enter__(self) -> "_StubCursor":
            return self

        def __exit__(self, *_: object) -> None:
            pass

    class _StubConn:
        def __init__(self, rows: list[tuple[int, Any]]) -> None:
            self._rows = rows

        def cursor(self) -> _StubCursor:
            return _StubCursor(self._rows)

    good_payload = {
        "eventId": "e-imp",
        "eventType": "impression",
        "userId": "u-1",
        "itemId": "p-1",
        "sessionId": "s-1",
        "position": 1,
        "ts": "2026-06-27T00:00:00Z",
        "context": {"requestId": "r-1"},
    }
    bad_payload = {"eventId": "e-bad", "eventType": "wishlist", "ts": "2026-06-27T00:00:00Z"}
    conn: Any = _StubConn([(1, good_payload), (2, bad_payload)])

    skipped: list[int] = []
    rows = build_label_rows(
        iter_events(conn, on_skip=lambda row_id, _exc: skipped.append(row_id))
    )

    assert skipped == [2]
    assert [r.impression_id for r in rows] == ["e-imp"]


def test_impression_missing_item_id_is_dropped_via_label_skip() -> None:
    imp = _impression(item_id=None)  # type: ignore[arg-type]
    skipped: list[tuple[int, str]] = []

    rows = build_label_rows([(1, imp)], on_skip=lambda row_id, reason: skipped.append((row_id, reason)))

    assert rows == []
    assert skipped and skipped[0][0] == 1


def test_click_at_exact_same_timestamp_as_impression_is_not_attributed() -> None:
    imp = _impression(ts=_T0)
    click = _action(EventType.CLICK, "e-click", _T0)

    rows = _rows_by_impression([imp, click])
    row = rows["e-imp"]

    assert not row.is_click
    assert row.label == 0


def test_batch_contract_invariants() -> None:
    imp1 = _impression(event_id="e-1", item_id="p-1")
    click1 = _action(EventType.CLICK, "e-1-click", _T0 + timedelta(minutes=1), item_id="p-1")
    purchase1 = _action(
        EventType.PURCHASE, "e-1-purchase", click1.ts + timedelta(hours=1), item_id="p-1", amount=999
    )

    imp2 = _impression(event_id="e-2", item_id="p-2", session_id="s-2", request_id="r-2")

    rows = _rows_by_impression([imp1, click1, purchase1, imp2])

    for row in rows.values():
        assert row.label in {0, 1, 2, 3}
        if row.is_click:
            assert row.click_date is not None
        if row.is_purchase:
            assert row.purchase_date is not None
            assert row.purchase_amount is not None
            assert row.click_date is not None or row.cart_date is not None
            anchor = row.click_date or row.cart_date
            assert anchor is not None
            assert row.purchase_date - anchor <= timedelta(hours=24)
