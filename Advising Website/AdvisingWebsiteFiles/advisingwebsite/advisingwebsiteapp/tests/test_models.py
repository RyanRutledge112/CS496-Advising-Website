from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from advisingwebsiteapp.models import Chat, ChatMember, Course, Degree, DegreeCourse, Message, Prerequisites, UserDegree
from django.utils import timezone

User = get_user_model()

"""
Runs test cases for every single model function to make sure that the models are created
with their intended values and the function inside the models are working properly.

ChatGPT was used to help facilitate the creation of views testing
https://chatgpt.com/share/67f47ab8-d7a0-800c-baea-6a808dfb69c2
"""

class CustomUserModelTests(TestCase):

    def test_create_user_successfully(self):
        user = User.objects.create_user(
            email="student@example.com",
            first_name="John",
            last_name="Doe",
            password="securepassword123",
            is_student=True,
            is_advisor=False,
            student_id=123456
        )
        self.assertEqual(user.email, "student@example.com")
        self.assertEqual(user.first_name, "John")
        self.assertEqual(user.last_name, "Doe")
        self.assertTrue(user.is_student)
        self.assertFalse(user.is_advisor)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password("securepassword123"))

    def test_create_superuser_successfully(self):
        admin = User.objects.create_superuser(
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            password="adminpass123",
            is_student=False,
            is_advisor=True,
            student_id=999999
        )
        self.assertEqual(admin.email, "admin@example.com")
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_advisor)
        self.assertTrue(admin.check_password("adminpass123"))

    def test_email_is_normalized(self):
        user = User.objects.create_user(
            email="Test@Example.com",
            first_name="Norm",
            last_name="Alize",
            password="test12345",
            is_student=True,
            is_advisor=False,
            student_id=222222
        )
        self.assertEqual(user.email, "Test@example.com")

    def test_create_user_without_email_raises_error(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email="",
                first_name="No",
                last_name="Email",
                password="nopass123",
                is_student=True,
                is_advisor=False,
                student_id=111111
            )

    def test_get_full_name_and_short_name(self):
        user = User.objects.create_user(
            email="user@example.com",
            first_name="Alice",
            last_name="Smith",
            password="strongpass",
            is_student=True,
            is_advisor=False,
            student_id=444444
        )
        self.assertEqual(user.get_full_name(), "Alice Smith")
        self.assertEqual(user.get_short_name(), "Alice")

    def test_get_full_name_and_short_name_when_name_is_blank(self):
        user = User.objects.create_user(
            email="noname@example.com",
            password="strongpass",
            is_student=True,
            is_advisor=False,
            student_id=555555
        )
        self.assertEqual(user.get_full_name(), "noname")
        self.assertEqual(user.get_short_name(), "noname")

    def test_get_student_id(self):
        user = User.objects.create_user(
            email="idtest@example.com",
            password="securepass",
            is_student=True,
            is_advisor=False,
            student_id=888888
        )
        self.assertEqual(user.get_student_id(), 888888)

class ChatModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            first_name="John",
            last_name="Doe",
            password="securepass",
            is_student=True,
            is_advisor=False,
            student_id=100001
        )
        self.chat = Chat.objects.create(chat_name="Test Chat")

    def test_str_method_returns_chat_name(self):
        self.assertEqual(str(self.chat), "Test Chat")

    def test_last_30_messages_returns_most_recent(self):
        # Create 35 messages
        for i in range(35):
            Message.objects.create(
                chat=self.chat,
                user=self.user,
                message_content=f"Message {i}",
                date_sent=timezone.now()
            )
        last_30 = self.chat.last_30_messages()
        self.assertEqual(len(last_30), 30)
        self.assertEqual(last_30[0].message_content, "Message 34")

    def test_last_message_returns_latest(self):
        Message.objects.create(
            chat=self.chat,
            user=self.user,
            message_content="First message",
            date_sent=timezone.now()
        )
        last = Message.objects.create(
            chat=self.chat,
            user=self.user,
            message_content="Most recent message",
            date_sent=timezone.now() + timezone.timedelta(minutes=5)
        )
        self.assertEqual(self.chat.last_message(), last)

    def test_last_message_returns_none_when_no_messages(self):
        self.assertIsNone(self.chat.last_message())

class ChatMemberModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="testuser@example.com",
            first_name="Jane",
            last_name="Doe",
            password="securepass123",
            is_student=True,
            is_advisor=False,
            student_id=123456
        )
        self.chat = Chat.objects.create(chat_name="Test Chat")

    def test_create_chat_member(self):
        member = ChatMember.objects.create(user=self.user, chat=self.chat)
        self.assertEqual(member.user, self.user)
        self.assertEqual(member.chat, self.chat)
        self.assertFalse(member.chat_deleted)
        self.assertIsNotNone(member.chat_last_viewed)

    def test_str_method(self):
        member = ChatMember.objects.create(user=self.user, chat=self.chat)
        expected = f'User: {self.user.get_full_name()} | Chat: {self.chat.__str__()}'
        self.assertEqual(str(member), expected.strip())

    def test_chat_last_viewed_is_auto_now_add(self):
        member = ChatMember.objects.create(user=self.user, chat=self.chat)
        now = timezone.now()
        self.assertTrue((now - member.chat_last_viewed).total_seconds() < 5)

class MessageModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="testuser@example.com",
            first_name="Alice",
            last_name="Smith",
            password="password123",
            is_student=True,
            is_advisor=False,
            student_id=987654
        )

        self.chat = Chat.objects.create(chat_name="General Discussion")
        self.chat_member = ChatMember.objects.create(user=self.user, chat=self.chat)

    def test_message_creation(self):
        msg = Message.objects.create(
            sent_by_member=self.chat_member,
            chat=self.chat,
            message_content="Hello, world!"
        )

        self.assertEqual(msg.sent_by_member, self.chat_member)
        self.assertEqual(msg.chat, self.chat)
        self.assertEqual(msg.message_content, "Hello, world!")
        self.assertIsNotNone(msg.date_sent)

    def test_str_method(self):
        msg = Message.objects.create(
            sent_by_member=self.chat_member,
            chat=self.chat,
            message_content="Testing the message model."
        )
        expected_str = f'{self.chat_member} | Testing the message model.'
        self.assertEqual(str(msg), expected_str.strip())

    def test_date_sent_auto_now_add(self):
        msg = Message.objects.create(
            sent_by_member=self.chat_member,
            chat=self.chat,
            message_content="Check date sent."
        )
        now = timezone.now()
        self.assertTrue((now - msg.date_sent).total_seconds() < 5)

class DegreeModelTests(TestCase):

    def test_degree_creation(self):
        degree = Degree.objects.create(
            degree_name="Computer Science",
            degree_number="CS101",
            concentration="Software Engineering",
            hours_needed=120,
            degree_type=1
        )

        self.assertEqual(degree.degree_name, "Computer Science")
        self.assertEqual(degree.degree_number, "CS101")
        self.assertEqual(degree.concentration, "Software Engineering")
        self.assertEqual(degree.hours_needed, 120)
        self.assertEqual(degree.degree_type, 1)

    def test_str_method_for_major(self):
        degree = Degree.objects.create(
            degree_name="Computer Science",
            degree_number="CS101",
            concentration="AI",
            hours_needed=120,
            degree_type=1
        )
        expected_str = "Computer Science AI Major"
        self.assertEqual(str(degree), expected_str)

    def test_str_method_with_unknown_degree_type(self):
        # Directly assigning an invalid degree_type value
        degree = Degree(
            degree_name="Mathematics",
            degree_number="MATH201",
            concentration="Pure Math",
            hours_needed=120,
            degree_type=999
        )
        self.assertEqual(str(degree), "Mathematics Pure Math Unknown")

class CourseModelTests(TestCase):

    def test_course_creation_non_colonade(self):
        course = Course.objects.create(
            course_name="Intro to Python",
            hours=3,
            is_colonade=False,
            colonade_id=None,
            corequisites="None",
            restrictions="None",
            recent_terms="Fall 2024"
        )

        self.assertEqual(course.course_name, "Intro to Python")
        self.assertEqual(course.hours, 3)
        self.assertFalse(course.is_colonade)
        self.assertIsNone(course.colonade_id)
        self.assertEqual(course.corequisites, "None")
        self.assertEqual(course.restrictions, "None")
        self.assertEqual(course.recent_terms, "Fall 2024")

        expected_str = "Name: Intro to Python\nHours required to graduate: 3 hours"
        self.assertEqual(str(course), expected_str)

    def test_course_creation_with_colonade(self):
        course = Course.objects.create(
            course_name="World History",
            hours=3,
            is_colonade=True,
            colonade_id="HUM101",
            corequisites="None",
            restrictions="None",
            recent_terms="Spring 2025"
        )

        expected_str = (
            "Name: World History\n"
            "Hours required to graduate: 3 hours\n"
            "Colonade requirement for: HUM101"
        )
        self.assertEqual(str(course), expected_str)

class DegreeCourseModelTests(TestCase):
    def setUp(self):
        self.degree = Degree.objects.create(
            degree_name="Computer Science",
            degree_number="CS101",
            concentration="AI",
            hours_needed=120,
            degree_type=1
        )
        self.course = Course.objects.create(
            course_name="Data Structures",
            hours=3,
            is_colonade=False,
            colonade_id=None
        )

    def test_required_only_course(self):
        degree_course = DegreeCourse.objects.create(
            degree=self.degree,
            course=self.course,
            is_elective=False,
            is_required=True
        )
        expected_str = "Data Structures is a requirement for Computer Science"
        self.assertEqual(str(degree_course), expected_str)

    def test_elective_only_course(self):
        degree_course = DegreeCourse.objects.create(
            degree=self.degree,
            course=self.course,
            is_elective=True,
            is_required=False
        )
        expected_str = "Data Structures is an elective for Computer Science"
        self.assertEqual(str(degree_course), expected_str)

    def test_elective_and_required_course(self):
        degree_course = DegreeCourse.objects.create(
            degree=self.degree,
            course=self.course,
            is_elective=True,
            is_required=True
        )
        expected_str = "Data Structures is an elective and a requirement for Computer Science"
        self.assertEqual(str(degree_course), expected_str)

    def test_neither_required_nor_elective(self):
        degree_course = DegreeCourse.objects.create(
            degree=self.degree,
            course=self.course,
            is_elective=False,
            is_required=False
        )
        expected_str = "Data Structures"
        self.assertEqual(str(degree_course), expected_str)

class PrerequisitesModelTests(TestCase):
    def setUp(self):
        self.course = Course.objects.create(
            course_name="Algorithms",
            hours=3,
            is_colonade=False,
            colonade_id=None
        )
        self.prerequisite_course = Course.objects.create(
            course_name="Data Structures",
            hours=3,
            is_colonade=False,
            colonade_id=None
        )

    def test_prerequisite_str(self):
        prereq = Prerequisites.objects.create(
            course=self.course,
            prerequisite=self.prerequisite_course
        )
        expected_str = "Data Structures is a prerequisite for Algorithms"
        self.assertEqual(str(prereq), expected_str)


class UserDegreeModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="student@example.com",
            first_name="John",
            last_name="Doe",
            password="testpass123",
            is_student=True,
            is_advisor=False,
            student_id=10001
        )
        self.degree = Degree.objects.create(
            degree_name="Computer Science",
            degree_number="CS101",
            concentration="Software Engineering",
            hours_needed=120,
            degree_type=1
        )

    def test_user_degree_str(self):
        user_degree = UserDegree.objects.create(
            user_student_id=self.user,
            degree=self.degree
        )
        expected_str = f"Student {self.user.get_full_name()} with a student id of {self.user.student_id} is going for a degree in {self.degree.__str__()}"
        self.assertEqual(str(user_degree), expected_str)