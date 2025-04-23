from django.test import TestCase
from unittest.mock import patch, MagicMock
from advisingwebsiteapp.scraptranscript import parse_transcript 

class ParseTranscriptTests(TestCase):
    @patch("advisingwebsiteapp.scraptranscript.os.path.exists", return_value=True)
    @patch("advisingwebsiteapp.scraptranscript.pdfplumber.open")
    @patch("advisingwebsiteapp.scraptranscript.LlamaParse")
    def test_parse_transcript_extraction(self, mock_llamaparse_class, mock_pdfplumber_open, mock_exists):
        mock_llamaparse = MagicMock()
        mock_llamaparse.load_data.return_value = [
            MagicMock(text="""
                Name : John Doe
                WKU ID : 800123456

                Curriculum Information
                College: Ogden
                Major and Department: [1234] Computer Science
                Minor: [5678] Mathematics
            """)
        ]
        mock_llamaparse_class.return_value = mock_llamaparse

        # Mock pdfplumber tables
        mock_page = MagicMock()
        mock_page.extract_tables.return_value = [
            [["CS", "120", "100", "Intro to CS", "A", "3.0", "12.0", ""]]
        ]
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        structured = parse_transcript("fake.pdf")

        self.assertEqual(structured["student_name"], "John Doe")
        self.assertEqual(structured["student_id"], "800123456")
        self.assertIn("Computer Science", structured["major"])
        self.assertIn("Mathematics", structured["major"])
        self.assertIn("1234", structured["degree_num"])
        self.assertIn("5678", structured["degree_num"])

        self.assertEqual(len(structured["courses"]), 1)
        course = structured["courses"][0]
        self.assertEqual(course["subject"], "CS")
        self.assertEqual(course["course_number"], "120")
        self.assertEqual(course["title"], "Intro to CS")
        self.assertEqual(course["credit_hours"], "3.0")
        self.assertEqual(course["quality_points"], "12.0")
