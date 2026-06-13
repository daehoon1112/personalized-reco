"""파이프라인 CLI (스캐폴딩 + 컨슈머 진입점).

실제 로직(silver 라벨링 #14, gold 인기순 #10, 평가 #11)은 후속 이슈에서 구현한다.
"""

from __future__ import annotations

import argparse

from py_common import banner


def example_popularity() -> list[dict[str, object]]:
    """예시 인기순 추천. TODO(#10): bronze events_raw 집계로 대체."""
    return [
        {"item_id": "item-1", "score": 0.92},
        {"item_id": "item-2", "score": 0.81},
        {"item_id": "item-3", "score": 0.77},
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="reco-pipelines",
        description="personalized-reco 파이프라인 (스캐폴딩)",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("hello", help="환경/워크스페이스 점검")
    sub.add_parser("example-popularity", help="예시 인기순 추천 출력")
    consume_p = sub.add_parser("consume", help="Kafka → Bronze 적재 (#13)")
    consume_p.add_argument("--idle-timeout", type=float, default=0.0)
    args = parser.parse_args()

    if args.command == "example-popularity":
        for row in example_popularity():
            print(f"{row['item_id']}\t{row['score']}")
    elif args.command == "consume":
        from pipelines.consumer import run_consumer

        run_consumer(idle_timeout=args.idle_timeout)
    else:
        print(banner())


if __name__ == "__main__":
    main()
