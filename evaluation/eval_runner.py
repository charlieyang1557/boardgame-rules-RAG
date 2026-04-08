"""Evaluation runner for the BoardGameOracle RAG pipeline."""

import json
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class RetrievalMetrics:
    recall_at_5: float
    keyword_hit_rate: float


@dataclass(frozen=True)
class AnswerMetrics:
    accuracy: bool
    forbidden_content_found: list[str]
    tier_correct: bool
    has_hallucination: bool


@dataclass
class EvalResult:
    query: str
    difficulty: str
    retrieval: RetrievalMetrics
    answer: AnswerMetrics
    category: str = ""


@dataclass
class EvalReport:
    results: list[EvalResult]
    overall_accuracy: float
    overall_recall_at_5: float
    tier3_rate: float
    hallucination_count: int


def load_golden_dataset(path: str) -> list[dict]:
    """Load a golden Q&A dataset from a JSON file."""
    with open(path) as f:
        return json.load(f)


def evaluate_retrieval(
    retrieved_chunks: list[dict], expected: dict
) -> RetrievalMetrics:
    """Evaluate retrieval quality against golden expected values.

    Args:
        retrieved_chunks: List of dicts with at least 'id' and 'text' keys.
        expected: Golden dataset entry with expected_chunks and
                  required_chunk_keywords.

    Returns:
        RetrievalMetrics with recall_at_5 and keyword_hit_rate.
    """
    # Recall@5: fraction of expected chunks found in top-5 retrieved chunk IDs
    expected_ids: list[str] = expected.get("expected_chunks", [])
    if expected_ids:
        top_5_ids = [c.get("id", "") for c in retrieved_chunks[:5]]
        hits = sum(1 for eid in expected_ids if eid in top_5_ids)
        recall = hits / len(expected_ids)
    else:
        # No expected chunks defined yet — default to 1.0 (not penalised)
        recall = 1.0

    # Keyword hit rate: fraction of required keywords found in any chunk text
    required_keywords: list[str] = expected.get("required_chunk_keywords", [])
    if required_keywords:
        all_text = " ".join(
            c.get("text", "").lower() for c in retrieved_chunks[:5]
        )
        kw_hits = sum(
            1 for kw in required_keywords if kw.lower() in all_text
        )
        keyword_hit_rate = kw_hits / len(required_keywords)
    else:
        keyword_hit_rate = 1.0

    return RetrievalMetrics(recall_at_5=recall, keyword_hit_rate=keyword_hit_rate)


def evaluate_answer(answer: str, tier: int, expected: dict) -> AnswerMetrics:
    """Evaluate an answer against the golden ground truth.

    Args:
        answer: The generated answer string.
        tier: The tier assigned by the pipeline (1, 2, or 3).
        expected: Golden dataset entry with ground_truth,
                  forbidden_content, and expected_tier.

    Returns:
        AnswerMetrics with accuracy, forbidden content check,
        tier correctness, and hallucination flag.
    """
    # Simple keyword overlap: check that key words from ground_truth
    # appear in the generated answer
    ground_truth: str = expected.get("ground_truth", "")
    gt_words = set(ground_truth.lower().split())
    answer_lower = answer.lower()
    answer_words = set(answer_lower.split())

    # Filter out short/common words for meaningful overlap
    meaningful_gt = {w for w in gt_words if len(w) > 3}
    if meaningful_gt:
        overlap = len(meaningful_gt & answer_words) / len(meaningful_gt)
        accuracy = overlap >= 0.3
    else:
        accuracy = True

    # Check forbidden content
    forbidden: list[str] = expected.get("forbidden_content", [])
    forbidden_found = [f for f in forbidden if f.lower() in answer_lower]

    # Tier correctness
    expected_tier: int = expected.get("expected_tier", 1)
    tier_correct = tier == expected_tier

    # Hallucination detection deferred to citation verifier
    has_hallucination = False

    return AnswerMetrics(
        accuracy=accuracy,
        forbidden_content_found=forbidden_found,
        tier_correct=tier_correct,
        has_hallucination=has_hallucination,
    )


def run_full_eval(
    pipeline_fn: Callable[[str], dict], dataset_path: str
) -> EvalReport:
    """Run the full evaluation pipeline over a golden dataset.

    Args:
        pipeline_fn: A callable that takes a query string and returns a dict
                     with keys 'answer' (str), 'tier' (int), and
                     'retrieved_chunks' (list[dict]).
        dataset_path: Path to the golden dataset JSON file.

    Returns:
        EvalReport with aggregated metrics.
    """
    dataset = load_golden_dataset(dataset_path)
    results: list[EvalResult] = []

    for entry in dataset:
        query = entry["query"]
        output = pipeline_fn(query)

        retrieval = evaluate_retrieval(output["retrieved_chunks"], entry)
        answer = evaluate_answer(output["answer"], output["tier"], entry)

        results.append(
            EvalResult(
                query=query,
                difficulty=entry.get("difficulty", "medium"),
                retrieval=retrieval,
                answer=answer,
                category=entry.get("category", ""),
            )
        )

    # Aggregate metrics
    n = len(results) if results else 1
    overall_accuracy = sum(1 for r in results if r.answer.accuracy) / n
    overall_recall = sum(r.retrieval.recall_at_5 for r in results) / n
    tier3_count = sum(1 for r in results if not r.answer.tier_correct)
    tier3_rate = tier3_count / n
    hallucination_count = sum(
        1 for r in results if r.answer.has_hallucination
    )

    return EvalReport(
        results=results,
        overall_accuracy=overall_accuracy,
        overall_recall_at_5=overall_recall,
        tier3_rate=tier3_rate,
        hallucination_count=hallucination_count,
    )


def print_report(report: EvalReport) -> None:
    """Print a human-readable evaluation report.

    Args:
        report: An EvalReport containing all evaluation results.
    """
    print("=" * 60)
    print("EVALUATION REPORT")
    print("=" * 60)
    print(f"Total queries evaluated: {len(report.results)}")
    print(f"Overall accuracy:        {report.overall_accuracy:.1%}")
    print(f"Overall recall@5:        {report.overall_recall_at_5:.1%}")
    print(f"Tier mismatch rate:      {report.tier3_rate:.1%}")
    print(f"Hallucination count:     {report.hallucination_count}")
    print()

    # Stratify by difficulty
    for difficulty in ("easy", "medium", "hard"):
        subset = [r for r in report.results if r.difficulty == difficulty]
        if not subset:
            continue
        n = len(subset)
        acc = sum(1 for r in subset if r.answer.accuracy) / n
        recall = sum(r.retrieval.recall_at_5 for r in subset) / n
        print(f"[{difficulty.upper():6s}] n={n:2d}  accuracy={acc:.1%}  recall@5={recall:.1%}")

    # Stratify by category (if any entries have categories)
    categories = sorted({r.category for r in report.results if r.category})
    if categories:
        print()
        print("Per-category breakdown:")
        for cat in categories:
            subset = [r for r in report.results if r.category == cat]
            if not subset:
                continue
            n = len(subset)
            acc = sum(1 for r in subset if r.answer.accuracy) / n
            recall = sum(r.retrieval.recall_at_5 for r in subset) / n
            print(f"  [{cat:20s}] n={n:2d}  accuracy={acc:.1%}  recall@5={recall:.1%}")

    # Print failures
    failures = [
        r
        for r in report.results
        if not r.answer.accuracy or r.answer.forbidden_content_found
    ]
    if failures:
        print()
        print(f"FAILURES ({len(failures)}):")
        print("-" * 60)
        for r in failures:
            print(f"  Q: {r.query}")
            if not r.answer.accuracy:
                print("     -> Low keyword overlap with ground truth")
            if r.answer.forbidden_content_found:
                print(
                    f"     -> Forbidden content found: "
                    f"{r.answer.forbidden_content_found}"
                )


if __name__ == "__main__":
    import sys

    path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "evaluation/golden_dataset/splendor.json"
    )
    data = load_golden_dataset(path)
    print(f"{len(data)} golden entries loaded")
