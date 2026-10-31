import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import store
import verification


class AppIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        store.DATABASE_PATH = Path(cls.tmp.name) / "app.sqlite3"
        verification.DATABASE_PATH = Path(cls.tmp.name) / "verification.sqlite3"
        import main

        cls.client = TestClient(main.app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        cls.tmp.cleanup()

    def register(self, name):
        r = self.client.post("/auth/register", json={"username": name, "password": "password123", "full_name": "Dr " + name})
        self.assertEqual(r.status_code, 200, r.text)
        return {"Authorization": f"Bearer {r.json()['token']}"}

    def test_cases_are_private_and_verification_is_admin_only(self):
        a, b = self.register("surgeona"), self.register("surgeonb")
        created = self.client.post("/cases", headers=a, json={
            "patient_label": "A.K.", "procedure_id": "appendectomy",
            "procedure_name": "Appendectomy", "intake": {"age": "30"}, "notes": "",
        })
        self.assertEqual(created.status_code, 200, created.text)
        case_id = created.json()["case_id"]
        self.assertEqual(self.client.get(f"/cases/{case_id}", headers=a).status_code, 200)
        self.assertEqual(self.client.get(f"/cases/{case_id}", headers=b).status_code, 404)
        self.assertEqual(self.client.get("/cases", headers=b).json(), [])
        self.assertEqual(self.client.get("/verification", headers=a).status_code, 403)
        self.assertEqual(self.client.get("/verification").status_code, 401)

        with store._connect() as connection:
            raw = connection.execute("SELECT payload FROM patient_cases").fetchone()[0]
        self.assertNotIn(b"A.K.", raw if isinstance(raw, bytes) else raw.encode())

    def test_post_surgery_falls_back_to_protocol_without_ai(self):
        a = self.register("surgeonc")
        case_id = self.client.post("/cases", headers=a, json={
            "patient_label": "B", "procedure_id": "appendectomy",
            "procedure_name": "Appendectomy", "intake": {}, "notes": "",
        }).json()["case_id"]
        r = self.client.post(f"/cases/{case_id}/post-surgery", headers=a, json={"current_status": ""})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn(r.json()["mode"], {"ai", "protocol_only"})

    def test_five_verification_cases(self):
        self.assertEqual(len(verification_cases()), 5)

    def test_own_security_summary_and_admin_self_check(self):
        a = self.register("surgeond")
        self.client.post("/cases", headers=a, json={
            "patient_label": "C.D.", "procedure_id": "appendectomy",
            "procedure_name": "Appendectomy", "intake": {}, "notes": "",
        })
        summary = self.client.get("/me/security", headers=a).json()
        self.assertEqual(summary["case_count"], 1)
        self.assertEqual(summary["cases_readable_in_storage"], 0)
        self.assertEqual(self.client.post("/admin/nfr/self-check", headers=a).status_code, 403)
        import nfr
        import main
        result = nfr.run_self_checks(main.rate_limit, main.SECURITY_HEADERS, main.allowed_origins)
        failed = [c for c in result["checks"] if c["status"] == "failed"]
        self.assertEqual(failed, [])


def verification_cases():
    from verification_data import CASES
    return CASES


if __name__ == "__main__":
    unittest.main()
