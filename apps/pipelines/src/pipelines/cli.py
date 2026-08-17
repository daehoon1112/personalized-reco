"""파이프라인 CLI (스캐폴딩). Kafka 컨슈머는 apps/bronze-sink(Kotlin)로 이동했다.

서브커맨드 디스패치는 if/elif 대신 argparse `set_defaults(handler=...)` —
핸들러 함수를 값으로 파서에 매달아두고(1급 시민), main은 꺼내서 호출만 한다.
실제 로직(silver 라벨링 #14, gold 인기순 #10, 평가 #11)은 후속 이슈에서 구현한다.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from py_common import banner
from py_common.config import load_settings


def example_popularity() -> list[dict[str, object]]:
    """예시 인기순 추천. TODO(#10): bronze events_raw 집계로 대체."""
    return [
        {"item_id": "item-1", "score": 0.92},
        {"item_id": "item-2", "score": 0.81},
        {"item_id": "item-3", "score": 0.77},
    ]


def _run_hello(_: argparse.Namespace) -> None:
    print(banner())


def _run_example_popularity(_: argparse.Namespace) -> None:
    for row in example_popularity():
        print(f"{row['item_id']}\t{row['score']}")


def _run_seed(args: argparse.Namespace) -> None:
    """합성 트래픽 시뮬레이터 (#9) — 생성 후 POST /events 전송(또는 --dry-run으로 JSONL 출력)."""
    from pipelines import ingest_client, simulator  # 무거운 import는 서브커맨드 안으로

    config = simulator.SimConfig(
        n_events=args.events,
        n_users=args.users,
        n_items=args.items,
        window_days=args.days,
        seed=args.seed,
    )

    exposure = None
    if args.from_api:
        import httpx

        api_client = httpx.Client(base_url=args.serving_url, timeout=10.0)

        def exposure(user_id: str, _k: int) -> list[str]:
            return ingest_client.fetch_recommended_items(
                args.serving_url, user_id, client=api_client
            )

    events = simulator.generate_events(config, exposure_source=exposure)

    if args.dry_run:
        for event in events:
            print(json.dumps(event, ensure_ascii=False))
        return

    report = ingest_client.post_events(events, args.serving_url, batch_size=args.batch_size)
    from collections import Counter

    counts = Counter(e["eventType"] for e in events)
    print(
        f"전송 완료: {report.sent}건 / {report.batches}배치 (재시도 {report.retried})"
        f" → {args.serving_url}/events",
        file=sys.stderr,
    )
    print(f"타입 분포: {dict(counts)}", file=sys.stderr)


def _run_label(_: argparse.Namespace) -> None:
    """silver 라벨링 (#14) — bronze 전량을 읽어 impression_label에 upsert."""
    import psycopg  # 무거운 import는 서브커맨드 안으로

    from pipelines.label import run_label

    with psycopg.connect(load_settings().database_url) as conn:
        report = run_label(conn)
    print(f"labeled: {report.labeled} rows")
    if report.has_losses:
        # 라벨 수가 조용히 줄어드는 것을 막는다 — 손실은 항상 눈에 보이게.
        print(
            f"손실: bronze 스킵 {report.skipped_bronze}건 · 조인키 누락 {report.skipped_impression}건"
            f" · 적재 실패 {report.failed}건",
            file=sys.stderr,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reco-pipelines",
        description="personalized-reco 파이프라인 (스캐폴딩)",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("hello", help="환경/워크스페이스 점검").set_defaults(handler=_run_hello)
    sub.add_parser("example-popularity", help="예시 인기순 추천 출력").set_defaults(
        handler=_run_example_popularity
    )
    sub.add_parser("label", help="silver 세션화/라벨링 (#14)").set_defaults(handler=_run_label)

    seed = sub.add_parser("seed", help="합성 트래픽 생성 → POST /events 전송 (#9)")
    seed.add_argument("--events", type=int, default=1000, help="생성할 이벤트 수")
    seed.add_argument("--users", type=int, default=200, help="가상 유저 수")
    seed.add_argument("--items", type=int, default=300, help="카탈로그 아이템 수")
    seed.add_argument("--days", type=int, default=7, help="백데이트 윈도(일)")
    seed.add_argument(
        "--seed", type=int, default=20260705,
        help="난수 시드 — 같은 시드 재전송은 bronze 멱등성으로 전부 중복 처리(추가 0건)",
    )
    seed.add_argument("--batch-size", type=int, default=200, help="전송 배치 크기")
    seed.add_argument(
        "--serving-url",
        default=load_settings().serving_url,
        help="수집 API 베이스 URL (env SERVING_URL)",
    )
    seed.add_argument(
        "--from-api",
        action="store_true",
        help="노출을 카탈로그 대신 추천 API(GET /api/recommendations)에서 구성",
    )
    seed.add_argument(
        "--dry-run", action="store_true", help="전송 없이 JSONL을 stdout으로 출력"
    )
    seed.set_defaults(handler=_run_seed)

    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = build_parser().parse_args()
    handler = getattr(args, "handler", _run_hello)  # 서브커맨드 없으면 hello
    handler(args)


if __name__ == "__main__":
    main()
