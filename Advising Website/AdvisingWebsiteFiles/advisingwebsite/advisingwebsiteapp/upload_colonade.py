# use this to insert colonade courses from colonade.pdf which has every single colonade course

code = r'''
import pdfplumber
import re
from advisingwebsiteapp.models import Course
from advisingwebsiteapp.majorreqs import fetch_course_info, normalize_course_name 

PDF_PATH = "/Users/pahmeh/Desktop/MehPah/CS496-Advising-Website/Advising Website/AdvisingWebsiteFiles/advisingwebsite/advisingwebsiteapp/colonade.pdf"

def import_colonnade_courses(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_matches = 0
            inserted = 0
            updated = 0
            skipped = 0
            language_inserted = 0

            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if not text:
                    continue

                lines = text.split('\n')
                j = 0
                while j < len(lines):
                    line = lines[j].strip()

                    match = re.match(
                        r'^([A-Z]{2,4})\s+(\d{3}[A-Z]?)\s+(.+?)\s+(\d+\.\d{2})\s+\d{6}\s+([A-Z0-9\-& ]+)',
                        line
                    )

                    if match:
                        subj, num, title, hours, colonade_id = match.groups()
                        course_name = normalize_course_name(f"{subj} {num}")
                        hours_int = int(float(hours))

                        if colonade_id == "F-W":
                            after_fw = line.split("F-W", 1)[1].strip()
                            num_match = re.match(r'(\d)', after_fw)
                            if num_match:
                                colonade_id += num_match.group(1)

                        obj, created = Course.objects.get_or_create(
                            course_name=course_name,
                            defaults={
                                "hours": hours_int,
                                "is_colonade": True,
                                "colonade_id": colonade_id.strip()
                            }
                        )

                        if not created:
                            updated_flag = False
                            if obj.hours == 0:
                                obj.hours = hours_int
                                updated_flag = True
                            if not obj.is_colonade:
                                obj.is_colonade = True
                                obj.colonade_id = colonade_id.strip()
                                updated_flag = True

                            course_info = fetch_course_info(course_name)
                            if course_info:
                                if not obj.corequisites and course_info.get("corequisites"):
                                    obj.corequisites = course_info["corequisites"]
                                    updated_flag = True
                                if not obj.restrictions and course_info.get("restrictions"):
                                    obj.restrictions = course_info["restrictions"]
                                    updated_flag = True
                                if not obj.recent_terms and course_info.get("recent_terms"):
                                    obj.recent_terms = course_info["recent_terms"]
                                    updated_flag = True

                            if updated_flag:
                                obj.save()
                                updated += 1
                            else:
                                skipped += 1
                        else:
                            course_info = fetch_course_info(course_name)
                            if course_info:
                                obj.corequisites = course_info.get("corequisites")
                                obj.restrictions = course_info.get("restrictions")
                                obj.recent_terms = course_info.get("recent_terms")
                                obj.save()
                            inserted += 1

                        total_matches += 1
                        j += 1
                        continue

                    # Language match
                    language_match = re.match(
                        r'^([A-Z]{2,4})\s+(\d{3}[A-Z]?)\s+(.+?)\s+(\d+\.\d{2})\s+(\d{6})$',
                        line
                    )
                    if language_match and j + 1 < len(lines) and lines[j + 1].strip() == "a":
                        subj, num, title, hours, term = language_match.groups()
                        course_name = normalize_course_name(f"{subj} {num}")
                        hours_int = int(float(hours))

                        obj, created = Course.objects.get_or_create(
                            course_name=course_name,
                            defaults={
                                "hours": hours_int,
                                "is_colonade": True,
                                "colonade_id": "Language Requirement"
                            }
                        )

                        if created:
                            course_info = fetch_course_info(course_name)
                            if course_info:
                                obj.corequisites = course_info.get("corequisites")
                                obj.restrictions = course_info.get("restrictions")
                                obj.recent_terms = course_info.get("recent_terms")
                                obj.save()
                            language_inserted += 1
                        else:
                            skipped += 1

                        total_matches += 1
                        j += 2
                        continue

                    j += 1

            # Manually insert ENG FAH-L as F-AH
            if not Course.objects.filter(course_name="ENG FAH-L").exists():
                Course.objects.create(
                    course_name="ENG FAH-L",
                    hours=3,
                    is_colonade=True,
                    colonade_id="F-AH"
                )
            else:
                print("already exists.")

            print(f"Inserted: {inserted}, Updated: {updated}, Skipped: {skipped}, Language Inserted: {language_inserted}, Total Matches: {total_matches}")

    except Exception as e:
        print(f"Error: {e}")


import_colonnade_courses(PDF_PATH)
'''
exec(code)
