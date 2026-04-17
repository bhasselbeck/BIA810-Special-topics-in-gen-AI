import logging
from pathlib import Path

from agent import create_agent
from random import shuffle
import streamlit as st
from datetime import datetime

app_title = "BIA-810 Search Tool"
llm_models = ['qwen3:8b', 'llama3:8b', 'gpt-oss:latest']
log = logging.getLogger(__name__)

if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title=app_title, layout="wide", page_icon="🔬")

# ── Load external CSS ────────────────────────────────────────────────────────
def _load_css(path: Path) -> None:
    st.markdown(f"<style>{path.read_text()}</style>", unsafe_allow_html=True)

_load_css(Path(__file__).parent / "style.css")


# ── Helpers ───────────────────────────────────────────────────────────────────

@st.dialog("Important")
def disclaimer():
    st.markdown("""
    ## ⚠️ PLEASE NOTE
    This tool is for **educational purposes only** and any output it produces does not constitute
    medical advice. Always consult a qualified healthcare professional before starting, changing,
    or stopping any treatment. Homeopathic, supplemental and alternative therapies should be
    discussed with your physician.""")


def _check_status(model: str) -> dict:
    """Ping Ollama to verify the selected model is reachable."""
    import httpx
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        if r.status_code == 200:
            available = [m["name"] for m in r.json().get("models", [])]
            model_ok = any(m.startswith(model.split(":")[0]) for m in available)
            return {
                "online": True,
                "model_ok": model_ok,
                "label": "LLM Connected" if model_ok else "Model Not Loaded",
                "sub": f"{model} ready" if model_ok else f"{model} not found in Ollama",
            }
    except Exception:
        pass
    return {"online": False, "model_ok": False, "label": "LLM Offline", "sub": "Cannot reach Ollama on localhost:11434"}


def _display_citations(citations: list[str]) -> None:
    if not citations:
        return
    st.markdown("### Sources & Citations")
    for i, citation in enumerate(citations, 1):
        st.markdown(f'<div class="citation">[{i}] {citation}</div>', unsafe_allow_html=True)


def _display_videos(youtube_links: list[str]) -> None:
    if not youtube_links:
        return
    st.markdown("### Video Resources")
    for link in youtube_links:
        st.markdown(
            f'<div class="citation"><a href="{link}" target="_blank" style="color:#00AFF0">▶ {link}</a></div>',
            unsafe_allow_html=True,
        )


def _display_response(response) -> None:
    try:
        output_text = response["output"]
    except (KeyError, TypeError):
        output_text = str(response)

    st.markdown(f"""
    <div class="answer-card">
        <div class="answer-header">
            <div class="answer-title">Answer</div>
            <span class="evidence-badge">Evidence-Based</span>
        </div>
        <div class="answer-body">{output_text}</div>
    </div>
    """, unsafe_allow_html=True)

    if "therapy_sections" in response:
        st.markdown("#### Treatment Dimensions")
        cols = st.columns(2)
        for i, (dimension, content) in enumerate(response["therapy_sections"].items()):
            with cols[i % 2]:
                st.markdown(f"**{dimension}**")
                st.markdown(content)

    if "youtube_links" in response:
        _display_videos(response["youtube_links"])

    if "citations" in response:
        _display_citations(response["citations"])

    if "safety_disclaimer" in response:
        st.markdown(
            f'<div class="safety-disclaimer"><strong>⚠️ Medical Disclaimer:</strong><br/>{response["safety_disclaimer"]}</div>',
            unsafe_allow_html=True,
        )

    try:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Response Time", f"{response.elapsed_seconds:.1f}s")
        with col2:
            st.metric("Memory Note", response.memory_note)
    except AttributeError:
        pass


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.logo(
    image=str(Path(__file__).parent.parent / "images" / "Pfizer_Logo_White.png"),
    size="large",
    link="https://www.pfizer.com",
)

with st.sidebar:
    st.markdown('<div class="sidebar-label">Configuration</div>', unsafe_allow_html=True)
    model = st.selectbox("Model", llm_models, label_visibility="visible")
    temperature = st.slider("Temperature", min_value=0.0, max_value=2.0, value=0.0, step=0.05)
    max_pubmed_docs = st.sidebar.number_input("Max PubMed Docs", min_value=1, max_value=20, value=5)
    st.session_state.max_pubmed_docs = max_pubmed_docs

    st.button("Disclaimer", on_click=disclaimer)

    status = _check_status(model)
    dot_color = "#00AFF0" if status["online"] and status["model_ok"] else "#f87171"
    st.markdown(f"""
    <div class="status-badge">
        <div class="status-dot" style="background:{dot_color};"></div>
        <div>
            <div class="status-text">{status['label']}</div>
            <div class="status-sub">{status['sub']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["Ask a Question", "About"])

with tab1:
    st.markdown("""
    <div class="hero-title">BIA–<span>810</span> Search Tool</div>
    <div class="hero-sub">AI-powered medical literature search &amp; analysis &nbsp;•&nbsp; <b>Powered by PubMed</b></div>
    """, unsafe_allow_html=True)

    agent = create_agent(model=model, temperature=temperature)

    question = st.text_input(
        "Query",
        placeholder="Ask a medical or pharmaceutical research question…",
        label_visibility="collapsed",
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        submit = st.button("Search", use_container_width=True)
    with col2:
        clear = st.button("Clear History", use_container_width=True)

    if clear:
        st.session_state.messages = []
        st.rerun()

    if submit and question:
        st.session_state.question = question
        try:
            with st.status("Starting research…", expanded=True) as status:
                from agent import StatusCallbackHandler
                import tools as _tools_module

                log_container = st.empty()
                # Write an initial animated placeholder immediately so the box
                # is never visually empty while the agent is warming up
                log_container.markdown("""
<div class="prog-line">
    <span class="prog-icon">⚙️</span>
    <span class="prog-text">Initializing agent <span class="prog-pulse"></span></span>
    <div class="prog-detail">Loading model and preparing tools…</div>
</div>
""", unsafe_allow_html=True)

                def _on_search_done(pmids: list[str]):
                    status.update(label="Pre-fetching papers in parallel…")
                    _tools_module._prefetch_cache.update(
                        _tools_module.prefetch_papers(pmids)
                    )

                _tools_module._on_search_done = _on_search_done

                response = agent.invoke(
                    {"input": question},
                    config={"callbacks": [StatusCallbackHandler(status, log_container)]},
                )
                status.update(label="Research complete", state="complete", expanded=False)
            st.session_state.messages.append({
                "question": question,
                "response": response,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
            _display_response(response)
        except Exception as e:
            st.error(f"Error processing question: {str(e)}")
            log.exception("Exception in asking question")

    if st.session_state.messages:
        st.markdown('<div class="history-header"><div class="history-title">Session History</div></div>',
                    unsafe_allow_html=True)
        for msg in reversed(st.session_state.messages):
            preview = msg["question"][:70] + ("…" if len(msg["question"]) > 70 else "")
            with st.expander(f"Q: {preview}   —   {msg['timestamp']}"):
                st.caption(f"Asked: {msg['timestamp']}")
                st.caption(f"Question: {msg['question']}")
                _display_response(msg['response'])

with tab2:
    st.markdown(f"### {app_title}")
    st.markdown("""
    ## A Research Assistant for Healthcare Research

    This tool helps researchers quickly surface evidence-based answers
    from the PubMed literature corpus using AI-powered search and analysis.
    """)
    st.markdown("---")
    names = ["Mick Twohig", "Matt Kelly", "Brian Hasselbeck"]
    shuffle(names)
    st.markdown("Created by " + ", ".join(names[:-1]) + " & " + names[-1])
