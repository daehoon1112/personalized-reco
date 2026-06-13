"""환경 설정 (스캐폴딩). 실제 사용은 후속 이슈에서 확장."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = "postgresql://reco:reco@localhost:5432/reco"
    kafka_bootstrap: str = "localhost:9092"


def load_settings() -> Settings:
    return Settings(
        database_url=os.environ.get("DATABASE_URL", Settings.database_url),
        kafka_bootstrap=os.environ.get("KAFKA_BOOTSTRAP", Settings.kafka_bootstrap),
    )
