import os
import json
import re
import pdfplumber
from dotenv import load_dotenv
from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from llama_index.readers.llama_parse import LlamaParse
from .models import User, Degree, UserDegree

def parse_transcript(file_path):
    """
    Parses a transcript PDF using LlamaParse and pdfplumber to extract
    student information and courses.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    load_dotenv()
    api_key = os.getenv("LLAMA_CLOUD_API_KEY")
    if not api_key:
        raise ValueError("Missing API key!")

    parser = LlamaParse(
        api_key=api_key,
        content_guideline_instruction="Extract all course details",
        enable_table_extraction=True  
    )

    parsed_data = parser.load_data(file_path)
    extracted_text = "\n".join([section.text.strip() for section in parsed_data if section.text])

    structured_data = {
        "student_name": "Unknown",
        "student_id": "Unknown",
        "college": [],
        "major": [],
        "degree_num": [],
        "courses": []
    }

    def parse_course(subject, course, level, title, grade, credit_hours, quality_points):
        # Appends a course to the structured_data['courses'] list
        structured_data["courses"].append({
            "subject": subject,
            "course_number": course,
            "level": level,
            "title": title,
            "grade": grade,
            "credit_hours": credit_hours if credit_hours.replace(".", "").isdigit() else "0",
            "quality_points": quality_points if quality_points.replace(".", "").isdigit() else "0"
        })

    # Extract name and ID
    name_match = re.search(r"Name\s*:\s*(.+)", extracted_text, re.IGNORECASE)
    if name_match:
        structured_data["student_name"] = name_match.group(1).strip()

    id_match = re.search(r"WKU ID\s*:\s*(\d+)", extracted_text, re.IGNORECASE)
    if id_match:
        structured_data["student_id"] = id_match.group(1).strip()

    # Extract curriculum info
    curriculum_match = re.search(r"Curriculum Information(.*?)(?=\n\w+:|End of Report|$)", extracted_text, re.DOTALL)
    if curriculum_match:
        curriculum = curriculum_match.group(1)
        colleges = re.findall(r"College:\s*(.+)", curriculum)
        structured_data["college"] = [c.strip() for c in colleges if "Exploratory Studies" not in c]

        majors = re.findall(r"Major and Department:\s*\[(\d{3,4}[A-Z]?)\]\s*([^\n,]+)", curriculum)
        for num, major in majors:
            structured_data["major"].append(major.strip())
            structured_data["degree_num"].append(num.strip())

        minors = re.findall(r"Minor:\s*\[(\d{3,4})\]\s*([^\n]+)", curriculum)
        for num, minor in minors:
            structured_data["major"].append(minor.strip())
            structured_data["degree_num"].append(num.strip())

        certs = re.findall(r"Major and Department:\s*\[(\d{4})\]\s*([^\n,]+)", curriculum)
        for num, cert in certs:
            if num.strip() not in structured_data["degree_num"]:
                structured_data["major"].append(cert.strip())
                structured_data["degree_num"].append(num.strip())

    # Extract courses info
    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for table_num, table in enumerate(tables):
                for row_num, row in enumerate(table):
                    row = [col.strip() if col else "" for col in row]
                    # print(f"Row {row_num + 1} ({len(row)} cols): {row}")

                    if not row or len(row) < 2:
                        continue
                    if row[0].lower() == "subject" and row[1].lower() == "course":
                        continue

                    subject = row[0]
                    course = row[1]

                    # Special case for language proficieny requirement 
                    if len(row) >= 7 and re.match(r"^[A-Z]{2,5}$", subject) and not course.isdigit():
                        parse_course(subject, course, "", row[2], row[4], row[5], row[6])
                        continue

                    # 11-column layout
                    if len(row) == 11 and course.isdigit() and re.match(r"^[A-Z]{2,5}$", subject):
                        parse_course(subject, course, row[2], row[3], row[7], row[8], row[9])
                    # 9-column layout
                    elif len(row) == 9 and course.isdigit() and re.match(r"^[A-Z]{2,5}$", subject):
                        parse_course(subject, course, "", row[2], row[4], row[5], row[6])
                    # 8-column layout
                    elif len(row) == 8 and course.isdigit() and re.match(r"^[A-Z]{2,5}$", subject):
                        parse_course(subject, course, row[2], row[3], row[4], row[5], row[6])
                    # 7-column layout 
                    elif len(row) == 7 and course.isdigit() and re.match(r"^[A-Z]{2,5}$", subject):
                        parse_course(subject, course, "", row[2], row[3], row[4], row[5])
                    # 5-column layout 
                    elif len(row) == 5 and course.isdigit() and re.match(r"^[A-Z]{2,5}$", subject):
                        parse_course(subject, course, row[2], row[3], "", row[4], "0")

    return structured_data

def store_user_degree(structured_data):
    """
    Stores extracted degree numbers to the UserDegree table, linking each to the correct User and Degree.
    """
    student_id = structured_data.get("student_id")
    degree_numbers = structured_data.get("degree_num", [])

    print(f"DEBUG: Extracted student_id: {student_id}")
    print(f"DEBUG: Extracted degree_numbers: {degree_numbers}")

    if student_id and degree_numbers:
        try:
            user = User.objects.get(student_id=student_id)
            print(f"DEBUG: Found User -> {user}")

            for degree_number in degree_numbers:
                degree = Degree.objects.filter(degree_number=degree_number).first()

                if not degree:
                    # print(f"No matching Degree found for degree_number={degree_number}")
                    continue

                user_degree, created = UserDegree.objects.get_or_create(
                    user_student_id=user,
                    degree=degree
                )

        except User.DoesNotExist:
            print(f"No User found with student_id={student_id}")
        except Exception as e:
            print(f"Failed to insert UserDegree - {e}")
