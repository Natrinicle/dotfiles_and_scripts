"""Tests for the SQLite write ledger and offline outbox."""

import tempfile
import unittest
from pathlib import Path

from mempalace_router.ledger import Ledger, Outbox


class LedgerBase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "router.db"
        self.ledger = Ledger(self.path)
        self.addCleanup(self.ledger.close)
        self.outbox = Outbox(self.path)
        self.addCleanup(self.outbox.close)


class LedgerTests(LedgerBase):
    def test_record_and_lookup_by_each_ref(self):
        rid = self.ledger.record(
            call_id="c1",
            target="company",
            tool="add_drawer",
            local_ref="L1",
            remote_ref="R1",
            payload={"a": 1},
            mine_job_id="M1",
        )
        self.assertIsInstance(rid, int)
        for ref in ("c1", "M1", "L1", "R1"):
            rows = self.ledger.lookup(ref)
            self.assertEqual(len(rows), 1, ref)
            self.assertEqual(rows[0]["id"], rid)
            self.assertEqual(rows[0]["payload"], {"a": 1})
            self.assertEqual(rows[0]["target"], "company")
        self.assertEqual(self.ledger.lookup("nope"), [])

    def test_forget_removes_rows(self):
        a = self.ledger.record(
            call_id="c1", target="t", tool="x", local_ref="l", remote_ref="r", payload={}
        )
        b = self.ledger.record(
            call_id="c2", target="t", tool="x", local_ref="l2", remote_ref="r2", payload={}
        )
        self.ledger.forget([a])
        self.assertEqual(self.ledger.lookup("c1"), [])
        self.assertEqual(len(self.ledger.lookup("c2")), 1)
        self.ledger.forget([])
        self.ledger.forget([b])
        self.assertEqual(self.ledger.lookup("c2"), [])

    def test_wal_mode_enabled(self):
        mode = self.ledger._conn.execute("PRAGMA journal_mode").fetchone()[0]
        self.assertEqual(mode.lower(), "wal")
        mode = self.outbox._conn.execute("PRAGMA journal_mode").fetchone()[0]
        self.assertEqual(mode.lower(), "wal")


class OutboxTests(LedgerBase):
    def _enqueue(self, n, target="company", tool="add_drawer"):
        return self.outbox.enqueue(
            target=target,
            tool=tool,
            arguments={"n": n},
            local_ref=f"L{n}",
            call_id=f"c{n}",
        )

    def test_enqueue_pending_order_fifo(self):
        ids = [self._enqueue(i) for i in range(3)]
        self._enqueue(9, target="other")
        rows = self.outbox.pending("company")
        self.assertEqual([r["id"] for r in rows], ids)
        self.assertEqual([r["arguments"]["n"] for r in rows], [0, 1, 2])
        self.assertEqual(rows[0]["attempts"], 0)
        self.assertIsNone(rows[0]["last_error"])
        self.assertEqual(len(self.outbox.pending("other")), 1)

    def test_drain_pushes_in_order_and_clears(self):
        for i in range(3):
            self._enqueue(i)
        seen = []

        def send(tool, args):
            seen.append((tool, args["n"]))
            return {"success": True, "drawer_id": f"D{args['n']}"}

        result = self.outbox.drain("company", send)
        self.assertEqual(
            result, {"pushed": 3, "skipped_stale": 0, "failed": 0, "errors": []}
        )
        self.assertEqual(seen, [("add_drawer", 0), ("add_drawer", 1), ("add_drawer", 2)])
        self.assertEqual(self.outbox.pending("company"), [])

    def test_on_pushed_receives_row_and_result(self):
        self._enqueue(1)
        calls = []
        self.outbox.drain(
            "company",
            lambda tool, args: {"success": True, "drawer_id": "D1"},
            on_pushed=lambda row, res: calls.append((row, res)),
        )
        self.assertEqual(len(calls), 1)
        row, res = calls[0]
        self.assertEqual(row["call_id"], "c1")
        self.assertEqual(row["local_ref"], "L1")
        self.assertEqual(row["arguments"], {"n": 1})
        self.assertEqual(res["drawer_id"], "D1")
        # row is gone from the outbox once pushed
        self.assertEqual(self.outbox.pending("company"), [])

    def test_drain_stops_on_transport_error_keeps_rest(self):
        for i in range(3):
            self._enqueue(i)
        seen = []

        def send(tool, args):
            seen.append(args["n"])
            if args["n"] == 1:
                raise ConnectionError("boom")
            return {"success": True}

        result = self.outbox.drain("company", send)
        self.assertEqual(result["pushed"], 1)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["skipped_stale"], 0)
        self.assertEqual(result["errors"], ["boom"])
        self.assertEqual(seen, [0, 1])  # stopped; row 2 never attempted
        rows = self.outbox.pending("company")
        self.assertEqual([r["arguments"]["n"] for r in rows], [1, 2])
        self.assertEqual(rows[0]["attempts"], 1)
        self.assertEqual(rows[0]["last_error"], "boom")
        self.assertEqual(rows[1]["attempts"], 0)

    def test_drain_skips_stale_supersede(self):
        self._enqueue(0, tool="kg_supersede")
        self._enqueue(1, tool="kg_supersede")
        self._enqueue(2, tool="kg_supersede")
        replies = {
            0: {"success": False, "error": "Fact is Not Current"},
            1: {"success": False, "error": "No current fact for subject"},
            2: {"success": True},
        }
        result = self.outbox.drain("company", lambda t, a: replies[a["n"]])
        self.assertEqual(
            result, {"pushed": 1, "skipped_stale": 2, "failed": 0, "errors": []}
        )
        self.assertEqual(self.outbox.pending("company"), [])

    def test_other_logical_rejection_stops_drain(self):
        self._enqueue(0)
        self._enqueue(1)
        result = self.outbox.drain(
            "company", lambda t, a: {"success": False, "error": "bad wing"}
        )
        self.assertEqual(result["pushed"], 0)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["errors"], ["bad wing"])
        rows = self.outbox.pending("company")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["attempts"], 1)
        self.assertEqual(rows[0]["last_error"], "bad wing")


if __name__ == "__main__":
    unittest.main()
