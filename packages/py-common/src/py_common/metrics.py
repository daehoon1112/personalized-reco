"""랭킹 평가 지표 (binary relevance). 평가 파이프라인(#11)이 재사용한다.

손으로 답을 검증할 수 있게 의도적으로 단순/명시적으로 구현한다.
지표가 틀리면 모델 평가 전체가 거짓말이 되므로 테스트(test_metrics.py)로 못 박는다.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence


def precision_at_k(recommended: Sequence[str], relevant: Iterable[str], k: int) -> float:
    """top-k 중 정답 비율. 분모는 k."""
    if k <= 0:
        return 0.0
    rel = set(relevant)
    topk = recommended[:k]
    hits = sum(1 for item in topk if item in rel)
    return hits / k


def recall_at_k(recommended: Sequence[str], relevant: Iterable[str], k: int) -> float:
    """정답 중 top-k에 들어온 비율. 분모는 정답 개수."""
    rel = set(relevant)
    if not rel:
        return 0.0
    topk = recommended[:k]
    hits = sum(1 for item in topk if item in rel)
    return hits / len(rel)


def dcg_at_k(recommended: Sequence[str], relevant: Iterable[str], k: int) -> float:
    """Discounted Cumulative Gain (binary gain)."""
    rel = set(relevant)
    return sum(
        (1.0 if item in rel else 0.0) / math.log2(idx + 2)
        for idx, item in enumerate(recommended[:k])
    )


def ndcg_at_k(recommended: Sequence[str], relevant: Iterable[str], k: int) -> float:
    """Normalized DCG. 이상적 정렬(정답을 앞에) 대비 비율. 0~1."""
    rel = set(relevant)
    dcg = dcg_at_k(recommended, rel, k)
    ideal_hits = min(len(rel), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    return dcg / idcg if idcg > 0 else 0.0
