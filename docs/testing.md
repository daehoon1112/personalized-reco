# 테스트 정책

모듈 성격이 다르므로 테스트 전략도 모듈별로 다르게 간다. 핵심 원칙은 **테스트 피라미드** —
빠르고 결정적인 단위/계약/메트릭 테스트를 많이, 느리고 Docker가 필요한 E2E/통합 테스트는 적게.

| 모듈 | 스택 | 종류 |
|---|---|---|
| `apps/serving` (Kotlin) | **Kotest** + **MockK** + **Testcontainers** | 단위 / E2E |
| `apps/pipelines`·`packages/*` (Python) | **pytest** (+ Testcontainers) | ①결정적 단위 ②계약 ③메트릭 ④행동·회귀 / 컨슈머 통합 |

빠른 테스트는 기본 실행에 포함, Docker가 필요한 테스트는 **태그/마커로 분리**해 따로 돌린다.

---

## 서빙 (Kotlin) — Kotest + MockK + Testcontainers

### 단위 테스트 (`gradle test`, 기본 포함)
- 순수 로직·컨트롤러를 **MockK로 협력자를 모킹**해 빠르게 검증. I/O 없음.
- 예:
  - `HealthController` → `{"status":"UP"}` 반환.
  - `EventIngestController` → 이벤트 N개 POST 시 Kafka로 **정확히 N번 produce**, `eventId`/`ts` 누락 시 채워지는지(`KafkaTemplate`은 MockK mock).

### E2E / 통합 테스트 (`gradle integrationTest`, Docker 필요)
- **Testcontainers로 실제 Kafka(+Postgres)** 를 띄우고 `@SpringBootTest`로 앱 전체를 기동.
- 예: `POST /events` → 실제 `events` 토픽에 메시지가 도착하는지(테스트 컨슈머로 확인).
- Kotest **태그 `Integration`** 으로 표시 → 기본 `test`에서 제외, `integrationTest` 태스크에서만 실행.
  ```
  ./gradlew test            # 단위만 (Docker 불필요)
  ./gradlew integrationTest # Testcontainers E2E (Docker 필요)
  ```

---

## 모델 / 데이터 (Python) — 4종 + 컨슈머 통합

### ① 결정적 단위 테스트 (plain pytest)
입력이 같으면 출력이 같은 부분 — **데이터 전처리, 피처 생성, 후보 생성** 로직. 그냥 값으로 검증.
> 예: `rank_by_popularity(events)`가 동일 입력에 동일 정렬을 반환.

### ② 계약(contract) 테스트
모델이 **약속(형식)** 을 지키는지. 출력값이 아니라 형식·불변식을 본다:
- K개 요청 → **≤ K개** 반환
- **중복 없음**
- **이미 본 아이템(seen) 재추천 안 함**
- **점수가 유효 범위**(예: 0~1, 내림차순)

여러 입력에 대해 파라미터라이즈해서 불변식을 건다.

### ③ 메트릭 코드 검증 (가장 중요)
**Precision@K, NDCG, Recall@K** 구현을 **손으로 답을 아는 작은 픽스처**에 돌려 정확성 확인.
지표가 틀리면 모델 평가 전체가 거짓말이 된다.
> 예: 추천 `[A,B,C,D]`, 정답 `{A,C}` → Precision@2 = 0.5, Recall@4 = 1.0, NDCG@K는 수기 계산값과 일치.

### ④ 행동(behavioral) + 회귀 테스트
- **방향성 기대**: "액션을 많이 본 유저에겐 액션이 코미디보다 높게 랭크된다."
- **콜드 스타트**: 신규 유저가 터지지 않고 **인기순 폴백**을 반환.
- **회귀 가드**: 고정 시드 검증셋에서 **NDCG ≥ 기준선**(baseline). 떨어지면 회귀 의심 → 실패.

### 컨슈머 통합 (Testcontainers, Docker 필요)
- `testcontainers`로 **Kafka+Postgres** 기동 → 이벤트 produce → `run_consumer()` → **Bronze 행 적재 + 멱등성**(중복 메시지가 한 행) 확인.

### 마커 분리
```
pytest                     # 기본: 빠른 테스트만 (integration 제외)
pytest -m integration      # Testcontainers 통합만 (Docker 필요)
```
`pyproject.toml`의 `[tool.pytest.ini_options]`에 `addopts = "-m 'not integration'"`, 마커 `integration` 등록.

---

## 공통 규칙

- **결정성**: 단위 계층은 고정 시드·고정 픽스처. 벽시계 시간·네트워크 금지.
- **빠른 것 우선**: `make test`는 단위/계약/메트릭/행동(빠른 것)만. Docker 통합은 `make test-integration`.
- **CI**: 단위는 항상, 통합은 Docker 가용 러너에서. (#12에서 GitHub Actions로 구성)
- **회귀 기준선은 데이터로 갱신**: ④의 NDCG 기준선은 모델/데이터 개선 시 의도적으로만 상향.
