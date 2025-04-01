from datetime import datetime
from advisingwebsiteapp.majorreqs import normalize_course_name
from advisingwebsiteapp.models import Course, DegreeCourse, UserDegree, Prerequisites

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

    hours_accumulated = {key: 0 for key in missing_colonade}

    def add_courses(courses, colonade_key, limit_hours):
        added = []
        for course in courses:
            if course.course_name in completed_names:
                continue
            ch = float(course.hours or 0)
            if hours_accumulated[colonade_key] + ch <= limit_hours:
                suggested_courses.append(course)
                added.append(course.course_name)
                hours_accumulated[colonade_key] += ch
            if hours_accumulated[colonade_key] >= limit_hours:
                break
        return added

    if ns_hours_needed > 0:
        if lab_needed:
            combined_courses = Course.objects.filter(
                colonade_id__icontains="E-NS & E-SL"
            ).exclude(course_name__in=completed_names)

            added = add_courses(combined_courses, "E-NS", ns_hours_needed)
            if not added:
                ens_courses = Course.objects.filter(
                    colonade_id__icontains="E-NS"
                ).exclude(course_name__in=completed_names)

                esl_courses = Course.objects.filter(
                    colonade_id__icontains="E-SL"
                ).exclude(course_name__in=completed_names)

                add_courses(ens_courses, "E-NS", ns_hours_needed)
                add_courses(esl_courses, "E-SL", 1)
        else:
            ens_only_courses = Course.objects.filter(
                colonade_id__icontains="E-NS"
            ).exclude(course_name__in=completed_names)

            add_courses(ens_only_courses, "E-NS", ns_hours_needed)

    for colonade_id, required_hours in missing_colonade.items():
        if colonade_id in ["E-NS", "E-SL"]:
            continue

        area_courses = Course.objects.filter(
            colonade_id__icontains=colonade_id
        ).exclude(course_name__in=completed_names)

        add_courses(area_courses, colonade_id, required_hours)

    return suggested_courses

def get_remaining_degree_courses(user, transcript_data):
    completed_courses = {c.course_name for c in get_user_completed_courses(transcript_data)}
    remaining_courses_set = set()

    user_degrees = UserDegree.objects.filter(user_student_id=user)
    print(f"DEBUG: User Degrees: {[ud.degree.degree_name for ud in user_degrees]}")

    for ud in user_degrees:
        degree_courses = DegreeCourse.objects.filter(degree=ud.degree).select_related('course')

        for dc in degree_courses:
            course_name = dc.course.course_name
            if course_name not in completed_courses:
                print(f"DEBUG: Adding {course_name} to remaining (not completed)")
                remaining_courses_set.add(dc.course)
            else:
                print(f"DEBUG: Skipping {course_name} (already completed)")

    return list(remaining_courses_set)

def filter_courses_by_prerequisites(courses, transcript_courses):
    taken = {c.course_name for c in transcript_courses}
    eligible = []
    for course in courses:
        prereqs = Prerequisites.objects.filter(course=course)
        if all(p.prerequisite.course_name in taken for p in prereqs):
            eligible.append(course)

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
    from collections import defaultdict
    grouped_courses = defaultdict(list)
    ungrouped_courses = []

    for course in courses:
        try:
            dc = DegreeCourse.objects.get(course=course, degree=degree)
            if dc.group_id:
                grouped_courses[dc.group_id].append(course)
            else:
                ungrouped_courses.append(course)
        except DegreeCourse.DoesNotExist:
            ungrouped_courses.append(course)
        except DegreeCourse.MultipleObjectsReturned:
            dcs = DegreeCourse.objects.filter(course=course, degree=degree)
            for dc in dcs:
                if dc.group_id:
                    grouped_courses[dc.group_id].append(course)
                else:
                    ungrouped_courses.append(course)

    filtered_courses = list(ungrouped_courses)

    for group_id, group_courses in grouped_courses.items():
        group_taken = DegreeCourse.objects.filter(
            group_id=group_id,
            course__course_name__in=completed_names,
            degree=degree
        ).exists()

        if group_taken:
            continue  

        for c in group_courses:
            filtered_courses.append(c)
            print(f"DEBUG: Adding {c.course_name} from group {group_id}")
            break

    return filtered_courses

def recommend_schedule(user, transcript_data, selected_term, max_hours=15):
    max_hours = int(max_hours)
    transcript_courses = get_user_completed_courses(transcript_data)
    completed_names = {normalize_course_name(c.course_name) for c in transcript_courses}

    completed_colonade = get_completed_colonade_hours(transcript_courses)
    missing_colonade = get_missing_colonade_reqs(completed_colonade)
    colonade_suggestions = get_available_colonade_courses(transcript_data, missing_colonade)

    degree_courses_needed = get_remaining_degree_courses(user, transcript_data)
    eligible_degree_courses = filter_courses_by_prerequisites(degree_courses_needed, transcript_courses)

    colonade_suggestions = filter_by_recent_terms(colonade_suggestions, selected_term)
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

    all_candidates = colonade_suggestions + eligible_degree_courses
    recommendations = []

    def total_hours():
        return sum(float(c.hours or 0) for c in recommendations)

    for course in all_candidates:
        if course.course_name in completed_names or course in recommendations:
            continue

        try:
            course_hours = float(course.hours or 0)
        except (TypeError, ValueError):
            continue

        if course_hours <= 0:
            continue

        coreqs = get_coreqs(course)
        coreqs = [c for c in coreqs if c.course_name not in completed_names and c not in recommendations]
        coreqs = filter_by_recent_terms(coreqs, selected_term)

        full_bundle = [course] + coreqs
        bundle_hours = sum(float(c.hours or 0) for c in full_bundle)

        if total_hours() + bundle_hours <= max_hours:
            recommendations.extend(full_bundle)
        elif total_hours() + course_hours <= max_hours:
            recommendations.append(course)

        if total_hours() >= max_hours:
            break
        
    return recommendations


