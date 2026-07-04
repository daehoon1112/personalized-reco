-- Bronze: 받은 그대로의 불변 이벤트 (append-only).
-- 컨벤션(셀러업 DB 가이드) 도입 이전 테이블 — 컨슈머(#13 consumer.py)와 기존 볼륨 호환을 위해
-- infra/postgres/init/01_bronze.sql 스키마를 그대로 이관 (IF NOT EXISTS: 기존 볼륨에서 무해 통과).
-- 컨벤션 정렬(리네임 등)은 후속 이슈에서.

CREATE TABLE IF NOT EXISTS events_raw (
    id           BIGSERIAL   PRIMARY KEY,
    event_id     TEXT        NOT NULL UNIQUE,
    event_type   TEXT        NOT NULL,
    user_id      TEXT,
    item_id      TEXT,
    session_id   TEXT,
    position     INTEGER,
    consent      BOOLEAN,
    event_ts     TIMESTAMPTZ NOT NULL,
    ingested_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload      JSONB       NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_raw_event_ts ON events_raw (event_ts);
CREATE INDEX IF NOT EXISTS idx_events_raw_type ON events_raw (event_type);
CREATE INDEX IF NOT EXISTS idx_events_raw_user ON events_raw (user_id);

COMMENT ON TABLE events_raw IS '브론즈원본이벤트(컨벤션이전테이블)';
