import csv
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, Client
from django.urls import reverse
from advisingwebsiteapp.models import Chat, ChatMember, Message, Degree, UserDegree, Course, Prerequisites, DegreeCourse
from django.contrib import auth
from unittest.mock import patch, MagicMock
import io

from advisingwebsiteapp.views import download_recommendations, process_and_recommend_courses

User = get_user_model()

"""
Runs a test on every single view in the website and confirms that they are functioning as intended.
Will show failures if a template doesn't load, a link does not work, or if the page opened was not
the one that was intended to be loaded.

ChatGPT was used to help facilitate the creation of views testing
https://chatgpt.com/share/67f47ab8-d7a0-800c-baea-6a808dfb69c2
"""

class TestHomeView(TestCase):
    def setUp(self):
        self.url = reverse('home')

    def test_home_view(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')

class TestLoginView(TestCase):
    def setUp(self):
        self.login_url = reverse('login')
        self.home_url = reverse('home')
        self.user = User.objects.create_user(email='test@example.com', password='testpassword123')

    def test_login_view_get(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_login_view_post_valid_credentials(self):
        response = self.client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'testpassword123',
        })
        self.assertRedirects(response, self.home_url)

        user = auth.get_user(self.client)
        self.assertTrue(user.is_authenticated)

    def test_login_view_post_invalid_credentials(self):
        response = self.client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid email or password")
        user = auth.get_user(self.client)
        self.assertFalse(user.is_authenticated)

class TestRegisterView(TestCase):
    def setUp(self):
        self.register_url = reverse('register')
        self.degree = Degree.objects.create(
            degree_name='Computer Science',
            degree_number='123',
            concentration='General',
            hours_needed = 120,
            degree_type = 1
        )

    def test_register_view_get(self):
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register.html')
        self.assertIn('grouped_degrees', response.context)

    def test_register_successful_post(self):
        response = self.client.post(self.register_url, {
            'first_name': 'Alice',
            'last_name': 'Smith',
            'email': 'alice@example.com',
            'password': 'StrongPass1!',
            'student_id': '123456789',
            'degrees[]': [str(self.degree.id)],
        })

        self.assertRedirects(response, reverse('home'))
        user_exists = User.objects.filter(email='alice@example.com').exists()
        self.assertTrue(user_exists)

        # Check that the user-degree relationship was created
        user = User.objects.get(email='alice@example.com')
        self.assertTrue(UserDegree.objects.filter(user_student_id=user, degree=self.degree).exists())

    def test_register_duplicate_email(self):
        User.objects.create_user(email='bob@example.com', password='TestPass1!', student_id='987654321')
        response = self.client.post(self.register_url, {
            'first_name': 'Bob',
            'last_name': 'Jones',
            'email': 'bob@example.com',
            'password': 'AnotherPass1!',
            'student_id': '123456789',
        })
        self.assertRedirects(response, self.register_url)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("already registered" in str(m) for m in messages))

    def test_register_duplicate_student_id(self):
        User.objects.create_user(email='bob@example.com', password='TestPass1!', student_id='123456789')
        response = self.client.post(self.register_url, {
            'first_name': 'Charlie',
            'last_name': 'Brown',
            'email': 'charlie@example.com',
            'password': 'StrongPass1!',
            'student_id': '123456789',
        })
        self.assertRedirects(response, self.register_url)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("student id is already registered" in str(m) for m in messages))

    def test_register_invalid_password(self):
        response = self.client.post(self.register_url, {
            'first_name': 'Dave',
            'last_name': 'Lee',
            'email': 'dave@example.com',
            'password': 'weakpass',
            'student_id': '111222333',
        })
        self.assertRedirects(response, self.register_url)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("Password must be at least 9 characters long" in str(m) for m in messages))

class UploadTranscriptViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="student@example.com", password="TestPass123!", student_id="123456789")
        self.client.login(email="student@example.com", password="TestPass123!")
        self.url = reverse("upload_transcript")

    def test_get_upload_transcript(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "uploadTranscript.html")

    def test_post_without_file(self):
        response = self.client.post(self.url, data={"term": "fall", "inputCreditHours": "15"})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "uploadTranscript.html")

    @patch("advisingwebsiteapp.views.process_and_recommend_courses")
    def test_post_with_valid_file_and_recommendations(self, mock_process):
        mock_results = {
            "transcript_data": {"courses": []},
            "major_requirements": {"requirements": []},
            "recommendations": [
                MagicMock(course_name="CS 101", hours=3),
                MagicMock(course_name="MATH 123", hours=3)
            ],
        }
        mock_process.return_value = mock_results

        fake_file = io.BytesIO(b"Fake PDF content")
        fake_file.name = "transcript.pdf"

        response = self.client.post(self.url, {
            "pdfFile": fake_file,
            "term": "fall",
            "inputCreditHours": "15"
        }, format="multipart")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "recommendedClasses.html")
        self.assertIn("recommendations", response.context)
        self.assertIn("CS 101", [rec.course_name for rec in response.context["recommendations"]])
        self.assertIn("recommendations", self.client.session)

    @patch("advisingwebsiteapp.views.process_and_recommend_courses", side_effect=AttributeError)
    def test_post_attribute_error(self, mock_process):
        fake_file = io.BytesIO(b"Fake PDF content")
        fake_file.name = "transcript.pdf"

        response = self.client.post(self.url, {
            "pdfFile": fake_file,
            "term": "spring",
            "inputCreditHours": "12"
        }, format="multipart")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "uploadTranscript.html")
        self.assertContains(response, "Student ID not found in user profile.")

class ProcessAndRecommendCoursesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="TestPass123!",
            student_id="123456789"
        )
        self.file_path = "fake_path/transcript.pdf"
        self.selected_term = "fall"
        self.max_hours = 15

    @patch("advisingwebsiteapp.views.extract_major_requirements")
    @patch("advisingwebsiteapp.views.recommend_schedule")
    @patch("advisingwebsiteapp.views.store_user_degree")
    @patch("advisingwebsiteapp.views.parse_transcript")
    def test_process_and_recommend_courses(self, mock_parse, mock_store, mock_recommend, mock_requirements):
        # Setup mock returns
        mock_parse.return_value = {"courses": ["CS 101", "MATH 123"]}
        mock_requirements.return_value = {"required": ["CS 200", "MATH 200"]}
        mock_recommend.return_value = [
            MagicMock(course_name="CS 200", hours=3),
            MagicMock(course_name="MATH 200", hours=3)
        ]

        result = process_and_recommend_courses(
            self.user,
            self.file_path,
            self.selected_term,
            self.max_hours
        )

        # Assertions
        mock_parse.assert_called_once_with(self.file_path)
        mock_store.assert_called_once_with(mock_parse.return_value)
        mock_recommend.assert_called_once_with(
            self.user,
            mock_parse.return_value,
            selected_term=self.selected_term,
            max_hours=self.max_hours
        )
        mock_requirements.assert_called_once_with(self.user.student_id)

        self.assertIn("transcript_data", result)
        self.assertIn("major_requirements", result)
        self.assertIn("recommendations", result)

        self.assertEqual(result["transcript_data"], mock_parse.return_value)
        self.assertEqual(result["major_requirements"], mock_requirements.return_value)
        self.assertEqual(result["recommendations"], mock_recommend.return_value)

class DownloadRecommendationsTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.session_data = [
            {'course_name': 'CS 101', 'hours': 3},
            {'course_name': 'MATH 200', 'hours': 4},
        ]

    def test_download_recommendations_creates_csv(self):
        # Create a request and set session data
        request = self.factory.get('/download-recommendations')
        request.session = {'recommendations': self.session_data}

        # Call the view
        response = download_recommendations(request)

        # Check response status and headers
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="recommendations.csv"')

        # Decode and parse the CSV
        content = response.content.decode('utf-8')
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        # Check headers
        self.assertEqual(rows[0], ['Course Name', 'Credit Hours'])

        # Check course data
        self.assertEqual(rows[1], ['CS 101', '3'])
        self.assertEqual(rows[2], ['MATH 200', '4'])