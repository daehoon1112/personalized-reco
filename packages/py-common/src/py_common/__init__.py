"""personalized-reco 공유 라이브러리 (스캐폴딩)."""

from py_common.config import Settings, load_settings

__all__ = ["Settings", "load_settings", "banner"]


def banner() -> str:
    return "personalized-reco · py-common OK (스캐폴딩)"
