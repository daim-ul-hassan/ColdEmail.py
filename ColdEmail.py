import streamlit as st
import os
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import ScrapeWebsiteTool
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Email Coder",
    page_icon=":email:",
    layout="wide"
)

if "count" not in st.session_state:
    st.session_state.count = 0

# Initialize session state for API key
if "api_key" not in st.session_state:
    st.session_state.api_key = ""
    
with st.sidebar:
    st.header("Settings")
    
    # API Key input
    api_key_input = st.text_input(
        "Gemini API Key", 
        type="password", 
        value=st.session_state.api_key or os.getenv("GOOGLE_API_KEY", "")
    )
    
    # Store API key in session state when provided
    if api_key_input:
        cleaned_key = api_key_input.strip()
        st.session_state.api_key = cleaned_key
        os.environ["GOOGLE_API_KEY"] = cleaned_key
        os.environ["GEMINI_API_KEY"] = cleaned_key
        st.success("API Key configured!")
    else:
        st.warning("Please enter Gemini API Key")
    
    name = st.text_input("Your name")

st.title("Welcome!")
if name:
    st.write(f"Hello, {name}!")
else:
    st.write("Enter your name in the sidebar!")

col1, col2 = st.columns(2)
with col1:
    if st.button("Click me"):
        st.session_state.count += 1
with col2:
    st.metric("Clicks", st.session_state.count)

agency_services = """
1. SEO Optimization Service: Best for companies with good products but low traffic. We increase organic reach.
2. Custom Web Development: Best for companies with outdated, ugly or slow websites. We build modern React/Python sites.
3. AI Automation: Best for companies with manual, repetitive tasks. We build agents to save time.
"""

# Target URL input
target_url = st.text_input("Target Website URL", placeholder="https://example.com", value="https://openai.com/")

if st.button("Generate Cold Email", type="primary"):
    if not st.session_state.api_key:
        st.error("Please enter your Gemini API Key in the sidebar!")
    elif not target_url:
        st.error("Please enter a target website URL!")
    else:
        with st.spinner("Researching and generating your cold email..."):
            # Initialize LLM inside the button click with fresh API key
            try:
                llm = LLM(
                    model="gemini/gemini-2.5-flash",
                    api_key=st.session_state.api_key
                )
            except Exception as e:
                st.error(f"Failed to initialize LLM: {e}")
                st.stop()
            
            scrape_tool = ScrapeWebsiteTool()
            
            researcher = Agent(
                role='Business Intelligence Analyst',
                goal='Analyze the target company website and identify their core business and potential weaknesses.',
                backstory="You are an expert at analyzing businesses just by looking at their landing page. You look for what they do and where they might be struggling.",
                tools=[scrape_tool],
                verbose=False,
                allow_delegation=False,
                llm=llm
            )
            
            strategist = Agent(
                role='Agency Strategist',
                goal='Match the target company needs with ONE of our agency services.',
                backstory=f"""You work for a top-tier digital agency.
                Your goal is to read the analysis of a prospect and decide which of OUR services to pitch.

                OUR SERVICES KNOWLEDGE BASE:
                {agency_services}

                You must pick the SINGLE best service for this specific client and explain why.""",
                verbose=False,
                llm=llm 
            )
            
            writer = Agent(
                role='Senior Sales Copywriter',
                goal='Write a personalized cold email that sounds human and professional.',
                backstory="""You write emails that get replies. You never sound robotic.
                You mention specific details found by the Researcher to prove we actually looked at their site.""",
                verbose=False,
                llm=llm
            )
            
            task_analyze = Task(
                description=f"Scrape the website {target_url}. Summarize what the company does and identify 1 key area where they could improve (e.g., design, traffic, automation).",
                expected_output="A brief summary of the company and their potential pain points.",
                agent=researcher
            )
            
            task_strategize = Task(
                description="Based on the analysis, pick ONE service from our Agency Knowledge Base that solves their problem. Explain the match.",
                expected_output="The selected service and the reasoning for the match.",
                agent=strategist
            )
            
            task_write = Task(
                description="Draft a cold email to the CEO of the target company. Pitch the selected service. Keep it under 150 words.",
                expected_output="A professional cold email ready to send.",
                agent=writer
            )
            
            sales_crew = Crew(
                agents=[researcher, strategist, writer],
                tasks=[task_analyze, task_strategize, task_write],
                process=Process.sequential,
                verbose=False
            )
            
            try:
                result = sales_crew.kickoff()
                st.success("Cold email generated!")
                st.text_area("Your Cold Email", value=result.raw, height=300)
            except Exception as e:
                st.error(f"Error generating email: {e}")

st.write(f"Button clicked {st.session_state.count} times!")