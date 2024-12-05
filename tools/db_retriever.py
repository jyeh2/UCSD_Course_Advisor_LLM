import streamlit as st
from graph import graph
import re

def get_course_info(course_id):
    query = """
        MATCH (c:Course {course_id: $course_id})
        RETURN 
            c.course_id as id,
            c.title as title,
            c.units as units,
            c.description as description
    """
    result = graph.query(query, params={"course_id": course_id})
    if result and len(result) > 0:
        return result
    return None

def get_prerequisites(course_id, _ashelper=False):
    # Double Checks for course_id format
    course_id = course_id.strip().replace('`', '').split('\n')[0]
    pattern = r'^[A-Z]+\s\d+[A-Z]*$'
    if not re.match(pattern, course_id):
        raise ValueError('Course ID must be in format like "MATH 18" or "MATH 20C"')

    query = """
        MATCH (c:Course {course_id: $course_id})
        MATCH (og:OrGroup)-[:REQUIRED]->(c)
        MATCH (prereq:Course)-[:INCLUDED_IN]->(og)
        RETURN og.group_id as group_id, 
            collect(prereq.course_id) as prereq_courses
        ORDER BY og.group_id
    """
    result = graph.query(query, params={"course_id": course_id})
    
    if _ashelper:
        return result
    if not result:
        return "This course has no prerequisites."
    
    prereq_groups = []
    for record in result:
        courses = record['prereq_courses']
        if len(courses) == 1:
            prereq_groups.append(courses[0])
        else:
            prereq_groups.append(f"({' OR '.join(courses)})")
    
    return "Prerequisites: " + " AND ".join(prereq_groups)

def iterative_get_prerequisites(course_id):
    # Double Checks for course_id format
    course_id = course_id.strip().replace('`', '').split('\n')[0]
    pattern = r'^[A-Z]+\s\d+[A-Z]*$'
    if not re.match(pattern, course_id):
        raise ValueError('Course ID must be in format like "MATH 18" or "MATH 20C"')
    
    prereq_tree = {}
    to_process = {course_id}
    processed = set()
    prereqs = []

    while to_process:
        current_course = to_process.pop()
        if current_course in processed:
            continue
            
        result = get_prerequisites(current_course, _ashelper=True)
        processed.add(current_course)
        
        if result:
            prereq_tree[current_course] = []
            subprereq_strings = []
            for record in result:
                group_id = record['group_id']
                prereq_courses = record['prereq_courses']
                
                # If there's only one course in the group, don't create an OR group
                if len(prereq_courses) == 1:
                    prereq_tree[current_course].append(prereq_courses[0])
                    subprereq_strings.append(f"({prereq_courses[0]})")
                else:
                    # Create an OR group
                    prereq_tree[current_course].append({
                        'type': 'OR',
                        'courses': prereq_courses
                    })
                    subprereq_strings.append(f"({' or '.join(prereq_courses)})")
                
                # Add all prerequisites to processing queue
                for prereq in prereq_courses:
                    if prereq not in processed:
                        to_process.add(prereq)
                
            prereqs.append(f"{current_course}: {' and '.join(subprereq_strings)}")
    
    return '\n'.join(prereqs)

def get_courses_by_milestone(dummy=None):
    # Cypher query to get course IDs grouped by milestone titles
    query_courses = """
        MATCH (c:Course)-[:INCLUDED_IN]->(m: Milestone)
        RETURN m.milestone_id AS milestone_id, 
               m.title AS title, 
               collect(c.course_id) AS course_ids
        ORDER BY m.milestone_id
    """
    query_orgroups = """
        MATCH (m:Milestone)<-[:INCLUDED_IN]-(og:OrGroup)<-[:REQUIRED]-(c:Course)
        WITH 
            m.milestone_id AS milestone_id, 
            m.title AS title,
            og.group_id AS or_group_id, 
            collect(c.course_id) AS courses
        WITH 
            milestone_id, 
            title, 
            collect(courses) AS grouped_courses
        RETURN 
            milestone_id, 
            title, 
            grouped_courses
        ORDER BY milestone_id
        """
    
    result_courses = graph.query(query_courses)
    result_orgroups = graph.query(query_orgroups)

    
    formatted_results = {}

    # Process direct courses
    for record in result_courses:
        title = record["title"]
        courses = record["course_ids"]

        # Initialize the title if not present
        if title not in formatted_results:
            formatted_results[title] = []

        # Add direct courses to the list
        formatted_results[title].extend(courses)

    # Process grouped courses
    for record in result_orgroups:
        title = record["title"]
        grouped_courses = record["grouped_courses"]

        # Initialize the title if not present
        if title not in formatted_results:
            formatted_results[title] = []

        # Add grouped courses (as lists) to the list
        formatted_results[title].extend(grouped_courses)

    return formatted_results

def get_major_requirements(major_id):
    requirements = {}

    # First query: Get direct course requirements
    direct_query = """
    MATCH (major:Milestone {milestone_id: $major_id})
    MATCH (div:Milestone)-[:REQUIRED]->(major)
    MATCH (require:Milestone)-[:REQUIRED]->(div)
    MATCH (c:Course)-[:INCLUDED_IN]->(require)
    RETURN major.title as major, major.description, 
        div.milestone_id as division, div.description,
        require.title as requirement, require.description, require.units_required as units_needed,
        collect(c.course_id) as select_from_courses
    """

    # Process direct course requirements
    direct_results = graph.query(direct_query, params={"major_id": major_id})
    
    record = direct_results[0]
    requirements['major ID'] = major_id
    requirements['title'] = record['major']
    requirements['description'] = record['major.description']
    requirements['curriculum'] = []

    for record in direct_results:
        current_div = record['division']
        # find division
        if not any(div['division']==current_div for div in requirements['curriculum']):
            requirements['curriculum'].append({
                'division': current_div, 
                'description': record['div.description'], 
                'requirements': []
            })
        
        # set units as needed criteria
        if record['units_needed']==0:
            needed = 'one course'
        else:
            needed = f"{record['units_needed']} units"

        for div in requirements['curriculum']:
            if div['division']==current_div:
                div['requirements'].append({
                    'study': record['requirement'], 
                    'description': record['require.description'],
                    'needed to satisfy': needed,
                    'select from': record['select_from_courses']
                })
    
    # Second query: Get OR group requirements
    or_group_query = """
    MATCH (major:Milestone {milestone_id: $major_id})
    MATCH (div:Milestone)-[:REQUIRED]->(major)
    MATCH (require:Milestone)-[:REQUIRED]->(div)
    MATCH (og:OrGroup)-[:INCLUDED_IN]->(require)
    MATCH (c:Course)-[:REQUIRED]->(og)
    RETURN major.title as major, major.description, 
        div.milestone_id as division, div.description,
        require.title as requirement, require.description, require.units_required as units_needed,
        og.group_id as path,
        collect(c.course_id) as select_from_courses
    """
    
    # Process requirements with sequence options
    or_group_results = graph.query(or_group_query, params={"major_id": major_id})
    for record in or_group_results:
        current_div = record['division']
        # find division
        if not any(div['division']==current_div for div in requirements['curriculum']):
            requirements['curriculum'].append({
                'division': current_div, 
                'description': record['div.description'], 
                'requirements': []
            })
        
        # since sequences are being offered, no units requirement are here
        needed = 'one sequence path'

        # check if current division is recorded
        for div in requirements['curriculum']:
            if div['division']==current_div:
                current_requirement = record['requirement']
                # check if current requirement is recorded
                if not any(study['study']==current_requirement for study in div['requirements']):
                    div['requirements'].append({
                        'study': record['requirement'], 
                        'description': record['require.description'],
                        'needed to satisfy': needed,
                        'select from': []
                    })
                
                for study in div['requirements']:
                    if study['study']==current_requirement:
                        study['select from'].append(tuple(record['select_from_courses']))
    
    return requirements