"""Blind, held-out review annotations compared with published visit-mode scores."""
from collections import defaultdict
import hashlib
import re

from src.scoring.verify import DIMS


def fingerprint(text):
    normalized = re.sub(r"\s+", " ", text or "").strip().casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest() if normalized else None


def validate_annotations(rows, catalog, used_reviews=()):
    """One row per independent review. Blank dimension values mean unmentioned.

    used_reviews: iterable of (source, review_id, text) already exposed to judge.
    """
    used_ids = {(source.casefold(), str(review_id)) for source, review_id, _ in used_reviews}
    used_text = {fingerprint(text) for _, _, text in used_reviews if fingerprint(text)}
    seen = set()
    grouped = defaultdict(list)
    excluded = []
    for row in rows:
        place_id, mode_id = row["place_id"], row["mode"]
        if place_id not in catalog or mode_id not in catalog[place_id]["modes"]:
            raise ValueError(f"Unknown place or mode: {place_id}/{mode_id}")
        source, review_id = row["source"].strip().casefold(), str(row["review_id"]).strip()
        if not source or not review_id or not row.get("source_url") or not row.get("review_text"):
            raise ValueError("source, review_id, source_url, and review_text required")
        key = (source, review_id)
        if key in seen:
            raise ValueError(f"Duplicate review: {key}")
        seen.add(key)
        if key in used_ids or fingerprint(row["review_text"]) in used_text:
            excluded.append({"place_id": place_id, "source": source, "review_id": review_id,
                             "reason": "used in scoring"})
            continue
        for dim in DIMS:
            label = row.get(dim)
            if label in (None, ""):
                continue
            try:
                label = int(label)
            except (TypeError, ValueError):
                raise ValueError(f"Invalid {dim} label: {label}") from None
            if not 1 <= label <= 10:
                raise ValueError(f"Invalid {dim} label: {label}")
            prediction = catalog[place_id]["modes"][mode_id]["dimensions"][dim]["score"]
            grouped[(place_id, mode_id, dim)].append({"review_id": review_id, "source": source,
                                                       "source_url": row["source_url"],
                                                       "human": label, "scoring_ai": prediction,
                                                       "difference": prediction - label})
    results = []
    for (place_id, mode_id, dim), items in sorted(grouped.items()):
        n = len(items)
        results.append({"place_id": place_id, "mode": mode_id, "dimension": dim,
                        "n": n, "within_1": sum(abs(x["difference"]) <= 1 for x in items),
                        "mean_absolute_error": round(sum(abs(x["difference"]) for x in items) / n, 2),
                        "evidence": items, "status": "reviewable" if n >= 3 else "insufficient"})
    return {"comparisons": results, "excluded": excluded,
            "note": "Review labels describe observed route conditions; not a 50+ traveler validation."}
