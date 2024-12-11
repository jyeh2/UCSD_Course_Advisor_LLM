import streamlit as st
import pandas as pd
from utils import write_message
from agent import generate_response

# Page Config
st.set_page_config("UCSD Course Advisor", page_icon=":books:")

# App Title
st.title("UC San Diego Course Advisor")

# Sample completed courses data
completed_courses = {
    'CS': pd.DataFrame({
        'Course Code': ['CSE 11', 'CSE 100', 'CSE 110'],
        'Course Name': ['Introduction to Programming', 'Advanced Data Structures', 'Software Engineering']
    }),
    'Math-CS': pd.DataFrame({
        'Course Code': ['MATH 18', 'MATH 20B', 'CSE 100'],
        'Course Name': ['Linear Algebra', 'Calculus for Science and Engineering', 'Advanced Data Structures']
    }),
    'Data Science': pd.DataFrame({
        'Course Code': ['DSC 10', 'DSC 20', 'DSC 100'],
        'Course Name': ['Principles of Data Science', 'Programming and Basic Data Structures', 'Introduction to Data Management']
    }),
    'Economics': pd.DataFrame({
        'Course Code': ['ECON 1', 'ECON 3', 'ECON 109'],
        'Course Name': ['Microeconomics', 'Macroeconomics', 'Game Theory']
    })
}

# Set up Session State
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi, I'm your UCSD course advisor! How can I help you?"},
    ]

# Step 1: Select Major
major = st.selectbox("Select your major:", ["Select Major", "Math-CS", "Data Science", "Economics", "CS"])

# Step 2: Select College (only shown if a major is selected)
if major != "Select Major":
    college = st.selectbox("Select your college:", ["Select College", "ERC", "Marshall", "Warren", "Muir", "Revelle", "Sixth"])

    # Step 3: Prompt for Course Completion (only shown if a college is selected)
    if college != "Select College":
        want_to_see_completed = st.selectbox(
            "Do you want to see what courses you have already completed?",
            ["Select an Option", "Yes", "No"]
        )

        # Step 4: Show Completed Courses or Ask for Course Interests
        if want_to_see_completed == "Yes":
            st.write(f"### Completed Courses for {major}")
            st.table(completed_courses.get(major, pd.DataFrame({"Message": ["No data available for this major."]})))
            ready_for_chat = True
        elif want_to_see_completed == "No":
            st.write(f"What topic of classes are you interested in taking?")
            ready_for_chat = True
        else:
            ready_for_chat = False
    else:
        ready_for_chat = False
else:
    ready_for_chat = False

# Submit handler
def handle_submit(message):
    """
    Submit handler:

    You will modify this method to talk with an LLM and provide
    context using data from Neo4j.
    """
    # Handle the response
    with st.spinner('Thinking...'):
        # Call the agent
        response = generate_response(message)
        write_message('assistant', response)

# Display Chat Interface only if all selections are made
if ready_for_chat:
    # Display initial assistant message
    st.write("### Chat with the Advisor")

    # Display messages in Session State
    for message in st.session_state.messages:
        write_message(message['role'], message['content'], save=False)

    # Handle any user input
    if question := st.chat_input("What is up?"):
        # Display user message in chat message container
        write_message('user', question)

        # Generate a response
        handle_submit(question)
