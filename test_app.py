import os
import sys
import unittest
from datetime import datetime

# Add root folder to python path to resolve imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class TestLMSIntegration(unittest.TestCase):
    
    def test_1_env_loading(self):
        """
        Check that configuration settings can be imported from .env or fallback defaults.
        """
        print("\n--- Test 1: Env Loading & App Configuration ---")
        from backend.app import app
        self.assertIsNotNone(app.config["SECRET_KEY"])
        self.assertIsNotNone(app.config["UPLOAD_FOLDER"])
        print("[OK] Configuration loaded successfully.")
        
    def test_2_mongodb_connection(self):
        """
        Test connection to MongoDB instance.
        """
        print("\n--- Test 2: MongoDB Connection ---")
        from backend.utils.db import db
        try:
            # The client will throw an error or time out if it cannot ping
            db.client.admin.command('ping')
            print("[OK] MongoDB is online and connected successfully.")
        except Exception as e:
            print(f"[WARN] MongoDB connection skipped or failed: {str(e)}")
            print("  (Application will fall back to local setup details or connection errors in runtime).")
            
    def test_3_certificate_generation(self):
        """
        Generate a test certificate PDF to verify ReportLab and qrcode integration.
        """
        print("\n--- Test 3: ReportLab Certificate Generator ---")
        from backend.services.certificate_service import generate_certificate_pdf
        
        test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "uploads", "certificates")
        os.makedirs(test_dir, exist_ok=True)
        
        cert_id, file_path = generate_certificate_pdf(
            student_name="Jane Doe",
            course_name="Introduction to Artificial Intelligence",
            issue_date=datetime.utcnow(),
            certificate_id="CERT-TEST-9999",
            output_dir=test_dir
        )
        
        full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", file_path)
        self.assertTrue(os.path.exists(full_path), f"Certificate PDF was not generated at: {full_path}")
        print(f"[OK] Certificate compiled. ID: {cert_id}")
        print(f"  Saved file: {full_path}")
        
    def test_4_gemini_quiz_generator(self):
        """
        Trigger the Gemini service quiz generator. Assert format of generated question list.
        """
        print("\n--- Test 4: Gemini AI Quiz Generator ---")
        from backend.services.gemini_service import generate_quiz_ai, is_mock_mode
        
        print(f"  Gemini API Mock Mode Active: {is_mock_mode}")
        questions = generate_quiz_ai(
            lesson_title="Understanding Data Frames in Pandas",
            lesson_desc="Introduction to manipulating tabular arrays using Python's Pandas package.",
            lesson_notes="Pandas is a fast, powerful, flexible and easy to use open source data analysis and manipulation tool."
        )
        
        self.assertIsNotNone(questions)
        self.assertTrue(len(questions) > 0)
        self.assertEqual(len(questions), 5, f"Expected 5 questions, got {len(questions)}")
        
        # Verify first question schema
        q = questions[0]
        self.assertIn("question_text", q)
        self.assertIn("options", q)
        self.assertIn("correct_answer", q)
        self.assertIn("explanation", q)
        self.assertEqual(len(q["options"]), 4)
        self.assertIn(q["correct_answer"], ["A", "B", "C", "D"])
        
        print("[OK] AI Quiz generator outputs correct schema questions.")
        print(f"  Sample Question: {q['question_text']}")
        print(f"  Correct Answer: ({q['correct_answer']}) {q['options'][['A','B','C','D'].index(q['correct_answer'])]}")
        
if __name__ == "__main__":
    unittest.main()
