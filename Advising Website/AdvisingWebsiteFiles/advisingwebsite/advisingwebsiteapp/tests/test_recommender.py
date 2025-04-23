from django.test import TestCase
from unittest.mock import patch, MagicMock
from advisingwebsiteapp.recommender import filter_by_recent_terms, filter_courses_by_prerequisites
from datetime import datetime
from advisingwebsiteapp.models import Prerequisites

class TermConstraintTests(TestCase):
    def test_filter_by_selected_term_fall_with_mock(self):
        current_year = datetime.now().year

        course1 = MagicMock()
        course1.course_name = "CS 120"
        course1.recent_terms = f"fall {current_year}; spring {current_year}"

        course2 = MagicMock()
        course2.course_name = "CS 121"
        course2.recent_terms = f"summer {current_year - 1}"

        course3 = MagicMock()
        course3.course_name = "CS 122"
        course3.recent_terms = f"fall {current_year - 3}"  

        course4 = MagicMock()
        course4.course_name = "CS 123"
        course4.recent_terms = ""  

        course5 = MagicMock()
        course5.course_name = "CS 124"
        course5.recent_terms = f"fall {current_year - 2}; fall {current_year}"

        filtered = filter_by_recent_terms([course1, course2, course3, course4, course5], "fall")
        filtered_names = [c.course_name for c in filtered]

        self.assertIn("CS 120", filtered_names)
        self.assertIn("CS 124", filtered_names)
        self.assertNotIn("CS 121", filtered_names)
        self.assertNotIn("CS 122", filtered_names)
        self.assertNotIn("CS 123", filtered_names)

class PrerequisiteConstraintTests(TestCase):
    @patch("advisingwebsiteapp.recommender.Prerequisites.objects.filter")
    def test_multiple_prerequisites_filtering(self, mock_filter):
        taken = MagicMock()
        taken.course_name = "CS 290"
        transcript_courses = [taken]

        #CS 339 requires CS 290 and MATH 136
        course1 = MagicMock()
        course1.course_name = "CS 339"

        prereq1a = MagicMock()
        prereq1a.course = course1
        prereq1a.prerequisite.course_name = "CS 290"

        prereq1b = MagicMock()
        prereq1b.course = course1
        prereq1b.prerequisite.course_name = "MATH 136"

        #CS 331 requires CS 290
        course2 = MagicMock()
        course2.course_name = "CS 331"

        prereq2 = MagicMock()
        prereq2.course = course2
        prereq2.prerequisite.course_name = "CS 290"

        def mock_filter_side_effect(course):
            if course == course1:
                return [prereq1a, prereq1b]
            elif course == course2:
                return [prereq2]
            return []

        mock_filter.side_effect = mock_filter_side_effect

        eligible = filter_courses_by_prerequisites([course1, course2], transcript_courses)
        eligible_names = [c.course_name for c in eligible]

        self.assertIn("CS 331", eligible_names)  
        self.assertNotIn("CS 339", eligible_names)  

