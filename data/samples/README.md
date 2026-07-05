# 예시 데이터 (합성, seed 고정)

실 DB 대신 쓰는 **합성 예시 데이터**. 현재 코드 계약(`EventEnvelope` · `consumer.to_row()` ·
`recommender.EVENT_WEIGHTS`) 기준으로 생성했고, seed 고정이라 재생성해도 동일하다.

| 파일 | 내용 | 규모 |
|---|---|---|
| `events.sample.jsonl` | 행동 이벤트(엔벨로프 JSON, 1행=1이벤트, ts 오름차순) | 1,000행 — impression 800 / click 137 / cart 45 / purchase 18 |
| `items.sample.csv` | 아이템 메타(카테고리·브랜드·가격) — 이벤트에 등장한 것만 | 223행 |
| `users.sample.csv` | 유저 프로필(성별·출생연도·가입일·consent) — 이벤트에 등장한 것만 | 85행 |
| `ingest_batch.sample.json` | `POST /events` 요청 바디 예시(한 세션의 전체 퍼널 15건) | 1배치 |

## 이벤트 포맷 (엔벨로프)

```json
{
  "eventId": "uuid",
  "eventType": "impression | click | cart | purchase",
  "userId": "u-000123",
  "itemId": "p-0456",
  "sessionId": "uuid",
  "position": 3,
  "consent": true,
  "ts": "2026-06-27T09:12:34.567Z",
  "context": { "device": "mobile", "page": "home", "requestId": "uuid", "modelVersion": "pop-v0" }
}
```

- `position`: **impression/click에만** 존재(노출 순위, 1-base). cart/purchase는 null — position bias 보정용.
- `context.requestId`: 같은 노출 배치(추천 응답 1회)를 묶는 키. 같은 세션의 impression과 그로부터 이어진
  click/cart/purchase가 공유한다 → silver 라벨링(impression↔결과 조인) 때 조인 키로 사용 가능.
- `context` 추가 필드: cart는 `quantity`, purchase는 `orderId·quantity·unitPrice·amount·currency`.
- 퍼널 정합성 보장: click은 반드시 같은 세션의 impression 뒤, cart는 click 뒤, purchase는 cart 뒤(ts 단조 증가).

## 사용 예

```bash
# 수집 API로 배치 전송 (Kafka produce → 202)
curl -X POST localhost:8080/events -H 'Content-Type: application/json' \
  -d @data/samples/ingest_batch.sample.json

# Kafka 우회, bronze events_raw에 직접 적재하고 싶으면 consumer.to_row()와 같은 매핑으로 INSERT
```

## 주의

- 전부 **합성 데이터**다. 아임웹 운영/개발 DB에서 나온 값이 아니며 개인정보 없음.
- 분포는 대략 현실적으로만 맞춤: CTR 17%, click→cart 33%, cart→purchase 40%, 아이템 인기 zipf 편중.
- 재생성: `python3 data/samples/generate.py` (표준 라이브러리만 사용, seed 고정).
- **정식 생성기는 `reco-pipelines seed`(#9, `apps/pipelines/src/pipelines/simulator.py`)** — 이 스크립트를
  기반으로 편입됐고 position-decay CTR이 추가됐다. `--dry-run`이 이 스크립트의 후계(JSONL stdout),
  기본 동작은 `POST /events` 전송(`make seed`). 여기 정적 샘플 파일들은 문서·수동 테스트용으로 유지.
