from langchain_classic.tools import tool
import requests
import lorem
from pypdf import PdfReader

@tool
def search_pubmed(query:str)->str:
    """Search research papers related to a pharmaceutical query"""
    # Mock response
    papers=[
        "mRNA vaccines show strong immune response in influenza trials.",
        "Phase 2 study indicates high antibody production using mRNA vaccines.",
        "mRNA vaccine platform shows promise for respiratory diseases."
    ]
    return "\n".join(papers)

@tool
def read_pdf(file_path: str) -> str:
    """Extract text from a scientific paper"""
    # reader = PdfReader(file_path)
    # text = ""
    #
    # for page in reader.pages:
    #     text += page.extract_text()
    #
    # return text[:2000]
    return lorem.paragraph()

@tool
def summarize_research(text: str) -> str:
    """Summarize pharmaceutical research findings"""
    return f"Summary of findings\n{text[:500]}"
