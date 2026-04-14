from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_ollama import ChatOllama
from langchain_classic import hub

from tools import search_pubmed, read_pdf, summarize_research, store_reference_information


def create_agent(model: str, temperature: float = 0):
    llm = ChatOllama(
        model=model,
        temperature=temperature
    )

    tools = [search_pubmed, read_pdf, store_reference_information, summarize_research]

    prompt = hub.pull("hwchase17/react")

    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=prompt)

    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True
    )
    return agent_executor
