import logging

from agent import create_agent
from random import shuffle
import streamlit as st
from datetime import  datetime

app_title = "BIA810 Project"
llm_models=['qwen3:8b', 'llama3:8b', 'gpt-oss:latest']
log = logging.getLogger(__name__)

if "messages" not in st.session_state:
    st.session_state.messages = []

@st.dialog("Important")
def disclaimer():
    st.markdown("""
     ## ⚠️   PLEASE NOTE
     This tool is for educational purposes only and any output it produces does not constitute
     medical advice. Always consult a qualified healthcare professional before starting, changing,
     or stopping any treatment. Homeopathic, supplemental and alternative therapies should be 
     discussed with your physician.""")
def _display_citations(citations: list[str]) -> None:
    """Display citations in a formatted manner."""
    if not citations:
        return

    st.markdown("### 📚 Sources & Citations")
    for i, citation in enumerate(citations, 1):
        st.markdown(f'<div class="citation">[{i}] {citation}</div>',
                   unsafe_allow_html=True)


def _display_videos(youtube_links: list[str]) -> None:
    """Display YouTube video links."""
    if not youtube_links:
        return

    st.markdown("### 🎬 Video Resources")
    for link in youtube_links:
        st.markdown(
            f'<div class="video-link"><a href="{link}" target="_blank">▶️ {link}</a></div>',
            unsafe_allow_html=True
        )
def _format_therapy_section(dimension: str, content: str) -> None:
    """Display a therapy dimension section with formatted content."""
    st.markdown(f"### {dimension}", unsafe_allow_html=True)
    st.markdown(content)


def _display_response(response) -> None:
    """Display a complete agent response."""
    with st.container():
        st.markdown('<div class="response-container">', unsafe_allow_html=True)

        # Main answer
        st.markdown("## Answer")
        try:
           st.markdown(response['output'])
        except AttributeError as ae:
            log.error(f"Attribute error; response object is: {response}")
            st.markdown(f"❌  An error occurred; couldn't parse response properly: {response} ")
        # Therapy dimensions

        if 'therapy_sections' in response:
            st.markdown("## Treatment Dimensions")

            # Create columns for therapy dimensions
            cols = st.columns(2)
            for i, (dimension, content) in enumerate(response['therapy_sections'].items()):
                with cols[i % 2]:
                    _format_therapy_section(dimension, content)
    # Videos
        if  'youtube_links' in response:
            _display_videos(response['youtube_links'])

        # Citations
        if 'citations' in response:
            _display_citations(response['citations'])

        # Safety disclaimer
        if 'safety_disclaimer' in response:
                st.markdown(
                    f'<div class="safety-disclaimer"><strong>⚠️  Medical Disclaimer:</strong><br/>{response['safety_disclaimer']}</div>',
                    unsafe_allow_html=True
                )

        # Performance metrics
        try:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Response Time", f"{response.elapsed_seconds:.1f}s")
            with col2:
                st.metric("Memory Note", response.memory_note)

            st.markdown('</div>', unsafe_allow_html=True)

        except AttributeError:
            pass
#-------------

st.set_page_config(page_title=app_title, layout='wide')
st.logo(image="../images/Pfizer_Logo_White.png", size="large", link="https://www.pfizer.com")
st.sidebar.markdown("## Configuration")
model = st.sidebar.selectbox("Model Name", llm_models)
temperature = st.sidebar.slider("Temperature", min_value=0.0, max_value=2.0, value=0.0, step=0.05)
st.sidebar.button("Disclaimer️", on_click=disclaimer)

tab1, tab2 = st.tabs(["Ask a Question", "ℹ️ About"])
with tab1:
    st.markdown("## Welcome to BIA-810 Search Tool")

    agent = create_agent(model=model, temperature=temperature)
    question = st.text_input(
        "Query:",
        placeholder="What can I research for you?",
        label_visibility='collapsed'
    )
    col1, _, col2 = st.columns([1,2, 1])
    with col1:
        submit = st.button("Search", use_container_width=True)
    with col2:
        clear = st.button("Clear History", use_container_width=True)
    if clear:
        st.session_state.messages = []
        st.rerun()

    if submit and question:
        with st.spinner("Researching..."):
            try:
                response = agent.invoke({'input': question})
                # Add to conversation history
                st.session_state.messages.append({
                    "question": question,
                    "response": response,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                _display_response(response)
            except Exception as e:
                st.error(f"❌ Error processing question: {str(e)}")
                log.exception("Exception in asking question")
    if st.session_state.messages:
        st.markdown("---")
        st.markdown("## Session History")
        for msg in reversed(st.session_state.messages):
            with st.expander(f"Q: {msg['question'][:60]}..."):
                st.markdown(f"**Asked:** {msg['timestamp']}")
                st.markdown(f"**Question:** {msg['question']}")
                st.markdown('---')
                _display_response(msg['response'])
    # def run_query():
    #     results = agent.invoke({"input": st.session_state.query})
    #     st.write(results['output'])
    #
    # for message in st.session_state.messages:
    #     with st.chat_message(message['role']):
    #         st.markdown(message['content'])
    #
    # if prompt := st.chat_input("Enter a query"):
    #     with st.chat_message('user'):
    #         st.markdown(prompt)
    #     st.session_state.messages.append({'role': 'user', 'content': prompt})
    #     resp = agent.invoke({'input': prompt})
    #     st.session_state.messages.append({'role': 'system', 'content': resp['output']})
    #     st.write(resp["output"])

with tab2:
    st.write(f"**{app_title}**")

    st.markdown("""
    ## A Research Assistant for Healthcare Research
    
    The project aims to be a tool useful to researchers....""")
    st.markdown('---')
    names = ["Mick Twohig", "Matt Kelly", "Brian Hasselbeck"]
    shuffle(names)
    st.markdown(f"Created by " + ", ".join(names[:-1]) + " & " + names[-1])