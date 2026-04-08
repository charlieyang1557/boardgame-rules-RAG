"""Tests for evaluation/eval_runner.py — per-category reporting."""

from evaluation.eval_runner import (
    AnswerMetrics,
    EvalReport,
    EvalResult,
    RetrievalMetrics,
    print_report,
)


def _make_result(
    query: str = "q",
    difficulty: str = "easy",
    category: str = "",
    accuracy: bool = True,
    recall: float = 1.0,
) -> EvalResult:
    return EvalResult(
        query=query,
        difficulty=difficulty,
        retrieval=RetrievalMetrics(recall_at_5=recall, keyword_hit_rate=1.0),
        answer=AnswerMetrics(
            accuracy=accuracy,
            forbidden_content_found=[],
            tier_correct=True,
            has_hallucination=False,
        ),
        category=category,
    )


class TestEvalResultCategory:
    def test_default_category_is_empty(self) -> None:
        r = _make_result()
        assert r.category == ""

    def test_category_accepted(self) -> None:
        r = _make_result(category="locations")
        assert r.category == "locations"


class TestPerCategoryReport:
    def test_report_with_categories(self, capsys) -> None:
        results = [
            _make_result(category="locations", accuracy=True, recall=0.8),
            _make_result(category="locations", accuracy=False, recall=0.6),
            _make_result(category="barrels", accuracy=True, recall=1.0),
        ]
        report = EvalReport(
            results=results,
            overall_accuracy=2 / 3,
            overall_recall_at_5=0.8,
            tier3_rate=0.0,
            hallucination_count=0,
        )
        print_report(report)
        out = capsys.readouterr().out

        assert "Per-category breakdown:" in out
        assert "barrels" in out
        assert "locations" in out
        # locations: 1/2 accuracy = 50%, recall avg = 0.7
        assert "50.0%" in out
        # barrels: 1/1 accuracy = 100%, recall = 1.0
        assert "100.0%" in out

    def test_report_without_categories_skips_section(self, capsys) -> None:
        results = [_make_result()]
        report = EvalReport(
            results=results,
            overall_accuracy=1.0,
            overall_recall_at_5=1.0,
            tier3_rate=0.0,
            hallucination_count=0,
        )
        print_report(report)
        out = capsys.readouterr().out
        assert "Per-category breakdown:" not in out
