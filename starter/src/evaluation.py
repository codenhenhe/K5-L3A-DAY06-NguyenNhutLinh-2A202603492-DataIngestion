"""Score exact evidence matches and preserve per-query traces."""
from typing import Any


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    """Require a complete quote on a gold page, accepting any listed alternative."""
    gold = [question, *question.get("alternate_evidence", [])]
    for hit in hits:
        metadata = hit["metadata"]
        hit["evidence_hit"] = any(
            metadata["document_id"] == entry["gold_source_id"]
            and metadata["page"] == entry["gold_page"]
            and entry["evidence_quote"] in hit["text"]
            for entry in gold
        )
    return {
        **question,
        "hits": hits,
        "hit_at_1": bool(hits and hits[0]["evidence_hit"]),
        "evidence_hit_at_3": any(hit["evidence_hit"] for hit in hits[:3]),
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "questions": len(traces),
        "hit_at_1": sum(trace["hit_at_1"] for trace in traces),
        "evidence_hit_at_3": sum(trace["evidence_hit_at_3"] for trace in traces),
    }
