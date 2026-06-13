from pipelines.cli import example_popularity


def test_example_popularity_returns_ranked_items() -> None:
    rows = example_popularity()
    assert len(rows) == 3
    scores = [r["score"] for r in rows]
    assert scores == sorted(scores, reverse=True)
