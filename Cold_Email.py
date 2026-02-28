import streamlit as st
import os
from crewai import Agent, Task, Crew, Process, LLM
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Cold Email Generator",
    page_icon=":email:",
    layout="centered"
)

# Initialize session state
if "email_generated" not in st.session_state:
    st.session_state.email_generated = False
    st.session_state.generated_email = ""

# Initialize LLM placeholder
llm = None

st.title(":email: Cold Email Generator")
st.markdown("Generate personalized cold emails using AI-powered agents")

st.divider()

# Sidebar for API Key and User Info
with st.sidebar:
    st.header(":key: Configuration")
    
    # API Key input
    api_key_input = st.text_input(
        "Gemini API Key *",
        type="password",
        value=os.getenv("GEMINI_API_KEY", ""),
        placeholder="AIzaSy..."
    )
    
    if api_key_input:
        api_key = api_key_input.strip()
        os.environ["GOOGLE_API_KEY"] = api_key
        os.environ["GEMINI_API_KEY"] = api_key
        try:
            llm = LLM(
                model="gemini/gemini-2.5-flash",
                api_key=api_key
            )
            st.success(":white_check_mark: API Key configured!")
        except Exception as e:
            st.error(f":x: Error initializing LLM: {e}")
    else:
        st.warning(":warning: Please enter Gemini API Key")
    
    st.divider()
    
    # Sender name in sidebar
    sender_name = st.text_input(
        "Your Name *",
        placeholder="John Doe",
        help="The name of the person sending the cold email"
    )

st.subheader("Enter Target Details")

# Target company name
target_company = st.text_input(
    "Target Company Name *",
    placeholder="Acme Corporation",
    help="The company you want to reach out to"
)

# Target person name
target_person = st.text_input(
    "Target Person's Name",
    placeholder="Jane Smith",
    help="The specific person you're targeting (optional)"
)

# Target role if name not known
target_role = st.text_input(
    "Target Role (if name unknown)",
    placeholder="CEO, Hiring Manager, etc.",
    help="The role/title of the person you're targeting"
)

# Email purpose
purpose = st.selectbox(
    "Email Purpose *",
    options=[
        "Job Application",
        "Business Partnership",
        "Sales Pitch",
        "Networking",
        "Investment Opportunity",
        "Other"
    ]
)

# Additional context
additional_context = st.text_area(
    "Additional Context",
    placeholder="Any specific details about the company, your background, or what you want to achieve...",
    height=100
)

st.divider()

# Generate button
if st.button(":rocket: Generate Cold Email", type="primary", use_container_width=True):
    # Validation
    if not api_key_input:
        st.error(":x: Please enter your Gemini API Key in the sidebar!")
    elif not sender_name:
        st.error(":x: Please enter your name in the sidebar!")
    elif not target_company:
        st.error(":x: Please enter the target company name!")
    elif llm is None:
        st.error(":x: LLM not initialized. Please check your API key.")
    else:
        with st.spinner(":robot_face: AI Agents are crafting your cold email..."):
            try:
                # Create CrewAI Agents
                researcher = Agent(
                    role='Company Researcher',
                    goal=f'Research and analyze {target_company} to understand their business, values, and needs',
                    backstory=f"""You are an expert business researcher. Your job is to analyze companies 
                    and identify what they do, their industry, and potential pain points or opportunities. 
                    You provide detailed insights that help craft personalized cold emails.""",
                    verbose=False,
                    allow_delegation=False,
                    llm=llm
                )
                
                strategist = Agent(
                    role='Email Strategist',
                    goal=f'Determine the best approach for a {purpose} email to {target_company}',
                    backstory=f"""You are a strategic communications expert. You analyze the research 
                    about a company and determine the best angle, tone, and key points to include 
                    in a cold email to maximize response rates. You understand what makes people 
                    respond to cold outreach.""",
                    verbose=False,
                    allow_delegation=False,
                    llm=llm
                )
                
                writer = Agent(
                    role='Professional Copywriter',
                    goal='Write a compelling, personalized cold email that gets responses',
                    backstory=f"""You are an elite copywriter specializing in cold emails. You write 
                    emails that are concise, engaging, and professional. You know how to hook readers 
                    in the first sentence, provide value, and include clear calls-to-action. 
                    Your emails never sound generic or spammy.""",
                    verbose=False,
                    allow_delegation=False,
                    llm=llm
                )
                
                # Determine recipient
                recipient = target_person if target_person else (target_role if target_role else "Hiring Manager")
                
                # Create Tasks
                task_research = Task(
                    description=f"""Research {target_company} and provide insights on:
                    1. What the company does (industry, products/services)
                    2. Their likely pain points or challenges
                    3. Recent news or achievements (if applicable)
                    4. What they might value in a {purpose} context
                    
                    Additional context: {additional_context if additional_context else 'None provided'}
                    """,
                    expected_output="A detailed analysis of the company including industry, pain points, and strategic opportunities.",
                    agent=researcher
                )
                
                task_strategize = Task(
                    description=f"""Based on the company research, determine:
                    1. The best angle/hook for a {purpose} email
                    2. Key value propositions to mention
                    3. The appropriate tone (formal, casual, enthusiastic, etc.)
                    4. What specific pain point or opportunity to address
                    
                    Sender: {sender_name}
                    Recipient: {recipient} at {target_company}
                    Purpose: {purpose}
                    """,
                    expected_output="A strategic brief with recommended angle, tone, and key talking points.",
                    agent=strategist
                )
                
                task_write = Task(
                    description=f"""Write a personalized cold email with these specifications:
                    
                    FROM: {sender_name}
                    TO: {recipient} at {target_company}
                    PURPOSE: {purpose}
                    
                    Use the research and strategy provided to create an email that:
                    - Has a compelling subject line
                    - Opens with a personalized hook (not generic)
                    - Shows you've researched the company
                    - Clearly states the purpose
                    - Includes a specific, low-friction call-to-action
                    - Is 150-200 words maximum
                    - Sounds human and professional
                    
                    Format with Subject line first, then the email body.
                    Sign off as {sender_name}.
                    """,
                    expected_output="A complete, ready-to-send cold email with subject line and body.",
                    agent=writer
                )
                
                # Create and run crew
                email_crew = Crew(
                    agents=[researcher, strategist, writer],
                    tasks=[task_research, task_strategize, task_write],
                    process=Process.sequential,
                    verbose=False
                )
                
                result = email_crew.kickoff()
                
                # Save to session state
                st.session_state.generated_email = result.raw
                st.session_state.email_generated = True
                
            except Exception as e:
                st.error(f":x: Error generating email: {str(e)}")

# Display generated email
if st.session_state.email_generated:
    st.divider()
    st.subheader(":white_check_mark: Your AI-Generated Cold Email")
    
    st.text_area(
        "Email Content",
        value=st.session_state.generated_email,
        height=350,
        label_visibility="collapsed"
    )
    
    # Show as code block for easy copying
    st.code(st.session_state.generated_email, language="text")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button(":arrows_counterclockwise: Generate Another", use_container_width=True):
            st.session_state.email_generated = False
            st.session_state.generated_email = ""
            st.rerun()
    
    with col2:
        if st.button("📋 Copy Text", use_container_width=True):
            st.toast("📋 Select and copy the text from above!")

st.divider()
st.caption("🔒 Your API key is only used for this session and never stored permanently.")
st.caption("🤖 Powered by CrewAI with Gemini LLM")
