from langchain_classic.tools import tool
import lorem
from pypdf import PdfReader
import logging
from typing import List
from pubmed_utils import pubmed_search, get_pubmed_contents
from pypaperretriever import PaperRetriever

@tool
def search_pubmed(query:str)->List[object]:
    """Search research papers related to a pharmaceutical query"""
    results = pubmed_search(query)
    if results['status_code'] == 200:
        # we have a field 'indices' that will be one or more PubMed ID's
        contents = get_pubmed_contents(results['indices'])
        if contents['status_code'] == 200:
            # content_dict has the pubmedID as the key; value is the related metadata
            content_dict = contents['contents']

            return ["voodoo"] # todo
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

    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text()
    except FileNotFoundError as fnf:
        logging.error(f"File not found: {file_path}")
    return text
    return lorem.paragraph()

@tool
def summarize_research(text: str) -> str:
    """Summarize pharmaceutical research findings"""
    return f"Summary of findings\n{text[:500]}"


# TODO: Consider splitting this paper fetching logic off into another source file, and
# providing a better interface for retrieving....
#@tool
def fetch_paper_by_doi(doi: str)->object:
    """Fetch paper using Digital Object ID (DOI)"""
    retriever = PaperRetriever(
        doi=doi,
        download_directory="PDF"
    )
    retriever.download()
    return "requested"

#@tool
def fetch_paper_by_pubmed_id(pmid: str)->object:
    """Fetch paper using PubMed ID"""
    retriever = PaperRetriever(
        pmid=pmid,
        download_directory="PDF"
    )
    retriever.download()
    return "requested"