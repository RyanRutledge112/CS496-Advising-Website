# Reccomendation not the best system because it is ruled based
# Based on restrictions I can think of at this time 
# Such as terms, prereqs, credit limit
# In the db, we have stored restrictions which have notes such as 
# Must pass prereq with a C, but I don't take that into consideration at this time
# In terms of instructional rows such as select from 300 level courses 6 hours,
# I don't have the most complex system for that, I just have the most basic for now
from datetime import datetime
from advisingwebsiteapp.models import Course, DegreeCourse, UserDegree, Prerequisites
import re
import random

# Normalize course name to sub and number 
def normalize_course_name(name):
    match = re.match(r'([A-Za-z]+)\s*0*(\d+)', name)
    if match:
        subject = match.group(1).lower()
        number = match.group(2)
        return f"{subject} {number}"
    return name.strip().lower()

# Gets Courses from db that user has completed based on transcript
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

# WKU col req codes
def get_colonade_requirements():
    return {
        "F-W1": 3, "F-W2": 3, "F-QR": 3,
        "E-NS": 6,  "E-SL": 1, 
        "F-AH": 3, "F-SB": 3, "F-OC": 3,
        "E-AH": 3, "E-SB": 3,
        "K-SC": 3, "K-LG": 3, "K-SY": 3,
    }

# calcuate col hours from users transcript courses 
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

# Handles which col reqs the user still needs 
def get_missing_colonade_reqs(completed_hours):
    # get col reqs user has completed 
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

# Handle missing colonade recs 
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

    # handle ns and sl req
    # prefer ns and sl req course to be together as one course if they are missing
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

# Handle instructional text ("select 6 hours from 300-level cs courses", etc)
def parse_instruction_to_course_rule(instruction_text, subject):
    rules = []

    text = instruction_text.lower()
    subject = subject.upper()

    # try to extract number of hours 
    hours_match = re.search(r'(\d+)\s*(?:credit)?\s*hour', text)
    min_hours = int(hours_match.group(1)) if hours_match else 3  
    #find course level/number mentions
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

# Gets courses from db that match course subject and level
def get_courses_by_level_rule(subject, min_level):
    return Course.objects.filter(
        course_name__regex=fr"^{subject}\s+{str(min_level)[0]}\d{{2}}"
    )

# Check if user has completed enough courses to satisfy instruct rule
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

# Gets the degree courses user still needs to complete 
def get_remaining_degree_courses(user, transcript_data):
    completed_courses = {c.course_name for c in get_user_completed_courses(transcript_data)}
    remaining_courses_set = set()

    # get all degrees the user has 
    user_degrees = UserDegree.objects.filter(user_student_id=user)

    # get all the degreecourses needed for each degree
    for ud in user_degrees:
        degree_courses = DegreeCourse.objects.filter(degree=ud.degree).select_related('course')

        # add course if not completed 
        for dc in degree_courses:
            course_name = dc.course.course_name
            if course_name not in completed_courses:
                remaining_courses_set.add(dc.course)
            else:
                print(f"DEBUG: Skipping {course_name} (already completed)")

    return list(remaining_courses_set)

# Gets courses filtered by needed prereqs
def filter_courses_by_prerequisites(courses, transcript_courses):
    taken = {normalize_course_name(c.course_name) for c in transcript_courses}
    eligible = []
    missing_prereq_courses = set()
    for course in courses:
        prereqs = Prerequisites.objects.filter(course=course)
        prereq_groups = {}

        # group prereqs by group id 
        for p in prereqs:
            group = getattr(p, 'group_id', None) or 'default' 
            prereq_groups.setdefault(group, []).append(p)

        for p in prereqs:
            group = getattr(p, 'group_id', None) or 'default'
            prereq_groups.setdefault(group, []).append(p)

        all_groups_met = True
        for group, prereqs_in_group in prereq_groups.items():
            group_met = False
            for p in prereqs_in_group:
                prereq_variants = [
                    normalize_course_name(p.prerequisite.course_name),
                    normalize_course_name(p.prerequisite.course_name.replace("PSYS", "PSY")),
                    normalize_course_name(p.prerequisite.course_name.replace("PSY", "PSYS")),
                ]
                # if one course in group is satisfied 
                if any(pr in taken for pr in prereq_variants):
                    group_met = True
                    break  
            
            # if no course in group satisfied 
            if not group_met:
                all_groups_met = False
                break 

        if all_groups_met:
            eligible.append(course)
        else:
            # check missing prereq for degreecourse 
            if DegreeCourse.objects.filter(course=course).exists():
                missing_prereq_courses.update({normalize_course_name(p.prerequisite.course_name) for g in prereq_groups.values() for p in g})
            else:
                print(f"DEBUG: {course.course_name} is elective; skipping due to missing prerequisites.")

    return eligible, missing_prereq_courses

# Gets courses that are in a users selected term
def filter_by_recent_terms(courses, selected_term):
    current_year = datetime.now().year
    selected_term = selected_term.strip().lower()
    filtered = []

    # splits season and year 
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

    # determines if course is avaliable based on terms 
    def is_course_available(term_list, selected_term):
        if not term_list:
            return False  

        seasons = [season for season, year in term_list]

        # Offered all year round
        if all(season in seasons for season in ["fall", "winter", "spring", "summer"]):
            return True

        # Offered every fall and spring
        if all(season in seasons for season in ["fall", "spring"]) and selected_term in ["fall", "spring"]:
            return True

        season_years = [year for season, year in term_list if season == selected_term]
        if not season_years:
            return False

        latest_season_year = max(season_years)

        current_year = datetime.now().year
        if latest_season_year < current_year - 2:
            return False

        # Check every other year pattern for selected term
        if len(season_years) >= 2:
            diffs = [j - i for i, j in zip(season_years[:-1], season_years[1:])]
            if all(diff == 2 for diff in diffs):
                if current_year % 2 == season_years[-1] % 2:
                    return True

        # Fallback: if offered in selected term very recently
        for year in season_years:
            if year >= current_year - 1:
                return True

        return False

    # goes through courses to grab based on term
    for course in courses:
        if not course.recent_terms or course.recent_terms.strip().lower() == "none":
            continue 

        term_list = parse_recent_terms(course.recent_terms)
        if is_course_available(term_list, selected_term):
            filtered.append(course)

    return filtered

# get coreqs for courses if avaliable
def get_coreqs(course):
    if not course.corequisites:
        return []

    # split coreqs and normalize 
    coreq_names = [
        normalize_course_name(c.strip()) 
        for c in course.corequisites.split(',') if c.strip()
    ]
    results = Course.objects.filter(course_name__in=coreq_names)
    return results

# filter courses by group
# if in group, usually one will satisfy
def filter_grouped_degree_courses(courses, completed_names, degree):
    grouped = {}
    ungrouped = []

    for course in courses:
        try:
            dc = DegreeCourse.objects.filter(course=course, degree=degree).first()
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

# Generate course recs
def recommend_schedule(user, transcript_data, selected_term, max_hours=15, instructional_rules=[]):
    SPECIAL_HOUR_GROUPS = {
        "a0b8b924-c7b0-4e65-b77b-6b757f1b7a76": 12,
    }
    max_hours = int(max_hours)
    transcript_courses = get_user_completed_courses(transcript_data)
    completed_names = {normalize_course_name(c.course_name) for c in transcript_courses}

    # get col reqs 
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

    # pick top 5 highest-hour courses for each missing Colonade area
    for colonade_id, course_list in colonade_map.items():
        unique_courses = list({c.course_name: c for c in course_list}.values())
        top_courses = sorted(unique_courses, key=lambda c: float(c.hours or 0), reverse=True)[:5]
        if len(course_list) > 1:
            colonade_suggestions.append(top_courses)
        elif top_courses:
            colonade_suggestions.append(top_courses[0])

    # get degree specific courses and filter 
    degree_courses_needed = get_remaining_degree_courses(user, transcript_data)
    eligible_degree_courses, missing_prereq_courses = filter_courses_by_prerequisites(degree_courses_needed, transcript_courses)

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

    colonade_or_groups = {
        normalize_course_name(c.course_name): group
        for group in colonade_suggestions if isinstance(group, list)
        for c in group
    }

    flattened_colonade = []
    for item in colonade_suggestions:
        if isinstance(item, list):
            flattened_colonade.extend(item)
        else:
            flattened_colonade.append(item)

    all_candidates = flattened_colonade + eligible_degree_courses

    recommendations = []
    recommendation_reasons = []

    # calculates total accumulated credit hours 
    def total_hours():
        total = 0
        for item in recommendations:
            if isinstance(item, list):
                max_hours_in_group = max(float(c.hours or 0) for c in item)
                total += max_hours_in_group
            else:
                total += float(item.hours or 0)
        return total

    # add reason for course
    def add_with_reason(entry, reason):
        if isinstance(entry, list):
            recommendations.append(entry)
            for c in entry:
                recommendation_reasons.append({"course": c, "reason": reason})
        else:
            recommendations.append(entry)
            recommendation_reasons.append({"course": entry, "reason": reason})
    
    # add coreq for course 
    def add_coreqs(coreqs_list):
        for c in coreqs_list:
            recommendations.append(c)
            recommendation_reasons.append({
                "course": c,
                "reason": "Corequisite"
            })

    used_group_ids = set()
    completed_group_ids = set()

    # track completed courses
    for c in transcript_courses:
        dc_entries = DegreeCourse.objects.filter(course=c)
        for dc_entry in dc_entries:
            if dc_entry.group_id:
                completed_group_ids.add((dc_entry.degree_id, dc_entry.group_id))

    # get user degrees 
    user_degrees = UserDegree.objects.filter(user_student_id=user)
    user_degree_ids = [ud.degree.id for ud in user_degrees]

    # pick courses for candidates 
    # degree courses are the most important,
    # then colonade
    # then missing prereq for degree courses
    for ud in user_degrees:
        degree = ud.degree

        for course in all_candidates:
            if course.course_name in completed_names or course in recommendations:
                continue

            dc_entry = DegreeCourse.objects.filter(course=course, degree=degree).first()
            if not dc_entry:
                continue

            group_id = dc_entry.group_id

            # skip if group already completed or used 
            if group_id:
                if (degree.id, group_id) in completed_group_ids and group_id not in SPECIAL_HOUR_GROUPS:
                    continue 

                #for special groups, check if hours completed < required
                if group_id in SPECIAL_HOUR_GROUPS:
                    required_hours = SPECIAL_HOUR_GROUPS[group_id]

                    # calculate completed hours for this group
                    full_group = DegreeCourse.objects.filter(group_id=group_id).select_related('course')
                    completed_group_hours = 0
                    for dc in full_group:
                        if normalize_course_name(dc.course.course_name) in completed_names:
                            completed_group_hours += float(dc.course.hours or 0)

                    if completed_group_hours >= required_hours:
                        continue  

            if group_id and group_id in used_group_ids:
                continue

            try:
                course_hours = float(course.hours or 0)
            except (TypeError, ValueError):
                continue
            if course_hours <= 0:
                continue

            coreqs = get_coreqs(course)
            coreqs = [c for c in coreqs if normalize_course_name(c.course_name) not in completed_names and c not in recommendations]
            coreqs = filter_by_recent_terms(coreqs, selected_term)

            # handle groups
            if group_id:
                full_group = DegreeCourse.objects.filter(group_id=group_id).select_related('course')

                # calculate completed hours
                completed_group_hours = 0
                for dc in full_group:
                    if normalize_course_name(dc.course.course_name) in completed_names:
                        completed_group_hours += float(dc.course.hours or 0)

                group_courses = [
                    dc.course for dc in full_group
                    if normalize_course_name(dc.course.course_name) not in completed_names
                ]
                group_courses = filter_by_recent_terms(group_courses, selected_term)
                group_courses = list({c.course_name: c for c in group_courses}.values())

                required_hours = SPECIAL_HOUR_GROUPS.get(group_id, None)

                if required_hours:
                    selected_courses = []
                    accumulated = completed_group_hours  

                    for course in group_courses:
                        course_hours = float(course.hours or 0)

                        if accumulated >= required_hours:
                            break

                        if total_hours() + course_hours > max_hours:
                            continue 

                        selected_courses.append(course)
                        accumulated += course_hours

                    if selected_courses:
                        if accumulated >= required_hours:
                            add_with_reason(selected_courses, f"Degree core/elective requirement group ({dc_entry.degree.degree_name})")
                            add_coreqs(coreqs)
                            used_group_ids.add(group_id)
                        else:
                            add_with_reason(selected_courses, f"Partial degree group ({dc_entry.degree.degree_name}) - more needed")
                            add_coreqs(coreqs)

                else:
                    # Normal behavior: pick 1 course
                    if group_courses:
                        bundle_hours = float(group_courses[0].hours or 0) + sum(float(c.hours or 0) for c in coreqs)
                        if total_hours() + bundle_hours <= max_hours:
                            add_with_reason(group_courses if len(group_courses) > 1 else group_courses[0],
                                            f"Degree core/elective requirement group ({dc_entry.degree.degree_name})")
                            add_coreqs(coreqs)
                            used_group_ids.add(group_id)

            else:
                # handle ungrouped
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
                            dc = DegreeCourse.objects.filter(course=course, degree=degree).first()
                            reason = (
                                f"Degree core/elective requirement ({dc.degree.degree_name})"
                                if dc else "Degree core/elective requirement (Unknown)"
                            )
                        add_with_reason(course, reason)

                    add_coreqs(coreqs)
    colonade_inserted = []
    for colonade_id, course_list in colonade_map.items():
        available = [
            c for c in course_list
            if normalize_course_name(c.course_name) not in completed_names
            and c not in recommendations
        ]

        available = filter_by_recent_terms(available, selected_term)

        # pick 5 random from colonade section
        # so people arent all recommended the same courses 
        available = list({c.course_name: c for c in available}.values())
        random.shuffle(available)  
        available = available[:5]

        if not available:
            continue

        max_hours_in_group = max(float(c.hours or 0) for c in available)

        if total_hours() + max_hours_in_group > max_hours:
            continue

        add_with_reason(available, f"Colonade ({colonade_id})")
        colonade_inserted.extend(available)

        if total_hours() >= max_hours:
            break  

    for inserted in colonade_inserted:
        if inserted in colonade_suggestions:
            colonade_suggestions.remove(inserted)
    if missing_prereq_courses:
        already_recommended = {
            normalize_course_name(r['course'].course_name): r['reason']
            for r in recommendation_reasons
        }

        recommended_course_names = {
            normalize_course_name(c.course_name)
            for c in recommendations
            if not isinstance(c, list)
        }

        completed_course_names = {
            normalize_course_name(c.course_name)
            for c in transcript_courses
        }

        for prereq_name in missing_prereq_courses:
            prereq_course = Course.objects.filter(course_name__startswith=prereq_name).first()
            if prereq_course:
                normalized = normalize_course_name(prereq_course.course_name)
                prereq_hours = float(prereq_course.hours or 0)

                filtered = filter_by_recent_terms([prereq_course], selected_term)
                if not filtered:
                    continue  

                prereq_reqs = Prerequisites.objects.filter(course=prereq_course)
                unmet = []
                for req in prereq_reqs:
                    req_name = normalize_course_name(req.prerequisite.course_name)
                    if req_name not in completed_course_names and req_name not in recommended_course_names:
                        unmet.append(req_name)

                if unmet:
                    continue  

                if normalized in already_recommended:
                    current_reason = already_recommended[normalized]
                    if "Degree core/elective requirement" not in current_reason:
                        for reason_entry in recommendation_reasons:
                            if normalize_course_name(reason_entry['course'].course_name) == normalized:
                                reason_entry['reason'] = "Missing prerequisite for required course"
                    continue 

                if total_hours() + prereq_hours <= max_hours:
                    add_with_reason(prereq_course, "Missing prerequisite for required course")

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

    # add note if schedule not filled
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
