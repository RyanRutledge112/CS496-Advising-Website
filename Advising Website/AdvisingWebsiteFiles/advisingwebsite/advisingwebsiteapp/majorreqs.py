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
from advisingwebsiteapp.recommender import parse_instruction_to_course_rule

BASE_URL = "https://catalog.wku.edu"
BASE_CATALOG_URL = f"{BASE_URL}/undergraduate/programs/"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARSE_DIR = os.path.join(BASE_DIR, "Parse")
os.makedirs(PARSE_DIR, exist_ok=True)

# Grabs users major from the db
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

# Clean text from HTML
def clean_text(s):
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()

# Normalize course names and codes 
def normalize_code(code):
    return clean_text(code).upper()

def normalize_course_name(name):
    name = re.sub(r"Option [A-Z]:\s*", "", name)
    return normalize_code(name)

# Get course code from name
def extract_course_code(course_name):
    match = re.match(r'([A-Z]{2,4})\s*0*(\d{2,3}[A-Z]?)', course_name.upper().strip())
    return f"{match.group(1)} {match.group(2)}" if match else course_name.strip()

# Checks if course is valid 
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
    # build href and url 
    href = f"/search/?P={course_name.replace(' ', '%20')}"
    full_url = f"{BASE_URL}{href}"

    try:
        res = requests.get(full_url, timeout=10)
        res.raise_for_status()
    except Exception:
        return None

    # parse html 
    soup = BeautifulSoup(res.text, "html.parser")
    # find block that contains course info
    block = soup.find("div", class_="searchresult search-courseresult")
    if not block or not block.find("h2"):
        return None

    header = re.sub(r"[\s\xa0]+", " ", block.find("h2").get_text(" ", strip=True))
    # Example: CS 360 Software Engineering I 3 Hours 
    match = re.match(r"^([A-Z]+ \d+)\s+(.*?)\s+(\d+)(?:[-–]\d+)?\s+Hour[s]?", header)
    if not match:
        return None

    course_code, title, hours = match.group(1), match.group(2), int(match.group(3))
    full_text = block.find("p", class_="search-summary").get_text(" ", strip=True) if block.find("p", class_="search-summary") else ""

    # Get extra fields under course info
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

# Grab or Create Course object using Django ORM
def get_or_create_course(course_name, hours=0, colonade=False, colonade_id=None,
                         corequisites=None, restrictions=None, recent_terms=None):
    # normalize name and code 
    course_name = normalize_course_name(course_name)
    normalized_code = extract_course_code(course_name)
    
    # check if exisiting Course matches 
    course = next((c for c in Course.objects.all() if extract_course_code(c.course_name) == normalized_code), None)
    # default for col
    colonade = False if colonade is None else colonade

    if course:
        # if Course already exists update fields if needed
        updated = False
        if course.hours == 0 and hours: course.hours, updated = hours, True
        if not course.is_colonade and colonade: course.is_colonade, course.colonade_id, updated = colonade, colonade_id, True
        if not course.corequisites and corequisites: course.corequisites, updated = corequisites, True
        if not course.restrictions and restrictions: course.restrictions, updated = restrictions, True
        if not course.recent_terms and recent_terms: course.recent_terms, updated = recent_terms, True
        if updated: course.save()
        return course, False
    else:
        # create new Course object if not found 
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

# Grab or Create DegreeCourse object using Django ORM
def get_or_create_degree_course(course_obj, degree_obj, is_required=False, is_elective=False, group_id=None):
    # check if there is already exisiting degreeecourse
    # create new if not
    obj, created = DegreeCourse.objects.get_or_create(
        course=course_obj,
        degree=degree_obj,
        defaults={"is_required": is_required, "is_elective": is_elective, "group_id": group_id}
    )
    
    # debugging
    if created:
        print(f"Created DegreeCourse for {course_obj.course_name} under {degree_obj.degree_name}")
    else:
        print(f"DegreeCourse already exists for {course_obj.course_name} under {degree_obj.degree_name}")
    
    return obj

# Deduplicate courses in db
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
        # initialize extractor with sections to work
        self.section = section
        self.extracted_courses = []
        self.current_required = False
        self.current_elective = False
        self.current_category = None
        self.should_stop = False

        # grouping related 
        self.group_mode = False
        self.current_group_id = None
        self.previous_course_data = None

    def parse(self, concentration=None):
        elements = self._get_starting_point(concentration)

        try:
            for elem in elements:
                if self.should_stop:
                    continue

                if elem.name == "h3" and "faculty" in elem.get_text(strip=True).lower():
                    continue

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

                # extract courses if course table found 
                if elem.name == "table" and "sc_courselist" in elem.get("class", []):
                    self._extract_table_courses(elem)

            return list(self.extracted_courses)

        except Exception as e:
            print(f"Exception: {e}")

    # get starting point based on concentration 
    def _get_starting_point(self, concentration=None):
        if concentration:
            # Normalize the concentration for matching
            norm_conc = re.sub(r"\s*\(.*?\)", "", concentration).strip().lower()
            for h3 in self.section.find_all("h3"):
                h3_text = h3.get_text(strip=True).lower()

                # Try matching cleaned version
                if norm_conc == h3_text or norm_conc in h3_text:
                    return h3.find_all_next()

            return []

        # No concentration: look for Program/Admission Requirements
        for elem in self.section.find_all():
            if elem.name == "h2":
                header = elem.get_text(strip=True).lower()
                if "program requirements" in header or "admission requirements" in header:
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

    # start new group when keywords found 
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

    # parse thorugh the courses table 
    def _extract_table_courses(self, table):
        if not isinstance(table, Tag):
            return

        stop_heading = "MEPN Second Degree Undergraduate Coursework"

        for row in table.find_all("tr"):
            # handles header rows in table
            header_span = row.find("span", class_="courselistcomment areaheader")
            if header_span:
                header_text = header_span.get_text(strip=True)
                if header_text == stop_heading:
                    break
                self._update_flags_from_header(header_text)
                continue
            
            # handles instructions
            if row.find("span", class_="courselistcomment"):
                self._reset_grouping()
                self._start_new_group(row.get_text(strip=True))
                instruction_text = clean_text(row.get_text(strip=True))
                instruction_data = {
                    "type": "instruction",
                    "text": instruction_text,
                    "group_id": self.current_group_id,
                    "hours": getattr(self, "shared_hours", None),
                    "is_required": self.current_required,
                    "is_elective": self.current_elective
                }
                self.extracted_courses.append(instruction_data)
                continue

            cols = row.find_all("td")
            if len(cols) < 2:
                continue
            
            # get basic course info
            course_number_raw = clean_text(cols[0].get_text())
            course_number_raw = re.sub(r"^\s*or\s+", "", course_number_raw, flags=re.IGNORECASE)  
            course_name_raw = clean_text(cols[1].get_text())
            credit_hours = clean_text(cols[2].get_text()) if len(cols) > 2 else ""
            course_href = cols[0].find("a", href=True)["href"] if cols[0].find("a", href=True) else None

            # handle multiple course/code names with split 
            course_numbers = [normalize_code(c) for c in re.split(r"&|,", course_number_raw)]
            
            split_names = [s.strip() for s in cols[1].stripped_strings if s.strip()]
            split_names = [n for n in split_names if not n.lower().startswith(('and', '&'))] 

            if len(split_names) == len(course_numbers):
                course_names = split_names
            else:
                course_names = [course_name_raw] * len(course_numbers)

            if len(course_numbers) != len(course_names):
                print(f"DEBUG: Mismatched course_numbers ({course_numbers}) and course_names ({course_names})")

            # process each course 
            for i in range(len(course_numbers)):
                course_number = course_numbers[i]
                course_name = course_names[i]
                full_course_name = normalize_course_name(f"{course_number} {course_name}")

                if not is_valid_course(course_number, full_course_name):
                    continue
                
                # get missing course info if needed
                if not credit_hours or str(credit_hours).lower() == "n/a":
                    info = fetch_course_info(full_course_name)
                    credit_hours = info["hours"] if info else "N/A"
                    colonade = info.get("colonade", False)
                    colonade_id = info.get("colonade_id", None)
                else:
                    colonade = colonade_id = None

                # handle grouping logic 
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

# gets/loads dynamic html pages 
def fetch_html_with_selenium(url, wait_for_id=None, timeout=15):
    # set up chrome options
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

# Get full html and save html to file
def fetch_and_save_html(major_url, major_name):
    html = fetch_html_with_selenium(major_url, wait_for_id="programrequirementstextcontainer")
    write_file(get_parse_path(major_name), html)

# Guesses possible urls for each major
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

# get url and save catalog 
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
    # find course blocks 
    course_blocks = soup.find_all("div", class_="courseblock")
    extracted_data = []

    for block in course_blocks:
        # Example: CS 180 Intro to Computer Science 3 Hours 
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
        # grab all hrefs link inside course block to connect to prepreqs
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

# Get courses from html for degree specific courses 
def extract_courses_from_html(major_name, concentration=None):
    # build html path
    html_path = get_parse_path(major_name)
    if not os.path.exists(html_path):
        return 

    soup = BeautifulSoup(read_file(html_path), "html.parser")
    # find correct section
    section = soup.find(id="programrequirementstextcontainer") or soup.find(id="textcontainer")
    if not section:
        return None

    # intialize and parse courses 
    extractor = CourseExtractor(section)
    parsed = extractor.parse(concentration)

    return extractor.extracted_courses, parsed

# inserted all courses into db
def insert_courses_into_db(catalog_courses, extracted_courses, degree):
    # Save all catalog_courses to Course table
    for course in catalog_courses:
        # get course info from web
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
        # get course info 
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

# link prereqs to its corresponding course 
def link_course_prerequisites(catalog_courses):
    # check each course 
    for course_data in catalog_courses:
        course_title = course_data.get("title", "").strip()
        prereq_text = course_data.get("prerequisites", "").strip()
        if not prereq_text:
            continue
        
        try:
            course_obj = Course.objects.get(course_name=course_title)
        except Course.DoesNotExist:
            continue

        # seperate into groups 
        parsed_groups = parse_prerequisite_logic(prereq_text)

        for group in parsed_groups:
            group_id = str(uuid.uuid4())  
            for prereq_code in group:
                # find prereq in db
                prereq_obj = Course.objects.filter(course_name__startswith=prereq_code).first()
                if not prereq_obj:
                    # if not found,fetch dynamically
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
                    # link prereq course to course 
                    Prerequisites.objects.get_or_create(
                        course=course_obj,
                        prerequisite=prereq_obj,
                        defaults={"group_id": group_id}  
                    )

def is_catalog_already_parsed(degree_name):
    filename = f"{degree_name.replace(' ', '_').lower()}.html"
    return os.path.exists(os.path.join(PARSE_DIR, filename))

def are_courses_already_extracted(degree_obj):
    return DegreeCourse.objects.filter(degree=degree_obj).exists()

def main(student_id):
    try:
        # look up user 
        user = User.objects.get(student_id=student_id)
        user_degrees = UserDegree.objects.filter(user_student_id=user)
    except User.DoesNotExist:
        return

    main_catalog_path = os.path.join(PARSE_DIR, "main_catalog.html")
    hardcoded = {
        "nursing": "https://catalog.wku.edu/undergraduate/health-human-services/nursing/nursing-bsn/",
    }

    all_extracted_courses = []
    all_instructional_entries = []

    for ud in user_degrees:
        degree = ud.degree
        degree_name = degree.degree_name
        concentration = degree.concentration
        degree_number = getattr(degree, "degree_number", None)
        if not degree_number:
            continue
        
        # get degree url
        if degree_name.lower().strip() in hardcoded:
            degree_url = hardcoded[degree_name.lower().strip()]
        else:
            degree_url = find_catalog_url_by_degree_number(main_catalog_path, degree_number)
        if not degree_url:
            continue
        
        # skip parsing if catalog already done and courses extracted 
        if is_catalog_already_parsed(degree_name) and are_courses_already_extracted(degree):
            continue
        
        catalog_path = fetch_and_save_course_catalog(degree_name)
        fetch_and_save_html(degree_url, degree_name)

        catalog_courses = extract_all_catalog_courses(read_file(catalog_path)) if catalog_path else []
        extracted_courses, instructional_entries = extract_courses_from_html(degree_name, concentration)

        # insert courses into db if not already there
        if not are_courses_already_extracted(degree) and extracted_courses:
            insert_courses_into_db(catalog_courses, extracted_courses, degree)
        else:
            print(f"Skipping course insertion for {degree_name}, already exists or empty")

        if extracted_courses:
            all_extracted_courses.extend(extracted_courses)
        else:
            print(f"Warning: extracted_courses is None or empty for {degree_name}")
        
        if instructional_entries:
            all_instructional_entries.extend(instructional_entries)
        else:
            print(f"Warning: instructional_entries is None for {degree_name}")

    parsed_rules = []
    for entry in all_instructional_entries:
        if entry.get("type") == "instruction":
            subject_match = re.search(r"\b([A-Z]{2,4})\s*\d{3}", entry.get("text", ""))
            subject = subject_match.group(1) if subject_match else "None"  
            rules = parse_instruction_to_course_rule(entry.get("text", ""), subject)
            parsed_rules.extend(rules)

    return {
        "courses": all_extracted_courses,
        "instructions": all_instructional_entries,
        "instructional_rules": parsed_rules
    }

