from langchain_classic.agents import AgentExecutor, create_react_agent, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain_classic import hub
from tools import search_pubmed, read_pdf, summarize_research


def create_agent():
    llm = ChatOllama(
#        model= "llama3-groq-tool-use",
        model= "llama3:8b",
        temperature=0
    )

    tools = [search_pubmed, read_pdf, summarize_research]

    # prompt = ChatPromptTemplate.from_messages(
    #     [
    #         ("system", "You are a pharmaceutical research assistant."),
    #         ("human", "{input}"),
    #         ("placeholder", "{agent_scratchpad}")
    #     ]
    # )
    # agent = create_tool_calling_agent(
    #     llm=llm,
    #     tools=tools,
    #     prompt=prompt
    # )

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