from django.test import TestCase
from advisingwebsiteapp.models import User, Degree, UserDegree, Course, DegreeCourse, Prerequisites
from advisingwebsiteapp.recommender import recommend_schedule

class RecommenderSystemTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="student@example.com",
            password="testpass123",
            student_id="800123456",
            first_name="John",
            last_name="Doe",
            is_student=True,
            is_advisor=False
        )

        self.degree = Degree.objects.create(
            degree_name="Computer Science",
            degree_number="629",
            concentration="General",
            hours_needed=120,
            degree_type=1
        )

        UserDegree.objects.create(user_student_id=self.user, degree=self.degree)

        cs120 = Course.objects.create(
            course_name="CS 180",
            hours=3,
            is_colonade=False,
            colonade_id="",
            corequisites="",
            recent_terms="fall 2024; spring 2025",
            restrictions=""
        )

        cs221 = Course.objects.create(
            course_name="CS 290",
            hours=3,
            is_colonade=False,
            colonade_id="",
            corequisites="",
            recent_terms="fall 2024; spring 2025",
            restrictions=""
        )
        DegreeCourse.objects.create(
            course=cs221, 
            degree=self.degree,
            is_required=True,
            is_elective=False
        )

        Prerequisites.objects.create(course=cs221, prerequisite=cs120)

        self.transcript_data = {
            "student_name": "Test User",
            "student_id": "800123456",
            "major": ["Computer Science"],
            "degree_num": ["629"],
            "courses": [
                {"subject": "CS", "course_number": "180", "grade": "A", "credit_hours": "3", "quality_points": "12"}
            ]
        }

    def test_full_recommendation_logic(self):
        result = recommend_schedule(
            user=self.user,
            transcript_data=self.transcript_data,
            selected_term="fall",
            max_hours=15,
            instructional_rules=[]
        )

        course_names = [c.course_name for c in result["recommendations"] if not isinstance(c, list)]

        self.assertIn("CS 290", course_names)
        self.assertEqual(result["credit_hours"], 3)
        self.assertEqual(
            result["notice"],
            "You have no more available courses to recommend for this term — most likely you've completed most of your degree requirements!"
        )
