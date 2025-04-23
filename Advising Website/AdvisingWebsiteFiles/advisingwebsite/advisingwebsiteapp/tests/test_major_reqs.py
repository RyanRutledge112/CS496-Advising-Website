from django.test import TestCase
from unittest.mock import patch, MagicMock
from advisingwebsiteapp.majorreqs import extract_all_catalog_courses, extract_courses_from_html, guess_course_catalog_url
from bs4 import BeautifulSoup

class ExtractCatalogCoursesTests(TestCase):
    def test_extract_basic_course_info(self):
        html = """
        <div class="courseblock">
            <p class="courseblocktitle">
                CS 120 Introduction to Programming (3 Hours)
            </p>
            <p class="courseblockextra">
                Prerequisite(s): MATH 117 or equivalent.
            </p>
            <p class="courseblockextra">
                Recent Term(s) Offered: fall 2022; spring 2023; fall 2023
            </p>
            <a class="bubblelink code" href="/search/?P=CS%20120">CS 120</a>
        </div>
        """

        courses = extract_all_catalog_courses(html)
        self.assertEqual(len(courses), 1)

        course = courses[0]
        self.assertEqual(course["title"], "CS 120")
        self.assertEqual(course["hours"], 3)
        self.assertIn("MATH 117", course["prerequisites"])
        self.assertIn("fall 2022", course["recent_terms"])
        self.assertEqual(course["href"], {"CS 120": "/search/?P=CS%20120"})

        self.assertEqual(course["corequisites"], "")
        self.assertEqual(course["restrictions"], "")

class ExtractDegreeCoursesTests(TestCase):
    @patch("advisingwebsiteapp.majorreqs.CourseExtractor")
    @patch("advisingwebsiteapp.majorreqs.read_file")
    @patch("advisingwebsiteapp.majorreqs.os.path.exists", return_value=True)
    @patch("advisingwebsiteapp.majorreqs.get_parse_path")
    def test_extract_courses_for_degree_and_concentration(
        self, mock_get_path, mock_exists, mock_read_file, mock_course_extractor
    ):

        mock_get_path.return_value = "fakepath/cs.html"
        mock_read_file.return_value = """
        <div id="programrequirementstextcontainer">
            <table><tr><td>CS 120</td></tr></table>
        </div>
        """

        mock_instance = MagicMock()
        mock_instance.extracted_courses = [{"title": "CS 120", "hours": 3}]
        mock_instance.parse.return_value = "parsed_structure"
        mock_course_extractor.return_value = mock_instance

        courses, structure = extract_courses_from_html("Computer Science", concentration="General")

        self.assertEqual(courses, [{"title": "CS 120", "hours": 3}])
        self.assertEqual(structure, "parsed_structure")

        mock_get_path.assert_called_once_with("Computer Science")
        mock_course_extractor.assert_called_once()
        mock_instance.parse.assert_called_once_with("General")

class URLMappingTests(TestCase):
    @patch("advisingwebsiteapp.majorreqs.requests.get")
    def test_guess_course_catalog_url(self, mock_get):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.text = """
        <html>
            <head><title>Courses</title></head>
            <body>
                <h1 class="page-title">Computer Science Courses</h1>
            </body>
        </html>
        """
        mock_get.return_value = mock_response

        url, soup = guess_course_catalog_url("Computer Science")

        self.assertIsNotNone(url)
        self.assertTrue(url.startswith("https://catalog.wku.edu/undergraduate/course-descriptions/"))

        heading = soup.find("h1", class_="page-title")
        self.assertIsNotNone(heading)
        self.assertIn("computer science", heading.text.lower())

