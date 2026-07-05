# personalized-reco — 루트 태스크 러너 (Kotlin/Gradle + Python/uv 통합)
# JVM은 Gradle Wrapper, Python은 uv로 위임한다.

# JDK 25 (macOS java_home으로 탐색). 다른 경로면 `make build JAVA_HOME=...`로 덮어쓰기.
JAVA_HOME ?= $(shell /usr/libexec/java_home -v 25 2>/dev/null)
export JAVA_HOME
GRADLE := ./gradlew
UV := uv

.DEFAULT_GOAL := help

.PHONY: help
help: ## 사용 가능한 타깃 출력
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

.PHONY: build
build: build-kotlin build-python ## 전체 빌드 (Kotlin + Python)

.PHONY: build-kotlin
build-kotlin: ## Kotlin(Gradle) 빌드 + 테스트
	$(GRADLE) build

.PHONY: build-python
build-python: ## Python(uv) 워크스페이스 동기화
	$(UV) sync

.PHONY: test
test: ## 단위/계약/메트릭/행동 테스트 (빠름, Docker 불필요)
	$(GRADLE) test
	$(UV) run pytest -q

.PHONY: test-integration
test-integration: ## 통합/E2E 테스트 (Testcontainers, Docker 필요)
	$(GRADLE) integrationTest
	$(UV) run pytest -m integration -v

.PHONY: bootstrap
bootstrap: ## 로컬 툴체인 보장 (JDK 25 · uv · Python 3.12 없으면 설치)
	./scripts/ensure-toolchain.sh

.PHONY: dev
dev: bootstrap ## 전체 스택 한 방 기동: 툴체인 확인 + 인프라 + serving + bronze-sink (Ctrl-C로 앱 종료)
	./scripts/dev-up.sh

.PHONY: run-serving
run-serving: ## Kotlin 서빙 앱 실행 (예시 API, :8080)
	$(GRADLE) :apps:serving:bootRun

.PHONY: ui
ui: ## 데모 스토어프론트 dev 서버 (:5173 → :8080 프록시, 백엔드는 make dev 먼저)
	cd apps/web && npm install --silent && npm run dev

.PHONY: lint
lint: ## 린트 (ruff)
	$(UV) run ruff check .

COMPOSE := docker compose -f infra/docker-compose.yml

.PHONY: up down consume
up:      ## 인프라 기동 (Postgres + Kafka, 헬시까지 대기)
	$(COMPOSE) up -d --wait

down:    ## 인프라 종료
	$(COMPOSE) down

consume: ## (#13) bronze-sink(Kotlin) — Kafka → bronze 적재 (무한 실행, Ctrl-C로 종료)
	$(GRADLE) :apps:bronze-sink:bootRun

.PHONY: migrate
migrate: ## (#5) Flyway 마이그레이션 (Postgres 필요: make up 먼저)
	$(GRADLE) :apps:serving:flywayMigrate

# --- 아래는 후속 이슈에서 채워질 자리표시자 ---
.PHONY: codegen seed label batch eval
codegen: ## (#4) protobuf 코드젠 (buf)
	@echo "TODO(#4): buf generate"
seed:    ## (#9) 합성 이벤트 → Kafka produce
	@echo "TODO(#9): seed synthetic events"
label:   ## (#14) silver 세션화/라벨링
	@echo "TODO(#14): build silver labels"
batch:   ## (#10) gold 인기순 배치
	@echo "TODO(#10): popularity batch"
eval:    ## (#11) 오프라인 평가
	@echo "TODO(#11): offline eval"
