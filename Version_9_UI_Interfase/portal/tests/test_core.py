import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config
import database
import lifecycle
import compliance
import audit


class SunhavenCoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        config.DB_PATH = Path(self.tmp.name) / "test.db"
        lifecycle.graph.mode = "mock"
        database.init_db(reset=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_seed_contains_required_roles(self):
        conn = database.connect()
        roles = {r["approved_role"] for r in conn.execute("SELECT DISTINCT approved_role FROM employees")}
        conn.close()
        self.assertTrue({"CareWorker","Nurse","Manager","AgencyWorker","Auditor","IAMOperator"}.issubset(roles))

    def test_agency_requires_sponsor_and_end_date(self):
        data = {
            "employee_id":"SC2001","name":"Test Agency","email":"agency@test.local",
            "worker_type":"Agency","approved_role":"AgencyWorker","facility":"Ashford Main",
            "status":"Active","manager_sponsor":"","start_date":"2026-09-01","end_date":""
        }
        with self.assertRaises(lifecycle.ValidationError):
            lifecycle.dry_run_joiner(data)

    def test_joiner_creates_role_and_audit(self):
        data = {
            "employee_id":"SC2002","name":"Test Nurse","email":"nurse@test.local",
            "worker_type":"Permanent","approved_role":"Nurse","facility":"Ashford Main",
            "status":"Active","manager_sponsor":"SC1002","start_date":"2026-09-18","end_date":""
        }
        state, corr = lifecycle.joiner(data, "SC1005")
        self.assertEqual(state["approved_role"], "Nurse")
        self.assertIn("Nurse", state["actual_roles"])
        self.assertTrue(corr.startswith("JNR-"))
        conn = database.connect()
        event = conn.execute("SELECT * FROM audit_events WHERE correlation_id=?", (corr,)).fetchone()
        conn.close()
        self.assertEqual(event["result"], "PASS")

    def test_mover_removes_old_role_before_new_state(self):
        state, _ = lifecycle.mover("SC1001", "Manager", "North Wing", "SC1005")
        self.assertEqual(state["approved_role"], "Manager")
        self.assertEqual(state["actual_roles"], ["Manager"])
        self.assertEqual(state["facility"], "North Wing")
        self.assertEqual(state["active_assignments"], [])

    def test_leaver_removes_access_and_blocks(self):
        state, _ = lifecycle.leaver("SC1003", "SC1005")
        self.assertEqual(state["status"], "Leaver")
        self.assertEqual(state["cloud_enabled"], 0)
        self.assertEqual(state["actual_roles"], [])
        self.assertEqual(state["active_assignments"], [])
        self.assertTrue(state["blocked"])

    def test_compliance_detects_seeded_expired_agency(self):
        findings = compliance.run_checks(store=False)
        pairs = {(f["employee_id"], f["rule_id"]) for f in findings}
        self.assertIn(("SC1006", "C02"), pairs)

    def test_audit_redacts_secret_fields(self):
        corr = audit.record("SC1005", "SC1001", "TEST_SECRET_REDACTION", "PASS", {
            "password":"dont-store-me","token":"dont-store-me","normal":"visible"
        })
        conn = database.connect(); row = conn.execute("SELECT details FROM audit_events WHERE correlation_id=?", (corr,)).fetchone(); conn.close()
        self.assertIn("[REDACTED]", row["details"])
        self.assertNotIn("dont-store-me", row["details"])
        self.assertIn("visible", row["details"])


if __name__ == "__main__":
    unittest.main()
