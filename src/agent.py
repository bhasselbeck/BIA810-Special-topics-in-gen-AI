from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.callbacks import BaseCallbackHandler
import tools as _tools_module
from tools import search_pubmed, read_pdf, summarize_research, store_reference_information


_REACT_TEMPLATE = """You are a biomedical research assistant. Answer the user's question using PubMed evidence.

STRICT RULES:
- Use search_pubmed to find papers, then read_pdf on the most relevant one.
- read_pdf returns a focused summary of the paper — use it as evidence to answer the question.
- Do NOT reproduce or reformat the summary text. Do NOT ask clarifying questions.
- Do NOT offer citation help, copyright advice, or access guidance.
- If read_pdf returns text starting with ERROR:, skip that paper and try another.
- After reading 1-2 papers you MUST write your Final Answer.
- Final Answer must directly answer the original question in plain prose.

Tools available:
{tools}

Format — follow EXACTLY:

Question: the input question
Thought: what you plan to do
Action: one of [{tool_names}]
Action Input: input for the tool
Observation: tool result
Thought: what you learned and what to do next
Action: one of [{tool_names}]
Action Input: input for the tool
Observation: tool result
Thought: I have enough evidence to answer
Final Answer: [your answer here — plain prose, directly addressing the question]

Begin!

Question: {input}
Thought:{agent_scratchpad}"""


# Human-readable labels shown in the live status widget
_TOOL_LABELS = {
    "search_pubmed":               "Searching PubMed",
    "read_pdf":                    "Downloading & reading paper",
    "summarize_research":          "Writing report",
    "store_reference_information": "Storing reference",
}

_TOOL_DETAIL = {
    "search_pubmed":               "Querying PubMed E-utilities and retrieving article metadata…",
    "read_pdf":                    "Fetching full-text PDF via open-access sources…",
    "summarize_research":          "Generating structured PDF report…",
    "store_reference_information": "Recording citation…",
}

# Internal LangChain pseudo-tools that should never surface to the user
_INTERNAL_TOOLS = {"_Exception", "_AgentAction", "_AgentFinish"}


class StatusCallbackHandler(BaseCallbackHandler):
    """Writes live step-by-step progress into a Streamlit container."""

    def __init__(self, status, log_container):
        self._status = status
        self._log = log_container   # st.empty() or st.container() inside the status
        self._lines: list[str] = []
        self._step = 0

    def _render(self):
        html = "\n".join(self._lines)
        self._log.markdown(html, unsafe_allow_html=True)

    def _append(self, icon: str, text: str, detail: str = "", active: bool = False):
        self._step += 1
        pulse = ' <span class="prog-pulse"></span>' if active else ' <span class="prog-done">✓</span>'
        line = (
            f'<div class="prog-line">'
            f'<span class="prog-icon">{icon}</span>'
            f'<span class="prog-text">{text}{pulse}</span>'
            + (f'<div class="prog-detail">{detail}</div>' if detail else "")
            + "</div>"
        )
        self._lines.append(line)
        self._render()
    def _complete_last(self):
        if self._lines:
            # Replace the last active pulse with a done checkmark
            self._lines[-1] = (
                self._lines[-1]
                .replace('<span class="prog-pulse"></span>', '<span class="prog-done">✓</span>')
            )
            self._render()

    def on_agent_action(self, action, **kwargs):
        if action.tool.startswith("_"):
            return
        self._complete_last()
        label  = _TOOL_LABELS.get(action.tool, action.tool)
        detail = _TOOL_DETAIL.get(action.tool, "")
        icons  = {"search_pubmed": "🔍", "read_pdf": "📄",
                  "summarize_research": "📝", "store_reference_information": "🗂️"}
        icon = icons.get(action.tool, "⚙️")
        self._status.update(label=f"{label}…")
        self._append(icon, label, detail, active=True)

    def on_tool_end(self, output, **kwargs):
        self._complete_last()

    def on_agent_finish(self, finish, **kwargs):
        self._complete_last()
        self._append("🧠", "Formulating answer", "Synthesising findings into a response…", active=True)
        self._status.update(label="Formulating answer…", state="running")


def create_agent(model: str, temperature: float = 0):
    llm = ChatOllama(model=model, temperature=temperature)

    # Share the LLM with tools so read_pdf can use it for paper summarisation
    _tools_module._llm = llm

    tools = [search_pubmed, read_pdf, store_reference_information, summarize_research]

    prompt = PromptTemplate.from_template(_REACT_TEMPLATE)

    agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=8,
        early_stopping_method="generate",
    )
