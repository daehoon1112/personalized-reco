# 데이터 모델

스키마 소유권은 **Flyway**(`apps/serving/src/main/resources/db/migration/`, #5).
로컬 반영: `make up` 후 `make migrate`(또는 serving 기동 시 자동).

**로컬 개발은 `bootRun` 하나로 끝**: spring-boot-docker-compose(developmentOnly)가 Postgres+Kafka를
자동 기동(start-only — 앱 꺼도 인프라 유지)하고, bootRun 기본 `seed` 프로파일이 Flyway repeatable
마이그레이션(`db/seed/R__seed_sample_data.sql`)으로 **합성 샘플을 멱등 시드**한다
(events_raw 1000 · item 223 · user_profile 85, `ON CONFLICT DO NOTHING`).
시드 SQL은 산출물이므로 직접 편집 금지 — `data/samples/generate.py` → `data/samples/to_seed_sql.py`로 재생성.
운영 배포(jar)에는 developmentOnly도 seed 프로파일도 적용되지 않는다.

## 레이어

```
Kafka(events) ─▶ bronze.events_raw ─▶ silver.impression_label ─▶ gold ─▶ 서빙
                  (#13 컨슈머)          (#14 라벨링 배치)          (#10 배치)   (#8 API)

gold = item_popularity(인기순) · user_item_interaction(CF) · recommendation(사전계산 결과)
메타데이터 = item · user_profile (피처 원천, 이벤트와 논리 참조)
```

| 테이블 | 레이어 | 적재 주체 | 마이그레이션 |
|---|---|---|---|
| `events_raw` | bronze | bronze-sink(Kotlin, #13) | V1 |
| `item`, `user_profile` | 메타 | (추후 동기화 배치) | V2 |
| `impression_label` | silver | 라벨링 배치(#14) | V3 |
| `item_popularity` | gold | 인기순 배치(#10) | V4 |
| `user_item_interaction` | gold | CF 입력 배치 | V4 |
| `recommendation` | gold/서빙 | 모델 배치, 추천 API(#8)가 조회 | V4 |

## DDL 컨벤션

셀러업 DB 가이드를 따르되, MySQL 문법인 부분만 Postgres로 적응:

| 가이드(MySQL) | 이 레포(Postgres 16) |
|---|---|
| PK `bigint AUTO_INCREMENT` | `id bigserial PRIMARY KEY` |
| `datetime(6)` | `timestamptz` (기본 μs 정밀도) |
| `is_delete varchar(1) 'N'` | `is_delete boolean NOT NULL DEFAULT false` |
| 인라인 `COMMENT` | `COMMENT ON TABLE/COLUMN` (전 테이블·컬럼 필수) |
| 인덱스명 `ix_컬럼명` (테이블 스코프) | PG는 스키마 전역 유니크 → `ix_테이블명_컬럼명` (컬럼 언더스코어 제거 규칙 유지) |
| `utf8mb4` | 해당 없음 (UTF-8) |

그대로 적용: PK는 의미 없는 surrogate `id`, 비즈니스 키는 `ux_` UNIQUE INDEX 필수,
문자형 varchar, 실수형 `numeric`(float/double 금지), 금액 KRW 정수 bigint,
복수형·과거형·불명확한 축약 금지, DEFAULT/NULL 명시, 날짜 컬럼 `create_date`/`update_date`/`delete_date`.

예외:
- **`events_raw`**: 컨벤션 도입 이전 테이블. 컨슈머(#13)·기존 볼륨 호환을 위해 기존 스키마 유지(정렬은 후속 이슈).
- **파생 레이어(silver/gold)는 `is_delete` 없음**: bronze에서 전량 재생성(rebuild)이 삭제·정정 수단.
- **물리 FK 없음**: 레이어 간 논리 참조만(재적재 순서 자유, 대량 배치 성능).
- `user`는 PG 예약어라 **`user_profile`** 사용.

## 이벤트 계약 클래스 (코드에서 구조 보기)

bronze `payload`는 원본 JSON 그대로지만, **코드에서 읽을 때는 타입드 모델**을 통한다.
양쪽은 거울상이며 동일한 계약 테스트 케이스로 동기화를 검증한다:

| 측 | 클래스 | 쓰는 곳 | 계약 테스트 |
|---|---|---|---|
| Kotlin (`packages/event-contract`) | `me.imweb.reco.event.Event` (+`EventType`,`EventContext`) | bronze-sink(적재), serving | `EventDeserializationTest` |
| Python (`py_common.event`) | `Event` (+`EventType`,`EventContext`,`parse_event`) | pipelines의 bronze 리더(배치 읽기) | `packages/py-common/tests/test_event.py` |

공통 규칙: 모르는 필드는 무시(전방 호환), 모르는 eventType·eventId/ts 누락은 **실패**(조용히 통과 금지).
수집(ingest)만은 예외로 `EventEnvelope`(Map pass-through) — bronze 원본 보존이 우선이라서다.
proto+buf 코드젠(#4)이 완성되면 이 수동 정의들이 생성 타입으로 대체된다(단일 소스).

## Attribution v1 (확정)

- **click**: 같은 `session_id` + 같은 `request_id` + 같은 `item_id`의 후행 클릭을 해당 impression에 귀속
- **purchase(cart 포함)**: 해당 아이템 `click_date`(없으면 `cart_date`)로부터 **24h** 이내 귀속
- 규칙은 `impression_label.label_version`에 기록(예: `v1:click=session+request,purchase=24h`) →
  윈도 변경 시 버전을 올리고 재라벨링, 서로 다른 버전 혼합 학습 금지

## Point-in-time correctness

`impression_label`의 `device`/`page`/`model_version`은 **impression 이벤트 payload의 스냅샷**이다.
학습 피처는 이 스냅샷과 "impression 시점 이전" 데이터만 사용(미래 정보 누수 방지).
`position`은 노출 순위 그대로 보존 — 추후 position bias 보정(IPS 등) 입력.

## Two-Tower 확장 노트 (추후 V5+)

지금 스키마로 막히지 않는다:
- 학습 예제 = `impression_label`(positive=click/cart/purchase, negative=노출 후 미클릭)이 이미 커버
- user/item 피처 집계 테이블(`user_feature`, `item_feature`)과 임베딩 테이블(pgvector `vector` 컬럼)은
  별도 마이그레이션으로 추가 — `item.attrs`/`user_profile.attrs` jsonb가 그때까지의 확장 슬롯
- 서빙은 동일하게 `recommendation` 사전계산으로 시작(아이템 임베딩 배치 계산), 실시간 유사도는 그 다음 단계
