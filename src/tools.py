from langchain_classic.tools import tool
import lorem
from pypdf import PdfReader
import logging
from typing import List
from pubmed_utils import pubmed_search, get_pubmed_contents
from pypaperretriever import PaperRetriever
import os
import string
import random
from fpdf import FPDF

log = logging.getLogger(__name__)

@tool
def search_pubmed(query:str)->List[object]:
    """Search research papers related to a pharmaceutical query. The query will return a title, a pmid and a doi"""
    results = pubmed_search(query)
    if results['status_code'] == 200:
        # we have a field 'indices' that will be one or more PubMed ID's
        contents = get_pubmed_contents(results['indices'])
        if contents['status_code'] == 200:
            # content_dict has the pubmedID as the key; value is the related metadata
            content_dict = contents['contents']
            return content_dict
        else:
            return ["no data"]
        # todo....
    else:
        logging.error("Failed to fetch query results from PubMed")
        return "" # Do we need to do something better....


@tool
def read_pdf(pmid:str = None, doi:str = None) -> str:
    """Extract text from a scientific paper. We can use either PMID or DOI"""
    logging.info(f"In read_pdf with pmid: '{pmid}' doi: '{doi}'")
    content = None
    if pmid is None and doi is None:
        logging.error("read_pdf call with no parameters")
        raise RuntimeError("Missing parameters")
    if doi is not None:
        content = fetch_paper_by_doi(doi=doi)
    if pmid is not None:
        content = fetch_paper_by_pubmed_id(pmid=pmid)
    text = ""
    try:
        if content:
            reader = PdfReader(content)
            for page in reader.pages:
                text += page.extract_text()
    except FileNotFoundError as fnf:
        logging.error(f"File not found: ")
    return text
    return lorem.paragraph()

@tool
def summarize_research(text: str) -> str:
    """Summarize pharmaceutical research findings and output as a PDF file. The function takes text content that is
     output into the pdf."""
    filename = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    filename = f"{filename}.pdf"
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.write(text=text)
#    pdf.cell(200, 10, txt=text, ln=True, align='C')
    pdf.output(filename)
    return f"Wrote pdf file {filename}"

#@tool
def fetch_paper_by_doi(doi: str)->object:
    """Fetch paper using Digital Object ID (DOI)"""
    print(f"fetch_paper_by_doi: doi = {doi}")
    filename = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    if doi.startswith("None"):
        return ""
    retriever = PaperRetriever(
        email='test@mail.com',
        doi=doi,
        download_directory="PDF",
        filename=f"{filename}.pdf",
        allow_scihub=True
    )
    download = retriever.download()
    return os.path.join(download.filepath, download.filename)

#@tool
def fetch_paper_by_pubmed_id(pmid: str)->object:
    """Fetch paper using PubMed ID"""
    print(f"fetch_paper_by_pubmed_id: pmid = {pmid}")
    filename = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    if pmid.startswith("None"):
        return ""
    retriever = PaperRetriever(
        email='test@mail.com',
        pmid=pmid,
        download_directory="PDF",
        filename=f"{filename}.pdf",
        allow_scihub=True
    )
    download = retriever.download()
    if download.is_downloaded:
        with open(os.path.join(download.filepath, download.filename), 'rb') as f:
            contents = f.read()
            return contents
    else:
        log.warning(f"fetch_paper_by_pubmed_id - failed to download pmid {pmid}")
