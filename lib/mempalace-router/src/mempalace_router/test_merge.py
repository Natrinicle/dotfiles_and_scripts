"""Tests for search and kg_query merging."""

import copy
import unittest

from mempalace_router.merge import merge_kg_query, merge_search, valid_from_key


def _hit(text, wing, room, eff, drawer_id="d"):
    return {
        "drawer_id": drawer_id,
        "text": text,
        "wing": wing,
        "room": room,
        "effective_distance": eff,
    }


def _identity(target, wing, room):
    return wing, room


def _fact(subject, predicate, obj, valid_from, current=True, valid_to=None):
    return {
        "subject": subject,
        "predicate": predicate,
        "object": obj,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "current": current,
    }


def _kg(*facts):
    return {
        "entity": "e",
        "as_of": None,
        "active_facts": list(facts),
        "historical_facts": [],
        "future_facts": [],
        "facts": list(facts),
        "count": len(facts),
    }


class MergeSearchTest(unittest.TestCase):
    """Test merge_search."""

    def test_search_sorted_by_distance_with_target_field(self):
        by_target = {
            "local": {
                "query": "q",
                "filters": {"wing": None},
                "total_before_filter": 3,
                "results": [_hit("a", "w", "r", 0.5), _hit("b", "w", "r", 0.9)],
            },
            "acme": {
                "query": "q2",
                "filters": {"x": 1},
                "total_before_filter": 4,
                "results": [_hit("c", "w", "r", 0.2)],
            },
        }
        out = merge_search(by_target, _identity)
        self.assertEqual(out["query"], "q")
        self.assertEqual(out["filters"], {"wing": None})
        self.assertEqual(out["total_before_filter"], 7)
        self.assertEqual([h["text"] for h in out["results"]], ["c", "a", "b"])
        self.assertEqual([h["target"] for h in out["results"]], ["acme", "local", "local"])
        for hit in out["results"]:
            self.assertEqual(hit["also_in_targets"], [])

    def test_search_dedupes_same_text_wing_room(self):
        by_target = {
            "local": {"results": [_hit("same", "w", "r", 0.4)]},
            "acme": {"results": [_hit("same", "w", "r", 0.1), _hit("same", "w", "other", 0.3)]},
        }
        out = merge_search(by_target, _identity)
        self.assertEqual(len(out["results"]), 2)
        first, second = out["results"]
        self.assertEqual(first["target"], "acme")
        self.assertEqual(first["room"], "r")
        self.assertEqual(first["also_in_targets"], ["local"])
        self.assertEqual(second["room"], "other")
        self.assertEqual(second["also_in_targets"], [])

    def test_search_translates_remote_wing_to_local(self):
        def to_local(target, wing, room):
            if target == "acme":
                return "acme_" + wing, room.upper()
            return wing, room

        by_target = {
            "local": {"results": [_hit("t", "acme_ops", "R", 0.5)]},
            "acme": {"results": [_hit("t", "ops", "r", 0.6)]},
        }
        out = merge_search(by_target, to_local)
        self.assertEqual(len(out["results"]), 1)
        hit = out["results"][0]
        self.assertEqual((hit["wing"], hit["room"]), ("acme_ops", "R"))
        self.assertEqual(hit["target"], "local")
        self.assertEqual(hit["also_in_targets"], ["acme"])

    def test_search_ignores_error_target(self):
        by_target = {
            "local": {"total_before_filter": 1, "results": [_hit("a", "w", "r", 0.5)]},
            "acme": {"error": "boom"},
        }
        out = merge_search(by_target, _identity)
        self.assertEqual(len(out["results"]), 1)
        self.assertEqual(out["total_before_filter"], 1)

    def test_search_inputs_not_mutated(self):
        by_target = {
            "local": {"results": [_hit("a", "w", "r", 0.5)]},
            "acme": {"results": [_hit("a", "w", "r", 0.1)]},
        }
        before = copy.deepcopy(by_target)
        merge_search(by_target, lambda t, w, r: ("x", "y"))
        self.assertEqual(by_target, before)


class MergeKgQueryTest(unittest.TestCase):
    """Test merge_kg_query."""

    def _merge(self, local_facts, company_facts):
        by_target = {"local": _kg(*local_facts), "acme": _kg(*company_facts)}
        return merge_kg_query(by_target, company="acme", local="local", single_valued={"p"})

    def test_kg_conflict_newer_company_wins(self):
        lf = _fact("s", "p", "old", "2026-01-01")
        cf = _fact("s", "p", "new", "2026-02-01")
        merged, conflicts = self._merge([lf], [cf])
        self.assertEqual(len(conflicts), 1)
        c = conflicts[0]
        self.assertEqual(c["winner"], "company")
        self.assertEqual(c["action"], "supersede_local")
        self.assertEqual(c["local"]["object"], "old")
        self.assertEqual(c["company"]["object"], "new")
        self.assertEqual((c["subject"], c["predicate"]), ("s", "p"))
        self.assertEqual(merged["count"], 2)
        self.assertEqual({f["target"] for f in merged["facts"]}, {"local", "acme"})
        self.assertEqual(len(merged["active_facts"]), 2)
        self.assertEqual(merged["entity"], "e")

    def test_kg_conflict_newer_local_wins(self):
        lf = _fact("s", "p", "new", "2026-03-01T10:00:00")
        cf = _fact("s", "p", "old", "2026-02-01")
        _, conflicts = self._merge([lf], [cf])
        self.assertEqual(conflicts[0]["winner"], "local")
        self.assertEqual(conflicts[0]["action"], "supersede_company")

    def test_kg_tie_goes_to_company(self):
        lf = _fact("s", "p", "a", "2026-01-01")
        cf = _fact("s", "p", "b", "2026-01-01")
        _, conflicts = self._merge([lf], [cf])
        self.assertEqual(conflicts[0]["winner"], "company")
        self.assertEqual(conflicts[0]["action"], "supersede_local")

    def test_kg_multivalued_no_action(self):
        lf = [_fact("s", "p", "a", "2026-01-01"), _fact("s", "p", "b", "2026-01-02")]
        cf = [_fact("s", "p", "c", "2026-02-01")]
        _, conflicts = self._merge(lf, cf)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["action"], "none")
        self.assertEqual(conflicts[0]["winner"], "company")

    def test_kg_no_conflict_when_same_object(self):
        lf = _fact("s", "p", "same", "2026-01-01")
        cf = _fact("s", "p", "same", "2026-02-01")
        _, conflicts = self._merge([lf], [cf])
        self.assertEqual(conflicts, [])

    def test_kg_non_current_facts_ignored_and_none_company(self):
        lf = _fact("s", "p", "a", "2026-01-01", current=False, valid_to="2026-01-05")
        cf = _fact("s", "p", "b", "2026-02-01")
        _, conflicts = self._merge([lf], [cf])
        self.assertEqual(conflicts, [])
        by_target = {"local": _kg(_fact("s", "p", "a", None)), "acme": _kg(cf)}
        merged, conflicts = merge_kg_query(by_target, company=None, local="local")
        self.assertEqual(conflicts, [])
        self.assertEqual(merged["count"], 2)

    def test_kg_none_valid_from_sorts_oldest(self):
        lf = _fact("s", "p", "a", None)
        cf = _fact("s", "p", "b", "2026-01-01")
        _, conflicts = self._merge([lf], [cf])
        self.assertEqual(conflicts[0]["winner"], "company")
        _, conflicts = self._merge([cf], [lf])
        self.assertEqual(conflicts[0]["winner"], "local")

    def test_kg_inputs_not_mutated(self):
        by_target = {
            "local": _kg(_fact("s", "p", "a", "2026-01-01")),
            "acme": _kg(_fact("s", "p", "b", "2026-02-01")),
        }
        before = copy.deepcopy(by_target)
        merge_kg_query(by_target, company="acme", local="local")
        self.assertEqual(by_target, before)


class SingleValuedAndTimestampTest(unittest.TestCase):
    """Corrections only on allowlisted predicates; normalised valid_from."""

    def _merge(self, lf, cf, single_valued=frozenset({"version"})):
        by_target = {"local": _kg(lf), "acme": _kg(cf)}
        return merge_kg_query(by_target, company="acme", local="local", single_valued=single_valued)

    def test_multivalued_predicate_one_value_per_side_has_no_action(self):
        _, conflicts = self._merge(_fact("s", "has_method", "a", "2026-01-01"),
                                   _fact("s", "has_method", "b", "2026-02-01"))
        self.assertEqual((conflicts[0]["action"], conflicts[0]["winner"]), ("none", "company"))

    def test_allowlisted_predicate_supersedes(self):
        _, conflicts = self._merge(_fact("s", "version", "1", "2026-01-01"),
                                   _fact("s", "version", "2", "2026-02-01"))
        self.assertEqual(conflicts[0]["action"], "supersede_local")

    def test_default_allowlist_is_empty(self):
        by_target = {"local": _kg(_fact("s", "version", "1", "2026-01-01")),
                     "acme": _kg(_fact("s", "version", "2", "2026-02-01"))}
        _, conflicts = merge_kg_query(by_target, company="acme", local="local")
        self.assertEqual(conflicts[0]["action"], "none")

    def test_date_only_vs_midnight_datetime_ties_to_company(self):
        for local_from in ("2026-03-01T00:00:00", "2026-03-01T00:00:00Z", "2026-03-01T00:00:00+00:00"):
            _, conflicts = self._merge(_fact("s", "version", "1", local_from),
                                       _fact("s", "version", "2", "2026-03-01"))
            self.assertEqual(conflicts[0]["winner"], "company", local_from)
            self.assertEqual(conflicts[0]["action"], "supersede_local", local_from)

    def test_offsets_compared_as_instants(self):
        # 2026-03-01T01:00+02:00 is 2026-02-28T23:00Z, older than company midnight
        _, conflicts = self._merge(_fact("s", "version", "1", "2026-03-01T01:00:00+02:00"),
                                   _fact("s", "version", "2", "2026-03-01"))
        self.assertEqual(conflicts[0]["winner"], "company")
        _, conflicts = self._merge(_fact("s", "version", "1", "2026-03-01T00:00:01Z"),
                                   _fact("s", "version", "2", "2026-03-01"))
        self.assertEqual(conflicts[0]["winner"], "local")

    def test_valid_from_key_none_and_garbage_oldest(self):
        self.assertEqual(valid_from_key(None), valid_from_key("not a date"))
        self.assertLess(valid_from_key(""), valid_from_key("1970-01-01"))

if __name__ == "__main__":
    unittest.main()
