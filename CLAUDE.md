# CLAUDE.md

이 파일은 Claude Code가 프로젝트 맥락을 이해하도록 돕는 가이드다.
초기 "결정 필요(OPEN)" 항목은 대부분 확정되었다(맨 아래 참조). 남은 미정 항목은 임의로
가정하지 말고 먼저 질문할 것.

## 프로젝트 개요

개인화 추천 서비스 (**이커머스 / 상품 도메인**). 목표는 단순히 "관련성 높은 항목을 노출"하는
것이 아니라, 퍼스트파티 행동 데이터를 기반으로 한 **실시간 ML 랭킹으로 비즈니스 성과
(전환·매출)를 최적화**하는 것. (Moloco 접근 방식 참고: 노출 하나하나를 학습해 지속적으로
성과를 개선하는 순환 구조)

성격·규모: **실서비스 초기(소규모)**. 초기에는 배치로 추천을 사전계산하고, 데이터·트래픽이
쌓이면 단계적으로 고도화한다.

## 핵심 아키텍처: 2단계 파이프라인

```
사용자 요청 → 후보 생성(retrieval) → 랭킹(ranking) → 추천 노출
                수만 → 수백          정밀 점수화        최종 결과
```

- **후보 생성(retrieval)**: 전체 아이템 중 후보를 넓게 추려 수백 개로 축소 (속도 우선).
- **랭킹(ranking)**: 추려진 후보를 정밀하게 점수화해 정렬 (정확도 우선).
- **피드백 루프(flywheel)**: 노출/클릭/전환 로그 → 데이터·피처 스토어 → 모델 재학습.

> **핫 패스 / 콜드 패스 분리**: 이벤트 수집은 동기 DB 쓰기가 아니라 **Kafka로 produce 후 즉시
> 반환**(impression 로깅도 fire-and-forget). 적재·학습은 비동기/배치. 서빙은 사전계산 결과만 읽음.
> 다이어그램은 [README.md](./README.md) 참조.

## 기술 스택 (확정)

- **서빙 / 비즈니스 (JVM)**: Kotlin + **Spring Boot 3.x**(+ Spring for Apache Kafka),
  Gradle(Kotlin DSL) + Wrapper, JDK **21 LTS** 툴체인 고정, DB 마이그레이션 **Flyway**(JVM 측 소유).
- **메시징**: **Apache Kafka (KRaft 모드, ZooKeeper 없음)** — docker-compose 단일 브로커.
  수집 API=프로듀서, 별도 컨슈머가 Bronze 적재.
- **ML / 데이터 (Python)**: Python 3.12 + **uv**(워크스페이스/패키지), pandas·numpy·scikit-learn,
  psycopg(Postgres). 모델은 인기순 → implicit/LightFM(CF) → 하이브리드 → 딥러닝 순.
- **데이터**: **PostgreSQL 16 단일 저장소** — Bronze/Silver/Gold 레이어 + 서빙 결과를 모두 Postgres로
  운영(소규모 초기 단순화). 로컬은 **Docker Compose**(Postgres + Kafka). Redis는 추후.
- **이벤트 스키마 단일 소스**: **Protobuf + buf** → Kotlin·Python 코드젠 (payload는 proto-over-JSON).
- **구조**: 폴리글랏 모노레포 — Gradle(Kotlin) + uv(Python), 루트 **Makefile**로 통합 태스크.
- **CI**: GitHub Actions (gradle build/test · uv sync/test · buf lint).

## 모노레포 구조

```
apps/serving        # Kotlin · Spring Boot — 수집 API(producer) + 컨슈머(bronze 적재) + 추천 서빙 (+ Flyway)
apps/pipelines      # Python — silver 라벨링 · gold/인기순 랭킹 · 오프라인 평가 · 합성 이벤트 생성
packages/schema-py  # protobuf → Python 코드젠
packages/py-common  # Python 공유 (DB·설정·지표)
contracts/proto     # ★ 이벤트/아이템/유저 스키마 단일 소스 + buf.yaml
infra               # docker-compose (Postgres + Kafka KRaft)
data                # 로컬 산출물 (gitignore)
```

## 데이터 전략 (가장 중요한 기반)

- **이벤트 로깅 스키마**: impression / click / cart / purchase 등 행동을 기록.
  → Protobuf 단일 소스로 초기에 확정. 나중에 바꾸기 매우 어려움. 이벤트 엔벨로프에는
  event_id·user_id·item_id·session_id·ts·event_type·context·**position(노출 순위)**·**consent(동의)** 포함.
- **수집은 비동기**: 요청 경로에서 DB를 직접 쓰지 않고 Kafka로 흘려보낸다(고볼륨 impression 대비).
- **메타데이터**: 아이템 속성, 유저 프로필.
- **콜드 스타트**: 신규 유저/아이템은 인기순·콘텐츠 기반 폴백으로 대응.
- **피처 스토어**: 행동·아이템·컨텍스트 피처를 후보 생성/랭킹 단계에 공급.

## 데이터 레이어링 & 학습 데이터

원천 이벤트(atomic) ≠ 학습 예제(labeled). **전부 Postgres** 안에서 레이어로 가공해 모델에 먹인다.

- **Bronze** `events_raw`: 받은 그대로의 불변 이벤트(append-only).
- **Silver** `labeled_impressions`: 세션화·중복제거 + impression↔결과(click/purchase) 조인 라벨링.
- **Gold**: 모델별 학습 입력 — `item_popularity`(인기순), `user_item_interactions`(CF용 암묵 피드백).

모델 단계별 입력 구조:
- 인기순(MVP): `(item_id, window, click_cnt, purchase_cnt, score)` 집계.
- CF: 암묵 피드백 `(user_id, item_id, weight)` → 희소 행렬(implicit/LightFM).
- 랭킹/딥러닝: impression 단위 라벨 예제
  `(ts, user_id, item_id, position, context, user_features, item_features, label, served_model_version)`.

반드시 지킬 것 (스키마에 미리 반영):
- **Point-in-time correctness(누수 방지)**: 피처는 impression 시점 상태 기준.
- **Attribution window**: 라벨 귀속 윈도 정의(예: 클릭=세션 내, 구매=24h 내).
- **Position bias**: position 로깅 → 추후 보정(IPS 등).

## 모델링 (MVP-first, 단계적 고도화)

1. 규칙 기반 + 인기순
2. 협업 필터링 (유저/아이템 유사도)
3. 콘텐츠 기반 / 하이브리드
4. 딥러닝 (데이터·트래픽이 쌓인 후)

> 처음부터 딥러닝·실시간을 전부 넣지 말 것. 단순하게 시작해 검증 후 고도화.

## 평가 & 피드백

- **오프라인 지표**: Precision@K, NDCG, Recall@K 로 모델 사전 검증.
- **온라인 검증**: A/B 테스트로 클릭률·전환율 등 비즈니스 지표 확인 (필수).
- **북극성 지표(잠정)**: 전환율(CVR), 가드레일 GMV. (평가 모듈 구현 시 확정)

## 시스템 아키텍처 결정사항

- 실시간 추론 vs 배치: **초기에는 배치**(추천 결과 사전 계산).
- 이벤트 수집: **비동기(Kafka KRaft)** — 핫 패스에서 분리. 수집 API는 produce 후 202.
- latency · 트래픽: 실서비스 초기 **소규모** 기준. 배치 사전계산 + Postgres로 시작,
  필요 시 서빙 캐시(Redis) 도입. (구체 SLO는 트래픽 측정 후 설정)

## 개인정보 · 보안

- 데이터는 저장·전송 시 암호화.
- 개인정보보호법(PIPA) 준수, 앱이면 추적 동의(ATT) 설계 초기 반영.
- 동의(consent)는 이벤트 스키마 레벨에서 플래그로 관리.

## MVP 로드맵 (빌드 순서)

1. **이벤트 로깅 + 평가 파이프라인 구축 및 검증**  ← 현재 단계
2. 협업 필터링으로 개인화 적용
3. A/B 테스트로 효과 확인
4. 데이터 축적 후 딥러닝으로 고도화

## 작업 추적

- 1단계(MVP-1)는 GitHub **Milestone `MVP-1`** + **Epic #1** 아래 하위 이슈로 분해(비동기 구조 반영해 확장).
- 구현 임계경로 1순위: **이벤트 스키마(protobuf+buf)** — Kotlin·Python 공유 계약이라 먼저 고정.
- 흐름: 구조 → Kafka·Postgres 인프라 → 스키마/DB(bronze·silver·gold) → 수집(produce)·컨슈머(적재)·서빙
  ∥ silver 라벨링 → gold/인기순 배치 → 오프라인 평가 → CI·엔드투엔드 검증.

## 코딩 컨벤션

- **Kotlin**: ktlint + detekt 통과. Spring Boot 관용(생성자 주입, `@RestController`, DTO 분리).
  널 안전성·`data class` 활용. 패키지 `me.imweb.reco.*`(또는 합의된 루트).
- **Python**: ruff(lint+format) + mypy(타입) 통과. `uv`로 의존성 관리, 함수/모듈 단위 타입 힌트.
- **Proto**: `buf lint` 통과. 필드 번호는 절대 재사용 금지(하위호환). 변경은 add-only 우선.
- **공통**: Conventional Commits(`feat:`, `fix:`, `chore:` …), 짧은 feature 브랜치 → PR.
  통합 명령은 루트 **Makefile** 사용.
- **테스트**: Kotlin = JUnit5, Python = pytest. 파이프라인은 합성 데이터로 엔드투엔드 스모크.

## 결정 필요 (OPEN)

- [x] 추천 대상: **상품·이커머스**로 확정
- [x] 기술 스택: **Kotlin(Spring Boot) + Python(uv) + Postgres + Protobuf/buf**로 확정
- [x] 실시간 vs 배치: **배치 우선**(소규모)으로 확정
- [x] 이벤트 수집: **비동기 Kafka(KRaft)** 로 확정 (동기 호출 폐기)
- [x] 학습 데이터 저장: **전부 Postgres(Bronze/Silver/Gold)** 로 확정
- [ ] 북극성 지표 최종 확정 (잠정 CVR / 가드레일 GMV) — 평가 모듈에서 검증 후 확정
- [ ] 구체 latency SLO·트래픽 목표 (초기 트래픽 측정 후)
- [ ] Attribution window 구체값(클릭/구매 귀속 시간) — silver 라벨링 구현 시 확정
- [ ] Redis(서빙 캐시) · 레이크/웨어하우스 분리 도입 시점
