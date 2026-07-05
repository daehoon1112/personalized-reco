"""파이프라인 CLI (스캐폴딩). Kafka 컨슈머는 apps/bronze-sink(Kotlin)로 이동했다.

서브커맨드 디스패치는 if/elif 대신 argparse `set_defaults(handler=...)` —
핸들러 함수를 값으로 파서에 매달아두고(1급 시민), main은 꺼내서 호출만 한다.
실제 로직(silver 라벨링 #14, gold 인기순 #10, 평가 #11)은 후속 이슈에서 구현한다.
"""

from __future__ import annotations

import argparse
import logging

from py_common import banner


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

    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = build_parser().parse_args()
    handler = getattr(args, "handler", _run_hello)  # 서브커맨드 없으면 hello
    handler(args)


if __name__ == "__main__":
    main()
