import tempfile
import unittest
from pathlib import Path

import verification


class VerificationStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_database_path = verification.DATABASE_PATH
        verification.DATABASE_PATH = Path(self.temp_dir.name) / "verification.sqlite3"
        verification.initialize()

    def tearDown(self):
        verification.DATABASE_PATH = self.original_database_path
        self.temp_dir.cleanup()

    def test_seeded_case_is_pending_and_contains_phase_questions(self):
        dashboard = verification.get_dashboard()

        self.assertEqual(len(dashboard["questions"]), 18)
        self.assertEqual(
            {question["phase"] for question in dashboard["questions"]},
            set(verification.PHASES),
        )
        self.assertEqual(dashboard["metrics"]["questions_tested"], 0)
        self.assertEqual(dashboard["metrics"]["expert_approval"], "Pending")
        self.assertTrue(
            all(not question["reference_approved"] for question in dashboard["questions"])
        )

    def test_case_signoff_requires_completed_clinician_reviews(self):
        dashboard = verification.get_dashboard()
        with self.assertRaisesRegex(ValueError, "every question"):
            verification.sign_off(verification.CASE_ID, "Reviewer", True)

        for question in dashboard["questions"]:
            run_id = verification.save_run(
                question["question_id"],
                "Captured test response",
            )
            verification.save_assessment(
                question_id=question["question_id"],
                run_id=run_id,
                status="pass",
                reviewer_name="Reviewer",
                comments="Reviewed",
                harmful_error=False,
                reference_answer="Clinician-entered test reference.",
                source_notes="Test source citation.",
                reference_approved=True,
            )

        verification.sign_off(verification.CASE_ID, "Reviewer", True)
        signed_dashboard = verification.get_dashboard()
        self.assertEqual(signed_dashboard["metrics"]["cases_reviewed"], 1)
        self.assertEqual(signed_dashboard["metrics"]["questions_reviewed"], 18)

    def test_approved_reference_requires_answer_and_citation(self):
        question = verification.get_dashboard()["questions"][0]
        run_id = verification.save_run(question["question_id"], "Captured answer")

        with self.assertRaisesRegex(ValueError, "clinician-written answer"):
            verification.save_assessment(
                question_id=question["question_id"],
                run_id=run_id,
                status="needs_expert_review",
                reviewer_name="Reviewer",
                comments="",
                harmful_error=False,
                reference_answer="",
                source_notes="",
                reference_approved=True,
            )

    def test_csv_report_includes_saved_response_and_review(self):
        question = verification.get_dashboard()["questions"][0]
        run_id = verification.save_run(question["question_id"], "Captured AI response")
        verification.save_assessment(
            question_id=question["question_id"],
            run_id=run_id,
            status="fail",
            reviewer_name="Reviewer",
            comments="Needs correction",
            harmful_error=True,
            reference_answer="Clinician reference",
            source_notes="Source title, section 1",
            reference_approved=False,
        )

        report = verification.export_csv()
        self.assertIn("latest_ai_response", report)
        self.assertIn("Captured AI response", report)
        self.assertIn("Needs correction", report)
        self.assertIn("appendicitis-appendectomy-pilot", report)


if __name__ == "__main__":
    unittest.main()
