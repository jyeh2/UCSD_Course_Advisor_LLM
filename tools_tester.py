from llm import llm
from graph import graph

from tools.db_retriever import (get_course_info, get_prerequisites)

test1 = get_course_info("MATH 20C")
print(test1)

test2 = get_prerequisites("CSE 156")
print(test2)

graph._driver.close()
