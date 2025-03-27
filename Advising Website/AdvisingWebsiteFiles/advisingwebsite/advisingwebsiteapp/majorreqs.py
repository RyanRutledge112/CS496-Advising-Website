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

BASE_CATALOG_URL = "https://catalog.wku.edu/undergraduate/programs/"

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
PARSE_DIR = os.path.join(BASE_DIR, "Parse")
os.makedirs(PARSE_DIR, exist_ok=True) 

def get_parse_path(name, suffix="", ext="html"):
    # Joins cleaned file name into the Parse dir
    return os.path.join(PARSE_DIR, get_safe_filename(name, suffix, ext))

def get_safe_filename(name, suffix="", ext="html"):
    # Cleans and returns file name
    safe_name = re.sub(r"[^\w]+", "_", name.strip())
    safe_name = re.sub(r"_+", "_", safe_name).strip("_")
    return f"{safe_name}{suffix}.{ext}"

def read_file(path, mode="r"):
    with open(path, mode, encoding="utf-8" if "b" not in mode else None) as f:
        return f.read()

def write_file(path, content, mode="w"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode, encoding="utf-8" if "b" not in mode else None) as f:
        f.write(content)

def extract_colonnade_info(root_tag):
    # Extracts Colonnade status and code from content
    colonade = False
    colonade_id = None

    # Look inside all <p class="courseblockdesc"> and <strong> tags
    desc_tag = root_tag.find("p", class_="courseblockdesc")
    if desc_tag:
        for strong in desc_tag.find_all("strong"):
            text = strong.get_text(" ", strip=True)
            if "colonnade" in text.lower():
                colonade = True
                match = re.search(r"Code\s*([A-Z0-9\-]+)", text)
                if match:
                    colonade_id = match.group(1).strip()

    # Also check <p class="courseblockextra">
    for extra_tag in root_tag.find_all("p", class_="courseblockextra"):
        text = extra_tag.get_text(" ", strip=True)
        if "colonnade" in text.lower():
            colonade = True
            match = re.search(r"Code\s*([A-Z0-9\-]+)", text)
            if match:
                colonade_id = match.group(1).strip()

    return colonade, colonade_id

def get_credit_hours_and_colonnade(course_href):
    # Fetches credit hours and colonnade info from a course description page
    if not course_href:
        return "N/A", False, None

    try:
        full_url = f"https://catalog.wku.edu{course_href}"
        response = requests.get(full_url, timeout=10)
        if response.status_code != 200:
            return "N/A", False, None

        soup = BeautifulSoup(response.text, "html.parser")

        credit_hours = None
        for tag in soup.find_all(["b", "strong"]):
            if "hour" in tag.text.lower():
                match = re.search(r"(\d+)\s+(credit\s+)?hours?", tag.text, re.IGNORECASE)
                if match:
                    credit_hours = match.group(1)
                    break

        if not credit_hours:
            page_text = soup.get_text(separator=" ", strip=True)
            match = re.search(r"(\d+)\s+(credit\s+)?hours?", page_text, re.IGNORECASE)
            if match:
                credit_hours = match.group(1)

        colonade, colonade_id = extract_colonnade_info(soup)
        return credit_hours or "N/A", colonade, colonade_id

    except Exception as e:
        print(f"[Error] Failed to fetch from {course_href}: {e}")
        return "N/A", False, None

def normalize_course_name(name):
    return re.sub(r"Option [A-Z]:\s*", "", name).strip()

def normalize_code(code):
    return re.sub(r"\s+", " ", code.replace("\xa0", " ")).strip().upper()

def is_valid_course(course_number, course_name):
    if not course_number or not course_name:
        return False
    if course_number.lower().startswith("or "):
        return True  
    if "select" in course_number.lower():
        return False
    if "one of the following" in course_name.lower():
        return False
    
    # Accept things like PSY/PSYS 220
    if re.match(r"[A-Z]{2,5}/?[A-Z]{0,5}\s?\d{3}", course_number):
        return True
    return False

def get_or_create_course(course_name, hours=0, colonade=False, colonade_id=None):
    course_name = course_name.strip()
    return Course.objects.get_or_create(
        course_name=course_name,
        defaults={
            "hours": hours,
            "is_colonade": colonade,
            "colonade_id": colonade_id
        }
    )

def get_or_create_degree_course(course_obj, degree_obj, is_required=False, is_elective=False):
    return DegreeCourse.objects.get_or_create(
        course=course_obj,
        degree=degree_obj,
        defaults={
            "is_required": is_required,
            "is_elective": is_elective
        }
    )

def get_user_major(student_id):
    try:
        user = User.objects.get(student_id=student_id)
        user_degrees = UserDegree.objects.filter(user_student_id=user)

        for ud in user_degrees:
            if ud.degree.degree_type == 1:
                major_name = ud.degree.degree_name.split(",")[0].replace("Major: ", "").strip()
                return major_name

        return None 
    except User.DoesNotExist:
        return None

class CourseExtractor:
    def __init__(self, section):
        self.section = section
        self.extracted_courses = []
        self.current_required = False
        self.current_elective = False
        self.current_category = None

        self.group_mode = False
        self.group_hours = None
        self.last_known_hours = None
        self.current_group_id = None
        self.current_indent_level = None
        self.previous_course_data = None

    def parse(self, concentration=None):
        elements_to_iterate = self._get_starting_point(concentration)
        for elem in elements_to_iterate:
            if elem.name in ["h2", "h3", "tr"]:
                text = elem.get_text(strip=True).lower()
                if "required" in text:
                    self._update_flags_from_header(text)

        for elem in elements_to_iterate:
            if elem.name == "h3" and "faculty" in elem.get_text(strip=True).lower():
                break

            if elem.name == "tr" and "areaheader" in elem.get("class", []):
                self._reset_grouping()
                self._update_flags_from_header(elem.get_text(strip=True).lower())
                continue

            if elem.name == "tr" and elem.find("span", class_="courselistcomment"):
                self._reset_grouping()
                self._start_new_group(elem.get_text(strip=True), elem)
                continue

            if elem.name == "table" and "sc_courselist" in elem.get("class", []):
                self._extract_table_courses(elem)

        return self.extracted_courses

    def _get_starting_point(self, concentration):
        if concentration:
            concentration_lower = concentration.lower()
            valid_headings = [
                f"{concentration_lower} concentration",
                f"{concentration_lower} option",
                f"{concentration_lower} track"
            ]
            for h3 in self.section.find_all("h3"):
                heading = h3.get_text().strip().lower()
                if any(valid in heading for valid in valid_headings):
                    return h3.find_all_next()
            print(f"Concentration '{concentration}' not found.")
            return []
        else:
            # Try to find the "General" or "All" concentration section
            for h3 in self.section.find_all("h3"):
                heading = h3.get_text().strip().lower()
                if any(keyword in heading for keyword in ["general", "all", "core", "undesignated"]):
                    return h3.find_all_next()
            
            # If nothing matches, fallback to everything 
            return self.section.find_all()

    def _reset_grouping(self):
        self.group_mode = False
        self.group_hours = None
        self.last_known_hours = None
        self.current_group_id = None
        self.current_indent_level = None
        self.previous_course_data = None

    def _update_flags_from_header(self, header_text):
        self.current_category = header_text
        header_text = header_text.lower()

        required_keywords = ["core", "required", "requirement", "additional requirement"]
        elective_keywords = ["elective", "electives"]

        self.current_required = any(word in header_text for word in required_keywords)
        self.current_elective = any(word in header_text for word in elective_keywords)

        # Fallback: if neither was triggered, but "required" is present
        if not self.current_required and "required" in header_text:
            self.current_required = True

        if self.current_required and self.current_elective:
            self.current_elective = False  

    def _start_new_group(self, comment, row_elem):
        comment_lower = comment.lower()
        if any(kw in comment_lower for kw in ["select", "choose", "one of the following", "two from the following", "hours from the following"]):
            self.group_mode = True
            self.current_category = comment
            self.current_group_id = str(uuid.uuid4())
            self._add_instruction_entry(comment)

    def _extract_credit_hours(self, text):
        match = re.search(r'(\d+)\s+hours?', text.lower())
        return int(match.group(1)) if match else None

    def _get_indent_level(self, row):
        indent = row.find("div", class_="blockindent")
        if indent:
            return 1
        return 0

    def _add_instruction_entry(self, text):
        self.extracted_courses.append({
            "course_number": text,
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

        last_course_data = None
        stop_heading = "MEPN Second Degree Undergraduate Coursework"

        for row in table.find_all("tr", class_=lambda c: c in ["even", "odd", "orclass"]):
            header_span = row.find("span", class_="courselistcomment areaheader")
            if header_span:
                header_text = header_span.get_text(strip=True)
                if header_text == stop_heading:
                    break
                self._update_flags_from_header(header_text)
                continue

            # If we hit a new instruction mid-table, start a new group
            if row.find("span", class_="courselistcomment"):
                self._reset_grouping()
                self._start_new_group(row.get_text(strip=True), row)
                continue

            is_or_row = "orclass" in row.get("class", [])

            cols = row.find_all("td")
            if len(cols) < 2:
                continue

            course_number = cols[0].get_text(strip=True).replace("\xa0", " ")
            href_tag = cols[0].find("a", href=True)
            course_href = href_tag["href"] if href_tag else None
            course_name = cols[1].get_text(strip=True)
            credit_hours = cols[2].get_text(strip=True) if len(cols) > 2 else ""

            note = "or" if is_or_row else self.current_category

            colonade = False
            colonade_id = None

            if not credit_hours or credit_hours.lower() == "n/a":
                credit_hours, colonade, colonade_id = get_credit_hours_and_colonnade(course_href)
            else:
                colonade = False
                colonade_id = None
            self.last_known_hours = credit_hours

            if course_number.strip().lower().startswith("or") and len(course_number.split()) >= 2:
                course_number = course_number.split("or", 1)[-1].strip()

            # Apply classification from the last known valid header
            if is_valid_course(course_number, course_name):
                is_required = self.current_required
                is_elective = self.current_elective
            else:
                is_required = False
                is_elective = False

            course_data = {
                "course_number": course_number,
                "course_name": course_name,
                "hours": credit_hours,
                "course_href": course_href,
                "is_required": is_required,
                "is_elective": is_elective,
                "note": note,
                "type": "course" if is_valid_course else "instruction",
                "colonade": colonade,
                "colonade_id": colonade_id
            }

            is_block_indented = row.find("div", class_="blockindent") is not None

            if is_or_row and last_course_data:
                or_group_id = str(uuid.uuid4())
                last_course_data["group_id"] = or_group_id
                course_data["group_id"] = or_group_id
            elif self.group_mode and is_block_indented:
                course_data["group_id"] = self.current_group_id
            else:
                self._reset_grouping()

            self.extracted_courses.append(course_data)

            if is_valid_course:
                last_course_data = course_data

def fetch_html_with_selenium(url, wait_for_id=None, timeout=15):
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = uc.Chrome(options=options)

    try:
        driver.get(url)
        if wait_for_id:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.ID, wait_for_id))
            )
        return driver.page_source
    except Exception as e:
        return driver.page_source  
    finally:
        driver.quit()

def fetch_and_save_html(major_url, major_name):
    html = fetch_html_with_selenium(major_url, wait_for_id="programrequirementstextcontainer")
    html_path = get_parse_path(major_name)
    write_file(html_path, html)

def fetch_and_save_course_catalog(major_name):
    catalog_url, soup = guess_course_catalog_url(major_name)
    
    if not catalog_url or not soup:
        return None

    # Normalize major name to safe file name
    safe_name = re.sub(r"_+", "_", major_name.strip().replace(" ", "_").replace(":", ""))
    safe_name = safe_name.rstrip("_")

    html_path = os.path.join(PARSE_DIR, f"{safe_name.replace(' ', '_')}_catalog.html")
    
    write_file(html_path, str(soup))
    
    print(f"Catalog HTML saved to {html_path}")
    return html_path

def fetch_course_from_href(base_url, href):
    full_url = base_url + href
    
    try:
        response = requests.get(full_url)
        response.raise_for_status()
    except Exception as e:
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    # Case 1: Catalog-style block
    block = soup.find("div", class_="courseblock")
    if block:
        title_tag = block.find("p", class_="courseblocktitle")
        if title_tag:
            title = title_tag.get_text(" ", strip=True)
            match = re.search(r"\b(\d+)(?:\s*[-–]\s*\d+)?\s+Hours?$", title, flags=re.IGNORECASE)
            hours = int(match.group(1)) if match else 0
            title_cleaned = re.sub(r"\s*\d+(\s*[-–]\s*\d+)?\s+Hours?$", "", title, flags=re.IGNORECASE)
            desc_tag = block.find("p", class_="courseblockdesc")
            full_text = desc_tag.get_text(" ", strip=True) if desc_tag else ""
            return {
                "course_name": title_cleaned.strip(),
                "hours": hours,
                "description": full_text,
            }
    
    # Fallback: search result page
    search_block = soup.find("div", class_="searchresult search-courseresult")
    if search_block:
        h2 = search_block.find("h2")
        if not h2:
            print(f"⚠️ No <h2> tag found in searchresult for {href}")
            return None

        # Normalize all whitespace
        title_text = h2.get_text(" ", strip=True)
        title_text = re.sub(r"[\s\xa0]+", " ", title_text)

        match = re.match(r"^([A-Z]+ \d+)\s+(.*?)\s+(\d+)(?:[-–]\d+)?\s+Hour[s]?", title_text)
        if not match:
            return None

        code = match.group(1)
        name = match.group(2)
        hours = int(match.group(3))
        course_name = f"{code}    {name}"

        desc_tag = search_block.find("p", class_="search-summary")
        desc = desc_tag.get_text(" ", strip=True) if desc_tag else ""

        return {
            "course_name": course_name.strip(),
            "hours": hours,
            "description": desc
        }

    return None

def fetch_and_add_prereq_course(course_code, all_hrefs):
    base_url = "https://catalog.wku.edu"
    normalized = normalize_code(course_code)

    href = all_hrefs.get(normalized)
    if href:
        result = fetch_course_from_href(base_url, href)
        if result:
            name = result["course_name"]
            hours = result["hours"]
            Course.objects.get_or_create(
                course_name=name,
                defaults={"hours": hours, "is_colonade": False, "colonade_id": None}
            )
            return True

    return False

def find_catalog_url_by_degree_number(main_catalog_path, degree_number):
    """Finds the catalog URL for any degree type based on degree number."""
    if not os.path.exists(main_catalog_path):
        return None

    with open(main_catalog_path, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")

    for link in soup.find_all("a", href=True):
        text = link.get_text(strip=True)
        if str(degree_number) in text:
            url = "https://catalog.wku.edu" + link["href"] + "/#programrequirementstext"  
            return url 
    return None

def guess_course_catalog_url(major_name):
    base_url = "https://catalog.wku.edu/undergraduate/course-descriptions/"
    major_name = major_name.lower().replace("&", "and")
    words = major_name.split()
    guesses = set()

    # Try first full word
    guesses.add(words[0])

    # Try 1-4 letter prefixes
    for i in range(1, 5):
        guesses.add(words[0][:i])

    # Try initials 
    initials = "".join(word[0] for word in words)
    guesses.add(initials)

    # Cleaned version 
    guesses.add("".join(words))

    for prefix in guesses:
        url = f"{base_url}{prefix}/"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, "html.parser")

            # Look for heading that confirms it's the correct page
            heading = soup.find("h1", class_="page-title")
            if heading and major_name.split()[0] in heading.text.lower():
                return url, soup
        except Exception as e:
            print(f"Failed to fetch {url} → {e}")

    return None, None

# Course Extraction and Insertion 
def extract_all_catalog_courses(html):
    soup = BeautifulSoup(html, "html.parser")
    course_blocks = soup.find_all("div", class_="courseblock")
    extracted_data = []

    for block in course_blocks:
        title_tag = block.find("p", class_="courseblocktitle")
        if not title_tag:
            continue
        hrefs = {}
        for link in block.find_all("a", class_="bubblelink code", href=True):
            raw_code = link.get_text(strip=True).replace("\xa0", " ").strip()
            href = link["href"]
            if raw_code and href:
                normalized = normalize_code(raw_code)
                hrefs[normalized] = href
        title = title_tag.get_text(" ", strip=True)
        match = re.search(r"\b(\d+)(?:\s*[-–]\s*\d+)?\s+Hours?$", title, flags=re.IGNORECASE)
        hours = int(match.group(1)) if match else 0
        title_cleaned = re.sub(r"\s*\d+(\s*[-–]\s*\d+)?\s+Hours?$", "", title, flags=re.IGNORECASE)

        prereq = restrict = terms = ""
        colonade = False
        colonade_id = None

        # Look through all extra tags to pull info
        extra_tags = block.find_all("p", class_="courseblockextra")
        for tag in extra_tags:
            text = tag.get_text(" ", strip=True)

            if "Prerequisite(s):" in text:
                prereq = text.split("Prerequisite(s):", 1)[-1].strip()
            if "Restriction(s):" in text:
                restrict = text.split("Restriction(s):", 1)[-1].strip()
            if "Recent Term(s) Offered:" in text:
                terms = text.split("Recent Term(s) Offered:", 1)[-1].strip()

        colonade, colonade_id = extract_colonnade_info(block)

        extracted_data.append({
            "title": title_cleaned,
            "hours": hours,
            "prerequisites": prereq,
            "restrictions": restrict,
            "recent_terms": terms,
            "colonade": colonade,
            "colonade_id": colonade_id,
            "href": hrefs
        })

    return extracted_data

def extract_courses_from_html(major_name, concentration=None):
    html_path = os.path.join(PARSE_DIR, f"{major_name.replace(' ', '_')}.html")

    if not os.path.exists(html_path):
        return None

    soup = BeautifulSoup(read_file(html_path), "html.parser")

    section = soup.find(id="programrequirementstextcontainer")
    if not section:
        # Fallback for certificate or non-standard pages
        section = soup.find(id="textcontainer")
    if not section:
        return None

    extractor = CourseExtractor(section)
    extracted_courses = extractor.parse(concentration)

    # Will need for recommender
    # group_map = defaultdict(list)
    # for item in extracted_courses:
    #     if item.get("group_id"):
    #         group_map[item["group_id"]].append(item)

    return extracted_courses

def insert_courses_into_db(catalog_courses, extracted_courses, major_name):
    try:
        degree = Degree.objects.get(degree_name__icontains=major_name)

        # Save all catalog_courses to Course table
        for course in catalog_courses:
            title = course.get("title", "").strip()
            colonade = course.get("colonade", False)
            colonade_id = course.get("colonade_id", None)

            hours = course.get("hours", 0)

            Course.objects.get_or_create(
                course_name=title,
                defaults={
                    "hours": hours,
                    "is_colonade": colonade,
                    "colonade_id": colonade_id
                }
            )

        # Save extracted courses only if not already in Course
        for i, entry in enumerate(extracted_courses, start=1):
            if entry["type"] != "course":
                continue

            if not is_valid_course(entry["course_number"], entry["course_name"]):
                continue

            course_name = normalize_course_name(entry["course_name"])
            hours = int(entry["hours"]) if entry["hours"].isdigit() else 0
            colonade = entry.get("colonade", False)
            colonade_id = entry.get("colonade_id", None)

            course_obj, created = get_or_create_course(course_name, hours, colonade, colonade_id)

            is_required = False if entry.get("group_id") else entry["is_required"]

            # Create link in DegreeCourse
            dc_obj, dc_created = get_or_create_degree_course(course_obj, degree, is_required, entry["is_elective"])

    except Degree.DoesNotExist:
        print(f" Degree '{major_name}' not found in the database.")

def is_catalog_already_parsed(degree_name):
    filename = f"{degree_name.replace(' ', '_').lower()}.html"
    filepath = os.path.join(PARSE_DIR, filename)
    return os.path.exists(filepath)

def are_courses_already_extracted(degree_name):
    return DegreeCourse.objects.filter(degree__degree_name=degree_name).exists()

def parse_prerequisite_logic(prereq_text):
    prereq_text = prereq_text.replace(",", " ,") 
    prereq_text = prereq_text.replace("(", "").replace(")", "")
    prereq_text = prereq_text.replace(" and ", " && ").replace(" or ", " || ")

    and_parts = prereq_text.split("&&")
    result = []

    for part in and_parts:
        courses = re.findall(r'\b([A-Z]{2,5})\s+(\d{3})\b', part)
        course_list = [f"{prefix} {num}" for prefix, num in courses]
        if course_list:
            result.append(course_list)

    return result

def link_course_prerequisites(catalog_courses):
    all_hrefs = {}
    for entry in catalog_courses:
        href_dict = entry.get("href", {})
        if not isinstance(href_dict, dict):
            continue
        for raw_code, href in href_dict.items():
            norm_code = normalize_code(raw_code)
            all_hrefs[norm_code] = href

    for course_data in catalog_courses:
        course_title = course_data.get("title", "").strip()
        prereq_text = course_data.get("prerequisites", "").strip()

        if not prereq_text:
            continue

        try:
            course_obj = Course.objects.get(course_name=course_title)
        except Course.DoesNotExist:
            continue

        prereq_groups = parse_prerequisite_logic(prereq_text)

        for group in prereq_groups:
            for prereq_code in group:
                prereq_obj = Course.objects.filter(course_name__startswith=prereq_code).first()

                # Try fetching if not found
                if not prereq_obj:
                    if fetch_and_add_prereq_course(prereq_code, all_hrefs):
                        prereq_obj = Course.objects.filter(course_name__startswith=prereq_code).first()

                # Link if found after fetch
                if prereq_obj:
                    Prerequisites.objects.get_or_create(
                        course=course_obj,
                        prerequisite=prereq_obj
                    )
        # if "concurrent" in prereq_text.lower():
        #     print(f"'{course_title}' has a concurrent prerequisite: {prereq_text}")

def main(student_id):
    try:
        user = User.objects.get(student_id=student_id)
        user_degrees = UserDegree.objects.filter(user_student_id=user)
    except User.DoesNotExist:
        return

    if not user_degrees:
        return

    main_catalog_path = os.path.join(PARSE_DIR, "main_catalog.html")

    HARDCODED_CATALOG_URLS = {
        "nursing": "https://catalog.wku.edu/undergraduate/health-human-services/nursing/nursing-bsn/",
    }

    for user_degree in user_degrees:
        degree = user_degree.degree
        degree_name = degree.degree_name
        degree_type = degree.degree_type
        concentration = degree.concentration
        degree_number = getattr(degree, "degree_number", None) 

        if degree_type in [1, 2, 3]: 
            if not degree_number:
                continue

            if degree_name.lower().strip() in HARDCODED_CATALOG_URLS:
                degree_url = HARDCODED_CATALOG_URLS[degree_name.lower().strip()]
            else:
                degree_url = find_catalog_url_by_degree_number(main_catalog_path, degree_number)

        if not degree_url:
            # print(f" URL not resolved for {degree_name}")
            continue
        
        if is_catalog_already_parsed(degree_name) and are_courses_already_extracted(degree_name):
            # print(f"Courses for {degree_name} already extracted, skipping.")
            continue
        
        catalog_file_path = get_parse_path(degree_name, "_catalog")

        if degree_type == 1:
            if not os.path.exists(catalog_file_path):
                fetch_and_save_course_catalog(degree_name)

        # Always fetch degree-specific HTML (overwrite if exists)
        fetch_and_save_html(degree_url, degree_name)

        # Extract full course descriptions from catalog page
        catalog_courses = [] 

        try:
            catalog_html = read_file(catalog_file_path)
            catalog_courses = extract_all_catalog_courses(catalog_html)
            print(f"Total catalog_courses found: {len(catalog_courses)}")
        except Exception as e:
            print(f"error reading catalog HTML for {degree_name}: {e}")

        # Extract courses
        # If it's a major (1), pass concentration; if minor/certificate (2/3), skip it
        concentration_safe = concentration if degree.degree_type == 1 else None
        courses = extract_courses_from_html(degree_name, concentration_safe)
        for c in courses:
            if c["type"] == "course":
                number = c.get("course_number", "").strip()
                name = c.get("course_name", "").strip()
                if number and name:
                    c["course_name"] = f"{number} {name}"
        if courses:
            insert_courses_into_db(catalog_courses, courses, degree_name)
            link_course_prerequisites(catalog_courses)
        else:
            print(f" No courses extracted for {degree_name}")
