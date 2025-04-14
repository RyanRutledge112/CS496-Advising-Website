from datetime import datetime
from advisingwebsiteapp.models import Course, DegreeCourse, UserDegree, Prerequisites
import re

def normalize_course_name(name):
    match = re.match(r'([A-Za-z]+)\s*0*(\d+)', name)
    if match:
        subject = match.group(1).lower()
        number = match.group(2)
        return f"{subject} {number}"
    return name.strip().lower()

def get_user_completed_courses(transcript_data):
    transcript_course_codes = {
        normalize_course_name(f"{c['subject']} {c['course_number']}")
        for c in transcript_data["courses"]
    }

    matched_courses = []
    for course in Course.objects.all():
        normalized_name = normalize_course_name(course.course_name)
        if normalized_name in transcript_course_codes:
            matched_courses.append(course)

    return matched_courses

def get_colonade_requirements():
    return {
        "F-W1": 3, "F-W2": 3, "F-QR": 3,
        "E-NS": 6,  "E-SL": 1, 
        "F-AH": 3, "F-SB": 3, "F-OC": 3,
        "E-AH": 3, "E-SB": 3,
        "K-SC": 3, "K-LG": 3, "K-SY": 3,
    }

def get_completed_colonade_hours(transcript_courses):
    completed = {key: 0 for key in get_colonade_requirements()}
    lab_completed = False

    for course in transcript_courses:
        if course.is_colonade and course.colonade_id:
            cid = course.colonade_id.upper()

            if "E-SL" in cid and not lab_completed:
                completed["E-SL"] = min(1, course.hours or 1)
                lab_completed = True

            if "E-NS" in cid:
                completed["E-NS"] += course.hours or 0
            
            for key in completed:
                if key not in ["E-NS", "E-SL"]:
                    if key in cid:
                        completed[key] += course.hours or 0

    completed["lab_completed"] = lab_completed
    return completed

def get_missing_colonade_reqs(completed_hours):
    required = get_colonade_requirements()
    missing_reqs = {}

    if completed_hours["E-NS"] < required["E-NS"]:
        missing_reqs["E-NS"] = required["E-NS"] - completed_hours["E-NS"]

    if not completed_hours.get("lab_completed", False):
        missing_reqs["E-SL"] = 1

    for area in required:
        if area in ["E-NS", "E-SL"]:
            continue
        required_hours = required[area]
        completed_area_hours = completed_hours.get(area, 0)

        if completed_area_hours < required_hours:
            missing_reqs[area] = required_hours - completed_area_hours

    return missing_reqs

def get_available_colonade_courses(transcript_data, missing_colonade):
    completed_courses = get_user_completed_courses(transcript_data)
    completed_names = {c.course_name for c in completed_courses}
    suggested_courses = []

    ns_hours_needed = missing_colonade.get("E-NS", 0)
    lab_needed = "E-SL" in missing_colonade

    def add_courses(courses, colonade_key):
        added = []
        for course in courses:
            if course.course_name in completed_names:
                continue
            # Allow up to 10 per Colonade key
            if len([c for c in suggested_courses if colonade_key in (c.colonade_id or "")]) < 10:
                suggested_courses.append(course)
                added.append(course.course_name)
        return added

    if ns_hours_needed > 0:
        if lab_needed:
            combined_courses = Course.objects.filter(
                colonade_id__icontains="E-NS & E-SL"
            ).exclude(course_name__in=completed_names)

            added = add_courses(combined_courses, "E-NS")
            if not added:
                ens_courses = Course.objects.filter(
                    colonade_id__icontains="E-NS"
                ).exclude(course_name__in=completed_names)

                esl_courses = Course.objects.filter(
                    colonade_id__icontains="E-SL"
                ).exclude(course_name__in=completed_names)

                add_courses(ens_courses, "E-NS")
                add_courses(esl_courses, "E-SL")
        else:
            ens_only_courses = Course.objects.filter(
                colonade_id__icontains="E-NS"
            ).exclude(course_name__in=completed_names)

            add_courses(ens_only_courses, "E-NS")

    for colonade_id in missing_colonade:
        if colonade_id in ["E-NS", "E-SL"]:
            continue

        area_courses = Course.objects.filter(
            colonade_id__icontains=colonade_id
        ).exclude(course_name__in=completed_names)

        add_courses(area_courses, colonade_id)

    return suggested_courses

def parse_instruction_to_course_rule(instruction_text, subject):
    rules = []

    text = instruction_text.lower()
    subject = subject.upper()

    hours_match = re.search(r'(\d+)\s*(?:credit)?\s*hour', text)
    min_hours = int(hours_match.group(1)) if hours_match else 3  

    level_matches = re.findall(r'(\d{3})[- ]*(?:level|and above|or above|courses|numbered)?', text)

    for level_str in level_matches:
        try:
            level = int(level_str)
            rules.append({
                "subject": subject,
                "min_level": level,
                "min_hours": min_hours
            })
        except ValueError:
            continue

    return rules

def get_courses_by_level_rule(subject, min_level):
    return Course.objects.filter(
        course_name__regex=fr"^{subject}\s+{str(min_level)[0]}\d{{2}}"
    )

def has_fulfilled_level_rule(rule, completed_courses):
    subject = rule["subject"].upper()
    min_level = rule["min_level"]
    required_hours = rule.get("min_hours", 3)

    total_hours = 0
    for course in completed_courses:
        name = normalize_course_name(course.course_name)
        match = re.match(rf"{subject.lower()} (\d+)", name)
        if match:
            level = int(match.group(1))
            if level >= min_level:
                total_hours += float(course.hours or 0)

    return total_hours >= required_hours

def get_remaining_degree_courses(user, transcript_data):
    completed_courses = {c.course_name for c in get_user_completed_courses(transcript_data)}
    remaining_courses_set = set()

    user_degrees = UserDegree.objects.filter(user_student_id=user)
    # print(f"DEBUG: User Degrees: {[ud.degree.degree_name for ud in user_degrees]}")

    for ud in user_degrees:
        degree_courses = DegreeCourse.objects.filter(degree=ud.degree).select_related('course')

        for dc in degree_courses:
            course_name = dc.course.course_name
            if course_name not in completed_courses:
                # print(f"DEBUG: Adding {course_name} to remaining (not completed)")
                remaining_courses_set.add(dc.course)
            else:
                print(f"DEBUG: Skipping {course_name} (already completed)")

    return list(remaining_courses_set)

def filter_courses_by_prerequisites(courses, transcript_courses):
    taken = {normalize_course_name(c.course_name) for c in transcript_courses}
    eligible = []
    for course in courses:
        prereqs = Prerequisites.objects.filter(course=course)
        unmet = []

        for p in prereqs:
            prereq_variants = [
                normalize_course_name(p.prerequisite.course_name),
                normalize_course_name(p.prerequisite.course_name.replace("PSYS", "PSY")),
                normalize_course_name(p.prerequisite.course_name.replace("PSY", "PSYS")),
            ]

            if not any(pr in taken for pr in prereq_variants):
                unmet.append(p.prerequisite.course_name)

        if not unmet:
            eligible.append(course)
        else:
            print(f"{course.course_name} - missing prereqs: {unmet}")

    return eligible

def filter_by_recent_terms(courses, selected_term):
    current_year = datetime.now().year
    selected_term = selected_term.strip().lower()
    filtered = []

    def parse_recent_terms(recent_terms_str):
        terms = [t.strip().lower() for t in recent_terms_str.split(';') if t.strip()]
        parsed = []
        for term in terms:
            try:
                season, year = term.split()
                parsed.append((season, int(year)))
            except ValueError:
                continue
        return parsed

    def is_course_available(term_list, selected_term):
        if not term_list:
            # No offering info = not available
            return False  

        years = [year for season, year in term_list]
        seasons = [season for season, year in term_list]
        last_year = max(years)

        # Not available if over 2 year gap 
        if last_year < current_year - 2:
            return False

        # Offered all year round
        if all(season in seasons for season in ["fall", "winter", "spring", "summer"]):
            return True

        # Offered every fall and spring
        if all(season in seasons for season in ["fall", "spring"]):
            return True

        # Check every other year pattern for selected term
        term_years = sorted([year for season, year in term_list if season == selected_term])
        if len(term_years) >= 2:
            diffs = [j - i for i, j in zip(term_years[:-1], term_years[1:])]
            if all(diff == 2 for diff in diffs):
                if current_year % 2 == term_years[-1] % 2:
                    return True

        # Check if offered in selected term recently
        for season, year in term_list:
            if season == selected_term and year >= current_year - 1:
                return True

        return False

    for course in courses:
        if not course.recent_terms or course.recent_terms.strip().lower() == "none":
            continue 

        term_list = parse_recent_terms(course.recent_terms)
        if is_course_available(term_list, selected_term):
            filtered.append(course)

    return filtered

def get_coreqs(course):
    if not course.corequisites:
        return []

    coreq_names = [
        normalize_course_name(c.strip()) 
        for c in course.corequisites.split(',') if c.strip()
    ]
    results = Course.objects.filter(course_name__in=coreq_names)
    return results

def filter_grouped_degree_courses(courses, completed_names, degree):
    grouped = {}
    ungrouped = []

    for course in courses:
        try:
            dc = DegreeCourse.objects.get(course=course, degree=degree)
        except DegreeCourse.DoesNotExist:
            continue

        if dc.group_id not in [None, ""]:
            grouped.setdefault(dc.group_id, []).append(course)
        else:
            ungrouped.append(course)

    filtered_courses = []

    for group_id, group_courses in grouped.items():
        full_group = DegreeCourse.objects.filter(group_id=group_id, degree=degree)
        for dc in full_group:
            course = dc.course
            normalized = normalize_course_name(course.course_name)

        if any(normalize_course_name(dc.course.course_name) in completed_names for dc in full_group):
            print("Skipping group (already fulfilled by one or more courses)")
        else:
            filtered_courses.extend(group_courses)  

    for c in ungrouped:
        normalized = normalize_course_name(c.course_name)
        if normalized in completed_names:
            print(f"Skipping ungrouped (completed): {c.course_name}")
        else:
            filtered_courses.append(c)

    return filtered_courses

def recommend_schedule(user, transcript_data, selected_term, max_hours=15, instructional_rules=[]):
    max_hours = int(max_hours)
    transcript_courses = get_user_completed_courses(transcript_data)
    completed_names = {normalize_course_name(c.course_name) for c in transcript_courses}

    completed_colonade = get_completed_colonade_hours(transcript_courses)
    missing_colonade = get_missing_colonade_reqs(completed_colonade)

    colonade_suggestions_raw = get_available_colonade_courses(transcript_data, missing_colonade)
    colonade_suggestions = []

    colonade_map = {}
    for course in colonade_suggestions_raw:
        if not course.colonade_id:
            continue
        for cid in course.colonade_id.upper().split(","):
            key = cid.strip()
            for missing_key in missing_colonade:
                if key.startswith(missing_key):
                    colonade_map.setdefault(missing_key, []).append(course)

    for colonade_id, course_list in colonade_map.items():
        unique_courses = list({c.course_name: c for c in course_list}.values())
        top_courses = sorted(unique_courses, key=lambda c: float(c.hours or 0), reverse=True)[:5]
        if len(course_list) > 1:
            colonade_suggestions.append(top_courses)
        elif top_courses:
            colonade_suggestions.append(top_courses[0])

    degree_courses_needed = get_remaining_degree_courses(user, transcript_data)
    eligible_degree_courses = filter_courses_by_prerequisites(degree_courses_needed, transcript_courses)

    filtered_colonade = []
    for item in colonade_suggestions:
        if isinstance(item, list):
            group = filter_by_recent_terms(item, selected_term)
            if group:
                filtered_colonade.append(group if len(group) > 1 else group[0])
        else:
            filtered = filter_by_recent_terms([item], selected_term)
            if filtered:
                filtered_colonade.append(filtered[0])
    colonade_suggestions = filtered_colonade

    eligible_degree_courses = filter_by_recent_terms(eligible_degree_courses, selected_term)

    user_degrees = UserDegree.objects.filter(user_student_id=user)

    filtered_courses = []
    for ud in user_degrees:
        filtered = filter_grouped_degree_courses(
            [c for c in eligible_degree_courses if DegreeCourse.objects.filter(course=c, degree=ud.degree).exists()],
            completed_names,
            ud.degree
        )
        filtered_courses.extend(filtered)

    eligible_degree_courses = list(set(filtered_courses))

    colonade_or_groups = {
        normalize_course_name(c.course_name): group
        for group in colonade_suggestions if isinstance(group, list)
        for c in group
    }

    # Flatten colonade courses for selection
    flattened_colonade = []
    for item in colonade_suggestions:
        if isinstance(item, list):
            flattened_colonade.extend(item)
        else:
            flattened_colonade.append(item)

    all_candidates = flattened_colonade + eligible_degree_courses

    recommendations = []
    recommendation_reasons = []

    def total_hours():
        total = 0
        for item in recommendations:
            if isinstance(item, list):
                max_hours_in_group = max(float(c.hours or 0) for c in item)
                total += max_hours_in_group
            else:
                total += float(item.hours or 0)
        return total

    def add_with_reason(entry, reason):
        if isinstance(entry, list):
            recommendations.append(entry)
            for c in entry:
                recommendation_reasons.append({"course": c, "reason": reason})
        else:
            recommendations.append(entry)
            recommendation_reasons.append({"course": entry, "reason": reason})

    def add_coreqs(coreqs_list):
        for c in coreqs_list:
            recommendations.append(c)
            recommendation_reasons.append({
                "course": c,
                "reason": "Corequisite"
            })

    used_group_ids = set()

    for course in all_candidates:
        if course.course_name in completed_names or course in recommendations:
            continue

        try:
            course_hours = float(course.hours or 0)
        except (TypeError, ValueError):
            continue
        if course_hours <= 0:
            continue

        group_id = None
        dc_entry = DegreeCourse.objects.filter(course=course).first()
        if dc_entry:
            group_id = dc_entry.group_id
        if group_id and group_id in used_group_ids:
            continue

        coreqs = get_coreqs(course)
        coreqs = [c for c in coreqs if normalize_course_name(c.course_name) not in completed_names and c not in recommendations]
        coreqs = filter_by_recent_terms(coreqs, selected_term)

        # Degree group logic
        if group_id:
            full_group = DegreeCourse.objects.filter(group_id=group_id).select_related('course')
            group_courses = [
                dc.course for dc in full_group
                if normalize_course_name(dc.course.course_name) not in completed_names
            ]
            group_courses = filter_by_recent_terms(group_courses, selected_term)
            group_courses = list({c.course_name: c for c in group_courses}.values())

            max_group_hours = max((float(c.hours or 0) for c in group_courses), default=0)
            coreq_hours = sum(float(c.hours or 0) for c in coreqs)
            bundle_hours = max_group_hours + coreq_hours

            if total_hours() + bundle_hours <= max_hours:
                reason = (
                    f"Degree core/elective requirement group ({dc_entry.degree.degree_name})"
                    if len(group_courses) > 1 else
                    f"Degree core/elective requirement ({dc_entry.degree.degree_name})"
                )
                add_with_reason(group_courses if len(group_courses) > 1 else group_courses[0], reason)
                add_coreqs(coreqs)
                used_group_ids.add(group_id)
        else:
            bundle_hours = float(course.hours or 0) + sum(float(c.hours or 0) for c in coreqs)
            if total_hours() + bundle_hours <= max_hours:
                normalized = normalize_course_name(course.course_name)

                if normalized in colonade_or_groups:
                    group = colonade_or_groups[normalized]
                    if group not in recommendations:
                        add_with_reason(group, f"Colonade ({group[0].colonade_id})")
                else:
                    if course.is_colonade:
                        reason = f"Colonade ({course.colonade_id})"
                    else:
                        dc = DegreeCourse.objects.filter(course=course).first()
                        reason = (
                            f"Degree core/elective requirement ({dc.degree.degree_name})"
                            if dc else "Degree core/elective requirement (Unknown)"
                        )
                    add_with_reason(course, reason)

                add_coreqs(coreqs)

    # Handle instructional rules
    for rule in instructional_rules:
        if has_fulfilled_level_rule(rule, transcript_courses):
            continue

        subj = rule["subject"]
        level = rule["min_level"]
        min_hours = rule.get("min_hours", 3)

        available = get_courses_by_level_rule(subj, level).exclude(course_name__in=completed_names)
        available = filter_by_recent_terms(available, selected_term)

        accumulated = 0
        for course in available:
            if course in recommendations:
                continue
            ch = float(course.hours or 0)
            if total_hours() + ch > max_hours:
                break
            add_with_reason(course, f"{subj} {level}+ requirement")
            accumulated += ch
            if accumulated >= min_hours:
                break

    partial_fill_notice = ""
    if total_hours() < max_hours:
        partial_fill_notice = (
            "You have no more available courses to recommend for this term — "
            "most likely you've completed most of your degree requirements!"
        )

    return {
        "recommendations": recommendations,
        "credit_hours": total_hours(),
        "recommendation_reasons": recommendation_reasons,
        "notice": partial_fill_notice
    }
