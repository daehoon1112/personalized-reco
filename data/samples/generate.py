"""personalized-reco 예시 데이터 생성기 (seed 고정 → 재실행해도 동일 산출물).

현재 코드 계약 기준:
- EventEnvelope(eventId, eventType, userId, itemId, sessionId, position, consent, ts, context)
- eventType ∈ {impression, click, cart, purchase}  (recommender.EVENT_WEIGHTS 소문자)
- consumer.to_row()가 camelCase/snake_case 둘 다 허용하지만 프로듀서(Kotlin)는 camelCase → camelCase로 생성
"""
import csv
import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

SEED = 20260704
N_EVENTS = 1000
N_USERS = 200
N_ITEMS = 300
BASE_TS = datetime(2026, 6, 27, 0, 0, 0, tzinfo=timezone.utc)  # 1주 윈도 시작
WINDOW_DAYS = 7

CATEGORIES = ["fashion", "beauty", "food", "living", "digital", "sports", "kids", "pet"]
BRANDS = ["hauslab", "monday-edition", "oatberry", "kindclub", "roundlab", "bytenine",
          "soltree", "peaksome", "daily-object", "nooni"]
PAGES = ["home", "category", "search", "product"]

rng = random.Random(SEED)


def rand_uuid() -> str:
    return str(uuid.UUID(int=rng.getrandbits(128), version=4))


def iso(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ts.microsecond // 1000:03d}Z"


# ── item 카탈로그: 카테고리/브랜드/가격 + zipf 인기 편중 ──────────────────────
items = []
for i in range(N_ITEMS):
    cat = rng.choice(CATEGORIES)
    items.append({
        "item_id": f"p-{i + 1:04d}",
        "category": cat,
        "brand": rng.choice(BRANDS),
        "price": rng.randrange(3_900, 189_000, 100),
        "currency": "KRW",
        "status": "sale" if rng.random() < 0.93 else "soldout",
        "created_at": iso(BASE_TS - timedelta(days=rng.randint(10, 400))),
    })
item_weights = [1.0 / (rank + 1) ** 0.8 for rank in range(N_ITEMS)]  # 앞 번호일수록 인기

# ── user 프로필 ───────────────────────────────────────────────────────────────
users = []
for i in range(N_USERS):
    users.append({
        "user_id": f"u-{i + 1:06d}",
        "gender": rng.choice(["F", "M", ""]),
        "birth_year": rng.randint(1972, 2006) if rng.random() < 0.9 else "",
        "joined_at": iso(BASE_TS - timedelta(days=rng.randint(0, 720))),
        "consent": rng.random() < 0.97,
    })

# ── 이벤트: 세션 단위 퍼널(impression→click→cart→purchase) ────────────────────
events = []
while len(events) < N_EVENTS:
    user = rng.choice(users)
    session_id = rand_uuid()
    device = "mobile" if rng.random() < 0.7 else "pc"
    page = rng.choices(PAGES, weights=[4, 3, 2, 1])[0]
    ts = BASE_TS + timedelta(seconds=rng.randint(0, WINDOW_DAYS * 86400 - 3600))

    request_id = rand_uuid()
    shown = rng.sample(range(N_ITEMS), counts=None, k=min(rng.randint(4, 10), N_ITEMS))
    shown = rng.choices(range(N_ITEMS), weights=item_weights, k=rng.randint(4, 10))
    shown = list(dict.fromkeys(shown))  # 중복 제거, 순서 유지

    base_ctx = {"device": device, "page": page, "requestId": request_id, "modelVersion": "pop-v0"}

    for pos, idx in enumerate(shown, start=1):
        item = items[idx]
        events.append({
            "eventId": rand_uuid(),
            "eventType": "impression",
            "userId": user["user_id"],
            "itemId": item["item_id"],
            "sessionId": session_id,
            "position": pos,
            "consent": user["consent"],
            "ts": iso(ts),
            "context": base_ctx,
        })
        ts += timedelta(milliseconds=rng.randint(5, 40))

        if rng.random() < 0.18:  # click
            ts += timedelta(seconds=rng.randint(1, 90))
            events.append({
                "eventId": rand_uuid(),
                "eventType": "click",
                "userId": user["user_id"],
                "itemId": item["item_id"],
                "sessionId": session_id,
                "position": pos,
                "consent": user["consent"],
                "ts": iso(ts),
                "context": base_ctx,
            })
            if rng.random() < 0.35:  # cart
                ts += timedelta(seconds=rng.randint(10, 300))
                qty = rng.choices([1, 2, 3], weights=[8, 2, 1])[0]
                events.append({
                    "eventId": rand_uuid(),
                    "eventType": "cart",
                    "userId": user["user_id"],
                    "itemId": item["item_id"],
                    "sessionId": session_id,
                    "position": None,
                    "consent": user["consent"],
                    "ts": iso(ts),
                    "context": {**base_ctx, "quantity": qty},
                })
                if rng.random() < 0.5:  # purchase
                    ts += timedelta(seconds=rng.randint(60, 1800))
                    events.append({
                        "eventId": rand_uuid(),
                        "eventType": "purchase",
                        "userId": user["user_id"],
                        "itemId": item["item_id"],
                        "sessionId": session_id,
                        "position": None,
                        "consent": user["consent"],
                        "ts": iso(ts),
                        "context": {
                            **base_ctx,
                            "orderId": f"o-{rand_uuid()[:8]}",
                            "quantity": qty,
                            "unitPrice": item["price"],
                            "amount": item["price"] * qty,
                            "currency": "KRW",
                        },
                    })

events = sorted(events[:N_EVENTS], key=lambda e: e["ts"])

# ── 출력 ─────────────────────────────────────────────────────────────────────
out = Path("/Users/daehoon/MyProjects/personalized-reco/data/samples")
out.mkdir(parents=True, exist_ok=True)

with open(out / "events.sample.jsonl", "w") as f:
    for e in events:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")

used_items = {e["itemId"] for e in events}
with open(out / "items.sample.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=items[0].keys())
    w.writeheader()
    w.writerows([it for it in items if it["item_id"] in used_items])

used_users = {e["userId"] for e in events}
with open(out / "users.sample.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=users[0].keys())
    w.writeheader()
    w.writerows([u for u in users if u["user_id"] in used_users])

# POST /events 배치 예시: 한 세션의 퍼널 전체(impression→click→cart→purchase 포함 세션)
by_session: dict[str, list[dict]] = {}
for e in events:
    by_session.setdefault(e["sessionId"], []).append(e)
full = next(evs for evs in by_session.values()
            if {ev["eventType"] for ev in evs} >= {"impression", "click", "cart", "purchase"})
with open(out / "ingest_batch.sample.json", "w") as f:
    json.dump(full, f, ensure_ascii=False, indent=2)

from collections import Counter
c = Counter(e["eventType"] for e in events)
print(f"events: {len(events)} -> {dict(c)}")
print(f"users: {len(used_users)}, items: {len(used_items)}, sessions: {len(by_session)}")
print(f"ingest batch: {len(full)} events (session {full[0]['sessionId'][:8]}...)")
