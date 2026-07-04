#!/usr/bin/env bash
# 로컬 개발 스택 한 방 기동: 인프라(Postgres+Kafka) → serving(마이그레이션+시드) → bronze-sink.
# Ctrl-C 로 앱 두 개를 내린다. 인프라는 남긴다(start-only 철학) — 내리려면 `make down`.
set -euo pipefail
cd "$(dirname "$0")/.."

LOG_DIR=data/logs
mkdir -p "$LOG_DIR"

SERVING_PATTERN='me.imweb.reco.serving.ServingApplication'
SINK_PATTERN='me.imweb.reco.bronzesink.BronzeSinkApplication'

cleanup() {
  echo ""
  echo "▸ 앱 종료 중... (인프라는 유지 — 내리려면 make down)"
  pkill -f "$SERVING_PATTERN" 2>/dev/null || true
  pkill -f "$SINK_PATTERN" 2>/dev/null || true
}
trap cleanup INT TERM

echo "▸ 인프라 기동 (Postgres + Kafka)"
docker compose -f infra/docker-compose.yml up -d --wait

echo "▸ serving 기동 → 로그: $LOG_DIR/serving.log (Flyway 마이그레이션 + 샘플 시드 포함)"
./gradlew :apps:serving:bootRun --console=plain > "$LOG_DIR/serving.log" 2>&1 &
SERVING_GRADLE_PID=$!

until curl -sf localhost:8080/health > /dev/null; do
  if ! kill -0 "$SERVING_GRADLE_PID" 2>/dev/null; then
    echo "✗ serving 기동 실패 — $LOG_DIR/serving.log 확인" >&2
    exit 1
  fi
  sleep 2
done
echo "  ✓ serving UP (:8080)"

echo "▸ bronze-sink 기동 → 로그: $LOG_DIR/bronze-sink.log"
./gradlew :apps:bronze-sink:bootRun --console=plain > "$LOG_DIR/bronze-sink.log" 2>&1 &
SINK_GRADLE_PID=$!

until grep -q "partitions assigned" "$LOG_DIR/bronze-sink.log" 2>/dev/null; do
  if ! kill -0 "$SINK_GRADLE_PID" 2>/dev/null; then
    echo "✗ bronze-sink 기동 실패 — $LOG_DIR/bronze-sink.log 확인" >&2
    cleanup
    exit 1
  fi
  sleep 2
done
echo "  ✓ bronze-sink UP (events 토픽 구독 중)"

echo ""
echo "전부 떴다. 확인:"
echo "  curl localhost:8080/health"
echo "  curl 'localhost:8080/api/recommendations?userId=u-000116'"
echo "  curl -X POST localhost:8080/events -H 'Content-Type: application/json' -d @data/samples/ingest_batch.sample.json"
echo ""
echo "Ctrl-C 로 앱 종료 (인프라는 유지)"
wait
