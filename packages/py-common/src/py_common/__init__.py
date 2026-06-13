"""personalized-reco 공유 라이브러리 (스캐폴딩)."""

from py_common.config import Settings, load_settings
from py_common.metrics import dcg_at_k, ndcg_at_k, precision_at_k, recall_at_k

__all__ = [
    "Settings",
    "load_settings",
    "banner",
    "precision_at_k",
    "recall_at_k",
    "dcg_at_k",
    "ndcg_at_k",
]


def banner() -> str:
    return "personalized-reco · py-common OK (스캐폴딩)"
