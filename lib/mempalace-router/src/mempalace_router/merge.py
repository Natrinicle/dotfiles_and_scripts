"""Pure merge logic for fan-out search and kg_query results."""

from typing import Callable


def merge_search(
    by_target: dict[str, dict],
    to_local: Callable[[str, str, str], tuple[str, str]],
) -> dict:
    """Merge decoded ``mempalace_search`` results from several targets.

    Args:
        by_target: Decoded search results keyed by target name, local first.
        to_local: Callable ``(target, wing, room) -> (local_wing, local_room)``.

    Returns:
        Merged search dict. Hits gain ``target`` and ``also_in_targets``,
        are deduped on ``(text, wing, room)`` keeping the lowest
        ``effective_distance``, and are sorted by that distance ascending.
    """
    merged: dict = {}
    total = 0
    kept: dict[tuple, dict] = {}
    order: list[tuple] = []
    seen_in: dict[tuple, list[str]] = {}
    first = True

    for target, result in by_target.items():
        if not isinstance(result, dict) or not isinstance(result.get("results"), list):
            continue
        if first:
            merged["query"] = result.get("query")
            merged["filters"] = result.get("filters")
            first = False
        total += result.get("total_before_filter") or 0
        for raw in result["results"]:
            hit = dict(raw)
            wing, room = to_local(target, hit.get("wing"), hit.get("room"))
            hit["wing"], hit["room"] = wing, room
            hit["target"] = target
            key = (hit.get("text"), wing, room)
            seen_in.setdefault(key, [])
            current = kept.get(key)
            if current is None:
                kept[key] = hit
                order.append(key)
            elif _distance(hit) < _distance(current):
                seen_in[key].append(current["target"])
                kept[key] = hit
            else:
                seen_in[key].append(target)

    hits = []
    for key in order:
        hit = kept[key]
        hit["also_in_targets"] = [t for t in seen_in[key] if t != hit["target"]]
        hits.append(hit)
    hits.sort(key=_distance)

    merged["total_before_filter"] = total
    merged["results"] = hits
    return merged


def _distance(hit: dict) -> float:
    """Return a hit's effective distance, treating missing as worst."""
    value = hit.get("effective_distance")
    return float("inf") if value is None else value


def _is_current(fact: dict) -> bool:
    """Return whether a fact is currently valid."""
    if "current" in fact:
        return bool(fact["current"])
    return fact.get("valid_to") is None


def merge_kg_query(
    by_target: dict[str, dict],
    *,
    company: str | None,
    local: str,
) -> tuple[dict, list[dict]]:
    """Merge decoded ``mempalace_kg_query`` results and detect conflicts.

    Args:
        by_target: Decoded kg_query results keyed by target name.
        company: Name of the company target, or None for no conflict check.
        local: Name of the local target.

    Returns:
        ``(merged, conflicts)``. Each conflict is ``{subject, predicate, local,
        company, winner, action}``.
    """
    merged: dict = {
        "entity": None,
        "as_of": None,
        "active_facts": [],
        "historical_facts": [],
        "future_facts": [],
        "facts": [],
    }
    local_result = by_target.get(local)
    if isinstance(local_result, dict):
        merged["entity"] = local_result.get("entity")
        merged["as_of"] = local_result.get("as_of")

    for target, result in by_target.items():
        if not isinstance(result, dict):
            continue
        if merged["entity"] is None:
            merged["entity"] = result.get("entity")
        for field in ("active_facts", "historical_facts", "future_facts", "facts"):
            for fact in result.get(field) or []:
                merged[field].append({**fact, "target": target})
    merged["count"] = len(merged["facts"])

    conflicts: list[dict] = []
    if company is not None:
        conflicts = _detect_conflicts(by_target.get(local), by_target.get(company))
    return merged, conflicts


def _current_by_key(result: object) -> dict[tuple, list[dict]]:
    """Group a kg_query result's current facts by (subject, predicate)."""
    groups: dict[tuple, list[dict]] = {}
    if not isinstance(result, dict):
        return groups
    for fact in result.get("facts") or []:
        if _is_current(fact):
            groups.setdefault((fact.get("subject"), fact.get("predicate")), []).append(fact)
    return groups


def _detect_conflicts(local_result: object, company_result: object) -> list[dict]:
    """Find differing current objects between local and company facts."""
    local_groups = _current_by_key(local_result)
    company_groups = _current_by_key(company_result)
    conflicts = []
    for key, local_facts in local_groups.items():
        company_facts = company_groups.get(key)
        if not company_facts:
            continue
        local_objects = {f.get("object") for f in local_facts}
        company_objects = {f.get("object") for f in company_facts}
        if local_objects == company_objects:
            continue
        multi = len(local_facts) > 1 or len(company_facts) > 1
        local_fact = max(local_facts, key=lambda f: f.get("valid_from") or "")
        company_fact = max(company_facts, key=lambda f: f.get("valid_from") or "")
        local_from = local_fact.get("valid_from") or ""
        company_from = company_fact.get("valid_from") or ""
        winner = "local" if local_from > company_from else "company"
        if multi:
            action = "none"
        else:
            action = "supersede_local" if winner == "company" else "supersede_company"
        conflicts.append(
            {
                "subject": key[0],
                "predicate": key[1],
                "local": local_fact,
                "company": company_fact,
                "winner": winner,
                "action": action,
            }
        )
    return conflicts
