import streamlit as st
from llm import llm
from graph import graph

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

def get_prerequisites(course_id):
    query = """
        MATCH (c:Course {course_id: $course_id})
        MATCH (og:OrGroup)-[:REQUIRED]->(c)
        MATCH (prereq:Course)-[:INCLUDED_IN]->(og)
        RETURN og.group_id as group_id, 
            collect(prereq.course_id) as prereq_courses
        ORDER BY og.group_id
    """
    result = graph.query(query, params={"course_id": course_id})
    prereqs = []
    for record in result:
        prereqs.append(record['prereq_courses'])
    
    #result = " and ".join([" or ".join(sublist) for sublist in prereqs])
    
    return result
