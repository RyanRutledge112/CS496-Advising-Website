from llama_index.readers.llama_parse import LlamaParse
import os
import json
import re
import pdfplumber

def parse_transcript(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    api_key = os.getenv("LLAMA_CLOUD_API_KEY")
    if not api_key:
        raise ValueError("Missing API key!")

    # Initialize LlamaParse with table extraction
    parser = LlamaParse(
        api_key=api_key,
        content_guideline_instruction="Extract all course details",
        enable_table_extraction=True  
    )

    parsed_data = parser.load_data(file_path)

    extracted_text = "\n".join([section.text.strip() for section in parsed_data if section.text])

    # Create dictonary to store data
    structured_data = {
        "student_name": "Unknown",
        "wku_id": "Unknown",
        "college": [],
        "major": [],
        "courses": []
    }

    student_name_match = re.search(r"Name\s*:\s*(.+)", extracted_text, re.IGNORECASE)
    if student_name_match:
        structured_data["student_name"] = student_name_match.group(1).strip()
    
    wku_id_match = re.search(r"WKU ID\s*:\s*(\d+)", extracted_text, re.IGNORECASE)
    if wku_id_match:
        structured_data["wku_id"] = wku_id_match.group(1).strip()
    else:
        structured_data["wku_id"] = "Unknown"

    curriculum_section_match = re.search(r"Curriculum Information(.*?)(?=\n\w+:|End of Report|$)", extracted_text, re.DOTALL)

    if curriculum_section_match:
        curriculum_section = curriculum_section_match.group(1)

        college_matches = re.findall(r"College:\s*(.+)", curriculum_section)
        major_matches = re.findall(r"Major and Department:\s*(.+)", curriculum_section)

        if college_matches:
            structured_data["colleges"] = [college.strip() for college in college_matches if "Exploratory Studies" not in college] 

        if major_matches:
            structured_data["majors"] = [major.strip() for major in major_matches] 


    # Extract course data from tables
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    # Remove empty values before processing
                    row = [col.strip() if col else "" for col in row]

                    # Ensure row has at least 7 values
                    row = [value for value in row if value] 

                    if len(row) >= 7: 
                        subject = row[0]  
                        course = row[1]  
                        level = row[2]  
                        title = row[3] 
                        grade = row[4] if len(row) > 4 else "N/A"
                        credit_hours = row[5] if len(row) > 5 and row[5].replace(".", "").isdigit() else "0"
                        quality_points = row[6] if len(row) > 6 and row[6].replace(".", "").isdigit() else "0"

                        # Append only if course number is valid
                        if course.isdigit():
                            structured_data["courses"].append({
                                "subject": subject,
                                "course_number": course,
                                "level": level,
                                "title": title,
                                "grade": grade,
                                "credit_hours": credit_hours,
                                "quality_points": quality_points
                            })
    return structured_data

if __name__ == "__main__":
    transcript_file = "Parse/personal.pdf"  

    transcript_data = parse_transcript(transcript_file)
    print(transcript_data)
