import tempfile
import unittest
from pathlib import Path

import yaml

from mempalace_router.taxonomy import TaxonomyError, TaxonomyMap, canonical


class CanonicalTests(unittest.TestCase):
    def test_canonical_k8s_matches_kubernetes(self):
        self.assertEqual(canonical("kubernetes"), canonical("k8s"))
        self.assertEqual(canonical("K8S"), "kubernetes")

    def test_canonical_examples(self):
        self.assertEqual(canonical("wing_K8S"), "kubernetes")
        self.assertEqual(canonical("Postgres-Notes"), "postgres_note")
        self.assertEqual(canonical("plans"), "plan")
        self.assertEqual(canonical("PostgreSQL"), "postgres")
        self.assertEqual(canonical("postgres"), "postgres")


class TaxonomyMapTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state = Path(self._tmp.name)

    def make(self):
        return TaxonomyMap("company", self.state)

    def test_k8s_maps_to_remote_kubernetes(self):
        m = self.make()
        remote = {"kubernetes": {"runbooks": 3}}
        self.assertEqual(
            m.to_remote("K8S", "runbook", remote), ("kubernetes", "runbooks", True)
        )

    def test_explicit_alias_wins_over_heuristic(self):
        m = self.make()
        m.wings["k8s"] = "ops"
        remote = {"kubernetes": {}, "ops": {}}
        rw, _, created = m.to_remote("k8s", "x", remote)
        self.assertEqual(rw, "ops")
        self.assertTrue(created)  # room identity alias is new

    def test_unknown_remote_uses_local_name_and_records_identity_alias(self):
        m = self.make()
        rw, rr, created = m.to_remote("solar", "bms", {"other": {}})
        self.assertEqual((rw, rr, created), ("solar", "bms", True))
        self.assertEqual(m.wings["solar"], "solar")
        self.assertEqual(m.rooms["solar"]["bms"], "bms")
        self.assertFalse(m.to_remote("solar", "bms", {"other": {}})[2])

    def test_round_trip_to_local(self):
        m = self.make()
        remote = {"kubernetes": {"runbooks": 1}}
        rw, rr, _ = m.to_remote("K8S", "runbook", remote)
        self.assertEqual(m.to_local(rw, rr), ("K8S", "runbook"))
        self.assertEqual(m.to_local("unknown", "thing"), ("unknown", "thing"))

    def test_no_implicit_many_to_one(self):
        m = self.make()
        remote = {"kubernetes": {"notes": 1}}
        self.assertEqual(m.to_remote("k8s", "note", remote)[:2], ("kubernetes", "notes"))
        # kube also canonicalizes to kubernetes, but k8s already owns it.
        rw, rr, _ = m.to_remote("kube", "note", remote)
        self.assertEqual(rw, "kube")
        # same invariant for rooms within one wing
        r = {"w": {"postgresql": 1}}
        self.assertEqual(m.to_remote("w", "pg", r)[:2], ("w", "postgresql"))
        self.assertEqual(m.to_remote("w", "postgres", r)[:2], ("w", "postgres"))

    def test_explicit_alias_may_be_many_to_one(self):
        m = self.make()
        m.wings.update({"a": "shared", "b": "shared"})
        self.assertEqual(m.to_remote("a", "r", {"shared": {}})[0], "shared")
        self.assertEqual(m.to_remote("b", "r", {"shared": {}})[0], "shared")

    def test_save_load_yaml_roundtrip(self):
        m = self.make()
        m.to_remote("K8S", "runbook", {"kubernetes": {"runbooks": 1}})
        m.save()
        path = self.state / "taxonomy" / "company.yaml"
        data = yaml.safe_load(path.read_text())
        self.assertEqual(data["wings"], {"K8S": "kubernetes"})
        self.assertEqual(data["rooms"], {"K8S": {"runbook": "runbooks"}})
        m2 = self.make()
        m2.load()
        self.assertEqual(m2.wings, m.wings)
        self.assertEqual(m2.rooms, m.rooms)

    def test_save_is_atomic_no_tmp_left_behind(self):
        m = self.make()
        m.to_remote("solar", "bms", {})
        m.save()
        self.assertEqual(
            [p.name for p in (self.state / "taxonomy").iterdir()], ["company.yaml"]
        )
        m2 = self.make()
        m2.load()
        self.assertEqual(m2.wings, m.wings)

    def _write(self, text):
        path = self.state / "taxonomy" / "company.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def test_load_malformed_yaml_raises_taxonomy_error(self):
        self._write("wings: {a: [unclosed\n")
        with self.assertRaises(TaxonomyError) as cm:
            self.make().load()
        self.assertIn("company.yaml", str(cm.exception))

    def test_load_wrong_shape_raises_taxonomy_error(self):
        for text in ("- a\n- b\n", "wings: [x]\n", "wings: {}\nrooms: {w: [x]}\n"):
            self._write(text)
            with self.assertRaises(TaxonomyError):
                self.make().load()

    def test_load_missing_file_is_empty(self):
        m = self.make()
        m.load()
        self.assertEqual((m.wings, m.rooms), ({}, {}))

    def test_to_remote_autosaves_when_alias_created(self):
        m = self.make()
        m.to_remote("solar", "bms", {})
        m2 = self.make()
        m2.load()
        self.assertEqual(m2.wings, {"solar": "solar"})


if __name__ == "__main__":
    unittest.main()
