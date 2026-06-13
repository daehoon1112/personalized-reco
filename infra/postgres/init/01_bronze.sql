-- Bronze: 받은 그대로의 불변 이벤트 (append-only).
-- NOTE: 임시 초기화 스크립트. #5에서 Flyway가 스키마 소유권을 가져가면 이 파일은 제거된다.

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
