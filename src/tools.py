from langchain_classic.tools import tool
import lorem
from pypdf import PdfReader
import logging
from typing import List
from pubmed_utils import pubmed_search, get_pubmed_contents

@tool
def search_pubmed(query:str)->List[object]:
    """Search research papers related to a pharmaceutical query"""
    results = pubmed_search(query)
    if results['status_code'] == 200:
        # we have a field 'indices' that will be one or more PubMed ID's
        contents = get_pubmed_contents(results['indices'])
        if contents['status'] == 200:
            docs_xml = contents['response'].content.decode()
            return [""] # todo
        else:
            return ["no data"]
        # todo....
    else:
        logging.error("Failed to fetch query results from PubMed")
        return "" # Do we need to do something better....


@tool
def read_pdf(file_path: str) -> str:
    """Extract text from a scientific paper"""
    logging.info(f"In read_pdf with filepath: {file_path}")
    reader = PdfReader(file_path)
    text = ""

    for page in reader.pages:
        text += page.extract_text()

    return text
    return lorem.paragraph()

@tool
def summarize_research(text: str) -> str:
    """Summarize pharmaceutical research findings"""
    return f"Summary of findings\n{text[:500]}"
