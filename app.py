# Fix for pysqlite3 import error on Streamlit
import sys
__import__('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import streamlit as st
import os
import time
from crewai import Agent, Task, Crew
from crewai_tools import SerperDevTool
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

# Load environment variables (if using a .env file)
# from dotenv import load_dotenv
# load_dotenv()

# Configure page settings
st.set_page_config(
    page_title="Stock Research Assistant",
    page_icon="📊",
    layout="wide"
)

# Header
st.title("Stock Research Assistant")

# Sidebar
with st.sidebar:
    st.image(
        "https://raw.githubusercontent.com/joaomdmoura/crewAI/main/docs/crewai_logo.png", width=150)

# Useful when running locally - Can set API keys in a .env file
    # openai_key = os.environ.get("OPENAI_API_KEY")
    # serper_key = os.environ.get("SERPER_API_KEY")
    # if openai_key and serper_key:
    #     st.success("Retrieved API Keys from environment variables.")
    # else:
    #     # API Key input
    #     st.subheader("API Keys")
    #     openai_key = st.text_input("OpenAI API Key", type="password")
    #     serper_key = st.text_input("Serper API Key", type="password")

    #     if st.button("Save Keys"):
    #         if openai_key:
    #             os.environ["OPENAI_API_KEY"] = openai_key
    #             st.success("OpenAI API Key set!")
    #         if serper_key:
    #             os.environ["SERPER_API_KEY"] = serper_key
    #             st.success("Serper API Key set!")

    # API Key input
    st.subheader("API Keys")
    openai_key = st.text_input("OpenAI API Key", type="password")
    serper_key = st.text_input("Serper API Key", type="password")

    if st.button("Save Keys"):
        if openai_key:
            os.environ["OPENAI_API_KEY"] = openai_key
            st.success("OpenAI API Key set!")
        if serper_key:
            os.environ["SERPER_API_KEY"] = serper_key
            st.success("Serper API Key set!")

    # Agent information
    st.subheader("About the Agent")
    st.markdown("""
    The Financial Research Specialist gathers comprehensive information about companies including:
    
    - Company overview
    - Recent news and developments
    - Competitor analysis
    - Products and services
    - Strategic initiatives
    - Financial performance
    
    The agent uses web search tools to compile the latest information and present it in a clear report.
    """)

    # Disclaimer
    st.caption(
        "Disclaimer: This is for educational purposes only. Not financial advice.")

# Main content area
col1, col2 = st.columns([1, 3])

with col1:
    # Stock input section
    ticker_input = st.text_input(
        "Enter Stock Ticker Symbol", placeholder="AAPL").upper()
    analyze_button = st.button(
        "Analyze Stock", type="primary", use_container_width=True)

with col2:
    # Display a stock preview from yfinance
    if ticker_input:
        try:
            # Get stock info
            stock_info = yf.Ticker(ticker_input).info
            company_name = stock_info.get('longName', ticker_input)
            sector = stock_info.get('sector', 'N/A')
            industry = stock_info.get('industry', 'N/A')

            # Show basic info
            st.subheader(f"{company_name} ({ticker_input})")
            st.text(f"Sector: {sector} | Industry: {industry}")

            # Show price chart
            end_date = datetime.now()

            # Give slider to select the time period and Give 3 buttons: 1 month, 3 months, 6 months
            time_period = st.select_slider(
                "Select Time Period", options=["1 Month", "3 Months", "6 Months"], value="3 Months")
            time_period_mapping = {
                "1 Month": 30,
                "3 Months": 90,
                "6 Months": 180
            }
            start_date = end_date - \
                timedelta(days=time_period_mapping[time_period])

            df = yf.download(ticker_input, start=start_date, end=end_date)
            if not df.empty:
                # Handle MultiIndex columns if present
                if isinstance(df.columns, pd.MultiIndex):
                    # Extract the price data with ticker name
                    fig = go.Figure(data=[go.Candlestick(
                        x=df.index,
                        open=df[('Open', ticker_input)],
                        high=df[('High', ticker_input)],
                        low=df[('Low', ticker_input)],
                        close=df[('Close', ticker_input)],
                        name='Candlestick'
                    )])
                else:
                    # Standard column names
                    fig = go.Figure(data=[go.Candlestick(
                        x=df.index,
                        open=df['Open'],
                        high=df['High'],
                        low=df['Low'],
                        close=df['Close'],
                        name='Candlestick'
                    )])

                fig.update_layout(
                    title=f"3 Month Price History",
                    xaxis_title="Date",
                    yaxis_title="Price ($)",
                    height=300,
                    margin=dict(l=0, r=0, t=40, b=0),
                    template="plotly_white"
                )

                st.plotly_chart(fig, use_container_width=True)

                # Key metrics
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    market_cap = stock_info.get('marketCap', 'N/A')
                    if market_cap != 'N/A':
                        market_cap = f"${market_cap / 1_000_000_000:.2f}B"
                    st.metric("Market Cap", market_cap)

                with col2:
                    pe_ratio = stock_info.get('trailingPE', 'N/A')
                    st.metric("P/E Ratio", pe_ratio)

                with col3:
                    div_yield = stock_info.get('dividendYield', 'N/A')
                    if div_yield != 'N/A':
                        div_yield = f"{div_yield * 100:.2f}%"
                    st.metric("Dividend Yield", div_yield)

                with col4:
                    fifty_two_week_high = stock_info.get(
                        'fiftyTwoWeekHigh', 'N/A')
                    fifty_two_week_low = stock_info.get(
                        'fiftyTwoWeekLow', 'N/A')
                    st.metric("52W High/Low",
                              f"${fifty_two_week_high}/{fifty_two_week_low}")

        except Exception as e:
            st.warning(
                f"Unable to get stock information. Please check the ticker symbol.")

# Research section
if analyze_button and ticker_input:
    research_section = st.container()

    with research_section:
        st.subheader(f"Analyzing {ticker_input}...")
        progress = st.progress(0)
        status = st.empty()

        status.text("Initializing research agent...")

        try:
            # Initialize tools
            search_tool = SerperDevTool()

            # Define Researcher Agent
            researcher = Agent(
                role="Financial Research Specialist",
                goal=f"Gather comprehensive information about {ticker_input} for investors",
                backstory="""You are an experienced financial researcher with a knack for
                finding the most relevant information about companies. You know how to
                filter through news and data to identify key developments.""",
                verbose=True,
                llm="gpt-4o-mini-2024-07-18",
                tools=[search_tool],
                max_iterations=3,
                max_token_limit=15000
            )

            progress.progress(30)
            status.text("Creating research task...")

            # Define Research Task
            research_task = Task(
                description=f"""Research the company {ticker_input} and gather the following information:
                1. Company overview and main business areas
                2. Recent news and developments (last 3 months)
                3. Key competitors and market position
                4. Major products or services
                5. Recent strategic initiatives
                6. Financial performance overview
                7. Market trends affecting the company
                8. Analysis of strengths and potential risks
                
                Be thorough but concise. Focus on information relevant to investors.
                Cite your sources where appropriate.
                
                Organize your findings in clear sections with proper headings.
                
                End with a brief summary of key investment considerations.
                """,
                agent=researcher,
                expected_output="A comprehensive research report on the company"
            )

            # Create Crew
            crew = Crew(
                agents=[researcher],
                tasks=[research_task],
                verbose=True
            )

            progress.progress(60)
            status.text(f"Researching {ticker_input}...")

            # Run the analysis
            with st.spinner(f"Gathering information about {ticker_input}..."):
                result = crew.kickoff()
                progress.progress(100)
                status.empty()

            # Display results
            st.subheader("Research Report")
            st.markdown(result)

        except Exception as e:
            st.error(f"Error during analysis: {str(e)}")
