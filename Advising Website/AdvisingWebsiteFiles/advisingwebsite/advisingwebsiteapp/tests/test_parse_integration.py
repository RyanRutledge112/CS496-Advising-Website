from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from unittest.mock import patch, MagicMock
from io import BytesIO
from advisingwebsiteapp.models import Course, Degree, UserDegree
import time

User = get_user_model()

class TranscriptUploadIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="student@example.com",
            password="testpass123",
            student_id="800123456",
            first_name="John",       
            last_name="Doe",             
            is_student=True,
            is_advisor=False
        )
        self.client.force_login(self.user)

    @patch("advisingwebsiteapp.views.parse_transcript")
    @patch("advisingwebsiteapp.views.extract_major_requirements")
    @patch("advisingwebsiteapp.views.recommend_schedule")
    def test_transcript_upload_and_parsing_flow(
        self, mock_recommend_schedule, mock_extract_major_requirements, mock_parse_transcript
    ):
        mock_parse_transcript.return_value = {
            "student_name": "John Doe",
            "student_id": "800123456",
            "major": ["Computer Science"],
            "degree_num": ["629"],
            "courses": [
                {"course_name": "CS 180", "grade": "A", "credit_hours": "3.0", "quality_points": "12.0"}
            ]
        }

        mock_extract_major_requirements.return_value = {
            "courses": [],
            "instructions": [],
            "instructional_rules": []
        }

        mock_recommend_schedule.return_value = {
            "recommendations": [MagicMock(course_name="CS 290", hours="3")],
            "credit_hours": 15,
            "recommendation_reasons": [{"course": "CS 290", "reason": "Degree core/elective requirement"}],
            "notice": ""
        }

        fake_pdf = BytesIO(b"%PDF-1.4 fake content")
        fake_pdf.name = "transcript.pdf"

        start = time.time()
        response = self.client.post(
            reverse("uploadTranscript"), 
            {
                "pdfFile": fake_pdf,
                "inputCreditHours": "15",
                "term": "fall"
            },
            format="multipart"
        )

        end = time.time() 
        elapsed = end - start

        self.assertLess(elapsed, 10.0, "Response time exceeded 10 seconds")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "recommendedClasses.html")

        self.assertIn("transcript_data", response.context)
        self.assertIn("major_requirements", response.context)
        self.assertIn("recommendations", response.context)
        self.assertIn("recommendation_reasons", response.context)
        self.assertEqual(response.context["credit_hours"], 15)
        self.assertEqual(response.context["selected_term"], "fall")

        session_recs = self.client.session.get("recommendations", [])
        self.assertEqual(len(session_recs), 1)
        self.assertEqual(session_recs[0]["course_name"], "CS 290")

    @patch("advisingwebsiteapp.views.parse_transcript")
    @patch("advisingwebsiteapp.views.extract_major_requirements")
    @patch("advisingwebsiteapp.views.recommend_schedule")
    def test_schedule_recommendation_logic(
        self, mock_recommend_schedule, mock_extract_major_requirements, mock_parse_transcript
    ):
        mock_parse_transcript.return_value = {
            "student_name": "Jane Doe",
            "student_id": "800123456",
            "major": ["Computer Science"],
            "degree_num": ["629"],
            "courses": [
                {"course_name": "CS 180", "grade": "A", "credit_hours": "3.0"},
                {"course_name": "ENG 100", "grade": "B", "credit_hours": "3.0"}
            ]
        }

        mock_extract_major_requirements.return_value = {
            "courses": [],  
            "instructions": [],
            "instructional_rules": []
        }

        mock_recommend_schedule.return_value = {
            "recommendations": [
                MagicMock(course_name="CS 290", hours="3"), 
                MagicMock(course_name="MATH 136", hours="3"),
                MagicMock(course_name="ENG 200", hours="3"),
                MagicMock(course_name="CS 301", hours="3"),
                MagicMock(course_name="CS 270", hours="3") 
            ],
            "credit_hours": 15,
            "recommendation_reasons": [
                {"course": "CS 290", "reason": "Degree core/elective requirement"},
                {"course": "MATH 136", "reason": "Degree core/elective requirement"},
                {"course": "ENG 300", "reason": "Colonade: W2"},
                {"course": "CS 301", "reason": "Degree core/elective requirement"},
                {"course": "CS 270", "reason": "Degree core/elective requirement"}
            ],
            "notice": ""
        }

        fake_pdf = BytesIO(b"%PDF-1.4 fake content")
        fake_pdf.name = "transcript.pdf"

        response = self.client.post(
            reverse("uploadTranscript"),
            {
                "pdfFile": fake_pdf,
                "inputCreditHours": "6",
                "term": "fall"
            },
            format="multipart"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "recommendedClasses.html")
        self.assertEqual(len(response.context["recommendations"]), 5)

        course_names = [rec["course_name"] for rec in response.context["recommendations"]]
        self.assertIn("CS 290", course_names)
        self.assertIn("MATH 136", course_names)
        self.assertIn("ENG 200", course_names)
        self.assertIn("CS 301", course_names)
        self.assertIn("CS 270", course_names)

        total_hours = sum(float(rec["hours"]) for rec in response.context["recommendations"])
        self.assertLessEqual(total_hours, 15)
    
    @patch("advisingwebsiteapp.views.parse_transcript")
    @patch("advisingwebsiteapp.views.extract_major_requirements")
    @patch("advisingwebsiteapp.views.recommend_schedule")
    def test_data_inserted_to_database_correctly(
        self, mock_recommend_schedule, mock_extract_major_requirements, mock_parse_transcript
    ):
        mock_parse_transcript.return_value = {
            "student_name": "John Doe",
            "student_id": "800123456",
            "major": ["Computer Science"],
            "degree_num": ["629"],
            "courses": [
                {"course_name": "CS 180", "grade": "A", "credit_hours": "3.0"}
            ]
        }

        mock_extract_major_requirements.return_value = {
            "courses": [],
            "instructions": [],
            "instructional_rules": []
        }

        mock_recommend_schedule.return_value = {
            "recommendations": [],
            "credit_hours": 15,
            "recommendation_reasons": [],
            "notice": ""
        }

        Degree.objects.create(
            degree_name="Computer Science",
            degree_number="629",
            concentration="General",
            hours_needed=120,
            degree_type=1
        )

        Course.objects.create(
            course_name="CS 180",
            hours=3.0,
            is_colonade=False,
            colonade_id=""
        )

        fake_pdf = BytesIO(b"%PDF-1.4 test content")
        fake_pdf.name = "transcript.pdf"

        response = self.client.post(
            reverse("uploadTranscript"),
            {
                "pdfFile": fake_pdf,
                "inputCreditHours": "15",
                "term": "fall"
            },
            format="multipart"
        )

        user_degrees = UserDegree.objects.filter(user_student_id=self.user)
        self.assertEqual(user_degrees.count(), 1)
        self.assertEqual(user_degrees.first().degree.degree_number, "629")
        self.assertTrue(Degree.objects.filter(degree_number="629").exists())
        self.assertTrue(Course.objects.filter(course_name="CS 180").exists())
