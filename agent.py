from llm import llm
from graph import graph

from langchain_core.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser

from langchain.tools import Tool

from langchain_community.chat_message_histories import Neo4jChatMessageHistory

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain import hub


from utils import get_session_id

from langchain_core.prompts import PromptTemplate


from tools.cypher import cypher_qa
from tools.db_retriever import *
#from tools.vector import get_course_description
from tools.pdf_reader import pdf_qa_tool


from pydantic import BaseModel, field_validator
import re

# Create a course chat chain
chat_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a UCSD course scheduler who provides professional course selection guidance."),
        ("human", "{input}"),
    ]
)

course_chat = chat_prompt | llm | StrOutputParser()

class CourseIDInput(BaseModel):
    course_id: str

    @field_validator('course_id')
    @classmethod
    def validate_course_id(cls, v):
        # Pattern: Letters + space + numbers (optionally followed by a letter)
        cleaned = v.strip().replace('`', '').split('\n')[0]
        pattern = r'^[A-Z]+\s\d+[A-Z]*$'
        if not re.match(pattern, cleaned):
            raise ValueError('Course ID must be in format like "MATH 18" or "MATH 20C"')
        print(f"VALIDATION OUTPUT:{cleaned}________")
        return cleaned

class MajorIDInput(BaseModel):
    major_id: str

    @field_validator('major_id')
    @classmethod
    def validate_major_id(cls, v):
        valid_majors = ['MA30']
        if v not in valid_majors:
            raise ValueError(f'Major ID must be one of: {valid_majors}')
        return v

# Create a set of tools
tools = [
    Tool.from_function(
        name="General Chat",
        description="dont use",
        func=course_chat.invoke,
    ),
    Tool.from_function(
        name="Course information",
        description="Provide information about course questions using Cypher",
        func = cypher_qa,
    ), 
    Tool.from_function(
        name="(Accurate) Gets immediate prerequisites",
        description="Accurately retrieves immediate prerequisite courses for given course_id from Neo4j database. Convert input course id into proper format before proceeding. ",
        func=get_prerequisites,
        args_schema=CourseIDInput,
    ),
    Tool.from_function(
        name="(Accurate) Iteratively retrieves ALL prerequisites",
        description="Iteratively handles the retrieval of ALL prerequisite courses for a given course_id from Neo4j database. DO NOT use unless you are retrieving ALL prerequisites. Otherwise, just use '(Accurate) Gets immediate prerequisites'.",
        func=iterative_get_prerequisites,
        args_schema=CourseIDInput,
    ),
    Tool.from_function(
        name="(Accurate) Get entire major requirement",
        description="Retrieves all sets of sub-requirements and courses for a given major_id. Use this dictionary to reference major_id: \{'MATH-CS major': 'MA30'\}",
        func=get_major_requirements,
        args_schema=MajorIDInput,
    ),
    Tool.from_function(
        name="PDF Course Catalog Search",
        description="Search through UCSD course catalogs (CSE and Math) for detailed course information and requirements",
        func=pdf_qa_tool,
    ),
    Tool.from_function(
        name="Major Requirement",
        description="Provided required courses to complete in order to graduate for a major",
        func=get_courses_by_milestone,
    ),
]

unused_tool = """
    Tool.from_function(
        name="Course Description Search",  
        description="For when you need to find information about course content based on a description",
        func=get_course_description, 
    )
"""

# Create chat history callback
def get_memory(session_id):
    return Neo4jChatMessageHistory(session_id=session_id, graph=graph)

# Create the agent
agent_prompt = PromptTemplate.from_template("""
You are an expert UCSD college course advisor providing information about UCSD courses.
Be as helpful as possible and return as much information as possible.

Some basic information about UCSD courses to make you more informed:
- Course id take the form like 'MATH 18' 'MATH 20C' or 'MATH 31CH', with all CAPs and space in between department and code. 
- Introductory sequences start with lower code number, with 1-99 indicating lower division undergraduate courses, 100-199 indicating upper division undergraduate courses. 200-299 indicating graduate only courses.
- Typical courses are 4 units, typical labs and seminars are 1-2 units. But this unit varies depending on the specific class. Consult specific data before making scheduling decisions.
- UCSD has 3 regular quarter terms, Fall(Sep-Dec), Winter(Jan-Mar), Spring(Apr-Jun). Each quarter has a maximum unit limit of 22.0, and minimum 12.0 units to remain as full-time enrollment.
- To request special approval of courses, or to gain permission to enroll even when requirements not all satisfied, students would need to complete an Enrollment Authorization Request ('EASy Request') at 'https://academicaffairs.ucsd.edu/Modules/Students/PreAuth/'
                                            
Maximize the use of the accurate retrieval tools; if failed, reflect on why it failed, and then assess what other tools to use.
Refrain from using your existing pretrained knowledge unless all relevant tools reach empty results. 

Do not answer any questions that do not relate to course planning or UCSD advising.
If General Chat is used, mention the info is beyond scope and may be inaccurate.

TOOLS:

------

You have access to the following tools:

{tools}

To use a tool, please use the following format:

```
Thought: Do I need to use a tool? Yes
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
```
You may use multiple tools to assist your tasks.

When you have a response to say to the Human, or if you do not need to use a tool, you MUST use the format:

```
Thought: Do I need to use a tool? No
Final Answer: [your response here]
```

Begin!

Previous conversation history:
{chat_history}

New input: {input}
{agent_scratchpad}
""")

agent = create_react_agent(llm, tools, agent_prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True

    )

chat_agent = RunnableWithMessageHistory(
    agent_executor,
    get_memory,
    input_messages_key="input",
    history_messages_key="chat_history",

)

# Create a handler to call the agent
def generate_response(user_input):
    """
    Create a handler that calls the Conversational agent
    and returns a response to be rendered in the UI
    """
    try:
        response = chat_agent.invoke(
            {"input": user_input},
            {"configurable": {"session_id": get_session_id()}},
        )
        return response['output']
    except Exception as e:
        # Log the error if you have logging set up
        print(f"Error occurred: {str(e)}")
        return "I apologize, but I encountered an error processing your request. Please try rephrasing your question or ask something else."