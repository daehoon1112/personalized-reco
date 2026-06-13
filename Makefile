# personalized-reco — 루트 태스크 러너 (Kotlin/Gradle + Python/uv 통합)
# JVM은 Gradle Wrapper, Python은 uv로 위임한다.

# JDK 21 LTS 고정 (macOS java_home으로 탐색). 다른 경로면 `make build JAVA_HOME=...`로 덮어쓰기.
JAVA_HOME ?= $(shell /usr/libexec/java_home -v 21 2>/dev/null)
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
test: ## 전체 테스트 (Gradle + pytest)
	$(GRADLE) test
	$(UV) run pytest -q

.PHONY: run-serving
run-serving: ## Kotlin 서빙 앱 실행 (예시 API, :8080)
	$(GRADLE) :apps:serving:bootRun

.PHONY: lint
lint: ## 린트 (ruff)
	$(UV) run ruff check .

# --- 아래는 후속 이슈에서 채워질 자리표시자 ---
.PHONY: up migrate codegen seed consume label batch eval
up:      ## (#3) docker-compose 기동 (Postgres + Kafka)
	@echo "TODO(#3): docker compose up"
migrate: ## (#5) Flyway 마이그레이션
	@echo "TODO(#5): flyway migrate"
codegen: ## (#4) protobuf 코드젠 (buf)
	@echo "TODO(#4): buf generate"
seed:    ## (#9) 합성 이벤트 → Kafka produce
	@echo "TODO(#9): seed synthetic events"
consume: ## (#13) Kafka 컨슈머 → bronze 적재
	@echo "TODO(#13): consume to bronze"
label:   ## (#14) silver 세션화/라벨링
	@echo "TODO(#14): build silver labels"
batch:   ## (#10) gold 인기순 배치
	@echo "TODO(#10): popularity batch"
eval:    ## (#11) 오프라인 평가
	@echo "TODO(#11): offline eval"
