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
from tools.db_retriever import (get_course_info, get_prerequisites)
#from tools.vector import get_course_description
from tools.pdf_reader import pdf_qa_tool


from pydantic import BaseModel

# Create a course chat chain
chat_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a UCSD course scheduler who provides professional course selection guidance."),
        ("human", "{input}"),
    ]
)

course_chat = chat_prompt | llm | StrOutputParser()

class PrerequisiteInput(BaseModel):
    course_id: str


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
        name="Gets immediate prerequisites",
        description="Accurately retrieves immediate prerequisite courses for given course_id from Neo4j database",
        func=get_prerequisites,
        args_schema=PrerequisiteInput,
    ),
     Tool.from_function(
        name="PDF Course Catalog Search",
        description="Search through UCSD course catalogs (CSE and Math) for detailed course information and requirements",
        func=pdf_qa_tool,
    )
]

unused_tool = """
    Tool.from_function(
        name="Course Description Search",  
        description="For when you need to find information about course content based on a description",
        func=get_course_description, 
    ),
    Tool.from_function(
        name="PDF Course Catalog Search",
        description="Search through UCSD course catalogs (CSE and Math) for detailed course information and requirements",
        func=pdf_qa_tool,
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
- Course id take the form like 'MATH 18' or 'MATH 20C', with all CAPs and space in between department and code.

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