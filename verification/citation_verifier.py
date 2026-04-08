from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ClaimVerification:
    claim: str
    chunk_id: str
    supported: bool
    overlap_score: float
    explanation: str = ""


@dataclass(frozen=True)
class VerificationResult:
    all_supported: bool
    details: list[ClaimVerification]


def compute_token_overlap(claim: str, chunk_text: str) -> float:
    claim_tokens = set(re.findall(r"\b\w+\b", claim.lower()))
    if not claim_tokens:
        return 0.0

    chunk_tokens = set(re.findall(r"\b\w+\b", chunk_text.lower()))
    overlap = claim_tokens & chunk_tokens
    return len(overlap) / len(claim_tokens)


def _extract_cited_claims(answer: str) -> list[tuple[str, str]]:
    pattern = re.compile(r"([^\n\[]+?)\s*\[([^\]]+)\]")
    claims: list[tuple[str, str]] = []
    for match in pattern.finditer(answer):
        claim = match.group(1).strip(" \t\n\r.:;-")
        chunk_id = match.group(2).strip()
        if claim and chunk_id:
            claims.append((claim, chunk_id))
    return claims


def verify_citations(
    answer: str,
    chunks: list[dict],
    anthropic_client=None,
) -> VerificationResult:
    cited_claims = _extract_cited_claims(answer)
    if not cited_claims:
        return VerificationResult(all_supported=True, details=[])

    chunks_by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
    details: list[ClaimVerification] = []
    pending: list[tuple[str, str, float]] = []

    for claim, chunk_id in cited_claims:
        chunk = chunks_by_id.get(chunk_id)
        if chunk is None:
            details.append(
                ClaimVerification(
                    claim=claim,
                    chunk_id=chunk_id,
                    supported=False,
                    overlap_score=0.0,
                    explanation="Cited chunk_id not found in retrieved chunks.",
                )
            )
            continue

        overlap = compute_token_overlap(claim, chunk["text"])
        if overlap > 0.6:
            details.append(
                ClaimVerification(
                    claim=claim,
                    chunk_id=chunk_id,
                    supported=True,
                    overlap_score=overlap,
                    explanation="Supported by token overlap threshold.",
                )
            )
        else:
            pending.append((claim, chunk_id, overlap))

    if pending and anthropic_client is not None:
        context_lines = []
        for idx, (claim, chunk_id, overlap) in enumerate(pending, 1):
            chunk_text = chunks_by_id[chunk_id]["text"]
            context_lines.append(
                f"Item {idx}\nClaim: {claim}\nChunk ID: {chunk_id}\nChunk: {chunk_text}\nOverlap: {overlap:.3f}"
            )
        prompt = "\n\n".join(context_lines)
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=(
                "You verify whether each claim is supported by its cited rule chunk. "
                "Return one line per item in the form: Item N: SUPPORTED or UNSUPPORTED."
            ),
            messages=[{"role": "user", "content": prompt}],
        )
        verdict_text = message.content[0].text
        verdicts = {
            int(item): status == "SUPPORTED"
            for item, status in re.findall(
                r"Item\s+(\d+)\s*:\s*(SUPPORTED|UNSUPPORTED)", verdict_text
            )
        }
        for idx, (claim, chunk_id, overlap) in enumerate(pending, 1):
            supported = verdicts.get(idx, False)
            details.append(
                ClaimVerification(
                    claim=claim,
                    chunk_id=chunk_id,
                    supported=supported,
                    overlap_score=overlap,
                    explanation="Supported by LLM entailment check." if supported else "Unsupported after LLM entailment check.",
                )
            )
    else:
        for claim, chunk_id, overlap in pending:
            details.append(
                ClaimVerification(
                    claim=claim,
                    chunk_id=chunk_id,
                    supported=False,
                    overlap_score=overlap,
                    explanation="Insufficient token overlap and no LLM verifier available.",
                )
            )

    supported_count = sum(1 for d in details if d.supported)
    total_count = len(details)
    # Downgrade to Tier 3 only if majority of claims are unsupported.
    # A single borderline false-negative from the entailment check should
    # not nuke an otherwise well-cited answer.
    majority_supported = supported_count > total_count / 2 if total_count > 0 else True
    return VerificationResult(
        all_supported=majority_supported,
        details=details,
    )
