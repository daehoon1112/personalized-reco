"""① 결정적 단위 테스트 — 같은 seed·설정이면 완전히 동일한 이벤트 시퀀스."""

from datetime import datetime, timezone

from pipelines.simulator import SimConfig, generate_events

FIXED_END = datetime(2026, 7, 4, 0, 0, 0, tzinfo=timezone.utc)


def test_same_seed_same_events() -> None:
    config = SimConfig(n_events=300, seed=42, end_ts=FIXED_END)
    assert generate_events(config) == generate_events(config)


def test_different_seed_different_events() -> None:
    a = generate_events(SimConfig(n_events=300, seed=1, end_ts=FIXED_END))
    b = generate_events(SimConfig(n_events=300, seed=2, end_ts=FIXED_END))
    assert a != b


def test_event_count_exact() -> None:
    events = generate_events(SimConfig(n_events=137, end_ts=FIXED_END))
    assert len(events) == 137


def test_backdated_within_window() -> None:
    config = SimConfig(n_events=200, window_days=7, end_ts=FIXED_END)
    for event in generate_events(config):
        ts = datetime.fromisoformat(event["ts"].replace("Z", "+00:00"))
        assert ts <= FIXED_END
        assert (FIXED_END - ts).days <= 7
