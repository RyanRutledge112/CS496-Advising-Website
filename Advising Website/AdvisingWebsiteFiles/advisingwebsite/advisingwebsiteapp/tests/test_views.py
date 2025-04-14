import csv
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, Client
from django.urls import reverse
from advisingwebsiteapp.models import Chat, ChatMember, Message, Degree, UserDegree
from django.contrib import auth
from unittest.mock import patch, MagicMock
import io
from django.http import JsonResponse
from django.contrib.auth import authenticate
from django.utils import timezone

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
        self.user = User.objects.create_user(
            email="user@example.com",
            first_name="John",
            last_name="Doe",
            password="securepass!",
            is_student=True,
            is_advisor=False,
            student_id=100001
        )

    def test_login_view_get(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_login_view_post_valid_credentials(self):
        response = self.client.post(self.login_url, {
            'email': 'user@example.com',
            'password': 'securepass!',
        })
        self.assertRedirects(response, self.home_url)

        user = auth.get_user(self.client)
        self.assertTrue(user.is_authenticated)

    def test_login_view_post_invalid_credentials(self):
        response = self.client.post(self.login_url, {
            'email': 'user@example.com',
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
            'student_id': 123456789,
            'degrees[]': [str(self.degree.id)],
        })

        self.assertRedirects(response, reverse('home'))
        user_exists = User.objects.filter(email='alice@example.com').exists()
        self.assertTrue(user_exists)

        # Check that the user-degree relationship was created
        user = User.objects.get(email='alice@example.com')
        self.assertTrue(UserDegree.objects.filter(user_student_id=user, degree=self.degree).exists())

    def test_register_duplicate_email(self):
        User.objects.create_user(
            email="bob@example.com",
            first_name="Bob",
            last_name="Jones",
            password="securepass",
            is_student=True,
            is_advisor=False,
            student_id=100009800
        )
        response = self.client.post(self.register_url, {
            'first_name': 'Bob',
            'last_name': 'Jones',
            'email': 'bob@example.com',
            'password': 'AnotherPass1!',
            'student_id': 123456789,
        })
        self.assertRedirects(response, self.register_url)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("email is already registered" in str(m) for m in messages))

    def test_register_duplicate_student_id(self):
        User.objects.create_user(
            email="charlie@example.com",
            first_name="Charlie",
            last_name="Brown",
            password="securepass",
            is_student=True,
            is_advisor=False,
            student_id=123456789
        )
        response = self.client.post(self.register_url, {
            'first_name': 'Charlie',
            'last_name': 'Brown',
            'email': 'charlie@2example.com',
            'password': 'StrongPass1!',
            'student_id': 123456789,
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
            'student_id': 111222333,
        })
        self.assertRedirects(response, self.register_url)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("Password must be at least 9 characters long" in str(m) for m in messages))

class UploadTranscriptViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="student@example.com", 
            password="TestPass123!", 
            student_id=123456789, 
            first_name='Stu', 
            last_name='Dent',
            is_student=True,
            is_advisor=False,
        )
        self.client.login(email="student@example.com", password="TestPass123!")
        self.url = reverse("uploadTranscript")

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
            "credit_hours": 6,
            "recommendation_reasons": [],
            "notice": ""
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
        self.assertIn("CS 101", [rec["course_name"] for rec in response.context["recommendations"]])
        self.assertIn("recommendations", self.client.session)

    @patch("advisingwebsiteapp.views.process_and_recommend_courses", side_effect=AttributeError)
    def test_post_attribute_error(self, mock_process):
        user_with_no_student_id = User.objects.create_user(
            email="no_student_id@example.com",
            password="TestPass123!",
            student_id=None,
            first_name='Jane',
            last_name='Doe',
            is_student=True,
            is_advisor=False,
        )
        self.client.login(email="no_student_id@example.com", password="TestPass123!")

        fake_file = io.BytesIO(b"Fake PDF content")
        fake_file.name = "transcript.pdf"

        response = self.client.post(self.url, {
            "pdfFile": fake_file,
            "term": "spring",
            "inputCreditHours": "12"
        }, format="multipart")

        # Ensure the correct error message is rendered
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "uploadTranscript.html")
        self.assertContains(response, "Student ID not found in user profile.")

class ProcessAndRecommendCoursesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="TestPass123!",
            student_id=123456789,
            first_name="Test",
            is_student=True,
            is_advisor=False,
            last_name='Example'
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
        mock_requirements.return_value = {
            "courses": [],
            "instructions": [],
            "instructional_rules": []
        }
        mock_recommend.return_value = {
            "recommendations": [
                MagicMock(course_name="CS 200", hours=3),
                MagicMock(course_name="MATH 200", hours=3)
            ],
            "credit_hours": 6,
            "recommendation_reasons": [],
            "notice": ""
        }

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
            max_hours=self.max_hours,
            instructional_rules=[]
        )
        self.assertEqual(mock_requirements.call_count, 2)
        mock_requirements.assert_any_call(self.user.student_id)

        self.assertIn("transcript_data", result)
        self.assertIn("major_requirements", result)
        self.assertIn("recommendations", result)

        self.assertEqual(result["transcript_data"], mock_parse.return_value)
        self.assertEqual(result["major_requirements"], mock_requirements.return_value)
        self.assertEqual(result["recommendations"], mock_recommend.return_value["recommendations"])
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

class ProfileViewTest(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="Testpass123!",
            student_id=123456789,
            first_name='Test',
            is_student=True,
            is_advisor=False,
            last_name="Example"
        )

        # Create degrees
        self.major = Degree.objects.create(degree_name="Computer Science", degree_number="CS123", degree_type=1, hours_needed=120, concentration="General")
        self.minor = Degree.objects.create(degree_name="Mathematics", degree_number="MA123", degree_type=2, concentration="Applied Math", hours_needed=120)
        self.certificate = Degree.objects.create(degree_name="Cybersecurity", degree_number="CY123", degree_type=3, hours_needed=120, concentration="General")

        # Link degrees to user
        UserDegree.objects.create(user_student_id=self.user, degree=self.major)
        UserDegree.objects.create(user_student_id=self.user, degree=self.minor)
        UserDegree.objects.create(user_student_id=self.user, degree=self.certificate)

        self.client = Client()
        self.client.login(email="testuser@example.com", password="Testpass123!")

    def test_profile_view_loads_correctly(self):
        response = self.client.get(reverse("profile"))  # Adjust the URL name if needed

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profile.html')

        # Check degrees are in context
        self.assertIn('majors', response.context)
        self.assertIn('minors', response.context)
        self.assertIn('certificates', response.context)
        self.assertIn('concentrations', response.context)

        self.assertIn(self.major, response.context['majors'])
        self.assertIn(self.minor, response.context['minors'])
        self.assertIn(self.certificate, response.context['certificates'])

        # Check concentrations for minor
        concentrations = response.context['concentrations']
        self.assertEqual(len(concentrations['minor']), 1)
        self.assertEqual(concentrations['minor'][0]['concentration'], "Applied Math")

class UpdateProfileViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='Testpass123!',
            first_name='Old',
            last_name='Name',
            is_student=True,
            is_advisor=False,
            student_id=123456789
        )
        self.client.login(email='testuser@example.com', password='Testpass123!')

    @patch('advisingwebsiteapp.views.update_user_degrees')
    def test_update_profile_success(self, mock_update_user_degrees):
        update_data = {
            'first_name': 'NewFirst',
            'last_name': 'NewLast',
            'email': 'newemail@example.com',
            'major': 'Computer Science',
            'major_number': 'CS123'
        }

        response = self.client.post(reverse('update_profile'), data=update_data)

        # Refresh from DB
        self.user.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('profile'))

        self.assertEqual(self.user.first_name, 'NewFirst')
        self.assertEqual(self.user.last_name, 'NewLast')
        self.assertEqual(self.user.email, 'newemail@example.com')

        # Check if helper function was called
        mock_update_user_degrees.assert_called_once()

    def test_update_profile_get_renders_profile_template(self):
        response = self.client.get(reverse('update_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profile.html')

class UpdateUserDegreesViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='student@example.com',
            password='StrongPass123!',
            first_name='Test',
            last_name='User',
            is_student=True,
            is_advisor=False,
            student_id=123456789
        )
        self.client.login(email='student@example.com', password='StrongPass123!')

        self.degree1 = Degree.objects.create(
            degree_name='Computer Science',
            degree_number='CS101',
            degree_type=1,
            hours_needed=120,
            concentration="General"
        )
        self.degree2 = Degree.objects.create(
            degree_name='Data Science',
            degree_number='DS201',
            degree_type=1,
            hours_needed=120,
            concentration="General"
        )
        # Initially assign degree1
        self.user_degree = UserDegree.objects.create(
            user_student_id=self.user,
            degree=self.degree1
        )

    def test_update_user_degrees_removes_and_adds(self):
        response = self.client.post(reverse('update_profile'), {
            'current_degree': self.degree1.id,
            'degree': self.degree2.id
        })

        self.assertRedirects(response, reverse('profile'))

        # Confirm degree1 was removed
        self.assertFalse(UserDegree.objects.filter(user_student_id=self.user, degree=self.degree1).exists())

        # Confirm degree2 was added
        self.assertTrue(UserDegree.objects.filter(user_student_id=self.user, degree=self.degree2).exists())

    def test_update_user_degrees_only_adds_if_no_duplicate(self):
        # Try adding degree1 again (already exists)
        response = self.client.post(reverse('update_profile'), {
            'degree': self.degree1.id
        })

        # Should not duplicate
        user_degrees = UserDegree.objects.filter(user_student_id=self.user, degree=self.degree1)
        self.assertEqual(user_degrees.count(), 1)

class ChangePasswordViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='OldPassword123!',
            first_name='Test',
            last_name='User',
            is_student=True,
            is_advisor=False,
            student_id=987654321
        )
        self.client.login(email='testuser@example.com', password='OldPassword123!')

    def test_change_password_successfully(self):
        response = self.client.post(reverse('changePassword'), {
            'old_password': 'OldPassword123!',
            'new_password1': 'NewPassword456!',
            'new_password2': 'NewPassword456!'
        })

        self.assertRedirects(response, reverse('profile'))

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPassword456!'))

    def test_change_password_wrong_old_password(self):
        response = self.client.post(reverse('changePassword'), {
            'old_password': 'WrongOldPass!',
            'new_password1': 'NewPassword456!',
            'new_password2': 'NewPassword456!'
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your old password is incorrect.')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('OldPassword123!'))

    def test_change_password_mismatch(self):
        response = self.client.post(reverse('changePassword'), {
            'old_password': 'OldPassword123!',
            'new_password1': 'NewPassword456!',
            'new_password2': 'Mismatch789!'
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Unable to update password. Try again!')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('OldPassword123!'))

class ChatHomeViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = User.objects.create_user(
            email='student@example.com',
            password='TestPass123!',
            first_name='Stu',
            last_name='Dent',
            is_student=True,
            is_advisor=False,
            student_id=123456789
        )

        self.advisor = User.objects.create_user(
            email='advisor@example.com',
            password='TestPass123!',
            first_name='Ad',
            last_name='Visor',
            is_student=False,
            is_advisor=True,
            student_id=987654321
        )

        self.chat = Chat.objects.create(chat_name='Stu Dent, Ad Visor')
        self.chat_member_student = ChatMember.objects.create(user=self.student, chat=self.chat, chat_deleted=False)
        self.chat_member_advisor = ChatMember.objects.create(user=self.advisor, chat=self.chat, chat_deleted=False)

        # Simulate a message
        self.last_message = Message.objects.create(
            chat=self.chat,
            sent_by_member=self.chat_member_advisor,
            message_content='Hello!',
            date_sent=timezone.now()
        )

        self.chat_member_student.chat_last_viewed = self.last_message.date_sent - timezone.timedelta(minutes=5)
        self.chat_member_student.save()

        self.client.login(email='student@example.com', password='TestPass123!')

    def test_chathome_view_renders_for_logged_in_user(self):
        response = self.client.get(reverse('chatHome'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'chat/room_base.html')
        self.assertContains(response, 'Hello!')  # last message
        self.assertIn('chats', response.context)
        self.assertTrue(any(chat['last_message'] == 'Hello!' for chat in response.context['chats']))
        self.assertIn('users', response.context)
        self.assertTrue(any(user.email == 'advisor@example.com' for user in response.context['users']))

    def test_chathome_no_new_messages(self):
        # Simulate last viewed after message sent
        self.chat_member_student.chat_last_viewed = self.last_message.date_sent + timezone.timedelta(minutes=1)
        self.chat_member_student.save()

        response = self.client.get(reverse('chatHome'))
        chats = response.context['chats']
        self.assertFalse(any(chat['new_message'] for chat in chats))  # No new messages

class ChatRoomViewTest(TestCase):
    def setUp(self):
        self.client = Client()

        self.student = User.objects.create_user(
            email='student@example.com',
            password='TestPass123!',
            first_name='Stu',
            last_name='Dent',
            is_student=True,
            is_advisor=False,
            student_id=123456789
        )

        self.advisor = User.objects.create_user(
            email='advisor@example.com',
            password='TestPass123!',
            first_name='Ad',
            last_name='Visor',
            is_advisor=True,
            is_student=False,
            student_id=987654321
        )

        self.chat = Chat.objects.create(chat_name='Stu Dent, Ad Visor')
        self.chat_member_student = ChatMember.objects.create(user=self.student, chat=self.chat, chat_deleted=False)
        self.chat_member_advisor = ChatMember.objects.create(user=self.advisor, chat=self.chat, chat_deleted=False)

        # Add message
        self.message = Message.objects.create(
            chat=self.chat,
            sent_by_member=self.chat_member_advisor,
            message_content='Hey!',
            date_sent=timezone.now()
        )

    def test_room_view_as_member(self):
        self.client.login(email='student@example.com', password='TestPass123!')
        response = self.client.get(reverse('room', args=[self.chat.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'chat/room.html')
        self.assertIn('chats', response.context)
        self.assertIn('email', response.context)
        self.assertContains(response, 'Hey!')

        # Confirm chat_last_viewed is updated
        self.chat_member_student.refresh_from_db()
        self.assertTrue(
            (timezone.now() - self.chat_member_student.chat_last_viewed).total_seconds() < 10
        )

    def test_room_view_nonexistent_chat(self):
        self.client.login(email='student@example.com', password='TestPass123!')
        response = self.client.get(reverse('room', args=[999]))  # Chat ID that doesn't exist
        self.assertRedirects(
            response,
            f"{reverse('error_page')}?exception=ERROR 404: Chat does not exist or could not be found."
        )

    def test_room_view_user_not_member(self):
        outsider = User.objects.create_user(
            email='outsider@example.com',
            password='TestPass123!',
            first_name='Out',
            last_name='Sider',
            is_student=True,
            is_advisor=False,
            student_id=10000000
        )
        self.client.login(email='outsider@example.com', password='TestPass123!')
        response = self.client.get(reverse('room', args=[self.chat.id]))

        self.assertRedirects(
            response,
            f"{reverse('error_page')}?exception=ERROR 500: User is not a member of this chat."
        )

class CheckChatMembershipViewTest(TestCase):
    def setUp(self):
        self.client = Client()

        # Creating users
        self.student = User.objects.create_user(
            email='student@example.com',
            password='TestPass123!',
            first_name='Stu',
            last_name='Dent',
            is_student=True,
            is_advisor=False,
            student_id=123456789
        )

        self.advisor = User.objects.create_user(
            email='advisor@example.com',
            password='TestPass123!',
            first_name='Ad',
            last_name='Visor',
            is_student=False,
            is_advisor=True,
            student_id=987654321
        )

        # Creating chat and adding the student to it
        self.chat = Chat.objects.create(chat_name='Study Group')
        self.chat_member_student = ChatMember.objects.create(user=self.student, chat=self.chat, chat_deleted=False)

    def test_check_chat_membership_member(self):
        # Logging in as the student (who is a member)
        self.client.login(email='student@example.com', password='TestPass123!')

        # Sending a GET request to check membership
        response = self.client.get(reverse('check_chat_membership', args=[self.chat.id]))

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'is_member': True})

    def test_check_chat_membership_non_member(self):
        # Logging in as the advisor (who is NOT a member)
        self.client.login(email='advisor@example.com', password='TestPass123!')

        # Sending a GET request to check membership
        response = self.client.get(reverse('check_chat_membership', args=[self.chat.id]))

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'is_member': False})

class ErrorPageViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_error_page_with_exception(self):
        # Simulating an error by passing an exception message in the query string
        exception_message = "ERROR 404: Page Not Found"
        
        # Sending a GET request with the exception message
        response = self.client.get(reverse('error_page') + f'?exception={exception_message}')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, exception_message)
        self.assertTemplateUsed(response, 'error.html')

    def test_error_page_without_exception(self):
        # Sending a GET request without an exception message
        response = self.client.get(reverse('error_page'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'An unknown error occurred.')
        self.assertTemplateUsed(response, 'error.html')