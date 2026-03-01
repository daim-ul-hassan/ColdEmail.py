import streamlit as st
import os
import json
from datetime import datetime, timedelta
import random

os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"

from crewai import Agent, Task, Crew, LLM
from crewai_tools import ScrapeWebsiteTool
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Subject Time Manager",
    page_icon="📚",
    layout="wide"
)

# Initialize session state for API key management
if "api_key" not in st.session_state:
    st.session_state.api_key = os.getenv("GEMINI_API_KEY") or ""
if "current_api_key_hash" not in st.session_state:
    st.session_state.current_api_key_hash = None

# Function to get a hash of the API key for identification
def get_api_key_hash(api_key):
    if not api_key:
        return None
    import hashlib
    return hashlib.md5(api_key.encode()).hexdigest()[:16]

# Function to get current user's data key prefix
def get_user_prefix():
    api_key_hash = st.session_state.get("current_api_key_hash")
    if not api_key_hash:
        return ""
    return f"user_{api_key_hash}_"

# Function to get current user's data key
def get_user_key(base_key):
    prefix = get_user_prefix()
    return f"{prefix}{base_key}"

# Function to get current user's data with default
def get_user_data(base_key, default=None):
    key = get_user_key(base_key)
    if default is None:
        default = [] if base_key in ["subjects", "test_history", "homework_chat", "definitions_chat"] else {} if base_key in ["syllabus", "test_answers"] else None
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]

# Function to set current user's data
def set_user_data(base_key, value):
    st.session_state[get_user_key(base_key)] = value

# Initialize data keys for current API key (create them if they don't exist)
def ensure_user_data_exists():
    keys = ["subjects", "syllabus", "study_routine", "test_history", "current_test", "test_answers", "homework_chat", "definitions_chat"]
    defaults = [ [], {}, None, [], None, {}, [], [] ]
    for key, default in zip(keys, defaults):
        get_user_data(key, default)

# Initialize data for current API key
if st.session_state.api_key:
    current_hash = get_api_key_hash(st.session_state.api_key)
    if current_hash != st.session_state.current_api_key_hash:
        st.session_state.current_api_key_hash = current_hash
        ensure_user_data_exists()
else:
    st.session_state.current_api_key_hash = None

# Legacy session state initialization (for backward compatibility - shared data when no API key)
if "subjects" not in st.session_state:
    st.session_state.subjects = []
if "syllabus" not in st.session_state:
    st.session_state.syllabus = {}
if "study_routine" not in st.session_state:
    st.session_state.study_routine = None
if "test_history" not in st.session_state:
    st.session_state.test_history = []
if "current_test" not in st.session_state:
    st.session_state.current_test = None
if "test_answers" not in st.session_state:
    st.session_state.test_answers = {}
if "homework_chat" not in st.session_state:
    st.session_state.homework_chat = []
if "definitions_chat" not in st.session_state:
    st.session_state.definitions_chat = []

# Property accessors for user-specific data
class UserData:
    @property
    def subjects(self):
        return get_user_data("subjects")
    @subjects.setter
    def subjects(self, value):
        set_user_data("subjects", value)
    
    @property
    def syllabus(self):
        return get_user_data("syllabus")
    @syllabus.setter
    def syllabus(self, value):
        set_user_data("syllabus", value)
    
    @property
    def study_routine(self):
        return get_user_data("study_routine")
    @study_routine.setter
    def study_routine(self, value):
        set_user_data("study_routine", value)
    
    @property
    def test_history(self):
        return get_user_data("test_history")
    @test_history.setter
    def test_history(self, value):
        set_user_data("test_history", value)
    
    @property
    def current_test(self):
        return get_user_data("current_test")
    @current_test.setter
    def current_test(self, value):
        set_user_data("current_test", value)
    
    @property
    def test_answers(self):
        return get_user_data("test_answers")
    @test_answers.setter
    def test_answers(self, value):
        set_user_data("test_answers", value)
    
    @property
    def homework_chat(self):
        return get_user_data("homework_chat")
    @homework_chat.setter
    def homework_chat(self, value):
        set_user_data("homework_chat", value)
    
    @property
    def definitions_chat(self):
        return get_user_data("definitions_chat")
    @definitions_chat.setter
    def definitions_chat(self, value):
        set_user_data("definitions_chat", value)

# Create user data instance
user_data = UserData()

# Sidebar for API key input
with st.sidebar:
    st.markdown("---")
    st.subheader("🔑 API Configuration")
    
    # Store previous API key to detect changes
    previous_api_key = st.session_state.api_key
    
    api_key_input = st.text_input(
        "Enter your Gemini API Key",
        value=st.session_state.api_key,
        type="password",
        placeholder="Paste your API key here...",
        help="Get your API key from https://aistudio.google.com/app/apikey"
    )
    
    # Handle API key change
    if api_key_input != previous_api_key:
        st.session_state.api_key = api_key_input
        if api_key_input:
            new_hash = get_api_key_hash(api_key_input)
            st.session_state.current_api_key_hash = new_hash
            ensure_user_data_exists()
            st.success("✅ API key configured - Your data is now isolated!")
            st.rerun()
        else:
            st.session_state.current_api_key_hash = None
            st.warning("⚠️ No API key - Using shared data")
            st.rerun()
    
    if not st.session_state.api_key:
        st.warning("⚠️ Please enter your Gemini API key for private data storage")
    else:
        # Show user identifier (first 8 chars of hash)
        user_id = st.session_state.current_api_key_hash[:8] if st.session_state.current_api_key_hash else "Unknown"
        st.success(f"✅ API key configured")
        st.caption(f"User ID: {user_id}... (Your data is private)")

# Initialize LLM only if API key is available
llm = None
if st.session_state.api_key:
    try:
        llm = LLM(
            model="gemini/gemini-2.5-flash",
            api_key=st.session_state.api_key
        )
    except Exception as e:
        st.sidebar.error(f"Error initializing LLM: {e}")

scrape_tool = ScrapeWebsiteTool()

# Define agents (only if LLM is available)
study_planner_agent = None
test_creator_agent = None
homework_helper_agent = None
definition_expert_agent = None

if llm:
    study_planner_agent = Agent(
        role="Study Planner",
        goal="Create effective study routines and schedules for students",
        backstory="""You are an expert educational planner with years of experience helping students 
        organize their study time effectively. You understand different learning styles, optimal 
        study durations, and how to balance multiple subjects. You create personalized study plans 
        that maximize learning efficiency.""",
        llm=llm,
        verbose=False
    )

    test_creator_agent = Agent(
        role="Test Creator",
        goal="Create comprehensive tests and assessments for students",
        backstory="""You are an experienced educator who specializes in creating well-structured 
        tests that accurately assess student understanding. You create questions that range from 
        basic recall to advanced application, and you provide clear, detailed solutions.""",
        llm=llm,
        tools=[scrape_tool],
        verbose=False
    )

    homework_helper_agent = Agent(
        role="Homework Helper",
        goal="Help students understand and complete their homework",
        backstory="""You are a patient and knowledgeable tutor who helps students with their 
        homework. You explain concepts clearly, provide step-by-step guidance, and help students 
        develop problem-solving skills. You use web research when needed to provide accurate information.""",
        llm=llm,
        tools=[scrape_tool],
        verbose=False
    )

    definition_expert_agent = Agent(
        role="Definition Expert",
        goal="Provide clear and comprehensive definitions for any term or concept",
        backstory="""You are a knowledge expert who excels at explaining definitions clearly. 
        You provide not just the basic definition, but also context, examples, and related concepts 
        to ensure complete understanding. You can explain terms from any field of study.""",
        llm=llm,
        tools=[scrape_tool],
        verbose=False
    )

# Sidebar navigation
st.sidebar.title("📚 Subject Time Manager")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["🏠 Home", "📋 Subjects & Syllabus", "📅 Study Routine", "📝 Tests & Exams", "❓ Homework Help", "📖 Definitions"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Your Progress")
st.sidebar.write(f"Subjects: {len(user_data.subjects)}")
st.sidebar.write(f"Tests Taken: {len(user_data.test_history)}")

# Home Page
if page == "🏠 Home":
    st.title("📚 Welcome to Subject Time Manager!")
    st.markdown("""
    ### Your Complete Study Companion
    
    This application helps you:
    
    1. **📋 Manage Subjects & Syllabus** - Add your subjects and their syllabus
    2. **📅 Create Study Routines** - Get AI-generated personalized study schedules
    3. **📝 Take Tests** - Practice with AI-generated tests and grand tests
    4. **❓ Homework Help** - Get help with any homework questions
    5. **📖 Definitions** - Look up definitions for any term or concept
    
    ### Get Started:
    Use the sidebar to navigate through different sections. Start by adding your subjects!
    """)
    
    # Quick stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Subjects", len(user_data.subjects))
    with col2:
        st.metric("Tests Completed", len(user_data.test_history))
    with col3:
        total_score = sum([t.get('score', 0) for t in user_data.test_history])
        avg_score = total_score / len(user_data.test_history) if user_data.test_history else 0
        st.metric("Average Score", f"{avg_score:.1f}%")

# Subjects & Syllabus Page
elif page == "📋 Subjects & Syllabus":
    st.title("📋 Subjects & Syllabus")
    
    tab1, tab2 = st.tabs(["Add Subjects", "View Syllabus"])
    
    with tab1:
        st.subheader("Add Your Subjects")
        
        with st.form("add_subject_form"):
            subject_name = st.text_input("Subject Name", placeholder="e.g., Mathematics, Physics, History")
            syllabus_content = st.text_area(
                "Syllabus/Topics",
                placeholder="Enter the topics you need to study (one per line)\n\ne.g.:\nAlgebra\nGeometry\nCalculus\nStatistics",
                height=200
            )
            
            difficulty = st.select_slider(
                "Difficulty Level",
                options=["Easy", "Medium", "Hard", "Very Hard"],
                value="Medium"
            )
            
            priority = st.select_slider(
                "Priority",
                options=["Low", "Medium", "High", "Very High"],
                value="Medium"
            )
            
            hours_per_week = st.number_input("Hours per week you want to study", min_value=1, max_value=40, value=5)
            
            submitted = st.form_submit_button("Add Subject")
            
            if submitted and subject_name:
                subject_data = {
                    "name": subject_name,
                    "syllabus": [s.strip() for s in syllabus_content.split('\n') if s.strip()],
                    "difficulty": difficulty,
                    "priority": priority,
                    "hours_per_week": hours_per_week,
                    "added_date": datetime.now().strftime("%Y-%m-%d")
                }
                
                # Check if subject already exists
                existing = [s for s in user_data.subjects if s["name"].lower() == subject_name.lower()]
                if existing:
                    st.error(f"Subject '{subject_name}' already exists!")
                else:
                    subjects_list = user_data.subjects
                    subjects_list.append(subject_data)
                    user_data.subjects = subjects_list
                    syllabus_dict = user_data.syllabus
                    syllabus_dict[subject_name] = subject_data["syllabus"]
                    user_data.syllabus = syllabus_dict
                    st.success(f"✅ Added {subject_name} successfully!")
    
    with tab2:
        st.subheader("Your Subjects & Syllabus")
        
        if not user_data.subjects:
            st.info("No subjects added yet. Go to 'Add Subjects' tab to get started!")
        else:
            for idx, subject in enumerate(user_data.subjects):
                with st.expander(f"📚 {subject['name']} (Priority: {subject['priority']}, Difficulty: {subject['difficulty']})"):
                    st.write(f"**Difficulty:** {subject['difficulty']}")
                    st.write(f"**Priority:** {subject['priority']}")
                    st.write(f"**Hours per week:** {subject['hours_per_week']}")
                    st.write("**Syllabus Topics:**")
                    for topic in subject['syllabus']:
                        st.write(f"  • {topic}")
                    
                    if st.button(f"Remove {subject['name']}", key=f"remove_{idx}"):
                        subjects_list = user_data.subjects
                        subjects_list.pop(idx)
                        user_data.subjects = subjects_list
                        syllabus_dict = user_data.syllabus
                        del syllabus_dict[subject['name']]
                        user_data.syllabus = syllabus_dict
                        st.rerun()

# Study Routine Page
elif page == "📅 Study Routine":
    st.title("📅 Study Routine Planner")
    
    if not st.session_state.subjects:
        st.warning("Please add subjects first in the 'Subjects & Syllabus' section!")
    else:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Generate Your Routine")
            
            study_hours_per_day = st.slider("Study hours per day", 1, 12, 4)
            preferred_time = st.selectbox(
                "Preferred study time",
                ["Morning (6AM-12PM)", "Afternoon (12PM-5PM)", "Evening (5PM-9PM)", "Night (9PM-12AM)", "Mixed"]
            )
            
            break_interval = st.slider("Break interval (minutes)", 15, 60, 30)
            break_duration = st.slider("Break duration (minutes)", 5, 30, 10)
            
            if st.button("Generate Study Routine", type="primary"):
                if not study_planner_agent:
                    st.error("⚠️ Please configure your Gemini API key in the sidebar first!")
                else:
                    with st.spinner("Creating your personalized study routine..."):
                        subjects_info = "\n".join([
                            f"- {s['name']}: Priority {s['priority']}, Difficulty {s['difficulty']}, "
                            f"{s['hours_per_week']} hrs/week, Topics: {', '.join(s['syllabus'][:3])}..."
                            for s in st.session_state.subjects
                        ])
                        
                        routine_task = Task(
                            description=f"""Create a personalized study routine based on the following:
                            
                            Subjects: {subjects_info}
                            
                            Constraints:
                            - Study hours per day: {study_hours_per_day}
                            - Preferred time: {preferred_time}
                            - Break every {break_interval} minutes for {break_duration} minutes
                            
                            Create a detailed weekly schedule that:
                            1. Balances all subjects based on their priority and difficulty
                            2. Allocates more time to high-priority and difficult subjects
                            3. Includes specific topics to study each session
                            4. Incorporates revision time
                            5. Provides a day-by-day breakdown
                            
                            Format the schedule clearly with days of the week and time slots.""",
                            expected_output="A detailed, well-structured weekly study schedule",
                            agent=study_planner_agent
                        )
                        
                        crew = Crew(
                            agents=[study_planner_agent],
                            tasks=[routine_task],
                            verbose=False
                        )
                        
                        result = crew.kickoff()
                        st.session_state.study_routine = result.raw
                        st.rerun()
        
        with col2:
            if st.session_state.study_routine:
                st.subheader("Your Study Routine")
                st.markdown(st.session_state.study_routine)
                
                if st.button("Clear Routine"):
                    st.session_state.study_routine = None
                    st.rerun()
            else:
                st.info("Generate a routine to see it here!")

# Tests & Exams Page
elif page == "📝 Tests & Exams":
    st.title("📝 Tests & Grand Tests")
    
    if not st.session_state.subjects:
        st.warning("Please add subjects first in the 'Subjects & Syllabus' section!")
    else:
        tab1, tab2, tab3 = st.tabs(["Create Test", "Take Test", "Test History"])
        
        with tab1:
            st.subheader("Create a New Test")
            
            test_subject = st.selectbox(
                "Select Subject",
                [s["name"] for s in st.session_state.subjects]
            )
            
            test_type = st.selectbox(
                "Test Type",
                ["Quick Test (5 questions)", "Standard Test (10 questions)", "Grand Test (20 questions)"]
            )
            
            difficulty = st.select_slider(
                "Test Difficulty",
                options=["Easy", "Medium", "Hard", "Mixed"],
                value="Medium"
            )
            
            if st.button("Generate Test", type="primary"):
                if not test_creator_agent:
                    st.error("⚠️ Please configure your Gemini API key in the sidebar first!")
                else:
                    with st.spinner("Creating your test..."):
                        subject_data = next(s for s in st.session_state.subjects if s["name"] == test_subject)
                        topics = ", ".join(subject_data["syllabus"])
                        
                        num_questions = 5 if "Quick" in test_type else (10 if "Standard" in test_type else 20)
                        
                        test_task = Task(
                            description=f"""Create a {difficulty} level test on {test_subject}.
                            
                            Topics to cover: {topics}
                            
                            Create {num_questions} multiple choice questions.
                            
                            For each question, provide:
                            1. The question text
                            2. 4 options (A, B, C, D)
                            3. The correct answer
                            4. A brief explanation of why it's correct
                            
                            Format as JSON:
                            {{
                                "questions": [
                                    {{
                                        "question": "...",
                                        "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
                                        "correct": "A",
                                        "explanation": "..."
                                    }}
                                ]
                            }}""",
                            expected_output="A JSON-formatted test with questions, options, correct answers, and explanations",
                            agent=test_creator_agent
                        )
                        
                        crew = Crew(
                            agents=[test_creator_agent],
                            tasks=[test_task],
                            verbose=False
                        )
                        
                        result = crew.kickoff()
                        
                        try:
                            # Try to parse JSON from the result
                            import re
                            json_match = re.search(r'\{.*\}', result.raw, re.DOTALL)
                            if json_match:
                                test_data = json.loads(json_match.group())
                            else:
                                test_data = json.loads(result.raw)
                            
                            st.session_state.current_test = {
                                "subject": test_subject,
                                "type": test_type,
                                "difficulty": difficulty,
                                "questions": test_data["questions"],
                                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                            }
                            st.session_state.test_answers = {}
                            st.success("✅ Test created! Go to 'Take Test' tab to start.")
                        except Exception as e:
                            st.error(f"Error parsing test. Please try again.")
                            st.text(result.raw)
        
        with tab2:
            if st.session_state.current_test:
                st.subheader(f"📝 {st.session_state.current_test['subject']} - {st.session_state.current_test['type']}")
                st.write(f"Difficulty: {st.session_state.current_test['difficulty']}")
                
                with st.form("test_form"):
                    for idx, q in enumerate(st.session_state.current_test["questions"]):
                        st.markdown(f"**Question {idx + 1}:** {q['question']}")
                        answer = st.radio(
                            f"Select your answer for Q{idx + 1}",
                            q["options"],
                            key=f"q_{idx}",
                            index=None
                        )
                        st.session_state.test_answers[idx] = answer[0] if answer else None
                        st.markdown("---")
                    
                    submitted = st.form_submit_button("Submit Test")
                    
                    if submitted:
                        correct = 0
                        total = len(st.session_state.current_test["questions"])
                        
                        for idx, q in enumerate(st.session_state.current_test["questions"]):
                            if st.session_state.test_answers.get(idx) == q["correct"]:
                                correct += 1
                        
                        score = (correct / total) * 100
                        
                        test_result = {
                            "subject": st.session_state.current_test["subject"],
                            "type": st.session_state.current_test["type"],
                            "difficulty": st.session_state.current_test["difficulty"],
                            "score": score,
                            "correct": correct,
                            "total": total,
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                        
                        st.session_state.test_history.append(test_result)
                        
                        st.success(f"Test completed! Score: {score:.1f}% ({correct}/{total})")
                        
                        with st.expander("View Detailed Results"):
                            for idx, q in enumerate(st.session_state.current_test["questions"]):
                                user_answer = st.session_state.test_answers.get(idx, "Not answered")
                                is_correct = user_answer == q["correct"]
                                
                                st.markdown(f"**Q{idx + 1}:** {q['question']}")
                                st.write(f"Your answer: {user_answer}")
                                st.write(f"Correct answer: {q['correct']}")
                                st.write(f"✅ {q['explanation']}" if is_correct else f"❌ {q['explanation']}")
                                st.markdown("---")
                        
                        st.session_state.current_test = None
                        st.session_state.test_answers = {}
            else:
                st.info("No active test. Create a test in the 'Create Test' tab!")
        
        with tab3:
            st.subheader("Test History")
            
            if not st.session_state.test_history:
                st.info("No tests taken yet!")
            else:
                for test in reversed(st.session_state.test_history):
                    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
                    with col1:
                        st.write(f"**{test['subject']}**")
                    with col2:
                        st.write(f"{test['type']}")
                    with col3:
                        color = "green" if test['score'] >= 80 else "orange" if test['score'] >= 60 else "red"
                        st.markdown(f"<span style='color:{color};font-weight:bold;'>{test['score']:.1f}%</span>", unsafe_allow_html=True)
                    with col4:
                        st.write(f"{test['date']}")
                    st.markdown("---")

# Homework Help Page
elif page == "❓ Homework Help":
    st.title("❓ Homework Helper")
    st.markdown("Get help with your homework questions using AI-powered assistance!")
    
    # Display chat history
    for message in st.session_state.homework_chat:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    if prompt := st.chat_input("Ask your homework question here..."):
        st.session_state.homework_chat.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            if not homework_helper_agent:
                response = "⚠️ Please configure your Gemini API key in the sidebar to use this feature."
                st.markdown(response)
            else:
                with st.spinner("Thinking..."):
                    homework_task = Task(
                        description=f"""Help with this homework question: {prompt}
                        
                        Please provide:
                        1. A clear, comprehensive explanation
                        2. Step-by-step breakdown if it's a problem
                        3. Relevant examples
                        4. Additional helpful context
                        
                        Make your response educational and easy to understand.""",
                        expected_output="A detailed, helpful response to the homework question",
                        agent=homework_helper_agent
                    )
                    
                    crew = Crew(
                        agents=[homework_helper_agent],
                        tasks=[homework_task],
                        verbose=False
                    )
                    
                    result = crew.kickoff()
                    response = result.raw
                    
                st.markdown(response)
        
        st.session_state.homework_chat.append({"role": "assistant", "content": response})
    
    if st.button("Clear Chat"):
        st.session_state.homework_chat = []
        st.rerun()

# Definitions Page
elif page == "📖 Definitions":
    st.title("📖 Definition Lookup")
    st.markdown("Look up definitions for any term or concept from any field of study!")
    
    # Display chat history
    for message in st.session_state.definitions_chat:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    if prompt := st.chat_input("Enter a term or concept to define..."):
        st.session_state.definitions_chat.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            if not definition_expert_agent:
                response = "⚠️ Please configure your Gemini API key in the sidebar to use this feature."
                st.markdown(response)
            else:
                with st.spinner("Looking up definition..."):
                    definition_task = Task(
                        description=f"""Provide a comprehensive definition for: {prompt}
                        
                        Please include:
                        1. Clear, concise definition
                        2. Etymology/origin if relevant
                        3. Examples of usage
                        4. Related concepts or terms
                        5. Any important context or nuances
                        
                        Make it educational and easy to understand.""",
                        expected_output="A comprehensive definition with context and examples",
                        agent=definition_expert_agent
                    )
                    
                    crew = Crew(
                        agents=[definition_expert_agent],
                        tasks=[definition_task],
                        verbose=False
                    )
                    
                    result = crew.kickoff()
                    response = result.raw
                    
                st.markdown(response)
        
        st.session_state.definitions_chat.append({"role": "assistant", "content": response})
    
    if st.button("Clear Definitions"):
        st.session_state.definitions_chat = []
        st.rerun()
