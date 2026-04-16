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
    "search_pubmed":              "Searching PubMed…",
    "read_pdf":                   "Downloading & reading paper…",
    "summarize_research":         "Writing report…",
    "store_reference_information":"Storing reference…",
}

# Internal LangChain pseudo-tools that should never surface to the user
_INTERNAL_TOOLS = {"_Exception", "_AgentAction", "_AgentFinish"}


class StatusCallbackHandler(BaseCallbackHandler):
    """Pushes live agent step updates into a Streamlit status container."""

    def __init__(self, status):
        self._status = status

    def on_agent_action(self, action, **kwargs):
        # Ignore internal LangChain error-recovery pseudo-tools
        if action.tool.startswith("_"):
            return
        label = _TOOL_LABELS.get(action.tool, f"Running {action.tool}…")
        self._status.update(label=label)

    def on_tool_end(self, output, **kwargs):
        pass  # status stays on the last action label until next step

    def on_agent_finish(self, finish, **kwargs):
        self._status.update(label="Finalising answer…", state="running")


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
