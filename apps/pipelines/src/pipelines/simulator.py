"""합성 트래픽 시뮬레이터 — 행동 모델 (#9).

가상 유저가 세션을 열고(노출 배치=requestId), 확률적으로 click→cart→purchase 퍼널을
내려가는 이벤트를 생성한다. `data/samples/generate.py`를 정식 편입한 것으로,
와이어 포맷(camelCase 엔벨로프)과 ID 컨벤션(`p-NNNN`/`u-NNNNNN`)을 그대로 따른다.

이 모듈은 **순수/결정적**이다 — `random.Random(seed)`를 주입받고 I/O가 없다.
같은 설정이면 같은 이벤트 시퀀스가 나온다(테스트·회귀 검증의 전제).

generate.py 대비 한 가지 개선: 평평한 CTR 대신 **position-decay CTR**
(`base_ctr / log2(pos + 1)`) — 노출 순위가 낮을수록 클릭이 줄어드는 현실 반영.
추후 position bias 보정(IPS) 검증에 필요한 신호를 데이터에 심어둔다.
"""

from __future__ import annotations

import math
import random
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

CATEGORIES = ["fashion", "beauty", "food", "living", "digital", "sports", "kids", "pet"]
BRANDS = [
    "hauslab", "monday-edition", "oatberry", "kindclub", "roundlab",
    "bytenine", "soltree", "peaksome", "daily-object", "nooni",
]
PAGES = ["home", "category", "search", "product"]
PAGE_WEIGHTS = [4, 3, 2, 1]

# 노출 소스 훅 — 기본은 카탈로그(zipf), --from-api면 추천 API 응답으로 대체된다.
# (user_id, 노출 개수) -> item_id 리스트
ExposureSource = Callable[[str, int], Sequence[str]]


@dataclass(frozen=True)
class SimConfig:
    """시뮬레이션 파라미터. 기본값은 generate.py와 동일한 분포를 만든다."""

    n_events: int = 1000
    n_users: int = 200
    n_items: int = 300
    window_days: int = 7
    # 주의: data/samples(generate.py)의 20260704와 다른 값 — 같은 시드면 PRNG 스트림이 부분
    # 정렬돼 eventId가 겹치고, bronze 멱등성(event_id UNIQUE)이 그만큼을 중복으로 걸러낸다.
    # 같은 시드로 재실행하면 전부 중복 처리(추가 0건) — 데이터를 더 쌓으려면 시드를 바꿀 것.
    seed: int = 20260705
    # 퍼널 전이 확률 — base_ctr는 position 1 기준(감쇠 전), 집계 CTR ~17%가 되도록 보정
    base_ctr: float = 0.28
    cart_rate: float = 0.35
    purchase_rate: float = 0.5
    model_version: str = "sim-v0"
    # 윈도 종료(=가장 최근) 시각. None이면 now(UTC) — 결정성이 필요한 테스트는 명시적으로 고정할 것.
    end_ts: datetime | None = None


@dataclass(frozen=True)
class Item:
    item_id: str
    category: str
    brand: str
    price: int


@dataclass(frozen=True)
class User:
    user_id: str
    consent: bool


@dataclass
class Catalog:
    """아이템(zipf 인기 편중) + 유저 풀."""

    items: list[Item]
    users: list[User]
    item_weights: list[float] = field(default_factory=list)


def click_prob(base_ctr: float, position: int) -> float:
    """position-decay CTR: 1위가 base, 아래로 갈수록 log 감쇠."""
    return base_ctr / math.log2(position + 1)


def build_catalog(config: SimConfig, rng: random.Random) -> Catalog:
    items = [
        Item(
            item_id=f"p-{i + 1:04d}",
            category=rng.choice(CATEGORIES),
            brand=rng.choice(BRANDS),
            price=rng.randrange(3_900, 189_000, 100),
        )
        for i in range(config.n_items)
    ]
    users = [
        User(user_id=f"u-{i + 1:06d}", consent=rng.random() < 0.97)
        for i in range(config.n_users)
    ]
    weights = [1.0 / (rank + 1) ** 0.8 for rank in range(config.n_items)]  # 앞 번호일수록 인기
    return Catalog(items=items, users=users, item_weights=weights)


def _rand_uuid(rng: random.Random) -> str:
    return str(uuid.UUID(int=rng.getrandbits(128), version=4))


def _iso(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ts.microsecond // 1000:03d}Z"


def generate_events(
    config: SimConfig,
    rng: random.Random | None = None,
    exposure_source: ExposureSource | None = None,
) -> list[dict[str, Any]]:
    """이벤트 엔벨로프(camelCase dict) 리스트 생성 — ts 오름차순.

    exposure_source가 없으면 카탈로그에서 zipf 가중 샘플링으로 노출을 구성한다.
    """
    rng = rng or random.Random(config.seed)
    catalog = build_catalog(config, rng)
    price_by_id = {it.item_id: it.price for it in catalog.items}
    end_ts = config.end_ts or datetime.now(timezone.utc)
    base_ts = end_ts - timedelta(days=config.window_days)

    def catalog_exposure(_user_id: str, k: int) -> Sequence[str]:
        picked = rng.choices(range(config.n_items), weights=catalog.item_weights, k=k)
        return [catalog.items[i].item_id for i in dict.fromkeys(picked)]  # 중복 제거, 순서 유지

    source = exposure_source or catalog_exposure

    events: list[dict[str, Any]] = []
    while len(events) < config.n_events:
        user = rng.choice(catalog.users)
        session_id = _rand_uuid(rng)
        request_id = _rand_uuid(rng)
        device = "mobile" if rng.random() < 0.7 else "pc"
        page = rng.choices(PAGES, weights=PAGE_WEIGHTS)[0]
        ts = base_ts + timedelta(seconds=rng.randint(0, config.window_days * 86400 - 3600))

        shown = source(user.user_id, rng.randint(4, 10))
        base_ctx = {
            "device": device,
            "page": page,
            "requestId": request_id,
            "modelVersion": config.model_version,
        }

        def emit(event_type: str, item_id: str, position: int | None,
                 ts: datetime, extra_ctx: dict[str, Any] | None = None) -> None:
            events.append({
                "eventId": _rand_uuid(rng),
                "eventType": event_type,
                "userId": user.user_id,
                "itemId": item_id,
                "sessionId": session_id,
                "position": position,
                "consent": user.consent,
                "ts": _iso(ts),
                "context": {**base_ctx, **(extra_ctx or {})},
            })

        for pos, item_id in enumerate(shown, start=1):
            emit("impression", item_id, pos, ts)
            ts += timedelta(milliseconds=rng.randint(5, 40))

            if rng.random() >= click_prob(config.base_ctr, pos):
                continue
            ts += timedelta(seconds=rng.randint(1, 90))
            emit("click", item_id, pos, ts)

            if rng.random() >= config.cart_rate:
                continue
            ts += timedelta(seconds=rng.randint(10, 300))
            qty = rng.choices([1, 2, 3], weights=[8, 2, 1])[0]
            emit("cart", item_id, None, ts, {"quantity": qty})

            if rng.random() >= config.purchase_rate:
                continue
            ts += timedelta(seconds=rng.randint(60, 1800))
            price = price_by_id.get(item_id, 10_000)  # API 노출 등 카탈로그 밖 아이템 폴백
            emit("purchase", item_id, None, ts, {
                "orderId": f"o-{_rand_uuid(rng)[:8]}",
                "quantity": qty,
                "unitPrice": price,
                "amount": price * qty,
                "currency": "KRW",
            })

    return sorted(events[: config.n_events], key=lambda e: e["ts"])
