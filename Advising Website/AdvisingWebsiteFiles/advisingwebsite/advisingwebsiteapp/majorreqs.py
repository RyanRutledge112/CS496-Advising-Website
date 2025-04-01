import os
import re
import uuid
import requests
from collections import defaultdict
from bs4 import BeautifulSoup, Tag
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from advisingwebsiteapp.models import User, UserDegree, Course, DegreeCourse, Degree, Prerequisites

BASE_URL = "https://catalog.wku.edu"
BASE_CATALOG_URL = f"{BASE_URL}/undergraduate/programs/"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARSE_DIR = os.path.join(BASE_DIR, "Parse")
os.makedirs(PARSE_DIR, exist_ok=True)

def get_user_major(student_id):
    try:
        user = User.objects.get(student_id=student_id)
    except User.DoesNotExist:
        return None

    major = next(
        (ud.degree.degree_name.split(",")[0].replace("Major: ", "").strip()
         for ud in UserDegree.objects.filter(user_student_id=user)
         if ud.degree.degree_type == 1),
        None
    )
    return major

def clean_text(s):
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()

def normalize_code(code):
    return clean_text(code).upper()

def normalize_course_name(name):
    name = re.sub(r"Option [A-Z]:\s*", "", name)
    return normalize_code(name)

def extract_course_code(course_name):
    match = re.match(r'([A-Z]{2,4})\s*0*(\d{2,3}[A-Z]?)', course_name.upper().strip())
    return f"{match.group(1)} {match.group(2)}" if match else course_name.strip()

def is_valid_course(course_number, course_name):
    if not course_number or not course_name:
        return False
    if "select" in course_number.lower() or "one of the following" in course_name.lower():
        return False
    # Accept things like PSY/PSYS 220
    return re.match(r"[A-Z]{2,5}/?[A-Z]{0,5}\s?\d{3}", course_number) is not None

def get_safe_filename(name, suffix="", ext="html"):
    # Cleans and returns file name
    name = re.sub(r"[^\w]+", "_", name.strip())
    return f"{re.sub(r'_+', '_', name).strip('_')}{suffix}.{ext}"

def get_parse_path(name, suffix="", ext="html"):
    return os.path.join(PARSE_DIR, get_safe_filename(name, suffix, ext))

def read_file(path, mode="r"):
    with open(path, mode, encoding=None if "b" in mode else "utf-8") as f:
        return f.read()

def write_file(path, content, mode="w"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode, encoding=None if "b" in mode else "utf-8") as f:
        f.write(content)

def extract_colonnade_info(soup):
    # Extracts Colonnade status and code from content
    colonade = False
    colonade_id = None

    tags = soup.find_all("p", class_=["courseblockdesc", "courseblockextra"])
    for tag in tags:
        text = tag.get_text(" ", strip=True).lower()
        if "colonnade" in text:
            colonade = True
            match = re.search(r"code\s*([A-Z0-9\-]+)", text, flags=re.IGNORECASE)
            if match:
                colonade_id = match.group(1).strip()
    return colonade, colonade_id

def fetch_course_info(course_name):
    href = f"/search/?P={course_name.replace(' ', '%20')}"
    full_url = f"{BASE_URL}{href}"

    try:
        res = requests.get(full_url, timeout=10)
        res.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(res.text, "html.parser")
    block = soup.find("div", class_="searchresult search-courseresult")
    if not block or not block.find("h2"):
        return None

    header = re.sub(r"[\s\xa0]+", " ", block.find("h2").get_text(" ", strip=True))
    match = re.match(r"^([A-Z]+ \d+)\s+(.*?)\s+(\d+)(?:[-–]\d+)?\s+Hour[s]?", header)
    if not match:
        return None

    course_code, title, hours = match.group(1), match.group(2), int(match.group(3))
    full_text = block.find("p", class_="search-summary").get_text(" ", strip=True) if block.find("p", class_="search-summary") else ""

    def extract_field(text, label):
        return text.split(label, 1)[-1].split(":", 1)[0].split("Restriction(s):")[0].split("Recent Term(s) Offered:")[0].strip() if label in text else ""

    return {
        "course_name": course_code,
        "title": title,
        "hours": hours,
        "description": full_text.split("Prerequisite(s):")[0].strip() if "Prerequisite(s):" in full_text else full_text,
        "prerequisites": extract_field(full_text, "Prerequisite(s):"),
        "corequisites": extract_field(full_text, "Corequisite(s):"),
        "restrictions": extract_field(full_text, "Restriction(s):"),
        "recent_terms": extract_field(full_text, "Recent Term(s) Offered:"),
        "colonade": extract_colonnade_info(soup)[0],
        "colonade_id": extract_colonnade_info(soup)[1],
    }

def get_or_create_course(course_name, hours=0, colonade=False, colonade_id=None,
                         corequisites=None, restrictions=None, recent_terms=None):
    course_name = normalize_course_name(course_name)
    normalized_code = extract_course_code(course_name)

    course = next((c for c in Course.objects.all() if extract_course_code(c.course_name) == normalized_code), None)

    if course:
        updated = False
        if course.hours == 0 and hours: course.hours, updated = hours, True
        if not course.is_colonade and colonade: course.is_colonade, course.colonade_id, updated = colonade, colonade_id, True
        if not course.corequisites and corequisites: course.corequisites, updated = corequisites, True
        if not course.restrictions and restrictions: course.restrictions, updated = restrictions, True
        if not course.recent_terms and recent_terms: course.recent_terms, updated = recent_terms, True
        if updated: course.save()
        return course, False
    else:
        course = Course.objects.create(
            course_name=course_name,
            hours=hours,
            is_colonade=colonade,
            colonade_id=colonade_id,
            corequisites=corequisites,
            restrictions=restrictions,
            recent_terms=recent_terms
        )
        return course, True

def get_or_create_degree_course(course_obj, degree_obj, is_required=False, is_elective=False, group_id=None):
    return DegreeCourse.objects.get_or_create(
        course=course_obj,
        degree=degree_obj,
        defaults={"is_required": is_required, "is_elective": is_elective, "group_id": group_id}
    )

def deduplicate_courses():
    courses_by_code = defaultdict(list)
    for course in Course.objects.all():
        code = extract_course_code(course.course_name)
        courses_by_code[code].append(course)

    for duplicates in courses_by_code.values():
        if len(duplicates) > 1:
            for course in duplicates[1:]:
                course.delete()
class CourseExtractor:
    def __init__(self, section):
        self.section = section
        self.extracted_courses = []
        self.current_required = False
        self.current_elective = False
        self.current_category = None
        self.should_stop = False

        self.group_mode = False
        self.current_group_id = None
        self.previous_course_data = None

    def parse(self, concentration=None):
        elements = self._get_starting_point(concentration)

        for elem in elements:
            text = elem.get_text(strip=True).lower()
            if elem.name in ["h2", "h3", "tr"] and "required" in text:
                self._update_flags_from_header(text)

        for elem in elements:
            if self.should_stop or (elem.name == "h3" and "faculty" in elem.get_text(strip=True).lower()):
                break

            heading = elem.get_text(strip=True).lower()
            if elem.name == "h3" and any(x in heading for x in ["forensic psychology", "sport psychology"]):
                self.should_stop = True
                break

            if elem.name == "tr" and "areaheader" in elem.get("class", []):
                self._reset_grouping()
                self._update_flags_from_header(heading)
                continue

            if elem.name == "tr" and elem.find("span", class_="courselistcomment"):
                self._reset_grouping()
                self._start_new_group(elem.get_text(strip=True))
                continue

            if elem.name == "table" and "sc_courselist" in elem.get("class", []):
                self._extract_table_courses(elem)

        return self.extracted_courses

    def _get_starting_point(self, concentration):
        if concentration:
            headings = [f"{concentration.lower()} {x}" for x in ["concentration", "option", "track"]]
            for h3 in self.section.find_all("h3"):
                if any(h in h3.get_text(strip=True).lower() for h in headings):
                    return h3.find_all_next()
            return []
        else:
            for elem in self.section.find_all():
                if elem.name == "h2" and "program requirements" in elem.get_text(strip=True).lower():
                    return elem.find_all_next()
            return self.section.find_all()

    def _reset_grouping(self):
        self.group_mode = False
        self.current_group_id = None
        self.previous_course_data = None

    def _update_flags_from_header(self, header):
        header = header.lower()
        self.current_category = header
        self.current_required = any(w in header for w in ["core", "required", "requirement", "additional requirement"])
        self.current_elective = not self.current_required and "elective" in header

    def _start_new_group(self, comment):
        keywords = ["select", "choose", "one of the following", "two from the following", "hours from the following"]
        if any(k in comment.lower() for k in keywords):
            self.group_mode = True
            self.current_group_id = str(uuid.uuid4())
            self.extracted_courses.append({
                "course_number": comment,
                "course_name": "",
                "hours": "N/A",
                "is_required": False,
                "is_elective": True,
                "note": self.current_category,
                "type": "instruction",
                "group_id": self.current_group_id
            })

    def _extract_table_courses(self, table):
        if not isinstance(table, Tag):
            return

        for row in table.find_all("tr", class_=lambda c: c in ["even", "odd", "orclass"]):
            if row.find("span", class_="courselistcomment areaheader"):
                self._update_flags_from_header(row.get_text(strip=True))
                continue

            if row.find("span", class_="courselistcomment"):
                self._reset_grouping()
                self._start_new_group(row.get_text(strip=True))
                continue

            cols = row.find_all("td")
            if len(cols) < 2:
                continue

            course_number_raw = clean_text(cols[0].get_text())
            course_name_raw = clean_text(cols[1].get_text())
            credit_hours = clean_text(cols[2].get_text()) if len(cols) > 2 else ""
            course_href = cols[0].find("a", href=True)["href"] if cols[0].find("a", href=True) else None

            course_numbers = [normalize_code(c) for c in re.split(r"&|,", course_number_raw)]
            course_names = [c.strip() for c in re.split(r" and | & ", course_name_raw)]

            if len(course_numbers) != len(course_names):
                course_names = [course_name_raw] * len(course_numbers)

            for i in range(len(course_numbers)):
                course_number = course_numbers[i]
                course_name = course_names[i]
                full_course_name = normalize_course_name(f"{course_number} {course_name}")

                if not is_valid_course(course_number, full_course_name):
                    continue

                if not credit_hours or credit_hours.lower() == "n/a":
                    info = fetch_course_info(full_course_name)
                    credit_hours = info["hours"] if info else "N/A"
                    colonade = info.get("colonade", False)
                    colonade_id = info.get("colonade_id", None)
                else:
                    colonade = colonade_id = None

                is_or_row = "orclass" in row.get("class", [])
                is_indented = row.find("div", class_="blockindent") is not None

                group_id = None
                if is_or_row and self.previous_course_data:
                    group_id = self.previous_course_data.get("group_id") or str(uuid.uuid4())
                    self.previous_course_data["group_id"] = group_id
                elif self.group_mode and is_indented:
                    group_id = self.current_group_id
                else:
                    self._reset_grouping()

                course_data = {
                    "course_number": course_number,
                    "course_name": full_course_name,
                    "hours": credit_hours,
                    "course_href": course_href,
                    "is_required": self.current_required if not group_id else False,
                    "is_elective": self.current_elective,
                    "note": "or" if is_or_row else self.current_category,
                    "type": "course",
                    "colonade": colonade,
                    "colonade_id": colonade_id,
                    "group_id": group_id
                }

                self.extracted_courses.append(course_data)
                self.previous_course_data = course_data

# --- HTML Fetching Helpers ---

def fetch_html_with_selenium(url, wait_for_id=None, timeout=15):
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = uc.Chrome(options=options)

    try:
        driver.get(url)
        if wait_for_id:
            WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.ID, wait_for_id)))
        return driver.page_source
    except Exception:
        return driver.page_source
    finally:
        driver.quit()

def fetch_and_save_html(major_url, major_name):
    html = fetch_html_with_selenium(major_url, wait_for_id="programrequirementstextcontainer")
    write_file(get_parse_path(major_name), html)

def guess_course_catalog_url(major_name):
    base_url = f"{BASE_URL}/undergraduate/course-descriptions/"
    major_name = major_name.lower().replace("&", "and")
    words = major_name.split()
    guesses = {words[0], "".join(words), "".join(w[0] for w in words)}

    for i in range(1, 5):
        guesses.add(words[0][:i])

    for prefix in guesses:
        url = f"{base_url}{prefix}/"
        try:
            response = requests.get(url, timeout=10)
            if response.ok:
                soup = BeautifulSoup(response.text, "html.parser")
                # Look for heading that confirms it's the correct page
                heading = soup.find("h1", class_="page-title")
                if heading and words[0] in heading.text.lower():
                    return url, soup
        except Exception:
            continue

    return None, None

def fetch_and_save_course_catalog(major_name):
    catalog_url, soup = guess_course_catalog_url(major_name)
    if catalog_url and soup:
        path = get_parse_path(major_name, "_catalog")
        write_file(path, str(soup))
        return path
    return None

def find_catalog_url_by_degree_number(main_catalog_path, degree_number):
    """Finds the catalog URL for any degree type based on degree number."""
    if not os.path.exists(main_catalog_path):
        return None

    soup = BeautifulSoup(read_file(main_catalog_path), "html.parser")
    for link in soup.find_all("a", href=True):
        if str(degree_number) in link.get_text(strip=True):
            return f"{BASE_URL}{link['href']}/#programrequirementstext"
    return None

# Course Extraction and Insertion 
def extract_all_catalog_courses(html):
    soup = BeautifulSoup(html, "html.parser")
    course_blocks = soup.find_all("div", class_="courseblock")
    extracted_data = []

    for block in course_blocks:
        title_tag = block.find("p", class_="courseblocktitle")
        if not title_tag:
            continue

        title_raw = clean_text(title_tag.get_text(" ", strip=True))
        match_hours = re.search(r"\b(\d+)(?:\s*[-–]\s*\d+)?\s+Hours?", title_raw, re.IGNORECASE)
        hours = int(match_hours.group(1)) if match_hours else 0

        match_code = re.match(r"([A-Z]{2,4} \d{3})", title_raw)
        if not match_code:
            continue

        course_code = normalize_course_name(match_code.group(1))
        hrefs = {
            normalize_code(link.get_text(strip=True)): link["href"]
            for link in block.find_all("a", class_="bubblelink code", href=True)
        }

        prereq = coreq = restrict = terms = ""
        # Look through all extra tags to pull info
        for tag in block.find_all("p", class_="courseblockextra"):
            text = clean_text(tag.get_text(" ", strip=True))
            if "Prerequisite(s):" in text: prereq = clean_text(text.split("Prerequisite(s):", 1)[-1])
            if "Corequisite(s):" in text: coreq = clean_text(text.split("Corequisite(s):", 1)[-1])
            if "Restriction(s):" in text: restrict = clean_text(text.split("Restriction(s):", 1)[-1])
            if "Recent Term(s) Offered:" in text: terms = clean_text(text.split("Recent Term(s) Offered:", 1)[-1])

        colonade, colonade_id = extract_colonnade_info(block)

        extracted_data.append({
            "title": course_code,
            "hours": hours,
            "prerequisites": prereq,
            "corequisites": coreq,
            "restrictions": restrict,
            "recent_terms": terms,
            "colonade": colonade,
            "colonade_id": colonade_id,
            "href": hrefs
        })

    return extracted_data

def extract_courses_from_html(major_name, concentration=None):
    html_path = get_parse_path(major_name)
    if not os.path.exists(html_path):
        return None

    soup = BeautifulSoup(read_file(html_path), "html.parser")
    section = soup.find(id="programrequirementstextcontainer") or soup.find(id="textcontainer")
    if not section:
        return None

    return CourseExtractor(section).parse(concentration)

def insert_courses_into_db(catalog_courses, extracted_courses, major_name):
    try:
        degree = Degree.objects.get(degree_name__icontains=major_name)
    except Degree.DoesNotExist:
        print(f"Degree '{major_name}' not found.")
        return

    # Save all catalog_courses to Course table
    for course in catalog_courses:
        course_info = fetch_course_info(course.get("title")) or course
        get_or_create_course(
            course_name=normalize_course_name(course_info.get("course_name", course.get("title"))),
            hours=course_info.get("hours", course.get("hours", 0)),
            colonade=course_info.get("colonade", False),
            colonade_id=course_info.get("colonade_id"),
            corequisites=course_info.get("corequisites"),
            restrictions=course_info.get("restrictions"),
            recent_terms=course_info.get("recent_terms")
        )

    # Save extracted courses only if not already in Course
    for entry in extracted_courses:
        if entry["type"] != "course" or not is_valid_course(entry["course_number"], entry["course_name"]):
            continue

        course_name = normalize_course_name(entry["course_name"])
        course_info = fetch_course_info(course_name) or entry
        hours = course_info.get("hours", entry.get("hours", 0))
        hours = int(hours) if isinstance(hours, str) and hours.isdigit() else hours

        course_obj, _ = get_or_create_course(
            course_name=course_name,
            hours=hours,
            colonade=course_info.get("colonade", False),
            colonade_id=course_info.get("colonade_id"),
            corequisites=course_info.get("corequisites"),
            restrictions=course_info.get("restrictions"),
            recent_terms=course_info.get("recent_terms")
        )

        # Create link in DegreeCourse
        get_or_create_degree_course(
            course_obj,
            degree,
            is_required=entry.get("is_required", False) if not entry.get("group_id") else False,
            is_elective=entry.get("is_elective", False),
            group_id=entry.get("group_id")
        )

    deduplicate_courses()
    link_course_prerequisites(catalog_courses)

def parse_prerequisite_logic(prereq_text):
    text = prereq_text.replace(",", " , ").replace("(", "").replace(")", "")
    text = text.replace(" and ", " && ").replace(" or ", " || ")
    return [[f"{p} {n}" for p, n in re.findall(r'\b([A-Z]{2,5})\s+(\d{3})\b', part)]
            for part in text.split("&&") if part.strip()]

def link_course_prerequisites(catalog_courses):
    for course_data in catalog_courses:
        course_title = course_data.get("title", "").strip()
        prereq_text = course_data.get("prerequisites", "").strip()
        if not prereq_text:
            continue

        try:
            course_obj = Course.objects.get(course_name=course_title)
        except Course.DoesNotExist:
            continue

        for group in parse_prerequisite_logic(prereq_text):
            for prereq_code in group:
                prereq_obj = Course.objects.filter(course_name__startswith=prereq_code).first()
                if not prereq_obj:
                    info = fetch_course_info(prereq_code)
                    if info:
                        prereq_obj, _ = get_or_create_course(
                            course_name=normalize_course_name(info["course_name"]),
                            hours=info["hours"],
                            colonade=info.get("colonade", False),
                            colonade_id=info.get("colonade_id"),
                            corequisites=info.get("corequisites"),
                            restrictions=info.get("restrictions"),
                            recent_terms=info.get("recent_terms")
                        )
                if prereq_obj:
                    Prerequisites.objects.get_or_create(course=course_obj, prerequisite=prereq_obj)

def is_catalog_already_parsed(degree_name):
    filename = f"{degree_name.replace(' ', '_').lower()}.html"
    return os.path.exists(os.path.join(PARSE_DIR, filename))

def are_courses_already_extracted(degree_name):
    return DegreeCourse.objects.filter(degree__degree_name=degree_name).exists()

def main(student_id):
    try:
        user = User.objects.get(student_id=student_id)
        user_degrees = UserDegree.objects.filter(user_student_id=user)
    except User.DoesNotExist:
        return

    main_catalog_path = os.path.join(PARSE_DIR, "main_catalog.html")
    hardcoded = {
        "nursing": "https://catalog.wku.edu/undergraduate/health-human-services/nursing/nursing-bsn/",
    }

    for ud in user_degrees:
        degree = ud.degree
        degree_name = degree.degree_name
        concentration = degree.concentration
        degree_number = getattr(degree, "degree_number", None)
        if not degree_number:
            continue

        if degree_name.lower().strip() in hardcoded:
            degree_url = hardcoded[degree_name.lower().strip()]
        else:
            degree_url = find_catalog_url_by_degree_number(main_catalog_path, degree_number)
        if not degree_url:
            continue

        if is_catalog_already_parsed(degree_name) and are_courses_already_extracted(degree_name):
            continue

        catalog_path = fetch_and_save_course_catalog(degree_name)
        fetch_and_save_html(degree_url, degree_name)

        catalog_courses = extract_all_catalog_courses(read_file(catalog_path)) if catalog_path else []
        extracted_courses = extract_courses_from_html(degree_name, concentration if degree.degree_type == 1 else None)

        if extracted_courses:
            insert_courses_into_db(catalog_courses, extracted_courses, degree_name)
        else:
            print(f"No courses extracted for {degree_name}")
